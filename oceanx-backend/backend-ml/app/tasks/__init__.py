# Tasks module - imported by Celery autodiscover
from .video_tasks import process_video_task
from .cluster_tasks import cluster_rois_task

__all__ = ["process_video_task", "cluster_rois_task"]
