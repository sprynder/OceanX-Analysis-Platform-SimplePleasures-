import base64
import io
from fastapi import APIRouter, HTTPException
from PIL import Image
from app.schemas.schemas import SearchROIsRequest, SearchROIsResponse, SearchROIResult, ImageSearchROIsRequest
from app.vision.embedding import embed_text, embed
from app.storage.qdrant import search_similar
from app.vision.dedup import deduplicate

router = APIRouter()


@router.post("/search-rois", response_model=SearchROIsResponse)
def search_rois(request: SearchROIsRequest):
    query_vector = embed_text(request.query)
    return _run_vector_search(
        query_vector=query_vector,
        video_id=request.video_id,
        top_k=request.top_k,
        dedup_enabled=request.dedup_enabled,
        tau_time=request.tau_time,
        tau_iou=request.tau_iou,
        tau_emb=request.tau_emb,
    )


def _run_vector_search(
    query_vector,
    video_id,
    top_k: int,
    dedup_enabled: bool,
    tau_time: float,
    tau_iou: float,
    tau_emb: float,
) -> SearchROIsResponse:
    """Shared logic for text and image vector searches."""
    raw_results = search_similar(query_vector, video_id, top_k=50)
    raw_count = len(raw_results)

    candidates = []
    for r in raw_results:
        raw_vec = r.vector
        if isinstance(raw_vec, dict):
            raw_vec = next(iter(raw_vec.values()))
        candidates.append({
            "roi_id":        r.payload["roi_id"],
            "timestamp_sec": r.payload["timestamp_sec"],
            "bbox":          r.payload["bbox"],
            "frame_idx":     r.payload["frame_idx"],
            "video_id":      r.payload["video_id"],
            "vector":        raw_vec,
            "score":         r.score,
        })

    if dedup_enabled:
        candidates = deduplicate(candidates, tau_time=tau_time, tau_iou=tau_iou, tau_emb=tau_emb)

    results = [
        SearchROIResult(
            roi_id=c["roi_id"],
            score=round(c["score"], 4),
            timestamp_sec=c["timestamp_sec"],
            bbox=c["bbox"],
            frame_idx=c["frame_idx"],
            video_id=c["video_id"],
            roi_url=f"/rois/{c['video_id']}/{c['roi_id']}.jpg",
        )
        for c in candidates[:top_k]
    ]

    return SearchROIsResponse(video_id=video_id, results=results, raw_count=raw_count)


@router.post("/search-rois-by-image", response_model=SearchROIsResponse)
def search_rois_by_image(request: ImageSearchROIsRequest):
    # Decode base64 → PIL Image → BioCLIP embedding
    try:
        img_bytes = base64.b64decode(request.image_b64)
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")

    query_vector = embed(image)

    return _run_vector_search(
        query_vector=query_vector,
        video_id=request.video_id,
        top_k=request.top_k,
        dedup_enabled=request.dedup_enabled,
        tau_time=request.tau_time,
        tau_iou=request.tau_iou,
        tau_emb=request.tau_emb,
    )
