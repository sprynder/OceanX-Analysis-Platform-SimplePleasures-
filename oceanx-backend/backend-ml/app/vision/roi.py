# backend-ml/app/vision/roi.py
from ultralytics import YOLO
import os
import uuid
import torch
from torchvision.ops import nms
from PIL import Image
from pathlib import Path
import numpy as np

YOLO_MODEL_A = Path(__file__).resolve().parent.parent.parent / "models/benthic_object_detector.pt"
YOLO_MODEL_B = Path(__file__).resolve().parent.parent.parent / "models/midwater_object_detector.pt"
YOLO_MODEL_A_ONNX = Path(__file__).resolve().parent.parent.parent / "models/benthic_object_detector.onnx"
YOLO_MODEL_B_ONNX = Path(__file__).resolve().parent.parent.parent / "models/midwater_object_detector.onnx"

CONF_THRESHOLD = 0.01   # as low as YOLO allows reliably
IOU_THRESHOLD = 0.9     # very permissive NMS inside YOLO
NMS_IOU_THRESH = 0.5
MIN_BOX_AREA = 32 * 32

# Try to use ONNX models first, fallback to PyTorch
try:
    import onnxruntime as ort
    USE_ONNX = True
    print("Using ONNX Runtime for YOLO inference")
    
    # Export models to ONNX if they don't exist
    if not YOLO_MODEL_A_ONNX.exists():
        print("Exporting benthic model to ONNX...")
        model_temp = YOLO(YOLO_MODEL_A)
        model_temp.export(format="onnx", imgsz=640, simplify=True)
        
    if not YOLO_MODEL_B_ONNX.exists():
        print("Exporting midwater model to ONNX...")
        model_temp = YOLO(YOLO_MODEL_B)
        model_temp.export(format="onnx", imgsz=640, simplify=True)
    
    # Load ONNX models with CPU execution provider
    sess_options = ort.SessionOptions()
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    
    yolo_session_1 = ort.InferenceSession(
        str(YOLO_MODEL_A_ONNX),
        sess_options,
        providers=['CPUExecutionProvider']
    )
    yolo_session_2 = ort.InferenceSession(
        str(YOLO_MODEL_B_ONNX),
        sess_options,
        providers=['CPUExecutionProvider']
    )
    yolo_model_1 = None
    yolo_model_2 = None
    
except ImportError:
    print("ONNX Runtime not available, using PyTorch")
    USE_ONNX = False
    yolo_model_1 = YOLO(YOLO_MODEL_A)
    yolo_model_2 = YOLO(YOLO_MODEL_B)
    yolo_session_1 = None
    yolo_session_2 = None


def preprocess_for_onnx(image: Image.Image, input_size=640):
    """Preprocess PIL image for ONNX YOLO model"""
    # Resize and pad to square
    img = image.convert('RGB')
    img = img.resize((input_size, input_size))
    
    # Convert to numpy and normalize
    img_np = np.array(img).astype(np.float32) / 255.0
    
    # HWC to CHW
    img_np = img_np.transpose(2, 0, 1)
    
    # Add batch dimension
    img_np = np.expand_dims(img_np, axis=0)
    
    return img_np


def postprocess_onnx_output(output, conf_threshold=0.01):
    """Extract boxes and scores from ONNX output"""
    # YOLO ONNX output shape: [batch, 84, 8400] or similar
    # First 4 are bbox coords, rest are class scores
    predictions = output[0]  # Remove batch dimension
    
    boxes = []
    scores = []
    
    # Transpose if needed: [84, 8400] -> [8400, 84]
    if predictions.shape[0] < predictions.shape[1]:
        predictions = predictions.T
    
    for pred in predictions:
        # pred[0:4] = bbox (xywh format), pred[4:] = class scores
        class_scores = pred[4:]
        max_score = np.max(class_scores)
        
        if max_score > conf_threshold:
            # Convert xywh to xyxy
            x, y, w, h = pred[0:4]
            x1 = x - w / 2
            y1 = y - h / 2
            x2 = x + w / 2
            y2 = y + h / 2
            
            boxes.append([x1, y1, x2, y2])
            scores.append(max_score)
    
    return torch.tensor(boxes), torch.tensor(scores)


def detect_rois(image: Image.Image, frame_id: int):
    """
    Detect ROIs in a single frame using two YOLO models + NMS.
    Uses ONNX Runtime if available, otherwise PyTorch.

    Returns:
        List of dicts:
            - 'frame_idx': int
            - 'bbox': [x1, y1, x2, y2]
            - 'roi_id': str
    """
    
    if USE_ONNX:
        # ONNX inference
        img_input = preprocess_for_onnx(image)
        
        # Run both models
        input_name_1 = yolo_session_1.get_inputs()[0].name
        input_name_2 = yolo_session_2.get_inputs()[0].name
        
        output_1 = yolo_session_1.run(None, {input_name_1: img_input})[0]
        output_2 = yolo_session_2.run(None, {input_name_2: img_input})[0]
        
        boxes_1, scores_1 = postprocess_onnx_output(output_1, CONF_THRESHOLD)
        boxes_2, scores_2 = postprocess_onnx_output(output_2, CONF_THRESHOLD)
        
        if len(boxes_1) == 0 and len(boxes_2) == 0:
            return []
        
        # Combine boxes
        boxes = torch.cat([boxes_1, boxes_2]) if len(boxes_1) > 0 and len(boxes_2) > 0 else (boxes_1 if len(boxes_1) > 0 else boxes_2)
        scores = torch.cat([scores_1, scores_2]) if len(scores_1) > 0 and len(scores_2) > 0 else (scores_1 if len(scores_1) > 0 else scores_2)
        
    else:
        # PyTorch inference (original code)
        if yolo_model_1 is None or yolo_model_2 is None:
            w, h = image.size
            return [{
                "frame_idx": frame_id,
                "bbox": [0, 0, w, h],
                "roi_id": f"{frame_id}_{uuid.uuid4()}"
            }]

        r1 = yolo_model_1(image, conf=CONF_THRESHOLD, iou=IOU_THRESHOLD)[0]
        r2 = yolo_model_2(image, conf=CONF_THRESHOLD, iou=IOU_THRESHOLD)[0]

        if len(r1.boxes) == 0 and len(r2.boxes) == 0:
            return []

        boxes = torch.cat([
            r1.boxes.xyxy.cpu() if len(r1.boxes) else torch.empty((0, 4)),
            r2.boxes.xyxy.cpu() if len(r2.boxes) else torch.empty((0, 4))
        ])
        scores = torch.cat([
            r1.boxes.conf.cpu() if len(r1.boxes) else torch.empty((0,)),
            r2.boxes.conf.cpu() if len(r2.boxes) else torch.empty((0,))
        ])

    # Apply NMS
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
