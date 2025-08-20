#!/usr/bin/env python3
"""
RAG Chatbot with GPT-4.1 function calling and multi-turn support, with streaming capabilities.
Integrates the optimized RAG search pipeline for document-based question answering.
"""
from rag_retrieval import RAGService
from openai import OpenAI, AsyncOpenAI
from google import genai
from typing import AsyncGenerator, Dict, Any, List, Optional
import sys
import asyncio
import json
import os
import tiktoken
import logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Import the RAG search function
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize OpenAI clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
openai_async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Gemini client
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Backward compatibility
client = openai_client
async_client = openai_async_client

# For debugging - set to True to print debug info (tool-call events only)
DEBUG = False

# Configure logging for token management
logging.basicConfig(level=logging.INFO)
token_logger = logging.getLogger("token_management")


def debug_print(*args, **kwargs):
    """Print debug information if DEBUG is True"""
    if DEBUG:
        print("[DEBUG]", *args, file=sys.stderr, **kwargs)


# Supported models configuration
OPENAI_MODELS = [
    "gpt-4.1", "gpt-4o", "gpt-4o-mini",
    "gpt-o3", "gpt-o3-pro", "gpt-o3-mini"
]

GEMINI_MODELS = [
    "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
    "gemini-2.0-flash", "gemini-2.0-flash-lite",
    "gemini-1.5-pro", "gemini-1.5-flash"
]

# Global variables for RAG configuration (will be set during initialization)
RAG_CONFIG = {
    'user_id': None,
    # namespace: None 
    'namespaces': [], # This is the new approach
    'embedding_model': None,
    'chatbot_model': None,
    'chatbot_description': None # Added for chatbot description
}


def validate_chatbot_model(model: str) -> bool:
    """
    Validate if the provided chatbot model is supported

    Args:
        model: Model name to validate

    Returns:
        True if model is supported, False otherwise
    """
    return model in OPENAI_MODELS or model in GEMINI_MODELS


def get_model_provider(model: str) -> str:
    """
    Get the provider (openai/gemini) for a given model

    Args:
        model: Model name

    Returns:
        'openai', 'gemini', or 'unknown'
    """
    if model in OPENAI_MODELS:
        return 'openai'
    elif model in GEMINI_MODELS:
        return 'gemini'
    else:
        return 'unknown'


def initialize_rag_config(user_id: str, namespaces: list, embedding_model: str, chatbot_model: str = "gpt-4.1", chatbot_description: str = None):
    """Initialize RAG configuration for the chatbot session

    Args:
        user_id: MongoDB ObjectId string of the user
        namespaces: List of document namespaces
        embedding_model: Embedding model used for the documents
        chatbot_model: Model to use for chat generation (default: gpt-4.1)
        chatbot_description: Custom description of what this chatbot is about
    """
    global RAG_CONFIG

    # Validate chatbot model
    if not validate_chatbot_model(chatbot_model):
        raise ValueError(
            f"Unsupported chatbot model: {chatbot_model}. Supported models: {OPENAI_MODELS + GEMINI_MODELS}")

    RAG_CONFIG['user_id'] = user_id
    RAG_CONFIG['namespaces'] = namespaces
    RAG_CONFIG['embedding_model'] = embedding_model
    RAG_CONFIG['chatbot_model'] = chatbot_model
    RAG_CONFIG['chatbot_description'] = chatbot_description

    provider = get_model_provider(chatbot_model)
    # Suppress verbose init prints in server mode
    pass


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

    # Keep debug logs suppressed in server mode
    pass

    try:
        rag_service = RAGService()
        result = rag_service.rag_search(
            query=query,
            user_id=RAG_CONFIG['user_id'],
            namespaces=RAG_CONFIG['namespaces'],
            embedding_model_of_chatbot_caller=RAG_CONFIG['embedding_model'],
            top_k=5  # Default to top 5 results
        )
        debug_print(f"✅ RAG Search returned result length: {len(result)}")
        return result
    except Exception as e:
        debug_print(f"❌ RAG Search error: {str(e)}")
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
    "## THINKING PROCESS\n"
    "Before answering, always think through your approach step by step:\n"
    "1. ANALYZE the user's question to understand what information they need\n"
    "2. PLAN your search strategy - what queries will you use and why\n"
    "3. EXECUTE searches using the rag_search_tool\n"
    "4. EVALUATE the search results and determine if you need more information\n"
    "5. SYNTHESIZE the information into a comprehensive answer\n\n"
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

def get_system_prompt(chatbot_description: str = None) -> str:
    """Generate system prompt with optional chatbot description"""
    
    base_prompt = (
        "# Identity\n"
        "You are a Personal Document Assistant, an AI agent that helps users find and understand information from their uploaded documents.\n\n"
    )
    
    if chatbot_description:
        base_prompt += (
            f"# Specialization\n"
            f"This chatbot is specifically designed for: {chatbot_description}\n"
            f"Keep your responses focused on this domain and use case.\n\n"
        )
    
    base_prompt += (
        "# Instructions\n"
        "## THINKING PROCESS\n"
        "Before answering, always think through your approach step by step:\n"
        "1. ANALYZE the user's question to understand what information they need\n"
        "2. PLAN your search strategy - what queries will you use and why\n"
        "3. EXECUTE searches using the rag_search_tool\n"
        "4. EVALUATE the search results and determine if you need more information\n"
        "5. SYNTHESIZE the information into a comprehensive answer\n\n"
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
    
    return base_prompt

MAX_TOOL_CALLS = 4

# Token management configuration
MAX_TOTAL_TOKENS = 200000      # Hard limit for trimming
TARGET_TOKENS_AFTER_TRIM = 150000  # Target after trimming (25% buffer)
TOKENS_PER_MESSAGE_OVERHEAD = 4    # Tiktoken message formatting overhead

# Initialize tokenizer for GPT-4.1
try:
    # GPT-4.1 uses same tokenizer as GPT-4
    TOKENIZER = tiktoken.encoding_for_model("gpt-4")
except Exception:
    # Fallback to cl100k_base if model-specific tokenizer fails
    TOKENIZER = tiktoken.get_encoding("cl100k_base")


def count_tokens_in_messages(messages: List[Dict[str, Any]]) -> int:
    """
    Count tokens in a list of messages for GPT-4.1
    Accounts for message structure overhead and different message types

    Args:
        messages: List of message dictionaries with 'role' and 'content' or other fields

    Returns:
        Total token count for all messages including overhead

    Raises:
        Exception: If token counting fails
    """
    try:
        total_tokens = 0

        for message in messages:
            # Count tokens in message content
            if isinstance(message, dict):
                # Handle different message types
                if message.get("role") and message.get("content"):
                    # Standard user/assistant/system messages
                    role_tokens = len(TOKENIZER.encode(message["role"]))
                    content_tokens = len(
                        TOKENIZER.encode(str(message["content"])))
                    total_tokens += role_tokens + content_tokens + TOKENS_PER_MESSAGE_OVERHEAD

                elif message.get("type") == "function_call":
                    # Function call messages
                    name_tokens = len(TOKENIZER.encode(
                        message.get("name", "")))
                    args_tokens = len(TOKENIZER.encode(
                        str(message.get("arguments", ""))))
                    total_tokens += name_tokens + args_tokens + TOKENS_PER_MESSAGE_OVERHEAD

                elif message.get("type") == "function_call_output":
                    # Function output messages
                    output_tokens = len(TOKENIZER.encode(
                        str(message.get("output", ""))))
                    total_tokens += output_tokens + TOKENS_PER_MESSAGE_OVERHEAD

                else:
                    # Fallback for unknown message types - count all string values
                    for key, value in message.items():
                        if isinstance(value, str):
                            total_tokens += len(TOKENIZER.encode(value))
                    total_tokens += TOKENS_PER_MESSAGE_OVERHEAD

        return total_tokens

    except Exception as e:
        # Log error but don't fail completely - return high estimate to be safe
        conservative_estimate = len(messages) * 100
        token_logger.warning(
            f"Token counting failed: {e}. Using conservative estimate of {conservative_estimate} tokens.")
        # Conservative estimate: ~100 tokens per message
        return conservative_estimate


def trim_conversation_history(messages: List[Dict[str, Any]], target_tokens: int = TARGET_TOKENS_AFTER_TRIM) -> List[Dict[str, Any]]:
    """
    Remove oldest conversation pairs to reduce token count while preserving conversation coherence

    Strategy:
    1. Keep system prompt (index 0) - never remove
    2. Keep current user query (last message) - never remove  
    3. Remove oldest user-assistant pairs from the middle
    4. Remove pairs together to maintain conversation coherence

    Args:
        messages: List of message dictionaries to trim
        target_tokens: Target token count after trimming

    Returns:
        Trimmed list of messages
    """
    try:
        current_tokens = count_tokens_in_messages(messages)

        # If already under target, no trimming needed
        if current_tokens <= target_tokens:
            return messages

        token_logger.info(
            f"🔄 Trimming conversation history: {current_tokens} tokens -> target: {target_tokens}")

        # Don't trim if we only have system prompt and current query
        if len(messages) <= 2:
            token_logger.warning(
                "⚠️  Cannot trim further - only system prompt and current query remain")
            return messages

        # Create a copy to work with
        trimmed_messages = messages.copy()

        # System prompt is always at index 0, current query is always last
        # History pairs are in between (indexes 1 to -2)
        pairs_removed = 0

        while count_tokens_in_messages(trimmed_messages) > target_tokens and len(trimmed_messages) > 2:
            # Find the start of conversation history (after system prompt)
            history_start_index = 1

            # Check if we have at least one conversation pair to remove
            if len(trimmed_messages) <= history_start_index + 1:  # Only system + current query left
                break

            # Remove the oldest conversation pair (user + assistant)
            # History starts at index 1, so oldest pair is at indexes 1 and 2
            if len(trimmed_messages) >= history_start_index + 2:
                # Check if we have a proper user-assistant pair
                if (trimmed_messages[history_start_index].get("role") == "user" and
                    len(trimmed_messages) > history_start_index + 1 and
                        trimmed_messages[history_start_index + 1].get("role") == "assistant"):

                    # Remove the pair (user + assistant)
                    removed_user = trimmed_messages.pop(history_start_index)
                    removed_assistant = trimmed_messages.pop(
                        history_start_index)  # Index shifts after first pop
                    pairs_removed += 1

                    token_logger.debug(
                        f"  📝 Removed conversation pair {pairs_removed}: User msg ({len(str(removed_user.get('content', ''))) if removed_user.get('content') else 0} chars) + Assistant msg ({len(str(removed_assistant.get('content', ''))) if removed_assistant.get('content') else 0} chars)")

                else:
                    # If not a proper pair, remove just the first history message
                    removed_msg = trimmed_messages.pop(history_start_index)
                    token_logger.debug(
                        f"  📝 Removed single message: {removed_msg.get('role', 'unknown')} ({len(str(removed_msg.get('content', '')))} chars)")

            else:
                # Can't remove any more pairs
                break

        final_tokens = count_tokens_in_messages(trimmed_messages)
        token_logger.info(
            f"✅ Trimming complete: {pairs_removed} pairs removed, {final_tokens} tokens remaining")

        return trimmed_messages

    except Exception as e:
        token_logger.error(
            f"❌ Error during conversation trimming: {e}. Returning original messages.")
        return messages


def ask_openai_assistant(history: list, query: str, model: str) -> str:
    """
    Ask OpenAI models to search documents and provide answers using the RAG tool.
    Supports multi-turn context by including the last 8 turns of user/assistant.
    Allows up to MAX_TOOL_CALLS sequential invocations before finalizing.

    Args:
        history: List of previous conversation turns
        query: User's current query
        model: OpenAI model to use (e.g., "gpt-4.1", "gpt-4o")

    Returns:
        Assistant's response string
    """
    # Initialize message history with dynamic system prompt
    system_prompt = get_system_prompt(RAG_CONFIG.get('chatbot_description'))
    messages = [{"role": "system", "content": system_prompt}]

    # Include last 8 user-assistant exchanges
    for turn in history[-8:]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})

    # Add current user query
    messages.append({"role": "user", "content": query})

    # Check token count and trim conversation history if needed
    total_tokens = count_tokens_in_messages(messages)
    if total_tokens > MAX_TOTAL_TOKENS:
        token_logger.warning(
            f"⚠️  Token limit exceeded: {total_tokens} > {MAX_TOTAL_TOKENS}. Trimming conversation history...")
        messages = trim_conversation_history(
            messages, TARGET_TOKENS_AFTER_TRIM)
        final_tokens = count_tokens_in_messages(messages)
        token_logger.info(
            f"📊 Final token count after trimming: {final_tokens}")
    else:
        token_logger.info(
            f"📊 Token count OK: {total_tokens} <= {MAX_TOTAL_TOKENS}")

    tool_calls = 0
    final_response = None

    while tool_calls < MAX_TOOL_CALLS:
        # Send to OpenAI with function schema
        resp = openai_client.responses.create(
            model=model,
            input=messages,
            tools=tools
        )

        # Check for function call
        func_call = next(
            (item for item in resp.output if item.type == "function_call"), None)
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
            closing = openai_client.responses.create(
                model=model,
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


async def ask_openai_assistant_stream(history: list, query: str, model: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Enhanced streaming version that includes thinking process events.
    Returns an async generator that yields content deltas and thinking events.
    """
    # Initialize message history with dynamic system prompt
    system_prompt = get_system_prompt(RAG_CONFIG.get('chatbot_description'))
    messages = [{"role": "system", "content": system_prompt}]

    # Include last 8 user-assistant exchanges
    for turn in history[-8:]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})

    # Add current user query
    messages.append({"role": "user", "content": query})

    # Check token count and trim conversation history if needed
    total_tokens = count_tokens_in_messages(messages)
    if total_tokens > MAX_TOTAL_TOKENS:
        token_logger.warning(
            f"⚠️  Token limit exceeded: {total_tokens} > {MAX_TOTAL_TOKENS}. Trimming conversation history...")
        messages = trim_conversation_history(
            messages, TARGET_TOKENS_AFTER_TRIM)
        final_tokens = count_tokens_in_messages(messages)
        token_logger.info(
            f"📊 Final token count after trimming: {final_tokens}")
    else:
        token_logger.info(
            f"📊 Token count OK: {total_tokens} <= {MAX_TOTAL_TOKENS}")

    tool_calls = 0
    final_messages = messages.copy()

    # Send thinking start event
    yield {"type": "thinking_start", "message": "Analyzing your question and planning search strategy..."}

    debug_print(f"Processing tool calls for query: {query}")

    while tool_calls < MAX_TOOL_CALLS:
        debug_print(f"Checking for tool call {tool_calls+1}/{MAX_TOOL_CALLS}")

        # Send thinking event for each tool call
        if tool_calls == 0:
            yield {"type": "thinking_step", "step": "search_planning", "message": "Planning search queries to find relevant information..."}
        else:
            yield {"type": "thinking_step", "step": "additional_search", "message": f"Searching for additional information (attempt {tool_calls + 1})..."}

        # Send to OpenAI with function schema
        resp = openai_client.responses.create(
            model=model,
            input=messages,
            tools=tools
        )

        # Check for function call
        func_call = next(
            (item for item in resp.output if item.type == "function_call"), None)
        if not func_call:
            # No more function calls; prepare for streaming
            break

        # Execute the function
        debug_print(f"Executing function call: {func_call.name}")
        args = json.loads(func_call.arguments)
        
        # Send search execution event
        yield {"type": "thinking_step", "step": "executing_search", "message": f"Searching documents for: '{args.get('query', '')}'"}
        
        result = rag_search_tool(args.get("query"))
        debug_print(f"Function returned result length: {len(result)}")

        # Send search results event
        yield {"type": "thinking_step", "step": "search_results", "message": f"Found {len(result)} relevant results"}

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

    # Send thinking completion event
    yield {"type": "thinking_complete", "message": "Analysis complete. Generating comprehensive answer..."}

    # Stream the final response
    try:
        # Use a streaming-compatible model for final response
        streaming_model = model if "mini" in model else f"{model}-mini-2025-04-14" if "gpt-4.1" in model else model

        stream = await openai_async_client.responses.create(
            model=streaming_model,
            input=final_messages,
            tools=tools,
            stream=True
        )

        got_content = False

        async for event in stream:
            if event.type == "response.output_text.delta":
                got_content = True
                yield {"type": "response_chunk", "chunk": event.delta}
            elif event.type == "text_delta":
                got_content = True
                yield {"type": "response_chunk", "chunk": event.delta}
            elif event.type == "content_part_added":
                if event.content_part.type == "text":
                    got_content = True
                    yield {"type": "response_chunk", "chunk": event.content_part.text}
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
            fallback_resp = openai_client.responses.create(
                model=streaming_model,
                input=final_messages,
                tools=tools
            )
            yield {"type": "response_chunk", "chunk": fallback_resp.output_text or "I'm sorry, I couldn't generate a response. Please try again."}
    except Exception:
        # Fallback on stream error
        fallback_resp = openai_client.responses.create(
            model=model,
            input=final_messages,
            tools=tools
        )
        yield {"type": "response_chunk", "chunk": fallback_resp.output_text}


def ask_gemini_assistant(history: list, query: str, model: str) -> str:
    """
    Ask Gemini models to search documents and provide answers using the RAG tool.
    Supports multi-turn context by including the last 8 turns of user/assistant.

    Args:
        history: List of previous conversation turns
        query: User's current query
        model: Gemini model to use (e.g., "gemini-2.5-pro", "gemini-1.5-flash")

    Returns:
        Assistant's response string
    """
    # Convert conversation history to Gemini format
    contents = []

    # Add system instruction with dynamic prompt
    system_prompt = get_system_prompt(RAG_CONFIG.get('chatbot_description'))
    contents.append({
        "role": "user",
        "parts": [{"text": f"System instructions: {system_prompt}"}]
    })
    contents.append({
        "role": "model",
        "parts": [{"text": "I understand. I will help you search and answer questions about your uploaded documents using the available tools."}]
    })

    # Include last 8 user-assistant exchanges
    for turn in history[-8:]:
        contents.append({"role": "user", "parts": [{"text": turn["user"]}]})
        contents.append({"role": "model", "parts": [
                        {"text": turn["assistant"]}]})

    # Add current user query
    contents.append({"role": "user", "parts": [{"text": query}]})

    # Define Gemini function schema
    gemini_tools = [{
        "function_declarations": [{
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
                "required": ["query"]
            }
        }]
    }]

    tool_calls = 0
    final_response = None

    while tool_calls < MAX_TOOL_CALLS:
        try:
            # Send to Gemini with function schema
            response = gemini_client.models.generate_content(
                model=model,
                contents=contents,
                tools=gemini_tools
            )

            # Check if there are function calls
            if response.candidates and response.candidates[0].content.parts:
                function_calls = [part for part in response.candidates[0].content.parts
                                  if hasattr(part, 'function_call')]

                if not function_calls:
                    # No function calls, get the text response
                    final_response = response.text
                    break

                # Process function calls
                for func_call in function_calls:
                    debug_print(
                        f"Executing Gemini function call: {func_call.function_call.name}")

                    # Extract arguments
                    args = {}
                    if hasattr(func_call.function_call, 'args'):
                        args = dict(func_call.function_call.args)

                    # Execute the function
                    result = rag_search_tool(args.get("query", ""))
                    debug_print(
                        f"Function returned result length: {len(result)}")

                    # Add function call to conversation
                    contents.append({
                        "role": "model",
                        "parts": [func_call]
                    })

                    # Add function response to conversation
                    contents.append({
                        "role": "function",
                        "parts": [{
                            "function_response": {
                                "name": func_call.function_call.name,
                                "response": {"result": result}
                            }
                        }]
                    })

                tool_calls += 1
                if tool_calls >= MAX_TOOL_CALLS:
                    debug_print(f"Reached max tool calls: {MAX_TOOL_CALLS}")
                    # Get final response
                    final_resp = gemini_client.models.generate_content(
                        model=model,
                        contents=contents
                    )
                    final_response = final_resp.text
                    break
            else:
                # No response, break
                final_response = "I'm sorry, I couldn't generate a response."
                break

        except Exception as e:
            debug_print(f"Error in Gemini function call: {e}")
            final_response = f"Error: {str(e)}"
            break

    return final_response or "I'm sorry, I couldn't generate a response."


async def ask_gemini_assistant_stream(history: list, query: str, model: str) -> AsyncGenerator[str, None]:
    """
    Streaming version of ask_gemini_assistant.
    Note: Gemini streaming with function calling is limited, so we process tools first then stream.

    Args:
        history: List of previous conversation turns
        query: User's current query
        model: Gemini model to use (e.g., "gemini-2.5-pro", "gemini-1.5-flash")

    Yields:
        Content deltas as they're received from the model
    """
    # First, handle any necessary function calls (non-streaming)
    # Convert conversation history to Gemini format
    contents = []

    # Add system instruction with dynamic prompt
    system_prompt = get_system_prompt(RAG_CONFIG.get('chatbot_description'))
    contents.append({
        "role": "user",
        "parts": [{"text": f"System instructions: {system_prompt}"}]
    })
    contents.append({
        "role": "model",
        "parts": [{"text": "I understand. I will help you search and answer questions about your uploaded documents using the available tools."}]
    })

    # Include last 8 user-assistant exchanges
    for turn in history[-8:]:
        contents.append({"role": "user", "parts": [{"text": turn["user"]}]})
        contents.append({"role": "model", "parts": [
                        {"text": turn["assistant"]}]})

    # Add current user query
    contents.append({"role": "user", "parts": [{"text": query}]})

    # Define Gemini function schema
    gemini_tools = [{
        "function_declarations": [{
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
                "required": ["query"]
            }
        }]
    }]

    # Process function calls first (non-streaming)
    tool_calls = 0
    while tool_calls < MAX_TOOL_CALLS:
        try:
            response = gemini_client.models.generate_content(
                model=model,
                contents=contents,
                tools=gemini_tools
            )

            # Check if there are function calls
            if response.candidates and response.candidates[0].content.parts:
                function_calls = [part for part in response.candidates[0].content.parts
                                  if hasattr(part, 'function_call')]

                if not function_calls:
                    # No function calls, break to streaming
                    break

                # Process function calls
                for func_call in function_calls:
                    debug_print(
                        f"Executing Gemini function call: {func_call.function_call.name}")

                    # Extract arguments
                    args = {}
                    if hasattr(func_call.function_call, 'args'):
                        args = dict(func_call.function_call.args)

                    # Execute the function
                    result = rag_search_tool(args.get("query", ""))
                    debug_print(
                        f"Function returned result length: {len(result)}")

                    # Add function call to conversation
                    contents.append({
                        "role": "model",
                        "parts": [func_call]
                    })

                    # Add function response to conversation
                    contents.append({
                        "role": "function",
                        "parts": [{
                            "function_response": {
                                "name": func_call.function_call.name,
                                "response": {"result": result}
                            }
                        }]
                    })

                tool_calls += 1
                if tool_calls >= MAX_TOOL_CALLS:
                    debug_print(f"Reached max tool calls: {MAX_TOOL_CALLS}")
                    break
            else:
                break

        except Exception as e:
            debug_print(f"Error in Gemini function call: {e}")
            yield f"Error: {str(e)}"
            return

    # Now stream the final response
    try:
        stream_response = gemini_client.models.generate_content_stream(
            model=model,
            contents=contents
        )

        got_content = False
        for chunk in stream_response:
            if chunk.text:
                got_content = True
                yield chunk.text

        if not got_content:
            yield "I'm sorry, I couldn't generate a response."

    except Exception as e:
        debug_print(f"Error in Gemini streaming: {e}")
        yield f"Error: {str(e)}"


def ask_rag_assistant(history: list, query: str) -> str:
    """
    Router function that selects the appropriate provider based on configured chatbot model.
    Supports multi-turn context by including the last 8 turns of user/assistant.
    Allows up to MAX_TOOL_CALLS sequential invocations before finalizing.

    Args:
        history: List of previous conversation turns
        query: User's current query

    Returns:
        Assistant's response string
    """
    if not RAG_CONFIG.get('chatbot_model'):
        raise ValueError(
            "Chatbot model not configured. Please call initialize_rag_config first.")

    model = RAG_CONFIG['chatbot_model']
    provider = get_model_provider(model)

    debug_print(f"Using {provider} provider with model: {model}")

    if provider == 'openai':
        return ask_openai_assistant(history, query, model)
    elif provider == 'gemini':
        return ask_gemini_assistant(history, query, model)
    else:
        raise ValueError(f"Unsupported model provider for model: {model}")


async def ask_rag_assistant_stream(history: list, query: str) -> AsyncGenerator[str, None]:
    """
    Router function for streaming that selects the appropriate provider based on configured chatbot model.
    Returns an async generator that yields content deltas as they're received.
    Tool calls are still processed synchronously before streaming the final response.

    Args:
        history: List of previous conversation turns
        query: User's current query

    Yields:
        Content deltas as they're received from the model
    """
    if not RAG_CONFIG.get('chatbot_model'):
        yield "Error: Chatbot model not configured. Please call initialize_rag_config first."
        return

    model = RAG_CONFIG['chatbot_model']
    provider = get_model_provider(model)

    debug_print(f"Using {provider} provider with model: {model} (streaming)")

    if provider == 'openai':
        async for chunk in ask_openai_assistant_stream(history, query, model):
            yield chunk
    elif provider == 'gemini':
        async for chunk in ask_gemini_assistant_stream(history, query, model):
            yield chunk
    else:
        yield f"Error: Unsupported model provider for model: {model}"

def ask_rag_assistant_sync_stream(history: list, query: str) -> str:
    """
    Synchronous wrapper for streaming assistant that provides real-time output to CLI.
    Handles the async streaming and displays chunks as they arrive.

    Args:
        history: List of previous conversation turns
        query: User's current query

    Returns:
        Complete response string (for conversation history)
    """
    import sys
    import time

    # Create async event loop for this sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        accumulated_response = ""

        async def stream_and_display():
            nonlocal accumulated_response

            # Show streaming indicator
            print("\nΓ£¿ Generating response", end="", flush=True)
            for i in range(3):
                time.sleep(0.05)
                print(".", end="", flush=True)
            print()

            print("≡ƒñû Assistant: ", end="", flush=True)

            chunk_count = 0
            start_time = time.time()

            async for chunk in ask_rag_assistant_stream(history, query):
                # Print each chunk immediately
                print(chunk, end="", flush=True)
                accumulated_response += chunk
                chunk_count += 1

                # Add small delay to make streaming visible for very fast responses
                if chunk_count % 5 == 0:
                    await asyncio.sleep(0.01)

            # Add final newline and completion indicator
            print()

            elapsed_time = time.time() - start_time
            debug_print(
                f"Streaming completed: {chunk_count} chunks in {elapsed_time:.2f}s")

            return accumulated_response

        # Run the async streaming
        result = loop.run_until_complete(stream_and_display())
        return result

    except Exception as e:
        print(f"\nΓ¥î Streaming error: {e}")
        debug_print(f"Streaming error details: {type(e).__name__}: {e}")
        print("≡ƒöä Falling back to non-streaming mode...")
        # Fallback to non-streaming
        fallback_response = ask_rag_assistant(history, query)
        print(f"≡ƒñû Assistant: {fallback_response}")
        return fallback_response
    finally:
        loop.close()

def start_rag_chat_session(user_id: str, namespace: str, embedding_model: str, chatbot_model: str = "gpt-4.1", chatbot_description: str = None):
    """
    Start an interactive RAG chat session with the user

    Args:
        user_id: MongoDB ObjectId string of the user
        namespace: Document namespace (without user_id suffix)
        embedding_model: Embedding model used for the documents
        chatbot_model: Model to use for chat generation (default: gpt-4.1)
        chatbot_description: Custom description of what this chatbot is about
    """
    # Initialize RAG configuration
    initialize_rag_config(user_id, namespace, embedding_model, chatbot_model, chatbot_description)

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
                print(
                    "\n👋 Thank you for using the Personal Document Assistant. Goodbye!")
                break

            if not user_input:
                print("Please enter a question about your documents.")
                continue

            print("\n🔍 Searching your documents...")

            # Get response from RAG assistant
            assistant_response = ask_rag_assistant(
                conversation_history, user_input)

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
# if __name__ == "__main__":
#     # Test mode - requires manual configuration
#     print("🧪 RAG Assistant Test Mode")
#     print("Note: In production, this will be called from the master pipeline")

#     # Example configuration (would normally come from the pipeline)
#     test_user_id = input("Enter user ID: ").strip()
#     test_namespace = input("Enter namespace: ").strip()
#     test_embedding_model = input(
#         "Enter embedding model (text-embedding-3-small/gemini-embedding-001): ").strip()
#     test_chatbot_description = input("Enter chatbot description (optional): ").strip()

#     if test_user_id and test_namespace and test_embedding_model:
#         start_rag_chat_session(
#             test_user_id, test_namespace, test_embedding_model, chatbot_description=test_chatbot_description if test_chatbot_description else None)
#     else:
#         print("❌ All fields are required for testing.")
