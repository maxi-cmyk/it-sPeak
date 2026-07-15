"""Runtime configuration, loaded from environment variables / ``.env``."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised settings for brokers, sampling and the LLM."""

    model_config = SettingsConfigDict(env_prefix="ITSPEAK_", env_file=".env", extra="ignore")

    # --- Celery / Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Frame sampling ---
    # 2 fps satisfies the ~93% compute reduction vs. 30 fps requirement.
    sample_fps: float = 2.0
    # Downscale long edge for CPU friendliness (0 = keep native resolution).
    max_frame_width: int = 640
    # ffmpeg binary (allow override on Windows where it may not be on PATH).
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"

    # --- MediaPipe confidence / degradation thresholds ---
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    # Fraction of frames that must yield a detection before we trust a metric.
    min_valid_frame_ratio: float = 0.30

    # --- LLM ---
    # "google" (google-genai) or "anthropic".
    llm_provider: str = "google"
    google_api_key: str = ""
    anthropic_api_key: str = ""
    google_model: str = "gemini-1.5-flash"
    anthropic_model: str = "claude-3-5-sonnet-latest"
    llm_temperature: float = 0.3  # low temp -> deterministic, no hallucination
    llm_max_output_tokens: int = 2048


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
