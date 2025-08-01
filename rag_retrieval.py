#!/usr/bin/env python3
"""
RAG Retrieval Module - Retrieves relevant chunks from user's documents using semantic search
Automatically selects embedding model and Pinecone index based on user's choice in master pipeline
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from pinecone import Pinecone
from bson import ObjectId
from db_service import Chunks

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGService:
    """
    Service class for RAG retrieval functionality
    Automatically handles embedding model selection and Pinecone index routing
    """

    def __init__(self):
        self.openai_client = None
        self.gemini_client = None
        self.pinecone_client = None

    def initialize_embedding_client(self, embedding_model: str) -> bool:
        """
        Initialize the appropriate embedding client based on model name

        Args:
            embedding_model: The embedding model to initialize

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if embedding_model.startswith("text-embedding"):
                # Initialize OpenAI client
                if not self.openai_client:
                    api_key = os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        raise ValueError(
                            "OPENAI_API_KEY environment variable not set")

                    self.openai_client = OpenAI(api_key=api_key)
                    logger.info(
                        f"✅ OpenAI client initialized for model: {embedding_model}")

                # Test the connection
                test_response = self.openai_client.embeddings.create(
                    model=embedding_model,
                    input=["test"]
                )
                return True

            elif embedding_model.startswith("gemini"):
                # Initialize Gemini client
                if not self.gemini_client:
                    api_key = os.getenv("GEMINI_API_KEY")
                    if not api_key:
                        raise ValueError(
                            "GEMINI_API_KEY environment variable not set")

                    self.gemini_client = genai.Client(api_key=api_key)
                    logger.info(
                        f"✅ Gemini client initialized for model: {embedding_model}")

                # Test the connection
                test_result = self.gemini_client.models.embed_content(
                    model=embedding_model,
                    contents=["test"]
                )
                return True

            else:
                raise ValueError(
                    f"Unsupported embedding model: {embedding_model}")

        except Exception as e:
            logger.error(
                f"Failed to initialize embedding client for {embedding_model}: {e}")
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
        Generate embedding for the query using the specified model

        Args:
            query: The search query
            embedding_model: The embedding model to use

        Returns:
            List of float values representing the embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        try:
            if embedding_model.startswith("text-embedding"):
                # Use OpenAI client
                response = self.openai_client.embeddings.create(
                    model=embedding_model,
                    input=query
                )
                return response.data[0].embedding

            elif embedding_model.startswith("gemini"):
                # Use Gemini client
                result = self.gemini_client.models.embed_content(
                    model=embedding_model,
                    contents=query
                )
                return result.embeddings[0].values

            else:
                raise ValueError(
                    f"Unsupported embedding model: {embedding_model}")

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


def rag_search(query: str, user_id: str, namespace: str, embedding_model: str, top_k: int = 5) -> str:
    """
    Main RAG search function that retrieves relevant document chunks for a user query

    This function:
    1. Auto-determines the correct Pinecone index based on embedding model
    2. Initializes the appropriate embedding client (OpenAI or Gemini)
    3. Generates query embedding using the same model used for document chunks
    4. Queries Pinecone for most similar vectors in user's namespace
    5. Retrieves full chunk data from MongoDB using vector IDs
    6. Returns formatted results for LLM consumption

    Args:
        query: User's search query
        user_id: MongoDB ObjectId string of the user
        namespace: User's namespace (without user_id suffix, will be auto-appended)
        embedding_model: Embedding model from master pipeline choice
                        - "text-embedding-3-small" for OpenAI
                        - "gemini-embedding-001" for Gemini
        top_k: Number of most relevant chunks to return (default: 5)

    Returns:
        Formatted string containing relevant document chunks with:
        - Source file names
        - Chunk summaries and content  
        - Relevance scores
        - Chunk metadata

    Example:
        >>> result = rag_search(
        ...     query="What is the company policy on remote work?",
        ...     user_id="507f1f77bcf86cd799439011", 
        ...     namespace="company_docs",
        ...     embedding_model="text-embedding-3-small"
        ... )
        >>> print(result)
        1.
        **Source File**: employee_handbook.pdf
        **Summary**: Remote work policy overview...
        **Content**: Employees may work remotely...
        ---
    """
    logger.info("=" * 60)
    logger.info("🔍 STARTING RAG SEARCH")
    logger.info("=" * 60)
    logger.info(f"📝 Query: {query}")
    logger.info(f"👤 User ID: {user_id}")
    logger.info(f"🏷️  Namespace: {namespace}")
    logger.info(f"🤖 Embedding Model: {embedding_model}")
    logger.info(f"📊 Top K: {top_k}")

    try:
        # Initialize RAG service
        rag_service = RAGService()

        # Step 1: Auto-determine Pinecone index based on embedding model
        pinecone_index = rag_service.determine_pinecone_index(embedding_model)
        logger.info(f"📊 Auto-selected Pinecone Index: {pinecone_index}")

        # Step 2: Initialize embedding client
        if not rag_service.initialize_embedding_client(embedding_model):
            return "Error: Failed to initialize embedding client. Please check your API keys."

        # Step 3: Initialize Pinecone client
        if not rag_service.initialize_pinecone_client():
            return "Error: Failed to initialize Pinecone client. Please check your PINECONE_API_KEY."

        # Step 4: Create user's full namespace (namespace_userid)
        full_namespace = f"{namespace}_{user_id}"
        logger.info(f"🔗 Full namespace: {full_namespace}")

        # Step 5: Generate query embedding
        logger.info("🔄 Generating query embedding...")
        query_embedding = rag_service.create_query_embedding(
            query, embedding_model)

        # Step 6: Query Pinecone for similar vectors
        logger.info("🔍 Querying Pinecone for similar vectors...")
        pinecone_matches = rag_service.query_pinecone(
            query_embedding=query_embedding,
            namespace=full_namespace,
            pinecone_index=pinecone_index,
            top_k=top_k
        )

        if not pinecone_matches:
            logger.info("ℹ️  No matches found in Pinecone")
            return f"No relevant documents found for your query in namespace '{namespace}'. Please check if you have uploaded documents to this namespace."

        # Step 7: Extract vector IDs and create score mapping
        vector_ids = [match['id'] for match in pinecone_matches]
        score_mapping = {match['id']: match['score']
                         for match in pinecone_matches}

        # Step 8: Retrieve full chunk data from MongoDB
        logger.info("🔄 Retrieving full chunk data from MongoDB...")
        chunks = rag_service.retrieve_chunks_from_mongodb(vector_ids)

        if not chunks:
            logger.warning(
                "⚠️  No chunks found in MongoDB for the retrieved vector IDs")
            return "Found relevant document IDs but could not retrieve full content. Please contact support."

        # Step 9: Sort chunks by Pinecone relevance score (highest first)
        chunks_sorted = sorted(
            chunks,
            key=lambda chunk: score_mapping.get(str(chunk.id), 0),
            reverse=True
        )

        # Step 10: Format results for LLM consumption
        logger.info("📝 Formatting results for LLM...")
        formatted_results = rag_service.format_rag_results(
            chunks_sorted, score_mapping)

        logger.info("✅ RAG search completed successfully")
        logger.info("=" * 60)

        return formatted_results

    except Exception as e:
        error_msg = f"RAG search failed: {str(e)}"
        logger.error(error_msg)
        logger.error("=" * 60)
        return f"Error retrieving relevant documents: {str(e)}"


def test_rag_search():
    """Test function to demonstrate RAG search usage"""
    # This would typically be called with real user data
    print("🧪 Testing RAG Search Function")
    print("=" * 50)

    # Example usage (would need real user data to work)
    test_query = "Who is Alice?"
    test_user_id = "688b48416faad142f66ca95e"  # Example ObjectId
    test_namespace = "ex"
    test_embedding_model = "gemini-embedding-001"

    print(f"Query: {test_query}")
    print(f"User ID: {test_user_id}")
    print(f"Namespace: {test_namespace}")
    print(f"Embedding Model: {test_embedding_model}")
    print()

    result = rag_search(
        query=test_query,
        user_id=test_user_id,
        namespace=test_namespace,
        embedding_model=test_embedding_model,
        top_k=3
    )

    print("Results:")
    print("=" * 50)
    print(result)


if __name__ == "__main__":
    # Test the RAG search function
    test_rag_search()
