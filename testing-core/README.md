# Pi-LMS Performance Testing Suite

A comprehensive performance testing framework for the Pi-LMS (Learning Management System) designed specifically for Orange Pi 5 hardware constraints and educational use cases.

## Overview

This testing suite provides detailed performance analysis for:

- **🚀 Lesson Generator** - AI-powered PDF to lesson conversion with time tracking per phase
- **🤖 AI Chatbot** - Real-time chat responses with context loading and quality metrics
- **💻 System Resources** - CPU, memory, disk, and network usage monitoring
- **🔄 Integration Tests** - End-to-end workflows and concurrent user simulation

## Features

### ⏱️ Time Spent per Phase Analysis

- PDF upload and processing time
- AI content generation phases
- Narration and TTS conversion timing
- Video search and integration timing
- Database operations and API calls

### 📊 System Resource Consumption

- Real-time CPU and memory monitoring
- Disk I/O and network usage tracking
- Process-specific resource analysis
- Orange Pi 5 hardware optimization insights
- Concurrent user load testing (up to 50 users)

### 📈 Performance Metrics

- Response time distributions
- Throughput measurements
- Resource efficiency scores
- Quality assessments for AI responses
- Performance regression detection

### 📝 Automated Reporting

- Detailed markdown reports with charts
- JSON data export for analysis
- Performance threshold monitoring
- Optimization recommendations
- Historical trend analysis

## Installation

### Prerequisites

- Python 3.8 or higher
- Pi-LMS system running (pi-ai, pi-frontend, pi-lms-backend)
- Orange Pi 5 or compatible ARM64 system

### Setup

1. **Install dependencies:**

```bash
cd testing
pip install -r requirements.txt
```

2. **Configure environment:**

```bash
# Set service URLs (defaults shown)
export PI_AI_URL="http://localhost:8000"
export PI_FRONTEND_URL="http://localhost:8080"
export PI_BACKEND_URL="http://localhost:3000"
```

3. **Create test data directory:**

```bash
mkdir -p testing/test_files
mkdir -p testing/results
```

## Usage

### Quick Start - Run All Tests

```bash
# Run comprehensive test suite
python run_all_tests.py
```

This will execute all performance tests and generate a detailed markdown report in `testing/results/`.

### Individual Test Components

#### 🚀 Lesson Generator Performance

```bash
# Test lesson generation performance
python lesson_generator_tests.py
```

**Tests Include:**

- Basic lesson generation (single PDF)
- Large content processing
- Concurrent lesson generation (3-5 users)
- Performance under load testing
- PDF processing phase timing
- AI content generation metrics
- Media upload and processing

#### 🤖 AI Chatbot Performance

```bash
# Test chatbot performance
python chatbot_performance_tests.py
```

**Tests Include:**

- Context loading performance
- Single message response timing
- WebSocket communication testing
- Conversation flow analysis
- Concurrent chat sessions (3-8 users)
- Response quality scoring
- Memory usage per session

#### 💻 System Resource Monitoring

```bash
# Test system resource usage
python system_resource_tests.py
```

**Tests Include:**

- Baseline resource consumption
- Load testing with resource monitoring
- Process-specific analysis (pi-ai, pi-frontend, pi-backend)
- Orange Pi 5 capacity testing
- Memory leak detection
- CPU and thermal monitoring

### Custom Testing

#### Monitor Specific Operations

```python
from performance_monitor import PerformanceMonitor, monitor_phase

# Create monitor
monitor = PerformanceMonitor()
session_id = monitor.start_session("custom_test")

# Monitor a specific phase
async with monitor_phase(monitor, "custom_operation"):
    # Your code here
    await some_operation()

# End session and get results
results = monitor.end_session()
```

#### Resource Monitoring

```python
from system_resource_tests import SystemResourceTester

tester = SystemResourceTester()

# Start continuous monitoring
tester.start_continuous_monitoring()

# Run your operations
await your_operations()

# Stop and analyze
tester.stop_continuous_monitoring()
```

## Test Configuration

### Performance Thresholds

Edit thresholds in the respective test files:

```python
# Lesson Generator Thresholds (seconds)
thresholds = {
    "pdf_upload": 5.0,
    "pdf_processing": 60.0,
    "content_generation": 30.0,
    "narration_generation": 20.0,
    "total_generation": 120.0
}

# Chatbot Thresholds (seconds)
thresholds = {
    "context_loading": 2.0,
    "chat_response": 5.0,
    "streaming_first_token": 1.0,
}

# Resource Thresholds (Orange Pi 5)
thresholds = {
    "cpu_warning": 70.0,      # % CPU usage
    "memory_warning": 75.0,   # % Memory usage
    "load_warning": 4.0,      # Load average for 4-core system
}
```

### Test Scenarios

Customize test scenarios by modifying:

```python
# Concurrent user counts
concurrent_users = [1, 3, 5, 8, 10]

# Test messages for chatbot
test_messages = [
    "What is this lesson about?",
    "Can you explain this concept?",
    "Create a practice question",
    # Add more scenarios
]

# PDF content variations
test_content_sizes = ["small", "medium", "large", "xl"]
```

## Output and Reports

### Markdown Reports

Generated reports include:

```
performance_test_report_YYYYMMDD_HHMMSS.md
├── Executive Summary
├── Key Performance Metrics
├── Critical Issues
├── Detailed Test Results
│   ├── Lesson Generator Performance
│   ├── AI Chatbot Performance
│   ├── System Resource Usage
│   └── Integration Test Results
├── Optimization Recommendations
└── Technical Details
```

### JSON Data Export

Raw data is saved as:

```json
{
  "test_suite": "Pi-LMS Comprehensive Performance Testing",
  "start_time": "2025-01-15T10:30:00",
  "tests": {
    "lesson_generator": {
      /* detailed results */
    },
    "ai_chatbot": {
      /* detailed results */
    },
    "system_resources": {
      /* detailed results */
    },
    "integration": {
      /* detailed results */
    }
  },
  "summary": {
    /* aggregated metrics */
  },
  "recommendations": [
    /* optimization suggestions */
  ]
}
```

## Performance Benchmarks

### Orange Pi 5 Targets

| Component        | Metric           | Target   | Warning  | Critical |
| ---------------- | ---------------- | -------- | -------- | -------- |
| Lesson Generator | Total Time       | < 120s   | > 180s   | > 300s   |
| Lesson Generator | PDF Processing   | < 60s    | > 90s    | > 120s   |
| AI Chatbot       | Response Time    | < 5s     | > 8s     | > 15s    |
| AI Chatbot       | Context Loading  | < 2s     | > 5s     | > 10s    |
| System           | CPU Usage        | < 70%    | > 85%    | > 95%    |
| System           | Memory Usage     | < 75%    | > 90%    | > 98%    |
| System           | Concurrent Users | 50 users | 30 users | 20 users |

### Expected Performance

**Lesson Generation:**

- Basic lesson (5-page PDF): 45-90 seconds
- Complex lesson (20-page PDF): 90-180 seconds
- Concurrent generation (3 users): 60-120 seconds per lesson

**AI Chatbot:**

- Context loading: 0.5-2 seconds
- Simple response: 2-5 seconds
- Complex response: 5-10 seconds
- Concurrent sessions (5 users): 3-8 seconds average

**System Resources:**

- Idle state: 5-15% CPU, 30-50% memory
- Single user load: 20-40% CPU, 50-70% memory
- Peak load (5 users): 60-80% CPU, 70-85% memory

## Optimization Recommendations

The testing suite automatically generates optimization recommendations based on results:

### 🚀 Performance Optimizations

- Implement Redis caching for lesson content
- Use background task queues for long operations
- Optimize database connection pooling
- Enable CPU performance governor

### 🧠 Memory Optimizations

- Implement context window pruning for chatbot
- Use memory-mapped files for large PDFs
- Add garbage collection triggers
- Optimize image and media handling

### ⚡ Scalability Improvements

- Implement horizontal scaling with load balancer
- Use CDN for static assets
- Add graceful degradation for resource limits
- Consider process-based scaling

## Troubleshooting

### Common Issues

**1. High Memory Usage**

```bash
# Check for memory leaks
python -c "
from system_resource_tests import SystemResourceTester
tester = SystemResourceTester()
tester.start_continuous_monitoring()
# Let it run for a few minutes
"
```

**2. Slow Response Times**

```bash
# Profile specific operations
python -c "
from performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor()
# Add detailed phase monitoring
"
```

**3. Connection Errors**

```bash
# Verify services are running
curl http://localhost:8000/api/chat/health
curl http://localhost:8080/api/me
curl http://localhost:3000/api/health
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run tests with debug output
python run_all_tests.py
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Performance Tests
on:
  schedule:
    - cron: "0 2 * * *" # Daily at 2 AM

jobs:
  performance:
    runs-on: [self-hosted, orange-pi-5]
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          cd testing
          pip install -r requirements.txt
      - name: Run performance tests
        run: |
          cd testing
          python run_all_tests.py
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: testing/results/
```

## Contributing

### Adding New Tests

1. **Create test module:**

```python
# testing/my_component_tests.py
from performance_monitor import PerformanceMonitor, monitor_phase

class MyComponentTester:
    def __init__(self, performance_monitor=None):
        self.monitor = performance_monitor or PerformanceMonitor()

    async def test_my_feature(self):
        session_id = self.monitor.start_session("my_test")

        async with monitor_phase(self.monitor, "my_phase"):
            # Your test code here
            pass

        return self.monitor.end_session()
```

2. **Add to main runner:**

```python
# In run_all_tests.py
from my_component_tests import MyComponentTester

# Add to ComprehensiveTestRunner
self.my_tester = MyComponentTester(performance_monitor=self.monitor)
```

### Test Best Practices

- Use descriptive phase names
- Add custom metrics for important values
- Check against realistic thresholds
- Include both success and failure scenarios
- Clean up resources after tests
- Document expected behaviors

## Architecture

### Core Components

```
testing/
├── performance_monitor.py     # Core monitoring system
├── lesson_generator_tests.py  # Lesson generation tests
├── chatbot_performance_tests.py # AI chatbot tests
├── system_resource_tests.py   # Resource monitoring tests
├── run_all_tests.py          # Comprehensive test runner
├── requirements.txt          # Python dependencies
├── README.md                # This documentation
└── results/                 # Generated reports
    ├── performance_test_results_*.json
    └── performance_test_report_*.md
```

### Data Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Test Runner   │───▶│ Performance      │───▶│ Results &       │
│                 │    │ Monitor          │    │ Reports         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Component Tests │    │ Resource         │    │ Markdown +      │
│ - Lesson Gen    │    │ Tracking         │    │ JSON Reports    │
│ - Chatbot       │    │ - CPU/Memory     │    │ - Metrics       │
│ - Integration   │    │ - Disk/Network   │    │ - Recommendations│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Support

For issues, questions, or contributions:

1. Check existing test results in `testing/results/`
2. Review performance thresholds and benchmarks
3. Enable debug logging for detailed information
4. Create GitHub issue with test results and system info

## License

This testing suite is part of the Pi-LMS project and follows the same license terms.

---

**Built for Orange Pi 5** 🍊 **Optimized for Education** 📚 **Performance First** ⚡
