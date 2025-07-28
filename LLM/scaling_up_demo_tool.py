#!/usr/bin/env python3
"""
IASPIS Search Module - Retrieves relevant chunks from Pinecone using semantic search
"""

import os
import json
from typing import List, Dict, Any
from openai import OpenAI
from pinecone import Pinecone

# Configuration
INDEX_NAME = "scaling-up"
NAMESPACE = "scaling-up-demo"
EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 9  # Number of chunks to retrieve
TOP_RERANKED = 4  # Number of chunks to keep after reranking

# Initialize clients
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

def get_embedding(text: str) -> List[float]:
    """
    Generate an embedding for the given text using OpenAI's text-embedding-3-small model.
    
    Args:
        text: The input text to embed
        
    Returns:
        List of float values representing the embedding vector
    """
    response = client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def scaling_up_search(query: str) -> str:
    """
    Search for relevant chunks in the Pinecone index based on the query.
    Retrieves TOP_K results and reranks using Cohere to select TOP_RERANKED.
    
    Args:
        query: User query string
        
    Returns:
        Formatted string containing the top k chunks with their IDs and content
    """
    try:
        # Get embedding for the query
        query_embedding = get_embedding(query)
        
        # Connect directly to the existing index
        index = pc.Index(INDEX_NAME)
        
        # Query the index
        query_response = index.query(
            namespace=NAMESPACE,
            vector=query_embedding,
            top_k=TOP_K,
            include_metadata=True,
            include_values=False
        )
        
        # Prepare documents for reranking
        documents = []
        doc_mapping = {}
        
        for i, match in enumerate(query_response.matches):
            chunk_id = match.id
            metadata = match.metadata or {}
            
            # Extract the text content to rerank
            contextual_summary = metadata.get("contextual_summary_preview", "")
            # Use this as the document for reranking
            doc_text = contextual_summary
            documents.append(doc_text)
            # Map the document back to its original match
            doc_mapping[doc_text] = match
        
        # Apply Cohere reranking
        reranked_results = pc.inference.rerank(
            model="cohere-rerank-3.5",
            query=query,
            documents=documents,
            top_n=TOP_RERANKED,
            return_documents=True
        )
        
        # Format results from reranked matches
        results = []
        for i, reranked in enumerate(reranked_results.data):
            # Get the original match using the mapping
            original_match = doc_mapping[reranked.document.text]
            
            # Extract metadata fields
            chunk_id = original_match.id
            score = reranked.score  # Use the reranked score
            metadata = original_match.metadata or {}
            
            # Extract specific metadata elements
            source_file = metadata.get("source_file", "")
            original_text = metadata.get("original_text_preview", "")
            contextual_summary = metadata.get("contextual_summary_preview", "")
            
            # Format the chunk
            chunk_text = f"{i+1}\n\n"
            chunk_text += f"##ID: {chunk_id}\n"
            chunk_text += f"##original_text: \"{original_text}\"\n"
            chunk_text += f"##contextual_summary: \"{contextual_summary}\"\n"
            chunk_text += f"##source_file: \"{source_file}\"\n"
            
            results.append(chunk_text)
        
        # Combine all chunks
        final_text = "\n".join(results)
        
        return final_text
        
    except Exception as e:
        return f"Error performing search: {str(e)}"

def test_search():
    """Test function to demonstrate usage"""
    query = "Unique identifier 563-456"
    print("\nSearching for:", query)
    print("\nResults:")
    print("="*80)
    results = scaling_up_search(query)
    print(results)
    print("="*80)

if __name__ == "__main__":
    # Test the search function
    test_search()