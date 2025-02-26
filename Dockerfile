# Use official Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MD_STORAGE_DIR=/app/stored_md_files \
    FAISS_INDEX_DIR=/app/faiss_index

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entire application
COPY ./app .

# Create document storage directory
RUN mkdir -p stored_md_files faiss_index

# Expose port
EXPOSE 8000

# Start application
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
