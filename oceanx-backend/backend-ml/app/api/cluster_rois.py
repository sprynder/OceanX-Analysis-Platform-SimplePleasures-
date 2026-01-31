# backend-ml/app/api/cluster_rois.py
import numpy as np
from fastapi import APIRouter, HTTPException
from app.storage.qdrant import client
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from app.vision.clustering import cluster_embeddings
from app.schemas.schemas import (
    ClusterROIsRequest,
    ClusterROIsResponse,
    ROIClusterMapping,
)
from app.config import COLLECTION_NAME

router = APIRouter(prefix="/cluster-rois")


@router.post("", response_model=ClusterROIsResponse)
async def cluster_rois(request: ClusterROIsRequest):
    """
    Cluster ROI embeddings for a video using HDBSCAN.
    
    Retrieves all ROI embeddings for a given video from Qdrant,
    clusters them, and returns the mapping of ROI IDs to cluster IDs.
    """
    video_id = request.video_id
    min_cluster_size = request.min_cluster_size
    pca_components = request.pca_components
    
    # Retrieve all embeddings for the video from Qdrant
    try:
        video_filter = Filter(must=[FieldCondition(key="video_id", match=MatchValue(value=video_id))])
        search_result = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=video_filter,
            limit=10000,  # Adjust as needed for your use case
            with_payload=True,
            with_vectors=True
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve embeddings from Qdrant: {str(e)}",
        )
    points, _ = search_result
    if not points:
        raise HTTPException(
            status_code=404,
            detail=f"No ROIs found for video {video_id}",
        )
    
    # Extract embeddings and ROI IDs
    embeddings = []
    roi_ids = []
    
    for point in points:
        embeddings.append(point.vector)
        roi_ids.append(point.payload.get("roi_id"))
    
    embeddings = np.array(embeddings)

    # Perform clustering
    try:
        cluster_labels = cluster_embeddings(
            embeddings,
            min_cluster_size=min_cluster_size,
            pca_components=pca_components,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Clustering failed: {str(e)}",
        )
    
    # Map ROI IDs to cluster IDs
    roi_clusters = [
        ROIClusterMapping(roi_id=roi_id, cluster_id=int(cluster_label))
        for roi_id, cluster_label in zip(roi_ids, cluster_labels)
    ]

    # Send clustering results to Go backend
    import requests
    from app.config import GATEWAY_API
    try:
        payload = {
            "video_id": video_id,
            "roi_clusters": [
                {"roi_id": rc.roi_id, "cluster_id": rc.cluster_id} for rc in roi_clusters
            ]
        }
        requests.post(
            f"{GATEWAY_API}/videos/{video_id}/clusters",
            json=payload,
            timeout=5
        )
    except Exception as e:
        print(f"Warning: Failed to notify Go backend of clustering results: {e}")

    # Count unique clusters (excluding noise with -1)
    unique_clusters = len(set(c for c in cluster_labels if c != -1))

    return ClusterROIsResponse(
        video_id=video_id,
        roi_clusters=roi_clusters,
        num_clusters=unique_clusters,
    )
