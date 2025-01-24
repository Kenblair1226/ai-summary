FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg nodejs && \
    npm install youtube-po-token-generator && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for database and media files
RUN mkdir -p /data

# Set environment variable for database path
ENV DB_PATH=/data/database.db

CMD ["python", "main.py"]
