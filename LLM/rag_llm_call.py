#!/usr/bin/env python3
"""
RAG Chatbot with GPT-4.1 function calling and multi-turn support, with streaming capabilities.
Integrates the optimized RAG search pipeline for document-based question answering.
"""
from dotenv import load_dotenv
load_dotenv()
import os
import json
import asyncio
import sys
from typing import AsyncGenerator, Dict, Any, List, Optional
from openai import OpenAI, AsyncOpenAI

# Import the RAG search function
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_retrieval import rag_search

# Initialize OpenAI clients
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# For debugging - set to True to print debug info (tool-call events only)
DEBUG = True

def debug_print(*args, **kwargs):
    """Print debug information if DEBUG is True"""
    if DEBUG:
        print("[DEBUG]", *args, file=sys.stderr, **kwargs)

# Global variables for RAG configuration (will be set during initialization)
RAG_CONFIG = {
    'user_id': None,
    'namespace': None,
    'embedding_model': None
}

def initialize_rag_config(user_id: str, namespace: str, embedding_model: str):
    """Initialize RAG configuration for the chatbot session"""
    global RAG_CONFIG
    RAG_CONFIG['user_id'] = user_id
    RAG_CONFIG['namespace'] = namespace
    RAG_CONFIG['embedding_model'] = embedding_model
    print(f"✅ RAG Configuration initialized:")
    print(f"   👤 User ID: {user_id}")
    print(f"   🏷️  Namespace: {namespace}")
    print(f"   🤖 Embedding Model: {embedding_model}")

def rag_search_tool(query: str) -> str:
    """
    Wrapper function for rag_search that uses the global configuration
    
    Args:
        query: User's search query
        
    Returns:
        Formatted string containing relevant document chunks
    """
    if not all(RAG_CONFIG.values()):
        return "Error: RAG system not properly initialized. Please contact support."
    
    try:
        result = rag_search(
            query=query,
            user_id=RAG_CONFIG['user_id'],
            namespace=RAG_CONFIG['namespace'],
            embedding_model=RAG_CONFIG['embedding_model'],
            top_k=5  # Default to top 5 results
        )
        return result
    except Exception as e:
        return f"Error retrieving documents: {str(e)}"

# Define function schema for GPT-4.1
tools = [
    {
        "type": "function",
        "name": "rag_search_tool",
        "description": "Search the user's uploaded documents for relevant information based on a query. Use this to find specific information from the user's document collection to answer their questions accurately.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string", 
                    "description": "The search query to find relevant information from the user's documents. Should be specific and focused on the information needed to answer the user's question."
                }
            },
            "required": ["query"],
            "additionalProperties": False
        },
        "strict": True
    }
]

# System prompt for the RAG chatbot
SYSTEM_PROMPT = (
    "# Identity\n"
    "You are a Personal Document Assistant, an AI agent that helps users find and understand information from their uploaded documents.\n\n"
    "# Instructions\n"
    "## PERSISTENCE\n"
    "You are an agent—keep working until the user's query is fully resolved. Only stop when you're sure the question is answered completely.\n"
    "## TOOL CALLING\n"
    "Use the rag_search_tool function to search the user's documents for relevant information. Do NOT guess or hallucinate information about the user's documents."
    " Always search their documents first before providing answers about document content.\n"
    "## SEARCH STRATEGY\n"
    "- Use specific search queries that target the information the user is asking about\n"
    "- If the first search doesn't provide complete information, try different search terms\n"
    "- Combine information from multiple searches if needed to provide comprehensive answers\n"
    "## RESPONSE STYLE\n"
    "- Provide clear, accurate answers based on the retrieved document content\n"
    "- Always cite which documents or sections your information comes from\n"
    "- If information is not found in the documents, clearly state this\n"
    "- Be helpful and conversational while staying accurate to the source material\n"
    "## PLANNING\n"
    "Plan extensively: decide whether to search, what to search for, reflect on results, then finalize the answer.\n"
)

MAX_TOOL_CALLS = 4

def ask_rag_assistant(history: list, query: str) -> str:
    """
    Ask GPT-4.1 to search documents and provide answers using the RAG tool.
    Supports multi-turn context by including the last 8 turns of user/assistant.
    Allows up to MAX_TOOL_CALLS sequential invocations before finalizing.
    """
    # Initialize message history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Include last 8 user-assistant exchanges
    for turn in history[-8:]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    
    # Add current user query
    messages.append({"role": "user", "content": query})

    tool_calls = 0
    final_response = None

    while tool_calls < MAX_TOOL_CALLS:
        # Send to GPT-4.1 with function schema
        resp = client.responses.create(
            model="gpt-4.1",
            input=messages,
            tools=tools
        )
        
        # Check for function call
        func_call = next((item for item in resp.output if item.type == "function_call"), None)
        if not func_call:
            # No more function calls; capture text and break
            final_response = resp.output_text
            break

        # Execute the function
        debug_print(f"Executing function call: {func_call.name}")
        args = json.loads(func_call.arguments)
        result = rag_search_tool(args.get("query"))
        debug_print(f"Function returned result length: {len(result)}")

        # Append the function call and its output
        messages.append({
            "type": "function_call",
            "name": func_call.name,
            "call_id": func_call.call_id,
            "arguments": func_call.arguments
        })
        messages.append({
            "type": "function_call_output",
            "call_id": func_call.call_id,
            "output": result
        })

        tool_calls += 1
        # If reached max calls, exit loop to finalize
        if tool_calls >= MAX_TOOL_CALLS:
            debug_print(f"Reached max tool calls: {MAX_TOOL_CALLS}")
            # Ask GPT to finalize answer without new calls
            closing = client.responses.create(
                model="gpt-4.1",
                input=messages,
                tools=tools
            )
            final_response = closing.output_text
            break
        # Otherwise, loop back to allow next call

    # Fallback: if loop finishes without setting, use last response text
    if final_response is None:
        final_response = resp.output_text

    return final_response

async def ask_rag_assistant_stream(history: list, query: str) -> AsyncGenerator[str, None]:
    """
    Streaming version of ask_rag_assistant.
    Returns an async generator that yields content deltas as they're received.
    Tool calls are still processed synchronously before streaming the final response.
    """
    
    # Initialize message history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Include last 8 user-assistant exchanges
    for turn in history[-8:]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    
    # Add current user query
    messages.append({"role": "user", "content": query})

    tool_calls = 0
    final_messages = messages.copy()
    
    debug_print(f"Processing tool calls for query: {query}")

    while tool_calls < MAX_TOOL_CALLS:
        debug_print(f"Checking for tool call {tool_calls+1}/{MAX_TOOL_CALLS}")
        
        # Send to GPT-4.1 with function schema
        resp = client.responses.create(
            model="gpt-4.1",
            input=messages,
            tools=tools
        )
        
        # Check for function call
        func_call = next((item for item in resp.output if item.type == "function_call"), None)
        if not func_call:
            # No more function calls; prepare for streaming
            break

        # Execute the function
        debug_print(f"Executing function call: {func_call.name}")
        args = json.loads(func_call.arguments)
        result = rag_search_tool(args.get("query"))
        debug_print(f"Function returned result length: {len(result)}")

        # Append the function call and its output
        function_call_msg = {
            "type": "function_call",
            "name": func_call.name,
            "call_id": func_call.call_id,
            "arguments": func_call.arguments
        }
        function_output_msg = {
            "type": "function_call_output",
            "call_id": func_call.call_id,
            "output": result
        }
        
        messages.append(function_call_msg)
        messages.append(function_output_msg)
        final_messages.append(function_call_msg)
        final_messages.append(function_output_msg)

        tool_calls += 1
        if tool_calls >= MAX_TOOL_CALLS:
            debug_print(f"Reached max tool calls: {MAX_TOOL_CALLS}")
            break

    # Stream the final response
    try:
        stream = await async_client.responses.create(
            model="gpt-4.1-mini-2025-04-14",
            input=final_messages,
            tools=tools,
            stream=True
        )
        
        got_content = False
        
        async for event in stream:
            if event.type == "response.output_text.delta":
                got_content = True
                yield event.delta
            elif event.type == "text_delta":
                got_content = True
                yield event.delta
            elif event.type == "content_part_added":
                if event.content_part.type == "text":
                    got_content = True
                    yield event.content_part.text
            elif event.type == "text_done":
                pass
            elif event.type == "content_part_done":
                pass
            elif event.type == "function_call":
                pass
            else:
                pass
        
        # If no content was streamed, yield a fallback message
        if not got_content:
            # Get a non-streaming response as fallback
            fallback_resp = client.responses.create(
                model="gpt-4.1-mini-2025-04-14",
                input=final_messages,
                tools=tools
            )
            yield fallback_resp.output_text or "I'm sorry, I couldn't generate a response. Please try again."
    except Exception:
        # Fallback on stream error
        fallback_resp = client.responses.create(
            model="gpt-4.1-mini-2025-04-14",
            input=final_messages,
            tools=tools
        )
        yield fallback_resp.output_text

def start_rag_chat_session(user_id: str, namespace: str, embedding_model: str):
    """
    Start an interactive RAG chat session with the user
    
    Args:
        user_id: MongoDB ObjectId string of the user
        namespace: Document namespace (without user_id suffix)
        embedding_model: Embedding model used for the documents
    """
    # Initialize RAG configuration
    initialize_rag_config(user_id, namespace, embedding_model)
    
    print("\n" + "=" * 80)
    print("🤖 PERSONAL DOCUMENT ASSISTANT")
    print("=" * 80)
    print("Your documents have been processed and I'm ready to help!")
    print("Ask me anything about your uploaded documents.")
    print("Type 'exit' or 'quit' to end the session.")
    print("=" * 80)
    
    # Start conversation loop
    conversation_history = []
    
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("\n👋 Thank you for using the Personal Document Assistant. Goodbye!")
                break
                
            if not user_input:
                print("Please enter a question about your documents.")
                continue
            
            print("\n🔍 Searching your documents...")
            
            # Get response from RAG assistant
            assistant_response = ask_rag_assistant(conversation_history, user_input)
            
            print(f"\n🤖 Assistant: {assistant_response}")
            
            # Add to conversation history
            conversation_history.append({
                "user": user_input,
                "assistant": assistant_response
            })
            
        except KeyboardInterrupt:
            print("\n\n👋 Session ended by user. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or contact support.")

# For backward compatibility and testing
if __name__ == "__main__":
    # Test mode - requires manual configuration
    print("🧪 RAG Assistant Test Mode")
    print("Note: In production, this will be called from the master pipeline")
    
    # Example configuration (would normally come from the pipeline)
    test_user_id = input("Enter user ID: ").strip()
    test_namespace = input("Enter namespace: ").strip()
    test_embedding_model = input("Enter embedding model (text-embedding-3-small/gemini-embedding-001): ").strip()
    
    if test_user_id and test_namespace and test_embedding_model:
        start_rag_chat_session(test_user_id, test_namespace, test_embedding_model)
    else:
        print("❌ All fields are required for testing.")