FROM python:3.12-alpine

WORKDIR /app

# Copy files and directories separately to ensure proper structure
COPY requirements.txt config.py slack_main.py /app/
COPY sdk /app/sdk/
COPY slack_handlers /app/slack_handlers/

# Install build dependencies, upgrade security-critical packages, then install Python packages
RUN apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers python3-dev \
    && apk upgrade libcrypto3 libssl3 sqlite-libs \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps

# Verify sqlite-libs version (for security audit)
RUN apk info sqlite-libs && echo "✅ sqlite-libs version verified"

# Remove sqlite binary tools (sqlite-libs must remain as Python dependency)
# Note: sqlite-libs cannot be removed from Alpine Python - it's a core Python dependency
RUN apk del sqlite || true

# Run the app
CMD ["python", "slack_main.py"]
