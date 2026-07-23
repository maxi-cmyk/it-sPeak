"""Fail-fast checks for the production container."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from .settings import Settings, get_settings


def production_configuration_errors(settings: Settings) -> list[str]:
    if settings.environment.lower() != "production":
        return []

    errors: list[str] = []
    redis_host = (urlparse(settings.redis_url).hostname or "").lower()
    frontend_host = (urlparse(settings.frontend_origin).hostname or "").lower()
    configured_artifact_dir = Path(settings.artifact_dir)
    artifact_dir = configured_artifact_dir.resolve()

    if redis_host in {"", "localhost", "127.0.0.1"}:
        errors.append("ITSPEAK_REDIS_URL must point to the managed Redis service")
    if frontend_host in {"", "localhost", "127.0.0.1"}:
        errors.append("ITSPEAK_FRONTEND_ORIGIN must be the deployed frontend origin")
    if not settings.clerk_secret_key:
        errors.append("CLERK_SECRET_KEY is required")
    if not settings.supabase_url:
        errors.append("ITSPEAK_SUPABASE_URL is required")
    if not settings.supabase_secret_key:
        errors.append("ITSPEAK_SUPABASE_SECRET_KEY is required")
    if not settings.openai_api_key:
        errors.append("ITSPEAK_OPENAI_API_KEY is required")
    if configured_artifact_dir == Path("/tmp/itspeak-sessions"):
        errors.append("ITSPEAK_ARTIFACT_DIR must use the mounted persistent volume")
    if not shutil.which(settings.ffmpeg_bin):
        errors.append(f"FFmpeg executable is unavailable: {settings.ffmpeg_bin}")
    if not shutil.which(settings.ffprobe_bin):
        errors.append(f"ffprobe executable is unavailable: {settings.ffprobe_bin}")

    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=artifact_dir):
            pass
    except OSError:
        errors.append(f"ITSPEAK_ARTIFACT_DIR is not writable: {artifact_dir}")

    concurrency = os.getenv("CELERY_WORKER_CONCURRENCY", "1")
    if not concurrency.isdigit() or int(concurrency) < 1:
        errors.append("CELERY_WORKER_CONCURRENCY must be a positive integer")

    return errors


def main() -> None:
    errors = production_configuration_errors(get_settings())
    if errors:
        formatted = "\n".join(f"- {error}" for error in errors)
        raise SystemExit(f"Production configuration is incomplete:\n{formatted}")
    print("Production configuration preflight passed.", flush=True)


if __name__ == "__main__":
    main()
