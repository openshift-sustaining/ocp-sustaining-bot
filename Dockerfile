FROM python:3.12-alpine

WORKDIR /app

# Copy files and directories separately to ensure proper structure
COPY requirements.txt config.py slack_main.py /app/
COPY sdk /app/sdk/
COPY slack_handlers /app/slack_handlers/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Remove zlib and compression libraries if not needed
# RUN apk del zlib zlib-dev

# Run the app
CMD ["python", "slack_main.py"]
