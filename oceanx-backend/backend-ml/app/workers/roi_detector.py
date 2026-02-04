from PIL import Image
import os
import uuid
from app.vision.roi import detect_rois
from app.messaging.kafka_consumer import run_consumer
from app.messaging.kafka_producer import produce
from app.messaging.topics import FRAME_SAMPLED, ROI_DETECTED
from app.config import ROI_DIR


def handle_frame(event):
    image = Image.open(event["frame_path"])
    rois = detect_rois(image, event["frame_index"])

    video_id = event["video_id"]

    roi_dir = os.path.join(ROI_DIR, video_id)
    os.makedirs(roi_dir, exist_ok=True)

    for roi in rois:
        x1, y1, x2, y2 = roi["bbox"]

        roi_id = str(uuid.uuid4())
        roi_crop = image.crop((x1, y1, x2, y2))

        roi_path = os.path.join(roi_dir, f"{roi_id}.jpg")
        roi_crop.save(roi_path)

        produce(ROI_DETECTED, {
            "video_id": video_id,
            "frame_id": event["frame_id"],
            "roi_id": roi_id,
            "bbox": roi["bbox"],
            "roi_path": roi_path
        })


if __name__ == "__main__":
    run_consumer(FRAME_SAMPLED, "roi-detector", handle_frame)
