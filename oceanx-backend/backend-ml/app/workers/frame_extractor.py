import os
import uuid
from PIL import Image
from app.video.extract_frames import extract_frames
from app.messaging.kafka_consumer import run_consumer
from app.messaging.kafka_producer import produce
from app.messaging.topics import VIDEO_UPLOADED, FRAME_SAMPLED
from app.config import ROI_DIR


def handle_video_uploaded(event):
    video_id = event["video_id"]
    video_path = event["video_path"]
    every_seconds = event.get("every_seconds", 0.5)

    frames = extract_frames(video_path, every_seconds)

    frame_dir = os.path.join("/data/frames", video_id)
    os.makedirs(frame_dir, exist_ok=True)

    for idx, frame in enumerate(frames):
        frame_id = str(uuid.uuid4())
        frame_path = os.path.join(frame_dir, f"{frame_id}.jpg")

        frame.save(frame_path)

        produce(FRAME_SAMPLED, {
            "video_id": video_id,
            "frame_id": frame_id,
            "frame_index": idx,
            "frame_path": frame_path,
            "timestamp_sec": idx * every_seconds
        })


if __name__ == "__main__":
    run_consumer(VIDEO_UPLOADED, "frame-extractor", handle_video_uploaded)
