"""
Vector Store Manager - Centralized connection management for all vector store operations.
Implements singleton pattern with connection pooling and lazy loading.
"""

import os
import time
import logging
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# Import clients
from openai import OpenAI
from google import genai
from pinecone import Pinecone, ServerlessSpec
from pymongo import MongoClient
from gridfs import GridFS
from mongoengine import connect, connection

# Import configuration
from config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionPoolError(Exception):
    """Custom exception for connection pool errors."""
    pass


class VectorStoreManager:
    """
    Singleton manager for all vector store and database connections.
    Provides persistent, pooled connections with health monitoring.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VectorStoreManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the manager (only once due to singleton)."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self.config = get_config()

            # Connection instances
            self._openai_client = None
            self._google_client = None
            self._pinecone_client = None
            self._mongodb_client = None
            self._gridfs = None
            self._mongodb_db = None

            # Connection pools and cache
            self._pinecone_indexes = {}  # Cache for index connections
            self._index_metadata = {}   # Cache for index specs
            self._connection_health = {}  # Track connection health

            # Health check configuration
            self._health_check_interval = 300  # 5 minutes
            self._last_health_check = {}

            # Thread safety
            self._openai_lock = threading.Lock()
            self._google_lock = threading.Lock()
            self._pinecone_lock = threading.Lock()
            self._mongodb_lock = threading.Lock()

            self._initialized = True
            logger.info("🚀 VectorStoreManager initialized")

    def _is_connection_healthy(self, connection_type: str) -> bool:
        """Check if a connection was recently verified as healthy."""
        last_check = self._last_health_check.get(connection_type)
        if not last_check:
            return False

        # Consider connection healthy if checked within the interval
        return (datetime.now() - last_check).total_seconds() < self._health_check_interval

    def _mark_connection_healthy(self, connection_type: str) -> None:
        """Mark connection as healthy with current timestamp."""
        self._last_health_check[connection_type] = datetime.now()

    def _validate_openai_connection(self, client: OpenAI) -> bool:
        """Validate OpenAI client connection."""
        try:
            # Simple test call
            client.models.list()
            return True
        except Exception as e:
            logger.warning(f"OpenAI connection validation failed: {e}")
            return False

    def _validate_google_connection(self, client) -> bool:
        """Validate Google client connection."""
        try:
            # Simple test call - list models
            models = client.models.list()
            return True
        except Exception as e:
            logger.warning(f"Google connection validation failed: {e}")
            return False

    def _validate_pinecone_connection(self, client: Pinecone) -> bool:
        """Validate Pinecone client connection."""
        try:
            # List indexes to test connection
            client.list_indexes()
            return True
        except Exception as e:
            logger.warning(f"Pinecone connection validation failed: {e}")
            return False

    def _validate_mongodb_connection(self, client: MongoClient) -> bool:
        """Validate MongoDB client connection."""
        try:
            # Simple ping to test connection
            client.admin.command('ping')
            return True
        except Exception as e:
            logger.warning(f"MongoDB connection validation failed: {e}")
            return False

    def get_openai_client(self) -> Optional[OpenAI]:
        """Get or create OpenAI client with connection pooling."""
        with self._openai_lock:
            # Return cached client if healthy
            if (self._openai_client and
                    self._is_connection_healthy("openai")):
                return self._openai_client

            # Validate existing connection
            if (self._openai_client and
                    self._validate_openai_connection(self._openai_client)):
                self._mark_connection_healthy("openai")
                return self._openai_client

            # Create new connection
            try:
                openai_config = self.config.get_openai_config()
                self._openai_client = OpenAI(**openai_config)

                # Validate new connection
                if self._validate_openai_connection(self._openai_client):
                    self._mark_connection_healthy("openai")
                    logger.info("✅ OpenAI client connection established")
                    return self._openai_client
                else:
                    raise ConnectionPoolError(
                        "OpenAI connection validation failed")

            except Exception as e:
                logger.error(f"❌ Failed to create OpenAI client: {e}")
                self._openai_client = None
                return None

    def get_google_client(self):
        """Get or create Google client with connection pooling."""
        with self._google_lock:
            # Return cached client if healthy
            if (self._google_client and
                    self._is_connection_healthy("google")):
                return self._google_client

            # Check if Google API key is available
            google_config = self.config.get_google_config()
            if not google_config:
                logger.warning("Google API key not available")
                return None

            # Validate existing connection
            if (self._google_client and
                    self._validate_google_connection(self._google_client)):
                self._mark_connection_healthy("google")
                return self._google_client

            # Create new connection
            try:
                self._google_client = genai.Client(**google_config)

                # Validate new connection
                if self._validate_google_connection(self._google_client):
                    self._mark_connection_healthy("google")
                    logger.info("✅ Google client connection established")
                    return self._google_client
                else:
                    raise ConnectionPoolError(
                        "Google connection validation failed")

            except Exception as e:
                logger.error(f"❌ Failed to create Google client: {e}")
                self._google_client = None
                return None

    def get_pinecone_client(self) -> Optional[Pinecone]:
        """Get or create Pinecone client with connection pooling."""
        with self._pinecone_lock:
            # Return cached client if healthy
            if (self._pinecone_client and
                    self._is_connection_healthy("pinecone")):
                return self._pinecone_client

            # Validate existing connection
            if (self._pinecone_client and
                    self._validate_pinecone_connection(self._pinecone_client)):
                self._mark_connection_healthy("pinecone")
                return self._pinecone_client

            # Create new connection
            try:
                pinecone_config = self.config.get_pinecone_config()
                self._pinecone_client = Pinecone(
                    api_key=pinecone_config["api_key"],
                    environment=pinecone_config["environment"]
                )

                # Validate new connection
                if self._validate_pinecone_connection(self._pinecone_client):
                    self._mark_connection_healthy("pinecone")
                    logger.info("✅ Pinecone client connection established")
                    return self._pinecone_client
                else:
                    raise ConnectionPoolError(
                        "Pinecone connection validation failed")

            except Exception as e:
                logger.error(f"❌ Failed to create Pinecone client: {e}")
                self._pinecone_client = None
                return None

    def get_mongodb_connection(self) -> tuple[Optional[MongoClient], Optional[Any], Optional[GridFS]]:
        """Get or create MongoDB connection with connection pooling."""
        with self._mongodb_lock:
            # Return cached connections if healthy
            if (self._mongodb_client is not None and self._mongodb_db is not None and
                    self._gridfs is not None and self._is_connection_healthy("mongodb")):
                return self._mongodb_client, self._mongodb_db, self._gridfs

            # Validate existing connection
            if (self._mongodb_client is not None and
                    self._validate_mongodb_connection(self._mongodb_client)):
                self._mark_connection_healthy("mongodb")
                return self._mongodb_client, self._mongodb_db, self._gridfs

            # Create new connection
            try:
                mongodb_config = self.config.get_mongodb_config()

                # Create MongoDB client
                self._mongodb_client = MongoClient(mongodb_config["url"])
                self._mongodb_db = self._mongodb_client[mongodb_config["database_name"]]
                self._gridfs = GridFS(self._mongodb_db)

                # Setup MongoEngine connection
                connect(
                    db=mongodb_config["database_name"],
                    host=mongodb_config["url"],
                    alias='default'
                )

                # Validate new connection
                if self._validate_mongodb_connection(self._mongodb_client):
                    self._mark_connection_healthy("mongodb")
                    logger.info("✅ MongoDB connection established")
                    return self._mongodb_client, self._mongodb_db, self._gridfs
                else:
                    raise ConnectionPoolError(
                        "MongoDB connection validation failed")

            except Exception as e:
                logger.error(f"❌ Failed to create MongoDB connection: {e}")
                self._mongodb_client = None
                self._mongodb_db = None
                self._gridfs = None
                return None, None, None

    def get_pinecone_index(self, index_name: str, model_name: str = None) -> Optional[Any]:
        """Get or create Pinecone index connection with caching."""
        # Get Pinecone client
        pinecone_client = self.get_pinecone_client()
        if not pinecone_client:
            return None

        # Return cached index if available
        if index_name in self._pinecone_indexes:
            return self._pinecone_indexes[index_name]

        try:
            # Check if index exists
            existing_indexes = pinecone_client.list_indexes()
            index_names = [idx.name for idx in existing_indexes]

            if index_name not in index_names:
                logger.warning(f"Pinecone index '{index_name}' does not exist")
                return None

            # Create index connection and cache it
            index = pinecone_client.Index(index_name)
            self._pinecone_indexes[index_name] = index

            # Cache index metadata
            index_info = next(
                (idx for idx in existing_indexes if idx.name == index_name), None)
            if index_info:
                self._index_metadata[index_name] = {
                    "dimension": getattr(index_info, 'dimension', None),
                    "metric": getattr(index_info, 'metric', 'cosine'),
                    "created_at": datetime.now()
                }

            logger.info(f"✅ Pinecone index '{index_name}' connection cached")
            return index

        except Exception as e:
            logger.error(f"❌ Failed to get Pinecone index '{index_name}': {e}")
            return None

    def ensure_pinecone_index_exists(self, index_name: str, model_name: str = None) -> bool:
        """Ensure Pinecone index exists, create if necessary."""
        pinecone_client = self.get_pinecone_client()
        if not pinecone_client:
            return False

        try:
            # Check if index exists
            existing_indexes = pinecone_client.list_indexes()
            index_names = [idx.name for idx in existing_indexes]

            if index_name in index_names:
                logger.info(f"✅ Pinecone index '{index_name}' already exists")
                return True

            # Determine dimension
            if model_name:
                dimension = self.config.get_embedding_model_dimension(
                    model_name)
            else:
                # Default dimension based on index name
                if "google" in index_name.lower():
                    dimension = 768
                else:
                    dimension = 1536

            # Create index
            logger.info(
                f"Creating Pinecone index '{index_name}' with dimension {dimension}")
            pinecone_client.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=self.config.get("pinecone_cloud", "aws"),
                    region=self.config.get("pinecone_region", "us-east-1")
                )
            )

            # Cache metadata
            self._index_metadata[index_name] = {
                "dimension": dimension,
                "metric": "cosine",
                "created_at": datetime.now()
            }

            logger.info(
                f"✅ Successfully created Pinecone index '{index_name}'")
            return True

        except Exception as e:
            logger.error(
                f"❌ Failed to ensure Pinecone index '{index_name}' exists: {e}")
            return False

    def get_index_metadata(self, index_name: str) -> Optional[Dict[str, Any]]:
        """Get cached metadata for a Pinecone index."""
        return self._index_metadata.get(index_name)

    def health_check_all_connections(self) -> Dict[str, bool]:
        """Perform health check on all connections."""
        health_status = {}

        # Check OpenAI
        openai_client = self.get_openai_client()
        health_status["openai"] = openai_client is not None

        # Check Google (optional)
        google_client = self.get_google_client()
        health_status["google"] = google_client is not None

        # Check Pinecone
        pinecone_client = self.get_pinecone_client()
        health_status["pinecone"] = pinecone_client is not None

        # Check MongoDB
        mongodb_client, _, _ = self.get_mongodb_connection()
        health_status["mongodb"] = mongodb_client is not None

        logger.info(f"Health check results: {health_status}")
        return health_status

    def close_all_connections(self) -> None:
        """Close all connections and clear cache."""
        with self._mongodb_lock:
            if self._mongodb_client is not None:
                self._mongodb_client.close()
                self._mongodb_client = None
                self._mongodb_db = None
                self._gridfs = None

        # Clear caches
        self._pinecone_indexes.clear()
        self._index_metadata.clear()
        self._connection_health.clear()
        self._last_health_check.clear()

        # Reset clients
        self._openai_client = None
        self._google_client = None
        self._pinecone_client = None

        logger.info("🔌 All connections closed and cache cleared")

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about current connections."""
        return {
            "initialized": self._initialized,
            "cached_indexes": len(self._pinecone_indexes),
            "cached_metadata": len(self._index_metadata),
            "last_health_checks": self._last_health_check,
            "active_connections": {
                "openai": self._openai_client is not None,
                "google": self._google_client is not None,
                "pinecone": self._pinecone_client is not None,
                "mongodb": self._mongodb_client is not None
            }
        }


# Global instance
_vector_store_manager = None
_manager_lock = threading.Lock()


def get_vector_store_manager() -> VectorStoreManager:
    """Get the global VectorStoreManager instance."""
    global _vector_store_manager

    if _vector_store_manager is None:
        with _manager_lock:
            if _vector_store_manager is None:
                _vector_store_manager = VectorStoreManager()

    return _vector_store_manager


def initialize_vector_store_manager() -> VectorStoreManager:
    """Initialize and return the VectorStoreManager instance."""
    manager = get_vector_store_manager()

    # Trigger initialization of connections
    health_status = manager.health_check_all_connections()

    failed_connections = [conn for conn,
                          status in health_status.items() if not status]
    if failed_connections:
        logger.warning(
            f"⚠️ Some connections failed to initialize: {failed_connections}")
    else:
        logger.info("✅ All connections initialized successfully")

    return manager


if __name__ == "__main__":
    """Test the VectorStoreManager."""
    print("Testing VectorStoreManager...")

    try:
        # Initialize manager
        manager = initialize_vector_store_manager()

        print("\n--- Connection Stats ---")
        stats = manager.get_connection_stats()
        print(f"Stats: {stats}")

        print("\n--- Health Check ---")
        health = manager.health_check_all_connections()
        print(f"Health: {health}")

        print("\n--- Testing Individual Connections ---")

        # Test OpenAI
        openai_client = manager.get_openai_client()
        print(
            f"OpenAI client: {'✅ Available' if openai_client else '❌ Failed'}")

        # Test Google
        google_client = manager.get_google_client()
        print(
            f"Google client: {'✅ Available' if google_client else '❌ Failed or not configured'}")

        # Test Pinecone
        pinecone_client = manager.get_pinecone_client()
        print(
            f"Pinecone client: {'✅ Available' if pinecone_client else '❌ Failed'}")

        # Test MongoDB
        mongo_client, mongo_db, gridfs = manager.get_mongodb_connection()
        print(f"MongoDB: {'✅ Available' if mongo_client else '❌ Failed'}")

        print("\n✅ VectorStoreManager test completed!")

    except Exception as e:
        print(f"❌ VectorStoreManager test failed: {e}")
        import traceback
        traceback.print_exc()
