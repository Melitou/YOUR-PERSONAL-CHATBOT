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

    PREFFERED_DB = "PINECONE"
    USER_CREATED_INDEX_NAME = "your-personal-chatbot"
    SUMMARY_EXAMPLE = "This is a summary of the text"
    TEXT_EXAMPLE = "This is the text of the chunk"

    chunks = []
    for batch_start in range(0, len(chunks), CHUNK_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + CHUNK_BATCH_SIZE]

        # We already have the summaries for each chunk
        # so we can use them to embed the chunks
        # chunk_summaries = [chunk.summary_raw for chunk in batch]
        
        # Take for each chunk, the summary and the text and combine 
        # them in one string following the format:
        # "Summary: <summary> Text: <text>"
        chunk_summaries = [SUMMARY_EXAMPLE for chunk in batch] # TODO: Change to chunk.summary_raw
        chunk_texts = [TEXT_EXAMPLE for chunk in batch] # TODO: Change to chunk.text
        chunk_texts_with_summaries = [f"Summary: {summary} \nText: {text}" for summary, text in zip(chunk_summaries, chunk_texts)]

        logger.info(f"Embedding {len(chunk_texts_with_summaries)} chunks (summaries together with texts).")

        # Batch-embed this chunk batch
        try:
            model_name = embedding_service.initialize_embedding_model()
            embeddings = embedding_service._create_embeddings_batch(chunk_texts_with_summaries, model_name, 3)
            logger.info(f"Embeddings created for {len(embeddings)} chunks.")
        except Exception as e:
            logger.error(f"Error embedding chunk summaries: {e}")
            continue
        
        # Upsert the embeddings to Pipecone
        try:
            if PREFFERED_DB == "PINECONE":
                # Initialize Pinecone
                pinecone_service.initialize_pinecone(
                    api_key=os.getenv("PINECONE_API_KEY"),
                    environment=os.getenv("PINECONE_ENVIRONMENT"),
                    index_name=USER_CREATED_INDEX_NAME
                )
                # Store the embeddings for the current batch in Pinecone
                pinecone_service.store_multiple_embeddings(
                    user_id="example_user_id_12345",
                    document_id="example_document_id_12345",
                    file_name="example_file_name_12345",
                    chunks_data=zip(chunk_texts_with_summaries, embeddings)
                )
                logger.info(f"Embeddings upserted to Pinecone for {len(embeddings)} chunks.")
            else:
                logger.info(f"Embeddings upserted to Chroma for {len(embeddings)} chunks.")
                # TODO: Implement Chroma upsert and FAISS upsert
        except Exception as e:
            logger.error(f"Error upserting embeddings to Pinecone: {e}")
            continue

        





