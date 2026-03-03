# backend-ml/app/tasks.py
import asyncio
import threading
from queue import Queue
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

# Simple in-memory task queue for background processing
task_queue: Queue = Queue()

def process_video_task(
    video_id: str,
    video_path: str,
    on_complete: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
):
    """Wrapper to queue a video processing task"""
    task_queue.put({
        'type': 'process_video',
        'video_id': video_id,
        'video_path': video_path,
        'on_complete': on_complete,
        'on_error': on_error,
    })
    logger.info(f"[Tasks] Queued video processing for {video_id}")


def start_task_worker():
    """
    Start a background worker thread that processes queued tasks.
    Call this once during app startup.
    """
    def worker():
        from app.api.process_video import process_video_sync
        
        logger.info("[Tasks] Worker thread started")
        while True:
            try:
                task = task_queue.get(timeout=1)
                
                if task['type'] == 'process_video':
                    video_id = task['video_id']
                    video_path = task['video_path']
                    
                    logger.info(f"[Tasks] Processing queued task for {video_id}")
                    try:
                        process_video_sync(video_id, video_path)
                        logger.info(f"[Tasks] Completed task for {video_id}")
                        if task.get('on_complete'):
                            task['on_complete'](video_id)
                    except Exception as e:
                        logger.error(f"[Tasks] Error processing {video_id}: {e}")
                        if task.get('on_error'):
                            task['on_error'](video_id, str(e))
                
                task_queue.task_done()
            except Exception as e:
                # timeout or other error, continue
                continue
    
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    logger.info("[Tasks] Background worker thread started")
    return worker_thread
