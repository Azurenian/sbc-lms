"""
Comprehensive Test Runner for Pi-LMS Performance Testing
Runs all performance tests and generates detailed markdown reports
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import logging
import os

from performance_monitor import PerformanceMonitor
from lesson_generator_tests import LessonGeneratorPerformanceTester
from chatbot_performance_tests import ChatbotPerformanceTester
from system_resource_tests import SystemResourceTester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComprehensiveTestRunner:
    """Runs all Pi-LMS performance tests and generates reports"""
    
    def __init__(self, auth_token: str, output_dir: str = "testing/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.auth_token = auth_token
        
        self.monitor = PerformanceMonitor()

        # Resolve service URLs from environment (injected by Docker)
        frontend_url = os.getenv("FRONTEND_URL")
        ai_url = os.getenv("AI_SERVICES_URL")

        if not all([frontend_url, ai_url]):
            missing = []
            if not frontend_url: missing.append("FRONTEND_URL")
            if not ai_url: missing.append("AI_SERVICES_URL")
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        self.lesson_tester = LessonGeneratorPerformanceTester(
            auth_token=self.auth_token,
            ai_service_url=ai_url,
            performance_monitor=self.monitor,
        )
        self.chatbot_tester = ChatbotPerformanceTester(
            auth_token=self.auth_token,
            ai_service_url=ai_url,
            frontend_url=frontend_url,
            performance_monitor=self.monitor,
        )
        self.resource_tester = SystemResourceTester(performance_monitor=self.monitor)
        
        self.test_results = {}
        self.test_start_time = None
        self.test_end_time = None
    
    async def run_all_tests(self, 
                          include_lesson_tests: bool = True,
                          include_chatbot_tests: bool = True,
                          include_resource_tests: bool = True,
                          include_integration_tests: bool = True) -> Dict[str, Any]:
        """Run all performance tests"""
        
        self.test_start_time = datetime.now()
        logger.info("🚀 Starting comprehensive Pi-LMS performance test suite")
        logger.info("=" * 80)
        
        comprehensive_results = {
            "test_suite": "Pi-LMS Comprehensive Performance Testing",
            "start_time": self.test_start_time.isoformat(),
            "tests": {},
            "summary": {},
            "recommendations": [],
            "metadata": {
                "test_runner": "ComprehensiveTestRunner",
                "version": "1.0.0",
                "components_tested": []
            }
        }
        
        try:
            # Test 1: Lesson Generator Performance
            if include_lesson_tests:
                logger.info("📚 Running Lesson Generator Performance Tests...")
                comprehensive_results["metadata"]["components_tested"].append("lesson_generator")
                try:
                    lesson_results = await self.lesson_tester.run_performance_test_suite()
                    comprehensive_results["tests"]["lesson_generator"] = lesson_results
                    logger.info("✅ Lesson Generator tests completed")
                except Exception as e:
                    logger.error(f"❌ Lesson Generator tests failed: {e}")
                    comprehensive_results["tests"]["lesson_generator"] = {"error": str(e)}
            
            # Add delay between test components to prevent API overload
            if include_lesson_tests and (include_chatbot_tests or include_resource_tests or include_integration_tests):
                logger.info("⏸️  Waiting 60 seconds between test components to prevent API overload...")
                await asyncio.sleep(60)
            
            # Test 2: AI Chatbot Performance
            if include_chatbot_tests:
                logger.info("🤖 Running AI Chatbot Performance Tests...")
                comprehensive_results["metadata"]["components_tested"].append("ai_chatbot")
                try:
                    chatbot_results = await self.chatbot_tester.run_chatbot_performance_suite()
                    comprehensive_results["tests"]["ai_chatbot"] = chatbot_results
                    logger.info("✅ AI Chatbot tests completed")
                except Exception as e:
                    logger.error(f"❌ AI Chatbot tests failed: {e}")
                    comprehensive_results["tests"]["ai_chatbot"] = {"error": str(e)}
            
            # Add delay before system resource tests
            if include_chatbot_tests and (include_resource_tests or include_integration_tests):
                logger.info("⏸️  Waiting 30 seconds before system tests...")
                await asyncio.sleep(30)
            
            # Test 3: System Resource Monitoring
            if include_resource_tests:
                logger.info("💻 Running System Resource Tests...")
                comprehensive_results["metadata"]["components_tested"].append("system_resources")
                try:
                    resource_results = await self.resource_tester.run_system_resource_test_suite()
                    comprehensive_results["tests"]["system_resources"] = resource_results
                    logger.info("✅ System Resource tests completed")
                except Exception as e:
                    logger.error(f"❌ System Resource tests failed: {e}")
                    comprehensive_results["tests"]["system_resources"] = {"error": str(e)}
            
            # Add delay before integration tests
            if include_resource_tests and include_integration_tests:
                logger.info("⏸️  Waiting 30 seconds before integration tests...")
                await asyncio.sleep(30)
            
            # Test 4: Integration and End-to-End Tests
            if include_integration_tests:
                logger.info("🔄 Running Integration Tests...")
                comprehensive_results["metadata"]["components_tested"].append("integration")
                try:
                    integration_results = await self.run_integration_tests()
                    comprehensive_results["tests"]["integration"] = integration_results
                    logger.info("✅ Integration tests completed")
                except Exception as e:
                    logger.error(f"❌ Integration tests failed: {e}")
                    comprehensive_results["tests"]["integration"] = {"error": str(e)}
            
            # Generate comprehensive summary and recommendations
            self.test_end_time = datetime.now()
            comprehensive_results["end_time"] = self.test_end_time.isoformat()
            comprehensive_results["total_duration"] = (self.test_end_time - self.test_start_time).total_seconds()
            
            comprehensive_results["summary"] = self._generate_comprehensive_summary(comprehensive_results["tests"])
            comprehensive_results["recommendations"] = self._generate_comprehensive_recommendations(comprehensive_results["tests"])
            
            # Save results
            self.test_results = comprehensive_results
            await self._save_results(comprehensive_results)
            
            logger.info("🎉 All tests completed successfully!")
            logger.info(f"Total duration: {comprehensive_results['total_duration']:.2f} seconds")
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            comprehensive_results["error"] = str(e)
            comprehensive_results["end_time"] = datetime.now().isoformat()
        
        return comprehensive_results
    
    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests combining multiple components"""
        
        integration_results = {
            "test_type": "integration",
            "start_time": datetime.now().isoformat(),
            "tests": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Test 1: Lesson Generation + Chatbot Integration
            logger.info("Testing lesson generation -> chatbot integration...")
            
            # Generate a lesson first
            lesson_result = await self.lesson_tester.test_single_lesson_generation(
                "integration_test",
                "Integration test content for chatbot testing",
                "Integration Test Lesson"
            )
            
            # Test chatbot with the generated lesson context
            if not lesson_result.get("errors"):
                # Simulate chatbot interaction with lesson
                chatbot_result = await self.chatbot_tester.test_single_chat_response(
                    "What is this lesson about?",
                    lesson_id=1,  # Mock lesson ID
                    mode="default"
                )
                
                integration_results["tests"]["lesson_to_chatbot"] = {
                    "lesson_generation": lesson_result,
                    "chatbot_interaction": chatbot_result,
                    "integration_success": not chatbot_result.get("errors"),
                    "total_workflow_time": lesson_result.get("total_duration", 0) + chatbot_result.get("total_duration", 0)
                }
            else:
                integration_results["errors"].append("Lesson generation failed, skipping chatbot integration")
            
            # Test 2: Concurrent Mixed Workload
            logger.info("Testing concurrent mixed workload...")
            
            async def mixed_workload():
                # Simulate mixed usage: lesson generation + chatbot + resource monitoring
                tasks = []
                
                # Start resource monitoring
                self.resource_tester.start_continuous_monitoring()
                
                # Concurrent lesson generation (2 users)
                for i in range(2):
                    task = asyncio.create_task(
                        self.lesson_tester.test_single_lesson_generation(
                            f"mixed_user_{i}",
                            f"Mixed workload content {i}",
                            f"Mixed Test {i}"
                        )
                    )
                    tasks.append(task)
                
                # Concurrent chatbot sessions (3 users)
                for i in range(3):
                    task = asyncio.create_task(
                        self.chatbot_tester.test_single_chat_response(
                            f"Mixed workload question {i}",
                            lesson_id=1
                        )
                    )
                    tasks.append(task)
                
                # Wait for all tasks
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Stop resource monitoring
                self.resource_tester.stop_continuous_monitoring()
                
                return {
                    "concurrent_tasks": len(tasks),
                    "successful_tasks": sum(1 for r in results if not isinstance(r, Exception) and not r.get("errors")),
                    "failed_tasks": sum(1 for r in results if isinstance(r, Exception) or r.get("errors")),
                    "resource_samples": len(self.resource_tester.resource_history)
                }
            
            mixed_result = await mixed_workload()
            integration_results["tests"]["mixed_workload"] = mixed_result
            
            # Test 3: System Stress Test
            logger.info("Running system stress test...")
            
            async def stress_test():
                # Maximum load test with all components
                stress_results = {
                    "start_time": time.time(),
                    "components": {}
                }
                
                # Start resource monitoring
                self.resource_tester.start_continuous_monitoring()
                
                try:
                    # Heavy lesson generation load
                    lesson_stress = await self.lesson_tester.test_concurrent_generation(3)
                    stress_results["components"]["lesson_generation"] = lesson_stress
                    
                    # Heavy chatbot load
                    chatbot_stress = await self.chatbot_tester.test_concurrent_chat_sessions(5, 2)
                    stress_results["components"]["chatbot"] = chatbot_stress
                    
                    stress_results["end_time"] = time.time()
                    stress_results["duration"] = stress_results["end_time"] - stress_results["start_time"]
                    
                    # Analyze resource usage during stress
                    stress_results["peak_resources"] = self._analyze_peak_resources()
                    
                finally:
                    self.resource_tester.stop_continuous_monitoring()
                
                return stress_results
            
            stress_result = await stress_test()
            integration_results["tests"]["stress_test"] = stress_result
            
        except Exception as e:
            integration_results["errors"].append(f"Integration test failed: {str(e)}")
            logger.error(f"Integration test error: {e}")
        
        integration_results["end_time"] = datetime.now().isoformat()
        return integration_results
    
    def _analyze_peak_resources(self) -> Dict[str, Any]:
        """Analyze peak resource usage from monitoring history"""
        if not self.resource_tester.resource_history:
            return {}
        
        cpu_values = [sample.get("cpu_percent", 0) for sample in self.resource_tester.resource_history]
        memory_values = [sample.get("memory", {}).get("percent", 0) for sample in self.resource_tester.resource_history]
        
        return {
            "peak_cpu": max(cpu_values) if cpu_values else 0,
            "avg_cpu": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "peak_memory": max(memory_values) if memory_values else 0,
            "avg_memory": sum(memory_values) / len(memory_values) if memory_values else 0,
            "samples_count": len(self.resource_tester.resource_history),
            "monitoring_duration": (
                self.resource_tester.resource_history[-1]["timestamp"] - 
                self.resource_tester.resource_history[0]["timestamp"]
            ) if len(self.resource_tester.resource_history) > 1 else 0
        }
    
    def _generate_comprehensive_summary(self, tests: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive summary across all test components"""
        summary = {
            "total_test_components": len(tests),
            "successful_components": 0,
            "failed_components": 0,
            "total_individual_tests": 0,
            "total_warnings": 0,
            "total_errors": 0,
            "performance_scores": {},
            "key_metrics": {},
            "critical_issues": []
        }
        
        for component_name, component_result in tests.items():
            if component_result.get("error"):
                summary["failed_components"] += 1
                summary["critical_issues"].append(f"{component_name}: {component_result['error']}")
            else:
                summary["successful_components"] += 1
                
                # Extract component-specific metrics
                if component_name == "lesson_generator":
                    self._extract_lesson_metrics(component_result, summary)
                elif component_name == "ai_chatbot":
                    self._extract_chatbot_metrics(component_result, summary)
                elif component_name == "system_resources":
                    self._extract_resource_metrics(component_result, summary)
                elif component_name == "integration":
                    self._extract_integration_metrics(component_result, summary)
        
        # Calculate overall performance score
        scores = list(summary["performance_scores"].values())
        summary["overall_performance_score"] = sum(scores) / len(scores) if scores else 0
        
        return summary
    
    def _extract_lesson_metrics(self, results: Dict, summary: Dict):
        """Extract lesson generator metrics"""
        tests = results.get("tests", {})
        summary["total_individual_tests"] += len(tests)
        
        durations = []
        for test_result in tests.values():
            if test_result.get("total_duration"):
                durations.append(test_result["total_duration"])
            summary["total_warnings"] += len(test_result.get("warnings", []))
            summary["total_errors"] += len(test_result.get("errors", []))
        
        if durations:
            summary["key_metrics"]["lesson_avg_duration"] = sum(durations) / len(durations)
            summary["key_metrics"]["lesson_max_duration"] = max(durations)
            
            # Performance score based on speed (target: 120s)
            avg_duration = summary["key_metrics"]["lesson_avg_duration"]
            summary["performance_scores"]["lesson_generation"] = max(0, min(1, (120 - avg_duration) / 120))
    
    def _extract_chatbot_metrics(self, results: Dict, summary: Dict):
        """Extract chatbot metrics"""
        tests = results.get("tests", {})
        summary["total_individual_tests"] += len(tests)
        
        response_times = []
        quality_scores = []
        
        for test_result in tests.values():
            if test_result.get("total_duration"):
                response_times.append(test_result["total_duration"])
            
            response_data = test_result.get("response_data", {})
            if response_data.get("response_quality_score"):
                quality_scores.append(response_data["response_quality_score"])
                
            summary["total_warnings"] += len(test_result.get("warnings", []))
            summary["total_errors"] += len(test_result.get("errors", []))
        
        if response_times:
            summary["key_metrics"]["chatbot_avg_response_time"] = sum(response_times) / len(response_times)
            summary["key_metrics"]["chatbot_max_response_time"] = max(response_times)
            
            # Performance score based on response time (target: 5s)
            avg_response = summary["key_metrics"]["chatbot_avg_response_time"]
            summary["performance_scores"]["chatbot_speed"] = max(0, min(1, (5 - avg_response) / 5))
        
        if quality_scores:
            summary["key_metrics"]["chatbot_avg_quality"] = sum(quality_scores) / len(quality_scores)
            summary["performance_scores"]["chatbot_quality"] = summary["key_metrics"]["chatbot_avg_quality"]
    
    def _extract_resource_metrics(self, results: Dict, summary: Dict):
        """Extract system resource metrics"""
        resource_summary = results.get("summary", {})
        
        summary["key_metrics"]["peak_cpu_usage"] = resource_summary.get("peak_cpu_usage", 0)
        summary["key_metrics"]["peak_memory_usage"] = resource_summary.get("peak_memory_usage", 0)
        summary["key_metrics"]["average_efficiency"] = resource_summary.get("average_efficiency", 0)
        
        # Performance score based on resource efficiency
        efficiency = resource_summary.get("average_efficiency", 0)
        summary["performance_scores"]["resource_efficiency"] = efficiency
        
        # Check for critical resource issues
        if summary["key_metrics"]["peak_cpu_usage"] > 90:
            summary["critical_issues"].append("CPU usage exceeded 90%")
        if summary["key_metrics"]["peak_memory_usage"] > 95:
            summary["critical_issues"].append("Memory usage exceeded 95%")
    
    def _extract_integration_metrics(self, results: Dict, summary: Dict):
        """Extract integration test metrics"""
        tests = results.get("tests", {})
        
        for test_name, test_result in tests.items():
            if test_name == "mixed_workload":
                total_tasks = test_result.get("concurrent_tasks", 0)
                successful_tasks = test_result.get("successful_tasks", 0)
                if total_tasks > 0:
                    success_rate = successful_tasks / total_tasks
                    summary["key_metrics"]["integration_success_rate"] = success_rate
                    summary["performance_scores"]["integration"] = success_rate
    
    def _generate_comprehensive_recommendations(self, tests: Dict[str, Any]) -> List[str]:
        """Generate comprehensive optimization recommendations"""
        recommendations = []
        
        # Collect all component recommendations
        component_recommendations = {}
        
        for component_name, component_result in tests.items():
            if component_result.get("recommendations"):
                component_recommendations[component_name] = component_result["recommendations"]
        
        # Priority recommendations based on critical issues
        recommendations.append("🚨 **Critical Priority Recommendations:**")
        
        # Check for system-wide issues
        resource_results = tests.get("system_resources", {})
        if resource_results:
            peak_cpu = resource_results.get("summary", {}).get("peak_cpu_usage", 0)
            peak_memory = resource_results.get("summary", {}).get("peak_memory_usage", 0)
            
            if peak_cpu > 85:
                recommendations.append("  - URGENT: CPU usage exceeding 85% - implement load balancing")
            if peak_memory > 90:
                recommendations.append("  - URGENT: Memory usage exceeding 90% - optimize memory management")
        
        # Component-specific recommendations
        if "lesson_generator" in component_recommendations:
            recommendations.append("\n📚 **Lesson Generator Optimizations:**")
            for rec in component_recommendations["lesson_generator"][-3:]:  # Last 3 recommendations
                recommendations.append(f"  {rec}")
        
        if "ai_chatbot" in component_recommendations:
            recommendations.append("\n🤖 **AI Chatbot Optimizations:**")
            for rec in component_recommendations["ai_chatbot"][-3:]:
                recommendations.append(f"  {rec}")
        
        if "system_resources" in component_recommendations:
            recommendations.append("\n💻 **System Resource Optimizations:**")
            for rec in component_recommendations["system_resources"][-3:]:
                recommendations.append(f"  {rec}")
        
        # Overall system recommendations
        recommendations.extend([
            "\n🎯 **Overall System Optimization Strategy:**",
            "  - Implement comprehensive caching strategy across all components",
            "  - Set up automated performance monitoring with alerts",
            "  - Consider horizontal scaling for high-load scenarios",
            "  - Optimize database queries and connection pooling",
            "  - Implement graceful degradation for resource constraints",
            "  - Use CDN for static assets and media files",
            "  - Set up load balancing for multiple Orange Pi 5 units if needed"
        ])
        
        return recommendations
    
    async def _save_results(self, results: Dict[str, Any]):
        """Save test results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON results
        json_file = self.output_dir / f"performance_test_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to: {json_file}")
        
        # Generate and save markdown report
        markdown_report = await self.generate_markdown_report(results)
        md_file = self.output_dir / f"performance_test_report_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        
        logger.info(f"Markdown report saved to: {md_file}")
        
        return json_file, md_file
    
    async def generate_markdown_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive markdown report"""
        
        report = f"""# Pi-LMS Performance Testing Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Test Duration:** {results.get('total_duration', 0):.2f} seconds  
**Components Tested:** {', '.join(results.get('metadata', {}).get('components_tested', []))}

---

## Executive Summary

"""
        
        summary = results.get("summary", {})
        
        # Add executive summary
        report += f"""
### Overall Performance Score: {summary.get('overall_performance_score', 0):.2f}/1.0

- **Test Components:** {summary.get('total_test_components', 0)} ({summary.get('successful_components', 0)} successful, {summary.get('failed_components', 0)} failed)
- **Individual Tests:** {summary.get('total_individual_tests', 0)} total tests
- **Warnings:** {summary.get('total_warnings', 0)}
- **Errors:** {summary.get('total_errors', 0)}

"""
        
        # Key metrics table
        key_metrics = summary.get("key_metrics", {})
        if key_metrics:
            report += "### Key Performance Metrics\n\n"
            report += "| Metric | Value | Status |\n"
            report += "|--------|-------|--------|\n"
            
            for metric, value in key_metrics.items():
                # Format value based on type
                if isinstance(value, float):
                    if "time" in metric.lower() or "duration" in metric.lower():
                        formatted_value = f"{value:.2f}s"
                        status = "✅ Good" if value < 10 else "⚠️ Slow" if value < 30 else "❌ Critical"
                    elif "usage" in metric.lower() or "percent" in metric.lower():
                        formatted_value = f"{value:.1f}%"
                        status = "✅ Good" if value < 70 else "⚠️ High" if value < 90 else "❌ Critical"
                    else:
                        formatted_value = f"{value:.2f}"
                        status = "✅ Good" if value > 0.7 else "⚠️ Fair" if value > 0.5 else "❌ Poor"
                else:
                    formatted_value = str(value)
                    status = "ℹ️ Info"
                
                report += f"| {metric.replace('_', ' ').title()} | {formatted_value} | {status} |\n"
            
            report += "\n"
        
        # Critical issues
        critical_issues = summary.get("critical_issues", [])
        if critical_issues:
            report += "### 🚨 Critical Issues\n\n"
            for issue in critical_issues:
                report += f"- ❌ {issue}\n"
            report += "\n"
        
        # Component results
        report += "---\n\n## Detailed Test Results\n\n"
        
        tests = results.get("tests", {})
        
        # Lesson Generator Results
        if "lesson_generator" in tests:
            report += self._generate_lesson_section(tests["lesson_generator"])
        
        # AI Chatbot Results
        if "ai_chatbot" in tests:
            report += self._generate_chatbot_section(tests["ai_chatbot"])
        
        # System Resources Results
        if "system_resources" in tests:
            report += self._generate_resource_section(tests["system_resources"])
        
        # Integration Results
        if "integration" in tests:
            report += self._generate_integration_section(tests["integration"])
        
        # Recommendations
        recommendations = results.get("recommendations", [])
        if recommendations:
            report += "---\n\n## Optimization Recommendations\n\n"
            for recommendation in recommendations:
                report += f"{recommendation}\n"
            report += "\n"
        
        # Technical Details
        report += "---\n\n## Technical Details\n\n"
        report += f"- **Test Runner Version:** {results.get('metadata', {}).get('version', 'Unknown')}\n"
        report += f"- **Start Time:** {results.get('start_time', 'Unknown')}\n"
        report += f"- **End Time:** {results.get('end_time', 'Unknown')}\n"
        report += f"- **Environment:** Pi-LMS on Orange Pi 5\n"
        
        # System information
        if "system_resources" in tests:
            system_info = tests["system_resources"].get("system_info", {})
            if system_info:
                report += f"- **CPU Cores:** {system_info.get('cpu_count', 'Unknown')}\n"
                report += f"- **Total Memory:** {system_info.get('memory_total', 0):.1f} GB\n"
                report += f"- **Platform:** {system_info.get('platform', 'Unknown')}\n"
        
        return report
    
    def _generate_lesson_section(self, lesson_results: Dict[str, Any]) -> str:
        """Generate lesson generator section of report"""
        section = "### 📚 Lesson Generator Performance\n\n"
        
        tests = lesson_results.get("tests", {})
        lesson_summary = lesson_results.get("summary", {})
        
        section += f"**Total Tests:** {lesson_summary.get('total_tests', 0)}  \n"
        section += f"**Success Rate:** {lesson_summary.get('successful_tests', 0)}/{lesson_summary.get('total_tests', 0)}  \n"
        section += f"**Average Duration:** {lesson_summary.get('average_duration', 0):.2f}s  \n"
        section += f"**Performance Issues:** {len(lesson_summary.get('performance_issues', []))}  \n\n"
        
        # Test details table
        if tests:
            section += "#### Test Details\n\n"
            section += "| Test | Duration | Status | Issues |\n"
            section += "|------|----------|--------|---------|\n"
            
            for test_name, test_result in tests.items():
                duration = test_result.get("total_duration", 0)
                errors = len(test_result.get("errors", []))
                warnings = len(test_result.get("warnings", []))
                
                status = "✅ Pass" if errors == 0 else "❌ Fail"
                issues = f"{errors} errors, {warnings} warnings"
                
                section += f"| {test_name} | {duration:.2f}s | {status} | {issues} |\n"
            
            section += "\n"
        
        return section
    
    def _generate_chatbot_section(self, chatbot_results: Dict[str, Any]) -> str:
        """Generate chatbot section of report"""
        section = "### 🤖 AI Chatbot Performance\n\n"
        
        tests = chatbot_results.get("tests", {})
        chatbot_summary = chatbot_results.get("summary", {})
        
        section += f"**Total Tests:** {chatbot_summary.get('total_tests', 0)}  \n"
        section += f"**Success Rate:** {chatbot_summary.get('successful_tests', 0)}/{chatbot_summary.get('total_tests', 0)}  \n"
        section += f"**Average Response Time:** {chatbot_summary.get('average_response_time', 0):.2f}s  \n"
        section += f"**Average Quality Score:** {chatbot_summary.get('response_quality_avg', 0):.2f}/1.0  \n\n"
        
        # Response time analysis
        response_times = []
        for test_result in tests.values():
            if test_result.get("total_duration"):
                response_times.append(test_result["total_duration"])
        
        if response_times:
            section += "#### Response Time Analysis\n\n"
            section += f"- **Fastest Response:** {min(response_times):.2f}s\n"
            section += f"- **Slowest Response:** {max(response_times):.2f}s\n"
            section += f"- **Median Response:** {sorted(response_times)[len(response_times)//2]:.2f}s\n\n"
        
        return section
    
    def _generate_resource_section(self, resource_results: Dict[str, Any]) -> str:
        """Generate system resources section of report"""
        section = "### 💻 System Resource Usage\n\n"
        
        resource_summary = resource_results.get("summary", {})
        
        section += f"**Peak CPU Usage:** {resource_summary.get('peak_cpu_usage', 0):.1f}%  \n"
        section += f"**Peak Memory Usage:** {resource_summary.get('peak_memory_usage', 0):.1f}%  \n"
        section += f"**Average Efficiency:** {resource_summary.get('average_efficiency', 0):.2f}  \n"
        section += f"**Target Violations:** {resource_summary.get('target_violations', 0)}  \n\n"
        
        # Resource usage chart (text-based)
        cpu_peak = resource_summary.get('peak_cpu_usage', 0)
        memory_peak = resource_summary.get('peak_memory_usage', 0)
        
        section += "#### Resource Usage Overview\n\n"
        section += "```\n"
        section += f"CPU Usage:    {'█' * int(cpu_peak / 5):<20} {cpu_peak:.1f}%\n"
        section += f"Memory Usage: {'█' * int(memory_peak / 5):<20} {memory_peak:.1f}%\n"
        section += "```\n\n"
        
        return section
    
    def _generate_integration_section(self, integration_results: Dict[str, Any]) -> str:
        """Generate integration test section of report"""
        section = "### 🔄 Integration Test Results\n\n"
        
        tests = integration_results.get("tests", {})
        
        for test_name, test_result in tests.items():
            section += f"#### {test_name.replace('_', ' ').title()}\n\n"
            
            if test_name == "mixed_workload":
                section += f"- **Concurrent Tasks:** {test_result.get('concurrent_tasks', 0)}\n"
                section += f"- **Successful Tasks:** {test_result.get('successful_tasks', 0)}\n"
                section += f"- **Failed Tasks:** {test_result.get('failed_tasks', 0)}\n"
                section += f"- **Success Rate:** {test_result.get('successful_tasks', 0) / max(1, test_result.get('concurrent_tasks', 1)) * 100:.1f}%\n\n"
            
            elif test_name == "stress_test":
                section += f"- **Test Duration:** {test_result.get('duration', 0):.2f}s\n"
                peak_resources = test_result.get('peak_resources', {})
                section += f"- **Peak CPU:** {peak_resources.get('peak_cpu', 0):.1f}%\n"
                section += f"- **Peak Memory:** {peak_resources.get('peak_memory', 0):.1f}%\n\n"
        
        return section

# Main execution
async def main():
    """Main function to run comprehensive tests"""
    print("🚀 Pi-LMS Comprehensive Performance Testing Suite")
    print("=" * 80)

    # In a real CI/CD environment, this token should be fetched securely
    auth_token = os.getenv("TEST_AUTH_TOKEN", "placeholder_token")
    if auth_token == "placeholder_token":
        logger.warning("Using a placeholder auth token. For real tests, set TEST_AUTH_TOKEN.")

    runner = ComprehensiveTestRunner(auth_token=auth_token)
    
    # Run all tests
    results = await runner.run_all_tests()
    
    # Print summary
    print("\n🎉 Test Suite Completed!")
    print("=" * 80)
    
    summary = results.get("summary", {})
    print(f"Overall Performance Score: {summary.get('overall_performance_score', 0):.2f}/1.0")
    print(f"Components Tested: {summary.get('total_test_components', 0)}")
    print(f"Total Individual Tests: {summary.get('total_individual_tests', 0)}")
    print(f"Success Rate: {summary.get('successful_components', 0)}/{summary.get('total_test_components', 0)} components")
    
    key_metrics = summary.get("key_metrics", {})
    if key_metrics:
        print("\nKey Performance Metrics:")
        for metric, value in key_metrics.items():
            if isinstance(value, float):
                print(f"  - {metric.replace('_', ' ').title()}: {value:.2f}")
            else:
                print(f"  - {metric.replace('_', ' ').title()}: {value}")
    
    critical_issues = summary.get("critical_issues", [])
    if critical_issues:
        print(f"\n🚨 Critical Issues Found: {len(critical_issues)}")
        for issue in critical_issues[:3]:  # Show first 3
            print(f"  - {issue}")
    
    print(f"\nResults saved to: testing/results/")
    print("Check the generated markdown report for detailed analysis and recommendations.")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())