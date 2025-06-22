"""
LLM Service for PI-LMS Chatbot
Handles communication with local Llama.cpp server for AI chat responses
"""

import aiohttp
import asyncio
import json
import os
from typing import Dict, List, Optional, AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

class LlamaCppService:
    def __init__(self):
        self.base_url = os.getenv("LLAMA_CPP_HOST", "http://localhost:8080")
        self.model = os.getenv("LLM_MODEL", "llama3.2-3b.Q4_K_M.gguf") # Model name from docker-compose.yml
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4000"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.enabled = os.getenv("ENABLE_LOCAL_LLM", "true").lower() == "true"
        
    async def is_available(self) -> bool:
        """Check if Llama.cpp server is running"""
        if not self.enabled:
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
        except Exception as e:
            print(f"Llama.cpp server availability check failed: {e}")
            return False
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """Generate a single response from the LLM"""
        if not await self.is_available():
            raise Exception("Llama.cpp LLM service is not available")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.append({"role": "system", "content": f"Context: {context}"})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False  # Ensure non-streaming for this method
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/v1/chat/completions", json=payload) as response:
                    response.raise_for_status()  # Raise an exception for HTTP errors
                    data = await response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        return data["choices"][0]["message"]["content"]
                    return ""
        except Exception as e:
            print(f"Error generating response from Llama.cpp server: {e}")
            raise

    async def generate_streaming_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM"""
        if not await self.is_available():
            raise Exception("Llama.cpp LLM service is not available")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.append({"role": "system", "content": f"Context: {context}"})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True  # Ensure streaming for this method
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/v1/chat/completions", json=payload) as response:
                    response.raise_for_status()  # Raise an exception for HTTP errors

                    async for chunk in response.content.iter_any():
                        try:
                            decoded_chunk = chunk.decode('utf-8')
                            for line in decoded_chunk.splitlines():
                                if line.startswith("data:"):  # Handle SSE format
                                    json_data = line[len("data:"):].strip()
                                    if json_data == "[DONE]":
                                        break
                                    data = json.loads(json_data)
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        if "content" in delta:
                                            yield delta["content"]
                        except json.JSONDecodeError:
                            print(f"JSON Decode Error: {line}")
                            continue
        except Exception as e:
            print(f"Error generating streaming response from Llama.cpp server: {e}")
            raise

# Factory function to get the appropriate LLM service
def get_llm_service():
    """Get LLM service instance (LlamaCppService or Mock based on availability)"""
    if os.getenv("ENABLE_LOCAL_LLM", "true").lower() == "true":
        return LlamaCppService()
    else:
        return MockLLMService()