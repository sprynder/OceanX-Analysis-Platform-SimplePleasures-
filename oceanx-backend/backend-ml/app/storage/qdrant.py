# backend-ml/app/storage/qdrant.py
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, Filter, FieldCondition, MatchValue
from app.config import QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

def init_collection(vector_size: int):
    collections = client.get_collections().collections
    if COLLECTION_NAME not in [c.name for c in collections]:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )


def search_similar(query_vector, video_id: str = None, top_k: int = 50):
    video_filter = None
    if video_id:
        video_filter = Filter(
            must=[FieldCondition(key="video_id", match=MatchValue(value=video_id))]
        )

    # Use query_points (modern API, qdrant-client 1.7+)
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector.tolist(),
        query_filter=video_filter,
        limit=top_k,
        with_payload=True,
        with_vectors=True,
    )

    return response.points


def scroll_all():
    """Scroll through ALL points in the collection, across all videos."""
    all_points = []
    offset = None

    while True:
        result, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            offset=offset,
            with_payload=True,
            with_vectors=False,   # not needed for global UMAP — embeddings fetched separately
        )
        all_points.extend(result)
        if next_offset is None:
            break
        offset = next_offset

    return all_points


def scroll_all_with_vectors():
    """Scroll through ALL points returning vectors (needed for global UMAP)."""
    all_points = []
    offset = None

    while True:
        result, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=500,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        all_points.extend(result)
        if next_offset is None:
            break
        offset = next_offset

    return all_points
