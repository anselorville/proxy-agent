"""Celery configuration and task definitions."""

from celery import Celery

from src.core.settings import settings

# Create Celery app
celery_app = Celery(
    "china_stock_proxy",
    broker=settings.redis_url,
    backend=settings.redis_url,
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

if settings.is_test:
    celery_app.conf.broker_url = "memory://"
    celery_app.conf.result_backend = "cache+memory://"
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@celery_app.task(name="health_check")
def health_check():
    """Simple health check task."""
    return "Celery worker is healthy"


# Import tasks
from src.tasks import scheduled_tasks  # noqa
