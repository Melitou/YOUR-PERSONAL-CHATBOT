import os
import logging
import time
from typing import List, Optional, Dict
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from pinecone import Pinecone, ServerlessSpec
from db_service import Chunks, User_Auth_Table
from bson import ObjectId

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service class for creating embeddings from text chunks.
    Supports multiple embedding models with fallback logic.
    """

    def __init__(self):
        self.openai_client = None
        self.google_initialized = False
        self.google_client = None
        self.pinecone_client = None

        # Fallback model hierarchy
        self.fallback_models = {
            "text-embedding-3-large": "text-embedding-3-small",
            "text-embedding-3-small": "text-embedding-ada-002",
            "text-embedding-ada-002": "text-embedding-005",
            "text-embedding-005": "text-multilingual-embedding-002",
            "text-multilingual-embedding-002": "multilingual-e5-large",
            "multilingual-e5-large": "gemini-embedding-001",
            "gemini-embedding-001": "text-embedding-3-small"
        }

    def initialize_embedding_model(self,
                                   model_name: str = "text-embedding-3-large",
                                   max_fallbacks: int = 3) -> Optional[str]:
        """
        Initialize the embedding model with fallback support.

        Args:
            model_name: The primary embedding model to use
            max_fallbacks: Maximum number of fallback attempts

        Returns:
            The successfully initialized model name, or None if all attempts fail
        """
        current_model = model_name
        attempts = 0

        while attempts <= max_fallbacks:
            try:
                logger.info(
                    f"Attempting to initialize model: {current_model} (attempt {attempts + 1})")

                if current_model.startswith("text-embedding"):
                    # Initialize OpenAI client
                    if not self.openai_client:
                        api_key = os.getenv("OPENAI_API_KEY")
                        base_url = os.getenv("OPENAI_BASE_URL")

                        if not api_key:
                            raise ValueError(
                                "OPENAI_API_KEY environment variable not set")

                        self.openai_client = OpenAI(
                            api_key=api_key,
                            base_url=base_url
                        )

                    # Test the connection
                    test_response = self.openai_client.embeddings.create(
                        model=current_model,
                        input=["test"]
                    )

                    logger.info(
                        f"Successfully initialized OpenAI model: {current_model}")
                    return current_model

                elif current_model.startswith("gemini"):
                    # Initialize Google client
                    if not self.google_initialized:
                        api_key = os.getenv("GOOGLE_API_KEY")

                        if not api_key:
                            raise ValueError(
                                "GOOGLE_API_KEY environment variable not set")

                        self.google_client = genai.Client(api_key=api_key)
                        self.google_initialized = True

                    # Test the connection
                    test_result = self.google_client.models.embed_content(
                        model=current_model,
                        contents=["test"]
                    )

                    logger.info(
                        f"Successfully initialized Google model: {current_model}")
                    return current_model

                else:
                    raise ValueError(
                        f"Invalid embedding model: {current_model}")

            except Exception as e:
                logger.warning(
                    f"Failed to initialize model {current_model}: {e}")

                # Try fallback model
                if current_model in self.fallback_models and attempts < max_fallbacks:
                    fallback_model = self.fallback_models[current_model]
                    logger.info(f"Trying fallback model: {fallback_model}")
                    current_model = fallback_model
                    attempts += 1
                    continue
                else:
                    logger.error(
                        "No more fallback models available. All attempts failed.")
                    return None

        logger.error(f"Exceeded maximum fallback attempts ({max_fallbacks})")
        return None

    def _create_embeddings_batch(self,
                                 chunks: List[str],
                                 model_name: str,
                                 max_retries: int) -> Optional[List[List[float]]]:
        """
        Create embeddings for a batch of chunks.

        Args:
            chunks: List of text chunks to embed, text chunks are strings that contain the summary and the text of the chunk with format: "Summary: <summary> Text: <text>"
            model_name: The embedding model to use
            max_retries: Maximum number of retry attempts

        Returns:
            List of embedding vectors for the batch, or None if failed
        """

        if not model_name:
            logger.error("Model name is required")
            return None

        for attempt in range(1, max_retries + 1):
            try:
                if model_name.startswith("text-embedding"):
                    if not self.openai_client:
                        raise RuntimeError("OpenAI client not initialized")

                    response = self.openai_client.embeddings.create(
                        model=model_name,
                        input=chunks
                    )

                    embeddings = [item.embedding for item in response.data]
                    return embeddings

                elif model_name.startswith("gemini"):
                    if not self.google_client:
                        raise RuntimeError("Google client not initialized")

                    result = self.google_client.models.embed_content(
                        model=model_name,
                        contents=chunks
                    )

                    # Extract the values from each embedding object
                    embeddings = [embedding.values for embedding in result.embeddings]
                    return embeddings

                else:
                    raise ValueError(f"Unknown embedding model: {model_name}")

            except Exception as e:
                logger.warning(
                    f"[Model: {model_name}, Attempt {attempt}] Error creating batch embeddings: {e}")
                if attempt < max_retries:
                    time.sleep(1)  # Wait before retrying
                else:
                    logger.error(
                        f"Failed to create batch embeddings after {max_retries} attempts")
                    return None

        return None

    def _is_model_initialized(self, model_name: str) -> bool:
        """
        Check if the specified model is properly initialized.

        Args:
            model_name: The model name to check

        Returns:
            True if the model is initialized, False otherwise
        """
        if model_name.startswith("text-embedding"):
            return self.openai_client is not None
        elif model_name.startswith("gemini"):
            return self.google_initialized
        else:
            return False

    def get_unembedded_chunks_by_user(self, user_id: str) -> List[Chunks]:
        """
        Get all chunks for a specific user where vector_id is empty or null.

        Args:
            user_id: MongoDB ObjectId string of the user

        Returns:
            List of Chunks objects that need embedding
        """
        try:
            # Convert string to ObjectId if needed
            if isinstance(user_id, str):
                user_object_id = ObjectId(user_id)
            else:
                user_object_id = user_id

            # Query chunks where vector_id is None or empty string
            chunks = Chunks.objects(
                user=user_object_id,
                vector_id__in=[None, ""]
            )

            logger.info(
                f"Found {len(chunks)} unembedded chunks for user {user_id}")
            return list(chunks)

        except Exception as e:
            logger.error(
                f"Error querying unembedded chunks for user {user_id}: {e}")
            return []

    def group_chunks_by_namespace(self, chunks: List[Chunks]) -> Dict[str, List[Chunks]]:
        """
        Group chunks by their namespace field.

        Args:
            chunks: List of Chunks objects

        Returns:
            Dictionary mapping namespace to list of chunks
        """
        namespace_groups = {}

        for chunk in chunks:
            namespace = chunk.namespace
            if namespace not in namespace_groups:
                namespace_groups[namespace] = []
            namespace_groups[namespace].append(chunk)

        logger.info(
            f"Grouped {len(chunks)} chunks into {len(namespace_groups)} namespaces: {list(namespace_groups.keys())}")

        for namespace, group_chunks in namespace_groups.items():
            logger.info(
                f"  Namespace '{namespace}': {len(group_chunks)} chunks")

        return namespace_groups

    def initialize_pinecone_client(self) -> bool:
        """
        Initialize Pinecone client.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if self.pinecone_client is not None:
                logger.info("Pinecone client already initialized")
                return True

            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                raise ValueError(
                    "PINECONE_API_KEY environment variable not set")

            self.pinecone_client = Pinecone(api_key=api_key)
            logger.info("Successfully initialized Pinecone client")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {e}")
            return False

    def ensure_pinecone_index_exists(self, index_name: str, dimension: int = 1536) -> bool:
        """
        Ensure Pinecone index exists, create if it doesn't.

        Args:
            index_name: Name of the Pinecone index
            dimension: Vector dimension (default: 1536 for text-embedding-3-small)

        Returns:
            True if index exists or was created successfully
        """
        try:
            if not self.pinecone_client:
                if not self.initialize_pinecone_client():
                    return False

            # Check if index exists
            existing_indexes = self.pinecone_client.list_indexes()
            index_names = [idx.name for idx in existing_indexes]

            if index_name in index_names:
                logger.info(f"Pinecone index '{index_name}' already exists")
                return True

            # Create index if it doesn't exist
            logger.info(
                f"Creating Pinecone index '{index_name}' with dimension {dimension}")
            self.pinecone_client.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )

            logger.info(f"Successfully created Pinecone index '{index_name}'")
            return True

        except Exception as e:
            logger.error(
                f"Error ensuring Pinecone index '{index_name}' exists: {e}")
            return False

    def prepare_embedding_text(self, chunk: Chunks) -> str:
        """
        Combine chunk content and summary for embedding.

        Args:
            chunk: Chunks object from MongoDB

        Returns:
            Combined text string ready for embedding
        """
        summary = chunk.summary.strip() if chunk.summary else ""
        content = chunk.content.strip() if chunk.content else ""

        if summary and content:
            combined_text = f"Summary: {summary}\n\nContent: {content}"
        elif content:
            combined_text = f"Content: {content}"
        elif summary:
            combined_text = f"Summary: {summary}"
        else:
            combined_text = ""

        return combined_text

    def create_embeddings_for_chunks(self, chunks: List[Chunks], model_name: str = "text-embedding-3-small") -> Dict[str, List[float]]:
        """
        Generate embeddings for a batch of chunks.

        Args:
            chunks: List of Chunks objects
            model_name: Embedding model to use (default: text-embedding-3-small)

        Returns:
            Dict mapping chunk_id to embedding vector
        """
        if not chunks:
            return {}

        try:
            # Prepare texts for embedding
            texts_for_embedding = []
            chunk_ids = []

            for chunk in chunks:
                text = self.prepare_embedding_text(chunk)
                if text.strip():  # Only process non-empty texts
                    texts_for_embedding.append(text)
                    chunk_ids.append(str(chunk.id))

            if not texts_for_embedding:
                logger.warning("No valid texts found for embedding")
                return {}

            logger.info(
                f"Creating embeddings for {len(texts_for_embedding)} chunks using model: {model_name}")

            # Generate embeddings using existing method
            embeddings = self._create_embeddings_batch(
                chunks=texts_for_embedding,
                model_name=model_name,
                max_retries=3
            )

            if not embeddings:
                logger.error("Failed to create embeddings")
                return {}

            # Create mapping of chunk_id to embedding
            chunk_embeddings = {}
            for chunk_id, embedding in zip(chunk_ids, embeddings):
                chunk_embeddings[chunk_id] = embedding

            logger.info(
                f"Successfully created {len(chunk_embeddings)} embeddings")
            return chunk_embeddings

        except Exception as e:
            logger.error(f"Error creating embeddings for chunks: {e}")
            return {}

    def prepare_pinecone_vectors(self, chunks: List[Chunks], chunk_embeddings: Dict[str, List[float]]) -> List[Dict]:
        """
        Prepare vector data with metadata for Pinecone.

        Args:
            chunks: List of Chunks objects
            chunk_embeddings: Dict mapping chunk_id to embedding vector

        Returns:
            List of vector dictionaries ready for Pinecone upsert
        """
        vectors = []

        for chunk in chunks:
            chunk_id = str(chunk.id)
            if chunk_id not in chunk_embeddings:
                continue

            # Prepare metadata
            metadata = {
                "user_id": str(chunk.user.id),
                "document_id": str(chunk.document.id),
                "chunk_index": chunk.chunk_index,
                "file_name": chunk.file_name,
                "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                "summary_preview": chunk.summary[:200] + "..." if len(chunk.summary) > 200 else chunk.summary,
                "chunking_method": chunk.chunking_method or "token",
                "created_at": chunk.created_at.isoformat() if chunk.created_at else ""
            }

            vector_data = {
                "id": chunk_id,  # Use MongoDB chunk._id as Pinecone vector ID
                "values": chunk_embeddings[chunk_id],
                "metadata": metadata
            }

            vectors.append(vector_data)

        logger.info(f"Prepared {len(vectors)} vectors for Pinecone upsert")
        return vectors

    def upsert_to_pinecone_namespace(self, vectors: List[Dict], namespace: str, index_name: str = "chatbot-vectors") -> List[str]:
        """
        Upload vectors to specific Pinecone namespace.

        Args:
            vectors: List of vector dictionaries
            namespace: Pinecone namespace to upsert to
            index_name: Pinecone index name

        Returns:
            List of successfully uploaded vector IDs
        """
        try:
            if not vectors:
                logger.warning("No vectors to upsert")
                return []

            if not self.pinecone_client:
                if not self.initialize_pinecone_client():
                    return []

            # Ensure index exists
            if not self.ensure_pinecone_index_exists(index_name):
                return []

            # Get index
            index = self.pinecone_client.Index(index_name)

            logger.info(
                f"Upserting {len(vectors)} vectors to Pinecone namespace '{namespace}' in index '{index_name}'")

            # Upsert vectors in batches (Pinecone recommends batches of 100)
            batch_size = 100
            successful_ids = []

            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]

                try:
                    upsert_response = index.upsert(
                        vectors=batch,
                        namespace=namespace
                    )

                    # Extract successful IDs from batch
                    batch_ids = [vector["id"] for vector in batch]
                    successful_ids.extend(batch_ids)

                    logger.info(
                        f"Successfully upserted batch {i//batch_size + 1}: {len(batch)} vectors")

                except Exception as e:
                    logger.error(
                        f"Failed to upsert batch {i//batch_size + 1}: {e}")
                    continue

            logger.info(
                f"Successfully upserted {len(successful_ids)}/{len(vectors)} vectors to Pinecone")
            return successful_ids

        except Exception as e:
            logger.error(
                f"Error upserting vectors to Pinecone namespace '{namespace}': {e}")
            return []

    def update_chunks_with_vector_ids(self, successful_vector_ids: List[str]) -> int:
        """
        Update MongoDB chunks with Pinecone vector IDs.

        Args:
            successful_vector_ids: List of chunk IDs that were successfully uploaded to Pinecone

        Returns:
            Count of successfully updated chunks
        """
        try:
            if not successful_vector_ids:
                logger.warning("No vector IDs to update")
                return 0

            updated_count = 0

            for chunk_id in successful_vector_ids:
                try:
                    # Find and update the chunk
                    chunk = Chunks.objects(id=chunk_id).first()
                    if chunk:
                        chunk.vector_id = chunk_id  # Use the chunk's own ID as vector_id
                        chunk.save()
                        updated_count += 1
                        logger.debug(
                            f"Updated chunk {chunk_id} with vector_id")
                    else:
                        logger.warning(f"Chunk with ID {chunk_id} not found")

                except Exception as e:
                    logger.error(f"Failed to update chunk {chunk_id}: {e}")
                    continue

            logger.info(
                f"Successfully updated {updated_count}/{len(successful_vector_ids)} chunks with vector IDs")
            return updated_count

        except Exception as e:
            logger.error(f"Error updating chunks with vector IDs: {e}")
            return 0

    def process_user_embeddings_by_namespace(self,
                                             user_id: str,
                                             embedding_model: str = "text-embedding-3-small",
                                             pinecone_index: str = "chatbot-vectors",
                                             batch_size: int = 50) -> Dict:
        """
        Main function: process all unembedded chunks for user, grouped by namespace.

        Args:
            user_id: MongoDB ObjectId string of the user
            embedding_model: Model to use for embeddings (text-embedding-3-small or gemini-embedding-001)
            pinecone_index: Pinecone index name
            batch_size: Number of chunks to process per batch

        Returns:
            Processing statistics and results
        """
        start_time = time.time()

        results = {
            "success": False,
            "user_id": user_id,
            "embedding_model": embedding_model,
            "pinecone_index": pinecone_index,
            "total_chunks_found": 0,
            "total_chunks_processed": 0,
            "total_chunks_embedded": 0,
            "total_chunks_updated": 0,
            "namespaces_processed": 0,
            "namespace_results": {},
            "processing_time": 0,
            "errors": []
        }

        try:
            logger.info("=" * 80)
            logger.info("🚀 STARTING USER EMBEDDING PROCESSING")
            logger.info("=" * 80)
            logger.info(f"👤 User ID: {user_id}")
            logger.info(f"🤖 Embedding Model: {embedding_model}")
            logger.info(f"📊 Pinecone Index: {pinecone_index}")
            logger.info(f"📦 Batch Size: {batch_size}")

            # Initialize embedding model
            if not self.initialize_embedding_model(embedding_model):
                error_msg = f"Failed to initialize embedding model: {embedding_model}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
                return results

            # Initialize Pinecone
            if not self.initialize_pinecone_client():
                error_msg = "Failed to initialize Pinecone client"
                results["errors"].append(error_msg)
                logger.error(error_msg)
                return results

            # Step 1: Get all unembedded chunks for user
            logger.info("\n📋 Step 1: Getting unembedded chunks...")
            chunks = self.get_unembedded_chunks_by_user(user_id)
            results["total_chunks_found"] = len(chunks)

            if not chunks:
                logger.info("✅ No unembedded chunks found for this user")
                results["success"] = True
                results["processing_time"] = time.time() - start_time
                return results

            # Step 2: Group chunks by namespace
            logger.info("\n🏷️  Step 2: Grouping chunks by namespace...")
            namespace_groups = self.group_chunks_by_namespace(chunks)

            # Step 3: Process each namespace
            logger.info(
                f"\n🔄 Step 3: Processing {len(namespace_groups)} namespaces...")

            for namespace, namespace_chunks in namespace_groups.items():
                namespace_start_time = time.time()

                logger.info(
                    f"\n--- Processing Namespace: '{namespace}' ({len(namespace_chunks)} chunks) ---")

                namespace_result = {
                    "chunks_found": len(namespace_chunks),
                    "chunks_embedded": 0,
                    "chunks_updated": 0,
                    "processing_time": 0,
                    "success": False,
                    "errors": []
                }

                try:
                    # Process chunks in batches
                    for i in range(0, len(namespace_chunks), batch_size):
                        batch = namespace_chunks[i:i + batch_size]
                        batch_num = i // batch_size + 1

                        logger.info(
                            f"  Processing batch {batch_num}: {len(batch)} chunks")

                        # Step 3a: Create embeddings
                        chunk_embeddings = self.create_embeddings_for_chunks(
                            batch, embedding_model)
                        if not chunk_embeddings:
                            error_msg = f"Failed to create embeddings for batch {batch_num} in namespace '{namespace}'"
                            namespace_result["errors"].append(error_msg)
                            logger.error(error_msg)
                            continue

                        # Step 3b: Prepare vectors for Pinecone
                        vectors = self.prepare_pinecone_vectors(
                            batch, chunk_embeddings)
                        if not vectors:
                            error_msg = f"Failed to prepare vectors for batch {batch_num} in namespace '{namespace}'"
                            namespace_result["errors"].append(error_msg)
                            logger.error(error_msg)
                            continue

                        # Step 3c: Upsert to Pinecone
                        successful_vector_ids = self.upsert_to_pinecone_namespace(
                            vectors, namespace, pinecone_index)
                        namespace_result["chunks_embedded"] += len(
                            successful_vector_ids)

                        # Step 3d: Update MongoDB
                        updated_count = self.update_chunks_with_vector_ids(
                            successful_vector_ids)
                        namespace_result["chunks_updated"] += updated_count

                        logger.info(
                            f"  ✅ Batch {batch_num}: {len(successful_vector_ids)} embedded, {updated_count} updated")

                    # Namespace completion
                    namespace_result["processing_time"] = time.time(
                    ) - namespace_start_time
                    namespace_result["success"] = namespace_result["chunks_updated"] > 0

                    if namespace_result["success"]:
                        logger.info(
                            f"✅ Namespace '{namespace}' completed: {namespace_result['chunks_updated']}/{namespace_result['chunks_found']} chunks processed")
                        results["namespaces_processed"] += 1
                    else:
                        logger.warning(
                            f"⚠️  Namespace '{namespace}' completed with issues")

                except Exception as e:
                    error_msg = f"Error processing namespace '{namespace}': {e}"
                    namespace_result["errors"].append(error_msg)
                    logger.error(error_msg)

                results["namespace_results"][namespace] = namespace_result
                results["total_chunks_processed"] += namespace_result["chunks_found"]
                results["total_chunks_embedded"] += namespace_result["chunks_embedded"]
                results["total_chunks_updated"] += namespace_result["chunks_updated"]

            # Final results
            results["processing_time"] = time.time() - start_time
            results["success"] = results["total_chunks_updated"] > 0

            # Summary logging
            logger.info("\n" + "=" * 80)
            logger.info("🏁 EMBEDDING PROCESSING COMPLETE")
            logger.info("=" * 80)
            logger.info(f"👤 User ID: {user_id}")
            logger.info(
                f"📋 Total chunks found: {results['total_chunks_found']}")
            logger.info(
                f"🤖 Total chunks embedded: {results['total_chunks_embedded']}")
            logger.info(
                f"💾 Total chunks updated: {results['total_chunks_updated']}")
            logger.info(
                f"🏷️  Namespaces processed: {results['namespaces_processed']}/{len(namespace_groups)}")
            logger.info(f"⏱️  Total time: {results['processing_time']:.2f}s")

            if results["success"]:
                logger.info(
                    "✅ SUCCESS: Embedding processing completed successfully!")
            else:
                logger.warning(
                    "⚠️  PARTIAL SUCCESS: Some issues occurred during processing")

            return results

        except Exception as e:
            error_msg = f"Critical error in embedding processing: {e}"
            results["errors"].append(error_msg)
            results["processing_time"] = time.time() - start_time
            logger.error(error_msg)
            return results
