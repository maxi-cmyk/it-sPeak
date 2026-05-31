# it-sPeak
manoj thulasidas

## Safe audio test batches

Keep benchmark files in the project root, and put new experiment clips in a separate folder:

```bash
mkdir -p audio_tests_round_1
```

Use clear clip names:

```text
audio_tests_round_1/base-person-a.m4a
audio_tests_round_1/flawed-person-a.m4a
audio_tests_round_1/better-person-a.m4a
```

Run the audio engine with an explicit input folder and output folder:

```bash
python3 audio-engine --input audio_tests_round_1 --output-dir audio_tests_round_1/results
```

This writes `*_analysis.json` files into `audio_tests_round_1/results` instead of overwriting benchmark analysis files in the project root.

For your numbered voice test folders, use:

```bash
python3 audio-engine --input voice-testing1
python3 audio-engine --input voice-testing2
```

Each folder can contain `.m4a` or `.mp3` files. If the folder contains `base.m4a` or `base.mp3`, that file becomes the folder benchmark. Other clips, such as `script1.m4a` and `script2.mp3`, are scored against that benchmark.

Without `--output-dir`, the JSON files are written beside the audio files inside that selected folder only.

## Calibration stats

After running the voice test folders, collect one tuning table:

```bash
python3 collect-calibration-stats.py --input-root . --output-dir calibration-results
```

This writes:

```text
calibration-results/calibration_stats.csv
calibration-results/calibration_stats.json
```

Use the CSV to compare each `script1` and `script2` clip against the `base` clip in the same folder.
It includes raw metrics, base-relative deltas, filler rates, pause counts, hesitation counts, and pause durations.

Then evaluate whether the scores match your expected ranking:

```bash
python3 evaluate-scoring.py --stats calibration-results/calibration_stats.json --manifest calibration_manifest.json --output-dir calibration-results
```

The manifest marks each clip as `strong`, `better`, or `flawed`. The evaluator checks that `base` scores above `script2`, and `script2` scores above `script1`, then warns when the gaps are too small to be convincing.
