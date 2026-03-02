# syntax=docker/dockerfile:1.7
# backend-ml/Dockerfile
FROM python:3.11-slim-bookworm

WORKDIR /app
RUN apt-get update && apt-get install -y \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    libglib2.0-0 \
    openjdk-17-jre-headless \
    gcc \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
RUN mkdir -p ./models
COPY models/benthic_object_detector.pt ./models/benthic_object_detector.pt
COPY models/midwater_object_detector.pt ./models/midwater_object_detector.pt
COPY app ./app
RUN find app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
