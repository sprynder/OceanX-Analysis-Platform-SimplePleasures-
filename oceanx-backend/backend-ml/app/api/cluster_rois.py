# backend-ml/app/api/cluster_rois.py
import numpy as np
import umap
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
    Cluster ROI embeddings for a video using HDBSCAN, then reduce to 3D via
    UMAP for visualisation.  Results are sent to the Go backend and returned.
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
            limit=10000,
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

    # Perform clustering — also returns PCA-reduced embeddings for UMAP
    try:
        cluster_labels, embeddings_reduced = cluster_embeddings(
            embeddings,
            min_cluster_size=min_cluster_size,
            pca_components=pca_components,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Clustering failed: {str(e)}",
        )

    # Compute 3D UMAP on the same PCA-reduced embeddings
    try:
        n_neighbors = min(15, len(roi_ids) - 1)
        reducer = umap.UMAP(
            n_components=3,
            n_neighbors=n_neighbors,
            min_dist=0.1,
            metric='euclidean',
            random_state=42,
        )
        coords_3d = reducer.fit_transform(embeddings_reduced)  # shape (n, 3)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"UMAP reduction failed: {str(e)}",
        )

    # Build ROI → cluster + 3D coords mappings
    roi_clusters = [
        ROIClusterMapping(
            roi_id=roi_ids[i],
            cluster_id=int(cluster_labels[i]),
            umap_x=float(coords_3d[i, 0]),
            umap_y=float(coords_3d[i, 1]),
            umap_z=float(coords_3d[i, 2]),
        )
        for i in range(len(roi_ids))
    ]

    # Send clustering results to Go backend
    import requests
    from app.config import GATEWAY_API
    try:
        payload = {
            "video_id": video_id,
            "roi_clusters": [
                {
                    "roi_id": rc.roi_id,
                    "cluster_id": rc.cluster_id,
                    "umap_x": rc.umap_x,
                    "umap_y": rc.umap_y,
                    "umap_z": rc.umap_z,
                }
                for rc in roi_clusters
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
