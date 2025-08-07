"""
Configuration management for the Personal RAG Chatbot.
Centralizes environment variable handling and default settings.
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Config:
    """Centralized configuration management for the application."""

    # Required environment variables
    REQUIRED_VARS = [
        "OPENAI_API_KEY",
        "PINECONE_API_KEY"
    ]

    # Optional environment variables with defaults
    OPTIONAL_VARS = {
        "GOOGLE_API_KEY": None,
        "GEMINI_API_KEY": None,
        "OPENAI_BASE_URL": None,
        "MONGODB_URL": "mongodb://localhost:27017/",
        "MONGODB_DB_NAME": "your_personal_chatbot_db",
        "PINECONE_ENVIRONMENT": "eu-west4-gcp",
        "PINECONE_CLOUD": "aws",
        "PINECONE_REGION": "us-east-1"
    }

    # Default configuration
    DEFAULT_CONFIG = {
        "embedding_models": {
            "openai_default": "text-embedding-3-small",
            "openai_large": "text-embedding-3-large",
            "openai_ada": "text-embedding-ada-002",
            "google_default": "gemini-embedding-001",
            "google_multilingual": "text-multilingual-embedding-002"
        },
        "pinecone_indexes": {
            "openai": "chatbot-vectors-openai",
            "google": "chatbot-vectors-google",
            "default": "chatbot-vectors"
        },
        "vector_dimensions": {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536,
            "gemini-embedding-001": 3072,
            "text-multilingual-embedding-002": 3072
        },
        "batch_sizes": {
            "embedding": 50,
            "pinecone_upsert": 100,
            "retrieval": 10
        },
        "retry_config": {
            "max_retries": 3,
            "backoff_factor": 1.0,
            "timeout": 30
        },
        "connection_pool": {
            "max_connections": 10,
            "connection_timeout": 30,
            "read_timeout": 60
        }
    }

    def __init__(self):
        """Initialize configuration and validate required variables."""
        self._config = self.DEFAULT_CONFIG.copy()
        self._validate_environment()
        self._load_environment_variables()

    def _validate_environment(self) -> None:
        """Validate that all required environment variables are set."""
        missing_vars = []
        for var in self.REQUIRED_VARS:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        logger.info("✅ All required environment variables are set")

    def _load_environment_variables(self) -> None:
        """Load environment variables into configuration."""
        # Load required variables
        for var in self.REQUIRED_VARS:
            self._config[var.lower()] = os.getenv(var)

        # Load optional variables
        for var, default in self.OPTIONAL_VARS.items():
            value = os.getenv(var, default)
            if value is not None:
                self._config[var.lower()] = value

        logger.info("✅ Environment variables loaded successfully")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return self._config.get(key, default)

    def get_openai_config(self) -> Dict[str, str]:
        """Get OpenAI client configuration."""
        config = {
            "api_key": self.get("openai_api_key")
        }

        base_url = self.get("openai_base_url")
        if base_url:
            config["base_url"] = base_url

        return config

    def get_google_config(self) -> Optional[Dict[str, str]]:
        """Get Google/Gemini client configuration."""
        # Check both GOOGLE_API_KEY and GEMINI_API_KEY for backward compatibility
        api_key = self.get("google_api_key") or self.get("gemini_api_key")

        if not api_key:
            return None

        return {"api_key": api_key}

    def get_pinecone_config(self) -> Dict[str, str]:
        """Get Pinecone client configuration."""
        return {
            "api_key": self.get("pinecone_api_key"),
            "environment": self.get("pinecone_environment")
        }

    def get_mongodb_config(self) -> Dict[str, str]:
        """Get MongoDB configuration."""
        return {
            "url": self.get("mongodb_url"),
            "database_name": self.get("mongodb_db_name")
        }

    def get_embedding_model_dimension(self, model_name: str) -> int:
        """Get vector dimension for embedding model."""
        dimensions = self.get("vector_dimensions", {})

        # Auto-determine dimension if not in config
        if model_name not in dimensions:
            if "google" in model_name.lower() or "gemini" in model_name.lower():
                return 3072  # Default for Google models (gemini-embedding-001)
            else:
                return 1536  # Default for OpenAI models

        return dimensions[model_name]

    def get_pinecone_index_name(self, embedding_model: str) -> str:
        """Get appropriate Pinecone index name based on embedding model."""
        indexes = self.get("pinecone_indexes", {})

        if "gemini" in embedding_model.lower() or "google" in embedding_model.lower():
            return indexes.get("google", "chatbot-vectors-google")
        elif "text-embedding" in embedding_model.lower():
            return indexes.get("openai", "chatbot-vectors-openai")
        else:
            return indexes.get("default", "chatbot-vectors")

    def is_google_model(self, model_name: str) -> bool:
        """Check if model is a Google/Gemini model."""
        return any(keyword in model_name.lower()
                   for keyword in ["gemini", "google", "multilingual"])

    def is_openai_model(self, model_name: str) -> bool:
        """Check if model is an OpenAI model."""
        return model_name.startswith("text-embedding")

    def __repr__(self) -> str:
        """String representation of config (without sensitive data)."""
        safe_config = {k: v for k, v in self._config.items()
                       if "key" not in k.lower() and "password" not in k.lower()}
        return f"Config({safe_config})"


# Global config instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def validate_config() -> bool:
    """Validate configuration and return True if valid."""
    try:
        config._validate_environment()
        logger.info("✅ Configuration validation successful")
        return True
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        return False


if __name__ == "__main__":
    """Test configuration module."""
    print("Testing configuration module...")

    try:
        cfg = get_config()
        print(f"Configuration loaded: {cfg}")

        print("\n--- OpenAI Config ---")
        print(cfg.get_openai_config())

        print("\n--- Google Config ---")
        print(cfg.get_google_config())

        print("\n--- Pinecone Config ---")
        print(cfg.get_pinecone_config())

        print("\n--- MongoDB Config ---")
        print(cfg.get_mongodb_config())

        print("\n--- Model Dimensions ---")
        for model in ["text-embedding-3-small", "gemini-embedding-001"]:
            print(f"{model}: {cfg.get_embedding_model_dimension(model)}")

        print("\n--- Index Names ---")
        for model in ["text-embedding-3-small", "gemini-embedding-001"]:
            print(f"{model}: {cfg.get_pinecone_index_name(model)}")

        print("\n✅ Configuration test completed successfully!")

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
