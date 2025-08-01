#!/usr/bin/env python3
"""
Master Document Processing Pipeline for RAG Chatbot
Combines document upload and processing into one seamless workflow:
1. Upload documents from local directory to GridFS
2. Parse documents using appropriate parsers
3. Chunk the content with one of the following methods: token, semantic, line, recursive
4. Generate AI summaries for each chunk
5. Store everything in MongoDB ready for embedding
"""

import os
import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Import both pipeline components
from document_pipeline import DocumentPipeline
from document_processor import DocumentProcessor
from embeddings import EmbeddingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class MasterPipeline:
    """Master pipeline that combines document upload and processing"""

    def __init__(self, max_workers: int = 4, rate_limit_delay: float = 0.2,
                 chunking_method: str = "token", chunking_params: dict = None, user=None):
        """Initialize both upload and processing pipelines

        Args:
            max_workers: Maximum number of parallel workers (default: 4)
            rate_limit_delay: Delay between database operations in seconds (default: 0.2)
            chunking_method: Chunking method to use ('token', 'semantic', 'line', 'recursive') (default: 'token')
            chunking_params: Parameters for the chunking method (default: None, uses method defaults)
            user: User object to use for processing (optional)
        """
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        self.chunking_method = chunking_method
        self.chunking_params = chunking_params or {}

        # Initialize all pipelines
        logger.info("Initializing master pipeline...")
        logger.info(
            f"Chunking method: {chunking_method} with params: {self.chunking_params}")

        try:
            # Upload pipeline (document_pipeline.py)
            self.upload_pipeline = DocumentPipeline(
                max_workers=max_workers,
                rate_limit_delay=rate_limit_delay,
                user=user
            )
            logger.info("✓ Document upload pipeline initialized")

            # Processing pipeline (document_processor.py)
            self.processing_pipeline = DocumentProcessor(
                max_workers=max_workers,
                rate_limit_delay=rate_limit_delay,
                chunking_method=chunking_method,
                chunking_params=chunking_params
            )
            logger.info("✓ Document processing pipeline initialized")

            # Embedding pipeline (embeddings.py)
            self.embedding_service = EmbeddingService()
            logger.info("✓ Embedding service initialized")

            logger.info("🚀 Master pipeline ready!")

        except Exception as e:
            logger.error(f"Failed to initialize master pipeline: {e}")
            raise

    async def process_directory_complete(self, directory_path: str, namespace: str,
                                       use_parallel_upload: bool = True,
                                       use_parallel_processing: bool = True) -> Dict:
        """Complete processing workflow: upload → process → chunk → summarize

        Args:
            directory_path: Path to directory containing documents
            namespace: Namespace for organizing documents
            use_parallel_upload: Use parallel processing for uploads
            use_parallel_processing: Use parallel processing for document processing

        Returns:
            Dict with complete workflow statistics
        """
        workflow_start_time = time.time()

        logger.info("=" * 80)
        logger.info("🚀 STARTING MASTER DOCUMENT PROCESSING WORKFLOW")
        logger.info("=" * 80)
        logger.info(f"📁 Source Directory: {directory_path}")
        logger.info(f"🏷️  Namespace: {namespace}")
        logger.info(f"⚡ Upload Parallel: {use_parallel_upload}")
        logger.info(f"⚡ Processing Parallel: {use_parallel_processing}")
        logger.info(f"👥 Max Workers: {self.max_workers}")

        try:
            # PHASE 1: Upload documents to GridFS
            logger.info("\n" + "=" * 60)
            logger.info("📤 PHASE 1: UPLOADING DOCUMENTS TO GRIDFS")
            logger.info("=" * 60)

            upload_results = self.upload_pipeline.process_directory(
                directory_path=directory_path,
                namespace=namespace,
                use_parallel=use_parallel_upload
            )

            # Log upload summary
            logger.info(f"\n✅ Upload Phase Complete:")
            logger.info(
                f"   📊 Total files found: {upload_results['total_files']}")
            logger.info(
                f"   ✅ Successfully uploaded: {upload_results['processed']}")
            logger.info(
                f"   ⚠️  Skipped (duplicates): {upload_results['skipped']}")
            logger.info(f"   ❌ Failed: {upload_results['failed']}")
            logger.info(
                f"   ⏱️  Upload time: {upload_results['processing_time']:.2f}s")

            # Check if we have any uploaded documents to process
            if upload_results['processed'] == 0:
                logger.warning(
                    "⚠️  No new documents were uploaded. Checking for existing pending documents...")

                # Check for existing pending documents
                pending_docs = self.processing_pipeline.get_pending_documents()
                if not pending_docs:
                    logger.info(
                        "ℹ️  No pending documents found. Workflow complete.")
                    return {
                        'workflow_success': True,
                        'upload_results': upload_results,
                        'processing_results': {
                            'total_documents': 0,
                            'processed': 0,
                            'failed': 0,
                            'chunks_created': 0,
                            'results': [],
                            'processing_time': 0
                        },
                        'total_workflow_time': time.time() - workflow_start_time,
                        'message': 'No new documents to process'
                    }
                else:
                    logger.info(
                        f"📋 Found {len(pending_docs)} existing pending documents to process")

            # PHASE 2: Process documents (parse, chunk, summarize)
            logger.info("\n" + "=" * 60)
            logger.info("🔄 PHASE 2: PROCESSING DOCUMENTS")
            logger.info("=" * 60)
            logger.info("🔍 Parsing documents...")
            logger.info(
                f"✂️  Chunking content using {self.chunking_method} method...")
            logger.info("🤖 Generating AI summaries...")
            logger.info("💾 Saving to database...")

            # Run document processing asynchronously
            async def run_processing():
                return await self.processing_pipeline.process_pending_documents(
                    limit=None,  # Process all pending documents
                    use_parallel=use_parallel_processing
                )

            processing_results = await run_processing()

            # Log processing summary
            logger.info(f"\n✅ Processing Phase Complete:")
            logger.info(
                f"   📊 Total documents processed: {processing_results['total_documents']}")
            logger.info(
                f"   ✅ Successfully processed: {processing_results['processed']}")
            logger.info(f"   ❌ Failed: {processing_results['failed']}")
            logger.info(
                f"   📝 Total chunks created: {processing_results['chunks_created']}")
            logger.info(
                f"   ⏱️  Processing time: {processing_results['processing_time']:.2f}s")

            # Calculate final workflow statistics
            total_workflow_time = time.time() - workflow_start_time

            # Determine overall success
            workflow_success = (
                upload_results['failed'] == 0 and
                processing_results['failed'] == 0 and
                (upload_results['processed'] >
                 0 or processing_results['processed'] > 0)
            )

            # FINAL SUMMARY
            logger.info("\n" + "=" * 80)
            logger.info("🏁 MASTER WORKFLOW COMPLETE")
            logger.info("=" * 80)
            logger.info(
                f"✅ Workflow Status: {'SUCCESS' if workflow_success else 'PARTIAL SUCCESS'}")
            logger.info(f"📁 Directory: {directory_path}")
            logger.info(f"🏷️  Namespace: {namespace}")
            logger.info("")
            logger.info("📤 UPLOAD PHASE:")
            logger.info(f"   📊 Files found: {upload_results['total_files']}")
            logger.info(f"   ✅ Uploaded: {upload_results['processed']}")
            logger.info(f"   ⚠️  Skipped: {upload_results['skipped']}")
            logger.info(f"   ❌ Failed: {upload_results['failed']}")
            logger.info("")
            logger.info("🔄 PROCESSING PHASE:")
            logger.info(
                f"   📊 Documents processed: {processing_results['total_documents']}")
            logger.info(f"   ✅ Successful: {processing_results['processed']}")
            logger.info(f"   ❌ Failed: {processing_results['failed']}")
            logger.info(
                f"   📝 Chunks created: {processing_results['chunks_created']}")
            logger.info("")
            logger.info("⏱️  TIMING:")
            logger.info(
                f"   📤 Upload time: {upload_results['processing_time']:.2f}s")
            logger.info(
                f"   🔄 Processing time: {processing_results['processing_time']:.2f}s")
            logger.info(
                f"   🏁 Total workflow time: {total_workflow_time:.2f}s")

            if processing_results['chunks_created'] > 0:
                throughput = processing_results['chunks_created'] / \
                    total_workflow_time * 60
                logger.info(
                    f"   📈 Chunk throughput: {throughput:.1f} chunks/minute")

            logger.info("=" * 80)

            return {
                'workflow_success': workflow_success,
                'upload_results': upload_results,
                'processing_results': processing_results,
                'total_workflow_time': total_workflow_time,
                'message': 'Workflow completed successfully' if workflow_success else 'Workflow completed with some issues'
            }

        except Exception as e:
            logger.error(f"❌ Master workflow failed: {e}")
            return {
                'workflow_success': False,
                'upload_results': None,
                'processing_results': None,
                'total_workflow_time': time.time() - workflow_start_time,
                'message': f'Workflow failed: {str(e)}'
            }

    async def process_directory_complete_with_embeddings(self, directory_path: str, namespace: str,
                                                         user_id: str = None,
                                                         embedding_model: str = "text-embedding-3-small",
                                                         use_parallel_upload: bool = True,
                                                         use_parallel_processing: bool = True) -> Dict:
        """Complete workflow: upload → process → chunk → summarize → embed → store in Pinecone

        Args:
            directory_path: Path to directory containing documents
            namespace: Namespace for organizing documents
            user_id: User ID for embedding processing (if None, will use default)
            embedding_model: Embedding model to use ('text-embedding-3-small' or 'gemini-embedding-001')
            use_parallel_upload: Use parallel processing for uploads
            use_parallel_processing: Use parallel processing for document processing

        Returns:
            Dict with complete workflow statistics including embeddings
        """
        # Auto-determine Pinecone index based on embedding model
        if "gemini" in embedding_model.lower():
            pinecone_index = "chatbot-vectors-google"
        else:
            # Default to OpenAI index for all OpenAI models
            pinecone_index = "chatbot-vectors-openai"
        
        workflow_start_time = time.time()

        logger.info("=" * 80)
        logger.info("🚀 STARTING COMPLETE DOCUMENT + EMBEDDING WORKFLOW")
        logger.info("=" * 80)
        logger.info(f"📁 Source Directory: {directory_path}")
        logger.info(f"🏷️  Namespace: {namespace}")
        logger.info(f"🤖 Embedding Model: {embedding_model}")
        logger.info(f"📊 Pinecone Index: {pinecone_index} (auto-selected)")
        logger.info(f"⚡ Upload Parallel: {use_parallel_upload}")
        logger.info(f"⚡ Processing Parallel: {use_parallel_processing}")
        logger.info(f"👥 Max Workers: {self.max_workers}")

        # First run the standard document processing workflow
        processing_results = await self.process_directory_complete(
            directory_path=directory_path,
            namespace=namespace,
            use_parallel_upload=use_parallel_upload,
            use_parallel_processing=use_parallel_processing
        )

        # Check if document processing was successful
        if not processing_results['workflow_success']:
            logger.error(
                "❌ Document processing failed, skipping embedding phase")
            return {
                **processing_results,
                'embedding_results': None,
                'complete_workflow_success': False,
                'message': 'Document processing failed, embedding skipped'
            }

        # PHASE 3: EMBEDDING PHASE
        logger.info("\n" + "=" * 60)
        logger.info("🧠 PHASE 3: EMBEDDING PROCESSING")
        logger.info("=" * 60)
        logger.info("🔍 Finding unembedded chunks...")
        logger.info(f"🤖 Creating embeddings using {embedding_model}...")
        logger.info(
            f"📊 Storing vectors in Pinecone index '{pinecone_index}'...")
        logger.info("💾 Updating MongoDB with vector IDs...")

        embedding_results = None
        try:
            # Use provided user_id or get from upload pipeline to ensure consistency
            if not user_id:
                # Get the user ID from the upload pipeline to ensure consistency
                upload_pipeline_user_id = str(self.upload_pipeline.user.id)
                user_id = upload_pipeline_user_id
                logger.info(
                    f"No user_id provided, using upload pipeline user: {user_id} ({self.upload_pipeline.user.user_name})")
            else:
                logger.info(f"👤 Using provided user_id: {user_id}")

            logger.info(f"👤 Processing embeddings for user: {user_id}")

            # Run embedding processing
            embedding_results = self.embedding_service.process_user_embeddings_by_namespace(
                user_id=user_id,
                embedding_model=embedding_model,
                pinecone_index=pinecone_index,
                batch_size=50
            )

            # Log embedding summary
            if embedding_results and embedding_results['success']:
                logger.info(f"\n✅ Embedding Phase Complete:")
                logger.info(
                    f"   📋 Total chunks found: {embedding_results['total_chunks_found']}")
                logger.info(
                    f"   🤖 Chunks embedded: {embedding_results['total_chunks_embedded']}")
                logger.info(
                    f"   💾 Chunks updated: {embedding_results['total_chunks_updated']}")
                logger.info(
                    f"   🏷️  Namespaces processed: {embedding_results['namespaces_processed']}")
                logger.info(
                    f"   ⏱️  Embedding time: {embedding_results['processing_time']:.2f}s")
            else:
                logger.warning("⚠️  Embedding phase completed with issues")

        except Exception as e:
            logger.error(f"❌ Embedding phase failed: {e}")
            embedding_results = {
                'success': False,
                'error': str(e),
                'message': f'Embedding processing failed: {str(e)}'
            }

        # Calculate final workflow statistics
        total_workflow_time = time.time() - workflow_start_time

        # Determine overall success
        complete_workflow_success = (
            processing_results['workflow_success'] and
            embedding_results and
            embedding_results.get('success', False)
        )

        # FINAL SUMMARY
        logger.info("\n" + "=" * 80)
        logger.info("🏁 COMPLETE WORKFLOW FINISHED")
        logger.info("=" * 80)
        logger.info(
            f"✅ Workflow Status: {'SUCCESS' if complete_workflow_success else 'PARTIAL SUCCESS'}")
        logger.info(f"📁 Directory: {directory_path}")
        logger.info(f"🏷️  Namespace: {namespace}")
        logger.info(f"🤖 Embedding Model: {embedding_model}")
        logger.info("")

        # Document processing summary
        logger.info("📤 DOCUMENT PROCESSING:")
        if processing_results.get('upload_results'):
            ur = processing_results['upload_results']
            logger.info(f"   📊 Files found: {ur['total_files']}")
            logger.info(f"   ✅ Uploaded: {ur['processed']}")
            logger.info(f"   ⚠️  Skipped: {ur['skipped']}")
            logger.info(f"   ❌ Failed: {ur['failed']}")

        if processing_results.get('processing_results'):
            pr = processing_results['processing_results']
            logger.info(f"   📊 Documents processed: {pr['total_documents']}")
            logger.info(f"   ✅ Successful: {pr['processed']}")
            logger.info(f"   ❌ Failed: {pr['failed']}")
            logger.info(f"   📝 Chunks created: {pr['chunks_created']}")

        # Embedding summary
        logger.info("")
        logger.info("🧠 EMBEDDING PROCESSING:")
        if embedding_results:
            logger.info(
                f"   📋 Chunks found: {embedding_results.get('total_chunks_found', 0)}")
            logger.info(
                f"   🤖 Chunks embedded: {embedding_results.get('total_chunks_embedded', 0)}")
            logger.info(
                f"   💾 Chunks updated: {embedding_results.get('total_chunks_updated', 0)}")
            logger.info(
                f"   🏷️  Namespaces processed: {embedding_results.get('namespaces_processed', 0)}")
        else:
            logger.info("   ❌ Embedding processing skipped or failed")

        # Timing summary
        logger.info("")
        logger.info("⏱️  TIMING:")
        logger.info(
            f"   📤 Document processing: {processing_results.get('total_workflow_time', 0):.2f}s")
        if embedding_results:
            logger.info(
                f"   🧠 Embedding processing: {embedding_results.get('processing_time', 0):.2f}s")
        logger.info(f"   🏁 Total workflow time: {total_workflow_time:.2f}s")

        # Performance metrics
        if embedding_results and embedding_results.get('total_chunks_embedded', 0) > 0:
            embedding_throughput = embedding_results['total_chunks_embedded'] / \
                embedding_results.get('processing_time', 1) * 60
            logger.info(
                f"   📈 Embedding throughput: {embedding_throughput:.1f} embeddings/minute")

        logger.info("=" * 80)

        return {
            **processing_results,
            'embedding_results': embedding_results,
            'complete_workflow_success': complete_workflow_success,
            'total_complete_workflow_time': total_workflow_time,
            'message': 'Complete workflow finished successfully' if complete_workflow_success else 'Workflow completed with some issues'
        }

    def close(self):
        """Close all pipeline connections"""
        try:
            if hasattr(self, 'upload_pipeline'):
                self.upload_pipeline.close()
                logger.info("✓ Upload pipeline closed")

            if hasattr(self, 'processing_pipeline'):
                self.processing_pipeline.close()
                logger.info("✓ Processing pipeline closed")

            logger.info("🔒 Master pipeline closed")

        except Exception as e:
            logger.error(f"Error closing master pipeline: {e}")


def main():
    """CLI interface for the master document processing pipeline"""
    print("=" * 80)
    print("🚀 COMPLETE RAG PIPELINE - DOCUMENTS TO VECTOR SEARCH")
    print("=" * 80)
    print("This tool provides the complete RAG pipeline workflow:")
    print("• 📤 Upload documents to GridFS")
    print("• 🔍 Parse documents (PDF, DOCX, TXT, CSV)")
    print("• ✂️  Chunk content with multiple methods (token, semantic, line, recursive)")
    print("• 🤖 Generate AI summaries for each chunk")
    print("• 💾 Store chunks in MongoDB")
    print("• 🧠 Create embeddings (OpenAI or Gemini)")
    print("• 📊 Store vectors in Pinecone with namespacing")
    print("• 🔗 Link MongoDB chunks to Pinecone vectors")
    print("=" * 80)
    print()

    try:
        # Get user input for directory path
        while True:
            folder_path = input(
                "📁 Enter the folder path containing documents: ").strip()
            if folder_path:
                # Handle quotes if user includes them
                folder_path = folder_path.strip('"\'')
                if os.path.exists(folder_path):
                    file_count = len([f for f in Path(folder_path).iterdir()
                                      if f.is_file() and f.suffix.lower() in {'.pdf', '.docx', '.txt', '.csv'}])
                    print(
                        f"✅ Found {file_count} supported files in {folder_path}")
                    break
                else:
                    print(
                        f"❌ Error: Folder '{folder_path}' does not exist. Please try again.")
            else:
                print("⚠️  Please enter a valid folder path.")

        # Get namespace
        while True:
            namespace = input(
                "🏷️  Enter the namespace (e.g., 'company_docs', 'user_manuals'): ").strip()
            if namespace:
                break
            else:
                print("⚠️  Please enter a valid namespace.")

        # Chunking method selection
        print("\n✂️  Chunking Method:")
        print("1. Token-based (default) - Split by token count, good for general use")
        print("2. Semantic - Split by meaning, requires OpenAI embeddings")
        print("3. Line-based - Split by line count, good for structured text")
        print("4. Recursive - Character-based recursive splitting")

        chunking_method = "token"  # default
        method_input = input(
            "Select chunking method (1-4, default 1): ").strip()

        method_map = {
            "1": "token",
            "2": "semantic",
            "3": "line",
            "4": "recursive"
        }

        if method_input in method_map:
            chunking_method = method_map[method_input]
        elif method_input == "":
            chunking_method = "token"
        else:
            print("⚠️  Invalid selection, using token-based chunking")
            chunking_method = "token"

        print(f"✅ Selected: {chunking_method} chunking")

        # Embedding model selection
        print("\n🤖 Embedding Model:")
        print("1. OpenAI (text-embedding-3-small) - High quality, requires OpenAI API key")
        print("2. Gemini (gemini-embedding-001) - Google's model, requires Google API key")

        embedding_model = "text-embedding-3-small"  # default
        embedding_input = input(
            "Select embedding model (1-2, default 1): ").strip()

        if embedding_input == "1" or embedding_input == "":
            embedding_model = "text-embedding-3-small"
            print("✅ Selected: OpenAI text-embedding-3-small")
        elif embedding_input == "2":
            embedding_model = "gemini-embedding-001"
            print("✅ Selected: Gemini embedding-001")
        else:
            print("⚠️  Invalid selection, using OpenAI text-embedding-3-small")
            embedding_model = "text-embedding-3-small"

        # Auto-determine Pinecone index based on embedding model
        if "gemini" in embedding_model.lower():
            pinecone_index = "chatbot-vectors-google"
        else:
            pinecone_index = "chatbot-vectors-openai"
        print(f"✅ Pinecone Index (auto-selected): {pinecone_index}")

        # Processing options
        print("\n⚙️  Processing Options:")

        # Parallel processing for upload
        use_parallel_upload = True
        upload_parallel_input = input(
            "📤 Use parallel processing for uploads? (Y/n): ").strip().lower()
        if upload_parallel_input in ['n', 'no']:
            use_parallel_upload = False

        # Parallel processing for document processing
        use_parallel_processing = True
        processing_parallel_input = input(
            "🔄 Use parallel processing for document processing? (Y/n): ").strip().lower()
        if processing_parallel_input in ['n', 'no']:
            use_parallel_processing = False

        # Worker count
        max_workers = 4
        workers_input = input("👥 Number of workers (2-5, default 4): ").strip()
        if workers_input.isdigit():
            max_workers = max(2, min(5, int(workers_input)))

        print(f"\n🔧 Configuration:")
        print(f"   📁 Directory: {folder_path}")
        print(f"   🏷️  Namespace: {namespace}")
        print(f"   ✂️  Chunking: {chunking_method}")
        print(f"   🤖 Embedding Model: {embedding_model}")
        print(f"   📊 Pinecone Index: {pinecone_index} (auto-selected)")
        print(f"   📤 Upload parallel: {use_parallel_upload}")
        print(f"   🔄 Processing parallel: {use_parallel_processing}")
        print(f"   👥 Workers: {max_workers}")

        # Confirmation
        confirm = input("\n🚀 Start processing? (Y/n): ").strip().lower()
        if confirm in ['n', 'no']:
            print("❌ Operation cancelled by user.")
            return

        # Initialize master pipeline
        print("\n⚙️  Initializing master pipeline...")
        master_pipeline = MasterPipeline(
            max_workers=max_workers,
            chunking_method=chunking_method
        )

        # Run complete workflow with embeddings (user_id will be auto-determined from upload pipeline)
        results = asyncio.run(master_pipeline.process_directory_complete_with_embeddings(
            directory_path=folder_path,
            namespace=namespace,
            user_id=None,  # Will auto-use the same user from upload pipeline
            embedding_model=embedding_model,
            use_parallel_upload=use_parallel_upload,
            use_parallel_processing=use_parallel_processing
        ))

        # Show detailed results
        if results.get('complete_workflow_success'):
            print(f"\n🎉 SUCCESS! Complete workflow finished successfully!")
        else:
            print(f"\n⚠️  PARTIAL SUCCESS: {results['message']}")

        # Performance summary
        print(f"\n📊 FINAL SUMMARY:")
        if results.get('upload_results'):
            ur = results['upload_results']
            print(
                f"   📤 Upload: {ur['processed']} processed, {ur['skipped']} skipped, {ur['failed']} failed")

        if results.get('processing_results'):
            pr = results['processing_results']
            print(
                f"   🔄 Processing: {pr['processed']} processed, {pr['failed']} failed")
            print(f"   📝 Chunks: {pr['chunks_created']} total chunks created")

        if results.get('embedding_results'):
            er = results['embedding_results']
            print(
                f"   🤖 Embedding: {er.get('total_chunks_embedded', 0)} chunks embedded")
            print(
                f"   💾 Updated: {er.get('total_chunks_updated', 0)} chunks updated in MongoDB")
            print(
                f"   🏷️  Namespaces: {er.get('namespaces_processed', 0)} processed")

        print(
            f"   ⏱️  Total time: {results.get('total_complete_workflow_time', results.get('total_workflow_time', 0)):.2f} seconds")

        # Close pipeline
        master_pipeline.close()

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Full error traceback:")

    print("\n🏁 Master pipeline finished.")


if __name__ == "__main__":
    main()
