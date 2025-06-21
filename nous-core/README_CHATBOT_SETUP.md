# AI Chatbot Setup Guide for PI-LMS

This guide covers the setup and installation of the AI Chatbot functionality for the PI-LMS system, including local LLM integration with Ollama.

## 🎯 Overview

The AI Chatbot system consists of:

- **LLM Service**: Interface with Ollama for local AI inference
- **Chatbot Service**: Chat logic, context management, and lesson integration
- **API Endpoints**: RESTful and WebSocket APIs for chat functionality
- **Configuration**: Prompts, environment variables, and system settings

## 📋 Prerequisites

### System Requirements

- **Memory**: Minimum 8GB RAM (4GB for model + 4GB for system)
- **Storage**: 5GB free space for model and dependencies
- **CPU**: Multi-core processor (ARM64 or x86_64)
- **Network**: Internet connection for model download

### Software Requirements

- Python 3.8+ with existing PI-LMS dependencies
- Ollama (will be installed automatically)
- curl (for API testing)

## 🚀 Installation Instructions

### Option 1: Linux/Orange Pi 5 Installation

1. **Run the automated setup script:**

   ```bash
   cd pi-ai/scripts
   chmod +x setup_ollama.sh
   ./setup_ollama.sh
   ```

2. **Manual installation (if script fails):**

   ```bash
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh

   # Start Ollama service
   sudo systemctl enable ollama
   sudo systemctl start ollama

   # Download the model
   ollama pull llama3.2:3b-instruct-q4_K_M

   # Test installation
   ollama list
   ```

### Option 2: Windows Development Installation

1. **Run the Windows setup script:**

   ```cmd
   cd pi-ai\scripts
   setup_ollama_windows.bat
   ```

2. **Manual installation:**
   - Download Ollama from https://ollama.ai/download/windows
   - Install and restart your system
   - Open Command Prompt and run:
     ```cmd
     ollama pull llama3.2:3b-instruct-q4_K_M
     ```

### Option 3: Development Mode (Mock LLM)

For development without installing Ollama:

1. **Update `.env` file:**

   ```env
   ENABLE_LOCAL_LLM=false
   ```

2. **Start the API server:**
   ```bash
   cd pi-ai
   python api.py
   ```

The system will use mock responses for development and testing.

## ⚙️ Configuration

### Environment Variables

Update your `pi-ai/.env` file with these settings:

```env
# LLM Configuration
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=llama3.2:3b-instruct-q4_K_M
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.7
ENABLE_LOCAL_LLM=true

# Payload CMS Configuration
PAYLOAD_BASE_URL=http://localhost:3000
PAYLOAD_CMS_TOKEN=your_payload_cms_token_here
```

### System Prompts

The chatbot behavior is configured in `config/chatbot_prompts.json`. You can customize:

- Default teaching assistant personality
- Quiz mode prompts
- Explanation templates
- Response suggestions

## 🧪 Testing the Installation

### 1. Test Ollama Service

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Test model generation
echo "Hello, can you help me study?" | ollama run llama3.2:3b-instruct-q4_K_M
```

### 2. Test PI-LMS API Integration

```bash
# Start the PI-LMS AI service
cd pi-ai
python api.py

# In another terminal, test chat health
curl http://localhost:8000/api/chat/health
```

### 3. Test Chat Functionality

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the main topic of this lesson?",
    "lesson_id": 1,
    "mode": "default"
  }'
```

## 📊 Performance Monitoring

### System Resource Monitoring

1. **Use the monitoring script:**

   ```bash
   # Linux/Orange Pi 5
   ./monitor_ollama.sh

   # Windows
   monitor_ollama.bat
   ```

2. **Manual monitoring:**

   ```bash
   # Check Ollama processes
   ollama ps

   # Monitor system resources
   htop  # Linux
   # or use Task Manager on Windows

   # Check model memory usage
   nvidia-smi  # If using GPU
   ```

### Performance Benchmarks

Expected performance on Orange Pi 5:

- **Model Loading**: 30-60 seconds
- **Response Generation**: 8-15 tokens/second
- **Memory Usage**: 3-4GB for model
- **Cold Start**: 2-3 seconds
- **Warm Response**: 0.5-1 second

## 🔧 Troubleshooting

### Common Issues

1. **Ollama won't start:**

   ```bash
   # Check system resources
   free -h

   # Restart Ollama service
   sudo systemctl restart ollama

   # Check logs
   journalctl -u ollama -f
   ```

2. **Model download fails:**

   ```bash
   # Check internet connection
   ping ollama.ai

   # Try manual download
   ollama pull llama3.2:3b-instruct-q4_K_M --verbose
   ```

3. **High memory usage:**

   ```bash
   # Limit Ollama memory (add to ~/.bashrc)
   export OLLAMA_MAX_LOADED_MODELS=1
   export OLLAMA_NUM_PARALLEL=1

   # Use smaller model if needed
   ollama pull llama3.2:1b-instruct-q4_K_M
   ```

4. **API connection issues:**

   ```bash
   # Check if API is running
   curl http://localhost:8000/api/chat/health

   # Check logs
   cd pi-ai && python api.py  # Check console output
   ```

### Error Messages

| Error                          | Solution                                                  |
| ------------------------------ | --------------------------------------------------------- |
| "Ollama service not available" | Ensure Ollama is running: `ollama serve`                  |
| "Model not found"              | Download model: `ollama pull llama3.2:3b-instruct-q4_K_M` |
| "Connection refused"           | Check OLLAMA_HOST setting in .env                         |
| "Out of memory"                | Reduce model size or increase system RAM                  |

## 🔒 Security Considerations

### Data Privacy

- Chat conversations are not persistently stored
- Lesson content is anonymized for LLM processing
- No personal data is sent to external services

### Resource Protection

- Rate limiting is implemented for chat requests
- Memory monitoring prevents system overload
- Automatic session cleanup prevents resource leaks

### Network Security

- Ollama runs locally (no external API calls)
- WebSocket connections require valid session IDs
- API endpoints respect existing authentication

## 📈 Scaling and Optimization

### For Production Deployment

1. **Resource Allocation:**

   ```bash
   # Set resource limits (systemd)
   sudo systemctl edit ollama

   # Add:
   [Service]
   LimitMEMLOCK=6G
   LimitNOFILE=65536
   ```

2. **Performance Tuning:**

   ```env
   # Optimize for your hardware
   OLLAMA_NUM_PARALLEL=2        # Increase for more CPU cores
   OLLAMA_MAX_LOADED_MODELS=1   # Keep low for Orange Pi 5
   LLM_MAX_TOKENS=2000         # Reduce for faster responses
   ```

3. **Load Balancing:**
   - Consider multiple Ollama instances for high load
   - Implement request queuing for concurrent users
   - Monitor response times and adjust accordingly

## 🔄 Alternative Models

If performance issues occur, try these alternatives:

| Model                         | Size  | Speed  | Quality | Use Case          |
| ----------------------------- | ----- | ------ | ------- | ----------------- |
| `llama3.2:1b-instruct-q4_K_M` | 1.2GB | Fast   | Good    | Limited resources |
| `llama3.2:3b-instruct-q4_K_M` | 2.2GB | Medium | Better  | Recommended       |
| `mistral:7b-instruct-q4_K_M`  | 4.1GB | Slow   | Best    | High-end hardware |

To switch models:

```bash
# Download new model
ollama pull llama3.2:1b-instruct-q4_K_M

# Update .env file
LLM_MODEL=llama3.2:1b-instruct-q4_K_M

# Restart API service
```

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review API logs: `cd pi-ai && python api.py`
3. Test individual components separately
4. Monitor system resources during operation

## 🎉 Next Steps

After successful setup:

1. **Proceed to Phase 2**: Frontend chat widget implementation
2. **Test with actual lesson content**: Verify context retrieval
3. **Performance optimization**: Adjust settings based on usage
4. **User testing**: Gather feedback on chat responses

The AI Chatbot backend is now ready for integration with the frontend interface!
