import os
import logging
import time
from typing import List, Optional
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai

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
                logger.info(f"Attempting to initialize model: {current_model} (attempt {attempts + 1})")
                
                if current_model.startswith("text-embedding"):
                    # Initialize OpenAI client
                    if not self.openai_client:
                        api_key = os.getenv("OPENAI_API_KEY")
                        base_url = os.getenv("OPENAI_BASE_URL")
                        
                        if not api_key:
                            raise ValueError("OPENAI_API_KEY environment variable not set")
                        
                        self.openai_client = OpenAI(
                            api_key=api_key,
                            base_url=base_url
                        )
                    
                    # Test the connection
                    test_response = self.openai_client.embeddings.create(
                        model=current_model,
                        input=["test"]
                    )
                    
                    logger.info(f"Successfully initialized OpenAI model: {current_model}")
                    return current_model
                
                elif current_model.startswith("gemini"):
                    # Initialize Google client
                    if not self.google_initialized:
                        api_key = os.getenv("GOOGLE_API_KEY")
                        
                        if not api_key:
                            raise ValueError("GOOGLE_API_KEY environment variable not set")
                        
                        genai.configure(api_key=api_key, transport="rest")
                        self.google_initialized = True
                    
                    # Test the connection
                    model = genai.GenerativeModel(current_model)
                    test_result = model.embed_content(contents=["test"])
                    
                    logger.info(f"Successfully initialized Google model: {current_model}")
                    return current_model
                
                else:
                    raise ValueError(f"Invalid embedding model: {current_model}")
                    
            except Exception as e:
                logger.warning(f"Failed to initialize model {current_model}: {e}")
                
                # Try fallback model
                if current_model in self.fallback_models and attempts < max_fallbacks:
                    fallback_model = self.fallback_models[current_model]
                    logger.info(f"Trying fallback model: {fallback_model}")
                    current_model = fallback_model
                    attempts += 1
                    continue
                else:
                    logger.error("No more fallback models available. All attempts failed.")
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
                    model = genai.GenerativeModel(model_name)
                    result = model.embed_content(contents=chunks)
                    
                    embeddings = result['embedding']
                    return embeddings
                
                else:
                    raise ValueError(f"Unknown embedding model: {model_name}")
                    
            except Exception as e:
                logger.warning(f"[Model: {model_name}, Attempt {attempt}] Error creating batch embeddings: {e}")
                if attempt < max_retries:
                    time.sleep(1)  # Wait before retrying
                else:
                    logger.error(f"Failed to create batch embeddings after {max_retries} attempts")
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
