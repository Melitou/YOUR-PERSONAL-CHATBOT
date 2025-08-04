#!/usr/bin/env python3
"""
IASPIS Search Module - Retrieves relevant chunks from Pinecone using semantic search
"""

import os
import json
from typing import List, Dict, Any
from openai import OpenAI
from google import genai
from pinecone import Pinecone
from dotenv import load_dotenv
from bson import ObjectId
from db_service import Chunks, initialize_db

load_dotenv()

# Initialize clients
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))


def get_embedding(text: str, model: str = "gemini-embedding-001") -> List[float]:
    """
    Generate an embedding for the given text using Gemini embedding model.

    Args:
        text: The input text to embed
        model: The embedding model to use

    Returns:
        List of float values representing the embedding vector
    """
    response = client.models.embed_content(
        contents=text,
        model=model
    )
    return response.embeddings[0].values


def search_rag(query: str, namespace: str, index_name: str = "chatbot-vectors-google",
               embedding_model: str = "gemini-embedding-001", top_k: int = 9, top_reranked: int = 4) -> str:
    """
    Search for relevant chunks in the Pinecone index based on the query.
    Retrieves top_k results and reranks using Cohere to select top_reranked.

    Args:
        query: User query string
        namespace: Pinecone namespace to search in
        index_name: Pinecone index name
        embedding_model: Gemini embedding model to use
        top_k: Number of chunks to retrieve initially
        top_reranked: Number of chunks to keep after reranking

    Returns:
        Formatted string containing the top reranked chunks with their IDs and content
    """
    try:
        # Get embedding for the query
        query_embedding = get_embedding(query, embedding_model)

        # Connect directly to the existing index
        index = pc.Index(index_name)

        # Query the index
        query_response = index.query(
            namespace=namespace,
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            include_values=False
        )

        # First, retrieve full content from MongoDB for all matches
        chunk_object_ids = []
        for match in query_response.matches:
            try:
                chunk_object_ids.append(ObjectId(match.id))
            except Exception:
                continue

        # Initialize database connection
        initialize_db()

        # Query MongoDB for full chunk data
        chunks = Chunks.objects(id__in=chunk_object_ids)
        chunk_dict = {str(chunk.id): chunk for chunk in chunks}

        # Prepare documents for reranking using full content and summary
        documents = []
        doc_mapping = {}

        for match in query_response.matches:
            chunk_id = match.id
            chunk = chunk_dict.get(chunk_id)

            if not chunk:
                continue  # Skip if chunk not found in MongoDB

            # Use full content and summary for reranking (much better than previews)
            full_content = chunk.content if chunk.content else ""
            full_summary = chunk.summary if chunk.summary else ""

            # Combine summary and content for optimal reranking
            if full_summary.strip() and full_content.strip():
                doc_text = f"Summary: {full_summary}\n\nContent: {full_content}"
            elif full_summary.strip():
                doc_text = full_summary
            elif full_content.strip():
                doc_text = full_content
            else:
                continue  # Skip empty chunks

            if doc_text.strip():  # Only add non-empty documents
                documents.append(doc_text)
                # Map the document back to its original match
                doc_mapping[doc_text] = match

        # Check if we have any documents to rerank
        if not documents:
            return "No relevant documents found for the query."

        # Apply Cohere reranking
        reranked_results = pc.inference.rerank(
            model="cohere-rerank-3.5",
            query=query,
            documents=documents,
            top_n=top_reranked,
            return_documents=True
        )

        # Get chunk IDs for MongoDB retrieval
        chunk_ids = []
        reranked_matches = []
        for reranked in reranked_results.data:
            original_match = doc_mapping[reranked.document.text]
            chunk_ids.append(original_match.id)
            reranked_matches.append((original_match, reranked.score))

        # We already have the chunk data from earlier MongoDB retrieval
        # No need to query again

        # Format results with full content and summary
        results = []
        for i, (original_match, score) in enumerate(reranked_matches):
            chunk_id = original_match.id
            metadata = original_match.metadata or {}

            # Get full chunk data from MongoDB
            chunk = chunk_dict.get(chunk_id)
            if not chunk:
                continue  # Skip if chunk not found in MongoDB

            # Extract metadata elements
            source_file = metadata.get("file_name", "") or chunk.file_name

            # Use full content and summary from MongoDB
            full_content = chunk.content if chunk.content else ""
            full_summary = chunk.summary if chunk.summary else ""

            # Format the chunk with full data for LLM consumption
            chunk_text = f"Document {i+1}:\n\n"
            chunk_text += f"**Source File**: {source_file}\n"
            chunk_text += f"**Chunk Index**: {chunk.chunk_index + 1}\n"
            chunk_text += f"**Relevance Score**: {score:.4f}\n\n"

            if full_summary.strip():
                chunk_text += f"**Summary**: {full_summary}\n\n"

            chunk_text += f"**Full Content**: {full_content}\n\n"
            chunk_text += "---\n"

            results.append(chunk_text)

        # Combine all chunks
        final_text = "\n".join(results)

        return final_text

    except Exception as e:
        return f"Error performing search: {str(e)}"


def test_search():
    """Test function to demonstrate usage"""
    query = "summarise alice in wonderland?"
    namespace = "ex_6889c26368f5b07f9550e806"
    print("\nSearching for:", query)
    print("\nResults:")
    print("="*80)
    results = search_rag(query, namespace)
    print(results)
    print("="*80)


if __name__ == "__main__":
    # Test the search function
    test_search()
