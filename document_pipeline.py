#!/usr/bin/env python3
"""
Document Upload Pipeline for RAG Chatbot
Processes documents from a local directory and uploads them to GridFS with metadata
"""

import os
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from db_service import initialize_db, User_Auth_Table, Documents, upload_file_to_gridfs
from file_type import doc_type_check


class DocumentPipeline:
    """Main document processing pipeline with parallel processing support"""

    def __init__(self, max_workers: int = 4, rate_limit_delay: float = 0.2):
        """Initialize the pipeline with database connection and parallel processing settings

        Args:
            max_workers: Maximum number of parallel workers (default: 4, recommended: 3-5)
            rate_limit_delay: Delay between database operations in seconds (default: 0.2)
        """
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
            'skipped': 0,
            'failed': 0,
            'start_time': None
        }
        self._stats_lock = Lock()

        # Get the existing test user
        try:
            self.user = User_Auth_Table.objects(user_name="test_user").first()
            if not self.user:
                raise Exception("Test user not found in database")
            print(f"Using user: {self.user.user_name} (ID: {self.user.id})")
            print(
                f"Parallel processing: {self.max_workers} workers, {self.rate_limit_delay}s rate limit")
        except Exception as e:
            raise Exception(f"Error getting user: {e}")

    def generate_file_hash(self, file_bytes: bytes) -> str:
        """Generate SHA256 hash for the file content"""
        return hashlib.sha256(file_bytes).hexdigest()

    def create_unique_namespace(self, user_namespace: str) -> str:
        """Create unique namespace by concatenating user input with user ID

        Args:
            user_namespace: User-provided namespace prefix (should be pre-validated)

        Returns:
            Unique namespace in format: {user_namespace}|{user_id}

        Raises:
            ValueError: If user_namespace contains spaces, pipe character, or is too long (failsafe validation)
        """
        # Failsafe validation (should already be validated in CLI)
        if ' ' in user_namespace:
            raise ValueError("Namespace cannot contain spaces")

        if '|' in user_namespace:
            raise ValueError(
                "Namespace cannot contain pipe character (used for user ID separation)")

        if len(user_namespace) > 50:  # Leave room for user ID
            raise ValueError("Namespace prefix too long (max 50 characters)")

        if not user_namespace.strip():
            raise ValueError("Namespace cannot be empty")

        # Create unique namespace
        unique_namespace = f"{user_namespace.strip()}|{self.user.id}"
        return unique_namespace

    def check_file_exists(self, file_hash: str) -> bool:
        """Check if a file with this hash already exists for this user (thread-safe)"""
        try:
            with self._db_lock:
                # Add small delay for rate limiting
                time.sleep(self.rate_limit_delay / 2)
                existing_doc = Documents.objects(
                    user=self.user, full_hash=file_hash).first()
                return existing_doc is not None
        except Exception as e:
            print(f"Error checking file existence: {e}")
            return False

    def get_supported_files(self, directory_path: str) -> List[str]:
        """Get list of supported files from directory"""
        supported_extensions = {'.pdf', '.docx', '.txt', '.csv'}
        files = []

        try:
            directory = Path(directory_path)
            if not directory.exists():
                print(f"Directory {directory_path} does not exist")
                return files

            for file_path in directory.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    files.append(str(file_path))

            print(f"Found {len(files)} supported files in {directory_path}")
            return files

        except Exception as e:
            print(f"Error scanning directory {directory_path}: {e}")
            return files

    def _update_stats(self, result_type: str):
        """Thread-safe statistics update"""
        with self._stats_lock:
            if result_type in self._stats:
                self._stats[result_type] += 1

    def _safe_gridfs_upload(self, file_bytes: bytes, filename: str, content_type: str):
        """Thread-safe GridFS upload with rate limiting"""
        with self._db_lock:
            time.sleep(self.rate_limit_delay)
            return upload_file_to_gridfs(self.fs, file_bytes, filename, content_type)

    def _safe_document_save(self, document: Documents):
        """Thread-safe document save with rate limiting"""
        with self._db_lock:
            time.sleep(self.rate_limit_delay)
            document.save()
            return document.id

    def process_single_file(self, file_path: str, namespace: str) -> Dict:
        """Process a single file and return processing result"""
        result = {
            'file_path': file_path,
            'success': False,
            'message': '',
            'file_type': '',
            'file_size': 0,
            'hash': '',
            'gridfs_id': None,
            'document_id': None
        }

        try:
            # Read file bytes
            with open(file_path, 'rb') as f:
                file_bytes = f.read()

            # Get file type and size using existing function
            file_type_info = doc_type_check(file_bytes)
            file_type_description = file_type_info[0]
            file_size = file_type_info[1]

            result['file_type'] = file_type_description
            result['file_size'] = file_size

            print(f"\nProcessing: {os.path.basename(file_path)}")
            print(f"  Type: {file_type_description}")
            print(
                f"  Size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")

            # Generate hash
            file_hash = self.generate_file_hash(file_bytes)
            result['hash'] = file_hash
            print(f"  Hash: {file_hash[:16]}...")

            # Check if file already exists
            if self.check_file_exists(file_hash):
                result['message'] = "File already exists (duplicate hash)"
                print(f"  Status: SKIPPED - {result['message']}")
                self._update_stats('skipped')
                return result

            # Determine content type for GridFS
            content_type_map = {
                "The document provided is a PDF file": "application/pdf",
                "The document provided is a DOCX file": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "The document provided is a TXT file": "text/plain",
                "The document provided is a CSV file": "text/csv"
            }
            content_type = content_type_map.get(
                file_type_description, "application/octet-stream")

            # Upload to GridFS (thread-safe)
            gridfs_file_id = self._safe_gridfs_upload(
                file_bytes,
                os.path.basename(file_path),
                content_type
            )

            if not gridfs_file_id:
                result['message'] = "Failed to upload to GridFS"
                print(f"  Status: FAILED - {result['message']}")
                self._update_stats('failed')
                return result

            result['gridfs_id'] = gridfs_file_id
            print(f"  GridFS ID: {gridfs_file_id}")

            # Map file type description to simple type
            file_type_simple_map = {
                "The document provided is a PDF file": "pdf",
                "The document provided is a DOCX file": "docx",
                "The document provided is a TXT file": "txt",
                "The document provided is a CSV file": "csv"
            }
            file_type_simple = file_type_simple_map.get(
                file_type_description, "unknown")

            # Create Documents record (thread-safe)
            document = Documents(
                user=self.user,
                file_name=os.path.basename(file_path),
                file_type=file_type_simple,
                gridfs_file_id=gridfs_file_id,
                status="pending",
                full_hash=file_hash,
                namespace=namespace,
                created_at=datetime.now()
            )

            result['document_id'] = self._safe_document_save(document)
            print(f"  Document ID: {result['document_id']}")
            print(f"  Status: SUCCESS - Uploaded to GridFS and created document record")

            result['success'] = True
            result['message'] = "Successfully processed"
            self._update_stats('processed')

        except Exception as e:
            result['message'] = f"Error processing file: {str(e)}"
            print(f"  Status: FAILED - {result['message']}")
            self._update_stats('failed')

        return result

    def process_directory(self, directory_path: str, namespace: str, use_parallel: bool = True) -> Dict:
        """Process all supported files in a directory with optional parallel processing"""
        print(f"\n=== Starting Document Upload Pipeline ===")
        print(f"Directory: {directory_path}")
        print(f"Namespace: {namespace}")
        print(f"User: {self.user.user_name}")

        # Reset statistics
        with self._stats_lock:
            self._stats = {
                'processed': 0,
                'skipped': 0,
                'failed': 0,
                'start_time': time.time()
            }

        # Get supported files
        files = self.get_supported_files(directory_path)

        if not files:
            return {
                'total_files': 0,
                'processed': 0,
                'skipped': 0,
                'failed': 0,
                'results': [],
                'processing_time': 0
            }

        if use_parallel and len(files) > 1:
            results = self._process_files_parallel(files, namespace)
        else:
            results = self._process_files_sequential(files, namespace)

        # Calculate final statistics
        with self._stats_lock:
            processing_time = time.time() - self._stats['start_time']
            summary = {
                'total_files': len(files),
                'processed': self._stats['processed'],
                'skipped': self._stats['skipped'],
                'failed': self._stats['failed'],
                'results': results,
                'processing_time': processing_time
            }

        print(f"\n=== Pipeline Complete ===")
        print(f"Total files found: {summary['total_files']}")
        print(f"Successfully processed: {summary['processed']}")
        print(f"Skipped (duplicates): {summary['skipped']}")
        print(f"Failed: {summary['failed']}")
        print(f"Processing time: {processing_time:.2f} seconds")
        if summary['processed'] > 0:
            print(
                f"Average time per file: {processing_time / len(files):.2f} seconds")

        return summary

    def _process_files_sequential(self, files: List[str], namespace: str) -> List[Dict]:
        """Process files sequentially (fallback method)"""
        print(f"Processing {len(files)} files sequentially...")
        results = []

        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] Processing file...")
            result = self.process_single_file(file_path, namespace)
            results.append(result)

        return results

    def _process_files_parallel(self, files: List[str], namespace: str) -> List[Dict]:
        """Process files in parallel using ThreadPoolExecutor"""
        print(
            f"Processing {len(files)} files in parallel ({self.max_workers} workers)...")
        results = []

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all files for processing
                future_to_file = {
                    executor.submit(self.process_single_file, file_path, namespace): file_path
                    for file_path in files
                }

                # Collect results as they complete
                completed_count = 0
                for future in as_completed(future_to_file):
                    completed_count += 1
                    file_path = future_to_file[future]

                    try:
                        # 5 minute timeout per file
                        result = future.result(timeout=300)
                        results.append(result)

                        # Show progress
                        filename = os.path.basename(file_path)
                        status = "✓" if result['success'] else (
                            "⚠" if 'already exists' in result['message'] else "✗")
                        print(
                            f"[{completed_count}/{len(files)}] {status} {filename}")

                    except Exception as e:
                        # Handle individual file errors
                        error_result = {
                            'file_path': file_path,
                            'success': False,
                            'message': f"Processing error: {str(e)}",
                            'file_type': '',
                            'file_size': 0,
                            'hash': '',
                            'gridfs_id': None,
                            'document_id': None
                        }
                        results.append(error_result)
                        self._update_stats('failed')
                        print(
                            f"[{completed_count}/{len(files)}] ✗ {os.path.basename(file_path)} - ERROR: {str(e)}")

        except Exception as e:
            print(f"Parallel processing error: {e}")
            print("Falling back to sequential processing...")
            return self._process_files_sequential(files, namespace)

        # Sort results by original file order for consistency
        file_order = {file_path: i for i, file_path in enumerate(files)}
        results.sort(key=lambda r: file_order.get(
            r['file_path'], float('inf')))

        return results

    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()


def main():
    """CLI interface for the document upload pipeline"""
    print("=== Document Upload Pipeline CLI ===")
    print("This tool uploads documents to GridFS and populates the documents table.")
    print("Supported file types: PDF, DOCX, TXT, CSV")
    print()

    try:
        # Get user input
        while True:
            folder_path = input(
                "Enter the folder path containing documents: ").strip()
            if folder_path:
                # Handle quotes if user includes them
                folder_path = folder_path.strip('"\'')
                if os.path.exists(folder_path):
                    break
                else:
                    print(
                        f"Error: Folder '{folder_path}' does not exist. Please try again.")
            else:
                print("Please enter a valid folder path.")

        print("\n🏷️  Namespace Configuration:")
        print("   Your namespace will be made unique by adding your user ID")
        print("   Format: your_input|userid")
        print("   Note: Cannot contain spaces or pipe character (reserved for user ID separation)")

        namespace = None
        while True:
            user_namespace = input(
                "Enter namespace prefix (e.g., 'my_documents'): ").strip()
            if user_namespace:
                # Comprehensive validation with immediate feedback
                if not user_namespace.strip():
                    print("⚠️  Namespace cannot be empty. Please try again.")
                    continue
                if ' ' in user_namespace:
                    print("⚠️  Namespace cannot contain spaces. Please try again.")
                    continue
                if '|' in user_namespace:
                    print(
                        "⚠️  Namespace cannot contain pipe character (reserved for user ID separation). Please try again.")
                    continue
                if len(user_namespace) > 50:
                    print(
                        "⚠️  Namespace too long (max 50 characters). Please try again.")
                    continue

                # All validation passed
                namespace = user_namespace  # Store user input, will be made unique later
                print(f"✅ Namespace '{user_namespace}' is valid.")
                break
            else:
                print("⚠️  Please enter a valid namespace.")

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

        # Initialize pipeline
        print("\nInitializing pipeline...")
        pipeline = DocumentPipeline(max_workers=max_workers)

        # Create unique namespace with retry loop
        unique_namespace = None
        while unique_namespace is None:
            try:
                unique_namespace = pipeline.create_unique_namespace(namespace)
                print(f"✅ Created unique namespace: {unique_namespace}")
            except ValueError as e:
                print(f"❌ Namespace error: {e}")
                print("Please enter a new namespace.")

                # Ask for new namespace
                while True:
                    user_namespace = input(
                        "Enter namespace prefix (e.g., 'my_documents'): ").strip()
                    if user_namespace:
                        # Comprehensive validation with immediate feedback
                        if not user_namespace.strip():
                            print("⚠️  Namespace cannot be empty. Please try again.")
                            continue
                        if ' ' in user_namespace:
                            print(
                                "⚠️  Namespace cannot contain spaces. Please try again.")
                            continue
                        if '|' in user_namespace:
                            print(
                                "⚠️  Namespace cannot contain pipe character (reserved for user ID separation). Please try again.")
                            continue
                        if len(user_namespace) > 50:
                            print(
                                "⚠️  Namespace too long (max 50 characters). Please try again.")
                            continue

                        # All validation passed
                        namespace = user_namespace
                        print(f"✅ Namespace '{user_namespace}' is valid.")
                        break
                    else:
                        print("⚠️  Please enter a valid namespace.")
            except Exception as e:
                print(f"❌ Unexpected error creating unique namespace: {e}")
                return

        # Process directory
        results = pipeline.process_directory(
            folder_path, unique_namespace, use_parallel)

        # Show detailed results if any files were processed
        if results['results']:
            print(f"\n=== Detailed Results ===")
            for result in results['results']:
                status = "✓ SUCCESS" if result['success'] else (
                    "⚠ SKIPPED" if 'already exists' in result['message'] else "✗ FAILED")
                print(
                    f"{status}: {os.path.basename(result['file_path'])} - {result['message']}")

        # Performance summary
        if results.get('processing_time', 0) > 0:
            print(f"\n=== Performance Summary ===")
            print(
                f"Total processing time: {results['processing_time']:.2f} seconds")
            if results['total_files'] > 0:
                avg_time = results['processing_time'] / results['total_files']
                print(f"Average time per file: {avg_time:.2f} seconds")
                throughput = results['total_files'] / \
                    results['processing_time'] * 60
                print(f"Throughput: {throughput:.1f} files per minute")

        # Close pipeline
        pipeline.close()

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")

    print("\nPipeline finished.")


if __name__ == "__main__":
    main()
