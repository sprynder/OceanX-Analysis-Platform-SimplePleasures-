from PIL import Image
from app.vision.embedding import embed, EMBEDDING_DIM
from app.storage.qdrant import client, init_collection
from app.messaging.kafka_consumer import run_consumer
from app.messaging.kafka_producer import produce
from app.messaging.topics import ROI_DETECTED, ROI_EMBEDDED


init_collection(EMBEDDING_DIM)


def handle_roi(event):
    img = Image.open(event["roi_path"])
    vector = embed(img)

    client.upsert(
        collection_name="roi_embeddings",
        points=[{
            "id": event["roi_id"],
            "vector": vector,
            "payload": event
        }]
    )

    produce(ROI_EMBEDDED, {
        "video_id": event["video_id"],
        "roi_id": event["roi_id"]
    })


if __name__ == "__main__":
    run_consumer(ROI_DETECTED, "embedder", handle_roi)
