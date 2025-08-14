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

# Transformers imports (with error handling for optional dependency)
try:
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModel
    from torch import Tensor
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    torch = None
    F = None
    AutoTokenizer = None
    AutoModel = None
    Tensor = None
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available. Install 'transformers' and 'torch' to use multilingual-e5-large model.")


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
        
        # Transformers models
        self.transformers_models = {}
        self.transformers_tokenizers = {}

        self.model_providers = {
            # OpenAI models
            "text-embedding-3-large": "openai",
            "text-embedding-3-small": "openai",
            "text-embedding-ada-002": "openai",

            # Google models
            "text-embedding-005": "google",
            "text-multilingual-embedding-002": "google",
            "gemini-embedding-001": "google",

            # Open-Source models
            "multilingual-e5-large": "other",
        }

        # Fallback model hierarchy
        self.fallback_models = {
            # OpenAI models
            "text-embedding-3-large": "text-embedding-3-small",
            "text-embedding-3-small": "text-embedding-ada-002",
            "text-embedding-ada-002": "gemini-embedding-001",

            # Gemini models
            "gemini-embedding-001": "text-embedding-3-small",
            "text-embedding-005": "text-multilingual-embedding-002", # not available
            "text-multilingual-embedding-002": "gemini-embedding-001", # not available

            # Open-Source models
            "multilingual-e5-large": "text-embedding-3-small", # very slow
        }

        # Model dimension mapping
        self.model_dimensions = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536,
            "text-embedding-005": 1536,
            "text-multilingual-embedding-002": 1536,
            "multilingual-e5-large": 1536,
            "gemini-embedding-001": 3072
        }

    def get_pinecone_index_for_model(self, embedding_model: str) -> str:
        """
        Get the appropriate Pinecone index name based on embedding model.
        Automatically determines provider and dimension to create the right index.
        
        Args:
            embedding_model: Name of the embedding model
            
        Returns:
            Pinecone index name with provider and dimension suffix
        """
        # Get model dimensions
        dimension = self.model_dimensions.get(embedding_model, 1536)
        
        # Determine provider based on model name
        if "gemini" in embedding_model.lower() or "google" in embedding_model.lower():
            provider = "google"
        else:
            provider = "openai"
        
        # Return index name with dimension
        index_name = f"chatbot-vectors-{provider}-{dimension}"
        logger.info(f"Selected Pinecone index '{index_name}' for model '{embedding_model}' (dimension: {dimension})")
        return index_name

    # def list_all_pinecone_indexes(self) -> Dict[str, Dict]:
    #     """
    #     List all Pinecone indexes with their details for debugging and management.
        
    #     Returns:
    #         Dictionary mapping index names to their details
    #     """
    #     try:
    #         if not self.pinecone_client:
    #             if not self.initialize_pinecone_client():
    #                 return {}
            
    #         indexes = self.pinecone_client.list_indexes()
    #         index_details = {}
            
    #         for idx in indexes:
    #             try:
    #                 # Get index stats to determine dimension
    #                 index = self.pinecone_client.Index(idx.name)
    #                 stats = index.describe_index_stats()
    #                 dimension = stats.dimension if hasattr(stats, 'dimension') else 'unknown'
                    
    #                 index_details[idx.name] = {
    #                     'name': idx.name,
    #                     'dimension': dimension,
    #                     'metric': stats.metric if hasattr(stats, 'metric') else 'unknown',
    #                     'status': 'ready' if idx.status.state == 'Ready' else idx.status.state
    #                 }
    #             except Exception as e:
    #                 logger.warning(f"Could not get details for index {idx.name}: {e}")
    #                 index_details[idx.name] = {
    #                     'name': idx.name,
    #                     'dimension': 'unknown',
    #                     'metric': 'unknown',
    #                     'status': 'error'
    #                 }
            
    #         return index_details
            
    #     except Exception as e:
    #         logger.error(f"Failed to list Pinecone indexes: {e}")
    #         return {}

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

                # Determine provider from model_providers dictionary
                if current_model not in self.model_providers:
                    raise ValueError(
                        f"Unknown embedding model: {current_model}")
                
                provider = self.model_providers[current_model]

                if provider == "openai":
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

                elif provider == "google":
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

                elif provider == "other":
                    # Handle open-source models (currently supports multilingual-e5-large)
                    if current_model == "multilingual-e5-large":
                        if not TRANSFORMERS_AVAILABLE:
                            raise ValueError(
                                "Transformers not available. Install 'transformers' and 'torch' to use multilingual-e5-large model.")
                        
                        # Initialize multilingual-e5-large model
                        if current_model not in self.transformers_models:
                            logger.info(f"Loading {current_model} model...")
                            
                            try:
                                tokenizer = AutoTokenizer.from_pretrained('intfloat/multilingual-e5-large')
                                model = AutoModel.from_pretrained('intfloat/multilingual-e5-large')
                                
                                self.transformers_tokenizers[current_model] = tokenizer
                                self.transformers_models[current_model] = model
                                
                                logger.info(f"Successfully loaded {current_model} model")
                            except Exception as e:
                                raise ValueError(f"Failed to load {current_model}: {e}")
                        
                        # Test the model with a simple embedding
                        test_input = ["query: test"]
                        tokenizer = self.transformers_tokenizers[current_model]
                        model = self.transformers_models[current_model]
                        
                        batch_dict = tokenizer(test_input, max_length=512, padding=True, truncation=True, return_tensors='pt')
                        with torch.no_grad():
                            outputs = model(**batch_dict)
                            embeddings = self._average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
                            embeddings = F.normalize(embeddings, p=2, dim=1)
                        
                        logger.info(f"Successfully initialized {current_model} model")
                        return current_model
                    else:
                        raise ValueError(f"Open-source model {current_model} not yet implemented")
                
                else:
                    raise ValueError(
                        f"Unknown provider '{provider}' for model: {current_model}")

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
                # Determine provider from model_providers dictionary
                if model_name not in self.model_providers:
                    raise ValueError(f"Unknown embedding model: {model_name}")
                
                provider = self.model_providers[model_name]

                if provider == "openai":
                    if not self.openai_client:
                        raise RuntimeError("OpenAI client not initialized")

                    response = self.openai_client.embeddings.create(
                        model=model_name,
                        input=chunks
                    )

                    embeddings = [item.embedding for item in response.data]
                    return embeddings

                elif provider == "google":
                    if not self.google_client:
                        raise RuntimeError("Google client not initialized")

                    result = self.google_client.models.embed_content(
                        model=model_name,
                        contents=chunks
                    )

                    # Extract the values from each embedding object
                    embeddings = [embedding.values for embedding in result.embeddings]
                    return embeddings

                elif provider == "other":
                    if model_name == "multilingual-e5-large":
                        if model_name not in self.transformers_models:
                            raise RuntimeError(f"{model_name} model not initialized")
                        
                        tokenizer = self.transformers_tokenizers[model_name]
                        model = self.transformers_models[model_name]
                        
                        # Preprocess chunks for multilingual-e5-large
                        # Add "query: " prefix as recommended by the model documentation
                        processed_chunks = [f"query: {chunk}" for chunk in chunks]
                        
                        # Tokenize the input texts
                        batch_dict = tokenizer(processed_chunks, max_length=512, padding=True, truncation=True, return_tensors='pt')
                        
                        with torch.no_grad():
                            outputs = model(**batch_dict)
                            embeddings = self._average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
                            # Normalize embeddings
                            embeddings = F.normalize(embeddings, p=2, dim=1)
                        
                        # Convert to list of lists for consistency with other providers
                        embeddings_list = embeddings.tolist()
                        return embeddings_list
                    else:
                        raise ValueError(f"Open-source model {model_name} not yet implemented")
                
                else:
                    raise ValueError(f"Unknown provider '{provider}' for model: {model_name}")

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
        if model_name not in self.model_providers:
            return False
        
        provider = self.model_providers[model_name]
        
        if provider == "openai":
            return self.openai_client is not None
        elif provider == "google":
            return self.google_initialized
        elif provider == "other":
            if model_name == "multilingual-e5-large":
                return model_name in self.transformers_models
            else:
                return False
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

    def ensure_pinecone_index_exists(self, index_name: str, embedding_model: str = "text-embedding-3-small") -> bool:
        """
        Ensure Pinecone index exists, create if it doesn't.

        Args:
            index_name: Name of the Pinecone index
            embedding_model: Embedding model to determine correct dimension

        Returns:
            True if index exists or was created successfully
        """
        try:
            if not self.pinecone_client:
                if not self.initialize_pinecone_client():
                    return False

            # Get the correct dimension for the model
            dimension = self.model_dimensions.get(embedding_model, 1536)  # Default to 1536 if model not found

            # Check if index exists
            existing_indexes = self.pinecone_client.list_indexes()
            index_names = [idx.name for idx in existing_indexes]

            if index_name in index_names:
                logger.info(f"Pinecone index '{index_name}' already exists")
                return True

            # Create index if it doesn't exist
            logger.info(f"Creating Pinecone index '{index_name}' with dimension {dimension} for model {embedding_model}")
            self.pinecone_client.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )

            logger.info(f"Successfully created Pinecone index '{index_name}'")
            return True

        except Exception as e:
            logger.error(f"Error ensuring Pinecone index '{index_name}' exists: {e}")
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

    def upsert_to_pinecone_namespace(self, vectors: List[Dict], namespace: str, index_name: str = "chatbot-vectors", embedding_model: str = "text-embedding-3-small") -> List[str]:
        """
        Upload vectors to specific Pinecone namespace.

        Args:
            vectors: List of vector dictionaries
            namespace: Pinecone namespace to upsert to
            index_name: Pinecone index name
            embedding_model: Embedding model to determine correct dimension

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

            # Ensure index exists with correct dimensions
            if not self.ensure_pinecone_index_exists(index_name, embedding_model):
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

    def delete_namespace(self, index_name: str, namespace: str) -> bool:
        """
        Delete all vectors in a Pinecone namespace for the given index.
        Safe to call even if namespace is empty or missing.
        """
        try:
            if not self.pinecone_client:
                if not self.initialize_pinecone_client():
                    return False
            index = self.pinecone_client.Index(index_name)
            index.delete(deleteAll=True, namespace=namespace)
            logger.info(f"Deleted Pinecone namespace '{namespace}' in index '{index_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Pinecone namespace '{namespace}' in index '{index_name}': {e}")
            return False

    def re_embed_document_for_chatbots(self, document_id: str, embedding_model: str = "text-embedding-3-small", batch_size: int = 50) -> Dict:
        """
        Re-embed existing document chunks for all chatbots that use this document
        This handles the case where a document is shared between multiple chatbots
        Each chatbot gets its own Pinecone namespace with the same document content
        
        Args:
            document_id: MongoDB ObjectId string of the document
            embedding_model: Model to use for embeddings  
            batch_size: Number of chunks to process per batch
            
        Returns:
            Processing statistics and results
        """
        start_time = time.time()
        
        results = {
            "success": False,
            "document_id": document_id,
            "embedding_model": embedding_model,
            "chatbots_processed": 0,
            "total_chunks_embedded": 0,
            "chatbot_results": {},
            "processing_time": 0,
            "errors": []
        }
        
        try:
            from db_service import Documents, ChatbotDocumentsMapper, Chunks
            
            # Get the document
            document = Documents.objects(id=document_id).first()
            if not document:
                error_msg = f"Document not found: {document_id}"
                results["errors"].append(error_msg)
                return results
                
            logger.info(f"🔄 Re-embedding document '{document.file_name}' for multiple chatbots")
            
            # Get all chatbots that use this document
            mappings = ChatbotDocumentsMapper.objects(document=document)
            if not mappings:
                error_msg = f"No chatbot mappings found for document {document_id}"
                results["errors"].append(error_msg)
                return results
                
            logger.info(f"📋 Found {len(mappings)} chatbots using this document")
            
            # Initialize embedding model and Pinecone
            if not self.initialize_embedding_model(embedding_model):
                error_msg = f"Failed to initialize embedding model: {embedding_model}"
                results["errors"].append(error_msg)
                return results
                
            pinecone_index = self.get_pinecone_index_for_model(embedding_model)
            if not self.initialize_pinecone_client():
                error_msg = "Failed to initialize Pinecone client"
                results["errors"].append(error_msg)
                return results
                
            if not self.ensure_pinecone_index_exists(pinecone_index, embedding_model):
                error_msg = f"Failed to ensure Pinecone index exists: {pinecone_index}"
                results["errors"].append(error_msg)
                return results
            
            # Get all chunks for this document
            chunks = list(Chunks.objects(document=document))
            if not chunks:
                error_msg = f"No chunks found for document {document_id}"
                results["errors"].append(error_msg)
                return results
                
            logger.info(f"📦 Found {len(chunks)} chunks to re-embed")
            
            # Process each chatbot's namespace
            for mapping in mappings:
                chatbot = mapping.chatbot
                namespace = chatbot.namespace
                
                logger.info(f"\n🤖 Processing chatbot '{chatbot.name}' (namespace: {namespace})")
                
                chatbot_result = {
                    "chunks_embedded": 0,
                    "success": False,
                    "errors": []
                }
                
                try:
                    # Process chunks in batches
                    for i in range(0, len(chunks), batch_size):
                        batch = chunks[i:i + batch_size]
                        batch_num = i // batch_size + 1
                        
                        logger.info(f"  Processing batch {batch_num}: {len(batch)} chunks")
                        
                        # Create embeddings
                        chunk_embeddings = self.create_embeddings_for_chunks(batch, embedding_model)
                        if not chunk_embeddings:
                            error_msg = f"Failed to create embeddings for batch {batch_num}"
                            chatbot_result["errors"].append(error_msg)
                            logger.error(error_msg)
                            continue
                            
                        # Upload to Pinecone with chatbot's namespace
                        vector_ids = self.upload_embeddings_to_pinecone(
                            chunk_embeddings, batch, pinecone_index, namespace
                        )
                        
                        if vector_ids:
                            # Update chunks with new vector IDs (each chatbot might have different vector IDs)
                            self.update_chunks_with_vector_ids(batch, vector_ids)
                            chatbot_result["chunks_embedded"] += len(vector_ids)
                            results["total_chunks_embedded"] += len(vector_ids)
                            logger.info(f"  ✅ Embedded {len(vector_ids)} chunks in namespace '{namespace}'")
                        else:
                            error_msg = f"Failed to upload embeddings to Pinecone for batch {batch_num}"
                            chatbot_result["errors"].append(error_msg)
                            logger.error(error_msg)
                    
                    if chatbot_result["chunks_embedded"] > 0:
                        chatbot_result["success"] = True
                        logger.info(f"✅ Successfully re-embedded {chatbot_result['chunks_embedded']} chunks for chatbot '{chatbot.name}'")
                    
                except Exception as e:
                    error_msg = f"Error processing chatbot '{chatbot.name}': {str(e)}"
                    chatbot_result["errors"].append(error_msg)
                    logger.error(error_msg)
                
                results["chatbot_results"][chatbot.name] = chatbot_result
                if chatbot_result["success"]:
                    results["chatbots_processed"] += 1
            
            # Mark document as processed
            document.status = "processed"
            document.save()
            
            if results["chatbots_processed"] > 0:
                results["success"] = True
                logger.info(f"🎉 Successfully re-embedded document for {results['chatbots_processed']} chatbots")
            
        except Exception as e:
            error_msg = f"Re-embedding failed: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        results["processing_time"] = time.time() - start_time
        return results

    def embed_document_for_chatbot(self, document_id: str, chatbot, embedding_model: str, batch_size: int = 50) -> Dict:
        """
        Re-embed a single document's chunks specifically for one chatbot and upsert to that chatbot's namespace.
        This is idempotent (upsert) and provider-aware.
        """
        results = {
            "success": False,
            "document_id": document_id,
            "chatbot_id": str(getattr(chatbot, 'id', chatbot)),
            "chatbot_namespace": getattr(chatbot, 'namespace', ''),
            "embedding_model": embedding_model,
            "chunks_embedded": 0,
            "processing_time": 0,
            "errors": []
        }
        import time
        start_time = time.time()
        try:
            from db_service import Documents, Chunks
            # Find document
            document = Documents.objects(id=document_id).first()
            if not document:
                results["errors"].append("Document not found")
                return results
            namespace = getattr(chatbot, 'namespace', None)
            if not namespace:
                results["errors"].append("Chatbot namespace missing")
                return results
            # Initialize model and pinecone
            if not self.initialize_embedding_model(embedding_model):
                results["errors"].append(f"Failed to initialize embedding model {embedding_model}")
                return results
            pinecone_index = self.get_pinecone_index_for_model(embedding_model)
            if not self.initialize_pinecone_client():
                results["errors"].append("Failed to initialize Pinecone client")
                return results
            if not self.ensure_pinecone_index_exists(pinecone_index, embedding_model):
                results["errors"].append(f"Failed to ensure Pinecone index {pinecone_index}")
                return results
            # Load chunks for document
            chunks = list(Chunks.objects(document=document))
            if not chunks:
                results["errors"].append("No chunks found for document")
                return results
            # Create embeddings in batches
            total_embedded = 0
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                chunk_embeddings = self.create_embeddings_for_chunks(batch, embedding_model)
                if not chunk_embeddings:
                    results["errors"].append(f"Failed to create embeddings for batch {i//batch_size+1}")
                    continue
                vectors = self.prepare_pinecone_vectors(batch, chunk_embeddings)
                successful_vector_ids = self.upsert_to_pinecone_namespace(vectors, namespace, pinecone_index, embedding_model)
                total_embedded += len(successful_vector_ids)
                # Keep chunk vector_id updated (idempotent)
                if successful_vector_ids:
                    self.update_chunks_with_vector_ids(successful_vector_ids)
            results["chunks_embedded"] = total_embedded
            results["success"] = total_embedded > 0
        except Exception as e:
            logger.error(f"Error in embed_document_for_chatbot: {e}")
            results["errors"].append(str(e))
        finally:
            results["processing_time"] = time.time() - start_time
        return results

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

            # Ensure index exists with correct dimensions for the embedding model
            if not self.ensure_pinecone_index_exists(pinecone_index, embedding_model):
                error_msg = f"Failed to ensure Pinecone index '{pinecone_index}' exists with correct dimensions for model '{embedding_model}'"
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
                            vectors, namespace, pinecone_index, embedding_model)
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
