FROM python:3.12-slim

WORKDIR /app

# Copy files and directories separately to ensure proper structure
COPY requirements.txt config.py slack_main.py /app/
COPY sdk /app/sdk/
COPY slack_handlers /app/slack_handlers/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the app
CMD ["python", "slack_main.py"]
