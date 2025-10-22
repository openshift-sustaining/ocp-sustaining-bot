FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY slack_worker/requirements.txt /app/slack_worker/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/slack_worker/requirements.txt

# Copy the entire project (needed for shared config.py)
COPY . /app/

# Create lock directory with proper permissions
RUN mkdir -p /app/locks && chmod 777 /app/locks

# Set Python path to include parent directory
ENV PYTHONPATH=/app:${PYTHONPATH}


# Run the worker
CMD ["python", "-u", "/app/slack_worker/slack_worker_main.py"]

