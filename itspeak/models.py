"""Shared data contracts for the it'sPEAK analysis + coaching pipeline.

These Pydantic models are the *only* thing the three layers share. They
enforce the "Modular Contracts" requirement: raw mathematical frame analysis
(``pipeline``), archetype scoring (``config``) and LLM execution (``coaching``)
never import each other's implementation details — they only pass these models
around.

Data flow
---------
    RAW ANALYSIS            SCORING                 LLM
    ------------            -------                 ---
    VideoAnalysisResult --> NormalizedScores --> list[CoachingCard]
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Archetype(str, Enum):
    """Supported speaking archetypes.

    The string values double as the keys into ``config.ARCHETYPE_PRESETS`` and
    are what the API accepts from clients.
    """

    CORPORATE_BOARD = "corporate_board"
    MOTIVATIONAL_KEYNOTE = "motivational_keynote"


class Module(str, Enum):
    """Which analysis module a coaching card belongs to."""

    FACE = "face"
    BODY = "body"


# --------------------------------------------------------------------------- #
# Raw analysis contracts (produced by pipeline.py, MediaPipe layer)
# --------------------------------------------------------------------------- #
class FaceMetrics(BaseModel):
    """Raw, un-scaled outputs of the MediaPipe Face Mesh module.

    All values are grounded in observable geometry so that downstream scoring
    stays deterministic and explainable.
    """

    eye_contact_ratio: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of analysed frames whose gaze vector fell inside "
        "the camera-center tolerance box.",
    )
    expression_variance: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Expressiveness index (0=flat, 1=highly animated) derived "
        "from temporal variance of mouth-corner and eyebrow landmarks.",
    )
    head_stability: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Head steadiness (1=rock steady, 0=constant sway/nod) "
        "derived from the std-dev of the nose-tip landmark.",
    )

    # Diagnostics / confidence
    frames_with_face: int = Field(
        0, ge=0, description="Number of frames where a face was detected."
    )


class BodyMetrics(BaseModel):
    """Raw, un-scaled outputs of the MediaPipe BlazePose module."""

    posture_alignment: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Spine/shoulder verticality (1=upright, 0=heavily slouched "
        "or leaning), derived from the shoulder-line angle vs. vertical.",
    )
    gesture_frequency: float = Field(
        0.0,
        ge=0.0,
        description="Average per-second wrist travel normalised by torso length "
        "(dimensionless). Higher = busier hands.",
    )
    gesture_range: float = Field(
        0.0,
        ge=0.0,
        description="Bounding-volume of wrist positions normalised by torso "
        "length. Higher = more expansive gesturing.",
    )
    openness_ratio: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of frames in an 'open' posture (wrists away from "
        "the torso midline) vs. 'closed' (crossed/at sides).",
    )

    frames_with_pose: int = Field(
        0, ge=0, description="Number of frames where a pose was detected."
    )


class VideoAnalysisResult(BaseModel):
    """Aggregate structured output of the whole analysis pipeline."""

    face: FaceMetrics
    body: BodyMetrics

    frames_analyzed: int = Field(0, ge=0)
    sample_fps: float = Field(2.0, gt=0.0)
    duration_seconds: float = Field(0.0, ge=0.0)

    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal degradations (e.g. low detection confidence, "
        "missing face) logged instead of crashing.",
    )


# --------------------------------------------------------------------------- #
# Scoring contracts (produced by config.py)
# --------------------------------------------------------------------------- #
class NormalizedScores(BaseModel):
    """Archetype-calibrated 0-100 scores."""

    eye_contact_score: float = Field(0.0, ge=0.0, le=100.0)
    expression_score: float = Field(0.0, ge=0.0, le=100.0)
    posture_score: float = Field(0.0, ge=0.0, le=100.0)
    gesture_score: float = Field(0.0, ge=0.0, le=100.0)

    archetype: Archetype

    def face_scores(self) -> dict[str, float]:
        return {
            "eye_contact_score": self.eye_contact_score,
            "expression_score": self.expression_score,
        }

    def body_scores(self) -> dict[str, float]:
        return {
            "posture_score": self.posture_score,
            "gesture_score": self.gesture_score,
        }


# --------------------------------------------------------------------------- #
# Coaching contracts (produced by coaching.py)
# --------------------------------------------------------------------------- #
class CoachingCard(BaseModel):
    """A single, strictly-formatted piece of coaching feedback."""

    module: Module
    problem: str = Field(..., description="Clear description of the behavioural issue.")
    importance: str = Field(
        ..., description="Why this hurts presence given the target audience."
    )
    actionable_fix: str = Field(
        ..., description="One tactical, physical exercise/trick to fix it next time."
    )


# --------------------------------------------------------------------------- #
# API request / response contracts
# --------------------------------------------------------------------------- #
class AnalyzeRequest(BaseModel):
    """Payload accepted by the ``/analyze`` endpoint."""

    video_path: str = Field(..., description="Local path to the extracted video file.")
    archetype: Archetype = Archetype.CORPORATE_BOARD
    audience_context: str = Field(
        "",
        description="Free-text description of the target audience / setting.",
    )
    baseline_scores: Optional[NormalizedScores] = Field(
        None,
        description="Prior session scores, used to compute progress differentials.",
    )


class AnalyzeAccepted(BaseModel):
    """Returned immediately after a job is enqueued."""

    task_id: str
    status: str = "queued"


class CoachingReport(BaseModel):
    """Final assembled report returned once a job finishes."""

    archetype: Archetype
    scores: NormalizedScores
    raw_analysis: VideoAnalysisResult
    cards: list[CoachingCard]
    progress: Optional[dict[str, float]] = Field(
        None, description="Per-metric score delta vs. baseline, if provided."
    )


class JobStatus(BaseModel):
    """Polling response for ``/result/{task_id}``."""

    task_id: str
    status: str
    result: Optional[CoachingReport] = None
    error: Optional[str] = None
