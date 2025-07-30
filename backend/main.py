from embedding_service import EmbeddingService
from pinecone_service import PineconeService
from dotenv import load_dotenv
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

load_dotenv()

CHUNK_BATCH_SIZE = 5

if __name__ == "__main__":
    
    embedding_service = EmbeddingService()
    pinecone_service = PineconeService()

    PREFERRED_DB = "PINECONE"
    USER_CREATED_INDEX_NAME = "your-personal-chatbot"
    SUMMARY_EXAMPLE = "This is a summary of the text"
    TEXT_EXAMPLE = "This is the text of the chunk"

    # For testing
    chunks = [
        {
            "chunk_id": "chunk_1",
            "chunk_index": 0,
            "text": TEXT_EXAMPLE,
            "summary": SUMMARY_EXAMPLE
        },
        {
            "chunk_id": "chunk_2", 
            "chunk_index": 1,
            "text": TEXT_EXAMPLE + " 2",
            "summary": SUMMARY_EXAMPLE + " 2"
        }
    ]

    for batch_start in range(0, len(chunks), CHUNK_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + CHUNK_BATCH_SIZE]

        # Create combined text with summary and text
        chunk_texts_with_summaries = [
            f"Summary: {chunk['summary']} \nText: {chunk['text']}" 
            for chunk in batch
        ]

        logger.info(f"Embedding {len(chunk_texts_with_summaries)} chunks (summaries together with texts).")

        # Batch-embed this chunk batch
        try:
            model_name = embedding_service.initialize_embedding_model()

            if not model_name:
                logger.error("Model name is required")
                continue

            embeddings = embedding_service._create_embeddings_batch(chunk_texts_with_summaries, model_name, 3)
            
            if not embeddings:
                logger.error("Embeddings are required")
                continue

            logger.info(f"Embeddings created for {len(embeddings)} chunks.")
        except Exception as e:
            logger.error(f"Error embedding chunk summaries: {e}")
            continue
        
        # Upsert the embeddings to Pinecone with correct data structure
        try:
            if PREFERRED_DB == "PINECONE":
                # Initialize Pinecone
                pinecone_service.initialize_pinecone(
                    api_key=os.getenv("PINECONE_API_KEY"),
                    environment=os.getenv("PINECONE_ENVIRONMENT"),
                    index_name=USER_CREATED_INDEX_NAME,
                    model_name=model_name
                )
                
                # Create proper chunks_data structure
                chunks_data = []
                for i, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                    chunks_data.append({
                        "chunk_id": chunk["chunk_id"],
                        "chunk_index": chunk["chunk_index"],
                        "embedding": embedding,
                        "summary": chunk["summary"],
                        "text": chunk["text"]
                    })
                
                # Store with correct function signature
                success = pinecone_service.store_multiple_embeddings(
                    user_id="example_user_id_12345",
                    document_id="example_document_id_12345",
                    chunks_data=chunks_data
                )
                
                if success:
                    logger.info(f"Embeddings upserted to Pinecone for {len(embeddings)} chunks.")
                else:
                    logger.error("Failed to store embeddings in Pinecone.")
            else:
                logger.info(f"Embeddings upserted to Chroma for {len(embeddings)} chunks.")
                # TODO: Implement Chroma upsert and FAISS upsert
        except Exception as e:
            logger.error(f"Error upserting embeddings to Pinecone: {e}")
            continue

        





