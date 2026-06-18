import argparse
import json
from pathlib import Path


EXPECTED_RANK = {
    "flawed": 1,
    "better": 2,
    "strong": 3,
}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def rows_by_folder(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["folder"], {})[row["clip"]] = row
    return grouped


def expected_clips_by_category(folder_manifest):
    grouped = {}
    for clip, category in folder_manifest.items():
        grouped.setdefault(category, []).append(clip)
    return grouped


def row_for_category(folder_rows, category_clips):
    if not category_clips:
        return None
    if len(category_clips) > 1:
        raise ValueError("Each category should map to one clip for this prototype evaluator.")
    return folder_rows.get(category_clips[0])


def compare_scores(higher_category, higher_row, lower_category, lower_row):
    score_gap = round(higher_row["aggregate_score"] - lower_row["aggregate_score"], 1)
    return {
        "comparison": f"{higher_category}_vs_{lower_category}",
        "higher_clip": higher_row["clip"],
        "lower_clip": lower_row["clip"],
        "higher_score": higher_row["aggregate_score"],
        "lower_score": lower_row["aggregate_score"],
        "score_gap": score_gap,
        "status": "pass" if score_gap > 0 else "fail",
    }


def evaluate_folder(folder_name, folder_rows, folder_manifest, minimum_score_gap, holdout_folders=None):
    holdout_folders = holdout_folders or set()
    categories = expected_clips_by_category(folder_manifest)
    strong_row = row_for_category(folder_rows, categories.get("strong", []))
    better_row = row_for_category(folder_rows, categories.get("better", []))
    flawed_row = row_for_category(folder_rows, categories.get("flawed", []))

    missing = [
        clip
        for clip in folder_manifest
        if clip not in folder_rows
    ]
    ranking_checks = []
    gap_warnings = []

    if strong_row and better_row:
        ranking_checks.append(compare_scores("strong", strong_row, "better", better_row))
    if better_row and flawed_row:
        ranking_checks.append(compare_scores("better", better_row, "flawed", flawed_row))

    for check in ranking_checks:
        if check["status"] == "pass" and check["score_gap"] < minimum_score_gap:
            gap_warnings.append({
                "comparison": check["comparison"],
                "message": f"Score gap is only {check['score_gap']}; scoring may be too forgiving.",
            })

    issue_expectations = []
    if flawed_row:
        issue_expectations.append({
            "clip": flawed_row["clip"],
            "expectation": "flawed clip should have distracting fillers",
            "observed": flawed_row.get("filler_label"),
            "status": "pass" if flawed_row.get("filler_label") == "Distracting fillers" else "warn",
        })
    if better_row:
        issue_expectations.append({
            "clip": better_row["clip"],
            "expectation": "better clip should not have distracting fillers",
            "observed": better_row.get("filler_label"),
            "status": "pass" if better_row.get("filler_label") != "Distracting fillers" else "warn",
        })

    return {
        "folder": folder_name,
        "validation_role": "holdout" if folder_name in holdout_folders else "calibration",
        "missing_clips": missing,
        "ranking_checks": ranking_checks,
        "gap_warnings": gap_warnings,
        "issue_expectations": issue_expectations,
    }


def evaluate_rows(rows, manifest, minimum_score_gap=5.0, holdout_folders=None):
    holdout_folders = set(holdout_folders or [])
    grouped_rows = rows_by_folder(rows)
    folder_results = []

    for folder_name in sorted(manifest):
        folder_results.append(evaluate_folder(
            folder_name,
            grouped_rows.get(folder_name, {}),
            manifest[folder_name],
            minimum_score_gap,
            holdout_folders=holdout_folders,
        ))

    ranking_failures = sum(
        1
        for folder in folder_results
        for check in folder["ranking_checks"]
        if check["status"] == "fail"
    )
    warnings = sum(len(folder["gap_warnings"]) for folder in folder_results)
    warnings += sum(
        1
        for folder in folder_results
        for check in folder["issue_expectations"]
        if check["status"] == "warn"
    )
    missing_clips = sum(len(folder["missing_clips"]) for folder in folder_results)

    return {
        "summary": {
            "folders": len(folder_results),
            "ranking_failures": ranking_failures,
            "warnings": warnings,
            "missing_clips": missing_clips,
            "minimum_score_gap": minimum_score_gap,
            "holdout_folders": sum(
                1 for folder in folder_results if folder["validation_role"] == "holdout"
            ),
        },
        "folders": folder_results,
    }


def write_outputs(result, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "scoring_evaluation.json"
    text_path = output_dir / "scoring_evaluation.txt"

    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    summary = result["summary"]
    lines = [
        "Scoring Evaluation",
        f"folders: {summary['folders']}",
        f"ranking failures: {summary['ranking_failures']}",
        f"warnings: {summary['warnings']}",
        f"missing clips: {summary.get('missing_clips', 0)}",
        f"minimum score gap: {summary.get('minimum_score_gap', 0)}",
        "",
    ]
    for folder in result["folders"]:
        lines.append(f"{folder['folder']} ({folder.get('validation_role', 'calibration')})")
        for check in folder["ranking_checks"]:
            lines.append(
                f"- {check['comparison']}: {check['status']} "
                f"({check['higher_score']} vs {check['lower_score']}, gap {check['score_gap']})"
            )
        for warning in folder["gap_warnings"]:
            lines.append(f"- warning: {warning['message']}")
        for check in folder["issue_expectations"]:
            if check["status"] == "warn":
                lines.append(f"- warning: {check['expectation']} observed {check['observed']}")
        lines.append("")

    text_path.write_text("\n".join(lines))
    return json_path, text_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate whether audio scoring matches expected clip ranking.")
    parser.add_argument("--stats", default="calibration-results/calibration_stats.json")
    parser.add_argument("--manifest", default="calibration_manifest.json")
    parser.add_argument("--output-dir", default="calibration-results")
    parser.add_argument("--minimum-score-gap", type=float, default=5.0)
    parser.add_argument(
        "--holdout-folder",
        action="append",
        default=[],
        help="Folder name to label as holdout validation in the report. Can be passed more than once.",
    )
    args = parser.parse_args(argv)

    stats = load_json(args.stats)
    manifest = load_json(args.manifest)
    result = evaluate_rows(
        stats["rows"],
        manifest,
        minimum_score_gap=args.minimum_score_gap,
        holdout_folders=set(args.holdout_folder),
    )
    json_path, text_path = write_outputs(result, args.output_dir)
    print(f"Wrote scoring evaluation to {json_path}")
    print(f"Wrote text report to {text_path}")


if __name__ == "__main__":
    main()
