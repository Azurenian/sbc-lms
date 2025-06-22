"""
Pi-LMS Testing Web Server
Provides web interface for running performance tests and viewing results
Optimized for Orange Pi 5 Capstone analysis
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Import testing modules
from run_all_tests import ComprehensiveTestRunner
from performance_monitor import PerformanceMonitor

app = FastAPI(
    title="Pi-LMS Performance Testing Dashboard",
    description="Comprehensive performance testing for Orange Pi 5 deployment",
    version="1.0.0"
)

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
results_dir = Path("results")
results_dir.mkdir(exist_ok=True)

# Mount results as static files for easy download
app.mount("/results", StaticFiles(directory="results"), name="results")

# Global test runner and status tracking
test_runner: Optional[ComprehensiveTestRunner] = None
current_test_status = {
    "running": False,
    "progress": 0,
    "current_stage": "",
    "start_time": None,
    "estimated_completion": None
}

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main testing dashboard"""
    
    # Get recent test results
    recent_results = get_recent_test_results(limit=5)
    
    # Get system info
    system_info = await get_system_info()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_status": current_test_status,
        "recent_results": recent_results,
        "system_info": system_info
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/tests/run-comprehensive")
async def run_comprehensive_tests(background_tasks: BackgroundTasks):
    """Start comprehensive performance test suite"""
    
    if current_test_status["running"]:
        raise HTTPException(status_code=409, detail="Test already running")
    
    # Start background test
    background_tasks.add_task(execute_comprehensive_tests)
    
    current_test_status.update({
        "running": True,
        "progress": 0,
        "current_stage": "Initializing",
        "start_time": datetime.now().isoformat(),
        "estimated_completion": None
    })
    
    return {"message": "Comprehensive test suite started", "status": current_test_status}

@app.post("/api/tests/run-quick")
async def run_quick_tests(background_tasks: BackgroundTasks):
    """Start quick performance validation"""
    
    if current_test_status["running"]:
        raise HTTPException(status_code=409, detail="Test already running")
    
    background_tasks.add_task(execute_quick_tests)
    
    current_test_status.update({
        "running": True,
        "progress": 0,
        "current_stage": "Quick validation",
        "start_time": datetime.now().isoformat(),
        "estimated_completion": None
    })
    
    return {"message": "Quick test suite started", "status": current_test_status}

@app.get("/api/tests/status")
async def get_test_status():
    """Get current test execution status"""
    return current_test_status

@app.get("/api/results")
async def get_test_results(limit: int = 10):
    """Get list of test results"""
    results = get_recent_test_results(limit)
    return {"results": results}

@app.get("/api/results/{result_id}")
async def get_test_result(result_id: str):
    """Get specific test result"""
    result_file = results_dir / f"performance_test_results_{result_id}.json"
    
    if not result_file.exists():
        raise HTTPException(status_code=404, detail="Test result not found")
    
    with open(result_file, 'r') as f:
        result_data = json.load(f)
    
    return result_data

@app.get("/api/results/{result_id}/download")
async def download_test_result(result_id: str, format: str = "json"):
    """Download test result in specified format"""
    
    if format == "json":
        result_file = results_dir / f"performance_test_results_{result_id}.json"
    elif format == "markdown":
        result_file = results_dir / f"performance_test_report_{result_id}.md"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
    
    if not result_file.exists():
        raise HTTPException(status_code=404, detail="Test result not found")
    
    return FileResponse(
        path=result_file,
        filename=result_file.name,
        media_type='application/octet-stream'
    )

@app.get("/api/system/info")
async def get_system_info():
    """Get Orange Pi 5 system information"""
    import psutil
    import platform
    
    # Get CPU info
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    
    # Get memory info
    memory = psutil.virtual_memory()
    
    # Get disk info
    disk = psutil.disk_usage('/')
    
    return {
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        },
        "cpu": {
            "physical_cores": psutil.cpu_count(logical=False),
            "total_cores": cpu_count,
            "max_frequency": cpu_freq.max if cpu_freq else None,
            "current_frequency": cpu_freq.current if cpu_freq else None
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "total_gb": round(memory.total / (1024**3), 2)
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": (disk.used / disk.total) * 100,
            "total_gb": round(disk.total / (1024**3), 2)
        }
    }

@app.get("/api/services/health")
async def check_services_health():
    """Check health of all Pi-LMS services"""
    import httpx
    
    services = {
        "frontend": "http://frontend:8080",
        "backend": "http://backend:3000", 
        "ai_services": "http://ai-services:8000",
        "ollama": "http://ollama:11434"
    }
    
    health_status = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in services.items():
            try:
                if service_name == "frontend":
                    response = await client.get(f"{service_url}/health")
                elif service_name == "backend":
                    response = await client.get(f"{service_url}/api/health")
                elif service_name == "ai_services":
                    response = await client.get(f"{service_url}/health")
                elif service_name == "ollama":
                    response = await client.get(f"{service_url}/api/version")
                
                health_status[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds(),
                    "status_code": response.status_code
                }
            except Exception as e:
                health_status[service_name] = {
                    "status": "unreachable",
                    "error": str(e),
                    "response_time": None,
                    "status_code": None
                }
    
    return health_status

async def execute_comprehensive_tests():
    """Execute comprehensive test suite in background"""
    global test_runner, current_test_status
    
    try:
        test_runner = ComprehensiveTestRunner(auth_token=os.getenv("TEST_AUTH_TOKEN", "placeholder_token"), output_dir="results")
        
        # Update progress at different stages
        current_test_status.update({
            "progress": 10,
            "current_stage": "Initializing test environment"
        })
        
        # Run comprehensive tests
        current_test_status.update({
            "progress": 20,
            "current_stage": "Running lesson generator tests"
        })
        
        results = await test_runner.run_all_tests(
            include_lesson_tests=True,
            include_chatbot_tests=True,
            include_resource_tests=True,
            include_integration_tests=True
        )
        
        current_test_status.update({
            "progress": 100,
            "current_stage": "Tests completed",
            "running": False,
            "completion_time": datetime.now().isoformat(),
            "last_result_id": extract_result_id(results)
        })
        
    except Exception as e:
        current_test_status.update({
            "running": False,
            "progress": 0,
            "current_stage": "Error occurred",
            "error": str(e),
            "completion_time": datetime.now().isoformat()
        })

async def execute_quick_tests():
    """Execute quick validation tests"""
    global current_test_status
    
    try:
        test_runner = ComprehensiveTestRunner(auth_token=os.getenv("TEST_AUTH_TOKEN", "placeholder_token"), output_dir="results")
        
        current_test_status.update({
            "progress": 25,
            "current_stage": "Quick system validation"
        })
        
        # Run limited test suite for quick results
        results = await test_runner.run_all_tests(
            include_lesson_tests=True,
            include_chatbot_tests=True,
            include_resource_tests=False,  # Skip resource tests for speed
            include_integration_tests=False  # Skip integration for speed
        )
        
        current_test_status.update({
            "progress": 100,
            "current_stage": "Quick tests completed",
            "running": False,
            "completion_time": datetime.now().isoformat(),
            "last_result_id": extract_result_id(results)
        })
        
    except Exception as e:
        current_test_status.update({
            "running": False,
            "progress": 0,
            "current_stage": "Error occurred",
            "error": str(e),
            "completion_time": datetime.now().isoformat()
        })

def get_recent_test_results(limit: int = 10) -> List[Dict]:
    """Get recent test results"""
    results = []
    
    # Get all JSON result files
    json_files = list(results_dir.glob("performance_test_results_*.json"))
    json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    for json_file in json_files[:limit]:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Extract summary info
            result_id = json_file.stem.replace("performance_test_results_", "")
            summary = data.get("summary", {})
            
            results.append({
                "id": result_id,
                "timestamp": data.get("start_time", ""),
                "duration": data.get("total_duration", 0),
                "performance_score": summary.get("overall_performance_score", 0),
                "components_tested": len(data.get("tests", {})),
                "issues": summary.get("total_errors", 0) + summary.get("total_warnings", 0),
                "file_size": json_file.stat().st_size
            })
        except Exception as e:
            print(f"Error reading result file {json_file}: {e}")
    
    return results

def extract_result_id(results: Dict) -> str:
    """Extract result ID from test results"""
    start_time = results.get("start_time", "")
    if start_time:
        # Convert ISO timestamp to result ID format
        try:
            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            return dt.strftime("%Y%m%d_%H%M%S")
        except:
            pass
    
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# Create basic HTML template directory and files
def create_dashboard_template():
    """Create basic dashboard template"""
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    dashboard_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pi-LMS Performance Testing Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2196F3; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status { display: flex; align-items: center; gap: 10px; }
        .status.running { color: #FF9800; }
        .status.complete { color: #4CAF50; }
        .status.error { color: #F44336; }
        .button { background: #2196F3; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        .button:hover { background: #1976D2; }
        .button:disabled { background: #ccc; cursor: not-allowed; }
        .results-table { width: 100%; border-collapse: collapse; }
        .results-table th, .results-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .results-table th { background: #f1f1f1; }
        .system-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .metric { text-align: center; }
        .metric h3 { margin: 5px 0; font-size: 2em; }
        .progress-bar { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: #4CAF50; transition: width 0.3s; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍊 Pi-LMS Performance Testing Dashboard</h1>
            <p>Orange Pi 5 Performance Analysis for Educational Deployment</p>
        </div>
        
        <div class="card">
            <h2>Quick Actions</h2>
            <button class="button" onclick="startComprehensiveTest()" id="comprehensive-btn">🚀 Run Comprehensive Test Suite</button>
            <button class="button" onclick="startQuickTest()" id="quick-btn">⚡ Run Quick Validation</button>
            <button class="button" onclick="refreshStatus()">🔄 Refresh Status</button>
        </div>
        
        <div class="card">
            <h2>Current Test Status</h2>
            <div id="test-status">
                <div class="status" id="status-indicator">
                    <span id="status-text">Ready to run tests</span>
                </div>
                <div id="progress-container" style="margin-top: 10px; display: none;">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
                    </div>
                    <p id="progress-text">0% - Initializing</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>System Information</h2>
            <div class="system-info" id="system-info">
                <div class="metric">
                    <h3>--</h3>
                    <p>CPU Cores</p>
                </div>
                <div class="metric">
                    <h3>--</h3>
                    <p>Memory (GB)</p>
                </div>
                <div class="metric">
                    <h3>--</h3>
                    <p>Storage (GB)</p>
                </div>
                <div class="metric">
                    <h3>--</h3>
                    <p>Platform</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Recent Test Results</h2>
            <table class="results-table" id="results-table">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Duration</th>
                        <th>Performance Score</th>
                        <th>Components</th>
                        <th>Issues</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="results-body">
                    <tr><td colspan="6">Loading results...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        let statusCheckInterval;
        
        async function startComprehensiveTest() {
            const btn = document.getElementById('comprehensive-btn');
            btn.disabled = true;
            
            try {
                const response = await fetch('/api/tests/run-comprehensive', { method: 'POST' });
                const result = await response.json();
                
                if (response.ok) {
                    startStatusPolling();
                } else {
                    alert('Error: ' + result.detail);
                    btn.disabled = false;
                }
            } catch (error) {
                alert('Error starting test: ' + error.message);
                btn.disabled = false;
            }
        }
        
        async function startQuickTest() {
            const btn = document.getElementById('quick-btn');
            btn.disabled = true;
            
            try {
                const response = await fetch('/api/tests/run-quick', { method: 'POST' });
                const result = await response.json();
                
                if (response.ok) {
                    startStatusPolling();
                } else {
                    alert('Error: ' + result.detail);
                    btn.disabled = false;
                }
            } catch (error) {
                alert('Error starting test: ' + error.message);
                btn.disabled = false;
            }
        }
        
        function startStatusPolling() {
            statusCheckInterval = setInterval(refreshStatus, 2000);
            document.getElementById('progress-container').style.display = 'block';
        }
        
        async function refreshStatus() {
            try {
                const response = await fetch('/api/tests/status');
                const status = await response.json();
                
                updateStatusDisplay(status);
                
                if (!status.running) {
                    clearInterval(statusCheckInterval);
                    document.getElementById('comprehensive-btn').disabled = false;
                    document.getElementById('quick-btn').disabled = false;
                    loadResults();
                }
            } catch (error) {
                console.error('Error fetching status:', error);
            }
        }
        
        function updateStatusDisplay(status) {
            const indicator = document.getElementById('status-indicator');
            const statusText = document.getElementById('status-text');
            const progressFill = document.getElementById('progress-fill');
            const progressText = document.getElementById('progress-text');
            
            if (status.running) {
                indicator.className = 'status running';
                statusText.textContent = 'Test in progress: ' + status.current_stage;
                progressFill.style.width = status.progress + '%';
                progressText.textContent = status.progress + '% - ' + status.current_stage;
            } else if (status.error) {
                indicator.className = 'status error';
                statusText.textContent = 'Error: ' + status.error;
                document.getElementById('progress-container').style.display = 'none';
            } else {
                indicator.className = 'status complete';
                statusText.textContent = 'Ready to run tests';
                document.getElementById('progress-container').style.display = 'none';
            }
        }
        
        async function loadSystemInfo() {
            try {
                const response = await fetch('/api/system/info');
                const info = await response.json();
                
                const metrics = document.querySelectorAll('.system-info .metric h3');
                metrics[0].textContent = info.cpu.total_cores;
                metrics[1].textContent = info.memory.total_gb;
                metrics[2].textContent = info.disk.total_gb;
                metrics[3].textContent = info.platform.machine;
            } catch (error) {
                console.error('Error loading system info:', error);
            }
        }
        
        async function loadResults() {
            try {
                const response = await fetch('/api/results');
                const data = await response.json();
                
                const tbody = document.getElementById('results-body');
                tbody.innerHTML = '';
                
                if (data.results.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6">No test results available</td></tr>';
                    return;
                }
                
                data.results.forEach(result => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${new Date(result.timestamp).toLocaleString()}</td>
                        <td>${Math.round(result.duration)}s</td>
                        <td>${(result.performance_score * 100).toFixed(1)}%</td>
                        <td>${result.components_tested}</td>
                        <td>${result.issues}</td>
                        <td>
                            <a href="/results/performance_test_results_${result.id}.json" download>JSON</a> |
                            <a href="/results/performance_test_report_${result.id}.md" download>Report</a>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            } catch (error) {
                console.error('Error loading results:', error);
            }
        }
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            loadSystemInfo();
            loadResults();
            refreshStatus();
        });
    </script>
</body>
</html>"""
    
    with open(templates_dir / "dashboard.html", "w") as f:
        f.write(dashboard_html)

# Create template on startup
create_dashboard_template()

if __name__ == "__main__":
    print("🍊 Starting Pi-LMS Performance Testing Dashboard")
    print("📊 Dashboard will be available at: http://localhost:9000")
    print("🔧 Orange Pi 5 optimized performance analysis")
    
    uvicorn.run(
        "testing_web_server:app",
        host="0.0.0.0",
        port=9000,
        log_level="info",
        reload=False
    )