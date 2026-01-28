"""Celery configuration and task definitions."""

from celery import Celery
import os

# Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "china_stock_proxy",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.tasks.scheduled_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
)


@celery_app.task(name="health_check")
def health_check():
    """Simple health check task."""
    return "Celery worker is healthy"


# Import tasks
from src.tasks import scheduled_tasks  # noqa
