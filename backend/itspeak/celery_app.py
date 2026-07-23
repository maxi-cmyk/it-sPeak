"""Celery application factory (Redis broker + result backend)."""

from __future__ import annotations

from celery import Celery

from .settings import get_settings

_settings = get_settings()

celery_app = Celery(
    "itspeak",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=["itspeak.jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=_settings.artifact_retention_seconds,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        # Redis returns an unacknowledged analysis job to the queue if a
        # worker disappears during a normal deployment restart.
        "visibility_timeout": max(_settings.artifact_retention_seconds, 3600),
    },
    # CPU-bound MediaPipe work: prefer a small prefetch so long jobs don't
    # starve others, and let the OS threads (not processes) parallelise inside
    # a task.
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "cleanup-expired-session-artifacts": {
            "task": "itspeak.cleanup_expired",
            "schedule": _settings.cleanup_interval_seconds,
        }
    },
)
