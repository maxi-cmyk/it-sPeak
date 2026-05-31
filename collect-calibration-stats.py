import argparse
import csv
import json
from pathlib import Path


FIELDNAMES = [
    "folder",
    "clip",
    "role",
    "wpm",
    "pitch_std",
    "filler_count",
    "word_count",
    "filler_per_100",
    "pause_count",
    "hesitation_gap_count",
    "strategic_pause_count",
    "average_pause_duration",
    "longest_pause_duration",
    "wpm_delta_from_base",
    "pitch_delta_from_base",
    "filler_per_100_delta_from_base",
    "overall_label",
    "headline",
    "pace_label",
    "intonation_label",
    "filler_label",
    "aggregate_score",
    "pacing_score",
    "intonation_score",
    "word_choice_score",
]


def clip_name_from_analysis_path(path):
    return path.name.removesuffix("_analysis.json")


def load_analysis(path):
    with open(path) as f:
        return json.load(f)


def pause_metrics(analysis):
    pauses = analysis.get("pauses_timeline", [])
    durations = [pause.get("duration", 0.0) for pause in pauses]

    return {
        "pause_count": len(pauses),
        "hesitation_gap_count": sum(1 for pause in pauses if pause.get("classification") == "Hesitation Gap"),
        "strategic_pause_count": sum(1 for pause in pauses if pause.get("classification") == "Strategic Pause"),
        "average_pause_duration": round(sum(durations) / len(durations), 2) if durations else 0.0,
        "longest_pause_duration": round(max(durations), 2) if durations else 0.0,
    }


def metric_row(folder, path, analysis):
    clip = clip_name_from_analysis_path(path)
    word_count = analysis["transcript"]["word_count"]
    filler_count = analysis["extracted_telemetry"]["total_filler_count"]
    filler_per_100 = round((filler_count / word_count * 100.0), 2) if word_count else 0.0
    scores = analysis["performance_scores"]
    readable_metrics = analysis.get("readable_metrics", {})
    pauses = pause_metrics(analysis)

    return {
        "folder": folder.name,
        "clip": clip,
        "role": "benchmark" if clip == "base" else "test",
        "wpm": analysis["raw_metrics"]["wpm"],
        "pitch_std": analysis["raw_metrics"]["pitch_variance_std"],
        "filler_count": filler_count,
        "word_count": word_count,
        "filler_per_100": filler_per_100,
        "pause_count": pauses["pause_count"],
        "hesitation_gap_count": pauses["hesitation_gap_count"],
        "strategic_pause_count": pauses["strategic_pause_count"],
        "average_pause_duration": pauses["average_pause_duration"],
        "longest_pause_duration": pauses["longest_pause_duration"],
        "wpm_delta_from_base": None,
        "pitch_delta_from_base": None,
        "filler_per_100_delta_from_base": None,
        "overall_label": analysis["summary"]["overall_label"],
        "headline": analysis["summary"]["headline"],
        "pace_label": readable_metrics.get("pace", {}).get("label"),
        "intonation_label": readable_metrics.get("intonation", {}).get("label"),
        "filler_label": readable_metrics.get("fillers", {}).get("label"),
        "aggregate_score": scores["aggregate_vocal_rating"],
        "pacing_score": scores["pacing_alignment"],
        "intonation_score": scores["vocal_intonation_variety"],
        "word_choice_score": scores["word_choice_efficiency"],
    }


def add_base_deltas(rows):
    base_row = next((row for row in rows if row["clip"] == "base"), None)
    if base_row is None:
        raise ValueError(f"{rows[0]['folder']} has no base_analysis.json benchmark")

    for row in rows:
        row["wpm_delta_from_base"] = round(row["wpm"] - base_row["wpm"], 1)
        row["pitch_delta_from_base"] = round(row["pitch_std"] - base_row["pitch_std"], 2)
        row["filler_per_100_delta_from_base"] = round(
            row["filler_per_100"] - base_row["filler_per_100"],
            2,
        )

    return rows


def collect_rows(root_dir):
    root_dir = Path(root_dir)
    all_rows = []

    for folder in sorted(path for path in root_dir.glob("voice-testing*") if path.is_dir()):
        analysis_paths = sorted(folder.glob("*_analysis.json"))
        if not analysis_paths:
            continue

        folder_rows = [
            metric_row(folder, path, load_analysis(path))
            for path in analysis_paths
        ]
        all_rows.extend(add_base_deltas(folder_rows))

    return all_rows


def summarize(rows):
    benchmark_rows = [row for row in rows if row["role"] == "benchmark"]
    test_rows = [row for row in rows if row["role"] == "test"]

    def average(values):
        return round(sum(values) / len(values), 2) if values else None

    return {
        "folder_count": len({row["folder"] for row in rows}),
        "benchmark_count": len(benchmark_rows),
        "test_clip_count": len(test_rows),
        "benchmark_wpm_average": average([row["wpm"] for row in benchmark_rows]),
        "benchmark_pitch_std_average": average([row["pitch_std"] for row in benchmark_rows]),
        "test_wpm_delta_average": average([row["wpm_delta_from_base"] for row in test_rows]),
        "test_pitch_delta_average": average([row["pitch_delta_from_base"] for row in test_rows]),
        "test_filler_per_100_delta_average": average([
            row["filler_per_100_delta_from_base"]
            for row in test_rows
        ]),
    }


def write_outputs(rows, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "calibration_stats.csv"
    json_path = output_dir / "calibration_stats.json"

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w") as f:
        json.dump({"summary": summarize(rows), "rows": rows}, f, indent=2)
        f.write("\n")

    return csv_path, json_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Collect calibration stats from voice-testing folders.")
    parser.add_argument("--input-root", default=".", help="Root folder containing voice-testing* folders.")
    parser.add_argument("--output-dir", default="calibration-results", help="Folder for CSV and JSON outputs.")
    args = parser.parse_args(argv)

    rows = collect_rows(args.input_root)
    if not rows:
        raise SystemExit("No *_analysis.json files found under voice-testing* folders.")

    csv_path, json_path = write_outputs(rows, args.output_dir)
    print(f"Wrote {len(rows)} rows to {csv_path}")
    print(f"Wrote summary to {json_path}")


if __name__ == "__main__":
    main()
