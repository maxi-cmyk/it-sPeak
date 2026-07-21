"""Tests for stagnant-progress detection (``itspeak.progress``).

These lock in the PRD rule: a comparable metric that gains fewer than
``stagnation_min_delta`` points between sessions is "not improving" and must
produce feedback, while genuinely improving metrics stay silent. They also
cover the comparability safeguards (no reference, changed archetype, missing
optional metrics).
"""

import unittest

from itspeak.models import Archetype, NormalizedScores, ProgressStatus
from itspeak.progress import detect_stagnation
from itspeak.settings import get_settings


# The reference session sits at 60 across the board; the "current" session
# clearly improves every core metric (+30) unless a test overrides one, so any
# flagged metric is unambiguously the one under test.
def _ref(archetype=Archetype.CORPORATE_BOARD) -> NormalizedScores:
    return NormalizedScores(
        eye_contact_score=60.0, expression_score=60.0,
        posture_score=60.0, gesture_score=60.0, archetype=archetype,
    )


def _cur(archetype=Archetype.CORPORATE_BOARD, **overrides) -> NormalizedScores:
    base = dict(
        eye_contact_score=90.0, expression_score=90.0,
        posture_score=90.0, gesture_score=90.0, archetype=archetype,
    )
    base.update(overrides)
    return NormalizedScores(**base)


class StagnationDetectionTest(unittest.TestCase):
    def test_no_reference_returns_no_feedback(self):
        # Baseline / first session has nothing to compare against.
        self.assertEqual(detect_stagnation(_cur(), None), [])

    def test_meaningful_improvement_is_not_flagged(self):
        signals = detect_stagnation(_cur(), _ref(), min_delta=5.0)  # every metric +30
        self.assertEqual([s.metric for s in signals], [])

    def test_flat_metric_is_stagnant(self):
        current = _cur(eye_contact_score=62.0)  # +2, below the 5 threshold
        signals = detect_stagnation(current, _ref(), min_delta=5.0)
        self.assertEqual(len(signals), 1)
        signal = signals[0]
        self.assertEqual(signal.metric, "eye_contact_score")
        self.assertEqual(signal.status, ProgressStatus.STAGNANT)
        self.assertEqual(signal.delta, 2.0)
        self.assertIn("eye contact", signal.message)
        self.assertIn("not improving", signal.message)

    def test_regression_is_declining(self):
        current = _cur(posture_score=45.0)  # -15
        signals = {s.metric: s for s in detect_stagnation(current, _ref(), min_delta=5.0)}
        self.assertIn("posture_score", signals)
        self.assertEqual(signals["posture_score"].status, ProgressStatus.DECLINING)
        self.assertEqual(signals["posture_score"].delta, -15.0)
        self.assertIn("backwards", signals["posture_score"].message)

    def test_boundary_exactly_at_threshold_improves(self):
        # Every metric gains exactly the threshold -> improving, nothing flagged.
        current = _cur(
            eye_contact_score=65.0, expression_score=65.0,
            posture_score=65.0, gesture_score=65.0,
        )
        self.assertEqual(detect_stagnation(current, _ref(), min_delta=5.0), [])

    def test_changed_archetype_is_not_comparable(self):
        current = _cur(archetype=Archetype.MOTIVATIONAL_KEYNOTE, eye_contact_score=60.0)
        self.assertEqual(detect_stagnation(current, _ref(), min_delta=5.0), [])

    def test_only_shared_metrics_are_compared(self):
        # Optional metric present now but absent before -> skipped, no error.
        current = _cur(eye_contact_score=61.0, smile_naturalness_score=90.0)
        metrics = {s.metric for s in detect_stagnation(current, _ref(), min_delta=5.0)}
        self.assertNotIn("smile_naturalness_score", metrics)
        self.assertIn("eye_contact_score", metrics)

    def test_default_threshold_comes_from_settings(self):
        gain = get_settings().stagnation_min_delta - 1.0  # just under the default
        current = _cur(eye_contact_score=60.0 + gain)
        signals = detect_stagnation(current, _ref())  # uses settings default
        self.assertEqual([s.metric for s in signals], ["eye_contact_score"])


if __name__ == "__main__":
    unittest.main()
