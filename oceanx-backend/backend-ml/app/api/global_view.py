import numpy as np
import umap
import hdbscan
from sklearn.decomposition import PCA
from fastapi import APIRouter, HTTPException
from app.storage.qdrant import scroll_all_with_vectors
from app.schemas.schemas import GlobalUMAPResponse, GlobalROI

router = APIRouter()


@router.post("/global-umap", response_model=GlobalUMAPResponse)
def global_umap():
    """
    Compute a single UMAP projection across ALL vectors in Qdrant (all videos).
    Uses fine-grained HDBSCAN (min_cluster_size=3) to surface species-level clusters
    rather than the coarser per-video clustering.
    """
    points = scroll_all_with_vectors()

    if not points:
        raise HTTPException(status_code=404, detail="No ROIs found in the database")

    embeddings = []
    payloads = []
    for p in points:
        vec = p.vector
        if isinstance(vec, dict):
            vec = next(iter(vec.values()))
        embeddings.append(vec)
        payloads.append(p.payload)

    embeddings = np.array(embeddings, dtype=np.float32)
    n = len(embeddings)

    # PCA dimensionality reduction (BioCLIP: 768D → 50D)
    pca_dim = min(50, n, embeddings.shape[1])
    embeddings_reduced = PCA(n_components=pca_dim).fit_transform(embeddings)

    # Fine-grained species-level clustering:
    # - min_cluster_size=3: detect clusters with as few as 3 similar ROIs
    # - min_samples=1: allow borderline points to join clusters rather than be noise
    # - cluster_selection_method='eom': excess-of-mass preserves small dense clusters
    #   without the over-fragmentation of 'leaf' mode
    # - No max_cluster_size cap so a truly dominant species can form one large cluster
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=3,
        min_samples=1,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    cluster_labels = clusterer.fit_predict(embeddings_reduced).tolist()

    # 3D UMAP — lower n_neighbors + min_dist to reveal tight species groupings
    n_neighbors = min(15, n - 1)
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
