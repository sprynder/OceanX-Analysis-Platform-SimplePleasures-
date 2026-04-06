import numpy as np
from typing import List, Dict, Any


def compute_iou(bbox_a: List[float], bbox_b: List[float]) -> float:
    """
    Compute Intersection over Union for two bounding boxes.
    bbox format: [x1, y1, x2, y2]
    """
    x1 = max(bbox_a[0], bbox_b[0])
    y1 = max(bbox_a[1], bbox_b[1])
    x2 = min(bbox_a[2], bbox_b[2])
    y2 = min(bbox_a[3], bbox_b[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (bbox_a[2] - bbox_a[0]) * (bbox_a[3] - bbox_a[1])
    area_b = (bbox_b[2] - bbox_b[0]) * (bbox_b[3] - bbox_b[1])
    union = area_a + area_b - intersection

    return intersection / union if union > 0 else 0.0


def deduplicate(
    candidates: List[Dict[str, Any]],
    tau_time: float = 2.0,
    tau_iou: float = 0.3,
    tau_emb: float = 0.85,
) -> List[Dict[str, Any]]:
    """
    Greedy deduplication pass. Candidates are already sorted by Qdrant score
    (highest first), so we always keep the better-scoring result when suppressing.

    A candidate is suppressed only if ALL THREE gates fire against any accepted result:
      - temporal:  |Δt| < tau_time  (same burst of frames)
      - spatial:   IoU  > tau_iou   (same region of the frame)
      - embedding: cosine_sim > tau_emb  (same visual appearance)
    """
    accepted = []

    for candidate in candidates:
        suppress = False

        for accepted_result in accepted:
            dt = abs(candidate["timestamp_sec"] - accepted_result["timestamp_sec"])
            iou = compute_iou(candidate["bbox"], accepted_result["bbox"])

            # Embeddings are L2-normalized, so dot product == cosine similarity
            # Convert to numpy array in case Qdrant returned a plain list
            v1 = np.asarray(candidate["vector"], dtype=np.float32)
            v2 = np.asarray(accepted_result["vector"], dtype=np.float32)
            emb_sim = float(np.dot(v1, v2))

            if dt < tau_time and iou > tau_iou and emb_sim > tau_emb:
                suppress = True
                break

        if not suppress:
            accepted.append(candidate)

    return accepted
