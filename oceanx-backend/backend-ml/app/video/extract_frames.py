# backend-ml/app/video/extract_frames.py
from PIL import Image
import cv2
import tempfile
from fastapi import UploadFile

def extract_frames(video_path: str, every_seconds: float = 1.0):
    """
    Extract frames from a video file uploaded via FastAPI.

    Args:
        file (UploadFile): FastAPI uploaded video file
        every_seconds (float): Sample a frame every N seconds

    Returns:
        List[PIL.Image.Image]: List of sampled frames as PIL Images
    """
    # Open video
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 30  # fallback to 30 fps if metadata missing
    stride = max(int(fps * every_seconds), 1)

    frames = []
    frame_idx = 0
    sample_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % stride == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(rgb))
            sample_idx += 1

        frame_idx += 1

    cap.release()


    return frames