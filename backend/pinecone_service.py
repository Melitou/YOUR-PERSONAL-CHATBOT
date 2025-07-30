import os
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from bson import ObjectId
import logging
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PineconeService:
    """Service class for managing Pinecone vector database operations"""
    
    def __init__(self):
        self.index = None
        self.pc = None
        
    def initialize_pinecone(self,
                          api_key: Optional[str] = None,
                          environment: Optional[str] = None,
                          index_name: str = "your-personal-chatbot",
                          model_name: str = "text-embedding-3-large") -> bool:
        """
        Initialize Pinecone client and connect to index
        
        Args:
            api_key: Pinecone API key (defaults to PINECONE_API_KEY env var)
            environment: Pinecone environment (defaults to PINECONE_ENVIRONMENT env var)
            index_name: Name of the Pinecone index to use
            
        Returns:
            bool: True if initialization successful, False otherwise
        """

        models_dimensions = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536,
            "text-embedding-005": 1536,
            "text-multilingual-embedding-002": 1536,
            "multilingual-e5-large": 1536,
            "gemini-embedding-001": 3072
        }

        try:
            # Get API key and environment from parameters or environment variables
            api_key = api_key or os.getenv("PINECONE_API_KEY")
            environment = environment or os.getenv("PINECONE_ENVIRONMENT")
            
            if not api_key:
                logger.error("Pinecone API key not found. Please set PINECONE_API_KEY environment variable.")
                return False
                
            if not environment:
                logger.error("Pinecone environment not found. Please set PINECONE_ENVIRONMENT environment variable.")
                return False
            
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=api_key)

            # Check if the index exists and delete it
            if index_name in self.pc.list_indexes().names():
                self.pc.delete_index(index_name)
                logger.info(f"Deleted old index: {index_name}")
            else:
                logger.info(f"Index does not exist, nothing to delete: {index_name}")

            logger.info(f"Model name: {model_name}")
            logger.info(f"Model dimension: {models_dimensions[model_name]}")
            
            # Check if index exists, create if it doesn't
            if not self.pc.has_index(index_name):
                logger.info(f"Creating Pinecone index: {index_name}")
                self.pc.create_index(
                    name=index_name,
                    dimension=models_dimensions[model_name],
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
                logger.info(f"\nIndex {index_name} created successfully\n")

                # Wait for index to be ready
                while not self.pc.has_index(index_name):
                    time.sleep(1)
                    logger.info(f"Waiting for index {index_name} to be ready...")

                index_info = self.pc.describe_index(index_name)
                logger.info(f"Index info: {index_info}")

            
            # Connect to the index
            self.index = self.pc.Index(index_name)
            
            logger.info(f"Pinecone initialized successfully with index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone: {e}")
            return False
    
    def store_multiple_embeddings(self, 
                                user_id: str,
                                document_id: str,
                                chunks_data: List[Dict[str, Any]]) -> bool:
        """
        Store multiple embeddings in a batch operation
        
        Args:
            user_id: User ID from the database
            document_id: Document ID from the database
            chunks_data: List of dictionaries containing chunk_id, chunk_index, embedding, and summary
            
        Returns:
            bool: True if all storage operations successful, False otherwise
        """
        if not self.pc or not self.index:
            logger.error("Pinecone not initialized. Call initialize_pinecone() first.")
            return False
        
        try:
            records = []
            
            for chunk_data in chunks_data:
                chunk_id = chunk_data.get('chunk_id')
                chunk_index = chunk_data.get('chunk_index')
                embedding = chunk_data.get('embedding')
                summary = chunk_data.get('summary')
                text = chunk_data.get('text')

                logger.info(f"\nChunk ID: {chunk_id}")
                logger.info(f"Chunk index: {chunk_index}")
                logger.info(f"Embedding: {embedding}")
                logger.info(f"Summary: {summary}")
                logger.info(f"Text: {text}\n")
                
                if not all([chunk_id, chunk_index is not None, embedding, summary, text]):
                    logger.warning(f"Missing required data for chunk: {chunk_data}")
                    continue
                
                record = {
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": {
                        "user_id": user_id,
                        "document_id": document_id,
                        "chunk_index": chunk_index,
                        "summary": summary,
                        "text": text
                    }
                }
                records.append(record)
            
            if records:
                self.index.upsert(vectors=records)
                logger.info(f"Successfully stored {len(records)} embeddings")
                return True
            else:
                logger.warning("No valid records to store")
                return False
                
        except Exception as e:
            logger.error(f"Error storing multiple embeddings: {e}")
            return False
    
    def query_similar(self, 
                     query_embedding: List[float], 
                     user_id: Optional[str] = None,
                     top_k: int = 5,
                     include_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        Query for similar embeddings
        
        Args:
            query_embedding: The query embedding vector
            user_id: Optional user ID to filter results by user
            top_k: Number of top results to return
            include_metadata: Whether to include metadata in results
            
        Returns:
            List of similar documents with scores
        """
        if not self.pc or not self.index:
            logger.error("Pinecone not initialized. Call initialize_pinecone() first.")
            return []
        
        try:
            # Build filter if user_id is provided
            filter_dict = {}
            if user_id:
                filter_dict["user_id"] = user_id
            
            # Query the index
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=include_metadata,
                filter=filter_dict if filter_dict else None
            )
            
            return results.matches
            
        except Exception as e:
            logger.error(f"Error querying similar embeddings: {e}")
            return []
    
    def delete_embeddings_by_document(self, document_id: str) -> bool:
        """
        Delete all embeddings for a specific document
        
        Args:
            document_id: Document ID to delete embeddings for
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        if not self.pc or not self.index:
            logger.error("Pinecone not initialized. Call initialize_pinecone() first.")
            return False
        
        try:
            # Delete vectors by metadata filter
            self.index.delete(filter={"document_id": document_id})
            logger.info(f"Successfully deleted embeddings for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting embeddings for document {document_id}: {e}")
            return False
    
    def delete_embeddings_by_user(self, user_id: str) -> bool:
        """
        Delete all embeddings for a specific user
        
        Args:
            user_id: User ID to delete embeddings for
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        if not self.pc or not self.index:
            logger.error("Pinecone not initialized. Call initialize_pinecone() first.")
            return False
        
        try:
            # Delete vectors by metadata filter
            self.index.delete(filter={"user_id": user_id})
            logger.info(f"Successfully deleted embeddings for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting embeddings for user {user_id}: {e}")  
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Pinecone index
        
        Returns:
            Dictionary containing index statistics
        """
        if not self.pc or not self.index:
            logger.error("Pinecone not initialized. Call initialize_pinecone() first.")
            return {}
        
        try:
            stats = self.index.describe_index_stats()
            return stats
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}


