FROM python:3.12-alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    linux-headers \
    python3-dev

# Copy requirements and install dependencies
COPY slack_worker/requirements.txt /app/slack_worker/requirements.txt
RUN pip install --no-cache-dir -r /app/slack_worker/requirements.txt
RUN apk del .build-deps


# Copy only the slack_worker service
COPY slack_worker /app/slack_worker/
# Copy sdk package for dependencies
COPY sdk /app/sdk/

# Create lock directory for file-based locking
RUN mkdir -p /tmp/slack_worker_locks

# Set Python path
ENV PYTHONPATH=/app

# Run the worker service
CMD ["python", "-m", "slack_worker.main"]
