# backend-ml/app/api/process_video.py
import os
import requests
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.video.extract_frames import extract_frames
from app.vision.roi import detect_rois
from app.vision.embedding import embed, EMBEDDING_DIM
from app.vision.dedup import deduplicate
from app.storage.qdrant import client, init_collection
from app.schemas.schemas import ProcessVideoRequest
from uuid import uuid4
from app.config import GATEWAY_API, ROI_DIR
router = APIRouter(prefix="/process-video")

@router.post("")
async def process_video(request: ProcessVideoRequest, every_seconds: float = 0.5):
    video_path = request.video_path
    video_id = request.video_id
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")
    
    frames = extract_frames(video_path, every_seconds)
    init_collection(EMBEDDING_DIM)

    # Create ROI directory for this video
    video_roi_dir = os.path.join(ROI_DIR, video_id)
    os.makedirs(video_roi_dir, exist_ok=True)

    points = []
    frames_data = []
    
    print("Processing frames and extracting ROIs...")
    for frame_idx, frame in enumerate(frames):
        rois = detect_rois(frame, frame_idx)
        timestamp_sec = frame_idx * every_seconds
        
        # Generate frame UUID
        frame_id = str(uuid4())
        
        rois_data = []
        for roi_idx, roi in enumerate(rois):
            x1, y1, x2, y2 = roi["bbox"]
            roi_crop = frame.crop((x1, y1, x2, y2))
            vector = embed(roi_crop)
            
            # Generate ROI UUID
            roi_id = str(uuid4())
            
            # Save ROI crop to disk
            roi_filename = f"{roi_id}.jpg"
            roi_path = os.path.join(video_roi_dir, roi_filename)
            roi_crop.save(roi_path, "JPEG")
            
            # Create relative path for storage
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
                    "timestamp_sec": timestamp_sec
                }
            })
            
            rois_data.append({
                "id": roi_id,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "roi_url": roi_url
            })
        
        frames_data.append({
            "id": frame_id,
            "video_id": video_id,
            "frame_index": frame_idx,
            "rois": rois_data
        })

    if points:
        # TODO: ingestion-time dedup — uncomment to keep only unique ROIs in Qdrant.
        # Use the dedup slider in the UI for now to explore at search-time instead.
        # dedup_candidates = [
        #     {"id": p["id"], "vector": p["vector"],
        #      "timestamp_sec": p["payload"]["timestamp_sec"], "bbox": p["payload"]["bbox"]}
        #     for p in points
        # ]
        # kept = deduplicate(dedup_candidates, tau_time=1.0, tau_iou=0.3, tau_emb=0.85)
        # kept_ids = {c["id"] for c in kept}
        # points = [p for p in points if p["id"] in kept_ids]
        # for frame in frames_data:
        #     frame["rois"] = [r for r in frame["rois"] if r["id"] in kept_ids]
        # print(f"[Dedup] {len(dedup_candidates)} ROIs → {len(points)} after ingestion dedup")

        client.upsert(collection_name="roi_embeddings", points=points)

    # Send frame and ROI metadata back to Go API
    response_payload = {
        "frames": frames_data
    }
    
    requests.post(
        f"{GATEWAY_API}/videos/{video_id}/complete",
        json=response_payload,
        timeout=5
    )
    
    return response_payload
