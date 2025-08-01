import os
from dotenv import load_dotenv
from google import genai
from openai import OpenAI
from google.genai import types

load_dotenv()


class LLMCall:
    def __init__(self):
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.rag_call = {
            "name": "RAG Tool",
            "description": "Takes the user's query and returns the most relevant information from the RAG database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The user's query"}
                },
                "required": ["query"]
            },
        }

    def get_rag_call(self):
        pass

    def gemini_call(self, prompt: str, model: str = "gemini-2.0-flash"):
        response = self.gemini_client.models.generate_stream(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=types.Tool(function_declarations=[self.rag_call])
            )
        )
        return response

    def openai_call(self, prompt: str, model: str = "gpt-4o-mini"):
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            tools=[self.rag_call],
            stream=True
        )
        return response
