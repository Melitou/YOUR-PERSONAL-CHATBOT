#!/usr/bin/env python3
"""
Document Processing Pipeline for RAG Chatbot
Processes documents from GridFS, parses them, chunks the content, generates summaries, and stores chunks in MongoDB
"""

import os
import asyncio
import logging
import tiktoken
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Database imports
from db_service import initialize_db, User_Auth_Table, Documents, Chunks
from gridfs import GridFS

# Parser imports
from pdf_parsing import pdf_to_md
from docx_parsing import docx_to_md
from csv_parsing import csv_to_md
from txt_parsing import txt_to_md
from keyword_extractor import KeywordExtractor

# OpenAI and rate limiting
from dotenv import load_dotenv
try:
    from openai import AsyncOpenAI, OpenAIError
    from aiolimiter import AsyncLimiter
    import backoff
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Please install: pip install openai aiolimiter backoff")
    raise

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Chunking methods imports
try:
    from chunking_methods import token_chunk, semantic_chunk, line_chunk, recursive_chunk
    CHUNKING_METHODS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import chunking methods: {e}")
    CHUNKING_METHODS_AVAILABLE = False


class DocumentProcessor:
    """Document processing pipeline that converts GridFS documents to chunked content with summaries"""

    def __init__(self, max_workers: int = 4, rate_limit_delay: float = 0.2,
                 chunking_method: str = "token", chunking_params: dict = None):
        """Initialize the document processor

        Args:
            max_workers: Maximum number of parallel workers (default: 4)
            rate_limit_delay: Delay between database operations in seconds (default: 0.2)
            chunking_method: Chunking method to use ('token', 'semantic', 'line', 'recursive') (default: 'token')
            chunking_params: Parameters for the chunking method (default: None, uses method defaults)
        """
        # Initialize database connections
        self.client, self.db, self.fs = initialize_db()
        if not self.client:
            raise Exception("Failed to connect to database")

        # Parallel processing settings
        self.max_workers = min(max_workers, 5)  # Cap at 5 for MongoDB safety
        self.rate_limit_delay = rate_limit_delay
        self._db_lock = Lock()  # Thread-safe database operations

        # Processing statistics
        self._stats = {
            'processed': 0,
            'failed': 0,
            'chunks_created': 0,
            'start_time': None
        }
        self._stats_lock = Lock()

        # OpenAI configuration (from split_and_upload_md.py)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise Exception("OPENAI_API_KEY environment variable not set")

        self.summary_model = "gpt-4.1-mini"  # Updated model name
        self.encoding_name = "cl100k_base"
        self.summary_rpm = 2000  # requests per minute

        # Initialize tiktoken encoding
        self.encoding = tiktoken.get_encoding(self.encoding_name)

        # OpenAI client and rate limiter
        self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
        self.summary_rate_limiter = AsyncLimiter(self.summary_rpm, 60)

        # Chunking method configuration
        self.chunking_method = chunking_method.lower()
        if self.chunking_method not in ['token', 'semantic', 'line', 'recursive']:
            raise ValueError(
                f"Invalid chunking method: {chunking_method}. Must be one of: token, semantic, line, recursive")

        # Validate chunking methods availability
        if not CHUNKING_METHODS_AVAILABLE:
            logger.warning(
                "Chunking methods not available, falling back to built-in token chunking")
            self.chunking_method = 'token'

        # Set default parameters for each chunking method
        self.chunking_params = chunking_params or {}
        self._set_default_chunking_params()

        # Legacy chunking parameters (for backward compatibility)
        self.max_tokens = 7000
        self.overlap = 300

        # Parser mapping
        self.parser_map = {
            "pdf": pdf_to_md,
            "docx": docx_to_md,
            "csv": csv_to_md,
            "txt": txt_to_md
        }

        # Keyword extractor
        self.keyword_extractor = KeywordExtractor()

        # Prompts (from split_and_upload_md.py)
        self.document_context_prompt = """
<document>
{doc_content}
</document>
"""

        self.chunk_context_prompt = """
Here is the chunk we want to situate within the whole document:
<chunk>
{chunk_content}
</chunk>

Please give a short, succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk.
Focus on what this specific chunk is about in relation to the entire document.
Answer only with the succinct context and nothing else.
"""

        logger.info(
            f"DocumentProcessor initialized with {self.max_workers} workers")
        logger.info(
            f"Rate limit: {self.rate_limit_delay}s delay, Summary RPM: {self.summary_rpm}")
        logger.info(
            f"Chunking method: {self.chunking_method} with params: {self.chunking_params}")

    def _set_default_chunking_params(self):
        """Set default parameters for each chunking method"""
        defaults = {
            'token': {
                'token_count': 7000,
                'overlap': 300,
                'encoding_name': 'cl100k_base'
            },
            'semantic': {
                'embedding_model': 'text-embedding-3-small',
                'breakpoint_threshold_type': 'percentile'
            },
            'line': {
                'line_count': 300,
                'overlap': 100
            },
            'recursive': {
                'chunk_size': 1000,
                'overlap': 100
            }
        }

        # Merge defaults with user-provided parameters
        method_defaults = defaults.get(self.chunking_method, {})
        for key, value in method_defaults.items():
            if key not in self.chunking_params:
                self.chunking_params[key] = value

    def _update_stats(self, result_type: str, count: int = 1):
        """Thread-safe statistics update"""
        with self._stats_lock:
            if result_type in self._stats:
                self._stats[result_type] += count

    def num_tokens_from_string(self, string: str) -> int:
        """Returns the number of tokens in a text string using the configured encoding."""
        return len(self.encoding.encode(string))

    def chunk_text(self, text: str) -> List[str]:
        """Chunk text using the configured chunking method.

        Args:
            text: The text to chunk

        Returns:
            List of text chunks

        Raises:
            Exception: If chunking fails or method is not available
        """
        try:
            if self.chunking_method == 'token':
                return self._chunk_token(text)
            elif self.chunking_method == 'semantic':
                return self._chunk_semantic(text)
            elif self.chunking_method == 'line':
                return self._chunk_line(text)
            elif self.chunking_method == 'recursive':
                return self._chunk_recursive(text)
            else:
                raise ValueError(
                    f"Unknown chunking method: {self.chunking_method}")
        except Exception as e:
            logger.error(
                f"Chunking failed with method {self.chunking_method}: {e}")
            # Fallback to token chunking
            logger.info("Falling back to token chunking")
            return self._chunk_token(text)

    def _chunk_token(self, text: str) -> List[str]:
        """Token-based chunking (built-in method)"""
        if CHUNKING_METHODS_AVAILABLE:
            return token_chunk(
                text,
                token_count=self.chunking_params.get('token_count', 7000),
                overlap=self.chunking_params.get('overlap', 300),
                encoding_name=self.chunking_params.get(
                    'encoding_name', 'cl100k_base')
            )
        else:
            # Fallback to legacy implementation
            tokens = self.encoding.encode(text)
            chunks = []
            start = 0
            total_tokens = len(tokens)
            max_tokens = self.chunking_params.get(
                'token_count', self.max_tokens)
            overlap = self.chunking_params.get('overlap', self.overlap)

            while start < total_tokens:
                end = min(start + max_tokens, total_tokens)
                chunk_tokens = tokens[start:end]
                chunk_text = self.encoding.decode(chunk_tokens)
                chunks.append(chunk_text)

                if end == total_tokens:
                    break
                start = end - overlap

            return chunks

    def _chunk_semantic(self, text: str) -> List[str]:
        """Semantic chunking using langchain"""
        if not CHUNKING_METHODS_AVAILABLE:
            raise Exception(
                "langchain-experimental not available for semantic chunking")
        return semantic_chunk(
            text,
            embedding_model=self.chunking_params.get(
                'embedding_model', 'text-embedding-3-small'),
            breakpoint_threshold_type=self.chunking_params.get(
                'breakpoint_threshold_type', 'percentile')
        )

    def _chunk_line(self, text: str) -> List[str]:
        """Line-based chunking"""
        if not CHUNKING_METHODS_AVAILABLE:
            raise Exception("chunking_methods not available for line chunking")
        return line_chunk(
            text,
            line_count=self.chunking_params.get('line_count', 100),
            overlap=self.chunking_params.get('overlap', 10)
        )

    def _chunk_recursive(self, text: str) -> List[str]:
        """Recursive character-based chunking using langchain"""
        if not CHUNKING_METHODS_AVAILABLE:
            raise Exception(
                "langchain-experimental not available for recursive chunking")
        return recursive_chunk(
            text,
            chunk_size=self.chunking_params.get('chunk_size', 1000),
            overlap=self.chunking_params.get('overlap', 100)
        )

    @backoff.on_exception(backoff.expo,
                          OpenAIError,
                          max_tries=10,
                          max_time=300,
                          jitter=backoff.full_jitter)
    async def generate_contextual_summary_async(self, doc_content: str, chunk_content: str) -> str:
        """Generate contextual summary for a chunk using OpenAI.

        Adapted from split_and_upload_md.py
        """
        async with self.summary_rate_limiter:
            response = await self.openai_client.chat.completions.create(
                model=self.summary_model,
                messages=[
                    {"role": "system", "content": "You are an expert at summarizing text chunks in the context of a larger document."},
                    {"role": "user", "content": self.document_context_prompt.format(
                        doc_content=doc_content)},
                    {"role": "user", "content": self.chunk_context_prompt.format(
                        chunk_content=chunk_content)}
                ],
                max_tokens=150,
                temperature=0.2
            )
            return response.choices[0].message.content.strip()

    def retrieve_file_bytes(self, document: Documents) -> bytes:
        """Retrieve file bytes from GridFS using the document's gridfs_file_id"""
        try:
            gridfs_file = document.get_gridfs_file(self.fs)
            if not gridfs_file:
                raise Exception(
                    f"Failed to retrieve GridFS file for document {document.id}")

            file_bytes = gridfs_file.read()
            logger.info(
                f"Retrieved {len(file_bytes)} bytes from GridFS for {document.file_name}")
            return file_bytes

        except Exception as e:
            logger.error(
                f"Error retrieving file bytes for document {document.id}: {e}")
            raise

    def parse_document(self, file_bytes: bytes, file_type: str, file_name: str) -> str:
        """Parse document using appropriate parser based on file type"""
        try:
            if file_type not in self.parser_map:
                raise Exception(f"Unsupported file type: {file_type}")

            parser_func = self.parser_map[file_type]
            logger.info(f"Parsing {file_name} using {parser_func.__name__}")

            markdown_content = parser_func(file_bytes)

            if not markdown_content:
                raise Exception(
                    f"Parser returned empty content for {file_name}")

            logger.info(
                f"Successfully parsed {file_name}, got {len(markdown_content)} characters")
            return markdown_content

        except Exception as e:
            logger.error(f"Error parsing {file_name} (type: {file_type}): {e}")
            raise

    async def chunk_and_summarize(self, markdown_content: str, document: Documents) -> List[Dict]:
        """Chunk the markdown content and generate summaries for each chunk"""
        try:
            # Generate chunks using the configured method
            chunks = self.chunk_text(markdown_content)
            logger.info(
                f"Generated {len(chunks)} chunks for document {document.file_name}")

            if not chunks:
                raise Exception(
                    f"No chunks generated for document {document.file_name}")

            chunk_data = []

            # Process chunks in batches to avoid overwhelming the API
            chunk_batch_size = 5  # From split_and_upload_md.py

            # Extract keywords for each chunk
            all_keywords = None
            try:
                all_keywords = self.keyword_extractor.extract_keywords_batch(chunks, max_keywords=10)
                logger.info(f"Extracted {len(all_keywords)} keywords for document {document.file_name}")
            except Exception as e:
                logger.error(f"Error extracting keywords for document {document.file_name}: {e}")
                all_keywords = None

            for batch_start in range(0, len(chunks), chunk_batch_size):
                batch = chunks[batch_start:batch_start + chunk_batch_size]

                # Generate summaries for this batch
                summary_tasks = [
                    self.generate_contextual_summary_async(
                        markdown_content, chunk_text
                    )
                    for chunk_text in batch
                ]

                try:
                    summaries = await asyncio.gather(*summary_tasks, return_exceptions=True)

                    # Process results
                    for idx, (chunk_text, summary) in enumerate(zip(batch, summaries)):
                        chunk_index = batch_start + idx

                        if isinstance(summary, Exception):
                            logger.error(f"Summary generation failed for chunk {chunk_index}: {summary}")
                            summary = f"Summary generation failed: {str(summary)[:100]}..."
                        
                        if all_keywords and chunk_index < len(all_keywords):
                            keywords = all_keywords[chunk_index]
                        else:
                            try:
                                keywords = self.keyword_extractor.extract_keywords(
                                    text=chunk_text,
                                    max_keywords=12,
                                    document_context=markdown_content,
                                    chunk_summary=summary if not isinstance(summary, Exception) else None
                                )
                                logger.info(f"Extracted {len(keywords)} keywords for chunk {chunk_index} resulting in {keywords}")
                            except Exception as kw_error:
                                logger.warning(f"Individual keyword extraction failed for chunk {chunk_index}: {kw_error}")
                                keywords = []

                        chunk_data.append({
                            'chunk_index': chunk_index,
                            'content': chunk_text,
                            'summary': summary,
                            'keywords': keywords,
                            'token_count': self.num_tokens_from_string(chunk_text)
                        })

                        logger.info(
                            f"Processed chunk {chunk_index + 1}/{len(chunks)} for {document.file_name}")

                except Exception as e:
                    logger.error(
                        f"Batch processing failed for chunks {batch_start}-{batch_start + len(batch) - 1}: {e}")
                    # Add chunks without summaries as fallback
                    for idx, chunk_text in enumerate(batch):
                        chunk_index = batch_start + idx
                        chunk_data.append({
                            'chunk_index': chunk_index,
                            'content': chunk_text,
                            'summary': f"Summary generation failed: {str(e)[:100]}...",
                            'keywords': [],
                            'token_count': self.num_tokens_from_string(chunk_text)
                        })

            logger.info(
                f"Completed chunking and summarization for {document.file_name}: {len(chunk_data)} chunks")
            return chunk_data

        except Exception as e:
            logger.error(
                f"Error in chunk_and_summarize for document {document.id}: {e}")
            raise

    def _safe_chunk_save(self, chunk: Chunks):
        """Thread-safe chunk save with rate limiting"""
        with self._db_lock:
            time.sleep(self.rate_limit_delay)
            chunk.save()
            return chunk.id

    def save_chunks_to_db(self, chunks_data: List[Dict], document: Documents) -> int:
        """Save all chunks to MongoDB"""
        try:
            saved_count = 0

            for chunk_info in chunks_data:
                try:
                    chunk = Chunks(
                        document=document,
                        user=document.user,
                        namespace=document.namespace,
                        file_name=document.file_name,
                        chunk_index=chunk_info['chunk_index'],
                        content=chunk_info['content'],
                        summary=chunk_info['summary'],
                        keywords=chunk_info.get('keywords', []),  # Include keywords
                        chunking_method=self.chunking_method,
                        vector_id=None,  # Initially null, populated later by embedding pipeline
                        created_at=datetime.now()
                    )

                    chunk_id = self._safe_chunk_save(chunk)
                    saved_count += 1

                    logger.debug(
                        f"Saved chunk {chunk_info['chunk_index']} for document {document.file_name} "
                        f"(ID: {chunk_id}, Keywords: {len(chunk_info.get('keywords', []))})")

                except Exception as e:
                    logger.error(
                        f"Failed to save chunk {chunk_info['chunk_index']} for document {document.id}: {e}")
                    continue

            logger.info(
                f"Successfully saved {saved_count}/{len(chunks_data)} chunks for document {document.file_name}")
            return saved_count

        except Exception as e:
            logger.error(f"Error saving chunks for document {document.id}: {e}")
            raise

    def _safe_document_status_update(self, document: Documents, status: str, error_message: str = None):
        """Thread-safe document status update"""
        with self._db_lock:
            # Shorter delay for status updates
            time.sleep(self.rate_limit_delay / 2)
            document.status = status
            document.chunking_method = self.chunking_method
            if hasattr(document, 'error_message') and error_message:
                document.error_message = error_message
            document.save()
            return document.id

    async def process_single_document(self, document: Documents) -> Dict:
        """Process a single document: retrieve → parse → chunk → summarize → save"""
        result = {
            'document_id': str(document.id),
            'file_name': document.file_name,
            'file_type': document.file_type,
            'success': False,
            'message': '',
            'chunks_created': 0,
            'processing_time': 0
        }

        start_time = time.time()

        try:
            logger.info(f"\n=== Processing Document: {document.file_name} ===")
            logger.info(f"Document ID: {document.id}")
            logger.info(f"File Type: {document.file_type}")
            logger.info(f"Namespace: {document.namespace}")

            # Step 1: Retrieve file bytes from GridFS
            logger.info("Step 1: Retrieving file from GridFS...")
            file_bytes = self.retrieve_file_bytes(document)

            # Step 2: Parse document to markdown
            logger.info("Step 2: Parsing document...")
            markdown_content = self.parse_document(
                file_bytes, document.file_type, document.file_name)

            # Step 3: Chunk and summarize
            logger.info("Step 3: Chunking and generating summaries...")
            chunks_data = await self.chunk_and_summarize(markdown_content, document)

            # Step 4: Save chunks to database
            logger.info("Step 4: Saving chunks to database...")
            chunks_saved = self.save_chunks_to_db(chunks_data, document)

            # Step 5: Update document status
            logger.info("Step 5: Updating document status...")
            self._safe_document_status_update(document, "processed")

            # Update results
            result['success'] = True
            result['chunks_created'] = chunks_saved
            result['message'] = f"Successfully processed {chunks_saved} chunks"
            result['processing_time'] = time.time() - start_time

            # Update statistics
            self._update_stats('processed')
            self._update_stats('chunks_created', chunks_saved)

            logger.info(
                f"✓ Successfully processed {document.file_name}: {chunks_saved} chunks in {result['processing_time']:.2f}s")

        except Exception as e:
            # Update document status to failed
            try:
                self._safe_document_status_update(document, "failed", str(e))
            except Exception as status_error:
                logger.error(
                    f"Failed to update document status: {status_error}")

            result['message'] = f"Processing failed: {str(e)}"
            result['processing_time'] = time.time() - start_time

            # Update statistics
            self._update_stats('failed')

            logger.error(f"✗ Failed to process {document.file_name}: {str(e)}")

        return result

    def get_pending_documents(self, user: User_Auth_Table, limit: Optional[int] = None) -> List[Documents]:
        """Get all documents with status='pending' for a specific user"""
        try:
            query = Documents.objects(status="pending", user=user)  # ✅ Add user filter
            if limit:
                query = query.limit(limit)
            
            documents = list(query)
            logger.info(f"Found {len(documents)} pending documents for user {user.user_name}")
            return documents
        except Exception as e:
            logger.error(f"Error querying pending documents: {e}")
            raise

    async def process_pending_documents(self, user: User_Auth_Table, limit: Optional[int] = None, use_parallel: bool = True) -> Dict:
        """Process all pending documents with optional parallel processing"""
        logger.info("\n=== Starting Document Processing Pipeline ===")

        # Reset statistics
        with self._stats_lock:
            self._stats = {
                'processed': 0,
                'failed': 0,
                'chunks_created': 0,
                'start_time': time.time()
            }

        try:
            # Get pending documents
            documents = self.get_pending_documents(user=user, limit=limit)

            if not documents:
                logger.info("No pending documents found")
                return {
                    'total_documents': 0,
                    'processed': 0,
                    'failed': 0,
                    'chunks_created': 0,
                    'results': [],
                    'processing_time': 0
                }

            logger.info(f"Processing {len(documents)} pending documents")

            if use_parallel and len(documents) > 1:
                results = await self._process_documents_parallel(documents)
            else:
                results = await self._process_documents_sequential(documents)

            # Calculate final statistics
            with self._stats_lock:
                processing_time = time.time() - self._stats['start_time']
                summary = {
                    'total_documents': len(documents),
                    'processed': self._stats['processed'],
                    'failed': self._stats['failed'],
                    'chunks_created': self._stats['chunks_created'],
                    'results': results,
                    'processing_time': processing_time
                }

            # Log final summary
            logger.info(f"\n=== Processing Complete ===")
            logger.info(f"Total documents: {summary['total_documents']}")
            logger.info(f"Successfully processed: {summary['processed']}")
            logger.info(f"Failed: {summary['failed']}")
            logger.info(f"Total chunks created: {summary['chunks_created']}")
            logger.info(f"Processing time: {processing_time:.2f} seconds")

            if summary['processed'] > 0:
                avg_time = processing_time / len(documents)
                logger.info(
                    f"Average time per document: {avg_time:.2f} seconds")

            return summary

        except Exception as e:
            logger.error(f"Error in process_pending_documents: {e}")
            raise

    async def _process_documents_sequential(self, documents: List[Documents]) -> List[Dict]:
        """Process documents sequentially"""
        logger.info(f"Processing {len(documents)} documents sequentially...")
        results = []

        for i, document in enumerate(documents, 1):
            logger.info(f"\n[{i}/{len(documents)}] Processing document...")
            result = await self.process_single_document(document)
            results.append(result)

        return results

    async def _process_documents_parallel(self, documents: List[Documents]) -> List[Dict]:
        """Process documents in parallel using asyncio"""
        logger.info(
            f"Processing {len(documents)} documents in parallel ({self.max_workers} workers)...")

        # Create semaphore to limit concurrent document processing
        semaphore = asyncio.Semaphore(self.max_workers)

        async def _limited_process(doc: Documents):
            async with semaphore:
                return await self.process_single_document(doc)

        # Process all documents concurrently
        tasks = [_limited_process(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Document {documents[i].file_name} failed with exception: {result}")
                processed_results.append({
                    'document_id': str(documents[i].id),
                    'file_name': documents[i].file_name,
                    'file_type': documents[i].file_type,
                    'success': False,
                    'message': f"Processing exception: {str(result)}",
                    'chunks_created': 0,
                    'processing_time': 0
                })
                self._update_stats('failed')
            else:
                processed_results.append(result)

        return processed_results

    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")


def main():
    """CLI interface for the document processor"""
    print("=== Document Processing Pipeline CLI ===")
    print("This tool processes pending documents: retrieves from GridFS, parses, chunks, and creates summaries.")
    print("Supported file types: PDF, DOCX, TXT, CSV")
    print()

    try:
        # Optional: Ask about processing parameters
        limit_input = input(
            "Limit number of documents to process (default: all): ").strip()
        limit = None
        if limit_input.isdigit():
            limit = int(limit_input)
            print(f"Will process maximum {limit} documents")
        else:
            print("Will process all pending documents")

        # Optional: Ask about parallel processing
        use_parallel = True
        parallel_input = input(
            "Use parallel processing? (Y/n): ").strip().lower()
        if parallel_input in ['n', 'no']:
            use_parallel = False
            print("Will use sequential processing")
        else:
            print("Will use parallel processing (4 workers)")

        # Optional: Custom worker count for advanced users
        max_workers = 4
        if use_parallel:
            workers_input = input(
                "Number of workers (2-5, default 4): ").strip()
            if workers_input.isdigit():
                max_workers = max(2, min(5, int(workers_input)))
                print(f"Using {max_workers} workers")

        # Initialize processor
        print("\nInitializing document processor...")
        processor = DocumentProcessor(max_workers=max_workers)

        # Process documents
        async def run_processing():
            return await processor.process_pending_documents(user=processor.user, limit=limit, use_parallel=use_parallel)

        results = asyncio.run(run_processing())

        # Show detailed results if any documents were processed
        if results['results']:
            print(f"\n=== Detailed Results ===")
            for result in results['results']:
                status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
                print(f"{status}: {result['file_name']} - {result['message']}")
                if result['success']:
                    print(f"  Chunks created: {result['chunks_created']}")
                    print(
                        f"  Processing time: {result['processing_time']:.2f}s")

        # Performance summary
        if results.get('processing_time', 0) > 0:
            print(f"\n=== Performance Summary ===")
            print(
                f"Total processing time: {results['processing_time']:.2f} seconds")
            if results['total_documents'] > 0:
                avg_time = results['processing_time'] / \
                    results['total_documents']
                print(f"Average time per document: {avg_time:.2f} seconds")
                throughput = results['total_documents'] / \
                    results['processing_time'] * 60
                print(f"Throughput: {throughput:.1f} documents per minute")
                if results['chunks_created'] > 0:
                    chunk_throughput = results['chunks_created'] / \
                        results['processing_time'] * 60
                    print(
                        f"Chunk throughput: {chunk_throughput:.1f} chunks per minute")

        # Close processor
        processor.close()

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        logger.exception("Full error traceback:")

    print("\nDocument processing pipeline finished.")


if __name__ == "__main__":
    main()
