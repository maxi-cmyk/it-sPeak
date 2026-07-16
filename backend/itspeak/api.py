"""FastAPI surface for gated sessions and secured temporary artifacts."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from .archetypes import list_archetypes
from .artifact_store import authorize, create_session, landmarks_path, read_manifest, session_dir, update_manifest, video_path
from .jobs import _enqueue_analysis, quality_check_task
from .models import Archetype, CoachingReport, QualityGateReport, SessionAccepted, SessionStatus
from .settings import get_settings
from .uploads import save_session_video

settings = get_settings()
app = FastAPI(title="it'sPEAK API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"] , expose_headers=["Accept-Ranges", "Content-Range", "ETag"])


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _authorized(session_id: str, authorization: str | None, access_token: str | None = None):
    try:
        return authorize(session_id, _bearer(authorization) or access_token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc
    except (FileNotFoundError, OSError, ValueError):
        raise HTTPException(status_code=404, detail="Session not found or expired")


@app.post("/sessions", response_model=SessionAccepted, status_code=202)
async def create_analysis_session(
    file: UploadFile = File(...), project_id: str = Form(...),
    archetype: Archetype = Form(Archetype.CORPORATE_BOARD), audience_context: str = Form(""),
) -> SessionAccepted:
    manifest, token = create_session({"project_id": project_id, "archetype": archetype.value, "audience_context": audience_context[:300]})
    try:
        path = await save_session_video(manifest["session_id"], file)
        update_manifest(manifest["session_id"], video_filename=path.name)
        quality_check_task.delay(manifest["session_id"])
    except Exception:
        shutil.rmtree(session_dir(manifest["session_id"]), ignore_errors=True)
        raise
    return SessionAccepted(session_id=manifest["session_id"], access_token=token, project_id=project_id, expires_at=manifest["expires_at"])


@app.get("/sessions/{session_id}", response_model=SessionStatus)
def get_session(session_id: str, authorization: str | None = Header(None)) -> SessionStatus:
    manifest = _authorized(session_id, authorization)
    return SessionStatus(
        session_id=session_id, status=manifest["status"], stage=manifest.get("stage"),
        quality_gate=QualityGateReport(**manifest["quality_gate"]) if manifest.get("quality_gate") else None,
        result=CoachingReport(**manifest["report"]) if manifest.get("report") else None,
        error=manifest.get("error"), expires_at=manifest["expires_at"],
    )


@app.post("/sessions/{session_id}/confirm", response_model=SessionStatus, status_code=202)
def confirm_session(session_id: str, authorization: str | None = Header(None)) -> SessionStatus:
    manifest = _authorized(session_id, authorization)
    if manifest["status"] != "needs_confirmation":
        raise HTTPException(status_code=409, detail="This session is not waiting for confirmation")
    _enqueue_analysis(session_id)
    return get_session(session_id, authorization)


def _file_chunks(path: Path, start: int, end: int, chunk_size: int = 1024 * 1024):
    with path.open("rb") as source:
        source.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = source.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@app.get("/sessions/{session_id}/video")
def get_video(session_id: str, request: Request, authorization: str | None = Header(None), access_token: str | None = Query(None)):
    _authorized(session_id, authorization, access_token)
    path = video_path(session_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video expired")
    size = path.stat().st_size
    etag = f'"{hashlib.sha256(f"{path.name}:{size}:{path.stat().st_mtime_ns}".encode()).hexdigest()}"'
    headers = {"Accept-Ranges": "bytes", "ETag": etag, "Cache-Control": "private, max-age=300", "Referrer-Policy": "no-referrer"}
    range_header = request.headers.get("range")
    start, end, status = 0, size - 1, 200
    if range_header:
        try:
            unit, value = range_header.split("=", 1)
            if unit != "bytes" or "," in value:
                raise ValueError
            first, last = value.split("-", 1)
            if first:
                start, end = int(first), min(int(last) if last else size - 1, size - 1)
            else:
                suffix = int(last)
                start, end = max(0, size - suffix), size - 1
            if start < 0 or start > end or start >= size:
                raise ValueError
            status = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        except ValueError:
            return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{size}"})
    headers["Content-Length"] = str(end - start + 1)
    media_type = {".webm": "video/webm", ".mov": "video/quicktime", ".mkv": "video/x-matroska"}.get(path.suffix.lower(), "video/mp4")
    return StreamingResponse(_file_chunks(path, start, end), status_code=status, media_type=media_type, headers=headers)


@app.get("/sessions/{session_id}/landmarks")
def get_landmarks(session_id: str, authorization: str | None = Header(None)):
    _authorized(session_id, authorization)
    path = landmarks_path(session_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Landmarks are not available yet")
    return Response(content=path.read_bytes(), media_type="application/json", headers={"Content-Encoding": "gzip", "Cache-Control": "private, max-age=300"})


# One-release compatibility route for older clients.
@app.post("/sessions/analyze", response_model=SessionAccepted, status_code=202, deprecated=True)
async def enqueue_session_analysis(file: UploadFile = File(...), project_id: str = Form(...), archetype: Archetype = Form(Archetype.CORPORATE_BOARD), audience_context: str = Form("")):
    return await create_analysis_session(file, project_id, archetype, audience_context)


@app.get("/archetypes")
def get_archetypes():
    return list_archetypes()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
