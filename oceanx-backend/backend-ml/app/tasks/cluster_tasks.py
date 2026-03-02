"""Async clustering task with HDBSCAN parameters"""
import numpy as np
import time
from typing import Optional
from app.celery_app import celery_app
from app.storage.qdrant import client
from app.vision.clustering import cluster_embeddings
from app.config import (
    COLLECTION_NAME,
    GATEWAY_API,
    SPARK_MASTER,
    SPARK_APP_NAME,
    KMEANS_USE_SPARK,
    QDRANT_SCROLL_PAGE_SIZE,
    CLUSTER_WRITE_BATCH_SIZE,
    CLUSTER_WRITE_MAX_RETRIES,
    CLUSTER_WRITE_TIMEOUT_SECONDS,
    CLUSTER_WRITE_RETRY_BACKOFF_SECONDS,
)
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
import requests


def _fetch_video_points(video_id: str, page_size: int):
    page_size = max(1, int(page_size))
    video_filter = Filter(must=[FieldCondition(key="video_id", match=MatchValue(value=video_id))])
    all_points = []
    next_offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=video_filter,
            limit=page_size,
            offset=next_offset,
            with_payload=True,
            with_vectors=True,
        )

        if not points:
            break

        all_points.extend(points)

        if next_offset is None:
            break

    return all_points


def _post_cluster_batch(
    video_id: str,
    roi_clusters_batch,
    timeout_seconds: int,
    max_retries: int,
    initial_backoff_seconds: float,
):
    retries = max(1, int(max_retries))
    backoff_seconds = max(0.0, float(initial_backoff_seconds))

    for attempt in range(retries):
        try:
            response = requests.post(
                f"{GATEWAY_API}/videos/{video_id}/clusters",
                json={"video_id": video_id, "roi_clusters": roi_clusters_batch},
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            return
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            if backoff_seconds > 0:
                time.sleep(backoff_seconds)
                backoff_seconds *= 2


def _post_cluster_results_batched(video_id: str, roi_clusters, batch_size: int):
    safe_batch_size = max(1, int(batch_size))

    for start in range(0, len(roi_clusters), safe_batch_size):
        batch = roi_clusters[start:start + safe_batch_size]
        _post_cluster_batch(
            video_id=video_id,
            roi_clusters_batch=batch,
            timeout_seconds=CLUSTER_WRITE_TIMEOUT_SECONDS,
            max_retries=CLUSTER_WRITE_MAX_RETRIES,
            initial_backoff_seconds=CLUSTER_WRITE_RETRY_BACKOFF_SECONDS,
        )


@celery_app.task(bind=True, name="clustering.cluster_rois")
def cluster_rois_task(
    self,
    video_id: str,
    algorithm: str = "hdbscan",
    min_cluster_size: int = 5,
    min_samples: Optional[int] = None,
    cluster_selection_epsilon: float = 0.0,
    max_cluster_size: int = 0,
    cluster_selection_method: str = "eom",
    pca_components: int = 100,
    kmeans_k: int = 8,
    kmeans_seed: int = 42,
    kmeans_max_iter: int = 20,
):
    """
    Cluster ROIs for a video using the configured clustering algorithm.
    
    Args:
        video_id: UUID of the video
        min_cluster_size: Minimum cluster size (default: 5)
        min_samples: Minimum samples in neighborhood (default: min_cluster_size if None)
        cluster_selection_epsilon: Distance threshold (default: 0.0)
        max_cluster_size: Maximum cluster size (0 = no limit, default: 0)
        cluster_selection_method: Cluster selection method ('eom' or 'leaf', default: 'eom')
        pca_components: Number of PCA components (default: 100)
        kmeans_k: Number of clusters for kmeans (default: 8)
        kmeans_seed: Random seed for kmeans (default: 42)
        kmeans_max_iter: Max iterations for kmeans (default: 20)
    """
    try:
        task_start = time.perf_counter()

        fetch_start = time.perf_counter()
        points = _fetch_video_points(video_id=video_id, page_size=QDRANT_SCROLL_PAGE_SIZE)
        fetch_seconds = time.perf_counter() - fetch_start

        if not points:
            raise ValueError(f"No ROIs found for video {video_id}")

        prepare_start = time.perf_counter()
        embeddings = []
        roi_ids = []

        for point in points:
            embeddings.append(point.vector)
            roi_ids.append(point.payload.get("roi_id"))

        embeddings = np.array(embeddings)
        prepare_seconds = time.perf_counter() - prepare_start

        cluster_start = time.perf_counter()
        cluster_labels = cluster_embeddings(
            embeddings,
            algorithm=algorithm,
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            cluster_selection_epsilon=cluster_selection_epsilon,
            max_cluster_size=max_cluster_size,
            cluster_selection_method=cluster_selection_method,
            pca_components=pca_components,
            kmeans_k=kmeans_k,
            kmeans_seed=kmeans_seed,
            kmeans_max_iter=kmeans_max_iter,
            use_spark_kmeans=KMEANS_USE_SPARK,
            spark_master=SPARK_MASTER,
            spark_app_name=SPARK_APP_NAME,
        )
        clustering_seconds = time.perf_counter() - cluster_start

        mapping_start = time.perf_counter()
        roi_clusters = [
            {"roi_id": roi_id, "cluster_id": int(cluster_label)}
            for roi_id, cluster_label in zip(roi_ids, cluster_labels)
        ]
        mapping_seconds = time.perf_counter() - mapping_start

        write_start = time.perf_counter()
        write_batch_size = max(1, int(CLUSTER_WRITE_BATCH_SIZE))
        _post_cluster_results_batched(
            video_id=video_id,
            roi_clusters=roi_clusters,
            batch_size=write_batch_size,
        )
        writeback_seconds = time.perf_counter() - write_start

        total_seconds = time.perf_counter() - task_start

        unique_clusters = len(set(c for c in cluster_labels if c != -1))

        return {
            "video_id": video_id,
            "algorithm": algorithm,
            "roi_clusters": roi_clusters,
            "num_clusters": unique_clusters,
            "metrics": {
                "points_fetched": len(points),
                "fetch_seconds": round(fetch_seconds, 4),
                "prepare_seconds": round(prepare_seconds, 4),
                "clustering_seconds": round(clustering_seconds, 4),
                "mapping_seconds": round(mapping_seconds, 4),
                "writeback_seconds": round(writeback_seconds, 4),
                "total_seconds": round(total_seconds, 4),
                "write_batch_size": write_batch_size,
                "write_batches": (len(roi_clusters) + write_batch_size - 1) // write_batch_size,
            },
        }

    except Exception as e:
        raise
