# backend-ml/app/api/process_video.py
import os
import requests
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.video.extract_frames import extract_frames
from app.vision.roi import detect_rois_batch
from app.vision.embedding import embed_batch, EMBEDDING_DIM
from app.storage.qdrant import client, init_collection
from app.schemas.schemas import ProcessVideoRequest
from uuid import uuid4
from app.config import GATEWAY_API, ROI_DIR
router = APIRouter(prefix="/process-video")

BATCH_SIZE = 8  # Process frames in batches of 8

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
    
    print("Processing frames and extracting ROIs (batch mode)...")
    
    # Process frames in batches
    for batch_start in range(0, len(frames), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(frames))
        frame_batch = frames[batch_start:batch_end]
        frame_ids = list(range(batch_start, batch_end))
        
        print(f"Processing frame batch {batch_start}-{batch_end-1} ({len(frame_batch)} frames)")
        
        # Batch ROI detection
        batch_rois = detect_rois_batch(frame_batch, frame_ids)
        
        # Collect ROI crops for batch embedding
        roi_crops_for_embedding = []
        roi_metadata = []  # Track ROI info for later
        
        for frame_idx, frame, rois_in_frame in zip(frame_ids, frame_batch, batch_rois):
            timestamp_sec = frame_idx * every_seconds
            frame_id = str(uuid4())
            rois_data = []
            
            for roi in rois_in_frame:
                x1, y1, x2, y2 = roi["bbox"]
                roi_crop = frame.crop((x1, y1, x2, y2))
                roi_id = str(uuid4())
                
                # Collect for batch embedding
                roi_crops_for_embedding.append(roi_crop)
                roi_metadata.append({
                    "roi_id": roi_id,
                    "roi_crop": roi_crop,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "frame_idx": frame_idx,
                    "frame_id": frame_id,
                    "timestamp_sec": timestamp_sec,
                    "video_id": video_id
                })
                
                rois_data.append({
                    "id": roi_id,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "roi_url": f"/rois/{video_id}/{roi_id}.jpg"
                })
            
            frames_data.append({
                "id": frame_id,
                "video_id": video_id,
                "frame_index": frame_idx,
                "rois": rois_data
            })
        
        # Batch embedding generation
        if roi_metadata:
            print(f"Generating embeddings for {len(roi_metadata)} ROIs...")
            embeddings = embed_batch([m["roi_crop"] for m in roi_metadata])
            
            # Process results and save
            for roi_meta, vector in zip(roi_metadata, embeddings):
                roi_id = roi_meta["roi_id"]
                roi_crop = roi_meta["roi_crop"]
                
                # Save ROI crop to disk
                roi_filename = f"{roi_id}.jpg"
                roi_path = os.path.join(video_roi_dir, roi_filename)
                roi_crop.save(roi_path, "JPEG")
                
                # Add to Qdrant points
                points.append({
                    "id": roi_id,
                    "vector": vector,
                    "payload": {
                        "frame_idx": roi_meta["frame_idx"],
                        "bbox": [roi_meta["x1"], roi_meta["y1"], roi_meta["x2"], roi_meta["y2"]],
                        "roi_id": roi_id,
                        "video_id": video_id,
                        "frame_id": roi_meta["frame_id"],
                        "timestamp_sec": roi_meta["timestamp_sec"]
                    }
                })
        
        # Batch upsert to Qdrant
        if points:
            print(f"Upserting {len(points)} embeddings to Qdrant...")
            client.upsert(collection_name="roi_embeddings", points=points, wait=False)
            points = []  # Clear for next batch

    # Send frame and ROI metadata back to Go API
    response_payload = {
        "frames": frames_data
    }
    
    print(f"Sending results to Go backend...")
    requests.post(
        f"{GATEWAY_API}/videos/{video_id}/complete",
        json=response_payload,
        timeout=5
    )
    
    return response_payload
