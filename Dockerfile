
FROM heroku/heroku:24


RUN apt-get update && \
    apt-get install -y \
    openblas-64bit-dev \  # Replaces libopenblas-dev in Ubuntu 24.04
    libomp-dev \          # OpenMP support
    python3-pip


WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt


EXPOSE $PORT


CMD uvicorn main:app --host=0.0.0.0 --port=$PORT