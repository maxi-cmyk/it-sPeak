"""Regression tests for the archetype scoring / normalization layer.

These lock in three properties of ``config.normalize_scores``:
  1. It emits a bounded, correctly-typed standardized structure.
  2. The two enabled archetypes calibrate identical raw data differently.
  3. It degrades gracefully when MediaPipe tracking is missing (zero frames /
     ``None`` optional metrics) instead of dividing by zero or raising.
"""

import unittest

from itspeak.archetypes import list_archetypes
from itspeak.config import ARCHETYPE_PRESETS, get_archetype_config, normalize_scores
from itspeak.models import (
    Archetype,
    BodyMetrics,
    FaceMetrics,
    VideoAnalysisResult,
)

ENABLED_ARCHETYPES = (
    Archetype.CORPORATE_BOARD,
    Archetype.MOTIVATIONAL_KEYNOTE,
    Archetype.STARTUP_PITCH,
    Archetype.ACADEMIC_CONFERENCE,
    Archetype.INFORMAL_TEAM,
    Archetype.JOB_INTERVIEW,
)

CORE_KEYS = {"eye_contact_score", "expression_score", "posture_score", "gesture_score"}
OPTIONAL_KEYS = {"smile_naturalness_score", "movement_purposefulness_score", "spatial_use_score"}


def _rich_result() -> VideoAnalysisResult:
    """A high-signal recording: wide expression and large, open gestures."""
    return VideoAnalysisResult(
        face=FaceMetrics(
            eye_contact_ratio=0.82, expression_variance=0.85, head_stability=0.9,
            au6_proxy=0.6, au12_proxy=0.7, smile_naturalness_proxy=0.65, frames_with_face=100,
        ),
        body=BodyMetrics(
            posture_alignment=0.88, gesture_frequency=0.72, gesture_range=0.75, openness_ratio=0.8,
            movement_purposefulness=0.7, movement_classification="purposeful_translation",
            spatial_use=0.6, frames_with_pose=100,
        ),
        frames_analyzed=100, sample_fps=5.0, duration_seconds=20.0,
    )


def _degraded_result() -> VideoAnalysisResult:
    """No usable tracking: zero frames and unavailable optional proxies."""
    return VideoAnalysisResult(
        face=FaceMetrics(frames_with_face=0),
        body=BodyMetrics(frames_with_pose=0, movement_classification="insufficient_data"),
        frames_analyzed=0, sample_fps=5.0, duration_seconds=0.0,
    )


class ArchetypeScoringTest(unittest.TestCase):
    def test_all_enabled_archetypes_are_configured(self):
        for archetype in ENABLED_ARCHETYPES:
            cfg = get_archetype_config(archetype)
            self.assertEqual(cfg.key, archetype)
            # Every judged metric must define a calibration band.
            for band in (
                cfg.eye_contact, cfg.expression, cfg.posture, cfg.gesture_frequency,
                cfg.gesture_range, cfg.openness, cfg.smile_naturalness,
                cfg.movement_purposefulness, cfg.spatial_use,
            ):
                self.assertTrue(hasattr(band, "score"))

    def test_registry_and_scoring_presets_agree(self):
        """Every registry-'enabled' archetype must have a scoring preset and vice versa."""
        enabled_keys = {row["key"] for row in list_archetypes() if row["status"] == "enabled"}
        preset_keys = {a.value for a in ARCHETYPE_PRESETS}
        self.assertEqual(enabled_keys, preset_keys)
        self.assertEqual(enabled_keys, {a.value for a in ENABLED_ARCHETYPES})

    def test_output_is_bounded_standardized_json(self):
        payload = normalize_scores(_rich_result(), Archetype.CORPORATE_BOARD).model_dump(mode="json")
        self.assertEqual(set(payload), CORE_KEYS | OPTIONAL_KEYS | {"archetype"})
        self.assertEqual(payload["archetype"], "corporate_board")
        self.assertIsNone(payload["smile_naturalness_score"])
        for key in CORE_KEYS:
            self.assertIsInstance(payload[key], (int, float))
            self.assertGreaterEqual(payload[key], 0.0)
            self.assertLessEqual(payload[key], 100.0)

    def test_archetypes_grade_identical_data_differently(self):
        rich = _rich_result()
        corp = normalize_scores(rich, Archetype.CORPORATE_BOARD)
        keyn = normalize_scores(rich, Archetype.MOTIVATIONAL_KEYNOTE)
        # Keynote rewards wide expression and large gestures; Corporate penalises them.
        self.assertGreater(keyn.expression_score, corp.expression_score)
        self.assertGreater(keyn.gesture_score, corp.gesture_score)

    def test_modest_expression_variation_no_longer_collapses_to_zero(self):
        result = VideoAnalysisResult(
            face=FaceMetrics(expression_variance=0.058, frames_with_face=100),
            body=BodyMetrics(),
            frames_analyzed=100,
            sample_fps=5.0,
            duration_seconds=20.0,
        )
        corporate = normalize_scores(result, Archetype.CORPORATE_BOARD)
        keynote = normalize_scores(result, Archetype.MOTIVATIONAL_KEYNOTE)
        self.assertGreater(corporate.expression_score, 40)
        self.assertLess(keynote.expression_score, corporate.expression_score)

    def test_moderate_delivery_scores_well_after_loosening(self):
        """A middling posture/expression/gesture recording should now land in
        the strong range instead of collapsing, for the strictest archetype."""
        moderate = VideoAnalysisResult(
            face=FaceMetrics(eye_contact_ratio=0.6, expression_variance=0.10, frames_with_face=100),
            body=BodyMetrics(
                posture_alignment=0.5, gesture_frequency=0.35, gesture_range=0.30, openness_ratio=0.45,
                movement_purposefulness=0.5, movement_classification="stable", spatial_use=0.3, frames_with_pose=100,
            ),
            frames_analyzed=100, sample_fps=5.0, duration_seconds=20.0,
        )
        scores = normalize_scores(moderate, Archetype.CORPORATE_BOARD)
        self.assertGreaterEqual(scores.posture_score, 80)
        self.assertGreaterEqual(scores.expression_score, 80)
        self.assertGreaterEqual(scores.gesture_score, 80)

    def test_all_archetypes_produce_valid_bounded_scores(self):
        rich = _rich_result()
        for archetype in ENABLED_ARCHETYPES:
            payload = normalize_scores(rich, archetype).model_dump(mode="json")
            self.assertEqual(set(payload), CORE_KEYS | OPTIONAL_KEYS | {"archetype"})
            self.assertEqual(payload["archetype"], archetype.value)
            for key in CORE_KEYS | OPTIONAL_KEYS:
                value = payload[key]
                if value is not None:
                    self.assertGreaterEqual(value, 0.0)
                    self.assertLessEqual(value, 100.0)

    def test_missing_tracking_degrades_without_error(self):
        degraded = _degraded_result()
        for archetype in Archetype:
            scores = normalize_scores(degraded, archetype)
            # Core scores still resolve (bounded), optionals collapse to None.
            for key in CORE_KEYS:
                self.assertLessEqual(getattr(scores, key), 100.0)
            self.assertIsNone(scores.smile_naturalness_score)
            self.assertIsNone(scores.movement_purposefulness_score)
            self.assertIsNone(scores.spatial_use_score)

    def test_expressive_archetypes_reward_variance_more_than_measured_ones(self):
        """High expression variance should score higher for warm/energetic modes
        than for the controlled ones (academic/interview/corporate)."""
        animated = _rich_result()  # expression_variance = 0.85
        expressive = normalize_scores(animated, Archetype.INFORMAL_TEAM).expression_score
        measured = normalize_scores(animated, Archetype.ACADEMIC_CONFERENCE).expression_score
        self.assertGreater(expressive, measured)

    def test_contained_archetypes_reward_minimal_gestures(self):
        """Small, contained gestures should score higher for a job interview than
        for a motivational keynote (which wants large, frequent gestures)."""
        contained = VideoAnalysisResult(
            face=FaceMetrics(eye_contact_ratio=0.8, expression_variance=0.4, head_stability=0.9, frames_with_face=100),
            body=BodyMetrics(
                posture_alignment=0.9, gesture_frequency=0.22, gesture_range=0.18, openness_ratio=0.5,
                movement_purposefulness=0.6, movement_classification="stable", spatial_use=0.12, frames_with_pose=100,
            ),
            frames_analyzed=100, sample_fps=5.0, duration_seconds=20.0,
        )
        interview = normalize_scores(contained, Archetype.JOB_INTERVIEW).gesture_score
        keynote = normalize_scores(contained, Archetype.MOTIVATIONAL_KEYNOTE).gesture_score
        self.assertGreater(interview, keynote)


if __name__ == "__main__":
    unittest.main()
