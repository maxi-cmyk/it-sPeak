"""Progress comparison and stagnation detection.

Pure, deterministic helpers that turn a pair of :class:`NormalizedScores`
into per-metric "you are not improving" feedback. Kept free of I/O so the
worker, the API and the future progress service can all share one source of
truth for what "stagnant" means.

Stagnation rule (PRD): a comparable metric whose score gain between two
sessions is smaller than ``stagnation_min_delta`` (default 5 points) is not
improving. Metrics that move backwards are also surfaced, flagged as
``declining`` so the copy can distinguish "flat" from "getting worse".
"""

from __future__ import annotations

from .models import NormalizedScores, ProgressStatus, StagnationSignal
from .settings import get_settings

# Human-readable metric names used in feedback copy.
METRIC_LABELS: dict[str, str] = {
    "eye_contact_score": "eye contact",
    "expression_score": "facial expression",
    "posture_score": "posture",
    "gesture_score": "gestures",
    "smile_naturalness_score": "smile naturalness",
    "movement_purposefulness_score": "purposeful movement",
    "spatial_use_score": "use of the space",
}


def _classify(delta: float, min_delta: float) -> ProgressStatus:
    if delta >= min_delta:
        return ProgressStatus.IMPROVING
    if delta <= -min_delta:
        return ProgressStatus.DECLINING
    return ProgressStatus.STAGNANT


def _message(label: str, status: ProgressStatus, delta: float, reference_label: str) -> str:
    if status is ProgressStatus.DECLINING:
        return (
            f"Your {label} dropped {abs(delta):.1f} points below {reference_label}. "
            f"This area is going backwards \u2014 make it a priority in your next rehearsal."
        )
    return (
        f"Your {label} has barely moved since {reference_label} "
        f"({delta:+.1f} points). You're not improving here yet \u2014 focus your next "
        f"rehearsal on this metric."
    )


def detect_stagnation(
    current: NormalizedScores,
    reference: NormalizedScores | None,
    *,
    min_delta: float | None = None,
    reference_label: str = "your last comparable session",
) -> list[StagnationSignal]:
    """Return feedback for metrics that are not meaningfully improving.

    A :class:`StagnationSignal` is produced for every metric that both
    recordings measure and whose gain is below ``min_delta`` (stagnant) or
    negative (declining). Metrics that improve by at least ``min_delta`` are
    omitted because they need no corrective feedback.

    Comparability safeguards:
      * ``reference is None`` (e.g. the baseline / first session) yields ``[]``.
      * A different archetype means the two scores are calibrated on different
        scales, so the deltas are not meaningful and ``[]`` is returned rather
        than presenting an incomparable comparison as improvement or decline.
      * Only metrics available in *both* recordings are compared, so missing or
        low-confidence optional metrics degrade silently instead of raising.
    """
    if reference is None:
        return []
    if current.archetype != reference.archetype:
        return []

    threshold = get_settings().stagnation_min_delta if min_delta is None else min_delta
    reference_values = reference.available()

    signals: list[StagnationSignal] = []
    for metric, value in current.available().items():
        if metric not in reference_values:
            continue
        delta = round(value - reference_values[metric], 1)
        status = _classify(delta, threshold)
        if status is ProgressStatus.IMPROVING:
            continue
        label = METRIC_LABELS.get(metric, metric.replace("_score", "").replace("_", " "))
        signals.append(
            StagnationSignal(
                metric=metric,
                label=label,
                current_score=value,
                reference_score=reference_values[metric],
                delta=delta,
                status=status,
                message=_message(label, status, delta, reference_label),
            )
        )
    return signals
