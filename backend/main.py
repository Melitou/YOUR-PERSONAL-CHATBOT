import logging
from embedding_service import EmbeddingService
from pinecone_service import PineconeService
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

CHUNK_BATCH_SIZE = 5

if __name__ == "__main__":
    
    embedding_service = EmbeddingService()
    pinecone_service = PineconeService()

    chunks = []
    for batch_start in range(0, len(chunks), CHUNK_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + CHUNK_BATCH_SIZE]

        # We already have the summaries for each chunk
        # so we can use them to embed the chunks
        # chunk_summaries = [chunk.summary_raw for chunk in batch]
        
        # Take for each chunk, the summary and the text and combine 
        # them in one string following the format:
        # "Summary: <summary> Text: <text>"
        chunk_summaries = [chunk.summary_raw for chunk in batch]
        chunk_texts = [chunk.text for chunk in batch]
        chunk_texts_with_summaries = [f"Summary: {summary} \nText: {text}" for summary, text in zip(chunk_summaries, chunk_texts)]

        logger.info(f"Embedding {len(chunk_texts_with_summaries)} chunks (summaries together with texts).")

        # Batch-embed this chunk batch
        try:
            embeddings = embedding_service._create_embeddings_batch(chunk_texts_with_summaries, "text-embedding-3-small", 3)
        except Exception as e:
            logger.error(f"Error embedding chunk summaries: {e}")
            continue
        
        # Now we have the embeddings for the chunk summaries
        





