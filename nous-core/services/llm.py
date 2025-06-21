"""
LLM Service for PI-LMS Chatbot
Handles communication with local Ollama server for AI chat responses
"""

import aiohttp
import asyncio
import json
import os
from typing import Dict, List, Optional, AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

class OllamaService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("LLM_MODEL", "llama3.2:3b")
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4000"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.enabled = os.getenv("ENABLE_LOCAL_LLM", "true").lower() == "true"
        
    async def is_available(self) -> bool:
        """Check if Ollama server is running and model is available"""
        if not self.enabled:
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                # Check if Ollama is running
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        models = await response.json()
                        # Check if our model is available
                        available_models = [model["name"] for model in models.get("models", [])]
                        return self.model in available_models
            return False
        except Exception as e:
            print(f"Ollama availability check failed: {e}")
            return False
    
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        stream: bool = False
    ) -> str:
        """Generate a single response from the LLM"""
        
        if not await self.is_available():
            raise Exception("Ollama LLM service is not available")
        
        # Construct the full prompt
        full_prompt = ""
        if system_prompt:
            full_prompt += f"System: {system_prompt}\n\n"
        if context:
            full_prompt += f"Context: {context}\n\n"
        full_prompt += f"User: {prompt}\nAssistant:"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": stream,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        if stream:
                            # Handle streaming response
                            full_response = ""
                            async for line in response.content:
                                if line:
                                    try:
                                        chunk = json.loads(line.decode())
                                        if chunk.get("response"):
                                            full_response += chunk["response"]
                                        if chunk.get("done"):
                                            break
                                    except json.JSONDecodeError:
                                        continue
                            return full_response
                        else:
                            # Handle non-streaming response
                            result = await response.json()
                            return result.get("response", "")
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"LLM generation error: {e}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    async def generate_streaming_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM"""
        
        if not await self.is_available():
            raise Exception("Ollama LLM service is not available")
        
        # Construct the full prompt
        full_prompt = ""
        if system_prompt:
            full_prompt += f"System: {system_prompt}\n\n"
        if context:
            full_prompt += f"Context: {context}\n\n"
        full_prompt += f"User: {prompt}\nAssistant:"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        async for line in response.content:
                            if line:
                                try:
                                    chunk = json.loads(line.decode())
                                    if chunk.get("response"):
                                        yield chunk["response"]
                                    if chunk.get("done"):
                                        break
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"LLM streaming error: {e}")
            raise Exception(f"Failed to generate streaming response: {str(e)}")
    
    async def pull_model(self) -> bool:
        """Pull/download the specified model if not available"""
        try:
            payload = {"name": self.model}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/pull",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        # Stream the pull progress
                        async for line in response.content:
                            if line:
                                try:
                                    chunk = json.loads(line.decode())
                                    status = chunk.get("status", "")
                                    print(f"Model pull status: {status}")
                                    if "successfully" in status.lower():
                                        return True
                                except json.JSONDecodeError:
                                    continue
                        return True
                    else:
                        error_text = await response.text()
                        print(f"Model pull error: {response.status} - {error_text}")
                        return False
        except Exception as e:
            print(f"Error pulling model: {e}")
            return False

# Mock LLM Service for development/testing
class MockLLMService:
    """Mock LLM service for development when Ollama is not available"""
    
    def __init__(self):
        self.enabled = True
        
    async def is_available(self) -> bool:
        return True
    
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        stream: bool = False
    ) -> str:
        """Generate a mock response for development"""
        await asyncio.sleep(1)  # Simulate processing time
        
        if "quiz" in prompt.lower() or "question" in prompt.lower():
            return "Here's a practice question based on the lesson content: What is the main concept discussed in this section? Can you explain it in your own words?"
        elif "explain" in prompt.lower():
            return "Based on the lesson content, this concept refers to a fundamental principle that helps students understand the relationship between different elements. Would you like me to break it down further or provide some examples?"
        elif "summary" in prompt.lower():
            return "Here's a summary of the key points from this lesson: The main topics covered include the core concepts, practical applications, and important takeaways that students should remember."
        else:
            return f"I understand you're asking about: '{prompt}'. Based on the current lesson content, I can help you explore this topic further. What specific aspect would you like me to explain?"
    
    async def generate_streaming_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a mock streaming response"""
        response = await self.generate_response(prompt, system_prompt, context)
        words = response.split()
        
        for word in words:
            yield word + " "
            await asyncio.sleep(0.1)  # Simulate streaming delay

# Factory function to get the appropriate LLM service
def get_llm_service():
    """Get LLM service instance (Ollama or Mock based on availability)"""
    if os.getenv("ENABLE_LOCAL_LLM", "true").lower() == "true":
        return OllamaService()
    else:
        return MockLLMService()