#!/bin/bash

# Ollama Setup Script for PI-LMS Chatbot
# This script installs Ollama and downloads the required model

echo "🚀 Setting up Ollama for PI-LMS Chatbot..."

# Check if script is run with sudo for system-wide installation
if [ "$EUID" -eq 0 ]; then
    echo "ℹ️  Running as root - installing system-wide"
    SYSTEM_INSTALL=true
else
    echo "ℹ️  Running as user - installing for current user"
    SYSTEM_INSTALL=false
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check system architecture
check_architecture() {
    ARCH=$(uname -m)
    echo "🔍 Detected architecture: $ARCH"
    
    case $ARCH in
        x86_64)
            echo "✅ x86_64 architecture supported"
            ;;
        aarch64|arm64)
            echo "✅ ARM64 architecture supported (Orange Pi 5)"
            ;;
        armv7l)
            echo "❌ ARM v7 not officially supported by Ollama"
            echo "   Consider using a lighter alternative or running on a different machine"
            exit 1
            ;;
        *)
            echo "❌ Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
}

# Function to install Ollama
install_ollama() {
    echo "📦 Installing Ollama..."
    
    if command_exists ollama; then
        echo "✅ Ollama is already installed"
        ollama --version
        return 0
    fi
    
    # Download and install Ollama
    echo "⬇️  Downloading Ollama installer..."
    if curl -fsSL https://ollama.ai/install.sh | sh; then
        echo "✅ Ollama installed successfully"
    else
        echo "❌ Failed to install Ollama"
        exit 1
    fi
}

# Function to start Ollama service
start_ollama_service() {
    echo "🔧 Starting Ollama service..."
    
    if $SYSTEM_INSTALL; then
        # System-wide installation
        if command_exists systemctl; then
            sudo systemctl enable ollama
            sudo systemctl start ollama
            echo "✅ Ollama service started (systemd)"
        else
            echo "⚠️  systemctl not available, starting manually"
            ollama serve &
            sleep 5
        fi
    else
        # User installation
        echo "🔄 Starting Ollama server in background..."
        ollama serve > /dev/null 2>&1 &
        OLLAMA_PID=$!
        sleep 5
        
        # Check if Ollama is running
        if kill -0 $OLLAMA_PID 2>/dev/null; then
            echo "✅ Ollama server started (PID: $OLLAMA_PID)"
        else
            echo "❌ Failed to start Ollama server"
            exit 1
        fi
    fi
}

# Function to download the model
download_model() {
    local model_name="llama3.2:3b-instruct-q4_K_M"
    echo "📥 Downloading model: $model_name"
    echo "   This may take several minutes depending on your internet connection..."
    
    if ollama pull $model_name; then
        echo "✅ Model downloaded successfully: $model_name"
    else
        echo "❌ Failed to download model: $model_name"
        echo "   You can try downloading it manually later with:"
        echo "   ollama pull $model_name"
        return 1
    fi
}

# Function to test the installation
test_installation() {
    echo "🧪 Testing Ollama installation..."
    
    # Wait for Ollama to be ready
    echo "⏳ Waiting for Ollama to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "✅ Ollama API is responding"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            echo "❌ Timeout waiting for Ollama to start"
            return 1
        fi
    done
    
    # Test model availability
    echo "🔍 Checking available models..."
    if ollama list | grep -q "llama3.2:3b-instruct-q4_K_M"; then
        echo "✅ Model is available and ready"
        
        # Test generation
        echo "🎯 Testing model generation..."
        test_response=$(echo "Hello, test message" | ollama run llama3.2:3b-instruct-q4_K_M --format json 2>/dev/null || echo "")
        if [ -n "$test_response" ]; then
            echo "✅ Model generation test successful"
        else
            echo "⚠️  Model generation test failed, but model is installed"
        fi
    else
        echo "❌ Model not found in Ollama"
        return 1
    fi
}

# Function to configure Ollama for optimal performance
configure_ollama() {
    echo "⚙️  Configuring Ollama for optimal performance..."
    
    if $SYSTEM_INSTALL && command_exists systemctl; then
        echo "📝 Creating systemd service override..."
        sudo mkdir -p /etc/systemd/system/ollama.service.d/
        
        cat << EOF | sudo tee /etc/systemd/system/ollama.service.d/override.conf
[Service]
# Increase memory limit for model loading
LimitMEMLOCK=8G
LimitNOFILE=65536

# Environment variables for optimization
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl restart ollama
        echo "✅ Systemd service configured"
    else
        echo "ℹ️  Manual configuration needed for user installation"
        echo "   Set these environment variables in your shell:"
        echo "   export OLLAMA_HOST=0.0.0.0:11434"
        echo "   export OLLAMA_NUM_PARALLEL=1"
        echo "   export OLLAMA_MAX_LOADED_MODELS=1"
    fi
}

# Function to create monitoring script
create_monitoring_script() {
    echo "📊 Creating monitoring script..."
    
    cat << 'EOF' > monitor_ollama.sh
#!/bin/bash
# Ollama Performance Monitor for PI-LMS

echo "🔍 Ollama Performance Monitor"
echo "================================"

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # CPU Usage
    CPU_USAGE=$(grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage}')
    
    # Memory Usage
    MEM_INFO=$(free | grep Mem)
    MEM_TOTAL=$(echo $MEM_INFO | awk '{print $2}')
    MEM_USED=$(echo $MEM_INFO | awk '{print $3}')
    MEM_PERCENT=$(awk "BEGIN {printf \"%.1f\", $MEM_USED/$MEM_TOTAL*100}")
    
    # Temperature (if available)
    if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
        TEMP=$(awk '{print $1/1000}' /sys/class/thermal/thermal_zone0/temp)
        TEMP_STR="TEMP: ${TEMP}°C"
    else
        TEMP_STR="TEMP: N/A"
    fi
    
    # Ollama process check
    if pgrep -f "ollama" > /dev/null; then
        OLLAMA_STATUS="RUNNING"
    else
        OLLAMA_STATUS="STOPPED"
    fi
    
    printf "[$TIMESTAMP] CPU: %.1f%% | MEM: %.1f%% | %s | Ollama: %s\n" \
           "$CPU_USAGE" "$MEM_PERCENT" "$TEMP_STR" "$OLLAMA_STATUS"
    
    sleep 10
done
EOF
    
    chmod +x monitor_ollama.sh
    echo "✅ Monitoring script created: monitor_ollama.sh"
    echo "   Run with: ./monitor_ollama.sh"
}

# Main installation process
main() {
    echo "🎯 Starting Ollama setup for PI-LMS..."
    echo "======================================"
    
    check_architecture
    install_ollama
    start_ollama_service
    download_model
    test_installation
    configure_ollama
    create_monitoring_script
    
    echo ""
    echo "🎉 Ollama setup completed successfully!"
    echo "======================================"
    echo ""
    echo "📋 Next steps:"
    echo "1. Update your PI-LMS .env file with:"
    echo "   ENABLE_LOCAL_LLM=true"
    echo "   OLLAMA_HOST=http://localhost:11434"
    echo "   LLM_MODEL=llama3.2:3b-instruct-q4_K_M"
    echo ""
    echo "2. Start your PI-LMS AI service:"
    echo "   cd pi-ai && python api.py"
    echo ""
    echo "3. Monitor performance with:"
    echo "   ./monitor_ollama.sh"
    echo ""
    echo "🔧 Useful commands:"
    echo "   ollama list              # List installed models"
    echo "   ollama ps                # Show running models"
    echo "   ollama show llama3.2:3b-instruct-q4_K_M  # Model info"
    echo "   systemctl status ollama  # Service status (if system install)"
}

# Run main function
main "$@"