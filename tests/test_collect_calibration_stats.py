import csv
import importlib.util
import json
import tempfile
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "collect-calibration-stats.py"
spec = importlib.util.spec_from_file_location("collect_calibration_stats", MODULE_PATH)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def write_analysis(path, wpm, pitch_std, filler_count, word_count, overall_label="Strong", pauses=None):
    path.write_text(json.dumps({
        "summary": {
            "overall_label": overall_label,
            "headline": "sample headline",
        },
        "performance_scores": {
            "pacing_alignment": 90.0,
            "vocal_intonation_variety": 80.0,
            "word_choice_efficiency": 70.0,
            "aggregate_vocal_rating": 80.0,
        },
        "readable_metrics": {
            "pace": {"label": "On target"},
            "intonation": {"label": "On target"},
            "fillers": {"label": "Clean"},
        },
        "raw_metrics": {
            "wpm": wpm,
            "pitch_variance_std": pitch_std,
            "is_monotone_delivery": False,
        },
        "extracted_telemetry": {
            "total_filler_count": filler_count,
        },
        "transcript": {
            "word_count": word_count,
        },
        "pauses_timeline": pauses or [],
    }))


class CalibrationStatsTests(unittest.TestCase):
    def test_collect_rows_adds_base_relative_deltas(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "voice-testing1"
            folder.mkdir()
            write_analysis(folder / "base_analysis.json", 150.0, 40.0, 0, 100)
            write_analysis(
                folder / "script1_analysis.json",
                165.0,
                50.0,
                5,
                100,
                "Developing",
                pauses=[
                    {"duration": 1.5, "classification": "Strategic Pause"},
                    {"duration": 2.25, "classification": "Hesitation Gap"},
                ],
            )

            rows = collector.collect_rows(root)

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["role"], "benchmark")
            self.assertEqual(rows[0]["wpm_delta_from_base"], 0.0)
            self.assertEqual(rows[1]["role"], "test")
            self.assertEqual(rows[1]["folder"], "voice-testing1")
            self.assertEqual(rows[1]["clip"], "script1")
            self.assertEqual(rows[1]["wpm"], 165.0)
            self.assertEqual(rows[1]["pitch_delta_from_base"], 10.0)
            self.assertEqual(rows[1]["filler_per_100"], 5.0)
            self.assertEqual(rows[1]["filler_per_100_delta_from_base"], 5.0)
            self.assertEqual(rows[1]["pause_count"], 2)
            self.assertEqual(rows[1]["hesitation_gap_count"], 1)
            self.assertEqual(rows[1]["strategic_pause_count"], 1)
            self.assertEqual(rows[1]["average_pause_duration"], 1.88)
            self.assertEqual(rows[1]["longest_pause_duration"], 2.25)

    def test_write_outputs_creates_csv_and_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            rows = [{
                "folder": "voice-testing1",
                "clip": "base",
                "role": "benchmark",
                "wpm": 150.0,
                "pitch_std": 40.0,
                "filler_count": 0,
                "word_count": 100,
                "filler_per_100": 0.0,
                "wpm_delta_from_base": 0.0,
                "pitch_delta_from_base": 0.0,
                "filler_per_100_delta_from_base": 0.0,
                "pause_count": 0,
                "hesitation_gap_count": 0,
                "strategic_pause_count": 0,
                "average_pause_duration": 0.0,
                "longest_pause_duration": 0.0,
                "overall_label": "Strong",
                "headline": "sample headline",
                "pace_label": "On target",
                "intonation_label": "On target",
                "filler_label": "Clean",
                "aggregate_score": 80.0,
                "pacing_score": 90.0,
                "intonation_score": 80.0,
                "word_choice_score": 70.0,
            }]

            csv_path, json_path = collector.write_outputs(rows, output_dir)

            self.assertTrue(csv_path.is_file())
            self.assertTrue(json_path.is_file())
            with csv_path.open() as f:
                csv_rows = list(csv.DictReader(f))
            self.assertEqual(csv_rows[0]["folder"], "voice-testing1")
            json_data = json.loads(json_path.read_text())
            self.assertEqual(json_data["rows"][0]["clip"], "base")
            self.assertEqual(json_data["summary"]["benchmark_count"], 1)


if __name__ == "__main__":
    unittest.main()
