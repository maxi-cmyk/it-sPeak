import unittest
import numpy as np

from itspeak.pipeline import OneEuro, classify_movement, spatial_coverage


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


if __name__ == "__main__":
    unittest.main()
