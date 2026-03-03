# backend-ml/app/api/cluster_rois.py
from fastapi import APIRouter
from app.schemas.schemas import ClusterROIsRequest
from app.tasks.cluster_tasks import cluster_rois_task

router = APIRouter(prefix="/cluster-rois")


@router.post("")
async def cluster_rois(request: ClusterROIsRequest):
    """
    Cluster ROI embeddings for a video using HDBSCAN.
    
    Retrieves all ROI embeddings for a given video from Qdrant,
    clusters them, and returns the mapping of ROI IDs to cluster IDs.
    """
    task = cluster_rois_task.delay(
        request.video_id,
        request.min_cluster_size,
        request.min_samples,
        request.cluster_selection_epsilon,
        request.max_cluster_size,
        request.cluster_selection_method,
        request.pca_components,
    )

    return {"task_id": task.id, "status": "queued"}
