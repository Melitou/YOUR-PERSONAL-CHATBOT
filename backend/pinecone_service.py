import os
import pinecone
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from bson import ObjectId
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PineconeService:
    """Service class for managing Pinecone vector database operations"""
    
    def __init__(self):
        self.index = None
        self.initialized = False
        
    def initialize_pinecone(self,
                          api_key: Optional[str] = None,
                          environment: Optional[str] = None,
                          index_name: str = "your-personal-chatbot") -> bool:
        """
        Initialize Pinecone client and connect to index
        
        Args:
            api_key: Pinecone API key (defaults to PINECONE_API_KEY env var)
            environment: Pinecone environment (defaults to PINECONE_ENVIRONMENT env var)
            index_name: Name of the Pinecone index to use
            
        Returns:
            bool: True if initialization successful, False otherwise
        """
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
            pinecone.init(api_key=api_key, environment=environment)
            
            # Check if index exists, create if it doesn't
            if index_name not in pinecone.list_indexes():
                logger.info(f"Creating Pinecone index: {index_name}")
                pinecone.create_index(
                    name=index_name,
                    dimension=1536,  # Default dimension for OpenAI embeddings
                    metric="cosine"
                )
                logger.info(f"Index {index_name} created successfully")
            
            # Connect to the index
            self.index = pinecone.Index(index_name)
            self.initialized = True
            
            logger.info(f"Pinecone initialized successfully with index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone: {e}")
            return False
    
    def store_embedding(self, 
                       user_id: str, 
                       document_id: str, 
                       chunk_id: str,
                       chunk_index: int,
                       embedding: List[float],
                       summary: str) -> bool:
        """
        Store an embedding in Pinecone with the specified metadata structure
        
        Args:
            user_id: User ID from the database
            document_id: Document ID from the database
            chunk_id: The string representation of the chunk's _id from MongoDB
            chunk_index: The sequential order of the chunk within the document
            embedding: The embedding vector (list of floats)
            summary: The summary of the chunk content
            
        Returns:
            bool: True if storage successful, False otherwise
        """
        if not self.initialized or not self.index:
            logger.error("Pinecone not initialized. Call initialize_pinecone() first.")
            return False
        
        try:
            # Create the record structure as specified
            record = {
                "id": chunk_id,  # The string representation of the chunk's _id
                "values": embedding,  # Embeddings from the chunk content
                "metadata": {
                    "user_id": user_id,
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "summary": summary
                }
            }
            
            # Upsert the record to Pinecone
            self.index.upsert(vectors=[record])
            
            logger.info(f"Successfully stored embedding for chunk {chunk_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing embedding for chunk {chunk_id}: {e}")
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
        if not self.initialized or not self.index:
            logger.error("Pinecone not initialized. Call initialize_pinecone() first.")
            return False
        
        try:
            records = []
            
            for chunk_data in chunks_data:
                chunk_id = chunk_data.get('chunk_id')
                chunk_index = chunk_data.get('chunk_index')
                embedding = chunk_data.get('embedding')
                summary = chunk_data.get('summary')  # Add summary field
                
                if not all([chunk_id, chunk_index is not None, embedding, summary]):
                    logger.warning(f"Missing required data for chunk: {chunk_data}")
                    continue
                
                record = {
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": {
                        "user_id": user_id,
                        "document_id": document_id,
                        "chunk_index": chunk_index,
                        "summary": summary  # Include summary in metadata
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
        if not self.initialized or not self.index:
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
        if not self.initialized or not self.index:
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
        if not self.initialized or not self.index:
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
        if not self.initialized or not self.index:
            logger.error("Pinecone not initialized. Call initialize_pinecone() first.")
            return {}
        
        try:
            stats = self.index.describe_index_stats()
            return stats
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}


