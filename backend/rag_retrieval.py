#!/usr/bin/env python3
"""
RAG Retrieval Module - Retrieves relevant chunks from user's documents using semantic search
Automatically selects embedding model and Pinecone index based on user's choice in master pipeline
Uses the same embedding functions as document indexing for consistency
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pinecone import Pinecone
from bson import ObjectId
from db_service import ChatBots, Chunks
from embeddings import EmbeddingService
from LLM.search_rag_openai import search_rag as search_rag_openai
from LLM.search_rag_google import search_rag as search_rag_google

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGService:
    """
    Service class for RAG retrieval functionality
    Uses EmbeddingService for consistent embedding generation
    Automatically handles Pinecone index routing
    """

    model_providers = {
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

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.pinecone_client = None

    def initialize_embedding_client(self, embedding_model: str) -> bool:
        """
        Initialize the embedding client using EmbeddingService

        Args:
            embedding_model: The embedding model to initialize

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Use EmbeddingService for consistent initialization
            initialized_model = self.embedding_service.initialize_embedding_model(embedding_model)
            
            if initialized_model:
                logger.info(f"✅ Embedding client initialized for model: {initialized_model}")
                return True
            else:
                logger.error(f"Failed to initialize embedding model: {embedding_model}")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize embedding client for {embedding_model}: {e}")
            return False

    def initialize_pinecone_client(self) -> bool:
        """
        Initialize Pinecone client

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if not self.pinecone_client:
                api_key = os.getenv("PINECONE_API_KEY")
                if not api_key:
                    raise ValueError(
                        "PINECONE_API_KEY environment variable not set")

                self.pinecone_client = Pinecone(api_key=api_key)
                logger.info("✅ Pinecone client initialized")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {e}")
            return False

    def determine_pinecone_index(self, embedding_model: str) -> str:
        """
        Determine the correct Pinecone index based on embedding model
        Follows the same logic as master_pipeline.py

        Args:
            embedding_model: The embedding model being used

        Returns:
            The appropriate Pinecone index name
        """
        if "gemini" in embedding_model.lower():
            return "chatbot-vectors-google"
        else:
            return "chatbot-vectors-openai"

    def create_query_embedding(self, query: str, embedding_model: str) -> List[float]:
        """
        Generate embedding for the query using EmbeddingService
        Uses the same embedding generation pipeline as document indexing

        Args:
            query: The search query
            embedding_model: The embedding model to use

        Returns:
            List of float values representing the embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        try:
            # Use EmbeddingService for consistent embedding generation
            embeddings = self.embedding_service._create_embeddings_batch(
                chunks=[query],  # Pass query as single item list
                model_name=embedding_model,
                max_retries=3
            )
            
            if embeddings and len(embeddings) > 0:
                return embeddings[0]  # Return first (and only) embedding
            else:
                raise ValueError("Failed to generate query embedding")

        except Exception as e:
            logger.error(f"Failed to create query embedding: {e}")
            raise

    def query_pinecone(self, query_embedding: List[float], namespace: str,
                       pinecone_index: str, top_k: int) -> List[Dict]:
        """
        Query Pinecone for similar vectors

        Args:
            query_embedding: The query vector
            namespace: The user's namespace  
            pinecone_index: The Pinecone index to query
            top_k: Number of results to return

        Returns:
            List of match dictionaries with id and score

        Raises:
            Exception: If Pinecone query fails
        """
        try:
            # Get the index
            index = self.pinecone_client.Index(pinecone_index)

            # Query the index
            query_response = index.query(
                namespace=namespace,
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                include_values=False
            )

            # Convert matches to list of dicts for easier handling
            matches = []
            for match in query_response.matches:
                matches.append({
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata or {}
                })

            logger.info(
                f"Found {len(matches)} matches in Pinecone namespace '{namespace}'")
            return matches

        except Exception as e:
            logger.error(f"Failed to query Pinecone: {e}")
            raise

    def retrieve_chunks_from_mongodb(self, vector_ids: List[str]) -> List[Chunks]:
        """
        Retrieve full chunk data from MongoDB using vector IDs

        Args:
            vector_ids: List of Pinecone vector IDs (which are MongoDB ObjectIds)

        Returns:
            List of Chunks objects from MongoDB

        Raises:
            Exception: If MongoDB query fails
        """
        try:
            # Convert string IDs to ObjectIds for MongoDB query
            chunk_object_ids = []
            for vid in vector_ids:
                try:
                    chunk_object_ids.append(ObjectId(vid))
                except Exception as e:
                    logger.warning(f"Invalid ObjectId format: {vid}, skipping")
                    continue

            if not chunk_object_ids:
                logger.warning("No valid ObjectIds to query")
                return []

            # Query MongoDB chunks collection
            chunks = Chunks.objects(id__in=chunk_object_ids)
            chunks_list = list(chunks)

            logger.info(f"Retrieved {len(chunks_list)} chunks from MongoDB")
            return chunks_list

        except Exception as e:
            logger.error(f"Failed to retrieve chunks from MongoDB: {e}")
            raise

    def format_rag_results(self, chunks: List[Chunks], score_mapping: Dict[str, float]) -> str:
        """
        Format retrieved chunks for LLM consumption

        Args:
            chunks: List of Chunks objects from MongoDB
            score_mapping: Mapping of chunk ID to relevance score

        Returns:
            Formatted string containing chunk information
        """
        if not chunks:
            return "No relevant documents found for your query."

        results = []
        for i, chunk in enumerate(chunks):
            chunk_id = str(chunk.id)
            relevance_score = score_mapping.get(chunk_id, 0.0)

            # Format chunk information
            chunk_text = f"{i + 1}.\n\n"
            chunk_text += f"**Source File**: {chunk.file_name}\n"
            chunk_text += f"**Chunk Index**: {chunk.chunk_index + 1}\n"
            chunk_text += f"**Relevance Score**: {relevance_score:.3f}\n"
            chunk_text += f"**Chunking Method**: {chunk.chunking_method}\n\n"
            chunk_text += f"**Summary**: {chunk.summary}\n\n"
            chunk_text += f"**Content**: {chunk.content}\n\n"
            chunk_text += "---\n"

            results.append(chunk_text)

        final_result = "\n".join(results)
        logger.info(f"Formatted {len(chunks)} chunks for LLM consumption")
        return final_result

# OLD RAG SEARCH FUNCTION
# def rag_search(query: str, user_id: str, namespace: str, embedding_model: str, top_k: int = 5) -> str:
#     """
#     Main RAG search function that retrieves relevant document chunks for a user query
#     Now uses optimized search functions with Cohere reranking for better results

#     This function:
#     1. Auto-determines the correct Pinecone index and search function based on embedding model
#     2. Routes to either OpenAI or Google search pipeline with reranking
#     3. Returns formatted results with relevance scores and metadata

#     Args:
#         query: User's search query
#         user_id: MongoDB ObjectId string of the user
#         namespace: User's namespace (without user_id suffix, will be auto-appended)
#         embedding_model: Embedding model from master pipeline choice
#                         - "text-embedding-3-small" for OpenAI
#                         - "gemini-embedding-001" for Gemini
#         top_k: Number of most relevant chunks to return (default: 5, used as top_reranked)

#     Returns:
#         Formatted string containing relevant document chunks with:
#         - Source file names
#         - Content and summary previews  
#         - Cohere rerank scores
#         - Chunk metadata

#     Example:
#         >>> result = rag_search(
#         ...     query="What is the company policy on remote work?",
#         ...     user_id="507f1f77bcf86cd799439011", 
#         ...     namespace="company_docs",
#         ...     embedding_model="text-embedding-3-small"
#         ... )
#         >>> print(result)
#         1
#         ##ID: 64f7b2...
#         ##content_preview: "Company policy states..."
#         ##summary_preview: "Remote work guidelines..."
#         ##source_file: "employee_handbook.pdf"
#         ##rerank_score: 0.8945
#     """
#     logger.info("=" * 60)
#     logger.info("🔍 STARTING OPTIMIZED RAG SEARCH")
#     logger.info("=" * 60)
#     logger.info(f"📝 Query: {query}")
#     logger.info(f"👤 User ID: {user_id}")
#     logger.info(f"🏷️  Namespace: {namespace}")
#     logger.info(f"🤖 Embedding Model: {embedding_model}")
#     logger.info(f"📊 Top K: {top_k}")

#     try:
#         # Step 1: Use the namespace as-is since it already includes the user_id
#         # The namespace parameter already contains the user_id (e.g., "DeepSeekChatbot_689484a1d2513e61085cf246")
#         full_namespace = namespace
#         logger.info(f"🔗 Full namespace: {full_namespace}")
        
#         # Debug: Check if documents exist for this namespace
#         from db_service import Documents, Chunks
#         doc_count = Documents.objects(namespace=namespace).count()
#         chunk_count = Chunks.objects(namespace=namespace).count()
#         logger.info(f"🔍 Found {doc_count} documents and {chunk_count} chunks for namespace: {namespace}")

#         # Step 2: Auto-determine Pinecone index and route to correct search function
#         if "gemini" in embedding_model.lower():
#             # Use Google/Gemini search pipeline
#             pinecone_index = "chatbot-vectors-google"
#             logger.info(f"📊 Using Google/Gemini search pipeline with index: {pinecone_index}")
            
#             result = search_rag_google(
#                 query=query,
#                 namespace=full_namespace,
#                 index_name=pinecone_index,
#                 embedding_model=embedding_model,
#                 top_k=top_k * 2,  # Get more initial results for better reranking
#                 top_reranked=top_k  # Return the requested number after reranking
#             )
            
#         else:
#             # Use OpenAI search pipeline  
#             pinecone_index = "chatbot-vectors-openai"
#             logger.info(f"📊 Using OpenAI search pipeline with index: {pinecone_index}")
            
#             result = search_rag_openai(
#                 query=query,
#                 namespace=full_namespace,
#                 index_name=pinecone_index,
#                 embedding_model=embedding_model,
#                 top_k=top_k * 2,  # Get more initial results for better reranking
#                 top_reranked=top_k  # Return the requested number after reranking
#             )

#         logger.info("✅ RAG search completed successfully using optimized pipeline")
#         logger.info("=" * 60)

#         return result

#     except Exception as e:
#         error_msg = f"RAG search failed: {str(e)}"
#         logger.error(error_msg)
#         logger.error("=" * 60)
#         return f"Error retrieving relevant documents: {str(e)}"

# def rag_search(query: str, user_id: str, namespaces: list, embedding_model: str, top_k: int = 5) -> str:
#     """
#     Main RAG search function that retrieves relevant document chunks for a user query
#     Now supports multiple namespaces for searching across multiple document collections

#     Args:
#         query: User's search query
#         user_id: MongoDB ObjectId string of the user
#         namespaces: List of namespaces to search in (can be single string or list)
#         embedding_model: Embedding model from master pipeline choice
#         top_k: Number of most relevant chunks to return

#     Returns:
#         Formatted string containing relevant document chunks
#     """
#     logger.info("=" * 60)
#     logger.info("🔍 STARTING OPTIMIZED RAG SEARCH")
#     logger.info("=" * 60)
#     logger.info(f"📝 Query: {query}")
#     logger.info(f"👤 User ID: {user_id}")
#     logger.info(f"🏷️  Namespaces: {namespaces}")
#     logger.info(f"🤖 Embedding Model: {embedding_model}")
#     logger.info(f"📊 Top K: {top_k}")

#     try:
#         # Convert single namespace to list for consistency
#         if isinstance(namespaces, str):
#             namespaces = [namespaces]
        
#         # Use full namespaces for both MongoDB and Pinecone
#         full_namespaces = namespaces
        
#         logger.info(f"🔗 Full namespaces: {full_namespaces}")
        
#         # Debug: Check if documents exist for these namespaces
#         from db_service import Documents, Chunks
#         total_doc_count = 0
#         total_chunk_count = 0
        
#         for full_ns in full_namespaces:
#             doc_count = Documents.objects(namespace=full_ns).count()
#             chunk_count = Chunks.objects(namespace=full_ns).count()
#             total_doc_count += doc_count
#             total_chunk_count += chunk_count
#             logger.info(f"🔍 Found {doc_count} documents and {chunk_count} chunks for namespace: {full_ns}")
        
#         logger.info(f"📊 Total: {total_doc_count} documents and {total_chunk_count} chunks across all namespaces")

#         # Step 2: Auto-determine Pinecone index and route to correct search function
#         if "gemini" in embedding_model.lower():
#             # Use Google/Gemini search pipeline
#             pinecone_index = "chatbot-vectors-google"
#             logger.info(f"📊 Using Google/Gemini search pipeline with index: {pinecone_index}")
            
#             # Search each namespace and combine results
#             all_results = []
#             for full_namespace in full_namespaces:
#                 logger.info(f"🔍 Searching namespace: {full_namespace}")
#                 result = search_rag_google(
#                     query=query,
#                     namespace=full_namespace,
#                     index_name=pinecone_index,
#                     embedding_model=embedding_model,
#                     top_k=top_k * 2,
#                     top_reranked=top_k * 2
#                 )
                
#                 # Just append the result if it's not empty
#                 if result and result != "No relevant documents found for the query.":
#                     all_results.append(result)
            
#             # Simple combination - just join the results
#             if all_results:
#                 result = "\n\n".join(all_results)
#             else:
#                 result = "No relevant documents found for the query."
            
#         else:
#             # Use OpenAI search pipeline  
#             pinecone_index = "chatbot-vectors-openai"
#             logger.info(f"📊 Using OpenAI search pipeline with index: {pinecone_index}")
            
#             # Search each namespace and combine results
#             all_results = []
#             for full_namespace in full_namespaces:
#                 logger.info(f"🔍 Searching namespace: {full_namespace}")
#                 result = search_rag_openai(
#                     query=query,
#                     namespace=full_namespace,
#                     index_name=pinecone_index,
#                     embedding_model=embedding_model,
#                     top_k=top_k * 2,
#                     top_reranked=top_k * 2
#                 )
                
#                 # Just append the result if it's not empty
#                 if result and result != "No relevant documents found for the query.":
#                     all_results.append(result)
            
#             # Simple combination - just join the results
#             if all_results:
#                 result = "\n\n".join(all_results)
#             else:
#                 result = "No relevant documents found for the query."

#         logger.info("✅ RAG search completed successfully using optimized pipeline")
#         logger.info("=" * 60)

#         return result

#     except Exception as e:
#         error_msg = f"RAG search failed: {str(e)}"
#         logger.error(error_msg)
#         logger.error("=" * 60)
#         return f"Error retrieving relevant documents: {str(e)}"

def rag_search(query: str, user_id: str, namespaces: list, embedding_model_of_chatbot_caller: str, top_k: int = 5) -> str:
    """
    Main RAG search function that retrieves relevant document chunks for a user query
    Now supports multiple namespaces for searching across multiple document collections
    """
    logger.info("=" * 60)
    logger.info("🔍 STARTING OPTIMIZED RAG SEARCH")
    logger.info("=" * 60)
    logger.info(f"📝 Query: {query}")
    logger.info(f"👤 User ID: {user_id}")
    logger.info(f"🏷️  Namespaces: {namespaces}")
    logger.info(f"🤖 Embedding Model: {embedding_model_of_chatbot_caller}")
    logger.info(f"📊 Top K: {top_k}")

    try:
        if isinstance(namespaces, str):
            namespaces = [namespaces]

        full_namespaces = namespaces
        logger.info(f"🔗 Full namespaces: {full_namespaces}")

        from db_service import Documents, Chunks
        total_doc_count = 0
        total_chunk_count = 0
        for full_ns in full_namespaces:
            doc_count = Documents.objects(namespace=full_ns).count()
            chunk_count = Chunks.objects(namespace=full_ns).count()
            total_doc_count += doc_count
            total_chunk_count += chunk_count
            logger.info(f"🔍 Found {doc_count} documents and {chunk_count} chunks for namespace: {full_ns}")
        logger.info(f"📊 Total: {total_doc_count} documents and {total_chunk_count} chunks across all namespaces")

        collected = []

        for full_namespace in full_namespaces:
            chatbot = ChatBots.objects(namespace=full_namespace).first()
            if not chatbot or not chatbot.embedding_model:
                logger.warning(f"No chatbot or embedding model found for namespace: {full_namespace}")
                continue

            embedding_model_of_namespace = chatbot.embedding_model
            provider = RAGService.model_providers.get(embedding_model_of_namespace, "other")

            if provider == "google":
                pinecone_index = "chatbot-vectors-google"
                logger.info(f"📊 Using Google/Gemini search pipeline with index: {pinecone_index}")
                result = search_rag_google(
                    query=query,
                    namespace=full_namespace,
                    index_name=pinecone_index,
                    embedding_model=embedding_model_of_namespace,
                    top_k=top_k * 2,
                    top_reranked=top_k * 2
                )
            elif provider == "openai":
                pinecone_index = "chatbot-vectors-openai"
                logger.info(f"📊 Using OpenAI search pipeline with index: {pinecone_index}")
                result = search_rag_openai(
                    query=query,
                    namespace=full_namespace,
                    index_name=pinecone_index,
                    embedding_model=embedding_model_of_namespace,
                    top_k=top_k * 2,
                    top_reranked=top_k * 2
                )
            else:
                logger.warning(f"Unsupported embedding model: {embedding_model_of_namespace}")
                continue

            if result and result != "No relevant documents found for the query.":
                collected.append(result)

        if collected:
            return "\n\n".join(collected)
        return "No relevant documents found for the query."

    except Exception as e:
        error_msg = f"RAG search failed: {str(e)}"
        logger.error(error_msg)
        logger.error("=" * 60)
        return f"Error retrieving relevant documents: {str(e)}"


if __name__ == "__main__":
    # Test the RAG search function
    # test_rag_search()
    pass