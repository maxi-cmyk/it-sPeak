"""Media preparation helpers shared by background analysis jobs."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .settings import get_settings


def extract_audio_track(video_path: str) -> Path:
    """Extract a mono 16 kHz WAV beside the uploaded video."""
    settings = get_settings()
    source = Path(video_path)
    audio_path = source.with_suffix(".analysis.wav")
    command = [
        settings.ffmpeg_bin,
        "-v",
        "error",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(audio_path),
    ]
    try:
        subprocess.run(command, capture_output=True, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"ffmpeg binary '{settings.ffmpeg_bin}' not found.") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.decode(errors="ignore").strip()
        raise RuntimeError(f"Could not extract the video's audio track: {message}") from exc
    return audio_path
