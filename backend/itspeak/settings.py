"""Runtime configuration loaded from environment variables / ``.env``."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ITSPEAK_", env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    sample_fps: float = 5.0
    gate_max_fps: float = 1.0
    gate_max_frames: int = 24
    max_frame_width: int = 640
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    min_valid_frame_ratio: float = 0.30

    gate_luminance_low: float = 45.0
    gate_luminance_high: float = 220.0
    gate_contrast_min: float = 20.0
    gate_blur_variance_min: float = 45.0
    gate_face_pixels_min: int = 200
    gate_face_presence_min: float = 0.70
    gate_pose_presence_min: float = 0.70
    gate_audio_rms_min_dbfs: float = -35.0
    gate_audio_peak_max_dbfs: float = -1.0
    gate_silence_max_ratio: float = 0.40
    max_video_duration_seconds: float = 180.0

    openai_api_key: str = ""
    coaching_model: str = "gpt-4o-mini"
    transcription_model: str = "whisper-1"
    llm_temperature: float = 0.3
    llm_max_output_tokens: int = 2048

    frontend_origin: str = "http://localhost:3000"
    artifact_dir: str = "/tmp/itspeak-sessions"
    max_upload_bytes: int = 250 * 1024 * 1024
    artifact_retention_seconds: int = 24 * 60 * 60
    cleanup_interval_seconds: int = 60 * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
