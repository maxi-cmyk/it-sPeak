"""Lightweight Celery dispatch helpers shared by FastAPI and worker tasks.

Keeping these helpers outside ``jobs`` prevents the API process from importing
MediaPipe, Librosa, NumPy analysis code, and OpenAI clients merely to enqueue a
task.
"""

from __future__ import annotations

from .artifact_store import update_manifest
from .celery_app import celery_app
from .persistence import get_persistence


def enqueue_quality_check(session_id: str):
    result = celery_app.send_task("itspeak.quality_check", args=[session_id])
    get_persistence().update_session(session_id, {"task_id": result.id})
    return result


def enqueue_analysis(session_id: str):
    result = celery_app.send_task("itspeak.analyze_session", args=[session_id])
    update_manifest(
        session_id,
        status="queued",
        stage="Waiting for full analysis",
        analysis_task_id=result.id,
    )
    get_persistence().update_session(
        session_id,
        {
            "status": "queued",
            "stage": "Waiting for full analysis",
            "task_id": result.id,
        },
    )
    return result
