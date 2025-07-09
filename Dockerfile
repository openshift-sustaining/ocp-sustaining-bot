FROM python:3.12-slim

WORKDIR /app

# Copy only the necessary files and directories
COPY requirements.txt config.py slack_main.py sdk/ slack_handlers/ ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the app
CMD ["python", "slack_main.py"]
