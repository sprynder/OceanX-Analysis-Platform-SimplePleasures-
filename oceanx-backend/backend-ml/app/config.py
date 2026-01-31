# backend-ml/app/config.py
import os

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "roi_embeddings"
GATEWAY_API = os.getenv("GATEWAY_API", "http://localhost:8080")
ROI_DIR = os.getenv("ROI_DIR", "/data/rois")
