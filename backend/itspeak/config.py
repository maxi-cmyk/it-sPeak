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
    smile_naturalness: Band
    movement_purposefulness: Band
    spatial_use: Band

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
            "gestures. Excessive movement or animation can make the delivery "
            "look visually unsettled."
        ),
        # Expects very high eye contact.
        eye_contact=FloorBand(low=0.35, ideal=0.80),
        # Controlled but not frozen expression.
        expression=TargetBand(ideal=0.12, tol_low=0.22, tol_high=0.60),
        # Posture scale is compressed so a merely-normal upright proxy (~0.7)
        # lands ~50 and only steady, genuinely square posture reaches 80-100.
        posture=FloorBand(low=0.40, ideal=1.0),
        # Minimal, deliberate gestures — a low ideal, punished if busy.
        gesture_frequency=TargetBand(ideal=0.25, tol_low=0.45, tol_high=0.85),
        gesture_range=TargetBand(ideal=0.20, tol_low=0.40, tol_high=0.80),
        # Open, but stillness matters more than expansiveness here.
        openness=FloorBand(low=0.12, ideal=0.40),
        smile_naturalness=FloorBand(low=0.15, ideal=0.65),
        movement_purposefulness=FloorBand(low=0.20, ideal=0.75),
        spatial_use=TargetBand(ideal=0.25, tol_low=0.25, tol_high=0.55),
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
        expression=FloorBand(low=0.02, ideal=0.14),
        posture=FloorBand(low=0.35, ideal=0.98),
        # Rewards frequent, large gestures.
        gesture_frequency=TargetBand(ideal=0.70, tol_low=0.90, tol_high=0.90),
        gesture_range=TargetBand(ideal=0.75, tol_low=0.90, tol_high=0.85),
        openness=FloorBand(low=0.12, ideal=0.45),
        smile_naturalness=FloorBand(low=0.20, ideal=0.75),
        movement_purposefulness=FloorBand(low=0.25, ideal=0.80),
        spatial_use=FloorBand(low=0.10, ideal=0.65),
        gesture_freq_weight=0.4,
    ),
    # ------------------------------------------------------------------ #
    # Startup Pitch: persuasive and energetic, but credible. More dynamic
    # than a boardroom, more disciplined than a keynote. Strong eye contact to
    # build investor trust, animated (not theatrical) expression, and
    # purposeful, moderately expansive gestures that emphasise key points.
    # ------------------------------------------------------------------ #
    Archetype.STARTUP_PITCH: ArchetypeConfig(
        key=Archetype.STARTUP_PITCH,
        label="Startup Pitch",
        description=(
            "A high-conviction investor or demo-day pitch. Presence is built on "
            "credible energy: strong, trust-building eye contact, animated but "
            "controlled expression, upright confident posture, and purposeful, "
            "moderately expansive gestures that punctuate key claims. Flat "
            "delivery reads as unconvincing; frantic, over-large motion reads as "
            "nervous and undercuts credibility."
        ),
        eye_contact=FloorBand(low=0.30, ideal=0.72),
        expression=FloorBand(low=0.02, ideal=0.12),
        posture=FloorBand(low=0.40, ideal=1.0),
        gesture_frequency=TargetBand(ideal=0.50, tol_low=0.75, tol_high=0.85),
        gesture_range=TargetBand(ideal=0.50, tol_low=0.75, tol_high=0.85),
        openness=FloorBand(low=0.12, ideal=0.42),
        smile_naturalness=FloorBand(low=0.20, ideal=0.70),
        movement_purposefulness=FloorBand(low=0.30, ideal=0.82),
        spatial_use=TargetBand(ideal=0.45, tol_low=0.40, tol_high=0.45),
        gesture_freq_weight=0.5,
    ),
    # ------------------------------------------------------------------ #
    # Academic / Conference: clarity and precision at the lectern. Measured,
    # credible delivery. Eye contact is moderate (slides/notes are referenced),
    # expression is controlled, and gestures are restrained and precise.
    # Podium-bound, so stage movement should be minimal.
    # ------------------------------------------------------------------ #
    Archetype.ACADEMIC_CONFERENCE: ArchetypeConfig(
        key=Archetype.ACADEMIC_CONFERENCE,
        label="Academic / Conference",
        description=(
            "A scholarly conference talk or lecture. Presence is built on clarity "
            "and precision: measured, controlled facial expression, upright "
            "posture, and restrained, deliberate gestures that clarify structure. "
            "Moderate eye contact is expected because slides and notes are "
            "referenced. Theatrical animation or wide roaming gestures distract "
            "from the substance."
        ),
        eye_contact=FloorBand(low=0.25, ideal=0.60),
        expression=TargetBand(ideal=0.14, tol_low=0.24, tol_high=0.65),
        posture=FloorBand(low=0.40, ideal=1.0),
        gesture_frequency=TargetBand(ideal=0.35, tol_low=0.60, tol_high=0.85),
        gesture_range=TargetBand(ideal=0.30, tol_low=0.55, tol_high=0.82),
        openness=FloorBand(low=0.10, ideal=0.38),
        smile_naturalness=FloorBand(low=0.10, ideal=0.55),
        movement_purposefulness=FloorBand(low=0.20, ideal=0.72),
        spatial_use=TargetBand(ideal=0.25, tol_low=0.25, tol_high=0.50),
        gesture_freq_weight=0.55,
    ),
    # ------------------------------------------------------------------ #
    # Informal / Team: relaxed, conversational and approachable. Natural
    # (not intense) eye contact, warm expression, and easy natural gestures with
    # a wide tolerance. Posture and movement expectations are the most
    # forgiving of any archetype.
    # ------------------------------------------------------------------ #
    Archetype.INFORMAL_TEAM: ArchetypeConfig(
        key=Archetype.INFORMAL_TEAM,
        label="Informal / Team",
        description=(
            "A relaxed team stand-up, update or internal discussion. Presence is "
            "built on warmth and approachability: natural conversational eye "
            "contact, warm animated expression, an easy relaxed posture, and "
            "natural hand gestures. Delivery should feel unforced; stiff, "
            "over-controlled behaviour reads as tense rather than collaborative."
        ),
        eye_contact=FloorBand(low=0.20, ideal=0.55),
        expression=FloorBand(low=0.02, ideal=0.13),
        posture=FloorBand(low=0.32, ideal=0.96),
        gesture_frequency=TargetBand(ideal=0.50, tol_low=0.80, tol_high=0.95),
        gesture_range=TargetBand(ideal=0.50, tol_low=0.80, tol_high=0.95),
        openness=FloorBand(low=0.10, ideal=0.42),
        smile_naturalness=FloorBand(low=0.20, ideal=0.70),
        movement_purposefulness=FloorBand(low=0.15, ideal=0.65),
        spatial_use=FloorBand(low=0.10, ideal=0.55),
        gesture_freq_weight=0.5,
    ),
    # ------------------------------------------------------------------ #
    # Job Interview: composed, professional and attentive (typically seated).
    # Very steady eye contact signals engagement and honesty, expression is warm
    # but measured, posture is notably upright, and gestures are minimal and
    # contained. Stage/spatial movement should be almost none.
    # ------------------------------------------------------------------ #
    Archetype.JOB_INTERVIEW: ArchetypeConfig(
        key=Archetype.JOB_INTERVIEW,
        label="Job Interview",
        description=(
            "A one-on-one or panel job interview, usually seated. Presence is "
            "built on composed professionalism: steady, engaged eye contact, a "
            "warm but measured expression, a notably upright posture, and "
            "minimal, contained gestures. A genuine smile builds rapport. "
            "Fidgeting, slumping or large sweeping gestures undermine composure."
        ),
        eye_contact=FloorBand(low=0.35, ideal=0.78),
        expression=TargetBand(ideal=0.12, tol_low=0.22, tol_high=0.60),
        posture=FloorBand(low=0.42, ideal=1.0),
        gesture_frequency=TargetBand(ideal=0.30, tol_low=0.55, tol_high=0.82),
        gesture_range=TargetBand(ideal=0.25, tol_low=0.50, tol_high=0.80),
        openness=FloorBand(low=0.15, ideal=0.42),
        smile_naturalness=FloorBand(low=0.20, ideal=0.70),
        movement_purposefulness=FloorBand(low=0.20, ideal=0.70),
        spatial_use=TargetBand(ideal=0.15, tol_low=0.15, tol_high=0.45),
        gesture_freq_weight=0.6,
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
        # Retain the optional contract field for older reports, but smile
        # naturalness is a diagnostic proxy rather than a judged score.
        smile_naturalness_score=None,
        movement_purposefulness_score=(round(cfg.movement_purposefulness.score(body.movement_purposefulness), 1) if body.movement_purposefulness is not None else None),
        spatial_use_score=(round(cfg.spatial_use.score(body.spatial_use), 1) if body.spatial_use is not None else None),
        archetype=archetype,
    )


def compute_progress(
    current: NormalizedScores, baseline: NormalizedScores | None
) -> dict[str, float] | None:
    """Return per-metric deltas (current - baseline), or ``None``."""
    if baseline is None:
        return None
    baseline_values = baseline.available()
    return {
        key: round(value - baseline_values[key], 1)
        for key, value in current.available().items()
        if key in baseline_values
    }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))
