from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np

from itspeak.audio import (
    InsufficientPitchDataError,
    build_segment_metrics,
    extract_yin_pitch_timeline,
)


class YinPitchTest(unittest.TestCase):
    def test_silence_is_rejected_instead_of_scored_as_flat(self):
        with self.assertRaisesRegex(InsufficientPitchDataError, "No voiced audio"):
            extract_yin_pitch_timeline(np.zeros(16000), 16000)

    def test_flat_on_target_and_over_varied_synthetic_delivery(self):
        sample_rate = 16000
        duration = 4.0
        times = np.arange(int(sample_rate * duration)) / sample_rate

        def modulated_voice(variation_std):
            modulation = variation_std * np.sqrt(2.0) * np.sin(2.0 * np.pi * 1.2 * times)
            frequency = 180.0 * np.power(2.0, modulation / 12.0)
            phase = 2.0 * np.pi * np.cumsum(frequency) / sample_rate
            return 0.4 * np.sin(phase)

        measured = []
        for expected in (0.0, 4.8, 8.0):
            timeline = extract_yin_pitch_timeline(modulated_voice(expected), sample_rate)
            measured.append(float(np.std([value for value in timeline if value is not None])))

        self.assertLess(measured[0], 0.3)
        self.assertGreaterEqual(measured[1], 3.5)
        self.assertLessEqual(measured[1], 6.1)
        self.assertGreater(measured[2], 6.1)

    def test_rms_masking_and_outlier_trimming_remove_bad_frames(self):
        regular = np.linspace(170.0, 190.0, 18)
        raw_f0 = np.concatenate(([70.0], regular, [490.0, 300.0]))
        rms = np.ones_like(raw_f0)
        rms[-1] = 0.001

        with (
            patch("itspeak.audio.librosa.yin", return_value=raw_f0),
            patch("itspeak.audio.librosa.feature.rms", return_value=np.array([rms])),
        ):
            timeline = extract_yin_pitch_timeline(np.ones(4096), 16000)

        self.assertIsNone(timeline[0])
        self.assertIsNone(timeline[-2])
        self.assertIsNone(timeline[-1])
        self.assertGreaterEqual(sum(value is not None for value in timeline), 10)

    def test_segment_metrics_use_negative_and_positive_semitone_frames(self):
        words = [
            {"word": "Hello.", "clean": "hello", "start": 0.0, "end": 1.0},
        ]
        timeline = [-2.0, -1.0, 0.0, 1.0, 2.0] + [None] * 30
        metrics = build_segment_metrics(
            words,
            [],
            timeline,
            sample_rate=2560,
        )

        self.assertAlmostEqual(metrics[0]["pitch_variation_std_semitones"], np.sqrt(2.0), places=2)


if __name__ == "__main__":
    unittest.main()
