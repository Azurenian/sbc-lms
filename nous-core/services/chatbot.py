"""
Chatbot Service for PI-LMS
Handles chat logic, context management, and lesson content integration
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp
import os
from dotenv import load_dotenv
from .llm import get_llm_service

load_dotenv()

class ChatSession:
    """Represents a chat session with context and history"""
    
    def __init__(self, session_id: str, lesson_id: int, user_id: Optional[int] = None):
        self.session_id = session_id
        self.lesson_id = lesson_id
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.history: List[Dict] = []
        self.context_cache = {}
        
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the chat history"""
        message = {
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.history.append(message)
        self.last_activity = datetime.now()
        
        # Keep only last 20 messages to manage memory
        if len(self.history) > 20:
            self.history = self.history[-20:]
    
    def get_recent_history(self, limit: int = 10) -> List[Dict]:
        """Get recent chat history"""
        return self.history[-limit:] if self.history else []
    
    def clear_history(self):
        """Clear chat history"""
        self.history = []

class ContentIndexer:
    """Handles lesson content processing and indexing for chat context"""
    
    @staticmethod
    def extract_text_from_lexical(lexical_content: Dict) -> str:
        """Extract plain text from Lexical JSON structure"""
        def extract_from_node(node):
            text = ""
            
            if isinstance(node, dict):
                # Handle text nodes
                if node.get("type") == "text":
                    text += node.get("text", "")
                
                # Handle paragraph nodes
                elif node.get("type") == "paragraph":
                    children = node.get("children", [])
                    for child in children:
                        text += extract_from_node(child)
                    text += "\n\n"
                
                # Handle heading nodes
                elif node.get("type") == "heading":
                    children = node.get("children", [])
                    for child in children:
                        text += extract_from_node(child)
                    text += "\n\n"
                
                # Handle list nodes
                elif node.get("type") in ["list", "listitem"]:
                    children = node.get("children", [])
                    for child in children:
                        text += extract_from_node(child)
                    text += "\n"
                
                # Recursively handle other nodes with children
                elif "children" in node:
                    children = node.get("children", [])
                    for child in children:
                        text += extract_from_node(child)
            
            return text
        
        if not lexical_content:
            return ""
        
        root = lexical_content.get("root", {})
        children = root.get("children", [])
        
        full_text = ""
        for child in children:
            full_text += extract_from_node(child)
        
        return full_text.strip()
    
    @staticmethod
    def create_context_summary(lesson_content: str, max_length: int = 2000) -> str:
        """Create a condensed summary of lesson content for context"""
        if len(lesson_content) <= max_length:
            return lesson_content
        
        # Simple truncation with sentence boundary awareness
        truncated = lesson_content[:max_length]
        last_sentence = truncated.rfind('.')
        if last_sentence > max_length * 0.7:  # If we can find a sentence ending in the last 30%
            truncated = truncated[:last_sentence + 1]
        
        return truncated + "..."
    
    @staticmethod
    def extract_keywords(lesson_content: str) -> List[str]:
        """Extract key terms from lesson content for semantic search"""
        # Simple keyword extraction (can be enhanced with NLP)
        import re
        
        # Remove common words and extract meaningful terms
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'will', 'would', 'could', 'should', 'may', 'might', 'can'
        }
        
        # Extract words (alphanumeric, 3+ characters)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', lesson_content.lower())
        
        # Filter out common words and get unique terms
        keywords = list(set([word for word in words if word not in common_words]))
        
        # Return top 20 most frequent keywords
        word_freq = {}
        for word in words:
            if word not in common_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_keywords[:20]]

class ChatbotService:
    """Main chatbot service handling chat logic and responses"""
    
    def __init__(self):
        self.llm_service = get_llm_service()
        self.sessions: Dict[str, ChatSession] = {}
        self.payload_base_url = os.getenv("PAYLOAD_BASE_URL", "http://localhost:3000")
        # Remove dependency on hardcoded token - will use dynamic user tokens only
        print("ChatbotService initialized - will use dynamic user tokens only")
        
    def load_system_prompts(self) -> Dict[str, str]:
        """Load chatbot system prompts from configuration"""
        try:
            with open("config/chatbot_prompts.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Extract prompts from nested structure
                return config.get("prompts", {})
        except Exception as e:
            print(f"Error loading chatbot prompts: {e}")
            return {
                "default": "You are an AI teaching assistant for an educational platform. Help students understand lesson content, answer questions, and provide study guidance.",
                "quiz_mode": "You are creating practice questions based on lesson content. Generate relevant questions to test student understanding.",
                "explanation": "You are explaining complex concepts in simple terms. Break down difficult topics into easy-to-understand explanations."
            }
    
    async def get_lesson_context(self, lesson_id: int, auth_token: str = None) -> Dict[str, Any]:
        """Fetch lesson content and related information from Payload CMS"""
        try:
            # Require auth token - no fallback to hardcoded token
            if not auth_token:
                print(f"Error: No auth token provided for lesson context {lesson_id}")
                return {}
            
            headers = {
                "Authorization": f"JWT {auth_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # Fetch lesson data
                async with session.get(
                    f"{self.payload_base_url}/api/lessons/{lesson_id}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        lesson_data = await response.json()
                        
                        # Extract text content
                        content = lesson_data.get("content", {})
                        text_content = ContentIndexer.extract_text_from_lexical(content)
                        
                        # Get course information if available
                        course_info = {}
                        course_id = lesson_data.get("course")
                        if course_id:
                            async with session.get(
                                f"{self.payload_base_url}/api/courses/{course_id}",
                                headers=headers
                            ) as course_response:
                                if course_response.status == 200:
                                    course_info = await course_response.json()
                        
                        return {
                            "lesson": lesson_data,
                            "text_content": text_content,
                            "course": course_info,
                            "keywords": ContentIndexer.extract_keywords(text_content),
                            "context_summary": ContentIndexer.create_context_summary(text_content)
                        }
                    else:
                        print(f"Failed to fetch lesson {lesson_id}: {response.status}")
                        if response.status == 403:
                            print(f"Authentication failed for lesson {lesson_id} - check if auth token is valid")
                        return {}
        except Exception as e:
            print(f"Error fetching lesson context: {e}")
            return {}
    
    async def find_related_lessons(self, lesson_id: int, keywords: List[str], limit: int = 5, auth_token: str = None) -> List[Dict]:
        """Find lessons related to the current one based on keywords"""
        try:
            # Require auth token - no fallback to hardcoded token
            if not auth_token:
                print(f"Error: No auth token provided for related lessons search {lesson_id}")
                return []
            
            headers = {
                "Authorization": f"JWT {auth_token}",
                "Content-Type": "application/json"
            }
            
            # Simple keyword-based search (can be enhanced with semantic search)
            search_query = " OR ".join(keywords[:5])  # Use top 5 keywords
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.payload_base_url}/api/lessons?where[title][contains]={search_query}&limit={limit}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        lessons = result.get("docs", [])
                        
                        # Filter out current lesson
                        related = [lesson for lesson in lessons if lesson.get("id") != lesson_id]
                        
                        return related[:limit]
                    else:
                        return []
        except Exception as e:
            print(f"Error finding related lessons: {e}")
            return []
    
    def create_session(self, lesson_id: int, user_id: Optional[int] = None) -> str:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = ChatSession(session_id, lesson_id, user_id)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get an existing chat session"""
        return self.sessions.get(session_id)
    
    async def generate_response(
        self,
        session_id: str,
        message: str,
        mode: str = "default",
        auth_token: str = None
    ) -> Dict[str, Any]:
        """Generate a chatbot response for a given message"""
        
        session = self.get_session(session_id)
        if not session:
            raise ValueError("Invalid session ID")
        
        # Add user message to history
        session.add_message("user", message)
        
        # Get lesson context if not cached
        if not session.context_cache:
            session.context_cache = await self.get_lesson_context(session.lesson_id, auth_token)
        
        context = session.context_cache
        lesson_content = context.get("context_summary", "")
        
        # Load system prompts
        prompts = self.load_system_prompts()
        system_prompt = prompts.get(mode, prompts["default"])
        
        # Build context for LLM
        llm_context = f"Lesson Content: {lesson_content}\n\n"
        
        # Add recent chat history for continuity
        recent_history = session.get_recent_history(5)
        if recent_history:
            llm_context += "Recent conversation:\n"
            for msg in recent_history[:-1]:  # Exclude the current message
                llm_context += f"{msg['role'].title()}: {msg['content']}\n"
            llm_context += "\n"
        
        try:
            print(f"🤖 Generating LLM response for message: '{message[:50]}...' in mode: '{mode}'")
            print(f"📝 System prompt: '{system_prompt[:100]}...'")
            print(f"📄 Context length: {len(llm_context)} chars")
            
            # Check if LLM service is available
            llm_available = await self.llm_service.is_available()
            print(f"🔌 LLM service available: {llm_available}")
            
            if not llm_available:
                print("❌ LLM service not available, cannot generate response")
                raise Exception("LLM service is not available - check Ollama connection and model")
            
            # Generate response using LLM
            response = await self.llm_service.generate_response(
                prompt=message,
                system_prompt=system_prompt,
                context=llm_context
            )
            print(f"✅ LLM response generated successfully: '{response[:100]}...'")
            
            # Add assistant response to history
            session.add_message("assistant", response)
            
            # Find related lessons for suggestions
            keywords = context.get("keywords", [])
            related_lessons = await self.find_related_lessons(session.lesson_id, keywords, 3, auth_token)
            
            # Generate smart suggestions based on the conversation
            suggestions = self.generate_suggestions(message, response, mode)
            
            return {
                "response": response,
                "session_id": session_id,
                "related_lessons": related_lessons,
                "suggestions": suggestions,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error generating response: {e}")
            # Fallback response
            fallback_response = "I'm sorry, I'm having trouble processing your request right now. Could you please try rephrasing your question?"
            session.add_message("assistant", fallback_response)
            
            return {
                "response": fallback_response,
                "session_id": session_id,
                "related_lessons": [],
                "suggestions": ["Can you explain this concept further?", "What are the key points?"],
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def generate_suggestions(self, user_message: str, bot_response: str, mode: str) -> List[str]:
        """Generate smart follow-up suggestions based on the conversation"""
        suggestions = []
        
        if mode == "quiz_mode":
            suggestions = [
                "Can you create another practice question?",
                "Explain the answer to this question",
                "What's a common mistake for this topic?"
            ]
        elif "explain" in user_message.lower():
            suggestions = [
                "Can you provide an example?",
                "How does this relate to other concepts?",
                "What are the practical applications?"
            ]
        elif "summary" in user_message.lower():
            suggestions = [
                "Can you create practice questions?",
                "What should I focus on studying?",
                "Are there related lessons?"
            ]
        else:
            suggestions = [
                "Can you explain this concept further?",
                "Create a practice question about this",
                "What are the key takeaways?",
                "How can I apply this knowledge?"
            ]
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old inactive sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            age = (current_time - session.last_activity).total_seconds() / 3600
            if age > max_age_hours:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            print(f"Cleaned up expired session: {session_id}")