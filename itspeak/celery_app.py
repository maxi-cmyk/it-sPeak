"""Celery application factory (Redis broker + result backend)."""

from __future__ import annotations

from celery import Celery

from .settings import get_settings

_settings = get_settings()

celery_app = Celery(
    "itspeak",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=["itspeak.pipeline"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_track_started=True,
    # CPU-bound MediaPipe work: prefer a small prefetch so long jobs don't
    # starve others, and let the OS threads (not processes) parallelise inside
    # a task.
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
