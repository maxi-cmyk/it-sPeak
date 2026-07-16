"""Size-limited upload streaming into the private session artifact store."""

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from .artifact_store import session_dir
from .settings import get_settings

ALLOWED_VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


async def save_session_video(session_id: str, upload: UploadFile) -> Path:
    settings = get_settings()
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_VIDEO_SUFFIXES:
        raise HTTPException(status_code=415, detail="Upload an MP4, MOV, AVI, MKV, or WebM video.")
    destination = session_dir(session_id) / f"{uuid4().hex}{suffix}"
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="Video exceeds the upload size limit.")
                output.write(chunk)
        destination.chmod(0o600)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    return destination


# Compatibility helper for older callers. New API sessions use save_session_video.
async def save_temporary_video(upload: UploadFile) -> Path:
    raise RuntimeError("Use save_session_video with an access-controlled session")
