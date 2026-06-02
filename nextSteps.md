# Plan

After `voice-testing4` is recorded and processed, use it as a holdout check before tuning anything else. If the scoring still ranks `base > script2 > script1` with no evaluator warnings, the next prototype step is segment-level feedback so the engine can point to the exact phrases that caused pacing, intonation, filler, or pause issues.

## Scope
- In: holdout validation, evaluator review, segment-level audio feedback, updated calibration stats, and regression tests.
- Out: video analysis, UI work, model training, production deployment, and replacing Whisper/librosa.

## Action items in sequence
[ ] Add `voice-testing4` to `calibration_manifest.json` with `base: strong`, `script1: flawed`, and `script2: better`.
[ ] Run `python3 audio-engine --input voice-testing4` to generate the holdout analysis files.
[ ] Run `python3 collect-calibration-stats.py --input-root . --output-dir calibration-results` to refresh the full calibration table.
[ ] Run `python3 evaluate-scoring.py --stats calibration-results/calibration_stats.json --manifest calibration_manifest.json --output-dir calibration-results`.
[ ] Review `calibration-results/scoring_evaluation.txt`; continue only if `ranking failures: 0` and `warnings: 0`.
[ ] If `voice-testing4` fails, inspect whether the issue is pace, intonation, filler caps, transcription error, or benchmark recording quality before changing score weights.
[ ] Add segment splitting in `audio-engine.py`, using sentence boundaries and word timestamps to create phrase-level chunks.
[ ] Compute per-segment WPM, filler count, pause gaps, and pitch variation where enough audio exists for a reliable estimate.
[ ] Replace generic first-phrase pacing and intonation flags with segment-specific `speech_issues` entries.
[ ] Extend `collect-calibration-stats.py` with segment issue counts, such as `rushed_segment_count`, `flat_segment_count`, and `filler_segment_count`.
[ ] Add unit tests for segment splitting, per-segment issue flags, and holdout evaluator behavior.
[ ] Verify with `python3 -m unittest discover -s tests`, then rerun the full voice-testing pipeline.

