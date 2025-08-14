def token_chunk(text: str, token_count: int = 7000, overlap: int = 300, encoding_name: str = "cl100k_base") -> list[str]:
    import tiktoken
    """
    Chunk text by tokens.

    Args:
        text: str The text to chunk.
        token_count: int The number of tokens to include in each chunk. Set to 7000 by default.
        overlap: int The number of tokens to overlap between chunks. Set to 300 by default.
        encoding_name: str The encoding to use. Set to "cl100k_base" by default. Other options are "p50k_base" and "r50k_base".

    Returns:
        list[str] The chunks of text.
    """
    if token_count < overlap:
        raise ValueError("token_count must be greater than overlap")
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)
    total_tokens = len(tokens)
    chunks = []
    start = 0
    while start < total_tokens:
        end = min(start + token_count, total_tokens)
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
        if end == total_tokens:
            break
        start = end - overlap
    return chunks


def semantic_chunk(text: str, embedding_model: str = "text-embedding-3-small", breakpoint_threshold_type: str = "percentile") -> list[str]:
    """
    Chunk text by semantic similarity.

    Args:
        text: str The text to chunk.
        embedding_model: str The embedding model to use. Set to "text-embedding-3-small" by default. Other options are "text-embedding-3-large" for OpenAI and "gemini-embedding-001" for Gemini.
        breakpoint_threshold_type: str The type of breakpoint threshold to use. Set to "percentile" by default. Other options are "standard_deviation", "interquartile" and "gradient".

    Returns:
        list[str] The chunks of text.
    """
    from langchain_experimental.text_splitter import SemanticChunker

    # Initialize the appropriate embedding model object
    if embedding_model.startswith("text-embedding"):
        # OpenAI embedding models
        from langchain_openai import OpenAIEmbeddings
        embeddings = OpenAIEmbeddings(model=embedding_model)
    elif embedding_model.startswith("gemini"):
        # Google Gemini embedding models
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        embeddings = GoogleGenerativeAIEmbeddings(model=embedding_model)
    else:
        # Fallback to OpenAI for unknown models
        from langchain_openai import OpenAIEmbeddings
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    splitter = SemanticChunker(
        embeddings,
        breakpoint_threshold_type=breakpoint_threshold_type)

    docs = splitter.create_documents([text])
    chunks = []
    for doc in docs:
        chunks.append(doc.page_content)
    return chunks


def line_chunk(text: str, line_count: int = 100, overlap: int = 10) -> list[str]:
    """
    Chunk text by line.

    Args:
        text: str The text to chunk.
        line_count: int The number of lines to include in each chunk. Set to 100 by default.
        overlap: int The number of lines to overlap between chunks. Set to 10 by default.

    Returns:
        list[str] The chunks of text.
    """
    lines = text.splitlines()
    total_lines = len(lines)
    step = line_count - overlap
    if step <= 0:
        raise ValueError("line_count must be greater than overlap")
    chunks = []
    for i in range(0, total_lines, step):
        start = i
        end = min(start + line_count, total_lines)
        chunk_lines = lines[start:end]
        chunk_text = "\n".join(chunk_lines)
        chunks.append(chunk_text)
    return chunks


def recursive_chunk(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """
    Chunk text recursively.

    Args:
        text: str The text to chunk.
        chunk_size: int The size of the chunks to create. Set to 1000 by default.
        overlap: int The number of characters to overlap between chunks. Set to 100 by default.

    Returns:
        list[str] The chunks of text.
    """
    from langchain_experimental.text_splitter import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap
    )
    docs = splitter.create_documents([text])
    chunks = []
    for doc in docs:
        chunks.append(doc.page_content)
    return chunks
