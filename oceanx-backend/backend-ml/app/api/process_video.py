# backend-ml/app/api/process_video.py
from fastapi import APIRouter, UploadFile, File
from app.video.extract_frames import extract_frames
from app.vision.roi import detect_rois
from app.vision.embedding import embed, EMBEDDING_DIM
from app.storage.qdrant import client, init_collection
from uuid import uuid4

router = APIRouter(prefix="/process-video")

@router.post("")
async def process_video(file: UploadFile = File(...), every_seconds: float = 1.0):
    frames = extract_frames(file, every_seconds)
    init_collection(EMBEDDING_DIM)

    points = []

    for frame_idx, frame in enumerate(frames):
        rois = detect_rois(frame, frame_idx)
        for roi_idx, roi in enumerate(rois):
            x1, y1, x2, y2 = roi["bbox"]
            roi_crop = frame.crop((x1, y1, x2, y2))
            vector = embed(roi_crop)
            points.append({
                "id": str(uuid4()),
                "vector": vector,
                "payload": {
                    "frame_idx": roi["frame_idx"],
                    "bbox": roi["bbox"],
                    "roi_id": roi["roi_id"],
                    "roi_idx": roi_idx
                }
            })

    if points:
        client.upsert(collection_name="roi_embeddings", points=points)


    return {
        "frames_processed": len(frames),
        "rois_stored": len(points)
    }
