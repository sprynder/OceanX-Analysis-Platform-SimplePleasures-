import os
from celery import Celery

# Get Redis URL from environment, default to docker compose service name
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Create Celery app
celery_app = Celery(
    "oceanx_ml",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=29 * 60,  # 29 minutes soft limit
    worker_prefetch_multiplier=1,  # Task-by-task processing
)

# Auto-discover tasks from app.tasks module

celery_app.autodiscover_tasks(["app.tasks"])

@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery connection"""
    print(f"Request: {self.request!r}")
