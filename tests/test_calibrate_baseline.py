import importlib.util
import io
from pathlib import Path
import unittest
from contextlib import redirect_stdout


MODULE_PATH = Path(__file__).resolve().parents[1] / "calibrate-baseline.py"
if not MODULE_PATH.exists():
    raise unittest.SkipTest("calibrate-baseline.py is not present in this checkout")

spec = importlib.util.spec_from_file_location("calibrate_baseline", MODULE_PATH)
calibrate_baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibrate_baseline)


class CalibrationDatasetTests(unittest.TestCase):
    def test_dataset_loader_uses_script_free_parquet_revision_with_decode_disabled(self):
        calls = []
        cast_calls = []

        class FakeDataset:
            def cast_column(self, column_name, feature):
                cast_calls.append((column_name, feature.decode))
                return self

        expected_dataset = FakeDataset()

        def fake_load_dataset(*args, **kwargs):
            calls.append((args, kwargs))
            return expected_dataset

        with redirect_stdout(io.StringIO()):
            dataset = calibrate_baseline.load_calibration_dataset(load_dataset_fn=fake_load_dataset)

        self.assertIs(dataset, expected_dataset)
        self.assertEqual(
            calls,
            [
                (
                    ("keithito/lj_speech", "main"),
                    {
                        "split": "train",
                        "streaming": True,
                        "revision": "8bf96aa8e609d5836e6c693ed3924148aeda9af1",
                    },
                ),
            ],
        )
        self.assertEqual(cast_calls, [("audio", False)])

    def test_normalized_text_is_preferred_but_spoken_text_is_supported(self):
        self.assertEqual(
            calibrate_baseline.extract_transcript({"normalized_text": "normalized", "spoken_text": "spoken"}),
            "normalized",
        )
        self.assertEqual(
            calibrate_baseline.extract_transcript({"spoken_text": "spoken"}),
            "spoken",
        )


if __name__ == "__main__":
    unittest.main()
