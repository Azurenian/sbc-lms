# Pi-LMS Testing Container - Optimized for Orange Pi 5 Performance Analysis
FROM python:3.11-slim

# Install system dependencies for testing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    htop \
    sysstat \
    net-tools \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash tester \
    && chown -R tester:tester /app
USER tester

# Python environment setup
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/home/tester/.local/bin:$PATH"

# Copy requirements first for better caching
COPY --chown=tester:tester requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir --upgrade pip \
    && pip install --user --no-cache-dir -r requirements.txt

# Install additional web server for results dashboard
RUN pip install --user --no-cache-dir fastapi uvicorn jinja2 aiofiles

# Copy testing suite
COPY --chown=tester:tester . .

# Create directories for results and test data
RUN mkdir -p results test_files reports logs

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Expose port for web interface
EXPOSE 9000

# Start testing web server
CMD ["python", "testing_web_server.py"]