"""
Celery app instance. Run the worker with:

    celery -A app.workers.celery_app worker --loglevel=info

Requires Redis (or another broker) reachable at CELERY_BROKER_URL.
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "reposage",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_time_limit=settings.ANALYSIS_TASK_TIMEOUT_SECONDS,
    task_soft_time_limit=settings.ANALYSIS_TASK_TIMEOUT_SECONDS - 30,
)

celery_app.autodiscover_tasks(["app.workers"])
