from pydantic import BaseModel
from typing import Dict, List

class ProcessVideoRequest(BaseModel):
    video_id: str
    video_path: str


class ClusterROIsRequest(BaseModel):
    video_id: str
    min_cluster_size: int = 5
    pca_components: int = 50


class ROIClusterMapping(BaseModel):
    roi_id: str
    cluster_id: int


class ClusterROIsResponse(BaseModel):
    video_id: str
    roi_clusters: List[ROIClusterMapping]
    num_clusters: int