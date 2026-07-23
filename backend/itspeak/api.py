"""FastAPI surface for gated sessions and secured temporary artifacts."""

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from .archetypes import list_archetypes
from .auth import AuthPrincipal, get_auth_principal
from .artifact_store import authorize, create_session, landmarks_path, read_manifest, session_dir, update_manifest, video_path
from .models import Archetype, CoachingReport, ImprovementArea, ProjectCreate, ProjectUpdate, QualityGateReport, SessionAccepted, SessionStatus, TranscriptUpdate
from .persistence import NotFoundError, PersistenceError, ReplacementRequired, get_persistence
from .settings import get_settings
from .task_dispatch import enqueue_analysis, enqueue_quality_check
from .uploads import save_session_video

settings = get_settings()
app = FastAPI(title="it'sPEAK API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["*"] , expose_headers=["Accept-Ranges", "Content-Range", "ETag"])


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_enabled_archetype(key: str | None) -> None:
    if key is None:
        return
    enabled = {item["key"] for item in list_archetypes() if item["status"] == "enabled"}
    if key not in enabled:
        raise HTTPException(status_code=422, detail="Select an enabled speaking archetype")


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
    replace_session_id: str | None = Form(None),
    principal: AuthPrincipal = Depends(get_auth_principal),
) -> SessionAccepted:
    persistence = get_persistence()
    persistence.ensure_profile(principal.user_id, principal.display_name, principal.avatar_url)
    project = persistence.get_project(principal.user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    manifest, token = create_session({
        "project_id": project_id,
        "owner_id": principal.user_id,
        "archetype": archetype.value,
        "audience_context": audience_context[:300],
        "replace_session_id": replace_session_id,
        "improvement_areas": project.get("improvement_areas", [area.value for area in ImprovementArea]),
    })
    try:
        persistence.create_pending_session({"id": manifest["session_id"], "project_id": project_id, "owner_id": principal.user_id, "archetype_key": archetype.value, "audience_context": audience_context[:300], "replace_session_id": replace_session_id})
        path = await save_session_video(manifest["session_id"], file)
        update_manifest(manifest["session_id"], video_filename=path.name)
        enqueue_quality_check(manifest["session_id"])
    except ReplacementRequired as exc:
        shutil.rmtree(session_dir(manifest["session_id"]), ignore_errors=True)
        raise HTTPException(status_code=409, detail={"code": "replacement_required", "message": str(exc), "candidates": exc.candidates}) from exc
    except (NotFoundError, PersistenceError) as exc:
        shutil.rmtree(session_dir(manifest["session_id"]), ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        shutil.rmtree(session_dir(manifest["session_id"]), ignore_errors=True)
        raise
    return SessionAccepted(session_id=manifest["session_id"], access_token=token, project_id=project_id, expires_at=manifest["expires_at"])


@app.get("/sessions/{session_id}", response_model=SessionStatus)
def get_session(session_id: str, principal: AuthPrincipal = Depends(get_auth_principal)) -> SessionStatus:
    persistence = get_persistence()
    durable = persistence.get_session(principal.user_id, session_id)
    if durable and durable.get("status") == "success" and durable.get("analysis_result"):
        result_row = durable["analysis_result"]
        report = result_row.get("report")
        project = persistence.get_project(principal.user_id, durable["project_id"])
        return SessionStatus(
            session_id=session_id, project_id=durable["project_id"], status="success", stage=durable.get("stage"),
            quality_gate=QualityGateReport(**durable["quality_gate"]) if durable.get("quality_gate") else None,
            result=CoachingReport(**report) if report else None, error=durable.get("error"),
            expires_at=durable.get("completed_at") or durable.get("updated_at") or _iso_now(),
            sequence_number=durable.get("sequence_number"), is_baseline=bool(project and project.get("baseline_session_id") == session_id),
            aggregates={k: float(result_row[k]) if result_row.get(k) is not None else None for k in ("overall_score", "vocal_score", "face_score", "body_score")},
        )
    try:
        manifest = read_manifest(session_id)
    except (FileNotFoundError, OSError, ValueError):
        raise HTTPException(status_code=404, detail="Session not found")
    if manifest.get("owner_id") != principal.user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionStatus(
        session_id=session_id, status=manifest["status"], stage=manifest.get("stage"),
        quality_gate=QualityGateReport(**manifest["quality_gate"]) if manifest.get("quality_gate") else None,
        result=CoachingReport(**manifest["report"]) if manifest.get("report") else None,
        error=manifest.get("error"), expires_at=manifest["expires_at"], project_id=manifest.get("project_id"),
    )


@app.post("/sessions/{session_id}/confirm", response_model=SessionStatus, status_code=202)
def confirm_session(session_id: str, principal: AuthPrincipal = Depends(get_auth_principal)) -> SessionStatus:
    try:
        manifest = read_manifest(session_id)
    except (FileNotFoundError, OSError, ValueError):
        raise HTTPException(status_code=404, detail="Session not found")
    if manifest.get("owner_id") != principal.user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    if manifest["status"] != "needs_confirmation":
        raise HTTPException(status_code=409, detail="This session is not waiting for confirmation")
    enqueue_analysis(session_id)
    return get_session(session_id, principal)


@app.patch("/sessions/{session_id}/transcript", response_model=SessionStatus)
def update_transcript(session_id: str, payload: TranscriptUpdate, principal: AuthPrincipal = Depends(get_auth_principal)) -> SessionStatus:
    try:
        get_persistence().update_transcript(principal.user_id, session_id, payload.transcript)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return get_session(session_id, principal)


@app.get("/projects")
def list_projects(principal: AuthPrincipal = Depends(get_auth_principal)):
    persistence = get_persistence()
    persistence.ensure_profile(principal.user_id, principal.display_name, principal.avatar_url)
    return persistence.list_projects(principal.user_id)


@app.post("/projects", status_code=201)
def create_project(payload: ProjectCreate, principal: AuthPrincipal = Depends(get_auth_principal)):
    _require_enabled_archetype(payload.default_archetype_key)
    persistence = get_persistence()
    persistence.ensure_profile(principal.user_id, principal.display_name, principal.avatar_url)
    try:
        return persistence.create_project(principal.user_id, payload.model_dump(mode="json", exclude_none=True))
    except PersistenceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/projects/{project_id}")
def get_project(project_id: str, principal: AuthPrincipal = Depends(get_auth_principal)):
    project = get_persistence().get_project(principal.user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.patch("/projects/{project_id}")
def update_project(project_id: str, payload: ProjectUpdate, principal: AuthPrincipal = Depends(get_auth_principal)):
    _require_enabled_archetype(payload.default_archetype_key)
    try:
        return get_persistence().update_project(principal.user_id, project_id, payload.model_dump(mode="json", exclude_unset=True))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PersistenceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: str, principal: AuthPrincipal = Depends(get_auth_principal)):
    persistence = get_persistence()
    try:
        paths = persistence.delete_project(principal.user_id, project_id)
        persistence.delete_objects(paths)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@app.get("/projects/{project_id}/sessions")
def list_project_sessions(project_id: str, principal: AuthPrincipal = Depends(get_auth_principal)):
    persistence = get_persistence()
    if not persistence.get_project(principal.user_id, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return persistence.list_sessions(principal.user_id, project_id)


@app.get("/sessions/{session_id}/artifacts")
def get_session_artifacts(session_id: str, principal: AuthPrincipal = Depends(get_auth_principal)):
    try:
        return get_persistence().signed_artifacts(principal.user_id, session_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
async def enqueue_session_analysis(file: UploadFile = File(...), project_id: str = Form(...), archetype: Archetype = Form(Archetype.CORPORATE_BOARD), audience_context: str = Form(""), principal: AuthPrincipal = Depends(get_auth_principal)):
    return await create_analysis_session(file, project_id, archetype, audience_context, None, principal)


@app.get("/archetypes")
def get_archetypes():
    return list_archetypes()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
