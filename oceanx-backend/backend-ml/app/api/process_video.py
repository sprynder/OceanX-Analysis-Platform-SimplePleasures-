# backend-ml/app/api/process_video.py
import os
from fastapi import APIRouter, HTTPException
from app.schemas.schemas import ProcessVideoRequest
from app.tasks.video_tasks import process_video_task

router = APIRouter(prefix="/process-video")

@router.post("")
async def process_video(request: ProcessVideoRequest, every_seconds: float = 0.5):
    video_path = request.video_path
    video_id = request.video_id

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")

    task = process_video_task.delay(video_id, video_path, every_seconds)
    return {"task_id": task.id, "status": "queued"}
