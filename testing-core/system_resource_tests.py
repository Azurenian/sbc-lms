"""
System Resource Consumption Tests
Monitors CPU, memory, disk, and network usage across Pi-LMS components
"""

import asyncio
import psutil
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from pathlib import Path
import sqlite3
import threading

from performance_monitor import PerformanceMonitor, ResourceMonitor, monitor_phase

logger = logging.getLogger(__name__)

class SystemResourceTester:
    """Comprehensive system resource monitoring and testing"""
    
    def __init__(self,
                 monitoring_interval: float = 1.0,
                 performance_monitor: Optional[PerformanceMonitor] = None):
        self.monitoring_interval = monitoring_interval
        # Always create a new monitor for thread safety in concurrent tests
        self.monitor = PerformanceMonitor()
        self.resource_monitor = ResourceMonitor()
        
        # Resource thresholds for Orange Pi 5
        self.thresholds = {
            "cpu_warning": 70.0,      # % CPU usage
            "cpu_critical": 85.0,     # % CPU usage  
            "memory_warning": 75.0,   # % Memory usage
            "memory_critical": 90.0,  # % Memory usage
            "disk_io_warning": 50.0,  # MB/s sustained
            "disk_io_critical": 100.0, # MB/s sustained
            "network_warning": 10.0,  # MB/s sustained
            "network_critical": 20.0, # MB/s sustained
            "load_warning": 4.0,      # Load average (for 4-core Orange Pi 5)
            "load_critical": 6.0      # Load average
        }
        
        # Performance targets for Orange Pi 5
        self.performance_targets = {
            "max_concurrent_users": 50,
            "target_response_time": 3.0,  # seconds
            "max_memory_per_user": 20.0,  # MB
            "target_cpu_per_user": 2.0,   # % CPU
        }
        
        self.monitoring_active = False
        self.resource_history = []
        self._monitoring_thread = None
    
    def start_continuous_monitoring(self):
        """Start continuous resource monitoring in background"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.resource_history = []
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        logger.info("Started continuous resource monitoring")
    
    def stop_continuous_monitoring(self):
        """Stop continuous resource monitoring"""
        self.monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
        logger.info("Stopped continuous resource monitoring")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                timestamp = time.time()
                
                # Collect system metrics
                cpu_percent = self.resource_monitor.get_cpu_usage()
                memory_info = self.resource_monitor.get_memory_usage()
                disk_io = self.resource_monitor.get_disk_io()
                network_io = self.resource_monitor.get_network_io()
                
                # Get process-specific information
                process_info = self._get_process_metrics()
                
                # Get system load
                try:
                    load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
                except:
                    load_avg = [0, 0, 0]
                
                resource_snapshot = {
                    "timestamp": timestamp,
                    "datetime": datetime.fromtimestamp(timestamp).isoformat(),
                    "cpu_percent": cpu_percent,
                    "memory": memory_info,
                    "disk_io": disk_io,
                    "network_io": network_io,
                    "load_average": load_avg,
                    "processes": process_info,
                    "alerts": self._check_thresholds(cpu_percent, memory_info, load_avg)
                }
                
                self.resource_history.append(resource_snapshot)
                
                # Keep only last hour of data (3600 seconds / interval)
                max_history = int(3600 / self.monitoring_interval)
                if len(self.resource_history) > max_history:
                    self.resource_history = self.resource_history[-max_history:]
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _get_process_metrics(self) -> Dict[str, Any]:
        """Get metrics for Pi-LMS related processes"""
        process_info = {
            "pi_ai": [],
            "pi_frontend": [],
            "pi_backend": [],
            "total_processes": 0
        }
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'cmdline']):
                try:
                    info = proc.info
                    cmdline_list = info.get('cmdline') or []
                    cmdline = ' '.join(cmdline_list) if cmdline_list else ''
                    
                    # Identify Pi-LMS processes
                    if any(keyword in cmdline.lower() for keyword in ['pi-ai', 'api.py', 'uvicorn']):
                        if 'api.py' in cmdline or 'pi-ai' in cmdline:
                            process_info["pi_ai"].append({
                                "pid": info['pid'],
                                "name": info['name'],
                                "cpu_percent": info['cpu_percent'],
                                "memory_mb": info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0
                            })
                    
                    elif any(keyword in cmdline.lower() for keyword in ['pi-frontend', 'main.py', 'fastapi']):
                        if 'main.py' in cmdline or 'pi-frontend' in cmdline:
                            process_info["pi_frontend"].append({
                                "pid": info['pid'],
                                "name": info['name'], 
                                "cpu_percent": info['cpu_percent'],
                                "memory_mb": info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0
                            })
                    
                    elif any(keyword in cmdline.lower() for keyword in ['payload', 'next', 'pi-lms-backend']):
                        if any(x in cmdline for x in ['payload', 'next dev', 'pi-lms-backend']):
                            process_info["pi_backend"].append({
                                "pid": info['pid'],
                                "name": info['name'],
                                "cpu_percent": info['cpu_percent'],
                                "memory_mb": info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0
                            })
                    
                    process_info["total_processes"] += 1
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Error getting process metrics: {e}")
        
        return process_info
    
    def _check_thresholds(self, cpu_percent: float, memory_info: Dict, load_avg: List[float]) -> List[str]:
        """Check resource usage against thresholds"""
        alerts = []
        
        # CPU alerts
        if cpu_percent >= self.thresholds["cpu_critical"]:
            alerts.append(f"CRITICAL: CPU usage {cpu_percent:.1f}% >= {self.thresholds['cpu_critical']}%")
        elif cpu_percent >= self.thresholds["cpu_warning"]:
            alerts.append(f"WARNING: CPU usage {cpu_percent:.1f}% >= {self.thresholds['cpu_warning']}%")
        
        # Memory alerts
        memory_percent = memory_info.get("percent", 0)
        if memory_percent >= self.thresholds["memory_critical"]:
            alerts.append(f"CRITICAL: Memory usage {memory_percent:.1f}% >= {self.thresholds['memory_critical']}%")
        elif memory_percent >= self.thresholds["memory_warning"]:
            alerts.append(f"WARNING: Memory usage {memory_percent:.1f}% >= {self.thresholds['memory_warning']}%")
        
        # Load average alerts (1-minute load)
        if load_avg and len(load_avg) > 0:
            load_1min = load_avg[0]
            if load_1min >= self.thresholds["load_critical"]:
                alerts.append(f"CRITICAL: Load average {load_1min:.2f} >= {self.thresholds['load_critical']}")
            elif load_1min >= self.thresholds["load_warning"]:
                alerts.append(f"WARNING: Load average {load_1min:.2f} >= {self.thresholds['load_warning']}")
        
        return alerts
    
    async def test_baseline_resource_usage(self, duration: int = 60) -> Dict[str, Any]:
        """Test baseline system resource usage without load"""
        
        session_id = self.monitor.start_session("baseline_resource_test")
        results = {
            "session_id": session_id,
            "test_type": "baseline",
            "duration": duration,
            "start_time": datetime.now().isoformat(),
            "samples": [],
            "statistics": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            async with monitor_phase(self.monitor, "baseline_monitoring") as monitor:
                monitor.add_custom_metric("duration_seconds", duration)
                
                start_time = time.time()
                sample_count = 0
                
                while (time.time() - start_time) < duration:
                    # Collect resource sample
                    sample = {
                        "timestamp": time.time(),
                        "cpu_percent": self.resource_monitor.get_cpu_usage(),
                        "memory": self.resource_monitor.get_memory_usage(),
                        "disk_io": self.resource_monitor.get_disk_io(),
                        "network_io": self.resource_monitor.get_network_io(),
                        "processes": self._get_process_metrics()
                    }
                    
                    results["samples"].append(sample)
                    sample_count += 1
                    
                    await asyncio.sleep(self.monitoring_interval)
                
                monitor.add_custom_metric("samples_collected", sample_count)
                
                # Calculate statistics
                results["statistics"] = self._calculate_resource_statistics(results["samples"])
                
        except Exception as e:
            error_msg = f"Baseline test failed: {str(e)}"
            self.monitor.add_error(error_msg)
            results["errors"].append(error_msg)
        
        # End session
        session_metrics = self.monitor.end_session()
        if session_metrics:
            results["total_duration"] = session_metrics.total_duration
            results["end_time"] = datetime.now().isoformat()
        
        return results
    
    async def test_load_resource_usage(self, 
                                     test_function,
                                     test_name: str,
                                     duration: int = 300) -> Dict[str, Any]:
        """Test resource usage under specific load"""
        
        session_id = self.monitor.start_session(f"load_resource_test_{test_name}")
        results = {
            "session_id": session_id,
            "test_type": "load",
            "test_name": test_name,
            "duration": duration,
            "start_time": datetime.now().isoformat(),
            "samples": [],
            "load_test_results": None,
            "statistics": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Start continuous monitoring
            self.start_continuous_monitoring()
            
            async with monitor_phase(self.monitor, f"load_test_{test_name}") as monitor:
                monitor.add_custom_metric("duration_seconds", duration)
                
                # Run the load test function
                load_start_time = time.time()
                load_results = await test_function()
                load_end_time = time.time()
                
                results["load_test_results"] = load_results
                monitor.add_custom_metric("load_test_duration", load_end_time - load_start_time)
                
                # Continue monitoring for a bit after load test
                post_test_duration = min(30, duration - (load_end_time - load_start_time))
                if post_test_duration > 0:
                    await asyncio.sleep(post_test_duration)
                
                # Copy resource history for this test
                results["samples"] = self.resource_history.copy()
                monitor.add_custom_metric("samples_collected", len(results["samples"]))
                
                # Calculate statistics
                results["statistics"] = self._calculate_resource_statistics(results["samples"])
                
                # Analyze performance vs targets
                results["performance_analysis"] = self._analyze_performance_vs_targets(
                    results["statistics"], 
                    load_results
                )
            
            # Stop monitoring
            self.stop_continuous_monitoring()
            
        except Exception as e:
            error_msg = f"Load test {test_name} failed: {str(e)}"
            self.monitor.add_error(error_msg)
            results["errors"].append(error_msg)
            self.stop_continuous_monitoring()
        
        # End session
        session_metrics = self.monitor.end_session()
        if session_metrics:
            results["total_duration"] = session_metrics.total_duration
            results["end_time"] = datetime.now().isoformat()
        
        return results
    
    def _calculate_resource_statistics(self, samples: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics from resource samples"""
        if not samples:
            return {}
        
        # Extract metrics
        cpu_values = [s["cpu_percent"] for s in samples if "cpu_percent" in s]
        memory_values = [s["memory"]["percent"] for s in samples if "memory" in s and "percent" in s["memory"]]
        memory_used_values = [s["memory"]["used"] for s in samples if "memory" in s and "used" in s["memory"]]
        
        # Process metrics
        pi_ai_cpu = []
        pi_ai_memory = []
        pi_frontend_cpu = []
        pi_frontend_memory = []
        pi_backend_cpu = []
        pi_backend_memory = []
        
        for sample in samples:
            processes = sample.get("processes", {})
            
            # Pi-AI metrics
            for proc in processes.get("pi_ai", []):
                if proc.get("cpu_percent"):
                    pi_ai_cpu.append(proc["cpu_percent"])
                if proc.get("memory_mb"):
                    pi_ai_memory.append(proc["memory_mb"])
            
            # Pi-Frontend metrics
            for proc in processes.get("pi_frontend", []):
                if proc.get("cpu_percent"):
                    pi_frontend_cpu.append(proc["cpu_percent"])
                if proc.get("memory_mb"):
                    pi_frontend_memory.append(proc["memory_mb"])
            
            # Pi-Backend metrics
            for proc in processes.get("pi_backend", []):
                if proc.get("cpu_percent"):
                    pi_backend_cpu.append(proc["cpu_percent"])
                if proc.get("memory_mb"):
                    pi_backend_memory.append(proc["memory_mb"])
        
        def calc_stats(values):
            if not values:
                return {"min": 0, "max": 0, "avg": 0, "median": 0}
            sorted_vals = sorted(values)
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "median": sorted_vals[len(sorted_vals) // 2]
            }
        
        statistics = {
            "sample_count": len(samples),
            "duration": samples[-1]["timestamp"] - samples[0]["timestamp"] if len(samples) > 1 else 0,
            "system": {
                "cpu": calc_stats(cpu_values),
                "memory_percent": calc_stats(memory_values),
                "memory_used_mb": calc_stats(memory_used_values)
            },
            "processes": {
                "pi_ai": {
                    "cpu": calc_stats(pi_ai_cpu),
                    "memory_mb": calc_stats(pi_ai_memory)
                },
                "pi_frontend": {
                    "cpu": calc_stats(pi_frontend_cpu),
                    "memory_mb": calc_stats(pi_frontend_memory)
                },
                "pi_backend": {
                    "cpu": calc_stats(pi_backend_cpu),
                    "memory_mb": calc_stats(pi_backend_memory)
                }
            }
        }
        
        return statistics
    
    def _analyze_performance_vs_targets(self, statistics: Dict, load_results: Dict) -> Dict[str, Any]:
        """Analyze performance against Orange Pi 5 targets"""
        analysis = {
            "meets_targets": True,
            "target_violations": [],
            "efficiency_score": 0.0,
            "recommendations": []
        }
        
        try:
            # Extract concurrent users from load results
            concurrent_users = 1  # Default
            if isinstance(load_results, dict):
                concurrent_users = load_results.get("concurrent_users", 1)
                if "aggregate_metrics" in load_results:
                    concurrent_users = load_results["aggregate_metrics"].get("total_successful", 1)
            
            # Check CPU efficiency
            system_cpu_avg = statistics.get("system", {}).get("cpu", {}).get("avg", 0)
            cpu_per_user = system_cpu_avg / concurrent_users if concurrent_users > 0 else system_cpu_avg
            
            if cpu_per_user > self.performance_targets["target_cpu_per_user"]:
                analysis["meets_targets"] = False
                analysis["target_violations"].append(
                    f"CPU per user: {cpu_per_user:.1f}% > target {self.performance_targets['target_cpu_per_user']}%"
                )
            
            # Check memory efficiency
            system_memory_mb = statistics.get("system", {}).get("memory_used_mb", {}).get("avg", 0)
            memory_per_user = system_memory_mb / concurrent_users if concurrent_users > 0 else system_memory_mb
            
            if memory_per_user > self.performance_targets["max_memory_per_user"]:
                analysis["meets_targets"] = False
                analysis["target_violations"].append(
                    f"Memory per user: {memory_per_user:.1f}MB > target {self.performance_targets['max_memory_per_user']}MB"
                )
            
            # Check overall system limits
            if system_cpu_avg > self.thresholds["cpu_warning"]:
                analysis["target_violations"].append(
                    f"System CPU usage: {system_cpu_avg:.1f}% > warning threshold {self.thresholds['cpu_warning']}%"
                )
            
            memory_percent = statistics.get("system", {}).get("memory_percent", {}).get("avg", 0)
            if memory_percent > self.thresholds["memory_warning"]:
                analysis["target_violations"].append(
                    f"System memory usage: {memory_percent:.1f}% > warning threshold {self.thresholds['memory_warning']}%"
                )
            
            # Calculate efficiency score (0-1)
            cpu_efficiency = max(0, 1 - (cpu_per_user / self.performance_targets["target_cpu_per_user"]))
            memory_efficiency = max(0, 1 - (memory_per_user / self.performance_targets["max_memory_per_user"]))
            analysis["efficiency_score"] = (cpu_efficiency + memory_efficiency) / 2
            
            # Generate recommendations
            if not analysis["meets_targets"]:
                analysis["recommendations"].extend([
                    "🎯 **Performance Optimization Needed:**",
                    f"  - Current capacity: ~{concurrent_users} users",
                    f"  - Target capacity: {self.performance_targets['max_concurrent_users']} users",
                    "  - Consider optimizing resource-intensive operations",
                    "  - Implement caching and load balancing strategies"
                ])
        
        except Exception as e:
            logger.error(f"Error in performance analysis: {e}")
            analysis["analysis_error"] = str(e)
        
        return analysis
    
    async def run_system_resource_test_suite(self) -> Dict[str, Any]:
        """Run comprehensive system resource test suite"""
        
        suite_results = {
            "suite_start_time": datetime.now().isoformat(),
            "system_info": self.resource_monitor.get_system_info(),
            "tests": {},
            "summary": {},
            "recommendations": []
        }
        
        # Test 1: Baseline resource usage
        logger.info("Testing baseline system resource usage...")
        baseline_test = await self.test_baseline_resource_usage(60)
        suite_results["tests"]["baseline"] = baseline_test
        
        # Test 2: Import and test lesson generator performance
        try:
            from lesson_generator_tests import LessonGeneratorPerformanceTester
            
            logger.info("Testing lesson generator resource usage...")
            lesson_tester = LessonGeneratorPerformanceTester()
            
            async def lesson_load_test():
                return await lesson_tester.test_concurrent_generation(3)
            
            lesson_resource_test = await self.test_load_resource_usage(
                lesson_load_test,
                "lesson_generation",
                300
            )
            suite_results["tests"]["lesson_generation"] = lesson_resource_test
            
        except ImportError as e:
            logger.warning(f"Could not import lesson generator tests: {e}")
        
        # Test 3: Import and test chatbot performance
        try:
            from chatbot_performance_tests import ChatbotPerformanceTester
            
            logger.info("Testing chatbot resource usage...")
            chatbot_tester = ChatbotPerformanceTester()
            
            async def chatbot_load_test():
                return await chatbot_tester.test_concurrent_chat_sessions(5, 3)
            
            chatbot_resource_test = await self.test_load_resource_usage(
                chatbot_load_test,
                "chatbot_concurrent",
                180
            )
            suite_results["tests"]["chatbot_concurrent"] = chatbot_resource_test
            
        except ImportError as e:
            logger.warning(f"Could not import chatbot tests: {e}")
        
        # Test 4: Simulated mixed load
        logger.info("Testing mixed load scenario...")
        
        async def mixed_load_test():
            # Simulate mixed usage pattern
            results = {"concurrent_users": 8, "scenario": "mixed_load"}
            
            # Simulate some CPU and memory load
            tasks = []
            for i in range(8):
                task = asyncio.create_task(self._simulate_user_activity(i))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            return results
        
        mixed_load_test_result = await self.test_load_resource_usage(
            mixed_load_test,
            "mixed_load",
            240
        )
        suite_results["tests"]["mixed_load"] = mixed_load_test_result
        
        # Generate summary and recommendations
        suite_results["suite_end_time"] = datetime.now().isoformat()
        suite_results["summary"] = self._generate_resource_summary(suite_results["tests"])
        suite_results["recommendations"] = self._generate_resource_recommendations(suite_results["tests"])
        
        return suite_results
    
    async def _simulate_user_activity(self, user_id: int):
        """Simulate typical user activity for load testing"""
        try:
            # Simulate some work
            for _ in range(5):
                # Simulate CPU work
                start = time.time()
                while time.time() - start < 0.1:
                    _ = sum(i * i for i in range(1000))
                
                # Brief pause
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error in user simulation {user_id}: {e}")
    
    def _generate_resource_summary(self, tests: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of resource test results"""
        summary = {
            "total_tests": len(tests),
            "successful_tests": 0,
            "failed_tests": 0,
            "peak_cpu_usage": 0,
            "peak_memory_usage": 0,
            "efficiency_scores": [],
            "target_violations": 0,
            "performance_issues": []
        }
        
        for test_name, test_result in tests.items():
            if test_result.get("errors"):
                summary["failed_tests"] += 1
            else:
                summary["successful_tests"] += 1
            
            # Extract peak usage
            stats = test_result.get("statistics", {})
            system_stats = stats.get("system", {})
            
            cpu_max = system_stats.get("cpu", {}).get("max", 0)
            if cpu_max > summary["peak_cpu_usage"]:
                summary["peak_cpu_usage"] = cpu_max
            
            memory_max = system_stats.get("memory_percent", {}).get("max", 0)
            if memory_max > summary["peak_memory_usage"]:
                summary["peak_memory_usage"] = memory_max
            
            # Collect efficiency scores
            perf_analysis = test_result.get("performance_analysis", {})
            if perf_analysis.get("efficiency_score"):
                summary["efficiency_scores"].append(perf_analysis["efficiency_score"])
            
            # Count target violations
            target_violations = perf_analysis.get("target_violations", [])
            summary["target_violations"] += len(target_violations)
            
            if target_violations:
                summary["performance_issues"].extend(target_violations)
        
        if summary["efficiency_scores"]:
            summary["average_efficiency"] = sum(summary["efficiency_scores"]) / len(summary["efficiency_scores"])
        else:
            summary["average_efficiency"] = 0
        
        return summary
    
    def _generate_resource_recommendations(self, tests: Dict[str, Any]) -> List[str]:
        """Generate system resource optimization recommendations"""
        recommendations = []
        
        # Analyze resource patterns
        high_cpu_tests = []
        high_memory_tests = []
        inefficient_tests = []
        
        for test_name, test_result in tests.items():
            stats = test_result.get("statistics", {})
            system_stats = stats.get("system", {})
            
            cpu_avg = system_stats.get("cpu", {}).get("avg", 0)
            memory_avg = system_stats.get("memory_percent", {}).get("avg", 0)
            
            if cpu_avg > self.thresholds["cpu_warning"]:
                high_cpu_tests.append((test_name, cpu_avg))
            
            if memory_avg > self.thresholds["memory_warning"]:
                high_memory_tests.append((test_name, memory_avg))
            
            perf_analysis = test_result.get("performance_analysis", {})
            efficiency = perf_analysis.get("efficiency_score", 1.0)
            if efficiency < 0.7:
                inefficient_tests.append((test_name, efficiency))
        
        # Generate specific recommendations
        if high_cpu_tests:
            recommendations.append("🔥 **CPU Optimization Required:**")
            for test_name, cpu_usage in high_cpu_tests:
                recommendations.append(f"  - {test_name}: {cpu_usage:.1f}% avg CPU usage")
        
        if high_memory_tests:
            recommendations.append("🧠 **Memory Optimization Required:**")
            for test_name, memory_usage in high_memory_tests:
                recommendations.append(f"  - {test_name}: {memory_usage:.1f}% avg memory usage")
        
        if inefficient_tests:
            recommendations.append("⚡ **Efficiency Improvements Needed:**")
            for test_name, efficiency in inefficient_tests:
                recommendations.append(f"  - {test_name}: {efficiency:.2f} efficiency score")
        
        # General Orange Pi 5 specific recommendations
        recommendations.extend([
            "🍊 **Orange Pi 5 Optimization Recommendations:**",
            "  - Enable CPU governor 'performance' mode for consistent performance",
            "  - Use SSD storage for better I/O performance",
            "  - Implement memory pooling for frequent allocations",
            "  - Use process-based scaling instead of thread-based for CPU-intensive tasks",
            "  - Monitor thermal throttling during peak loads",
            "  - Implement graceful degradation when resources are constrained",
            "  - Use Redis for session storage to reduce memory usage",
            "  - Consider horizontal scaling with multiple Orange Pi 5 units for high load"
        ])
        
        return recommendations

# Standalone test runner
async def main():
    """Main function to run system resource tests"""
    print("💻 Starting Pi-LMS System Resource Tests")
    print("=" * 60)
    
    tester = SystemResourceTester()
    results = await tester.run_system_resource_test_suite()
    
    print("\n📊 Test Suite Results:")
    print(f"System: {results['system_info']['cpu_count']} CPU cores, {results['system_info']['memory_total']:.1f}GB RAM")
    print(f"Total Tests: {results['summary']['total_tests']}")
    print(f"Successful: {results['summary']['successful_tests']}")
    print(f"Failed: {results['summary']['failed_tests']}")
    print(f"Peak CPU Usage: {results['summary']['peak_cpu_usage']:.1f}%")
    print(f"Peak Memory Usage: {results['summary']['peak_memory_usage']:.1f}%")
    print(f"Average Efficiency: {results['summary']['average_efficiency']:.2f}")
    print(f"Target Violations: {results['summary']['target_violations']}")
    
    if results['summary']['performance_issues']:
        print("\n⚠️  Performance Issues:")
        for issue in results['summary']['performance_issues'][:5]:  # Show first 5
            print(f"  - {issue}")
    
    print("\n💡 Recommendations:")
    for rec in results['recommendations']:
        print(rec)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())