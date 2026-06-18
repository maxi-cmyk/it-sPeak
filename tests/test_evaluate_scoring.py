import importlib.util
import json
import tempfile
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "evaluate-scoring.py"
spec = importlib.util.spec_from_file_location("evaluate_scoring", MODULE_PATH)
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


class ScoringEvaluationTests(unittest.TestCase):
    def test_evaluate_rows_checks_expected_rank_order_and_gap_warnings(self):
        manifest = {
            "voice-testing1": {
                "base": "strong",
                "script1": "flawed",
                "script2": "better",
            }
        }
        rows = [
            {"folder": "voice-testing1", "clip": "base", "aggregate_score": 100.0, "filler_label": "Clean"},
            {"folder": "voice-testing1", "clip": "script1", "aggregate_score": 86.0, "filler_label": "Distracting fillers"},
            {"folder": "voice-testing1", "clip": "script2", "aggregate_score": 89.0, "filler_label": "Some fillers"},
        ]

        result = evaluator.evaluate_rows(rows, manifest, minimum_score_gap=5.0)

        self.assertEqual(result["summary"]["ranking_failures"], 0)
        self.assertEqual(result["summary"]["warnings"], 1)
        self.assertEqual(result["folders"][0]["ranking_checks"][0]["status"], "pass")
        self.assertEqual(result["folders"][0]["gap_warnings"][0]["comparison"], "better_vs_flawed")

    def test_evaluate_rows_reports_ranking_failures(self):
        manifest = {
            "voice-testing1": {
                "base": "strong",
                "script1": "flawed",
                "script2": "better",
            }
        }
        rows = [
            {"folder": "voice-testing1", "clip": "base", "aggregate_score": 100.0, "filler_label": "Clean"},
            {"folder": "voice-testing1", "clip": "script1", "aggregate_score": 92.0, "filler_label": "Distracting fillers"},
            {"folder": "voice-testing1", "clip": "script2", "aggregate_score": 88.0, "filler_label": "Some fillers"},
        ]

        result = evaluator.evaluate_rows(rows, manifest)

        self.assertEqual(result["summary"]["ranking_failures"], 1)
        self.assertEqual(result["folders"][0]["ranking_checks"][1]["status"], "fail")

    def test_evaluate_rows_marks_holdout_folders(self):
        manifest = {
            "voice-testing4": {
                "base": "strong",
                "script1": "flawed",
                "script2": "better",
            }
        }
        rows = [
            {"folder": "voice-testing4", "clip": "base", "aggregate_score": 98.0, "filler_label": "Clean"},
            {"folder": "voice-testing4", "clip": "script1", "aggregate_score": 78.0, "filler_label": "Distracting fillers"},
            {"folder": "voice-testing4", "clip": "script2", "aggregate_score": 89.0, "filler_label": "Clean"},
        ]

        result = evaluator.evaluate_rows(rows, manifest, holdout_folders={"voice-testing4"})

        self.assertEqual(result["summary"]["holdout_folders"], 1)
        self.assertEqual(result["folders"][0]["validation_role"], "holdout")
        self.assertEqual(result["folders"][0]["ranking_checks"][0]["status"], "pass")

    def test_write_outputs_creates_json_and_text_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            result = {
                "summary": {
                    "folders": 1,
                    "ranking_failures": 0,
                    "warnings": 0,
                },
                "folders": [],
            }

            json_path, text_path = evaluator.write_outputs(result, output_dir)

            self.assertTrue(json_path.is_file())
            self.assertTrue(text_path.is_file())
            self.assertEqual(json.loads(json_path.read_text())["summary"]["folders"], 1)
            self.assertIn("ranking failures: 0", text_path.read_text())


if __name__ == "__main__":
    unittest.main()
