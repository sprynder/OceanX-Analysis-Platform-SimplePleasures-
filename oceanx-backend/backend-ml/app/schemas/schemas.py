from pydantic import BaseModel
from typing import Dict, List, Optional

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
    umap_x: float
    umap_y: float
    umap_z: float


class ClusterROIsResponse(BaseModel):
    video_id: str
    roi_clusters: List[ROIClusterMapping]
    num_clusters: int


class SearchROIsRequest(BaseModel):
    video_id: Optional[str] = None  # None = search across all videos
    query: str
    top_k: int = 10
    dedup_enabled: bool = True
    tau_time: float = 2.0    # seconds — suppress results within this window
    tau_iou: float = 0.3     # IoU threshold — suppress overlapping boxes
    tau_emb: float = 0.85    # cosine similarity — suppress visually identical results


class ImageSearchROIsRequest(BaseModel):
    video_id: Optional[str] = None  # None = search across all videos
    image_b64: str            # base64-encoded image (any format PIL can read)
    top_k: int = 10
    dedup_enabled: bool = True
    tau_time: float = 2.0
    tau_iou: float = 0.3
    tau_emb: float = 0.85


class SearchROIResult(BaseModel):
    roi_id: str
    score: float             # cosine similarity to the text query (0–1)
    timestamp_sec: float
    bbox: List[float]        # [x1, y1, x2, y2]
    frame_idx: int
    roi_url: str
    video_id: str            # included so cross-video results know their source


class SearchROIsResponse(BaseModel):
    video_id: Optional[str]
    results: List[SearchROIResult]
    raw_count: int           # candidates before dedup, for comparing dedup impact


class GlobalUMAPRequest(BaseModel):
    dedup_enabled: bool = False
    tau_time: float = 2.0    # seconds — suppress ROIs within this temporal window
    tau_iou: float = 0.3     # IoU threshold
    tau_emb: float = 0.85    # cosine similarity threshold


class GlobalROI(BaseModel):
    roi_id: str
    video_id: str
    frame_idx: int
    roi_url: str
    umap_x: float
    umap_y: float
    umap_z: float
    cluster: int             # per-video cluster assignment preserved for context


class GlobalUMAPResponse(BaseModel):
    rois: List[GlobalROI]
    video_count: int
    roi_count: int
