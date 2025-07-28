#!/usr/bin/env python3
"""
Scaling Up Search Client using GPT-4.1 with function calling and multi-turn support, with streaming capabilities.
"""
from dotenv import load_dotenv
load_dotenv()
import os
import json
import asyncio
import sys
from typing import AsyncGenerator, Dict, Any, List, Optional
from openai import OpenAI, AsyncOpenAI
from .scaling_up_demo_tool import scaling_up_search

# Initialize OpenAI clients
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# For debugging - set to True to print debug info (tool-call events only)
DEBUG = True

def debug_print(*args, **kwargs):
    """Print debug information if DEBUG is True"""
    if DEBUG:
        print("[DEBUG]", *args, file=sys.stderr, **kwargs)

# Define function schema for GPT-4.1
tools = [
    {
        "type": "function",
        "name": "scaling_up_search",
        "description": "Search the Scaling Up Pinecone index for relevant information based on a user query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The query to search the Scaling Up Pinecone index for relevant information. Based on the user's query, you should be able to retrieve the most relevant information from the index."}
            },
            "required": ["query"],
            "additionalProperties": False
        },
        "strict": True
    }
]

# System prompt based on project documentation
SYSTEM_PROMPT = (
    "# Identity\n"
    "You are Scaling Up Search Assistant, an AI agent that retrieves relevant information from the Scaling Up Pinecone index.\n\n"
    "# Instructions\n"
    "## PERSISTENCE\n"
    "You are an agent—keep working until the user's query is fully resolved. Only stop when you're sure the problem is solved.\n"
    "## TOOL CALLING\n"
    "Use the scaling_up_search function to fetch relevant information. Do NOT guess or hallucinate results."
    " If you need clarification to call the tool, ask the user.\n"
    "## PLANNING\n"
    "Plan extensively: decide whether to call the function, reflect on results, then finalize the answer.\n"
    "## LANGUAGE\n"
    "Users may ask questions in English or Greek, and can switch languages mid-conversation.\n"
    " The tool returns English text; You MUST format your responses accordingly. For an english user query, reply to the user in English.\n"
    "For Greek user queries, you MUST reply in Greek and change the original English tool call output to Greek."
)

MAX_TOOL_CALLS = 4

def ask_scaling_up(history: list, query: str) -> str:
    """
    Ask GPT-4.1 to decide when to call the scaling_up_search function and return the final answer.
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
        args = json.loads(func_call.arguments)
        result = scaling_up_search(args.get("query"))

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

async def ask_scaling_up_stream(history: list, query: str) -> AsyncGenerator[str, None]:
    """
    Streaming version of ask_scaling_up.
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
        # no more function calls; proceed to streaming
            break

        # Execute the function
        debug_print(f"Executing function call: {func_call.name}")
        args = json.loads(func_call.arguments)
        result = scaling_up_search(args.get("query"))
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

    # For direct single response (fallback)
    if DEBUG and not tool_calls:
        debug_print(f"No tool calls made for query: {query}")

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
                # The delta of streamed text is available on .delta, not .text
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

# For backward compatibility with the api_server reference
ask_iaspis = ask_scaling_up
ask_iaspis_stream = ask_scaling_up_stream

if __name__ == "__main__":
    # CLI chat loop for multi-turn testing
    conversation_history = []
    print("Welcome to Scaling Up Search Assistant (English/Greek). Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        assistant_response = ask_scaling_up(conversation_history, user_input)
        print(f"Assistant: {assistant_response}\n")
        conversation_history.append({"user": user_input, "assistant": assistant_response})