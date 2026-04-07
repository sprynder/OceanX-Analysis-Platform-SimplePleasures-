import numpy as np
import umap
import hdbscan
from collections import defaultdict
from sklearn.decomposition import PCA
from fastapi import APIRouter, HTTPException
from app.storage.qdrant import scroll_all_with_vectors
from app.schemas.schemas import GlobalUMAPRequest, GlobalUMAPResponse, GlobalROI
from app.vision.dedup import deduplicate

router = APIRouter()


@router.post("/global-umap", response_model=GlobalUMAPResponse)
def global_umap(request: GlobalUMAPRequest = GlobalUMAPRequest()):
    """
    Compute a single UMAP projection across ALL vectors in Qdrant (all videos).
    Uses fine-grained HDBSCAN (min_cluster_size=3) to surface species-level clusters
    rather than the coarser per-video clustering.
    """
    points = scroll_all_with_vectors()

    if not points:
        raise HTTPException(status_code=404, detail="No ROIs found in the database")

    embeddings_list = []
    payloads_list = []
    for p in points:
        vec = p.vector
        if isinstance(vec, dict):
            vec = next(iter(vec.values()))
        embeddings_list.append(vec)
        payloads_list.append(p.payload)

    if request.dedup_enabled:
        # Dedup within each video independently — timestamps are per-video so
        # cross-video temporal comparison is meaningless.
        by_video = defaultdict(list)
        for i, payload in enumerate(payloads_list):
            by_video[payload["video_id"]].append(i)

        kept_indices = []
        for vid_indices in by_video.values():
            candidates = [
                {
                    "id": payloads_list[i]["roi_id"],
                    "vector": embeddings_list[i],
                    "timestamp_sec": payloads_list[i]["timestamp_sec"],
                    "bbox": payloads_list[i]["bbox"],
                }
                for i in vid_indices
            ]
            kept = deduplicate(candidates, tau_time=request.tau_time,
                               tau_iou=request.tau_iou, tau_emb=request.tau_emb)
            kept_ids = {c["id"] for c in kept}
            kept_indices.extend(i for i in vid_indices if payloads_list[i]["roi_id"] in kept_ids)

        kept_indices.sort()
        embeddings_list = [embeddings_list[i] for i in kept_indices]
        payloads_list  = [payloads_list[i]  for i in kept_indices]
        print(f"[GlobalUMAP] Dedup: {len(points)} → {len(payloads_list)} ROIs")

    embeddings = np.array(embeddings_list, dtype=np.float32)
    payloads = payloads_list
    n = len(embeddings)

    if n < 4:
        raise HTTPException(status_code=400, detail=f"Need at least 4 ROIs to compute UMAP (found {n})")

    # PCA dimensionality reduction (BioCLIP: 768D → 50D)
    # n_components must be strictly less than min(n_samples, n_features)
    pca_dim = min(50, n - 1, embeddings.shape[1] - 1)
    embeddings_reduced = PCA(n_components=pca_dim).fit_transform(embeddings)

    # Fine-grained species-level clustering:
    # - min_cluster_size=3: detect clusters with as few as 3 similar ROIs
    # - min_samples=1: allow borderline points to join clusters rather than be noise
    # - cluster_selection_method='eom': excess-of-mass preserves small dense clusters
    #   without the over-fragmentation of 'leaf' mode
    # - No max_cluster_size cap so a truly dominant species can form one large cluster
    min_cs = min(3, n)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cs,
        min_samples=1,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    cluster_labels = clusterer.fit_predict(embeddings_reduced).tolist()

    # 3D UMAP — lower n_neighbors + min_dist to reveal tight species groupings
    n_neighbors = max(2, min(15, n - 1))
    reducer = umap.UMAP(
        n_components=3,
        n_neighbors=n_neighbors,
        min_dist=0.05,
        metric="euclidean",
        random_state=42,
    )
    coords = reducer.fit_transform(embeddings_reduced)   # (n, 3)

    rois = [
        GlobalROI(
            roi_id=payloads[i]["roi_id"],
            video_id=payloads[i]["video_id"],
            frame_idx=payloads[i]["frame_idx"],
            roi_url=f"/rois/{payloads[i]['video_id']}/{payloads[i]['roi_id']}.jpg",
            umap_x=float(coords[i, 0]),
            umap_y=float(coords[i, 1]),
            umap_z=float(coords[i, 2]),
            cluster=int(cluster_labels[i]),
        )
        for i in range(n)
    ]

    video_ids = {p["video_id"] for p in payloads}
    n_clusters = len(set(cluster_labels) - {-1})
    print(f"[GlobalUMAP] {n} ROIs, {n_clusters} clusters, {cluster_labels.count(-1)} noise points")

    return GlobalUMAPResponse(
        rois=rois,
        video_count=len(video_ids),
        roi_count=n,
    )
