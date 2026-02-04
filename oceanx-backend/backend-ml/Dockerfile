# backend-ml/Dockerfile
FROM python:3.13-slim

WORKDIR /app
RUN apt-get update && apt-get install -y \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    libglib2.0-0 \ 
    gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p ./models
COPY models/benthic_object_detector.pt ./models/benthic_object_detector.pt
COPY models/midwater_object_detector.pt ./models/midwater_object_detector.pt
COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
