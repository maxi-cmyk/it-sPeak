"""Filesystem-backed, access-controlled temporary session artifacts."""

from __future__ import annotations

import gzip
import hashlib
import hmac
import json
import secrets
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from .settings import get_settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _root() -> Path:
    root = Path(get_settings().artifact_dir).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def _safe_id(session_id: str) -> str:
    return str(UUID(session_id))


def session_dir(session_id: str) -> Path:
    path = (_root() / _safe_id(session_id)).resolve()
    if path.parent != _root():
        raise ValueError("Invalid session path")
    return path


def create_session(metadata: dict[str, Any]) -> tuple[dict[str, Any], str]:
    session_id = str(uuid4())
    token = secrets.token_urlsafe(32)
    created = _now()
    directory = session_dir(session_id)
    directory.mkdir(mode=0o700)
    manifest = {
        "session_id": session_id,
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "created_at": created.isoformat(),
        "expires_at": (created + timedelta(seconds=get_settings().artifact_retention_seconds)).isoformat(),
        "status": "quality_check",
        "stage": "Checking recording quality",
        **metadata,
    }
    write_manifest(session_id, manifest)
    return manifest, token


def manifest_path(session_id: str) -> Path:
    return session_dir(session_id) / "manifest.json"


def read_manifest(session_id: str) -> dict[str, Any]:
    with manifest_path(session_id).open(encoding="utf-8") as source:
        return json.load(source)


def write_manifest(session_id: str, manifest: dict[str, Any]) -> None:
    path = manifest_path(session_id)
    temp = path.with_name(f".{uuid4().hex}.tmp")
    temp.write_text(json.dumps(manifest, separators=(",", ":")), encoding="utf-8")
    temp.replace(path)


def update_manifest(session_id: str, **changes: Any) -> dict[str, Any]:
    manifest = read_manifest(session_id)
    manifest.update(changes)
    write_manifest(session_id, manifest)
    return manifest


def authorize(session_id: str, token: str | None) -> dict[str, Any]:
    if not token:
        raise PermissionError("Missing session access token")
    manifest = read_manifest(session_id)
    supplied = hashlib.sha256(token.encode()).hexdigest()
    if not hmac.compare_digest(supplied, manifest["token_hash"]):
        raise PermissionError("Invalid session access token")
    if datetime.fromisoformat(manifest["expires_at"]) <= _now():
        raise FileNotFoundError("Session expired")
    return manifest


def video_path(session_id: str, filename: str | None = None) -> Path:
    directory = session_dir(session_id)
    if filename:
        candidate = (directory / Path(filename).name).resolve()
        if candidate.parent != directory:
            raise ValueError("Invalid video path")
        return candidate
    manifest = read_manifest(session_id)
    return video_path(session_id, manifest["video_filename"])


def landmarks_path(session_id: str) -> Path:
    return session_dir(session_id) / "landmarks.v1.json.gz"


def write_landmarks(session_id: str, payload: dict[str, Any]) -> None:
    target = landmarks_path(session_id)
    with gzip.open(target, "wt", encoding="utf-8", compresslevel=6) as output:
        json.dump(payload, output, separators=(",", ":"))


def cleanup_expired(now: datetime | None = None) -> int:
    current = now or _now()
    removed = 0
    for directory in _root().iterdir():
        if not directory.is_dir():
            continue
        try:
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
            expired = datetime.fromisoformat(manifest["expires_at"]) <= current
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            expired = datetime.fromtimestamp(directory.stat().st_mtime, timezone.utc) + timedelta(seconds=get_settings().artifact_retention_seconds) <= current
        if expired:
            shutil.rmtree(directory, ignore_errors=True)
            removed += 1
    return removed
