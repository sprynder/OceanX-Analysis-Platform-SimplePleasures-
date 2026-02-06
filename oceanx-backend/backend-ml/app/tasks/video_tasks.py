"""Async video processing task"""
import os
from typing import Optional
from uuid import uuid4
from app.celery_app import celery_app
from app.video.extract_frames import extract_frames
from app.vision.roi import detect_rois
from app.vision.embedding import embed, EMBEDDING_DIM
from app.storage.qdrant import client, init_collection
from app.config import ROI_DIR, GATEWAY_API, COLLECTION_NAME
import requests


def send_progress_event(video_id: str, event_type: str, **kwargs):
    """Send a progress event to the Go backend"""
    payload = {
        "type": event_type,
        "video_id": video_id,
        **kwargs
    }
    try:
        requests.post(
            f"{GATEWAY_API}/videos/{video_id}/progress",
            json=payload,
            timeout=5,
        )
    except Exception as e:
        print(f"Failed to post progress: {e}")


@celery_app.task(bind=True, name="video.process_video")
def process_video_task(
    self,
    video_id: str,
    video_path: str,
    every_seconds: float = 0.5,
    embedding_model: str = "bioclip2"
):
    """
    Extract frames from video, detect ROIs, generate embeddings, and store in Qdrant
    
    Args:
        video_id: UUID of the video
        video_path: Path to video file
        every_seconds: Extract frame every N seconds (default: 0.5)
    """
    try:
        # Initialize Qdrant collection
        init_collection(EMBEDDING_DIM)
        
        # Create ROI directory for this video
        video_roi_dir = os.path.join(ROI_DIR, video_id)
        os.makedirs(video_roi_dir, exist_ok=True)
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        frames = extract_frames(video_path, every_seconds)
        init_collection(EMBEDDING_DIM)

        points = []
        frames_data = []

        send_progress_event(
            video_id,
            "processing_started",
            message=f"Starting processing with {len(frames)} frames",
        )

        for frame_idx, frame in enumerate(frames):
            rois = detect_rois(frame, frame_idx)
            timestamp_sec = frame_idx * every_seconds

            frame_id = str(uuid4())
            rois_data = []

            for roi in rois:
                x1, y1, x2, y2 = roi["bbox"]
                roi_crop = frame.crop((x1, y1, x2, y2))
                vector = embed(roi_crop, model_name=embedding_model)

                roi_id = str(uuid4())

                # Save ROI crop to disk
                roi_filename = f"{roi_id}.jpg"
                roi_path = os.path.join(video_roi_dir, roi_filename)
                roi_crop.save(roi_path, "JPEG")

                roi_url = f"/rois/{video_id}/{roi_filename}"

                points.append({
                    "id": roi_id,
                    "vector": vector,
                    "payload": {
                        "frame_idx": roi["frame_idx"],
                        "bbox": roi["bbox"],
                        "roi_id": roi_id,
                        "video_id": video_id,
                        "frame_id": frame_id,
                        "timestamp_sec": timestamp_sec,
                    }
                })

                rois_data.append({
                    "id": roi_id,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "roi_url": roi_url,
                })

            frames_data.append({
                "id": frame_id,
                "video_id": video_id,
                "frame_index": frame_idx,
                "rois": rois_data,
            })

            if (frame_idx + 1) % 3 == 0:
                send_progress_event(
                    video_id,
                    "frame_progress",
                    frame_index=frame_idx,
                    frames_processed=frame_idx + 1,
                    total_frames=len(frames),
                    rois_detected=len(points),
                    message=(
                        f"Processed {frame_idx + 1}/{len(frames)} frames, "
                        f"found {len(points)} ROIs"
                    ),
                )

        if points:
            client.upsert(collection_name=COLLECTION_NAME, points=points)

        response_payload = {
            "frames": frames_data,
        }

        requests.post(
            f"{GATEWAY_API}/videos/{video_id}/complete",
            json=response_payload,
            timeout=5,
        )

        send_progress_event(
            video_id,
            "processing_complete",
            message="Video processing complete",
            frames_processed=len(frames),
            total_frames=len(frames),
            rois_detected=len(points),
        )

        return response_payload
        
    except Exception as e:
        error_msg = str(e)
        send_progress_event(video_id, "processing_error", message=f"Error: {error_msg}")
        raise
