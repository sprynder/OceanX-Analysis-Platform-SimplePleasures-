import json
import os
from confluent_kafka import Consumer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")


def run_consumer(topic: str, group_id: str, handler):
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": group_id,
        "auto.offset.reset": "earliest"
    })

    consumer.subscribe([topic])

    print(f"Listening on topic: {topic}")

    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue

        if msg.error():
            print(msg.error())
            continue

        try:
            event = json.loads(msg.value().decode())
            handler(event)
        except Exception as e:
            print(f"Worker error: {e}")
