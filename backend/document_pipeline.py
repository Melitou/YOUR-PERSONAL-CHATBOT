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

from db_service import initialize_db, User_Auth_Table, Documents, upload_file_to_gridfs, Chunks, Conversation, Messages, ChatbotDocumentsMapper, ChatBots
from file_type import doc_type_check
import logging

logger = logging.getLogger(__name__)


class DocumentPipeline:
    """Main document processing pipeline with parallel processing support"""

    def __init__(self, max_workers: int = 4, rate_limit_delay: float = 0.2, user: User_Auth_Table = None):
        """Initialize the pipeline with database connection and parallel processing settings

        Args:
            max_workers: Maximum number of parallel workers (default: 4, recommended: 3-5)
            rate_limit_delay: Delay between database operations in seconds (default: 0.2)
            user: User object to use for processing (optional, will create/find test_user if not provided)
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

        # Set user for processing
        if user:
            self.user = user
            print(f"Using provided user: {self.user.user_name} (ID: {self.user.id})")
        else:
            # Get or create test user for backward compatibility
            try:
                self.user = User_Auth_Table.objects(user_name="test_user").first()
                if not self.user:
                    # Create test user if it doesn't exist
                    from datetime import datetime
                    self.user = User_Auth_Table(
                        user_name="test_user",
                        password="hashed_password_here",
                        first_name="Test",
                        last_name="User",
                        email="test@example.com",
                        created_at=datetime.now(),
                        role="User"
                    )
                    self.user.save()
                    print(f"Created test user: {self.user.user_name} (ID: {self.user.id})")
                else:
                    print(f"Using existing test user: {self.user.user_name} (ID: {self.user.id})")
            except Exception as e:
                raise Exception(f"Error getting/creating user: {e}")
        
        print(f"Parallel processing: {self.max_workers} workers, {self.rate_limit_delay}s rate limit")

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

    def process_single_file(self, file_path: str, namespace: str, chatbot: ChatBots) -> Dict:
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

                # Take the exising document
                existing_document = Documents.objects(
                    user=self.user,
                    full_hash=file_hash
                ).first()

                # Add the association in the chatbot_documents_mapper collection
                try:
                    chatbot_documents_mapper = ChatbotDocumentsMapper(
                        chatbot=chatbot,
                        document=existing_document,
                        user=self.user,
                        assigned_at=datetime.now()
                    )   
                    chatbot_documents_mapper.save()
                    print(f"  Added document to chatbot mapping")
                except Exception as e:
                    logger.error(f"Error adding association to chatbot_documents_mapper: {e}")

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

            # Save the document first
            result['document_id'] = self._safe_document_save(document)

            # Add the association in the chatbot_documents_mapper collection
            try:
                chatbot_documents_mapper = ChatbotDocumentsMapper(
                    chatbot=chatbot,
                    document=document,
                    user=self.user,
                    assigned_at=datetime.now()
                )   
                chatbot_documents_mapper.save()
                print(f"  Added document to chatbot mapping")   
            except Exception as e:
                logger.error(f"Error adding association to chatbot_documents_mapper: {e}")
            
            # Chatbot associations will be created centrally after the chatbot is saved
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

    def process_directory(self, directory_path: str, namespace: str, use_parallel: bool = True, chatbot: ChatBots = None) -> Dict:
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
            results = self._process_files_parallel(files, namespace, chatbot)
        else:
            results = self._process_files_sequential(files, namespace, chatbot)

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

    def _process_files_sequential(self, files: List[str], namespace: str, chatbot: ChatBots) -> List[Dict]:
        """Process files sequentially (fallback method)"""
        print(f"Processing {len(files)} files sequentially...")
        results = []

        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] Processing file...")
            result = self.process_single_file(file_path, namespace, chatbot)
            results.append(result)

        return results

    def _process_files_parallel(self, files: List[str], namespace: str, chatbot: ChatBots) -> List[Dict]:
        """Process files in parallel using ThreadPoolExecutor"""
        print(
            f"Processing {len(files)} files in parallel ({self.max_workers} workers)...")
        results = []

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all files for processing
                future_to_file = {
                    executor.submit(self.process_single_file, file_path, namespace, chatbot): file_path
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
            return self._process_files_sequential(files, namespace, chatbot)

        # Sort results by original file order for consistency
        file_order = {file_path: i for i, file_path in enumerate(files)}
        results.sort(key=lambda r: file_order.get(
            r['file_path'], float('inf')))

        return results

    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()


    def get_directory_file_hashes(self, directory_path: str) -> Dict[str, str]:
        """Calculate hashes for all supported files in directory

        Args:
            directory_path: Path to directory containing documents

        Returns:
            Dict mapping filename -> hash for all supported files
        """
        file_hashes = {}

        try:
            files = self.get_supported_files(directory_path)
            print(f"≡ƒôè Calculating hashes for {len(files)} files...")

            for file_path in files:
                try:
                    with open(file_path, 'rb') as f:
                        file_bytes = f.read()

                    file_hash = self.generate_file_hash(file_bytes)
                    filename = os.path.basename(file_path)
                    file_hashes[filename] = file_hash
                    print(f"   Γ£ô {filename}: {file_hash[:16]}...")

                except Exception as e:
                    print(
                        f"   Γ¥î Error hashing {os.path.basename(file_path)}: {e}")
                    continue

            return file_hashes

        except Exception as e:
            print(f"Γ¥î Error calculating directory hashes: {e}")
            return {}

    def check_namespace_chatbot_status(self, namespace: str) -> Dict:
        """Check if a complete, functional chatbot exists in the given namespace

        Args:
            namespace: The namespace to check (should include user_id suffix)

        Returns:
            Dict with chatbot status information
        """
        try:
            # Query all documents in the namespace that are processed
            processed_docs = Documents.objects(
                user=self.user,
                namespace=namespace,
                status="processed"
            )

            if not processed_docs:
                return {
                    'exists': False,
                    'is_complete': False,
                    'document_count': 0,
                    'chunk_count': 0,
                    'embedded_chunk_count': 0,
                    'file_names': [],
                    'created_date': None,
                    'last_updated': None
                }

            # Get chunks for these documents and check embeddings
            total_chunks = 0
            embedded_chunks = 0
            file_names = []
            created_dates = []

            for doc in processed_docs:
                file_names.append(doc.file_name)
                created_dates.append(doc.created_at)

                # Count chunks for this document
                doc_chunks = Chunks.objects(document=doc, namespace=namespace)
                total_chunks += doc_chunks.count()

                # Count embedded chunks (have vector_id)
                embedded_doc_chunks = doc_chunks.filter(vector_id__ne=None)
                embedded_chunks += embedded_doc_chunks.count()

            # Determine if chatbot is complete (all chunks have embeddings)
            is_complete = total_chunks > 0 and embedded_chunks == total_chunks

            return {
                'exists': True,
                'is_complete': is_complete,
                'document_count': len(processed_docs),
                'chunk_count': total_chunks,
                'embedded_chunk_count': embedded_chunks,
                'file_names': file_names,
                'created_date': min(created_dates) if created_dates else None,
                'last_updated': max(created_dates) if created_dates else None
            }

        except Exception as e:
            print(f"Γ¥î Error checking namespace status: {e}")
            return {
                'exists': False,
                'is_complete': False,
                'document_count': 0,
                'chunk_count': 0,
                'embedded_chunk_count': 0,
                'file_names': [],
                'created_date': None,
                'last_updated': None,
                'error': str(e)
            }

    def get_namespace_file_inventory(self, namespace: str) -> List[Dict]:
        """Get detailed inventory of files in a namespace

        Args:
            namespace: The namespace to analyze

        Returns:
            List of dicts with file details
        """
        try:
            inventory = []

            # Get all documents in namespace
            docs = Documents.objects(user=self.user, namespace=namespace)

            for doc in docs:
                # Count chunks for this document
                doc_chunks = Chunks.objects(document=doc, namespace=namespace)
                total_chunks = doc_chunks.count()
                embedded_chunks = doc_chunks.filter(vector_id__ne=None).count()

                inventory.append({
                    'file_name': doc.file_name,
                    'file_type': doc.file_type,
                    'status': doc.status,
                    'file_hash': doc.full_hash,
                    'total_chunks': total_chunks,
                    'embedded_chunks': embedded_chunks,
                    'is_complete': embedded_chunks == total_chunks and total_chunks > 0,
                    'created_at': doc.created_at,
                    'chunking_method': getattr(doc, 'chunking_method', 'unknown')
                })

            return inventory

        except Exception as e:
            print(f"Γ¥î Error getting file inventory: {e}")
            return []

    def format_chatbot_summary(self, namespace_status: Dict, file_inventory: List[Dict] = None) -> str:
        """Format chatbot status information for user display

        Args:
            namespace_status: Status dict from check_namespace_chatbot_status()
            file_inventory: Optional detailed file inventory

        Returns:
            Formatted string for display
        """
        if not namespace_status['exists']:
            return "Γ¥î No chatbot found in this namespace"

        # Extract namespace name (remove user_id suffix)
        namespace_name = namespace_status.get('namespace_name', 'Unknown')

        summary = f"""
≡ƒÄ» EXISTING CHATBOT DETECTED!

≡ƒôè Chatbot Details:
   ≡ƒÅ╖∩╕Å  Name: "{namespace_name}"
   ≡ƒôü Files: {namespace_status['document_count']} documents
   ≡ƒô¥ Chunks: {namespace_status['chunk_count']} total chunks
   ≡ƒºá Embeddings: {namespace_status['embedded_chunk_count']}/{namespace_status['chunk_count']} complete
   ≡ƒôà Created: {namespace_status['created_date'].strftime('%Y-%m-%d %H:%M:%S') if namespace_status['created_date'] else 'Unknown'}
   ≡ƒöä Last Updated: {namespace_status['last_updated'].strftime('%Y-%m-%d %H:%M:%S') if namespace_status['last_updated'] else 'Unknown'}

{'Γ£à This chatbot is ready to use!' if namespace_status['is_complete'] else 'ΓÜá∩╕Å  This chatbot is incomplete (missing embeddings)'}
"""

        if file_inventory:
            summary += "\n≡ƒôï Files in this chatbot:\n"
            for file_info in file_inventory:
                status_icon = "Γ£à" if file_info['is_complete'] else "ΓÜá∩╕Å"
                summary += f"   {status_icon} {file_info['file_name']} ({file_info['embedded_chunks']} chunks)\n"

        return summary

    def analyze_directory_for_existing_chatbots(self, directory_path: str, user_namespace: str) -> Dict:
        """Analyze directory for existing chatbots before processing

        This is the main function that orchestrates the detection of existing chatbots

        Args:
            directory_path: Path to directory containing documents
            user_namespace: User-provided namespace (without user_id suffix)

        Returns:
            Dict with analysis results and recommendations
        """
        print(f"\n≡ƒöì Analyzing directory for existing chatbots...")
        print(f"≡ƒôü Directory: {directory_path}")
        print(f"≡ƒÅ╖∩╕Å  Namespace: {user_namespace}")

        try:
            # Step 1: Calculate hashes for all files in directory
            directory_hashes = self.get_directory_file_hashes(directory_path)
            if not directory_hashes:
                return {
                    'existing_chatbot_found': False,
                    'message': 'No supported files found in directory'
                }

            # Step 2: Create the full namespace that would be used
            proposed_namespace = f"{user_namespace}|{self.user.id}"

            # Step 3: Check if namespace already has a chatbot
            namespace_status = self.check_namespace_chatbot_status(
                proposed_namespace)

            # Step 4: If namespace exists, check file overlap
            if namespace_status['exists']:
                file_inventory = self.get_namespace_file_inventory(
                    proposed_namespace)

                # Check for file overlap
                existing_hashes = {item['file_hash']
                                   for item in file_inventory}
                directory_hash_set = set(directory_hashes.values())

                overlap_hashes = existing_hashes.intersection(
                    directory_hash_set)
                overlap_percentage = len(
                    overlap_hashes) / len(directory_hash_set) * 100 if directory_hash_set else 0

                # Determine scenario
                if overlap_percentage == 100:
                    scenario = "identical_files"
                    message = "Identical files found in existing chatbot"
                elif overlap_percentage > 0:
                    scenario = "partial_overlap"
                    message = f"Partial file overlap ({overlap_percentage:.1f}%)"
                else:
                    scenario = "different_files"
                    message = "Namespace exists but with different files"

                return {
                    'existing_chatbot_found': True,
                    'scenario': scenario,
                    'namespace_status': namespace_status,
                    'file_inventory': file_inventory,
                    'directory_hashes': directory_hashes,
                    'overlap_percentage': overlap_percentage,
                    'overlap_hashes': overlap_hashes,
                    'proposed_namespace': proposed_namespace,
                    'user_namespace': user_namespace,
                    'message': message,
                    'formatted_summary': self.format_chatbot_summary(
                        {**namespace_status, 'namespace_name': user_namespace},
                        file_inventory
                    )
                }

            # Step 5: Check if files exist in other namespaces
            files_in_other_namespaces = []
            for filename, file_hash in directory_hashes.items():
                existing_docs = Documents.objects(
                    user=self.user, full_hash=file_hash)
                for doc in existing_docs:
                    if doc.namespace != proposed_namespace:
                        files_in_other_namespaces.append({
                            'filename': filename,
                            'file_hash': file_hash,
                            'existing_namespace': doc.namespace,
                            'existing_namespace_name': doc.namespace.split('|')[0] if '|' in doc.namespace else doc.namespace
                        })

            if files_in_other_namespaces:
                return {
                    'existing_chatbot_found': False,
                    'files_in_other_namespaces': files_in_other_namespaces,
                    'directory_hashes': directory_hashes,
                    'proposed_namespace': proposed_namespace,
                    'user_namespace': user_namespace,
                    'message': f"Files found in {len(set(item['existing_namespace'] for item in files_in_other_namespaces))} other namespace(s)"
                }

            # Step 6: No existing chatbot found
            return {
                'existing_chatbot_found': False,
                'directory_hashes': directory_hashes,
                'proposed_namespace': proposed_namespace,
                'user_namespace': user_namespace,
                'message': 'No existing chatbot found - ready for new processing'
            }

        except Exception as e:
            print(f"Γ¥î Error analyzing directory: {e}")
            return {
                'existing_chatbot_found': False,
                'error': str(e),
                'message': f'Analysis failed: {str(e)}'
            }


# def main():
#     """CLI interface for the document upload pipeline"""
#     print("=== Document Upload Pipeline CLI ===")
#     print("This tool uploads documents to GridFS and populates the documents table.")
#     print("Supported file types: PDF, DOCX, TXT, CSV")
#     print()

#     try:
#         # Get user input
#         while True:
#             folder_path = input(
#                 "Enter the folder path containing documents: ").strip()
#             if folder_path:
#                 # Handle quotes if user includes them
#                 folder_path = folder_path.strip('"\'')
#                 if os.path.exists(folder_path):
#                     break
#                 else:
#                     print(
#                         f"Error: Folder '{folder_path}' does not exist. Please try again.")
#             else:
#                 print("Please enter a valid folder path.")

#         print("\n🏷️  Namespace Configuration:")
#         print("   Your namespace will be made unique by adding your user ID")
#         print("   Format: your_input|userid")
#         print("   Note: Cannot contain spaces or pipe character (reserved for user ID separation)")

#         namespace = None
#         while True:
#             user_namespace = input(
#                 "Enter namespace prefix (e.g., 'my_documents'): ").strip()
#             if user_namespace:
#                 # Comprehensive validation with immediate feedback
#                 if not user_namespace.strip():
#                     print("⚠️  Namespace cannot be empty. Please try again.")
#                     continue
#                 if ' ' in user_namespace:
#                     print("⚠️  Namespace cannot contain spaces. Please try again.")
#                     continue
#                 if '|' in user_namespace:
#                     print(
#                         "⚠️  Namespace cannot contain pipe character (reserved for user ID separation). Please try again.")
#                     continue
#                 if len(user_namespace) > 50:
#                     print(
#                         "⚠️  Namespace too long (max 50 characters). Please try again.")
#                     continue

#                 # All validation passed
#                 namespace = user_namespace  # Store user input, will be made unique later
#                 print(f"✅ Namespace '{user_namespace}' is valid.")
#                 break
#             else:
#                 print("⚠️  Please enter a valid namespace.")

#         # Optional: Ask about parallel processing
#         use_parallel = True
#         parallel_input = input(
#             "Use parallel processing? (Y/n): ").strip().lower()
#         if parallel_input in ['n', 'no']:
#             use_parallel = False
#             print("Will use sequential processing")
#         else:
#             print("Will use parallel processing (4 workers)")

#         # Optional: Custom worker count for advanced users
#         max_workers = 4
#         if use_parallel:
#             workers_input = input(
#                 "Number of workers (2-5, default 4): ").strip()
#             if workers_input.isdigit():
#                 max_workers = max(2, min(5, int(workers_input)))
#                 print(f"Using {max_workers} workers")

#         # Initialize pipeline
#         print("\nInitializing pipeline...")
#         pipeline = DocumentPipeline(max_workers=max_workers)

#         # Create unique namespace with retry loop
#         unique_namespace = None
#         while unique_namespace is None:
#             try:
#                 unique_namespace = pipeline.create_unique_namespace(namespace)
#                 print(f"✅ Created unique namespace: {unique_namespace}")
#             except ValueError as e:
#                 print(f"❌ Namespace error: {e}")
#                 print("Please enter a new namespace.")

#                 # Ask for new namespace
#                 while True:
#                     user_namespace = input(
#                         "Enter namespace prefix (e.g., 'my_documents'): ").strip()
#                     if user_namespace:
#                         # Comprehensive validation with immediate feedback
#                         if not user_namespace.strip():
#                             print("⚠️  Namespace cannot be empty. Please try again.")
#                             continue
#                         if ' ' in user_namespace:
#                             print(
#                                 "⚠️  Namespace cannot contain spaces. Please try again.")
#                             continue
#                         if '|' in user_namespace:
#                             print(
#                                 "⚠️  Namespace cannot contain pipe character (reserved for user ID separation). Please try again.")
#                             continue
#                         if len(user_namespace) > 50:
#                             print(
#                                 "⚠️  Namespace too long (max 50 characters). Please try again.")
#                             continue

#                         # All validation passed
#                         namespace = user_namespace
#                         print(f"✅ Namespace '{user_namespace}' is valid.")
#                         break
#                     else:
#                         print("⚠️  Please enter a valid namespace.")
#             except Exception as e:
#                 print(f"❌ Unexpected error creating unique namespace: {e}")
#                 return

#         # Process directory
#         results = pipeline.process_directory(
#             folder_path, unique_namespace, use_parallel)

#         # Show detailed results if any files were processed
#         if results['results']:
#             print(f"\n=== Detailed Results ===")
#             for result in results['results']:
#                 status = "✓ SUCCESS" if result['success'] else (
#                     "⚠ SKIPPED" if 'already exists' in result['message'] else "✗ FAILED")
#                 print(
#                     f"{status}: {os.path.basename(result['file_path'])} - {result['message']}")

#         # Performance summary
#         if results.get('processing_time', 0) > 0:
#             print(f"\n=== Performance Summary ===")
#             print(
#                 f"Total processing time: {results['processing_time']:.2f} seconds")
#             if results['total_files'] > 0:
#                 avg_time = results['processing_time'] / results['total_files']
#                 print(f"Average time per file: {avg_time:.2f} seconds")
#                 throughput = results['total_files'] / \
#                     results['processing_time'] * 60
#                 print(f"Throughput: {throughput:.1f} files per minute")

#         # Close pipeline
#         pipeline.close()

#     except KeyboardInterrupt:
#         print("\n\nOperation cancelled by user.")
#     except Exception as e:
#         print(f"\nError: {e}")

#     print("\nPipeline finished.")


if __name__ == "__main__":
    # main()
    pass
