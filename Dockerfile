# Located in root directory
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

# Set working directory and copy requirements
WORKDIR /app
COPY ./requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY ./app ./app
COPY ./stored_md_files ./stored_md_files

# Expose port and run application
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
