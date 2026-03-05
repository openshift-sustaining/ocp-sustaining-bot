FROM python:3.12-alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    linux-headers \
    python3-dev

# Copy slack_worker requirements
COPY slack_worker/requirements.txt /app/slack_worker/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/slack_worker/requirements.txt

# Remove build dependencies
RUN apk del .build-deps

# Copy necessary files from parent directory
COPY sdk /app/sdk/

# Copy slack_worker service
COPY slack_worker /app/slack_worker/

# Create lock directory for file-based locking
RUN mkdir -p /tmp/slack_worker_locks

# Set Python path
ENV PYTHONPATH=/app

# Run the worker service
CMD ["python", "-m", "slack_worker.main"]
