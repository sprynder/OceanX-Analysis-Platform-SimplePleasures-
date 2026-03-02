# backend-ml/app/config.py
import os


def _env_bool(name: str, default: bool = False) -> bool:
	value = os.getenv(name)
	if value is None:
		return default
	return value.strip().lower() in {"1", "true", "yes", "on"}

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "roi_embeddings"
GATEWAY_API = os.getenv("GATEWAY_API", "http://localhost:8080")
ROI_DIR = os.getenv("ROI_DIR", "/data/rois")
SPARK_MASTER = os.getenv("SPARK_MASTER", "local[*]")
SPARK_APP_NAME = os.getenv("SPARK_APP_NAME", "oceanx-clustering-kmeans")
KMEANS_USE_SPARK = _env_bool("KMEANS_USE_SPARK", True)
QDRANT_SCROLL_PAGE_SIZE = int(os.getenv("QDRANT_SCROLL_PAGE_SIZE", 1000))
CLUSTER_WRITE_BATCH_SIZE = int(os.getenv("CLUSTER_WRITE_BATCH_SIZE", 1000))
CLUSTER_WRITE_MAX_RETRIES = int(os.getenv("CLUSTER_WRITE_MAX_RETRIES", 3))
CLUSTER_WRITE_TIMEOUT_SECONDS = int(os.getenv("CLUSTER_WRITE_TIMEOUT_SECONDS", 10))
CLUSTER_WRITE_RETRY_BACKOFF_SECONDS = float(os.getenv("CLUSTER_WRITE_RETRY_BACKOFF_SECONDS", 0.5))
