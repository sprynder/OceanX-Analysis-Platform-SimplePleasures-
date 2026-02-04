import json
from confluent_kafka import Producer
import os

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")

producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})


def produce(topic: str, value: dict):
    producer.produce(topic, json.dumps(value).encode("utf-8"))
    producer.poll(0)


def flush():
    producer.flush()
