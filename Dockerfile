FROM python:3.12-slim

WORKDIR /app

# Copy only the necessary files and directories
COPY requirements.txt .
COPY config.py .
COPY slack_main.py .
COPY sdk/ sdk/
COPY slack_handlers/ slack_handlers/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the app
CMD ["python", "slack_main.py"]
