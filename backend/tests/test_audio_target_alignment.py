from __future__ import annotations

import unittest

from itspeak.audio import build_performance_scores, build_readable_metrics


CALIBRATED_METRICS = {
    "target_wpm": 160.7,
    "target_pitch_std": 36.37,
    "wpm_tolerance_margin": 12.0,
    "pitch_tolerance_margin": 20.0,
}


class AudioTargetAlignmentTest(unittest.TestCase):
    def test_outside_pace_range_cannot_be_proficient(self):
        scores = build_performance_scores(190.9, 36.37, 0, 100, CALIBRATED_METRICS)
        metrics = build_readable_metrics(190.9, 36.37, 0, 100, CALIBRATED_METRICS, scores)

        self.assertEqual(metrics["pace"]["target_range"], "148.7-172.7 words per minute")
        self.assertEqual(metrics["pace"]["label"], "Too fast")
        self.assertEqual(scores["pacing_alignment"], 79.0)

    def test_filler_proficiency_uses_the_documented_rate(self):
        within_target = build_performance_scores(160.7, 36.37, 2, 100, CALIBRATED_METRICS)
        above_target = build_performance_scores(160.7, 36.37, 4, 100, CALIBRATED_METRICS)
        metrics = build_readable_metrics(160.7, 36.37, 4, 100, CALIBRATED_METRICS, above_target, ["um", "like", "um", "so", "actually"])

        self.assertEqual(within_target["word_choice_efficiency"], 100.0)
        self.assertEqual(above_target["word_choice_efficiency"], 79.0)
        self.assertEqual(metrics["fillers"]["rate_per_100_words"], 4.0)
        self.assertEqual(metrics["fillers"]["label"], "Some fillers")
        self.assertEqual(metrics["fillers"]["examples"], ["um", "like", "so"])


if __name__ == "__main__":
    unittest.main()
