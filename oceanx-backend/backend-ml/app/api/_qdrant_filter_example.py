# Example for QdrantClient scroll filter usage
from qdrant_client.http.models import Filter, FieldCondition, Match

# Example: filter for video_id = 'abc123'
f = Filter(must=[FieldCondition(key="video_id", match=Match(value="abc123"))])

# Usage:
# client.scroll(collection_name="roi_embeddings", scroll_filter=f, limit=10000)
