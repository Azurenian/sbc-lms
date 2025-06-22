"""
Lesson Generator Performance Testing
Tests time spent per phase and resource consumption during lesson generation
"""

import asyncio
import aiohttp
import tempfile
import shutil
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import time
from datetime import datetime

from performance_monitor import PerformanceMonitor, monitor_phase
import logging

logger = logging.getLogger(__name__)

class LessonGeneratorPerformanceTester:
    """Performance tester for AI lesson generation pipeline"""
    
    def __init__(self,
                 auth_token: str,
                 ai_service_url: str = os.getenv("AI_SERVICES_URL"),
                 user_id: str = "user123",
                 num_lessons: int = 5,
                 performance_monitor: Optional[PerformanceMonitor] = None):
        self.auth_token = auth_token
        self.ai_service_url = ai_service_url
        self.user_id = user_id
        self.num_lessons = num_lessons
        # Always create a new monitor for thread safety in concurrent tests
        self.monitor = PerformanceMonitor()
        self.test_files_dir = Path("testing/test_files")
        self.test_files_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance thresholds (in seconds)
        self.thresholds = {
            "pdf_upload": 5.0,
            "pdf_processing": 60.0,
            "content_generation": 30.0,
            "narration_generation": 20.0,
            "video_search": 10.0,
            "total_generation": 120.0
        }
        
        # Resource thresholds
        self.resource_thresholds = {
            "max_memory_mb": 500,
            "max_cpu_percent": 80,
            "max_disk_io_mb": 100
        }
    
    async def create_test_pdf(self, content: str, filename: str) -> Path:
        """Create a test PDF file for testing"""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        filepath = self.test_files_dir / filename
        
        try:
            c = canvas.Canvas(str(filepath), pagesize=letter)
            c.drawString(100, 750, "Test PDF for Performance Testing")
            c.drawString(100, 720, f"Generated at: {datetime.now().isoformat()}")
            c.drawString(100, 690, "Content:")
            
            # Add content line by line
            y_position = 660
            for line in content.split('\n'):
                if y_position < 50:  # Start new page
                    c.showPage()
                    y_position = 750
                c.drawString(100, y_position, line[:80])  # Limit line length
                y_position -= 20
            
            c.save()
            logger.info(f"Created test PDF: {filepath}")
            return filepath
            
        except ImportError:
            # Fallback: create a simple text file as "PDF"
            with open(filepath.with_suffix('.txt'), 'w') as f:
                f.write(f"Test Content for Performance Testing\n")
                f.write(f"Generated at: {datetime.now().isoformat()}\n\n")
                f.write(content)
            logger.warning("ReportLab not available, created text file instead")
            return filepath.with_suffix('.txt')
    
    async def test_single_lesson_generation(self, 
                                          test_name: str,
                                          pdf_content: str,
                                          title: str = "Test Lesson",
                                          course_id: int = 1,
                                          custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Test a single lesson generation process"""
        
        session_id = self.monitor.start_session(f"lesson_generation_{test_name}")
        results = {
            "session_id": session_id,
            "test_name": test_name,
            "start_time": datetime.now().isoformat(),
            "phases": {},
            "performance_check": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Phase 1: PDF Creation and Upload
            async with monitor_phase(self.monitor, "pdf_upload") as monitor:
                pdf_path = await self.create_test_pdf(pdf_content, f"test_{test_name}.pdf")
                monitor.add_custom_metric("file_size_bytes", pdf_path.stat().st_size)
                
                # Prepare multipart form data
                data = aiohttp.FormData()
                data.add_field('file', open(pdf_path, 'rb'), filename=pdf_path.name)
                data.add_field('title', title)
                data.add_field('course_id', str(course_id))
                data.add_field('auth_token', self.auth_token)
                if custom_prompt:
                    data.add_field('prompt', custom_prompt)
                
                # Upload PDF
                headers = {'Authorization': f'Bearer {self.auth_token}'}
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{self.ai_service_url}/process-pdf/", data=data, headers=headers) as response:
                        if response.status == 200:
                            upload_result = await response.json()
                            lesson_session_id = upload_result.get("session_id")
                            monitor.add_custom_metric("lesson_session_id", lesson_session_id)
                        else:
                            error_msg = f"PDF upload failed: {response.status}"
                            monitor.add_error(error_msg)
                            results["errors"].append(error_msg)
                            return results
            
            # Phase 2: Monitor PDF Processing
            async with monitor_phase(self.monitor, "pdf_processing") as monitor:
                processing_complete = False
                start_time = time.time()
                
                while not processing_complete and (time.time() - start_time) < 300:  # 5 min timeout
                    headers = {'Authorization': f'Bearer {self.auth_token}'}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.ai_service_url}/progress/{lesson_session_id}", headers=headers) as response:
                            if response.status == 200:
                                progress_data = await response.json()
                                stage = progress_data.get("stage")
                                progress = progress_data.get("progress", 0)
                                message = progress_data.get("message", "")
                                
                                monitor.add_custom_metric("current_stage", stage)
                                monitor.add_custom_metric("current_progress", progress)
                                monitor.add_custom_metric("current_message", message)
                                
                                if stage == "selection" and progress >= 100:
                                    processing_complete = True
                                elif stage == "error":
                                    error_msg = f"Processing failed: {message}"
                                    monitor.add_error(error_msg)
                                    results["errors"].append(error_msg)
                                    return results
                    
                    await asyncio.sleep(2)  # Check every 2 seconds
                
                if not processing_complete:
                    error_msg = "Processing timeout"
                    monitor.add_error(error_msg)
                    results["errors"].append(error_msg)
                    return results
            
            # Phase 3: Retrieve Generated Lesson
            async with monitor_phase(self.monitor, "lesson_retrieval") as monitor:
                headers = {'Authorization': f'Bearer {self.auth_token}'}
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.ai_service_url}/lesson-result/{lesson_session_id}", headers=headers) as response:
                        if response.status == 200:
                            lesson_data = await response.json()
                            monitor.add_custom_metric("lesson_data_size", len(json.dumps(lesson_data)))
                            
                            # Analyze lesson structure
                            lesson_content = lesson_data.get("lesson_data", {})
                            content_structure = lesson_content.get("content", {})
                            if "root" in content_structure:
                                children_count = len(content_structure["root"].get("children", []))
                                monitor.add_custom_metric("content_children_count", children_count)
                            
                            youtube_videos = lesson_data.get("youtube_videos", [])
                            monitor.add_custom_metric("youtube_videos_found", len(youtube_videos))
                            
                        else:
                            error_msg = f"Failed to retrieve lesson: {response.status}"
                            monitor.add_error(error_msg)
                            results["errors"].append(error_msg)
            
            # Cleanup test file
            if pdf_path.exists():
                pdf_path.unlink()
                
        except Exception as e:
            error_msg = f"Test failed with exception: {str(e)}"
            self.monitor.add_error(error_msg)
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        # End session and get final metrics
        session_metrics = self.monitor.end_session()
        if session_metrics:
            results["total_duration"] = session_metrics.total_duration
            results["end_time"] = datetime.now().isoformat()
            
            # Analyze phase performance
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
                
                # Check against thresholds
                threshold_key = phase.phase_name.replace("_", "_")
                if threshold_key in self.thresholds:
                    threshold = self.thresholds[threshold_key]
                    if phase.duration > threshold:
                        warning_msg = f"Phase {phase.phase_name} exceeded threshold: {phase.duration:.2f}s > {threshold}s"
                        results["warnings"].append(warning_msg)
                        logger.warning(warning_msg)
                
                # Check resource usage
                if phase.memory_peak > self.resource_thresholds["max_memory_mb"]:
                    warning_msg = f"Phase {phase.phase_name} exceeded memory threshold: {phase.memory_peak:.2f}MB"
                    results["warnings"].append(warning_msg)
                
                cpu_max = max(phase.cpu_usage_start, phase.cpu_usage_end)
                if cpu_max > self.resource_thresholds["max_cpu_percent"]:
                    warning_msg = f"Phase {phase.phase_name} exceeded CPU threshold: {cpu_max:.1f}%"
                    results["warnings"].append(warning_msg)
            
            # Overall performance check
            results["performance_check"] = {
                "total_duration_ok": session_metrics.total_duration <= self.thresholds["total_generation"],
                "memory_usage_ok": all(p.memory_peak <= self.resource_thresholds["max_memory_mb"] for p in session_metrics.phases),
                "cpu_usage_ok": all(max(p.cpu_usage_start, p.cpu_usage_end) <= self.resource_thresholds["max_cpu_percent"] for p in session_metrics.phases),
                "errors_count": len(session_metrics.errors),
                "warnings_count": len(session_metrics.warnings)
            }
        
        return results
    
    async def test_concurrent_generation(self, 
                                       concurrent_users: int = 5,
                                       test_content: str = "Sample content for concurrent testing") -> Dict[str, Any]:
        """Test concurrent lesson generation to simulate multiple users"""
        
        session_id = self.monitor.start_session(f"concurrent_generation_{concurrent_users}_users")
        results = {
            "session_id": session_id,
            "concurrent_users": concurrent_users,
            "start_time": datetime.now().isoformat(),
            "individual_results": [],
            "aggregate_metrics": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            async with monitor_phase(self.monitor, "concurrent_lesson_generation") as monitor:
                monitor.add_custom_metric("concurrent_users", concurrent_users)
                
                # Create tasks for concurrent execution with isolated monitoring
                tasks = []
                for i in range(concurrent_users):
                    # Create isolated tester instance for each concurrent user
                    isolated_tester = LessonGeneratorPerformanceTester(auth_token=self.auth_token, ai_service_url=self.ai_service_url, user_id=self.user_id, num_lessons=self.num_lessons)
                    task = asyncio.create_task(
                        isolated_tester.test_single_lesson_generation(
                            test_name=f"concurrent_user_{i+1}",
                            pdf_content=f"{test_content} - User {i+1}",
                            title=f"Concurrent Test Lesson {i+1}",
                            course_id=1
                        )
                    )
                    tasks.append(task)
                
                # Execute all tasks concurrently and wait for completion
                individual_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                successful_tests = []
                failed_tests = []
                
                for i, result in enumerate(individual_results):
                    if isinstance(result, Exception):
                        error_msg = f"User {i+1} failed: {str(result)}"
                        results["errors"].append(error_msg)
                        failed_tests.append(i+1)
                    else:
                        results["individual_results"].append(result)
                        if result.get("errors"):
                            failed_tests.append(i+1)
                        else:
                            successful_tests.append(result)
                
                monitor.add_custom_metric("successful_tests", len(successful_tests))
                monitor.add_custom_metric("failed_tests", len(failed_tests))
                
                # Calculate aggregate metrics
                if successful_tests:
                    total_durations = [r["total_duration"] for r in successful_tests if r.get("total_duration")]
                    results["aggregate_metrics"] = {
                        "success_rate": len(successful_tests) / concurrent_users * 100,
                        "avg_duration": sum(total_durations) / len(total_durations) if total_durations else 0,
                        "min_duration": min(total_durations) if total_durations else 0,
                        "max_duration": max(total_durations) if total_durations else 0,
                        "total_successful": len(successful_tests),
                        "total_failed": len(failed_tests)
                    }
                
                # Log completion for debugging
                logger.info(f"Concurrent test completed: {len(successful_tests)} successful, {len(failed_tests)} failed")
                
        except Exception as e:
            error_msg = f"Concurrent test failed: {str(e)}"
            self.monitor.add_error(error_msg)
            results["errors"].append(error_msg)
        
        # End session
        session_metrics = self.monitor.end_session()
        if session_metrics:
            results["total_duration"] = session_metrics.total_duration
            results["end_time"] = datetime.now().isoformat()
        
        return results
    
    async def run_performance_test_suite(self) -> Dict[str, Any]:
        """Run comprehensive performance test suite with API rate limiting"""
        
        suite_results = {
            "suite_start_time": datetime.now().isoformat(),
            "tests": {},
            "summary": {},
            "recommendations": []
        }
        
        # Test 1: Basic lesson generation
        logger.info("Running basic lesson generation test...")
        basic_test = await self.test_single_lesson_generation(
            "basic_generation",
            "This is a basic test lesson about mathematics. It covers fundamental concepts like addition, subtraction, multiplication, and division.",
            "Basic Math Lesson"
        )
        suite_results["tests"]["basic_generation"] = basic_test
        
        # Add delay between operations to prevent API overload
        logger.info("Waiting 20 seconds before next test to prevent Gemini API overload...")
        await asyncio.sleep(20)
        
        # Test 2: Large content lesson generation
        logger.info("Running large content lesson generation test...")
        large_content = """
        Advanced Mathematics and Calculus
        
        Chapter 1: Introduction to Differential Calculus
        Differential calculus is a fundamental branch of mathematics that deals with the study of rates of change and slopes of curves. The primary tool used in differential calculus is the derivative, which measures how a function changes as its input changes.
        
        Chapter 2: Limits and Continuity
        Before we can understand derivatives, we must first understand the concept of limits. A limit describes the value that a function approaches as the input approaches some value.
        
        Chapter 3: The Derivative
        The derivative of a function at a point is the slope of the tangent line to the function at that point. It represents the instantaneous rate of change of the function.
        
        Chapter 4: Rules of Differentiation
        There are several rules that make finding derivatives easier: the power rule, product rule, quotient rule, and chain rule.
        
        Chapter 5: Applications of Derivatives
        Derivatives have many practical applications in physics, engineering, economics, and other fields.
        """ * 3  # Make it larger
        
        large_test = await self.test_single_lesson_generation(
            "large_content_generation",
            large_content,
            "Advanced Calculus Course"
        )
        suite_results["tests"]["large_content_generation"] = large_test
        
        # Add delay before concurrent tests
        logger.info("Waiting 30 seconds before concurrent tests to prevent Gemini API overload...")
        await asyncio.sleep(30)
        
        # Test 3: Concurrent users simulation
        logger.info("Running concurrent users test...")
        concurrent_test = await self.test_concurrent_generation(3)  # Start with 3 users
        suite_results["tests"]["concurrent_generation"] = concurrent_test
        
        # Add delay before load test
        logger.info("Waiting 30 seconds before load test to prevent Gemini API overload...")
        await asyncio.sleep(30)
        
        # Test 4: Performance under load
        logger.info("Running performance under load test...")
        load_test = await self.test_concurrent_generation(5)  # 5 concurrent users
        suite_results["tests"]["load_generation"] = load_test
        
        # Generate summary and recommendations
        suite_results["suite_end_time"] = datetime.now().isoformat()
        suite_results["summary"] = self._generate_test_summary(suite_results["tests"])
        suite_results["recommendations"] = self._generate_recommendations(suite_results["tests"])
        
        return suite_results
    
    def _generate_test_summary(self, tests: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from test results"""
        summary = {
            "total_tests": len(tests),
            "successful_tests": 0,
            "failed_tests": 0,
            "average_duration": 0,
            "total_warnings": 0,
            "total_errors": 0,
            "performance_issues": []
        }
        
        durations = []
        for test_name, test_result in tests.items():
            if test_result.get("errors"):
                summary["failed_tests"] += 1
            else:
                summary["successful_tests"] += 1
            
            if test_result.get("total_duration"):
                durations.append(test_result["total_duration"])
            
            summary["total_warnings"] += len(test_result.get("warnings", []))
            summary["total_errors"] += len(test_result.get("errors", []))
            
            # Check for performance issues
            performance_check = test_result.get("performance_check", {})
            if not performance_check.get("total_duration_ok", True):
                summary["performance_issues"].append(f"{test_name}: Duration exceeded threshold")
            if not performance_check.get("memory_usage_ok", True):
                summary["performance_issues"].append(f"{test_name}: Memory usage exceeded threshold")
            if not performance_check.get("cpu_usage_ok", True):
                summary["performance_issues"].append(f"{test_name}: CPU usage exceeded threshold")
        
        if durations:
            summary["average_duration"] = sum(durations) / len(durations)
        
        return summary
    
    def _generate_recommendations(self, tests: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Analyze performance patterns
        slow_phases = {}
        high_memory_phases = {}
        
        for test_name, test_result in tests.items():
            phases = test_result.get("phases", {})
            for phase_name, phase_data in phases.items():
                duration = phase_data.get("duration", 0)
                memory_peak = phase_data.get("memory_peak", 0)
                
                if duration > self.thresholds.get(phase_name, float('inf')):
                    if phase_name not in slow_phases:
                        slow_phases[phase_name] = []
                    slow_phases[phase_name].append(duration)
                
                if memory_peak > self.resource_thresholds["max_memory_mb"]:
                    if phase_name not in high_memory_phases:
                        high_memory_phases[phase_name] = []
                    high_memory_phases[phase_name].append(memory_peak)
        
        # Generate recommendations based on analysis
        if slow_phases:
            recommendations.append("⚡ **Performance Optimization Needed:**")
            for phase, durations in slow_phases.items():
                avg_duration = sum(durations) / len(durations)
                recommendations.append(f"  - {phase}: Average {avg_duration:.2f}s (consider caching or optimization)")
        
        if high_memory_phases:
            recommendations.append("🧠 **Memory Optimization Needed:**")
            for phase, memory_usage in high_memory_phases.items():
                avg_memory = sum(memory_usage) / len(memory_usage)
                recommendations.append(f"  - {phase}: Average {avg_memory:.1f}MB (consider memory cleanup)")
        
        # General recommendations
        recommendations.extend([
            "📊 **General Recommendations:**",
            "  - Monitor CPU and memory usage during peak hours",
            "  - Implement caching for frequently accessed lesson content", 
            "  - Consider using background task queues for long-running operations",
            "  - Set up automated performance monitoring alerts",
            "  - Optimize database queries for lesson and course data"
        ])
        
        return recommendations

# Standalone test runner
async def main():
    """Main function to run lesson generator performance tests"""
    print("🚀 Starting Pi-LMS Lesson Generator Performance Tests")
    print("=" * 60)
    
    tester = LessonGeneratorPerformanceTester()
    results = await tester.run_performance_test_suite()
    
    print("\n📊 Test Suite Results:")
    print(f"Total Tests: {results['summary']['total_tests']}")
    print(f"Successful: {results['summary']['successful_tests']}")
    print(f"Failed: {results['summary']['failed_tests']}")
    print(f"Average Duration: {results['summary']['average_duration']:.2f}s")
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