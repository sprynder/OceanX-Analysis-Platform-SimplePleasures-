import numpy as np
from app.messaging.kafka_consumer import run_consumer
from app.messaging.kafka_producer import produce
from app.messaging.topics import VIDEO_CLUSTER_REQUESTED, VIDEO_CLUSTERED
from app.storage.qdrant import client
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from app.vision.clustering import cluster_embeddings
from app.config import COLLECTION_NAME


def handle_cluster(event):
    video_id = event["video_id"]

    search = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[FieldCondition(key="video_id", match=MatchValue(value=video_id))]
        ),
        limit=10000,
        with_vectors=True,
        with_payload=True
    )

    points, _ = search

    embeddings = [p.vector for p in points]
    roi_ids = [p.payload["roi_id"] for p in points]

    labels = cluster_embeddings(np.array(embeddings))

    produce(VIDEO_CLUSTERED, {
        "video_id": video_id,
        "clusters": [
            {"roi_id": r, "cluster_id": int(l)}
            for r, l in zip(roi_ids, labels)
        ]
    })


if __name__ == "__main__":
    run_consumer(VIDEO_CLUSTER_REQUESTED, "clusterer", handle_cluster)
