#!/usr/bin/env python3
"""
Master Document Processing Pipeline for RAG Chatbot
Combines document upload and processing into one seamless workflow:
1. Upload documents from local directory to GridFS
2. Parse documents using appropriate parsers
3. Chunk the content with token-based chunking
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class MasterPipeline:
    """Master pipeline that combines document upload and processing"""
    
    def __init__(self, max_workers: int = 4, rate_limit_delay: float = 0.2):
        """Initialize both upload and processing pipelines
        
        Args:
            max_workers: Maximum number of parallel workers (default: 4)
            rate_limit_delay: Delay between database operations in seconds (default: 0.2)
        """
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        
        # Initialize both pipelines
        logger.info("Initializing master pipeline...")
        
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
                rate_limit_delay=rate_limit_delay
            )
            logger.info("✓ Document processing pipeline initialized")
            
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
            logger.info(f"   📊 Total files found: {upload_results['total_files']}")
            logger.info(f"   ✅ Successfully uploaded: {upload_results['processed']}")
            logger.info(f"   ⚠️  Skipped (duplicates): {upload_results['skipped']}")
            logger.info(f"   ❌ Failed: {upload_results['failed']}")
            logger.info(f"   ⏱️  Upload time: {upload_results['processing_time']:.2f}s")
            
            # Check if we have any uploaded documents to process
            if upload_results['processed'] == 0:
                logger.warning("⚠️  No new documents were uploaded. Checking for existing pending documents...")
                
                # Check for existing pending documents
                pending_docs = self.processing_pipeline.get_pending_documents()
                if not pending_docs:
                    logger.info("ℹ️  No pending documents found. Workflow complete.")
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
                    logger.info(f"📋 Found {len(pending_docs)} existing pending documents to process")
            
            # PHASE 2: Process documents (parse, chunk, summarize)
            logger.info("\n" + "=" * 60)
            logger.info("🔄 PHASE 2: PROCESSING DOCUMENTS")
            logger.info("=" * 60)
            logger.info("🔍 Parsing documents...")
            logger.info("✂️  Chunking content...")
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
            logger.info(f"   📊 Total documents processed: {processing_results['total_documents']}")
            logger.info(f"   ✅ Successfully processed: {processing_results['processed']}")
            logger.info(f"   ❌ Failed: {processing_results['failed']}")
            logger.info(f"   📝 Total chunks created: {processing_results['chunks_created']}")
            logger.info(f"   ⏱️  Processing time: {processing_results['processing_time']:.2f}s")
            
            # Calculate final workflow statistics
            total_workflow_time = time.time() - workflow_start_time
            
            # Determine overall success
            workflow_success = (
                upload_results['failed'] == 0 and 
                processing_results['failed'] == 0 and
                (upload_results['processed'] > 0 or processing_results['processed'] > 0)
            )
            
            # FINAL SUMMARY
            logger.info("\n" + "=" * 80)
            logger.info("🏁 MASTER WORKFLOW COMPLETE")
            logger.info("=" * 80)
            logger.info(f"✅ Workflow Status: {'SUCCESS' if workflow_success else 'PARTIAL SUCCESS'}")
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
            logger.info(f"   📊 Documents processed: {processing_results['total_documents']}")
            logger.info(f"   ✅ Successful: {processing_results['processed']}")
            logger.info(f"   ❌ Failed: {processing_results['failed']}")
            logger.info(f"   📝 Chunks created: {processing_results['chunks_created']}")
            logger.info("")
            logger.info("⏱️  TIMING:")
            logger.info(f"   📤 Upload time: {upload_results['processing_time']:.2f}s")
            logger.info(f"   🔄 Processing time: {processing_results['processing_time']:.2f}s")
            logger.info(f"   🏁 Total workflow time: {total_workflow_time:.2f}s")
            
            if processing_results['chunks_created'] > 0:
                throughput = processing_results['chunks_created'] / total_workflow_time * 60
                logger.info(f"   📈 Chunk throughput: {throughput:.1f} chunks/minute")
            
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
    print("🚀 MASTER DOCUMENT PROCESSING PIPELINE")
    print("=" * 80)
    print("This tool provides complete document processing workflow:")
    print("• 📤 Upload documents to GridFS")
    print("• 🔍 Parse documents (PDF, DOCX, TXT, CSV)")
    print("• ✂️  Chunk content with smart token-based splitting")
    print("• 🤖 Generate AI summaries for each chunk")
    print("• 💾 Store everything in MongoDB ready for embedding")
    print("=" * 80)
    print()
    
    try:
        # Get user input for directory path
        while True:
            folder_path = input("📁 Enter the folder path containing documents: ").strip()
            if folder_path:
                # Handle quotes if user includes them
                folder_path = folder_path.strip('"\'')
                if os.path.exists(folder_path):
                    file_count = len([f for f in Path(folder_path).iterdir() 
                                    if f.is_file() and f.suffix.lower() in {'.pdf', '.docx', '.txt', '.csv'}])
                    print(f"✅ Found {file_count} supported files in {folder_path}")
                    break
                else:
                    print(f"❌ Error: Folder '{folder_path}' does not exist. Please try again.")
            else:
                print("⚠️  Please enter a valid folder path.")
        
        # Get namespace
        while True:
            namespace = input("🏷️  Enter the namespace (e.g., 'company_docs', 'user_manuals'): ").strip()
            if namespace:
                break
            else:
                print("⚠️  Please enter a valid namespace.")
        
        # Processing options
        print("\n⚙️  Processing Options:")
        
        # Parallel processing for upload
        use_parallel_upload = True
        upload_parallel_input = input("📤 Use parallel processing for uploads? (Y/n): ").strip().lower()
        if upload_parallel_input in ['n', 'no']:
            use_parallel_upload = False
        
        # Parallel processing for document processing
        use_parallel_processing = True
        processing_parallel_input = input("🔄 Use parallel processing for document processing? (Y/n): ").strip().lower()
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
        master_pipeline = MasterPipeline(max_workers=max_workers)
        
        # Run complete workflow
        results = master_pipeline.process_directory_complete(
            directory_path=folder_path,
            namespace=namespace,
            use_parallel_upload=use_parallel_upload,
            use_parallel_processing=use_parallel_processing
        )
        
        # Show detailed results
        if results['workflow_success']:
            print(f"\n🎉 SUCCESS! Workflow completed successfully!")
        else:
            print(f"\n⚠️  PARTIAL SUCCESS: {results['message']}")
        
        # Performance summary
        print(f"\n📊 FINAL SUMMARY:")
        if results.get('upload_results'):
            ur = results['upload_results']
            print(f"   📤 Upload: {ur['processed']} processed, {ur['skipped']} skipped, {ur['failed']} failed")
        
        if results.get('processing_results'):
            pr = results['processing_results']
            print(f"   🔄 Processing: {pr['processed']} processed, {pr['failed']} failed")
            print(f"   📝 Chunks: {pr['chunks_created']} total chunks created")
        
        print(f"   ⏱️  Total time: {results['total_workflow_time']:.2f} seconds")
        
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