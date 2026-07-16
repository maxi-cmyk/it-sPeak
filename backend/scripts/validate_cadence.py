"""Compare 2/5/10 fps visual outputs on one or more local fixture clips."""

from __future__ import annotations

import argparse
import json
import time

from itspeak.pipeline import analyze_frames, extract_frames


def available_metrics(result):
    values = {
        "eye_contact": result.face.eye_contact_ratio,
        "expression": result.face.expression_variance,
        "smile_naturalness": result.face.smile_naturalness_proxy,
        "posture": result.body.posture_alignment,
        "movement_purposefulness": result.body.movement_purposefulness,
        "spatial_use": result.body.spatial_use,
    }
    return {key: value for key, value in values.items() if value is not None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("clips", nargs="+")
    parser.add_argument("--tolerance", type=float, default=.05)
    args = parser.parse_args()
    failed = False
    reports = []
    for clip in args.clips:
        runs = {}
        for fps in (2, 5, 10):
            started = time.perf_counter()
            result = analyze_frames(extract_frames(clip, sample_fps=fps))
            runs[fps] = {"elapsed_seconds": round(time.perf_counter() - started, 3), "movement_classification": result.body.movement_classification, "metrics": available_metrics(result)}
        common = set(runs[5]["metrics"]) & set(runs[10]["metrics"])
        deltas = {key: abs(runs[5]["metrics"][key] - runs[10]["metrics"][key]) for key in common}
        cadence_ok = all(delta <= args.tolerance for delta in deltas.values()) and runs[5]["movement_classification"] == runs[10]["movement_classification"]
        failed |= not cadence_ok
        reports.append({"clip": clip, "five_fps_accepted": cadence_ok, "five_vs_ten_deltas": deltas, "runs": runs})
    print(json.dumps(reports, indent=2))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
