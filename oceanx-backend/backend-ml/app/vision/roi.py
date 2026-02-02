# backend-ml/app/vision/roi.py
from ultralytics import YOLO
import os
import uuid
import torch
from torchvision.ops import nms
from PIL import Image
from pathlib import Path

YOLO_MODEL_A = Path(__file__).resolve().parent.parent.parent / "models/benthic_object_detector.pt"
YOLO_MODEL_B = Path(__file__).resolve().parent.parent.parent / "models/midwater_object_detector.pt"
CONF_THRESHOLD = 0.01   # as low as YOLO allows reliably
IOU_THRESHOLD = 0.9     # very permissive NMS inside YOLO
NMS_IOU_THRESH = 0.5
MIN_BOX_AREA = 32 * 32
yolo_model_1 = YOLO(YOLO_MODEL_A)
yolo_model_2 = YOLO(YOLO_MODEL_B)

def detect_rois(image: Image.Image, frame_id: int):
    # Dummy ROI: full image

    """
    Detect ROIs in a single frame using two YOLO models + NMS.

    Returns:
        List of dicts:
            - 'frame_idx': int
            - 'bbox': [x1, y1, x2, y2]
            - 'roi_id': str
    """
    if yolo_model_1 is None or yolo_model_2 is None:
        # Fallback: return full-frame ROI
        w, h = image.size
        return [{
            "frame_idx": frame_id,
            "bbox": [0, 0, w, h],
            "roi_id": f"{frame_id}_{uuid.uuid4()}"
        }]

    # Run YOLO models
    r1 = yolo_model_1(image, conf=CONF_THRESHOLD, iou=IOU_THRESHOLD)[0]
    r2 = yolo_model_2(image, conf=CONF_THRESHOLD, iou=IOU_THRESHOLD)[0]

    if len(r1.boxes) == 0 and len(r2.boxes) == 0:
        return []

    # Combine boxes and scores
    boxes = torch.cat([
        r1.boxes.xyxy.cpu() if len(r1.boxes) else torch.empty((0, 4)),
        r2.boxes.xyxy.cpu() if len(r2.boxes) else torch.empty((0, 4))
    ])
    scores = torch.cat([
        r1.boxes.conf.cpu() if len(r1.boxes) else torch.empty((0,)),
        r2.boxes.conf.cpu() if len(r2.boxes) else torch.empty((0,))
    ])

    keep = nms(boxes, scores, NMS_IOU_THRESH)
    boxes = boxes[keep]

    roi_records = []
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.tolist())
        roi_records.append({
            "frame_idx": frame_id,
            "bbox": [x1, y1, x2, y2],
            "roi_id": f"{frame_id}_{uuid.uuid4()}"
        })

    return roi_records


def detect_rois_batch(images: list, frame_ids: list):
    """
    Detect ROIs in multiple frames using batch processing.
    
    Args:
        images: List of PIL Images
        frame_ids: List of frame indices corresponding to each image
    
    Returns:
        List of lists: roi_records for each frame
    """
    if yolo_model_1 is None or yolo_model_2 is None:
        return [detect_rois(img, fid) for img, fid in zip(images, frame_ids)]
    
    # Batch detection
    r1_results = yolo_model_1(images, conf=CONF_THRESHOLD, iou=IOU_THRESHOLD)
    r2_results = yolo_model_2(images, conf=CONF_THRESHOLD, iou=IOU_THRESHOLD)
    
    batch_roi_records = []
    
    for idx, (frame_id, r1, r2) in enumerate(zip(frame_ids, r1_results, r2_results)):
        if len(r1.boxes) == 0 and len(r2.boxes) == 0:
            batch_roi_records.append([])
            continue
        
        # Combine boxes and scores
        boxes = torch.cat([
            r1.boxes.xyxy.cpu() if len(r1.boxes) else torch.empty((0, 4)),
            r2.boxes.xyxy.cpu() if len(r2.boxes) else torch.empty((0, 4))
        ])
        scores = torch.cat([
            r1.boxes.conf.cpu() if len(r1.boxes) else torch.empty((0,)),
            r2.boxes.conf.cpu() if len(r2.boxes) else torch.empty((0,))
        ])
        
        keep = nms(boxes, scores, NMS_IOU_THRESH)
        boxes = boxes[keep]
        
        roi_records = []
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.tolist())
            roi_records.append({
                "frame_idx": frame_id,
                "bbox": [x1, y1, x2, y2],
                "roi_id": f"{frame_id}_{uuid.uuid4()}"
            })
        
        batch_roi_records.append(roi_records)
    
    return batch_roi_records
