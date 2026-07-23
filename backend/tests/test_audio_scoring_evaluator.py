from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_audio_scoring.py"
SPEC = importlib.util.spec_from_file_location("evaluate_audio_scoring", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AudioScoringEvaluatorTest(unittest.TestCase):
    def test_requires_rankings_to_clear_the_minimum_gap_and_marks_holdout(self):
        rows = [
            {"folder": "calibration", "clip": "base", "aggregate_score": 90, "pitch_variation_std_semitones": 4.8},
            {"folder": "calibration", "clip": "better", "aggregate_score": 84},
            {"folder": "calibration", "clip": "flawed", "aggregate_score": 78},
            {"folder": "holdout", "clip": "base", "aggregate_score": 85, "pitch_variation_std_semitones": 7.0},
            {"folder": "holdout", "clip": "better", "aggregate_score": 86},
            {"folder": "holdout", "clip": "flawed", "aggregate_score": 80},
        ]
        manifest = {
            "calibration": {"base": "strong", "better": "better", "flawed": "flawed"},
            "holdout": {"base": "strong", "better": "better", "flawed": "flawed"},
        }

        result = MODULE.evaluate_rows(rows, manifest, holdout_folders={"holdout"})

        self.assertEqual(result["summary"]["ranking_failures"], 1)
        self.assertEqual(result["summary"]["base_target_failures"], 1)
        self.assertEqual(result["summary"]["holdout_folders"], 1)
        self.assertEqual(result["folders"][1]["validation_role"], "holdout")
        self.assertEqual(result["folders"][0]["ranking_checks"][0]["required_gap"], 0.0)
        self.assertEqual(result["folders"][0]["ranking_checks"][1]["required_gap"], 5.0)


if __name__ == "__main__":
    unittest.main()
