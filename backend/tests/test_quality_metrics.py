import unittest
from unittest.mock import Mock, patch

import numpy as np

from itspeak.quality import _audio_stats, blur_variance, frame_contrast, frame_luminance, select_primary_face


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


if __name__ == "__main__":
    unittest.main()
