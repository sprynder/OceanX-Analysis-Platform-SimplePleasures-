"""Async clustering task with HDBSCAN parameters"""
import numpy as np
from typing import Optional
from app.celery_app import celery_app
from app.storage.qdrant import client
from app.vision.clustering import cluster_embeddings
from app.config import COLLECTION_NAME, GATEWAY_API
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
import requests


@celery_app.task(bind=True, name="clustering.cluster_rois")
def cluster_rois_task(
    self,
    video_id: str,
    min_cluster_size: int = 5,
    min_samples: Optional[int] = None,
    cluster_selection_epsilon: float = 0.0,
    max_cluster_size: int = 0,
    cluster_selection_method: str = "eom",
    pca_components: int = 100
):
    """
    Cluster ROIs for a video using HDBSCAN with specified parameters
    
    Args:
        video_id: UUID of the video
        min_cluster_size: Minimum cluster size (default: 5)
        min_samples: Minimum samples in neighborhood (default: min_cluster_size if None)
        cluster_selection_epsilon: Distance threshold (default: 0.0)
        max_cluster_size: Maximum cluster size (0 = no limit, default: 0)
        cluster_selection_method: Cluster selection method ('eom' or 'leaf', default: 'eom')
        pca_components: Number of PCA components (default: 100)
    """
    try:
        video_filter = Filter(must=[FieldCondition(key="video_id", match=MatchValue(value=video_id))])
        search_result = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=video_filter,
            limit=10000,
            with_payload=True,
            with_vectors=True,
        )
        points, _ = search_result

        if not points:
            raise ValueError(f"No ROIs found for video {video_id}")

        embeddings = []
        roi_ids = []

        for point in points:
            embeddings.append(point.vector)
            roi_ids.append(point.payload.get("roi_id"))

        embeddings = np.array(embeddings)

        cluster_labels = cluster_embeddings(
            embeddings,
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            cluster_selection_epsilon=cluster_selection_epsilon,
            max_cluster_size=max_cluster_size,
            cluster_selection_method=cluster_selection_method,
            pca_components=pca_components,
        )

        roi_clusters = [
            {"roi_id": roi_id, "cluster_id": int(cluster_label)}
            for roi_id, cluster_label in zip(roi_ids, cluster_labels)
        ]

        requests.post(
            f"{GATEWAY_API}/videos/{video_id}/clusters",
            json={"video_id": video_id, "roi_clusters": roi_clusters},
            timeout=5,
        )

        unique_clusters = len(set(c for c in cluster_labels if c != -1))

        return {
            "video_id": video_id,
            "roi_clusters": roi_clusters,
            "num_clusters": unique_clusters,
        }

    except Exception as e:
        raise
