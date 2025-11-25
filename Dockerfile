# Multi-stage Dockerfile for EDA Agent Template

# Stage 1: Base image with EDA tools
FROM ubuntu:22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Note: EDA tools (OpenSTA, OpenROAD, Yosys) must be pre-installed
# or available via pip install from company mirror
# If tools are installed via pip, they will be installed in the next stage

# Stage 2: Python environment
FROM base AS python-env

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies from company mirror
# Set PIP_INDEX_URL environment variable to use company mirror
ARG PIP_INDEX_URL
RUN if [ -n "$PIP_INDEX_URL" ]; then \
        pip3 install --no-cache-dir --index-url $PIP_INDEX_URL -r requirements.txt; \
    else \
        pip3 install --no-cache-dir -r requirements.txt; \
    fi

# Stage 3: Application
FROM python-env AS app

WORKDIR /app

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Expose Streamlit port
EXPOSE 8501

# Default command
CMD ["streamlit", "run", "examples/ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

