from pydantic import BaseModel
from typing import Dict, List

class ProcessVideoRequest(BaseModel):
    video_id: str
    video_path: str
    embedding_model: str = "bioclip2"


class ClusterROIsRequest(BaseModel):
    video_id: str
    algorithm: str = 'hdbscan'
    min_cluster_size: int = 5
    min_samples: int = None
    cluster_selection_epsilon: float = 0.0
    max_cluster_size: int = None
    cluster_selection_method: str = 'eom'
    pca_components: int = 50
    kmeans_k: int = 8
    kmeans_seed: int = 42
    kmeans_max_iter: int = 20


class ROIClusterMapping(BaseModel):
    roi_id: str
    cluster_id: int


class ClusterROIsResponse(BaseModel):
    video_id: str
    roi_clusters: List[ROIClusterMapping]
    num_clusters: int