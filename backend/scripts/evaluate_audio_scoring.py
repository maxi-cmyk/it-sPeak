"""Evaluate calibration rankings without bundling the private media corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _category_rows(folder_rows, folder_manifest):
    by_clip = {row["clip"]: row for row in folder_rows}
    return {
        category: by_clip.get(clip)
        for clip, category in folder_manifest.items()
    }


def evaluate_rows(
    rows,
    manifest,
    minimum_score_gap=5.0,
    holdout_folders=None,
    target_pitch_variation=4.8,
    pitch_tolerance=1.3,
):
    holdout_folders = set(holdout_folders or [])
    rows_by_folder = {}
    for row in rows:
        rows_by_folder.setdefault(row["folder"], []).append(row)

    folders = []
    for folder_name, folder_manifest in sorted(manifest.items()):
        available = rows_by_folder.get(folder_name, [])
        categories = _category_rows(available, folder_manifest)
        strong_pitch = (categories.get("strong") or {}).get("pitch_variation_std_semitones")
        strong_pitch_on_target = (
            strong_pitch is None
            or target_pitch_variation - pitch_tolerance
            <= strong_pitch
            <= target_pitch_variation + pitch_tolerance
        )
        missing = sorted(set(folder_manifest) - {row["clip"] for row in available})
        checks = []
        for higher, lower in (("strong", "better"), ("better", "flawed")):
            if not categories.get(higher) or not categories.get(lower):
                continue
            gap = round(
                categories[higher]["aggregate_score"] - categories[lower]["aggregate_score"],
                1,
            )
            required_gap = minimum_score_gap if (higher, lower) == ("better", "flawed") else 0.0
            checks.append({
                "comparison": f"{higher}_vs_{lower}",
                "score_gap": gap,
                "required_gap": required_gap,
                "status": "pass" if gap >= required_gap else "fail",
            })
        folders.append({
            "folder": folder_name,
            "validation_role": "holdout" if folder_name in holdout_folders else "calibration",
            "missing_clips": missing,
            "strong_pitch_on_target": strong_pitch_on_target,
            "ranking_checks": checks,
        })

    return {
        "summary": {
            "folders": len(folders),
            "ranking_failures": sum(
                check["status"] == "fail"
                for folder in folders
                for check in folder["ranking_checks"]
            ),
            "missing_clips": sum(len(folder["missing_clips"]) for folder in folders),
            "base_target_failures": sum(not folder["strong_pitch_on_target"] for folder in folders),
            "minimum_score_gap": minimum_score_gap,
            "holdout_folders": sum(
                folder["validation_role"] == "holdout" for folder in folders
            ),
        },
        "folders": folders,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate calibrated audio score rankings.")
    parser.add_argument("--stats", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--holdout-folder", action="append", default=[])
    parser.add_argument("--minimum-score-gap", type=float, default=5.0)
    parser.add_argument("--target-pitch-variation", type=float, default=4.8)
    parser.add_argument("--pitch-tolerance", type=float, default=1.3)
    args = parser.parse_args(argv)

    stats = json.loads(Path(args.stats).read_text())
    manifest = json.loads(Path(args.manifest).read_text())
    result = evaluate_rows(
        stats["rows"],
        manifest,
        minimum_score_gap=args.minimum_score_gap,
        holdout_folders=args.holdout_folder,
        target_pitch_variation=args.target_pitch_variation,
        pitch_tolerance=args.pitch_tolerance,
    )
    print(json.dumps(result, indent=2))
    return int(
        result["summary"]["ranking_failures"] > 0
        or result["summary"]["missing_clips"] > 0
        or result["summary"]["base_target_failures"] > 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
