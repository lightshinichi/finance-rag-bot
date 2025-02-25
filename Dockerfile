# Dockerfile
FROM heroku/heroku:24

# System dependencies
RUN apt-get update && \
    apt-get install -y \
    python3-pip \
    libopenblas-dev \
    libgomp1

# Application setup
WORKDIR /app
COPY . .

# Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Runtime configuration
ENV PORT=8000
EXPOSE $PORT
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]
