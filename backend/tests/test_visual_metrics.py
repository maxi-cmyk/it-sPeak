import unittest
from types import SimpleNamespace

import numpy as np

from itspeak.pipeline import OneEuro, classify_movement, posture_from_landmarks, shoulder_alignment, spatial_coverage


def _pose_landmarks(nose, left_shoulder, right_shoulder):
    """Build a minimal indexable pose-landmark list (indices 0, 11, 12)."""
    landmarks = [SimpleNamespace(x=0.5, y=0.5, visibility=0.9) for _ in range(33)]
    landmarks[0] = SimpleNamespace(**nose)
    landmarks[11] = SimpleNamespace(**left_shoulder)
    landmarks[12] = SimpleNamespace(**right_shoulder)
    return landmarks


class VisualMetricTest(unittest.TestCase):
    def test_movement_categories_are_observable(self):
        stable = np.zeros((12, 2))
        purposeful = np.column_stack((np.linspace(0, .5, 12), np.zeros(12)))
        repetitive = np.column_stack((np.tile([0, .15], 6), np.zeros(12)))
        self.assertEqual(classify_movement(stable)[0], "stable")
        self.assertEqual(classify_movement(purposeful)[0], "purposeful_translation")
        self.assertEqual(classify_movement(repetitive)[0], "repetitive_shifting")

    def test_spatial_coverage_requires_enough_visible_boxes(self):
        self.assertIsNone(spatial_coverage(np.zeros((4, 4))))
        boxes = np.array([[.1 + i * .03, .2, .4 + i * .03, .8] for i in range(10)])
        self.assertGreater(spatial_coverage(boxes), 0)

    def test_one_euro_filter_smooths_display_stream(self):
        filter_ = OneEuro(5)
        values = [filter_(value) for value in [0, 0, 1, 1]]
        self.assertGreater(values[2], 0)
        self.assertLess(values[2], 1)

    def test_level_shoulders_score_full_alignment_in_either_x_order(self):
        left = SimpleNamespace(x=.7, y=.3)
        right = SimpleNamespace(x=.3, y=.3)
        self.assertEqual(shoulder_alignment(left, right), 1.0)
        self.assertEqual(shoulder_alignment(right, left), 1.0)

    def test_sloped_shoulders_score_below_level_shoulders(self):
        left = SimpleNamespace(x=.7, y=.3)
        right = SimpleNamespace(x=.3, y=.4)
        self.assertLess(shoulder_alignment(left, right), 1.0)

    def test_upright_frontal_pose_scores_high_posture(self):
        landmarks = _pose_landmarks(
            nose={"x": 0.50, "y": 0.20, "visibility": 0.9},
            left_shoulder={"x": 0.65, "y": 0.50, "visibility": 0.9},
            right_shoulder={"x": 0.35, "y": 0.50, "visibility": 0.9},
        )
        self.assertGreaterEqual(posture_from_landmarks(landmarks), 0.85)

    def test_posture_does_not_collapse_for_slightly_angled_pose(self):
        landmarks = _pose_landmarks(
            nose={"x": 0.54, "y": 0.22, "visibility": 0.9},
            left_shoulder={"x": 0.62, "y": 0.52, "visibility": 0.9},
            right_shoulder={"x": 0.36, "y": 0.48, "visibility": 0.9},
        )
        self.assertGreater(posture_from_landmarks(landmarks), 0.6)

    def test_posture_is_none_when_shoulders_not_visible(self):
        landmarks = _pose_landmarks(
            nose={"x": 0.50, "y": 0.20, "visibility": 0.9},
            left_shoulder={"x": 0.65, "y": 0.50, "visibility": 0.1},
            right_shoulder={"x": 0.35, "y": 0.50, "visibility": 0.1},
        )
        self.assertIsNone(posture_from_landmarks(landmarks))


if __name__ == "__main__":
    unittest.main()
