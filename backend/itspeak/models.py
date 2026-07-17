"""Versioned contracts shared by the API, workers, CV and frontend."""

from __future__ import annotations

from enum import Enum
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class Archetype(str, Enum):
    CORPORATE_BOARD = "corporate_board"
    MOTIVATIONAL_KEYNOTE = "motivational_keynote"


class Module(str, Enum):
    FACE = "face"
    BODY = "body"
    AUDIO = "audio"


class MetricConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient_data"


class EyeContactState(str, Enum):
    ON_CAMERA = "on_camera"
    AWAY = "away"
    UNKNOWN = "unknown"


class QualityDisposition(str, Enum):
    PASS = "pass"
    CONFIRM = "confirm"
    REJECT = "reject"


class QualityIssue(BaseModel):
    code: str
    severity: str
    title: str
    message: str
    action: str


class QualityMeasurements(BaseModel):
    duration_seconds: float = 0.0
    source_width: int = 0
    source_height: int = 0
    sampled_frames: int = 0
    median_luminance: Optional[float] = None
    median_contrast: Optional[float] = None
    median_blur_variance: Optional[float] = None
    median_face_width_px: Optional[float] = None
    median_face_height_px: Optional[float] = None
    face_presence_ratio: float = 0.0
    pose_visibility_ratio: float = 0.0
    max_faces: int = 0
    audio_rms_dbfs: Optional[float] = None
    audio_peak_dbfs: Optional[float] = None
    audio_noise_floor_dbfs: Optional[float] = None
    silence_ratio: Optional[float] = None


class QualityGateReport(BaseModel):
    version: str = "1.0"
    disposition: QualityDisposition
    issues: list[QualityIssue] = Field(default_factory=list)
    measurements: QualityMeasurements
    thresholds: dict[str, float] = Field(default_factory=dict)
    primary_face_confidence: MetricConfidence = MetricConfidence.INSUFFICIENT
    limitations: list[str] = Field(default_factory=list)


class FaceMetrics(BaseModel):
    eye_contact_ratio: float = Field(0.0, ge=0.0, le=1.0)
    expression_variance: float = Field(0.0, ge=0.0, le=1.0)
    head_stability: float = Field(0.0, ge=0.0, le=1.0)
    au6_proxy: Optional[float] = Field(None, ge=0.0, le=1.0)
    au12_proxy: Optional[float] = Field(None, ge=0.0, le=1.0)
    smile_naturalness_proxy: Optional[float] = Field(None, ge=0.0, le=1.0)
    smile_confidence: MetricConfidence = MetricConfidence.INSUFFICIENT
    frames_with_face: int = Field(0, ge=0)


class BodyMetrics(BaseModel):
    posture_alignment: float = Field(0.0, ge=0.0, le=1.0)
    gesture_frequency: float = Field(0.0, ge=0.0)
    gesture_range: float = Field(0.0, ge=0.0)
    openness_ratio: float = Field(0.0, ge=0.0, le=1.0)
    movement_purposefulness: Optional[float] = Field(None, ge=0.0, le=1.0)
    movement_classification: str = "insufficient_data"
    movement_confidence: MetricConfidence = MetricConfidence.INSUFFICIENT
    spatial_use: Optional[float] = Field(None, ge=0.0, le=1.0)
    spatial_confidence: MetricConfidence = MetricConfidence.INSUFFICIENT
    frames_with_pose: int = Field(0, ge=0)


class VideoAnalysisResult(BaseModel):
    face: FaceMetrics
    body: BodyMetrics
    frames_analyzed: int = Field(0, ge=0)
    sample_fps: float = Field(5.0, gt=0.0)
    duration_seconds: float = Field(0.0, ge=0.0)
    metric_confidence: dict[str, MetricConfidence] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class NormalizedScores(BaseModel):
    eye_contact_score: float = Field(0.0, ge=0.0, le=100.0)
    expression_score: float = Field(0.0, ge=0.0, le=100.0)
    posture_score: float = Field(0.0, ge=0.0, le=100.0)
    gesture_score: float = Field(0.0, ge=0.0, le=100.0)
    smile_naturalness_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    movement_purposefulness_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    spatial_use_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    archetype: Archetype

    def available(self) -> dict[str, float]:
        return {k: v for k, v in self.model_dump(exclude={"archetype"}).items() if v is not None}

    def face_scores(self) -> dict[str, float]:
        return {k: v for k, v in self.available().items() if k in {"eye_contact_score", "expression_score", "smile_naturalness_score"}}

    def body_scores(self) -> dict[str, float]:
        return {k: v for k, v in self.available().items() if k in {"posture_score", "gesture_score", "movement_purposefulness_score", "spatial_use_score"}}


class CoachingCard(BaseModel):
    module: Module
    problem: str
    importance: str
    actionable_fix: str


class AudioAnalysisResult(BaseModel):
    summary: dict[str, Any]
    performance_scores: dict[str, float]
    readable_metrics: dict[str, Any]
    transcript: dict[str, Any]
    pauses_timeline: list[dict[str, Any]] = Field(default_factory=list)
    speech_issues: dict[str, Any] = Field(default_factory=dict)
    actionable_coaching_cards: list[str] = Field(default_factory=list)


class ArtifactLinks(BaseModel):
    video: str
    landmarks: str


class CoachingReport(BaseModel):
    archetype: Archetype
    scores: NormalizedScores
    raw_analysis: VideoAnalysisResult
    audio: AudioAnalysisResult
    cards: list[CoachingCard]
    progress: Optional[dict[str, float]] = None
    artifacts: Optional[ArtifactLinks] = None


class SessionAccepted(BaseModel):
    session_id: str
    access_token: str
    status: str = "quality_check"
    project_id: Optional[str] = None
    expires_at: str


class SessionStatus(BaseModel):
    session_id: str
    status: str
    stage: Optional[str] = None
    quality_gate: Optional[QualityGateReport] = None
    result: Optional[CoachingReport] = None
    error: Optional[str] = None
    expires_at: str
    project_id: Optional[str] = None
    sequence_number: Optional[int] = None
    is_baseline: bool = False
    aggregates: Optional[dict[str, float | None]] = None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    goal: Optional[str] = Field(None, max_length=1000)
    deadline: Optional[date] = None
    pinned: bool = False
    default_archetype_key: str = "corporate_board"

    @field_validator("name")
    @classmethod
    def project_name_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project name is required")
        return value


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    goal: Optional[str] = Field(None, max_length=1000)
    deadline: Optional[date] = None
    pinned: Optional[bool] = None
    default_archetype_key: Optional[str] = None

    @field_validator("name")
    @classmethod
    def updated_name_must_have_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Project name is required")
        return value


# Kept as aliases for code importing the earlier contract names.
AnalyzeAccepted = SessionAccepted
JobStatus = SessionStatus
