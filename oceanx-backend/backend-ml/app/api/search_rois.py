from fastapi import APIRouter
from app.schemas.schemas import SearchROIsRequest, SearchROIsResponse, SearchROIResult
from app.vision.embedding import embed_text
from app.storage.qdrant import search_similar
from app.vision.dedup import deduplicate

router = APIRouter()


@router.post("/search-rois", response_model=SearchROIsResponse)
def search_rois(request: SearchROIsRequest):
    # 1. Encode the text query into the same 768-dim space as the image embeddings
    query_vector = embed_text(request.query)

    # 2. ANN search — optionally scoped to a single video
    raw_results = search_similar(query_vector, request.video_id, top_k=50)
    raw_count = len(raw_results)

    # 3. Reshape Qdrant results into dicts the dedup function understands
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

    # 4. Greedy deduplication (skipped when dedup_enabled=False)
    if request.dedup_enabled:
        deduped = deduplicate(
            candidates,
            tau_time=request.tau_time,
            tau_iou=request.tau_iou,
            tau_emb=request.tau_emb,
        )
    else:
        deduped = candidates

    # 5. Trim to top_k and build response
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
        for c in deduped[: request.top_k]
    ]

    return SearchROIsResponse(
        video_id=request.video_id,
        results=results,
        raw_count=raw_count,
    )
