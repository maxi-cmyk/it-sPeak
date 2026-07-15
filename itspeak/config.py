"""Archetype context, calibration matrix and score normalization.

This module is the *scoring* layer. It is deliberately free of any MediaPipe /
FastAPI / LLM imports — it only consumes ``VideoAnalysisResult`` and produces
``NormalizedScores`` (see the Modular Contracts requirement).

Design
------
Every metric is mapped to 0-100 against an archetype-specific "band". A band is
defined by an *ideal* target and a *tolerance*. Two band shapes exist:

* ``TargetBand`` — score peaks at ``ideal`` and falls off on both sides
  (e.g. gesture frequency: too little *and* too much are both penalised).
* ``FloorBand``  — score rises monotonically toward ``ideal`` and is flat above
  it (e.g. eye contact / posture: "more is better, up to the target").

Because each archetype supplies its own bands, the exact same raw numbers score
very differently for a Corporate/Board talk vs. a Motivational/Keynote.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Archetype, NormalizedScores, VideoAnalysisResult


# --------------------------------------------------------------------------- #
# Band primitives
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FloorBand:
    """Monotonic "more is better up to a ceiling" mapping.

    ``low`` scores 0, ``ideal`` (and anything above it) scores 100, values in
    between are linearly interpolated.
    """

    low: float
    ideal: float

    def score(self, value: float) -> float:
        if self.ideal <= self.low:  # guard against misconfiguration
            return 100.0 if value >= self.ideal else 0.0
        pct = (value - self.low) / (self.ideal - self.low)
        return _clamp(pct * 100.0)


@dataclass(frozen=True)
class TargetBand:
    """Symmetric-ish peak mapping.

    Score is 100 at ``ideal`` and decays linearly to 0 once the value is more
    than ``tol_low`` below or ``tol_high`` above the ideal. This penalises both
    under- and over-doing a behaviour (e.g. gesturing).
    """

    ideal: float
    tol_low: float
    tol_high: float

    def score(self, value: float) -> float:
        if value <= self.ideal:
            if self.tol_low <= 0:
                return 100.0
            deficit = max(0.0, self.ideal - value)
            return _clamp(100.0 * (1.0 - deficit / self.tol_low))
        else:
            if self.tol_high <= 0:
                return 100.0
            excess = value - self.ideal
            return _clamp(100.0 * (1.0 - excess / self.tol_high))


Band = FloorBand | TargetBand


# --------------------------------------------------------------------------- #
# Archetype configuration
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ArchetypeConfig:
    """Full calibration matrix for one archetype.

    ``description`` is fed to the LLM layer so the coaching stays on-brand with
    the chosen speaking style.
    """

    key: Archetype
    label: str
    description: str

    eye_contact: Band
    expression: Band
    posture: Band
    gesture_frequency: Band
    gesture_range: Band
    openness: Band

    # Weight blend between frequency and range when producing one gesture score.
    gesture_freq_weight: float = 0.5


ARCHETYPE_PRESETS: dict[Archetype, ArchetypeConfig] = {
    # ------------------------------------------------------------------ #
    # Corporate / Board: authority through stillness. High sustained eye
    # contact, controlled expression, upright posture, few deliberate gestures.
    # ------------------------------------------------------------------ #
    Archetype.CORPORATE_BOARD: ArchetypeConfig(
        key=Archetype.CORPORATE_BOARD,
        label="Corporate / Board",
        description=(
            "A high-stakes boardroom or executive setting. Presence is built on "
            "calm authority: strong sustained eye contact, an upright and still "
            "posture, controlled facial expression, and sparse, deliberate "
            "gestures. Excessive movement or animation reads as nervous."
        ),
        # Expects very high eye contact.
        eye_contact=FloorBand(low=0.35, ideal=0.80),
        # Controlled but not frozen expression.
        expression=TargetBand(ideal=0.35, tol_low=0.30, tol_high=0.45),
        posture=FloorBand(low=0.45, ideal=0.90),
        # Minimal, deliberate gestures — a low ideal, punished if busy.
        gesture_frequency=TargetBand(ideal=0.25, tol_low=0.25, tol_high=0.45),
        gesture_range=TargetBand(ideal=0.20, tol_low=0.20, tol_high=0.40),
        # Open, but stillness matters more than expansiveness here.
        openness=FloorBand(low=0.30, ideal=0.65),
        gesture_freq_weight=0.6,
    ),
    # ------------------------------------------------------------------ #
    # Motivational / Keynote: energy and reach. Wide expression variance,
    # large expansive gestures, dynamic (but not chaotic) movement.
    # ------------------------------------------------------------------ #
    Archetype.MOTIVATIONAL_KEYNOTE: ArchetypeConfig(
        key=Archetype.MOTIVATIONAL_KEYNOTE,
        label="Motivational / Keynote",
        description=(
            "An energetic keynote or motivational stage. Presence is built on "
            "reach and dynamism: wide, animated facial expression, large "
            "expansive open gestures, and confident movement that fills the "
            "stage. Flat delivery or small, closed gestures kill the energy."
        ),
        # Eye contact still matters but sweeping the room is fine.
        eye_contact=FloorBand(low=0.25, ideal=0.65),
        # Wants high expressiveness.
        expression=FloorBand(low=0.25, ideal=0.80),
        posture=FloorBand(low=0.40, ideal=0.85),
        # Rewards frequent, large gestures.
        gesture_frequency=TargetBand(ideal=0.70, tol_low=0.55, tol_high=0.50),
        gesture_range=TargetBand(ideal=0.75, tol_low=0.55, tol_high=0.45),
        openness=FloorBand(low=0.35, ideal=0.80),
        gesture_freq_weight=0.4,
    ),
}


def get_archetype_config(archetype: Archetype) -> ArchetypeConfig:
    """Return the calibration matrix for ``archetype`` (defaults sensibly)."""
    return ARCHETYPE_PRESETS.get(
        archetype, ARCHETYPE_PRESETS[Archetype.CORPORATE_BOARD]
    )


# --------------------------------------------------------------------------- #
# Normalization
# --------------------------------------------------------------------------- #
def normalize_scores(
    analysis: VideoAnalysisResult, archetype: Archetype
) -> NormalizedScores:
    """Map raw face/body metrics to archetype-calibrated 0-100 scores.

    Parameters
    ----------
    analysis:
        Raw ``VideoAnalysisResult`` from the pipeline.
    archetype:
        Which calibration matrix to apply.

    Returns
    -------
    NormalizedScores
        Four 0-100 scores plus the archetype used.
    """
    cfg = get_archetype_config(archetype)
    face = analysis.face
    body = analysis.body

    eye_contact_score = cfg.eye_contact.score(face.eye_contact_ratio)
    expression_score = cfg.expression.score(face.expression_variance)
    posture_score = cfg.posture.score(body.posture_alignment)

    # Gesture score blends frequency, range and openness.
    freq_s = cfg.gesture_frequency.score(body.gesture_frequency)
    range_s = cfg.gesture_range.score(body.gesture_range)
    open_s = cfg.openness.score(body.openness_ratio)
    fw = cfg.gesture_freq_weight
    motion_s = fw * freq_s + (1.0 - fw) * range_s
    # Openness is a lighter modifier (30%) on top of the motion blend.
    gesture_score = 0.7 * motion_s + 0.3 * open_s

    return NormalizedScores(
        eye_contact_score=round(_clamp(eye_contact_score), 1),
        expression_score=round(_clamp(expression_score), 1),
        posture_score=round(_clamp(posture_score), 1),
        gesture_score=round(_clamp(gesture_score), 1),
        archetype=archetype,
    )


def compute_progress(
    current: NormalizedScores, baseline: NormalizedScores | None
) -> dict[str, float] | None:
    """Return per-metric deltas (current - baseline), or ``None``."""
    if baseline is None:
        return None
    return {
        "eye_contact_score": round(
            current.eye_contact_score - baseline.eye_contact_score, 1
        ),
        "expression_score": round(
            current.expression_score - baseline.expression_score, 1
        ),
        "posture_score": round(current.posture_score - baseline.posture_score, 1),
        "gesture_score": round(current.gesture_score - baseline.gesture_score, 1),
    }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))
