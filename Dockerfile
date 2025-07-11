FROM python:3.12-alpine

WORKDIR /app

# Copy files and directories separately to ensure proper structure
COPY requirements.txt config.py slack_main.py /app/
COPY sdk /app/sdk/
COPY slack_handlers /app/slack_handlers/

# Install build dependencies, then install Python packages, then remove build dependencies
RUN apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers python3-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps

# Remove zlib and compression libraries if not needed
# RUN apk del zlib zlib-dev

# Run the app
CMD ["python", "slack_main.py"]
