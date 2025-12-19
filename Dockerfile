# Use official Python 3.10 image as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Update package manager and install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

COPY . /app
RUN pip install --no-cache-dir .

# Expose port
EXPOSE 8000

# Set default startup command
ENTRYPOINT ["python", "-m", "alibaba_cloud_ops_mcp_server"]
