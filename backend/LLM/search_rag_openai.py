#!/usr/bin/env python3
"""
IASPIS Search Module - Retrieves relevant chunks from Pinecone using semantic search with OpenAI embeddings
"""

import os
import json
from typing import List, Dict, Any
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv
from bson import ObjectId
from db_service import Chunks, initialize_db
import logging

# Import keyword extractor for query enhancement
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keyword_extractor import KeywordExtractor

logger = logging.getLogger(__name__)

load_dotenv()

# Initialize clients
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

# Initialize keyword extractor for query enhancement
keyword_extractor = KeywordExtractor()


def get_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    Generate an embedding for the given text using OpenAI embedding model.
    Args:
        text: The input text to embed
        model: The embedding model to use
    Returns:
        List of float values representing the embedding vector
    """
    response = client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding


def apply_hybrid_keyword_boosting(semantic_matches, query_keywords: List[str], 
                                 chunk_dict: Dict, boost_factor: float = 0.3) -> List[str]:
    """
    Apply keyword-based boosting to semantic search results.
    
    Args:
        semantic_matches: Pinecone search matches
        query_keywords: Extracted keywords from user query
        chunk_dict: Dictionary mapping chunk IDs to chunk objects
        boost_factor: How much to boost scores for keyword matches (0.0 to 1.0)
        
    Returns:
        List of document texts with enhanced scoring for reranking
    """
    enhanced_documents = []
    
    for match in semantic_matches:
        chunk_id = match.id
        chunk = chunk_dict.get(chunk_id)
        
        if not chunk:
            continue
            
        # Get chunk content and keywords
        chunk_content = chunk.content if chunk.content else ""
        chunk_summary = chunk.summary if chunk.summary else ""
        chunk_keywords = chunk.keywords if hasattr(chunk, 'keywords') and chunk.keywords else []
        
        # Calculate keyword match score
        keyword_matches = 0
        total_query_keywords = len(query_keywords)
        
        if total_query_keywords > 0 and (chunk_keywords or chunk_content):
            # Check matches in chunk keywords
            chunk_keywords_lower = [kw.lower() for kw in chunk_keywords]
            
            for query_kw in query_keywords:
                query_kw_lower = query_kw.lower()
                
                # Direct keyword match
                if query_kw_lower in chunk_keywords_lower:
                    keyword_matches += 1
                # Partial match in content (fallback)
                elif query_kw_lower in chunk_content.lower():
                    keyword_matches += 0.5
                # Partial match in summary (fallback)
                elif query_kw_lower in chunk_summary.lower():
                    keyword_matches += 0.3
            
            # Calculate keyword score (0.0 to 1.0)
            keyword_score = min(keyword_matches / total_query_keywords, 1.0)
        else:
            keyword_score = 0.0
        
        # Apply boosting to semantic score
        original_score = match.score
        enhanced_score = original_score + (keyword_score * boost_factor)
        
        # Prepare document for reranking with enhanced context
        doc_text = ""
        if chunk_summary.strip() and chunk_content.strip():
            doc_text = f"Summary: {chunk_summary}\n\nContent: {chunk_content}"
        elif chunk_summary.strip():
            doc_text = chunk_summary
        elif chunk_content.strip():
            doc_text = chunk_content
        
        # Add keyword match info for debugging (will be used during reranking)
        if keyword_score > 0:
            doc_text = f"[Keyword Score: {keyword_score:.2f}] {doc_text}"
            
        enhanced_documents.append(doc_text)
    
    return enhanced_documents

# Original
# def search_rag(query: str, namespace: str, index_name: str = None,
#                embedding_model: str = "text-embedding-3-small", top_k: int = 9, top_reranked: int = 4) -> str:
#     """
#     Search for relevant chunks in the Pinecone index based on the query.
#     Retrieves top_k results and reranks using Cohere to select top_reranked.

#     Args:
#         query: User query string
#         namespace: Pinecone namespace to search in
#         index_name: Pinecone index name
#         embedding_model: OpenAI embedding model to use
#         top_k: Number of chunks to retrieve initially
#         top_reranked: Number of chunks to keep after reranking

#     Returns:
#         Formatted string containing the top reranked chunks with their IDs and content
#     """
#     try:
#         # Get embedding for the query
#         query_embedding = get_embedding(query, embedding_model)

#         # Connect directly to the existing index
#         index = pc.Index(index_name)

#         # Query the index
#         query_response = index.query(
#             namespace=namespace,
#             vector=query_embedding,
#             top_k=top_k,
#             include_metadata=True,
#             include_values=False
#         )

#         # First, retrieve full content from MongoDB for all matches
#         chunk_object_ids = []
#         for match in query_response.matches:
#             try:
#                 chunk_object_ids.append(ObjectId(match.id))
#             except Exception:
#                 continue

#         # Initialize database connection
#         initialize_db()

#         # Query MongoDB for full chunk data
#         chunks = Chunks.objects(id__in=chunk_object_ids)
#         chunk_dict = {str(chunk.id): chunk for chunk in chunks}

#         # Prepare documents for reranking using full content and summary
#         documents = []
#         doc_mapping = {}

#         for match in query_response.matches:
#             chunk_id = match.id
#             chunk = chunk_dict.get(chunk_id)

#             if not chunk:
#                 continue  # Skip if chunk not found in MongoDB

#             # Use full content and summary for reranking (much better than previews)
#             full_content = chunk.content if chunk.content else ""
#             full_summary = chunk.summary if chunk.summary else ""

#             # Combine summary and content for optimal reranking
#             if full_summary.strip() and full_content.strip():
#                 doc_text = f"Summary: {full_summary}\n\nContent: {full_content}"
#             elif full_summary.strip():
#                 doc_text = full_summary
#             elif full_content.strip():
#                 doc_text = full_content
#             else:
#                 continue  # Skip empty chunks

#             if doc_text.strip():  # Only add non-empty documents
#                 documents.append(doc_text)
#                 # Map the document back to its original match
#                 doc_mapping[doc_text] = match

#         # Check if we have any documents to rerank
#         if not documents:
#             return "No relevant documents found for the query."

#         # Apply Cohere reranking
#         try:
#             reranked_results = pc.inference.rerank(
#                 model="cohere-rerank-3.5",
#                 query=query,
#                 documents=documents,
#                 top_n=top_reranked,
#                 return_documents=True
#             )
#         except Exception as rerank_error:
#             # Fallback: use original results without reranking
#             print(f"Reranking failed, using original results: {rerank_error}")
#             reranked_matches = [(match, match.score) for match in query_response.matches[:top_reranked]]
#             chunk_ids = [match.id for match in query_response.matches[:top_reranked]]
#             return format_results_without_reranking(query_response.matches[:top_reranked], chunk_dict)

#         # Get chunk IDs for MongoDB retrieval
#         chunk_ids = []
#         reranked_matches = []
#         for reranked in reranked_results.data:
#             original_match = doc_mapping[reranked.document.text]
#             chunk_ids.append(original_match.id)
#             reranked_matches.append((original_match, reranked.score))

#         # We already have the chunk data from earlier MongoDB retrieval
#         # No need to query again

#         # Format results with full content and summary
#         results = []
#         for i, (original_match, score) in enumerate(reranked_matches):
#             chunk_id = original_match.id
#             metadata = original_match.metadata or {}

#             # Get full chunk data from MongoDB
#             chunk = chunk_dict.get(chunk_id)
#             if not chunk:
#                 continue  # Skip if chunk not found in MongoDB

#             # Extract metadata elements
#             source_file = metadata.get("file_name", "") or chunk.file_name

#             # Use full content and summary from MongoDB
#             full_content = chunk.content if chunk.content else ""
#             full_summary = chunk.summary if chunk.summary else ""

#             # Format the chunk with full data for LLM consumption
#             chunk_text = f"Document {i+1}:\n\n"
#             chunk_text += f"**Source File**: {source_file}\n"
#             chunk_text += f"**Chunk Index**: {chunk.chunk_index + 1}\n"
#             chunk_text += f"**Relevance Score**: {score:.4f}\n\n"

#             if full_summary.strip():
#                 chunk_text += f"**Summary**: {full_summary}\n\n"

#             chunk_text += f"**Full Content**: {full_content}\n\n"
#             chunk_text += "---\n"

#             results.append(chunk_text)

#         # Combine all chunks
#         final_text = "\n".join(results)

#         return final_text

#     except Exception as e:
#         return f"Error performing search: {str(e)}"

# New
def search_rag(query: str, namespace: str, index_name: str = None,
               embedding_model: str = "text-embedding-3-small", top_k: int = 9, 
               top_reranked: int = 4, keyword_boost_factor: float = 0.3, 
               use_keyword_enhancement: bool = False) -> str:
    """
    Search for relevant chunks in the Pinecone index.
    Retrieves top_k results, reranks using Cohere, and (optionally) adjusts scores using keyword overlap.
    """
    try:
        # 1. Get embedding for query
        query_embedding = get_embedding(query, embedding_model)

        # 2. Connect to Pinecone
        index = pc.Index(index_name)

        # 3. Query Pinecone
        query_response = index.query(
            namespace=namespace,
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter={"keywords": {"$in": query_keywords}},
            include_values=False
        )

        # 4. Collect MongoDB chunks
        chunk_object_ids = []
        for match in query_response.matches:
            try:
                chunk_object_ids.append(ObjectId(match.id))
            except Exception:
                continue

        initialize_db()
        chunks = Chunks.objects(id__in=chunk_object_ids)
        chunk_dict = {str(chunk.id): chunk for chunk in chunks}

        # 5. Build documents for reranker
        documents, doc_mapping = [], {}
        for match in query_response.matches:
            chunk = chunk_dict.get(match.id)
            if not chunk:
                continue

            full_content = (chunk.content or "").strip()
            full_summary = (chunk.summary or "").strip()

            if full_summary and full_content:
                doc_text = f"Summary: {full_summary}\n\nContent: {full_content}"
            else:
                doc_text = full_summary or full_content

            if not doc_text:
                continue

            documents.append(doc_text)
            doc_mapping[doc_text] = match

        if not documents:
            return "No relevant documents found."

        # 6. Cohere rerank
        try:
            reranked_results = pc.inference.rerank(
                model="cohere-rerank-3.5",
                query=query,
                documents=documents,
                top_n=top_reranked,
                return_documents=True
            )
        except Exception as rerank_error:
            print(f"Reranking failed, fallback: {rerank_error}")
            return format_results_without_reranking(query_response.matches[:top_reranked], chunk_dict)

        # 7. Optional keyword enhancement
        reranked_matches = []
        if use_keyword_enhancement:
            query_keywords = [kw.lower() for kw in query.split()]

            def keyword_overlap(query_kws, chunk_kws):
                q = set(query_kws)
                c = set([kw.lower() for kw in chunk_kws or []])
                if not q or not c:
                    return 0.0
                return len(q & c) / len(q)  # fraction of query kws found in chunk

            for reranked in reranked_results.data:
                match = doc_mapping[reranked.document.text]
                chunk = chunk_dict.get(match.id)
                if not chunk:
                    continue

                chunk_kws = getattr(chunk, "keywords", []) or []
                ov = keyword_overlap(query_keywords, chunk_kws)

                adjusted_score = reranked.score * (1 + ov * keyword_boost_factor)
                reranked_matches.append((match, adjusted_score, ov))

            reranked_matches.sort(key=lambda x: x[1], reverse=True)
        else:
            # Keep Cohere scores directly, with ov=0
            for reranked in reranked_results.data:
                match = doc_mapping[reranked.document.text]
                if not match:
                    continue
                reranked_matches.append((match, reranked.score, 0.0))

        # 8. Take top results
        reranked_matches = reranked_matches[:top_reranked]

        # 9. Format results
        results = []
        for i, (match, score, ov) in enumerate(reranked_matches, 1):
            chunk = chunk_dict.get(match.id)
            if not chunk:
                continue

            source_file = match.metadata.get("file_name", "") or chunk.file_name
            full_summary = (chunk.summary or "").strip()
            full_content = (chunk.content or "").strip()

            chunk_text = f"Document {i}:\n\n"
            chunk_text += f"**Source File**: {source_file}\n"
            chunk_text += f"**Chunk Index**: {chunk.chunk_index + 1}\n"
            chunk_text += f"**Final Score**: {score:.4f}"
            if use_keyword_enhancement:
                chunk_text += f" (overlap={ov:.2f})"
            chunk_text += "\n\n"
            if full_summary:
                chunk_text += f"**Summary**: {full_summary}\n\n"
            if full_content:
                chunk_text += f"**Full Content**: {full_content}\n\n"
            chunk_text += "---\n"

            results.append(chunk_text)

        return "\n".join(results)

    except Exception as e:
        return f"Error performing search: {str(e)}"





def format_results_without_reranking(matches, chunk_dict):
    """
    Format results without reranking when the reranking service is unavailable
    
    Args:
        matches: List of Pinecone matches
        chunk_dict: Dictionary of chunk data from MongoDB
        
    Returns:
        Formatted string with chunk information
    """
    results = []
    for i, match in enumerate(matches):
        chunk_id = match.id
        metadata = match.metadata or {}

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
        chunk_text += f"**Relevance Score**: {match.score:.4f}\n\n"

        if full_summary.strip():
            chunk_text += f"**Summary**: {full_summary}\n\n"

        chunk_text += f"**Full Content**: {full_content}\n\n"
        chunk_text += "---\n"

        results.append(chunk_text)

    # Combine all chunks
    final_text = "\n".join(results)
    return final_text


# def test_search():
#     """Test function to demonstrate usage"""
#     query = "tell me something about ai by dna?"
#     namespace = "test_688b48416faad142f66ca95e"
#     print("\nSearching for:", query)
#     print("\nResults:")
#     print("="*80)
#     results = search_rag(query, namespace)
#     print(results)
#     print("="*80)


if __name__ == "__main__":
    # Test the search function
    #test_search()
    pass
