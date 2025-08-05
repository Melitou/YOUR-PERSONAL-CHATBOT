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
                 chunking_method: str = "token", chunking_params: dict = None):
        """Initialize both upload and processing pipelines

        Args:
            max_workers: Maximum number of parallel workers (default: 4)
            rate_limit_delay: Delay between database operations in seconds (default: 0.2)
            chunking_method: Chunking method to use ('token', 'semantic', 'line', 'recursive') (default: 'token')
            chunking_params: Parameters for the chunking method (default: None, uses method defaults)
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
                rate_limit_delay=rate_limit_delay
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

    def process_directory_complete(self, directory_path: str, namespace: str,
                                   use_parallel_upload: bool = True,
                                   use_parallel_processing: bool = True) -> Dict:
        """Complete processing workflow: upload → process → chunk → summarize

        Args:
            directory_path: Path to directory containing documents
            namespace: Unique namespace (already concatenated with user ID)
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

            processing_results = asyncio.run(run_processing())

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

    def process_directory_complete_with_embeddings(self, directory_path: str, namespace: str,
                                                   user_id: str = None,
                                                   embedding_model: str = "text-embedding-3-small",
                                                   use_parallel_upload: bool = True,
                                                   use_parallel_processing: bool = True) -> Dict:
        """Complete workflow: upload → process → chunk → summarize → embed → store in Pinecone

        Args:
            directory_path: Path to directory containing documents
            namespace: Unique namespace (already concatenated with user ID)
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
        processing_results = self.process_directory_complete(
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


def handle_existing_chatbot_scenario(analysis: Dict, master_pipeline) -> str:
    """Handle the scenario when an existing chatbot is detected

    Args:
        analysis: Analysis results from analyze_directory_for_existing_chatbots()
        master_pipeline: MasterPipeline instance for accessing user info

    Returns:
        User choice: 'use_existing', 'create_new', 'overwrite', 'cancel', 'add_files'
    """
    print(analysis['formatted_summary'])

    # Determine available options based on scenario
    scenario = analysis.get('scenario', 'unknown')

    if scenario == 'identical_files':
        print("\n🤔 What would you like to do?")
        print("1. 💬 Start chatting with existing chatbot")
        print("2. 🆕 Create new chatbot with timestamp suffix")
        print("3. 🗑️  Replace existing chatbot completely")
        print("4. ❌ Cancel operation")

        valid_choices = ['1', '2', '3', '4']
        choice_map = {
            '1': 'use_existing',
            '2': 'create_new',
            '3': 'overwrite',
            '4': 'cancel'
        }

    elif scenario == 'partial_overlap':
        print(
            f"\n🤔 Files partially overlap ({analysis['overlap_percentage']:.1f}%). What would you like to do?")
        print("1. 📁 Add new files to existing chatbot")
        print("2. 🆕 Create new chatbot with all files")
        print("3. 🗑️  Replace existing chatbot completely")
        print("4. ❌ Cancel operation")

        valid_choices = ['1', '2', '3', '4']
        choice_map = {
            '1': 'add_files',
            '2': 'create_new',
            '3': 'overwrite',
            '4': 'cancel'
        }

    elif scenario == 'different_files':
        print(f"\n🤔 Namespace exists but with different files. What would you like to do?")
        print("1. 📁 Add files to existing chatbot")
        print("2. 🗑️  Replace existing chatbot completely")
        print("3. 🆕 Create new chatbot with timestamp suffix")
        print("4. ❌ Cancel operation")

        valid_choices = ['1', '2', '3', '4']
        choice_map = {
            '1': 'add_files',
            '2': 'overwrite',
            '3': 'create_new',
            '4': 'cancel'
        }

    else:
        # Fallback for unknown scenarios
        print("\n🤔 What would you like to do?")
        print("1. 💬 Use existing chatbot")
        print("2. 🆕 Create new chatbot")
        print("3. ❌ Cancel operation")

        valid_choices = ['1', '2', '3']
        choice_map = {
            '1': 'use_existing',
            '2': 'create_new',
            '3': 'cancel'
        }

    # Get user choice with validation
    while True:
        try:
            choice = input(
                f"\nChoose option (1-{len(valid_choices)}): ").strip()
            if choice in valid_choices:
                selected_action = choice_map[choice]

                # Confirm risky actions
                if selected_action == 'overwrite':
                    confirm = input(
                        "⚠️  This will delete all existing data. Are you sure? (y/N): ").strip().lower()
                    if confirm not in ['y', 'yes']:
                        print("Operation cancelled.")
                        continue

                print(f"✅ Selected: {selected_action}")
                return selected_action
            else:
                print(
                    f"⚠️  Please enter a number between 1 and {len(valid_choices)}.")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user.")
            return 'cancel'
        except Exception as e:
            print(f"❌ Error getting user input: {e}")
            return 'cancel'


def handle_files_in_other_namespaces(analysis: Dict) -> str:
    """Handle scenario when files exist in other namespaces

    Args:
        analysis: Analysis results containing files_in_other_namespaces

    Returns:
        User choice: 'continue', 'cancel'
    """
    print("\n📋 FILES FOUND IN OTHER CHATBOTS:")

    # Group by namespace for cleaner display
    namespace_groups = {}
    for file_info in analysis['files_in_other_namespaces']:
        ns_name = file_info['existing_namespace_name']
        if ns_name not in namespace_groups:
            namespace_groups[ns_name] = []
        namespace_groups[ns_name].append(file_info['filename'])

    for ns_name, files in namespace_groups.items():
        print(f"\n🏷️  Chatbot: \"{ns_name}\"")
        for filename in files:
            print(f"   📄 {filename}")

    print(
        f"\n💡 These files already exist in {len(namespace_groups)} other chatbot(s).")
    print("You can still create a new chatbot with the same files in your new namespace.")

    print("\n🤔 What would you like to do?")
    print("1. ✅ Continue with new chatbot creation")
    print("2. ❌ Cancel operation")

    while True:
        try:
            choice = input("Choose option (1-2): ").strip()
            if choice == '1':
                print("✅ Continuing with new chatbot creation...")
                return 'continue'
            elif choice == '2':
                print("❌ Operation cancelled.")
                return 'cancel'
            else:
                print("⚠️  Please enter 1 or 2.")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user.")
            return 'cancel'
        except Exception as e:
            print(f"❌ Error getting user input: {e}")
            return 'cancel'


def create_timestamped_namespace(base_namespace: str) -> str:
    """Create a namespace with timestamp suffix

    Args:
        base_namespace: The base namespace name

    Returns:
        Namespace with timestamp suffix
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_namespace}_{timestamp}"


def start_existing_chatbot(analysis: Dict, master_pipeline, embedding_model: str, chatbot_model: str):
    """Start chat with existing chatbot

    Args:
        analysis: Analysis results
        master_pipeline: MasterPipeline instance
        embedding_model: Embedding model used
        chatbot_model: Chatbot model to use
    """
    print("\n" + "=" * 80)
    print("🤖 STARTING EXISTING CHATBOT...")
    print("=" * 80)

    # Get user ID and namespace info
    user_id = str(master_pipeline.upload_pipeline.user.id)
    user_namespace = analysis['user_namespace']

    print(f"👤 User ID: {user_id}")
    print(f"🏷️  Namespace: {user_namespace}")
    print(f"🤖 Using existing chatbot data...")

    # Import and start the RAG chatbot
    from LLM.rag_llm_call import start_rag_chat_session

    # Start the interactive chat session
    start_rag_chat_session(
        user_id=user_id,
        namespace=user_namespace,
        embedding_model=embedding_model,
        chatbot_model=chatbot_model
    )


def main():
    """Complete CLI interface: Document Processing + RAG Chatbot"""
    print("=" * 80)
    print("🚀 COMPLETE RAG CHATBOT PIPELINE")
    print("=" * 80)
    print("Complete workflow: Documents → Processing → Embeddings → Chat")
    print("• 📤 Upload and process your documents")
    print("• 🧠 Create embeddings and store in vector database")
    print("• 🤖 Start chatting with your personal document assistant")
    print("=" * 80)
    print()

    try:
        # STEP 1: Get folder path
        while True:
            folder_path = input(
                "📁 Enter folder path containing documents: ").strip()
            if folder_path:
                folder_path = folder_path.strip('"\'')
                if os.path.exists(folder_path):
                    file_count = len([f for f in Path(folder_path).iterdir()
                                      if f.is_file() and f.suffix.lower() in {'.pdf', '.docx', '.txt', '.csv'}])
                    print(
                        f"✅ Found {file_count} supported files in {folder_path}")
                    break
                else:
                    print(
                        f"❌ Folder '{folder_path}' does not exist. Please try again.")
            else:
                print("⚠️  Please enter a valid folder path.")

        # STEP 2: Get namespace
        while True:
            namespace = input(
                "🏷️  Enter namespace (e.g., 'my_documents', 'company_data'): ").strip()
            if namespace:
                # Comprehensive validation with immediate feedback
                if not namespace.strip():
                    print("⚠️  Namespace cannot be empty. Please try again.")
                    continue
                if ' ' in namespace:
                    print("⚠️  Namespace cannot contain spaces. Please try again.")
                    continue
                if '|' in namespace:
                    print(
                        "⚠️  Namespace cannot contain pipe character (reserved for user ID separation). Please try again.")
                    continue
                if len(namespace) > 50:
                    print(
                        "⚠️  Namespace too long (max 50 characters). Please try again.")
                    continue

                # All validation passed
                print(f"✅ Namespace '{namespace}' is valid.")
                break
            else:
                print("⚠️  Please enter a valid namespace.")

        # STEP 3: Get embedding model
        print("\n🤖 Select embedding provider:")
        print("1. OpenAI (text-embedding-3-small)")
        print("2. Gemini (gemini-embedding-001)")

        while True:
            choice = input("Choose provider (1 or 2): ").strip()
            if choice == "1":
                embedding_model = "text-embedding-3-small"
                print("✅ Selected: OpenAI")
                break
            elif choice == "2":
                embedding_model = "gemini-embedding-001"
                print("✅ Selected: Gemini")
                break
            else:
                print("⚠️  Please enter 1 or 2.")

        # STEP 4: Get chatbot model
        print("\n🤖 Select chatbot model:")
        print("Choose which AI model will power your personal document assistant:")
        print()
        print("📘 OpenAI Models:")
        openai_models = [
            ("gpt-4.1", "GPT-4.1 - Latest flagship model (recommended)"),
            ("gpt-4o", "GPT-4o - Optimized for general use"),
            ("gpt-4o-mini", "GPT-4o Mini - Fast and efficient"),
            ("gpt-o3", "GPT-o3 - Advanced reasoning model")
        ]

        print("🟢 Gemini Models:")
        gemini_models = [
            ("gemini-2.5-pro", "Gemini 2.5 Pro - Latest flagship model"),
            ("gemini-2.5-flash", "Gemini 2.5 Flash - Fast and efficient"),
            ("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite - Lightweight"),
            ("gemini-2.0-flash", "Gemini 2.0 Flash - Reliable performance"),
            ("gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite - Quick responses"),
            ("gemini-1.5-pro", "Gemini 1.5 Pro - Proven performance"),
            ("gemini-1.5-flash", "Gemini 1.5 Flash - Balanced option")
        ]

        # Display options with numbers
        all_models = openai_models + gemini_models
        for i, (model_id, description) in enumerate(all_models, 1):
            provider = "🔵 OpenAI" if model_id.startswith("gpt") else "🟢 Gemini"
            print(f"{i:2d}. {provider} - {description}")

        chatbot_model = None
        while True:
            try:
                choice = input(
                    f"\nChoose chatbot model (1-{len(all_models)}): ").strip()
                if choice.isdigit():
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(all_models):
                        chatbot_model = all_models[choice_num - 1][0]
                        provider = "OpenAI" if chatbot_model.startswith(
                            "gpt") else "Gemini"
                        print(f"✅ Selected: {chatbot_model} ({provider})")
                        break
                    else:
                        print(
                            f"⚠️  Please enter a number between 1 and {len(all_models)}.")
                else:
                    print(
                        f"⚠️  Please enter a valid number between 1 and {len(all_models)}.")
            except ValueError:
                print(
                    f"⚠️  Please enter a valid number between 1 and {len(all_models)}.")

        # STEP 5: Get chunking strategy
        print("\n✂️  Select chunking strategy:")
        print("1. Token-based (default) - Split by token count, good for general use")
        print("2. Semantic - Split by meaning, requires OpenAI embeddings")
        print("3. Line-based - Split by line count, good for structured text")
        print("4. Recursive - Character-based recursive splitting")

        chunking_method = "token"  # default
        while True:
            choice = input(
                "Choose chunking strategy (1-4, default 1): ").strip()
            if choice == "1" or choice == "":
                chunking_method = "token"
                print("✅ Selected: Token-based chunking")
                break
            elif choice == "2":
                chunking_method = "semantic"
                print("✅ Selected: Semantic chunking")
                break
            elif choice == "3":
                chunking_method = "line"
                print("✅ Selected: Line-based chunking")
                break
            elif choice == "4":
                chunking_method = "recursive"
                print("✅ Selected: Recursive chunking")
                break
            else:
                print("⚠️  Please enter 1, 2, 3, or 4.")

        print(f"\n🔧 Configuration:")
        print(f"   📁 Folder: {folder_path}")
        print(f"   🏷️  Namespace: {namespace}")
        print(f"   🔍 Embedding: {embedding_model}")
        print(f"   🤖 Chatbot: {chatbot_model}")
        print(f"   ✂️  Chunking: {chunking_method}")
        print(f"   💬 Interface: ✨ Streaming (real-time responses)")

        # Confirmation
        confirm = input("\n🚀 Start processing? (Y/n): ").strip().lower()
        if confirm in ['n', 'no']:
            print("❌ Operation cancelled.")
            return

        print("\n" + "=" * 80)
        print("🔄 STARTING DOCUMENT PROCESSING...")
        print("=" * 80)

        # Initialize master pipeline with user-selected chunking method
        master_pipeline = MasterPipeline(
            max_workers=4,
            chunking_method=chunking_method
        )

        # Create unique namespace with retry loop
        unique_namespace = None
        while unique_namespace is None:
            try:
                unique_namespace = master_pipeline.upload_pipeline.create_unique_namespace(
                    namespace)
                print(f"✅ Created namespace: {unique_namespace}")
            except ValueError as e:
                print(f"❌ Namespace error: {e}")
                print("Please enter a new namespace.")

                # Ask for new namespace
                while True:
                    namespace = input(
                        "🏷️  Enter namespace (e.g., 'my_documents', 'company_data'): ").strip()
                    if namespace:
                        # Comprehensive validation with immediate feedback
                        if not namespace.strip():
                            print("⚠️  Namespace cannot be empty. Please try again.")
                            continue
                        if ' ' in namespace:
                            print(
                                "⚠️  Namespace cannot contain spaces. Please try again.")
                            continue
                        if '|' in namespace:
                            print(
                                "⚠️  Namespace cannot contain pipe character (reserved for user ID separation). Please try again.")
                            continue
                        if len(namespace) > 50:
                            print(
                                "⚠️  Namespace too long (max 50 characters). Please try again.")
                            continue

                        # All validation passed
                        print(f"✅ Namespace '{namespace}' is valid.")
                        break
                    else:
                        print("⚠️  Please enter a valid namespace.")
            except Exception as e:
                print(f"❌ Unexpected error creating namespace: {e}")
                return

        # PHASE 0: Analyze directory for existing chatbots
        print(f"\n🔍 Analyzing directory for existing chatbots...")
        try:
            analysis = master_pipeline.upload_pipeline.analyze_directory_for_existing_chatbots(
                folder_path, namespace
            )
        except Exception as e:
            print(f"⚠️  Analysis failed: {e}")
            print("🔄 Proceeding with normal processing...")
            analysis = {
                'existing_chatbot_found': False,
                'message': f'Analysis failed: {str(e)}',
                'error': str(e)
            }

        # Handle different analysis results
        if analysis.get('existing_chatbot_found'):
            # Existing chatbot detected - let user choose
            user_choice = handle_existing_chatbot_scenario(
                analysis, master_pipeline)

            if user_choice == 'cancel':
                print("❌ Operation cancelled.")
                master_pipeline.close()
                return

            elif user_choice == 'use_existing':
                # Skip processing and go directly to chat
                print("🚀 Using existing chatbot...")
                # Don't close pipeline yet - we need user info for chat
                start_existing_chatbot(
                    analysis, master_pipeline, embedding_model, chatbot_model)
                master_pipeline.close()
                return

            elif user_choice == 'create_new':
                # Create timestamped namespace
                namespace = create_timestamped_namespace(namespace)
                unique_namespace = master_pipeline.upload_pipeline.create_unique_namespace(
                    namespace)
                print(
                    f"✅ Created new timestamped namespace: {unique_namespace}")

            elif user_choice == 'overwrite':
                # Delete existing data first
                print("🗑️  Deleting existing chatbot data...")
                try:
                    # Delete chunks first (due to foreign key constraints)
                    from db_service import Chunks, Documents
                    existing_docs = Documents.objects(
                        user=master_pipeline.upload_pipeline.user,
                        namespace=unique_namespace
                    )

                    for doc in existing_docs:
                        # Delete associated chunks
                        Chunks.objects(document=doc).delete()
                        # Delete the document
                        doc.delete()

                    print("✅ Existing chatbot data deleted.")

                except Exception as e:
                    print(f"❌ Error deleting existing data: {e}")
                    print("❌ Cannot proceed with overwrite.")
                    master_pipeline.close()
                    return

            elif user_choice == 'add_files':
                # For now, treat this as normal processing (files will be skipped if duplicates)
                print("📁 Adding new files to existing chatbot...")

        elif analysis.get('files_in_other_namespaces'):
            # Files exist in other namespaces - inform user
            user_choice = handle_files_in_other_namespaces(analysis)
            if user_choice == 'cancel':
                print("❌ Operation cancelled.")
                master_pipeline.close()
                return
            # If 'continue', proceed with normal processing

        else:
            # No existing chatbot found - proceed normally
            print(
                "✅ No existing chatbot detected. Proceeding with new chatbot creation...")

        # Run complete workflow with embeddings
        results = master_pipeline.process_directory_complete_with_embeddings(
            directory_path=folder_path,
            namespace=unique_namespace,
            user_id=None,  # Auto-determined
            embedding_model=embedding_model,
            use_parallel_upload=True,
            use_parallel_processing=True
        )

        # Check if processing was successful
        if not results.get('complete_workflow_success'):
            print(
                f"\n❌ Processing failed: {results.get('message', 'Unknown error')}")
            master_pipeline.close()
            return

        # Show results summary
        print(f"\n✅ PROCESSING COMPLETE!")
        if results.get('processing_results'):
            pr = results['processing_results']
            print(f"   📝 Created {pr['chunks_created']} chunks")
        if results.get('embedding_results'):
            er = results['embedding_results']
            print(f"   🤖 Embedded {er.get('total_chunks_embedded', 0)} chunks")

        # Get user ID for chatbot
        user_id = str(master_pipeline.upload_pipeline.user.id)

        # Close the pipeline
        master_pipeline.close()

        # PHASE 2: Start RAG Chatbot
        print("\n" + "=" * 80)
        print("🤖 INITIALIZING PERSONAL DOCUMENT ASSISTANT...")
        print("=" * 80)

        # Import and start the RAG chatbot
        from LLM.rag_llm_call import start_rag_chat_session

        # Start the interactive chat session
        start_rag_chat_session(
            user_id=user_id,
            namespace=namespace,  # Use original namespace (without user_id)
            embedding_model=embedding_model,
            chatbot_model=chatbot_model
        )

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Full error traceback:")

    print("\n🏁 Complete pipeline finished.")


if __name__ == "__main__":
    main()
