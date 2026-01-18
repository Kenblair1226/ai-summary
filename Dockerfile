FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (ffmpeg for yt-dlp audio extraction, curl/unzip for deno)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl unzip && \
    rm -rf /var/lib/apt/lists/*

# Install deno (JavaScript runtime for yt-dlp YouTube extraction)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_INSTALL="/root/.deno"
ENV PATH="${DENO_INSTALL}/bin:${PATH}"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY run.py .
COPY public/ ./public/

# Create directory for database and media files
RUN mkdir -p /data

# Set environment variable for database path
ENV DB_PATH=/data/database.db
ENV PYTHONPATH=/app/src

CMD ["python", "run.py"]
