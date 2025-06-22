"""
AI Chatbot Performance Testing
Tests chatbot response times, context loading, and resource consumption
"""

import asyncio
import aiohttp
import websockets
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import os
from urllib.parse import urlparse

from performance_monitor import PerformanceMonitor, monitor_phase

logger = logging.getLogger(__name__)

class ChatbotPerformanceTester:
    """Performance tester for AI chatbot functionality"""
    
    def __init__(self,
                 auth_token: str,
                 ai_service_url: str = os.getenv("AI_SERVICES_URL"),
                 frontend_url: str = "http://localhost:8080",
                 performance_monitor: Optional[PerformanceMonitor] = None):
        if not ai_service_url:
            raise ValueError("AI_SERVICES_URL environment variable not set.")
        
        self.auth_token = auth_token
        self.ai_service_url = ai_service_url
        self.frontend_url = frontend_url
        # Always create a new monitor for thread safety in concurrent tests
        self.monitor = PerformanceMonitor()
        
        # Performance thresholds (in seconds)
        self.thresholds = {
            "context_loading": 2.0,
            "chat_response": 5.0,
            "websocket_connection": 1.0,
            "streaming_first_token": 1.0,
            "streaming_complete": 10.0
        }
        
        # Resource thresholds
        self.resource_thresholds = {
            "max_memory_mb": 200,
            "max_cpu_percent": 60,
            "max_response_size_kb": 50
        }
        
        # Test scenarios
        self.test_messages = [
            "What is the main topic of this lesson?",
            "Can you explain this concept in simple terms?",
            "Create a practice question about this topic",
            "What are the key takeaways from this lesson?",
            "How does this relate to other concepts?",
            "Can you provide a summary of the lesson?",
            "What should I focus on when studying this?",
            "Are there any practical applications of this knowledge?",
            "Can you give me an example to illustrate this concept?",
            "What are common mistakes students make with this topic?"
        ]
    
    async def test_context_loading(self, lesson_id: int = 1) -> Dict[str, Any]:
        """Test lesson context loading performance"""
        
        session_id = self.monitor.start_session("chatbot_context_loading")
        results = {
            "session_id": session_id,
            "lesson_id": lesson_id,
            "start_time": datetime.now().isoformat(),
            "phases": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            async with monitor_phase(self.monitor, "context_loading") as monitor:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.ai_service_url}/api/chat/context/{lesson_id}",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            context_data = await response.json()
                            context_size = len(json.dumps(context_data))
                            
                            monitor.add_custom_metric("context_size_bytes", context_size)
                            monitor.add_custom_metric("lesson_title", context_data.get("lesson", {}).get("title", ""))
                            monitor.add_custom_metric("keywords_count", len(context_data.get("keywords", [])))
                            monitor.add_custom_metric("context_summary_length", len(context_data.get("context_summary", "")))
                            
                        else:
                            error_msg = f"Context loading failed: {response.status}"
                            monitor.add_error(error_msg)
                            results["errors"].append(error_msg)
        
        except Exception as e:
            error_msg = f"Context loading test failed: {str(e)}"
            self.monitor.add_error(error_msg)
            results["errors"].append(error_msg)
        
        # End session and collect results
        session_metrics = self.monitor.end_session()
        if session_metrics:
            results["total_duration"] = session_metrics.total_duration
            results["end_time"] = datetime.now().isoformat()
            
            for phase in session_metrics.phases:
                results["phases"][phase.phase_name] = {
                    "duration": phase.duration,
                    "cpu_usage_start": phase.cpu_usage_start,
                    "cpu_usage_end": phase.cpu_usage_end,
                    "memory_usage_start": phase.memory_usage_start,
                    "memory_usage_end": phase.memory_usage_end,
                    "memory_peak": phase.memory_peak,
                    "custom_metrics": phase.custom_metrics
                }
                
                # Check thresholds
                if phase.duration > self.thresholds.get("context_loading", float('inf')):
                    warning_msg = f"Context loading exceeded threshold: {phase.duration:.2f}s"
                    results["warnings"].append(warning_msg)
        
        return results
    
    async def test_single_chat_response(self, 
                                      message: str,
                                      lesson_id: int = 1,
                                      mode: str = "default") -> Dict[str, Any]:
        """Test a single chat message response"""
        
        session_id = self.monitor.start_session("chatbot_single_response")
        results = {
            "session_id": session_id,
            "message": message,
            "lesson_id": lesson_id,
            "mode": mode,
            "start_time": datetime.now().isoformat(),
            "phases": {},
            "response_data": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Phase 1: Send chat message
            async with monitor_phase(self.monitor, "send_chat_message") as monitor:
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "message": message,
                    "lesson_id": lesson_id,
                    "mode": mode
                }
                
                monitor.add_custom_metric("message_length", len(message))
                monitor.add_custom_metric("lesson_id", lesson_id)
                monitor.add_custom_metric("mode", mode)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.ai_service_url}/api/chat/send",
                        json=payload,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            
                            # Analyze response
                            chat_response = response_data.get("response", "")
                            conversation_id = response_data.get("conversation_id", "")
                            related_lessons = response_data.get("related_lessons", [])
                            suggestions = response_data.get("suggestions", [])
                            
                            monitor.add_custom_metric("response_length", len(chat_response))
                            monitor.add_custom_metric("related_lessons_count", len(related_lessons))
                            monitor.add_custom_metric("suggestions_count", len(suggestions))
                            monitor.add_custom_metric("conversation_id", conversation_id)
                            
                            results["response_data"] = {
                                "response_length": len(chat_response),
                                "conversation_id": conversation_id,
                                "related_lessons_count": len(related_lessons),
                                "suggestions_count": len(suggestions),
                                "response_quality_score": self._evaluate_response_quality(chat_response, message)
                            }
                            
                        else:
                            error_msg = f"Chat request failed: {response.status}"
                            monitor.add_error(error_msg)
                            results["errors"].append(error_msg)
        
        except Exception as e:
            error_msg = f"Chat response test failed: {str(e)}"
            self.monitor.add_error(error_msg)
            results["errors"].append(error_msg)
        
        # End session and collect results
        session_metrics = self.monitor.end_session()
        if session_metrics:
            results["total_duration"] = session_metrics.total_duration
            results["end_time"] = datetime.now().isoformat()
            
            for phase in session_metrics.phases:
                results["phases"][phase.phase_name] = {
                    "duration": phase.duration,
                    "cpu_usage_start": phase.cpu_usage_start,
                    "cpu_usage_end": phase.cpu_usage_end,
                    "memory_usage_start": phase.memory_usage_start,
                    "memory_usage_end": phase.memory_usage_end,
                    "memory_peak": phase.memory_peak,
                    "custom_metrics": phase.custom_metrics
                }
                
                # Check thresholds
                if phase.duration > self.thresholds.get("chat_response", float('inf')):
                    warning_msg = f"Chat response exceeded threshold: {phase.duration:.2f}s"
                    results["warnings"].append(warning_msg)
                
                if phase.memory_peak > self.resource_thresholds["max_memory_mb"]:
                    warning_msg = f"Memory usage exceeded threshold: {phase.memory_peak:.2f}MB"
                    results["warnings"].append(warning_msg)
        
        return results
    
    async def test_websocket_chat(self, 
                                message: str,
                                lesson_id: int = 1) -> Dict[str, Any]:
        """Test WebSocket-based chat communication"""
        
        session_id = self.monitor.start_session("chatbot_websocket")
        results = {
            "session_id": session_id,
            "message": message,
            "lesson_id": lesson_id,
            "start_time": datetime.now().isoformat(),
            "phases": {},
            "websocket_events": [],
            "errors": [],
            "warnings": []
        }
        
        try:
            # Phase 1: WebSocket connection
            async with monitor_phase(self.monitor, "websocket_connection") as monitor:
                parsed_url = urlparse(self.ai_service_url)
                ws_host = parsed_url.netloc
                websocket_url = f"ws://{ws_host}/ws/chat/{session_id}?token={self.auth_token}"
                
                try:
                    async with websockets.connect(websocket_url) as websocket:
                        monitor.add_custom_metric("connection_established", True)
                        
                        # Phase 2: Send message and receive response
                        async with monitor_phase(self.monitor, "websocket_chat_exchange") as chat_monitor:
                            # Send message
                            message_payload = {
                                "type": "message",
                                "content": message,
                                "lesson_id": lesson_id,
                                "mode": "default"
                            }
                            
                            await websocket.send(json.dumps(message_payload))
                            chat_monitor.add_custom_metric("message_sent", True)
                            
                            # Receive responses
                            response_tokens = []
                            first_token_time = None
                            complete_response_time = None
                            
                            while True:
                                try:
                                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                                    response_data = json.loads(response)
                                    response_type = response_data.get("type")
                                    
                                    results["websocket_events"].append({
                                        "timestamp": datetime.now().isoformat(),
                                        "type": response_type,
                                        "data": response_data
                                    })
                                    
                                    if response_type == "typing":
                                        chat_monitor.add_custom_metric("typing_received", True)
                                    
                                    elif response_type == "token":
                                        if first_token_time is None:
                                            first_token_time = time.time()
                                            chat_monitor.add_custom_metric("first_token_time", first_token_time)
                                        
                                        token_content = response_data.get("content", "")
                                        response_tokens.append(token_content)
                                    
                                    elif response_type == "complete":
                                        complete_response_time = time.time()
                                        chat_monitor.add_custom_metric("complete_response_time", complete_response_time)
                                        chat_monitor.add_custom_metric("total_tokens", len(response_tokens))
                                        chat_monitor.add_custom_metric("response_length", len("".join(response_tokens)))
                                        break
                                    
                                    elif response_type == "error":
                                        error_msg = f"WebSocket error: {response_data.get('content', 'Unknown error')}"
                                        chat_monitor.add_error(error_msg)
                                        results["errors"].append(error_msg)
                                        break
                                
                                except asyncio.TimeoutError:
                                    error_msg = "WebSocket response timeout"
                                    chat_monitor.add_error(error_msg)
                                    results["errors"].append(error_msg)
                                    break
                
                except Exception as ws_error:
                    error_msg = f"WebSocket connection failed: {str(ws_error)}"
                    monitor.add_error(error_msg)
                    results["errors"].append(error_msg)
        
        except Exception as e:
            error_msg = f"WebSocket test failed: {str(e)}"
            self.monitor.add_error(error_msg)
            results["errors"].append(error_msg)
        
        # End session and collect results
        session_metrics = self.monitor.end_session()
        if session_metrics:
            results["total_duration"] = session_metrics.total_duration
            results["end_time"] = datetime.now().isoformat()
            
            for phase in session_metrics.phases:
                results["phases"][phase.phase_name] = {
                    "duration": phase.duration,
                    "cpu_usage_start": phase.cpu_usage_start,
                    "cpu_usage_end": phase.cpu_usage_end,
                    "memory_usage_start": phase.memory_usage_start,
                    "memory_usage_end": phase.memory_usage_end,
                    "memory_peak": phase.memory_peak,
                    "custom_metrics": phase.custom_metrics
                }
        
        return results
    
    async def test_concurrent_chat_sessions(self, 
                                          concurrent_users: int = 5,
                                          messages_per_user: int = 3) -> Dict[str, Any]:
        """Test concurrent chat sessions to simulate multiple users"""
        
        session_id = self.monitor.start_session(f"chatbot_concurrent_{concurrent_users}_users")
        results = {
            "session_id": session_id,
            "concurrent_users": concurrent_users,
            "messages_per_user": messages_per_user,
            "start_time": datetime.now().isoformat(),
            "individual_results": [],
            "aggregate_metrics": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            async with monitor_phase(self.monitor, "concurrent_chat_sessions") as monitor:
                monitor.add_custom_metric("concurrent_users", concurrent_users)
                monitor.add_custom_metric("messages_per_user", messages_per_user)
                
                # Create tasks for concurrent chat sessions with isolated monitoring
                tasks = []
                for user_id in range(concurrent_users):
                    # Create isolated tester instance for each concurrent user
                    isolated_tester = ChatbotPerformanceTester(self.auth_token)
                    task = asyncio.create_task(
                        isolated_tester._simulate_user_chat_session(user_id + 1, messages_per_user)
                    )
                    tasks.append(task)
                
                # Execute all tasks concurrently and wait for completion
                individual_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                successful_sessions = []
                failed_sessions = []
                
                for i, result in enumerate(individual_results):
                    if isinstance(result, Exception):
                        error_msg = f"User {i+1} session failed: {str(result)}"
                        results["errors"].append(error_msg)
                        failed_sessions.append(i+1)
                    else:
                        results["individual_results"].append(result)
                        if result.get("errors"):
                            failed_sessions.append(i+1)
                        else:
                            successful_sessions.append(result)
                
                monitor.add_custom_metric("successful_sessions", len(successful_sessions))
                monitor.add_custom_metric("failed_sessions", len(failed_sessions))
                
                # Calculate aggregate metrics
                if successful_sessions:
                    response_times = []
                    memory_peaks = []
                    
                    for session in successful_sessions:
                        for message_result in session.get("messages", []):
                            if message_result.get("total_duration"):
                                response_times.append(message_result["total_duration"])
                            
                            phases = message_result.get("phases", {})
                            for phase_data in phases.values():
                                if phase_data.get("memory_peak"):
                                    memory_peaks.append(phase_data["memory_peak"])
                    
                    results["aggregate_metrics"] = {
                        "success_rate": len(successful_sessions) / concurrent_users * 100,
                        "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
                        "min_response_time": min(response_times) if response_times else 0,
                        "max_response_time": max(response_times) if response_times else 0,
                        "avg_memory_peak": sum(memory_peaks) / len(memory_peaks) if memory_peaks else 0,
                        "max_memory_peak": max(memory_peaks) if memory_peaks else 0,
                        "total_messages_processed": len(response_times),
                        "total_successful_sessions": len(successful_sessions),
                        "total_failed_sessions": len(failed_sessions)
                    }
        
        except Exception as e:
            error_msg = f"Concurrent chat test failed: {str(e)}"
            self.monitor.add_error(error_msg)
            results["errors"].append(error_msg)
        
        # End session
        session_metrics = self.monitor.end_session()
        if session_metrics:
            results["total_duration"] = session_metrics.total_duration
            results["end_time"] = datetime.now().isoformat()
        
        return results
    
    async def _simulate_user_chat_session(self, user_id: int, message_count: int) -> Dict[str, Any]:
        """Simulate a single user's chat session"""
        
        session_results = {
            "user_id": user_id,
            "message_count": message_count,
            "messages": [],
            "errors": [],
            "warnings": []
        }
        
        try:
            # Select random messages for this user
            import random
            selected_messages = random.sample(self.test_messages, min(message_count, len(self.test_messages)))
            
            for i, message in enumerate(selected_messages):
                message_result = await self.test_single_chat_response(
                    message=message,
                    lesson_id=1,
                    mode="default"
                )
                
                session_results["messages"].append({
                    "message_index": i + 1,
                    "message": message,
                    "result": message_result
                })
                
                # Add any errors or warnings
                session_results["errors"].extend(message_result.get("errors", []))
                session_results["warnings"].extend(message_result.get("warnings", []))
                
                # Small delay between messages to simulate realistic usage
                await asyncio.sleep(0.5)
        
        except Exception as e:
            session_results["errors"].append(f"User {user_id} session error: {str(e)}")
        
        return session_results
    
    def _evaluate_response_quality(self, response: str, original_message: str) -> float:
        """Simple response quality evaluation"""
        if not response:
            return 0.0
        
        quality_score = 0.0
        
        # Length check (reasonable response length)
        if 50 <= len(response) <= 1000:
            quality_score += 0.3
        
        # Relevance check (contains key terms from question)
        original_words = set(original_message.lower().split())
        response_words = set(response.lower().split())
        overlap = len(original_words.intersection(response_words))
        if overlap > 0:
            quality_score += min(0.3, overlap * 0.1)
        
        # Completeness check (ends with proper punctuation)
        if response.strip().endswith(('.', '!', '?')):
            quality_score += 0.2
        
        # Helpfulness indicators
        helpful_phrases = ['explain', 'example', 'concept', 'understand', 'learn']
        for phrase in helpful_phrases:
            if phrase in response.lower():
                quality_score += 0.04
        
        return min(1.0, quality_score)
    
    async def run_chatbot_performance_suite(self) -> Dict[str, Any]:
        """Run comprehensive chatbot performance test suite"""
        
        suite_results = {
            "suite_start_time": datetime.now().isoformat(),
            "tests": {},
            "summary": {},
            "recommendations": []
        }
        
        # Test 1: Context loading performance
        logger.info("Testing context loading performance...")
        context_test = await self.test_context_loading()
        suite_results["tests"]["context_loading"] = context_test
        
        # Test 2: Single chat response performance
        logger.info("Testing single chat response performance...")
        single_response_test = await self.test_single_chat_response(
            "What is the main topic of this lesson?"
        )
        suite_results["tests"]["single_chat_response"] = single_response_test
        
        # Test 3: WebSocket chat performance
        logger.info("Testing WebSocket chat performance...")
        websocket_test = await self.test_websocket_chat(
            "Can you explain this concept in simple terms?"
        )
        suite_results["tests"]["websocket_chat"] = websocket_test
        
        # Test 4: Multiple message conversation
        logger.info("Testing multiple message conversation...")
        conversation_messages = [
            "What is this lesson about?",
            "Can you give me more details?",
            "What should I focus on?",
            "Create a practice question"
        ]
        
        conversation_results = []
        for i, message in enumerate(conversation_messages):
            result = await self.test_single_chat_response(message)
            conversation_results.append(result)
            await asyncio.sleep(1)  # Simulate thinking time
        
        suite_results["tests"]["conversation_flow"] = {
            "messages": conversation_results,
            "total_messages": len(conversation_results),
            "conversation_duration": sum(r.get("total_duration", 0) for r in conversation_results)
        }
        
        # Test 5: Concurrent users simulation
        logger.info("Testing concurrent chat users...")
        concurrent_test = await self.test_concurrent_chat_sessions(3, 2)
        suite_results["tests"]["concurrent_chat"] = concurrent_test
        
        # Test 6: Load testing
        logger.info("Testing chat system under load...")
        load_test = await self.test_concurrent_chat_sessions(5, 3)
        suite_results["tests"]["load_chat"] = load_test
        
        # Generate summary and recommendations
        suite_results["suite_end_time"] = datetime.now().isoformat()
        suite_results["summary"] = self._generate_chatbot_summary(suite_results["tests"])
        suite_results["recommendations"] = self._generate_chatbot_recommendations(suite_results["tests"])
        
        return suite_results
    
    def _generate_chatbot_summary(self, tests: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from chatbot test results"""
        summary = {
            "total_tests": len(tests),
            "successful_tests": 0,
            "failed_tests": 0,
            "average_response_time": 0,
            "total_warnings": 0,
            "total_errors": 0,
            "performance_issues": [],
            "response_quality_avg": 0
        }
        
        response_times = []
        quality_scores = []
        
        for test_name, test_result in tests.items():
            if test_result.get("errors"):
                summary["failed_tests"] += 1
            else:
                summary["successful_tests"] += 1
            
            # Collect response times
            if test_result.get("total_duration"):
                response_times.append(test_result["total_duration"])
            
            # Collect quality scores
            response_data = test_result.get("response_data", {})
            if response_data.get("response_quality_score"):
                quality_scores.append(response_data["response_quality_score"])
            
            summary["total_warnings"] += len(test_result.get("warnings", []))
            summary["total_errors"] += len(test_result.get("errors", []))
        
        if response_times:
            summary["average_response_time"] = sum(response_times) / len(response_times)
        
        if quality_scores:
            summary["response_quality_avg"] = sum(quality_scores) / len(quality_scores)
        
        return summary
    
    def _generate_chatbot_recommendations(self, tests: Dict[str, Any]) -> List[str]:
        """Generate chatbot optimization recommendations"""
        recommendations = []
        
        # Analyze performance patterns
        slow_responses = []
        high_memory_usage = []
        
        for test_name, test_result in tests.items():
            if test_result.get("total_duration", 0) > self.thresholds["chat_response"]:
                slow_responses.append((test_name, test_result["total_duration"]))
            
            phases = test_result.get("phases", {})
            for phase_name, phase_data in phases.items():
                if phase_data.get("memory_peak", 0) > self.resource_thresholds["max_memory_mb"]:
                    high_memory_usage.append((test_name, phase_data["memory_peak"]))
        
        # Generate specific recommendations
        if slow_responses:
            recommendations.append("🐌 **Response Time Optimization:**")
            for test_name, duration in slow_responses:
                recommendations.append(f"  - {test_name}: {duration:.2f}s (optimize LLM response generation)")
        
        if high_memory_usage:
            recommendations.append("🧠 **Memory Optimization:**")
            for test_name, memory in high_memory_usage:
                recommendations.append(f"  - {test_name}: {memory:.1f}MB (optimize context caching)")
        
        # General chatbot recommendations
        recommendations.extend([
            "🤖 **Chatbot Optimization Recommendations:**",
            "  - Implement response caching for common questions",
            "  - Use streaming responses to improve perceived performance",
            "  - Optimize context window size for better memory usage",
            "  - Implement conversation history pruning",
            "  - Add response quality monitoring and feedback",
            "  - Consider using smaller, faster models for simple queries",
            "  - Implement graceful degradation when LLM is unavailable"
        ])
        
        return recommendations

# Standalone test runner
async def main():
    """Main function to run chatbot performance tests"""
    print("🤖 Starting Pi-LMS AI Chatbot Performance Tests")
    print("=" * 60)
    
    tester = ChatbotPerformanceTester("test_token")
    results = await tester.run_chatbot_performance_suite()
    
    print("\n📊 Test Suite Results:")
    print(f"Total Tests: {results['summary']['total_tests']}")
    print(f"Successful: {results['summary']['successful_tests']}")
    print(f"Failed: {results['summary']['failed_tests']}")
    print(f"Average Response Time: {results['summary']['average_response_time']:.2f}s")
    print(f"Average Response Quality: {results['summary']['response_quality_avg']:.2f}/1.0")
    print(f"Total Warnings: {results['summary']['total_warnings']}")
    print(f"Total Errors: {results['summary']['total_errors']}")
    
    if results['summary']['performance_issues']:
        print("\n⚠️  Performance Issues:")
        for issue in results['summary']['performance_issues']:
            print(f"  - {issue}")
    
    print("\n💡 Recommendations:")
    for rec in results['recommendations']:
        print(rec)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())