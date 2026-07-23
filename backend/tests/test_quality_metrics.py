import unittest
from unittest.mock import Mock, patch

import numpy as np

from itspeak.quality import (
    _audio_stats,
    blur_variance,
    evaluate_face_distance,
    frame_contrast,
    frame_luminance,
    select_primary_face,
)

_DISTANCE_DEFAULTS = dict(
    min_face_px=200,
    min_tracking_confidence=0.5,
    full_body_min_ratio=0.5,
    head_ratio_bounds=(0.08, 0.24),
)


class QualityMetricTest(unittest.TestCase):
    def test_image_measurements_distinguish_dark_flat_and_sharp_frames(self):
        dark = np.full((20, 20, 3), 20, dtype=np.uint8)
        checker = np.indices((20, 20)).sum(axis=0) % 2 * 255
        checker = np.repeat(checker[..., None], 3, axis=2).astype(np.uint8)
        self.assertAlmostEqual(frame_luminance(dark), 20, delta=.1)
        self.assertEqual(frame_contrast(dark), 0)
        self.assertGreater(frame_contrast(checker), 100)
        self.assertGreater(blur_variance(checker), blur_variance(dark))

    def test_primary_face_prefers_continuity_over_a_new_bystander(self):
        previous = (.25, .2, .55, .65)
        primary, confidence = select_primary_face([(.26, .2, .56, .65), (.65, .1, .98, .65)], previous)
        self.assertEqual(primary, (.26, .2, .56, .65))
        self.assertGreater(confidence, .4)

    def test_ffmpeg_audio_statistics_are_parsed(self):
        stderr = "RMS level dB: -28.0\nPeak level dB: -0.5\nNoise floor dB: -52.0\nsilence_duration: 2.0\nsilence_duration: 1.0"
        with patch("itspeak.quality.subprocess.run", return_value=Mock(stderr=stderr)):
            stats = _audio_stats("talk.mp4", 10)
        self.assertEqual(stats["rms"], -28)
        self.assertEqual(stats["peak"], -.5)
        self.assertAlmostEqual(stats["silence_ratio"], .3)


class FaceDistanceTest(unittest.TestCase):
    def _evaluate(self, **overrides):
        params = dict(
            median_face_width_px=260.0,
            median_face_height_px=300.0,
            face_tracking_confidence=0.8,
            full_body_ratio=0.0,
            head_to_body_ratio=None,
            **_DISTANCE_DEFAULTS,
        )
        params.update(overrides)
        return evaluate_face_distance(**params)

    def test_close_up_shot_passes_cleanly(self):
        self.assertIsNone(self._evaluate())

    def test_full_body_proportional_face_is_never_flagged_too_far(self):
        # Tiny face, but proportional to a detected full body and well tracked.
        issue = self._evaluate(
            median_face_width_px=40.0, median_face_height_px=60.0,
            face_tracking_confidence=0.72, full_body_ratio=0.9, head_to_body_ratio=0.13,
        )
        self.assertIsNone(issue)

    def test_full_body_low_confidence_is_a_soft_non_blocking_suggestion(self):
        issue = self._evaluate(
            median_face_width_px=40.0, median_face_height_px=60.0,
            face_tracking_confidence=0.35, full_body_ratio=0.9, head_to_body_ratio=0.13,
        )
        self.assertIsNotNone(issue)
        self.assertEqual(issue.code, "distance_precision")
        self.assertEqual(issue.severity, "warning")
        self.assertIn("Full body detected", issue.message)

    def test_upper_body_small_and_poorly_tracked_face_is_flagged(self):
        issue = self._evaluate(
            median_face_width_px=120.0, median_face_height_px=140.0,
            face_tracking_confidence=0.3, full_body_ratio=0.0, head_to_body_ratio=None,
        )
        self.assertIsNotNone(issue)
        self.assertEqual(issue.code, "face_pixels")
        self.assertEqual(issue.severity, "warning")

    def test_confident_tracking_overrides_small_pixels_on_a_mid_shot(self):
        # A standard-distance shot with solid tracking is never blocked.
        self.assertIsNone(
            self._evaluate(
                median_face_width_px=120.0, median_face_height_px=140.0,
                face_tracking_confidence=0.7, full_body_ratio=0.0, head_to_body_ratio=None,
            )
        )

    def test_missing_face_measurements_degrade_without_error(self):
        self.assertIsNone(self._evaluate(median_face_width_px=None, median_face_height_px=None))

    def test_no_issue_is_ever_a_hard_error(self):
        for conf in (0.0, 0.3, 0.5, 0.9):
            for full in (0.0, 0.9):
                issue = self._evaluate(
                    median_face_width_px=50.0, median_face_height_px=70.0,
                    face_tracking_confidence=conf, full_body_ratio=full,
                    head_to_body_ratio=0.02,  # disproportionately tiny
                )
                if issue is not None:
                    self.assertEqual(issue.severity, "warning")


if __name__ == "__main__":
    unittest.main()
