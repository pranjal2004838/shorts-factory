# Cloud Run-ready image for the Shorts Factory backend (Week 1 slice).
FROM python:3.11-slim

# ffmpeg + ffprobe are required by the sanitizer and slicer.
# libgl/libglib are required by opencv-python-headless / mediapipe.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Cloud Run injects $PORT (defaults to 8080).
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
