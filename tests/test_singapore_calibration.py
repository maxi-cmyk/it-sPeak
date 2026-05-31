import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

import numpy as np


MODULE_PATH = Path(__file__).resolve().parents[1] / "calibrate-singapore-baselines.py"
spec = importlib.util.spec_from_file_location("singapore_calibration", MODULE_PATH)
singapore_calibration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(singapore_calibration)


class SingaporeCalibrationTests(unittest.TestCase):
    def test_stream_samples_reads_audio_from_remote_zip_members(self):
        metadata = [{"filename": "0000.wav", "text": "hello singapore"}]
        open_calls = []
        fake_file = object()

        class FakeOpen:
            def __init__(self, path, mode):
                open_calls.append((path, mode))

            def __enter__(self):
                return fake_file

            def __exit__(self, exc_type, exc, traceback):
                return False

        read_audio = Mock(return_value=(np.array([0.0, 0.1], dtype=np.float32), 16000))

        samples = list(
            singapore_calibration.iter_singapore_samples(
                metadata,
                max_samples=1,
                open_fn=FakeOpen,
                read_audio_fn=read_audio,
            )
        )

        self.assertEqual(open_calls, [(singapore_calibration.build_imda_wav_path("0000.wav"), "rb")])
        read_audio.assert_called_once_with(fake_file, dtype="float32")
        self.assertEqual(samples[0]["text"], "hello singapore")
        self.assertEqual(samples[0]["sampling_rate"], 16000)
        np.testing.assert_array_equal(samples[0]["audio"], np.array([0.0, 0.1], dtype=np.float32))

    def test_multichannel_audio_is_collapsed_to_mono(self):
        metadata = [{"filename": "0001.wav", "text": "mono please"}]

        class FakeOpen:
            def __init__(self, path, mode):
                pass

            def __enter__(self):
                return object()

            def __exit__(self, exc_type, exc, traceback):
                return False

        stereo = np.array([[1.0, -1.0], [0.5, 0.25]], dtype=np.float32)

        samples = list(
            singapore_calibration.iter_singapore_samples(
                metadata,
                max_samples=1,
                open_fn=FakeOpen,
                read_audio_fn=Mock(return_value=(stereo, 16000)),
            )
        )

        np.testing.assert_allclose(samples[0]["audio"], np.array([0.0, 0.375], dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
