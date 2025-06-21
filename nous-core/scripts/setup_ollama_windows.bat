@echo off
REM Ollama Setup Script for Windows Development
REM This script downloads and installs Ollama for Windows development

echo 🚀 Setting up Ollama for PI-LMS Chatbot (Windows)
echo ================================================

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ℹ️  Running as Administrator
) else (
    echo ⚠️  Not running as Administrator - some features may be limited
)

REM Function to check if command exists
where ollama >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Ollama is already installed
    ollama --version
    goto :start_service
) else (
    echo 📦 Ollama not found, downloading installer...
)

REM Download Ollama for Windows
echo ⬇️  Downloading Ollama for Windows...
echo Please download Ollama from: https://ollama.ai/download/windows
echo After installation, run this script again.
echo.
echo Alternatively, you can install with winget:
echo   winget install Ollama.Ollama
echo.
pause
goto :check_installation

:check_installation
where ollama >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Ollama installation detected
    ollama --version
) else (
    echo ❌ Ollama not found. Please install it first.
    echo Visit: https://ollama.ai/download/windows
    pause
    exit /b 1
)

:start_service
echo 🔧 Starting Ollama service...

REM Start Ollama service in background
start /B ollama serve
echo ⏳ Waiting for Ollama to start...
timeout /t 5 /nobreak >nul

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Ollama service is running
) else (
    echo ❌ Failed to start Ollama service
    echo Please check if the service is running manually
    pause
    exit /b 1
)

:download_model
echo 📥 Downloading model: llama3.2:3b-instruct-q4_K_M
echo This may take several minutes depending on your internet connection...

ollama pull llama3.2:3b-instruct-q4_K_M
if %errorLevel% == 0 (
    echo ✅ Model downloaded successfully
) else (
    echo ❌ Failed to download model
    echo You can try downloading it manually later with:
    echo   ollama pull llama3.2:3b-instruct-q4_K_M
    pause
)

:test_installation
echo 🧪 Testing Ollama installation...

REM Test if model is available
ollama list | findstr "llama3.2:3b-instruct-q4_K_M" >nul
if %errorLevel% == 0 (
    echo ✅ Model is available and ready
) else (
    echo ❌ Model not found in Ollama
    goto :manual_test
)

REM Test generation
echo 🎯 Testing model generation...
echo Hello, test message | ollama run llama3.2:3b-instruct-q4_K_M >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Model generation test successful
) else (
    echo ⚠️  Model generation test failed, but model is installed
)

goto :create_scripts

:manual_test
echo Please test manually with:
echo   ollama run llama3.2:3b-instruct-q4_K_M
echo   ^> Hello, can you respond?

:create_scripts
echo 📊 Creating monitoring script...

REM Create monitoring batch file
(
echo @echo off
echo REM Ollama Performance Monitor for PI-LMS Windows
echo echo 🔍 Ollama Performance Monitor ^(Windows^)
echo echo ================================
echo.
echo :monitor_loop
echo for /f "tokens=1-4 delims=/ " %%%%i in ^('date /t'^) do set mydate=%%%%l-%%%%j-%%%%k
echo for /f "tokens=1-2 delims=: " %%%%i in ^('time /t'^) do set mytime=%%%%i:%%%%j
echo set timestamp=%%mydate%% %%mytime%%
echo.
echo REM Check if Ollama is running
echo tasklist /FI "IMAGENAME eq ollama.exe" 2^>NUL ^| find /I /N "ollama.exe" ^>NUL
echo if "%%ERRORLEVEL%%"=="0" ^(
echo     set ollama_status=RUNNING
echo ^) else ^(
echo     set ollama_status=STOPPED
echo ^)
echo.
echo echo [%%timestamp%%] Ollama: %%ollama_status%%
echo.
echo timeout /t 10 /nobreak ^>nul
echo goto :monitor_loop
) > monitor_ollama.bat

echo ✅ Monitoring script created: monitor_ollama.bat

REM Create start/stop scripts
(
echo @echo off
echo echo Starting Ollama service...
echo start /B ollama serve
echo echo Ollama service started in background
echo echo Check status with: curl http://localhost:11434/api/tags
) > start_ollama.bat

(
echo @echo off
echo echo Stopping Ollama service...
echo taskkill /F /IM ollama.exe 2^>nul
echo if "%%ERRORLEVEL%%"=="0" ^(
echo     echo Ollama service stopped
echo ^) else ^(
echo     echo Ollama service was not running
echo ^)
) > stop_ollama.bat

echo ✅ Created start_ollama.bat and stop_ollama.bat

:completion
echo.
echo 🎉 Ollama setup completed successfully!
echo ======================================
echo.
echo 📋 Next steps:
echo 1. Update your PI-LMS .env file with:
echo    ENABLE_LOCAL_LLM=true
echo    OLLAMA_HOST=http://localhost:11434
echo    LLM_MODEL=llama3.2:3b-instruct-q4_K_M
echo.
echo 2. Start your PI-LMS AI service:
echo    cd pi-ai && python api.py
echo.
echo 3. Monitor performance with:
echo    monitor_ollama.bat
echo.
echo 🔧 Useful commands:
echo    ollama list              # List installed models
echo    ollama ps                # Show running models
echo    ollama show llama3.2:3b-instruct-q4_K_M  # Model info
echo    start_ollama.bat         # Start Ollama service
echo    stop_ollama.bat          # Stop Ollama service
echo.
echo 💡 Development Tips:
echo - Set ENABLE_LOCAL_LLM=false in .env to use mock responses
echo - Use Task Manager to check Ollama memory usage
echo - Ollama runs on port 11434 by default
echo.
pause