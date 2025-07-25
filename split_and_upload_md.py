import os
import asyncio
import logging
import tiktoken
import aiofiles  # async file operations
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai import OpenAIError
from pinecone import Pinecone, ServerlessSpec
from aiolimiter import AsyncLimiter
import backoff

load_dotenv()

# configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Configuration
PINECONE_API_KEY     = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY       = os.getenv("OPENAI_API_KEY")
MD_DIR               = "/Users/aparajitbhattacharya/Library/CloudStorage/OneDrive-Personal/MyDocuments/AI/IASPIS_AND_SCALING_UP/md"
CHECKPOINT_DIR       = os.path.join(MD_DIR, ".checkpoints")
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

INDEX_NAME           = "scaling-up"
NAMESPACE            = "scaling-up-demo-2"
EMBEDDING_MODEL      = "text-embedding-3-small"
EMBEDDING_DIMENSION  = 1536
SUMMARY_MODEL        = "gpt-4.1-mini"
ENCODING_NAME        = "cl100k_base"  # For tiktoken

# Rate limits
SUMMARY_RPM = 2000    # requests per minute for gpt-4.1-mini
EMBED_RPM   = 600     # safe default for embeddings

# Tiktoken Encoding
ENCODING = tiktoken.get_encoding(ENCODING_NAME)

# Concurrency & batch sizes
# Concurrency & batch sizes
FILE_CONCURRENCY = 20
CHUNK_BATCH_SIZE = 5
# Dynamically derive semaphores from rate limits (reqs/sec)
MAX_CONCURRENT_SUMMARIES = max(1, SUMMARY_RPM // 60)
MAX_CONCURRENT_EMBEDS = max(1, EMBED_RPM // 60)

# Clients & semaphores
summary_concurrency_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SUMMARIES)
embed_concurrency_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EMBEDS)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)
pc     = Pinecone(api_key=PINECONE_API_KEY)

# Pinecone index setup (sync, at startup)
# list_indexes returns list of index names (strings)
if INDEX_NAME not in pc.list_indexes():
    logger.info("Creating Pinecone index %s", INDEX_NAME)
    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBEDDING_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
else:
    logger.info("Pinecone index %s already exists", INDEX_NAME)
index = pc.Index(INDEX_NAME)

# Rate limiters
summary_rate_limiter = AsyncLimiter(SUMMARY_RPM, 60)
embed_rate_limiter   = AsyncLimiter(EMBED_RPM, 60)

# Prompts
DOCUMENT_CONTEXT_PROMPT = """
<document>
{doc_content}
</document>
"""

CHUNK_CONTEXT_PROMPT = """
Here is the chunk we want to situate within the whole document:
<chunk>
{chunk_content}
</chunk>

Please give a short, succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk.
Focus on what this specific chunk is about in relation to the entire document.
Answer only with the succinct context and nothing else.
"""

def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string using the global ENCODING."""
    return len(ENCODING.encode(string))

def chunk_markdown(text: str, max_tokens: int = 7000, overlap: int = 300):
    """Chunks markdown text into smaller pieces based on token count using the global ENCODING."""
    tokens = ENCODING.encode(text)
    chunks = []
    start = 0
    total_tokens = len(tokens)
    while start < total_tokens:
        end = min(start + max_tokens, total_tokens)
        chunk_tokens = tokens[start:end]
        chunk_text = ENCODING.decode(chunk_tokens)
        chunks.append(chunk_text)
        if end == total_tokens:
            break
        start = end - overlap # Recalculate start for the next chunk, considering overlap
    return chunks

@backoff.on_exception(backoff.expo,
                      OpenAIError,
                      max_tries=10,
                      max_time=300,
                      jitter=backoff.full_jitter)
async def generate_contextual_summary_async(doc_content: str, chunk_content: str) -> str:
    async with summary_concurrency_semaphore: # Added semaphore for concurrency control
        async with summary_rate_limiter: # Keep RPM limiter as well
            response = await client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert at summarizing text chunks in the context of a larger document."},
                    {"role": "user", "content": DOCUMENT_CONTEXT_PROMPT.format(doc_content=doc_content)},
                    {"role": "user", "content": CHUNK_CONTEXT_PROMPT.format(chunk_content=chunk_content)}
                ],
                max_tokens=150,
                temperature=0.2
            )
            return response.choices[0].message.content.strip()

@backoff.on_exception(backoff.expo,
                      OpenAIError,
                      max_tries=8,
                      max_time=240,
                      jitter=backoff.full_jitter)
async def get_batched_embeddings_with_retry_async(texts_for_embedding: list[str]) -> list[list[float]]:
    """Gets batched embeddings from OpenAI with retry logic."""
    if not texts_for_embedding:
        return []
    async with embed_concurrency_semaphore, embed_rate_limiter:
        response = await client.embeddings.create(
            input=texts_for_embedding,
            model=EMBEDDING_MODEL
        )
        return [data.embedding for data in response.data]

def upsert_vectors_to_pinecone(index, vectors_to_upsert):
    """Upserts a list of vectors to Pinecone in batches."""
    for i in range(0, len(vectors_to_upsert), 100):
        batch = vectors_to_upsert[i:i+100]
        index.upsert(vectors=batch, namespace=NAMESPACE)

async def upsert_vectors_to_pinecone_async(index, vectors_to_upsert, batch_size=100):
    """Async upserts a list of vectors to Pinecone in batches using threads."""
    tasks = []
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i+batch_size]
        # Revert to asyncio.to_thread for synchronous Pinecone client calls
        tasks.append(asyncio.to_thread(index.upsert, vectors=batch, namespace=NAMESPACE))
    await asyncio.gather(*tasks)

async def prepare_chunk_data_async(md_file: str, full_text: str, idx: int, chunk_text: str):
    """Generates summary for a chunk and prepares text for embedding and metadata parts."""
    summary = await generate_contextual_summary_async(full_text, chunk_text)
    text_for_embedding = f"{chunk_text}\n\nContextual summary: {summary}"
    
    # Prepare base metadata, embedding will be added later
    base_metadata = {
        "source_file": md_file,
        "chunk_id": idx,
        "original_text": chunk_text,
        # contextual_summary_preview will be added in process_file after embedding
        "Source": "Scaling_Up"
    }
    return summary, text_for_embedding, base_metadata, f"{md_file}_chunk_{idx}"

async def process_file(md_file: str):
    """Read, chunk, summarize, embed and upsert in micro-batches; write checkpoint on success."""
    checkpoint_path = os.path.join(CHECKPOINT_DIR, f"{md_file}.done")
    if os.path.exists(checkpoint_path):
        logger.info("Skipping %s (already processed)", md_file)
        return

    path = os.path.join(MD_DIR, md_file)
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            full_text = await f.read()
    except Exception as e:
        logger.error("Failed to read %s: %s", md_file, e)
        return

    chunks = chunk_markdown(full_text)
    if not chunks:
        logger.warning("No chunks generated for %s; skipping", md_file)
        open(checkpoint_path, "w").close()
        return

    logger.info("Processing %s: %d chunks", md_file, len(chunks))

    # Process in micro-batches to limit memory and isolate failures
    for batch_start in range(0, len(chunks), CHUNK_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + CHUNK_BATCH_SIZE]

        # 1) Summarize each chunk in the batch (isolate failures)
        tasks = [
            prepare_chunk_data_async(md_file, full_text, batch_start + idx, ch)
            for idx, ch in enumerate(batch)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        good = []
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(
                    "Chunk %d of %s failed to summarize: %s",
                    batch_start + idx,
                    md_file,
                    res,
                )
            else:
                good.append(res)

        if not good:
            logger.warning(
                "All chunks failed in batch %d–%d for %s; skipping batch",
                batch_start,
                batch_start + len(batch) - 1,
                md_file,
            )
            continue

        # 2) Batch-embed this chunk batch
        texts = [item[1] for item in good]
        try:
            embeddings = await get_batched_embeddings_with_retry_async(texts)
        except Exception as e:
            logger.error(
                "Embedding batch %d–%d for %s failed: %s",
                batch_start,
                batch_start + len(batch) - 1,
                md_file,
                e,
            )
            continue

        # 3) Build and upsert vectors immediately
        vectors = []
        for (summary, _, base_meta, chunk_id), embed in zip(good, embeddings):
            meta = {**base_meta, "contextual_summary": summary}
            vectors.append({"id": chunk_id, "values": embed, "metadata": meta})

        if vectors:
            logger.info(
                "Upserting %d vectors for %s (chunks %d–%d)",
                len(vectors),
                md_file,
                batch_start,
                batch_start + len(vectors) - 1,
            )
            try:
                await upsert_vectors_to_pinecone_async(index, vectors)
            except Exception as e:
                logger.error(
                    "Upsert failed for %s batch %d–%d: %s",
                    md_file,
                    batch_start,
                    batch_start + len(vectors) - 1,
                    e,
                )

    # Mark file as done for checkpointing
    open(checkpoint_path, "w").close()
    logger.info("Completed processing %s", md_file)

async def main():
    md_files = [f for f in os.listdir(MD_DIR) if f.lower().endswith(".md")]
    file_semaphore = asyncio.Semaphore(FILE_CONCURRENCY)

    async def _limited_process(md_file: str):
        async with file_semaphore:
            await process_file(md_file)

    tasks = [_limited_process(f) for f in md_files]
    await asyncio.gather(*tasks)
    logger.info("All markdown files processed and contextual embeddings uploaded to Pinecone.")

if __name__ == "__main__":
    asyncio.run(main())
