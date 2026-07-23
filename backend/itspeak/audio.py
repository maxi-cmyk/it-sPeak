import time
import argparse
import contextlib
import io
import json
import os
import tempfile
from pathlib import Path

def _configure_numba_cache() -> Path:
    """Configure a writable Numba cache without changing numerical behavior."""
    cache_dir = Path(
        os.environ.setdefault(
            "NUMBA_CACHE_DIR",
            str(Path(tempfile.gettempdir()) / "itspeak-numba-cache"),
        )
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


# Configure the cache before importing Librosa/Numba. Production's entrypoint
# points this at the persistent artifact volume; local tools and tests fall back
# to the operating system's temporary directory.
_numba_cache_dir = _configure_numba_cache()

import librosa
import numpy as np
from openai import OpenAI

from .settings import get_settings

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a"}
DEFAULT_SCORING_PROFILE_PATH = Path(__file__).resolve().parents[1] / "calibrated_singapore_targets.json"
DEFAULT_SAMPLE_AUDIO_FILENAME = "sample_presentation.mp3"
DEFAULT_FILLERS = ["um", "uh", "like", "so", "basically", "actually"]
FILLER_EXAMPLE_LIMIT = 3
PITCH_FRAME_HOP_LENGTH = 512
MIN_SEGMENT_VOICED_PITCHES = 3

def is_supported_audio_file(file_path):
    return Path(file_path).suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS

def list_local_audio_files(search_dir=Path.cwd()):
    search_dir = Path(search_dir)
    return sorted(
        path
        for path in search_dir.iterdir()
        if path.is_file() and is_supported_audio_file(path)
    )

def resolve_default_audio_file(search_dir=Path.cwd()):
    search_dir = Path(search_dir)
    sample_audio = search_dir / DEFAULT_SAMPLE_AUDIO_FILENAME

    if sample_audio.is_file():
        return sample_audio

    local_audio_files = sorted(
        path
        for path in search_dir.iterdir()
        if path.is_file() and is_supported_audio_file(path)
    )

    if local_audio_files:
        return max(local_audio_files, key=lambda path: path.stat().st_mtime)

    return sample_audio

def resolve_output_path(audio_file, output_path=None, output_dir=None):
    if output_path:
        return Path(output_path)

    audio_path = Path(audio_file)
    if output_dir:
        return Path(output_dir) / f"{audio_path.stem}_analysis.json"

    return audio_path.with_name(f"{audio_path.stem}_analysis.json")

def write_analysis_json(results, output_path):
    output_path = Path(output_path)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
        f.write("\n")
    return output_path

def process_audio_files(audio_files, output_path=None, output_dir=None, analyze_fn=None, print_fn=print):
    if analyze_fn is None:
        analyze_fn = analyze_audio

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    audio_files = [Path(audio_file) for audio_file in audio_files]
    total = len(audio_files)

    for index, audio_file in enumerate(audio_files, start=1):
        with contextlib.redirect_stdout(io.StringIO()):
            results = analyze_fn(audio_file)
        write_analysis_json(results, resolve_output_path(audio_file, output_path, output_dir))
        print_fn(f"{index}/{total} complete")

    print_fn("complete")

def find_base_audio_file(audio_files):
    base_files = [Path(audio_file) for audio_file in audio_files if Path(audio_file).stem.lower() == "base"]
    if len(base_files) > 1:
        raise ValueError("Found more than one base audio file. Keep only one base.mp3 or base.m4a per test folder.")
    return base_files[0] if base_files else None

def build_folder_benchmark_profile(base_results, base_audio_file):
    template_metrics = base_results["baseline_profile"]["calibrated_metrics"]
    raw_metrics = base_results["raw_metrics"]

    return {
        "archetype": "Folder Benchmark Rehearsal",
        "dataset_source": f"Folder benchmark: {Path(base_audio_file).name}",
        "calibrated_metrics": {
            "target_wpm": raw_metrics["wpm"],
            "target_pitch_std": raw_metrics["pitch_variance_std"],
            "wpm_tolerance_margin": template_metrics["wpm_tolerance_margin"],
            "pitch_tolerance_margin": template_metrics["pitch_tolerance_margin"],
        },
    }

def build_coaching_cards(
    observed_wpm,
    observed_pitch_std,
    target_wpm,
    target_pitch_std,
    pacing_score,
    intonation_score,
    word_choice_score,
    filler_ratio,
):
    coaching_cards = []
    if pacing_score < 80.0:
        if observed_wpm > target_wpm:
            coaching_cards.append("Delivery speed is rushing past your baseline. Try slowing down your syllables.")
        else:
            coaching_cards.append("Cadence drops below target metrics. Focus on maintaining kinetic delivery speed.")

    if intonation_score < 80.0:
        if observed_pitch_std < target_pitch_std:
            coaching_cards.append("Flat tonal profile found. Intentionally color your words with expressive high/low pitch changes.")
        else:
            coaching_cards.append("Pitch variation is above the benchmark. Keep emphasis for the most important phrases.")

    if word_choice_score < 80.0:
        coaching_cards.append(f"High density of filler keywords found ({filler_ratio * 100:.1f}%). Replace 'um' or 'like' with silent breaks.")

    return coaching_cards if coaching_cards else ["Outstanding verbal performance alignment!"]

def rescore_analysis_with_profile(results, scoring_profile):
    calibrated_metrics = scoring_profile["calibrated_metrics"]
    target_wpm = calibrated_metrics["target_wpm"]
    target_pitch_std = calibrated_metrics["target_pitch_std"]
    wpm_tolerance = calibrated_metrics["wpm_tolerance_margin"]
    pitch_tolerance = calibrated_metrics["pitch_tolerance_margin"]
    observed_wpm = results["raw_metrics"]["wpm"]
    observed_pitch_std = results["raw_metrics"]["pitch_variance_std"]
    total_words = results["transcript"]["word_count"]
    filler_count = results["extracted_telemetry"]["total_filler_count"]
    filler_ratio = filler_count / total_words if total_words else 0.0

    performance_scores = build_performance_scores(
        observed_wpm,
        observed_pitch_std,
        filler_count,
        total_words,
        calibrated_metrics,
    )
    pacing_score = performance_scores["pacing_alignment"]
    intonation_score = performance_scores["vocal_intonation_variety"]
    word_choice_score = performance_scores["word_choice_efficiency"]
    coaching_cards = build_coaching_cards(
        observed_wpm,
        observed_pitch_std,
        target_wpm,
        target_pitch_std,
        pacing_score,
        intonation_score,
        word_choice_score,
        filler_ratio,
    )
    readable_metrics = build_readable_metrics(
        observed_wpm,
        observed_pitch_std,
        filler_count,
        total_words,
        calibrated_metrics,
        performance_scores,
        extract_filler_examples(results.get("speech_issues", {}).get("filler_words", [])),
    )

    results["baseline_profile"] = {
        "archetype": scoring_profile["archetype"],
        "dataset_source": scoring_profile.get("dataset_source"),
        "calibrated_metrics": calibrated_metrics,
    }
    results["performance_scores"] = performance_scores
    results["readable_metrics"] = readable_metrics
    results["summary"] = build_summary(readable_metrics, performance_scores, coaching_cards)
    results["actionable_coaching_cards"] = coaching_cards
    results["speech_issues"] = build_speech_issues(
        results.get("debug", {}).get("word_timeline", []),
        results.get("pauses_timeline", []),
        segment_metrics=results.get("debug", {}).get("segment_metrics", []),
        calibrated_metrics=calibrated_metrics,
        readable_metrics=readable_metrics,
    )
    return results

def process_benchmark_audio_files(audio_files, output_dir=None, analyze_fn=None, print_fn=print):
    if analyze_fn is None:
        analyze_fn = analyze_audio

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    audio_files = [Path(audio_file) for audio_file in audio_files]
    base_audio = find_base_audio_file(audio_files)
    if base_audio is None:
        return process_audio_files(audio_files, output_dir=output_dir, analyze_fn=analyze_fn, print_fn=print_fn)

    script_files = [audio_file for audio_file in audio_files if audio_file != base_audio]
    ordered_files = [base_audio] + script_files
    total = len(ordered_files)

    with contextlib.redirect_stdout(io.StringIO()):
        base_results = analyze_fn(base_audio)
    benchmark_profile = build_folder_benchmark_profile(base_results, base_audio)
    base_results = rescore_analysis_with_profile(base_results, benchmark_profile)
    write_analysis_json(base_results, resolve_output_path(base_audio, output_dir=output_dir))
    print_fn(f"1/{total} complete")

    for index, audio_file in enumerate(script_files, start=2):
        with contextlib.redirect_stdout(io.StringIO()):
            results = analyze_fn(audio_file, scoring_profile=benchmark_profile)
        results = rescore_analysis_with_profile(results, benchmark_profile)
        write_analysis_json(results, resolve_output_path(audio_file, output_dir=output_dir))
        print_fn(f"{index}/{total} complete")

    print_fn("complete")

def load_scoring_profile(profile_path=DEFAULT_SCORING_PROFILE_PATH):
    with open(profile_path) as f:
        return json.load(f)

def score_alignment(observed_value, target_value, tolerance_margin):
    if abs(observed_value - target_value) <= tolerance_margin:
        return 100.0

    if target_value <= 0:
        return 0.0

    deviation = abs(observed_value - target_value) - tolerance_margin
    return max(0.0, round(100.0 - (deviation / target_value * 100.0), 1))

def score_word_choice(filler_ratio, allowed_filler_ratio=0.02):
    if filler_ratio <= allowed_filler_ratio:
        return 100.0

    excess = filler_ratio - allowed_filler_ratio
    return max(0.0, round(100.0 - (excess * 200.0), 1))

def cap_score_for_label(score, label, caps):
    return min(score, caps.get(label, score))

def aggregate_performance_score(pacing_score, intonation_score, word_choice_score):
    return round(
        pacing_score * 0.35 +
        intonation_score * 0.30 +
        word_choice_score * 0.35,
        1,
    )

def build_performance_scores(
    observed_wpm,
    observed_pitch_std,
    filler_count,
    total_words,
    calibrated_metrics,
):
    target_wpm = calibrated_metrics["target_wpm"]
    target_pitch_std = calibrated_metrics["target_pitch_std"]
    wpm_tolerance = calibrated_metrics["wpm_tolerance_margin"]
    pitch_tolerance = calibrated_metrics["pitch_tolerance_margin"]
    filler_ratio = filler_count / total_words if total_words else 0.0

    pace_label = label_pace(observed_wpm, target_wpm, wpm_tolerance)
    intonation_label = label_intonation(observed_pitch_std, target_pitch_std, pitch_tolerance)
    filler_label = label_fillers(filler_count, filler_ratio)

    pacing_score = score_alignment(observed_wpm, target_wpm, wpm_tolerance)
    intonation_score = score_alignment(observed_pitch_std, target_pitch_std, pitch_tolerance)
    word_choice_score = score_word_choice(filler_ratio)

    pacing_score = cap_score_for_label(pacing_score, pace_label, {
        "Too slow": 79.0,
        "Too fast": 79.0,
    })
    intonation_score = cap_score_for_label(intonation_score, intonation_label, {
        "Too flat": 79.0,
        "Over-varied": 79.0,
    })
    word_choice_score = cap_score_for_label(word_choice_score, filler_label, {
        "Some fillers": 79.0,
        "Distracting fillers": 75.0,
    })

    return {
        "pacing_alignment": pacing_score,
        "vocal_intonation_variety": intonation_score,
        "word_choice_efficiency": word_choice_score,
        "aggregate_vocal_rating": aggregate_performance_score(
            pacing_score,
            intonation_score,
            word_choice_score,
        ),
    }

def build_transcript_text(words_data):
    return " ".join(word["word"] for word in words_data)

def extract_filler_examples(items, filler_words=DEFAULT_FILLERS, limit=FILLER_EXAMPLE_LIMIT):
    examples = []
    for item in items or []:
        if isinstance(item, dict):
            value = item.get("clean") or item.get("phrase") or item.get("word")
        else:
            value = item
        clean = str(value or "").lower().strip().strip(".,!?:;\"'()[]{}")
        if clean in filler_words and clean not in examples:
            examples.append(clean)
        if len(examples) == limit:
            break
    return examples

def label_overall_score(score):
    if score >= 85.0:
        return "Strong"
    if score >= 70.0:
        return "Developing"
    return "Needs work"

def format_target_range(target_value, tolerance_margin, unit):
    lower = round(target_value - tolerance_margin, 1)
    upper = round(target_value + tolerance_margin, 1)
    return f"{lower}-{upper} {unit}"

def label_pace(observed_wpm, target_wpm, tolerance_margin):
    if observed_wpm > target_wpm + tolerance_margin:
        return "Too fast"
    if observed_wpm < target_wpm - tolerance_margin:
        return "Too slow"
    return "On target"

def label_intonation(observed_pitch_std, target_pitch_std, tolerance_margin):
    if observed_pitch_std < target_pitch_std - tolerance_margin:
        return "Too flat"
    if observed_pitch_std > target_pitch_std + tolerance_margin:
        return "Over-varied"
    return "On target"

def label_fillers(filler_count, filler_ratio):
    if filler_ratio <= 0.02:
        return "Clean"
    if filler_ratio <= 0.06:
        return "Some fillers"
    return "Distracting fillers"

def build_readable_metrics(
    observed_wpm,
    observed_pitch_std,
    filler_count,
    total_words,
    calibrated_metrics,
    performance_scores,
    filler_examples=None,
):
    target_wpm = calibrated_metrics["target_wpm"]
    target_pitch_std = calibrated_metrics["target_pitch_std"]
    wpm_tolerance = calibrated_metrics["wpm_tolerance_margin"]
    pitch_tolerance = calibrated_metrics["pitch_tolerance_margin"]
    filler_ratio = filler_count / total_words if total_words else 0.0

    pace_label = label_pace(observed_wpm, target_wpm, wpm_tolerance)
    intonation_label = label_intonation(observed_pitch_std, target_pitch_std, pitch_tolerance)
    filler_label = label_fillers(filler_count, filler_ratio)

    pace_meanings = {
        "Too fast": "You are speaking faster than the calibrated Singapore presentation range, which can make ideas feel rushed.",
        "Too slow": "You are speaking slower than the calibrated Singapore presentation range, which can reduce energy and flow.",
        "On target": "Your speaking speed sits inside the calibrated Singapore presentation range.",
    }
    intonation_meanings = {
        "Too flat": "Your pitch variation is below the target range, so the delivery may sound less expressive.",
        "Over-varied": "Your pitch variation is above the target range, so the delivery may sound uneven or exaggerated.",
        "On target": "Your pitch variation sits inside the target range for expressive but controlled delivery.",
    }
    filler_meanings = {
        "Clean": "Your filler-word rate stayed within the target for this sample.",
        "Some fillers": "You used a few filler words. They are noticeable, but not yet dominating the delivery.",
        "Distracting fillers": "Filler words are frequent enough that they may distract from the message.",
    }

    return {
        "pace": {
            "label": pace_label,
            "value": observed_wpm,
            "unit": "words per minute",
            "target_range": format_target_range(target_wpm, wpm_tolerance, "words per minute"),
            "score": performance_scores["pacing_alignment"],
            "meaning": pace_meanings[pace_label],
        },
        "intonation": {
            "label": intonation_label,
            "value": observed_pitch_std,
            "unit": "pitch standard deviation in Hz",
            "target_range": format_target_range(target_pitch_std, pitch_tolerance, "Hz pitch standard deviation"),
            "score": performance_scores["vocal_intonation_variety"],
            "meaning": intonation_meanings[intonation_label],
        },
        "fillers": {
            "label": filler_label,
            "value": filler_count,
            "rate_per_100_words": round(filler_ratio * 100, 1),
            "examples": extract_filler_examples(filler_examples),
            "unit": "filler words",
            "target_range": "0-2 per 100 words",
            "score": performance_scores["word_choice_efficiency"],
            "meaning": filler_meanings[filler_label],
        },
    }

def build_summary(readable_metrics, performance_scores, coaching_cards):
    overall_score = performance_scores["aggregate_vocal_rating"]
    problem_labels = [
        metric["label"].lower()
        for metric in readable_metrics.values()
        if metric["label"] not in {"On target", "Clean"}
    ]

    if problem_labels:
        headline = "Main delivery issues: " + ", ".join(problem_labels) + "."
    else:
        headline = "Delivery is aligned with the current benchmark."

    top_actions = []
    pace_label = readable_metrics["pace"]["label"]
    intonation_label = readable_metrics["intonation"]["label"]
    filler_label = readable_metrics["fillers"]["label"]

    if pace_label == "Too fast":
        top_actions.append("Slow down key phrases and leave a short beat between ideas.")
    elif pace_label == "Too slow":
        top_actions.append("Tighten pauses and keep sentences moving with steadier energy.")

    if intonation_label == "Too flat":
        top_actions.append("Add more pitch contrast on important words so the message sounds less monotone.")
    elif intonation_label == "Over-varied":
        top_actions.append("Reduce pitch swings and keep emphasis for the most important phrases.")

    if filler_label != "Clean":
        top_actions.append("Replace filler words with brief silent pauses.")

    for card in coaching_cards:
        if card != "Outstanding verbal performance alignment!" and card not in top_actions:
            top_actions.append(card)

    if not top_actions:
        top_actions.append("Keep the current pacing, intonation, and filler-word control consistent.")

    overall_label = label_overall_score(overall_score)
    if overall_label == "Strong" and problem_labels:
        overall_label = "Developing"

    return {
        "overall_label": overall_label,
        "headline": headline,
        "top_actions": top_actions[:3],
    }

def phrase_from_words(words_data, limit=8):
    return " ".join(word["word"] for word in words_data[:limit])

def segment_phrase(words_data):
    return " ".join(word["word"] for word in words_data)

def is_sentence_boundary(word):
    return word.rstrip().endswith((".", "?", "!"))

def split_speech_segments(words_data):
    segments = []
    current_words = []

    for word in words_data:
        current_words.append(word)
        if is_sentence_boundary(word["word"]):
            segments.append(current_words)
            current_words = []

    if current_words:
        segments.append(current_words)

    return [
        {
            "phrase": segment_phrase(segment_words),
            "start": segment_words[0]["start"],
            "end": segment_words[-1]["end"],
            "word_count": len(segment_words),
            "words": segment_words,
        }
        for segment_words in segments
        if segment_words
    ]

def pitch_values_for_time_range(pitch_timeline, start, end, sample_rate, hop_length=PITCH_FRAME_HOP_LENGTH):
    start_frame = max(0, int(start * sample_rate / hop_length))
    end_frame = min(len(pitch_timeline), int(np.ceil(end * sample_rate / hop_length)))
    if end_frame <= start_frame:
        return []
    return [pitch for pitch in pitch_timeline[start_frame:end_frame] if pitch > 0]

def pause_gaps_for_segment(pauses, start, end):
    return [
        pause
        for pause in pauses
        if start <= pause.get("timestamp", 0.0) <= end
    ]

def build_segment_metrics(words_data, pauses, pitch_timeline, sample_rate, filler_words=DEFAULT_FILLERS):
    segment_metrics = []
    for segment in split_speech_segments(words_data):
        start = segment["start"]
        end = segment["end"]
        duration_minutes = (end - start) / 60.0
        voiced_pitches = pitch_values_for_time_range(pitch_timeline, start, end, sample_rate)
        pause_gaps = pause_gaps_for_segment(pauses, start, end)
        filler_count = sum(1 for word in segment["words"] if word["clean"] in filler_words)

        segment_metrics.append({
            "phrase": segment["phrase"],
            "start": start,
            "end": end,
            "word_count": segment["word_count"],
            "wpm": round(segment["word_count"] / duration_minutes, 1) if duration_minutes > 0 else 0.0,
            "filler_count": filler_count,
            "pause_gap_count": len(pause_gaps),
            "pause_gaps": pause_gaps,
            "pitch_variance_std": (
                round(float(np.std(voiced_pitches)), 2)
                if len(voiced_pitches) >= MIN_SEGMENT_VOICED_PITCHES
                else None
            ),
        })

    return segment_metrics

def pace_issue_meaning(label):
    meanings = {
        "Too fast": "This phrase is faster than the calibrated target range, which can make the idea feel rushed.",
        "Too slow": "This phrase is slower than the calibrated target range, which can reduce energy and flow.",
    }
    return meanings[label]

def intonation_issue_meaning(label):
    meanings = {
        "Too flat": "This phrase has less pitch variation than the target range, so it may sound monotone.",
        "Over-varied": "This phrase has more pitch variation than the target range, so emphasis may sound uneven.",
    }
    return meanings[label]

def build_segment_pacing_flags(segment_metrics, calibrated_metrics):
    flags = []
    target_wpm = calibrated_metrics["target_wpm"]
    wpm_tolerance = calibrated_metrics["wpm_tolerance_margin"]

    for segment in segment_metrics:
        pace_label = label_pace(segment["wpm"], target_wpm, wpm_tolerance)
        if pace_label == "On target":
            continue
        flags.append({
            "phrase": segment["phrase"],
            "timestamp": segment["start"],
            "issue": pace_label,
            "value": segment["wpm"],
            "meaning": pace_issue_meaning(pace_label),
            "suggestion": "Rehearse this phrase against the target range and add or shorten pauses as needed.",
        })

    return flags

def build_segment_intonation_flags(segment_metrics, calibrated_metrics):
    flags = []
    target_pitch_std = calibrated_metrics["target_pitch_std"]
    pitch_tolerance = calibrated_metrics["pitch_tolerance_margin"]

    for segment in segment_metrics:
        pitch_std = segment.get("pitch_variance_std")
        if pitch_std is None:
            continue
        intonation_label = label_intonation(pitch_std, target_pitch_std, pitch_tolerance)
        if intonation_label == "On target":
            continue
        flags.append({
            "phrase": segment["phrase"],
            "timestamp": segment["start"],
            "issue": intonation_label,
            "value": pitch_std,
            "meaning": intonation_issue_meaning(intonation_label),
            "suggestion": "Mark the key words in this phrase and keep pitch movement intentional.",
        })

    return flags

def build_speech_issues(
    words_data,
    pauses,
    filler_words=DEFAULT_FILLERS,
    readable_metrics=None,
    segment_metrics=None,
    calibrated_metrics=None,
):
    filler_issues = []
    for word in words_data:
        if word["clean"] in filler_words:
            filler_issues.append({
                "phrase": word["word"],
                "timestamp": word["start"],
                "issue": "Filler word",
                "suggestion": "Replace this with a brief silent pause or move directly to the next idea."
            })

    pause_issues = []
    for pause in pauses:
        pause_issues.append({
            "timestamp": pause["timestamp"],
            "duration": pause["duration"],
            "issue": pause["classification"],
            "suggestion": "Keep this pause if it separates ideas; shorten it if it was unplanned."
        })

    pacing_flags = []
    intonation_flags = []
    if segment_metrics and calibrated_metrics:
        pacing_flags = build_segment_pacing_flags(segment_metrics, calibrated_metrics)
        intonation_flags = build_segment_intonation_flags(segment_metrics, calibrated_metrics)
    elif readable_metrics:
        first_phrase = phrase_from_words(words_data)
        first_timestamp = words_data[0]["start"] if words_data else 0.0
        pace_metric = readable_metrics["pace"]
        intonation_metric = readable_metrics["intonation"]

        if pace_metric["label"] != "On target":
            pacing_flags.append({
                "phrase": first_phrase,
                "timestamp": first_timestamp,
                "issue": pace_metric["label"],
                "meaning": pace_metric["meaning"],
                "suggestion": "Use the target range as a guide and rehearse this section with deliberate pauses."
            })

        if intonation_metric["label"] != "On target":
            intonation_flags.append({
                "phrase": first_phrase,
                "timestamp": first_timestamp,
                "issue": intonation_metric["label"],
                "meaning": intonation_metric["meaning"],
                "suggestion": "Mark the key words in this phrase and vary pitch on those emphasis points."
            })

    return {
        "filler_words": filler_issues,
        "pause_flags": pause_issues,
        "pacing_flags": pacing_flags,
        "intonation_flags": intonation_flags
    }

def analyze_audio(file_path, pause_threshold=1.5, scoring_profile=None):
    if not is_supported_audio_file(file_path):
        supported_formats = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise ValueError(f"Unsupported audio format. Use one of: {supported_formats}")
    if not Path(file_path).is_file():
        raise FileNotFoundError(file_path)

    print("--- Starting Audio Analysis Prototype ---")
    start_time = time.time()
    if scoring_profile is None:
        scoring_profile = load_scoring_profile()
    calibrated_metrics = scoring_profile["calibrated_metrics"]
    target_wpm = calibrated_metrics["target_wpm"]
    target_pitch_std = calibrated_metrics["target_pitch_std"]
    wpm_tolerance = calibrated_metrics["wpm_tolerance_margin"]
    pitch_tolerance = calibrated_metrics["pitch_tolerance_margin"]

    # ==========================================
    # 1. ACOUSTIC ANALYSIS LAYER (Librosa)
    # ==========================================
    print("[1/2] Extracting Pitch Tracking Data...")
    # Load audio at 16kHz (Standard sample rate for speech models)
    sr = 16000
    y, _ = librosa.load(file_path, sr=sr, mono=True)

    # Compute short-time fundamental frequency (pitch) via probabilistic YIN
    f0, _, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz('C2'), # ~65Hz (Low male voice base)
        fmax=librosa.note_to_hz('C7')  # ~2093Hz (High screaming/expressive range)
    )

    # Clean up NaNs from silence zones for presentation
    pitch_timeline = np.nan_to_num(f0).astype(float).tolist()

    # Extract structural pitch metrics
    voiced_pitches = [p for p in pitch_timeline if p > 0]
    pitch_min = min(voiced_pitches) if voiced_pitches else 0
    pitch_max = max(voiced_pitches) if voiced_pitches else 0
    pitch_std = float(np.std(voiced_pitches)) if voiced_pitches else 0.0

    # Determine basic monotony threshold (Heuristic Tuning Target)
    is_monotone = bool(pitch_std < 20.0)

    # ==========================================
    # 2. SEMANTIC ANALYSIS LAYER (Whisper)
    # ==========================================
    print("[2/2] Transcribing with Word-Level Timestamps...")
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("ITSPEAK_OPENAI_API_KEY is required for transcription.")
    client = OpenAI(api_key=settings.openai_api_key)
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            file=audio_file,
            model=settings.transcription_model,
            language="en",
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )

    words_data = []
    filler_count = 0

    for word in transcript.words or []:
        text = word.word.strip()
        clean_word = text.lower().strip(".,!?")
        words_data.append({
            "word": text,
            "clean": clean_word,
            "start": round(word.start, 2),
            "end": round(word.end, 2),
        })
        if clean_word in DEFAULT_FILLERS:
            filler_count += 1

    total_words = len(words_data)
    if total_words == 0:
        return {"error": "No decipherable speech detected in audio target file."}

    # ==========================================
    # 3. HEURISTIC ANALYSIS ENGINE (Pacing & Pauses)
    # ==========================================
    pauses = []
    for i in range(len(words_data) - 1):
        current_word_end = words_data[i]["end"]
        next_word_start = words_data[i+1]["start"]
        gap = next_word_start - current_word_end

        if gap >= pause_threshold:
            # Simple context matching: Does it end a clause?
            prev_word = words_data[i]["word"]
            is_strategic = any(char in prev_word for char in ['.', ',', '?', '!'])

            pauses.append({
                "timestamp": current_word_end,
                "duration": round(gap, 2),
                "classification": "Strategic Pause" if is_strategic else "Hesitation Gap"
            })

    # Calculate overall metrics
    total_duration_mins = len(y) / sr / 60
    wpm = total_words / total_duration_mins if total_duration_mins > 0 else 0
    observed_wpm = round(wpm, 1)
    observed_pitch_std = round(pitch_std, 2)
    filler_ratio = filler_count / total_words
    segment_metrics = build_segment_metrics(words_data, pauses, pitch_timeline, sample_rate=sr)

    performance_scores = build_performance_scores(
        observed_wpm,
        observed_pitch_std,
        filler_count,
        total_words,
        calibrated_metrics,
    )
    pacing_score = performance_scores["pacing_alignment"]
    intonation_score = performance_scores["vocal_intonation_variety"]
    word_choice_score = performance_scores["word_choice_efficiency"]

    execution_time = time.time() - start_time
    print(f"Analysis complete in {execution_time:.2f}s\n")

    coaching_cards = build_coaching_cards(
        observed_wpm,
        observed_pitch_std,
        target_wpm,
        target_pitch_std,
        pacing_score,
        intonation_score,
        word_choice_score,
        filler_ratio,
    )
    readable_metrics = build_readable_metrics(
        observed_wpm,
        observed_pitch_std,
        filler_count,
        total_words,
        calibrated_metrics,
        performance_scores,
        extract_filler_examples(words_data),
    )
    summary = build_summary(readable_metrics, performance_scores, coaching_cards)

    return {
        "analysis_status": "Success",
        "summary": summary,
        "baseline_profile": {
            "archetype": scoring_profile["archetype"],
            "dataset_source": scoring_profile.get("dataset_source"),
            "calibrated_metrics": calibrated_metrics
        },
        "performance_scores": performance_scores,
        "readable_metrics": readable_metrics,
        "extracted_telemetry": {
            "measured_wpm": observed_wpm,
            "measured_pitch_std_hz": observed_pitch_std,
            "total_filler_count": filler_count
        },
        "pauses_timeline": pauses,
        "actionable_coaching_cards": coaching_cards,
        "transcript": {
            "text": build_transcript_text(words_data),
            "word_count": total_words
        },
        "speech_issues": build_speech_issues(
            words_data,
            pauses,
            segment_metrics=segment_metrics,
            calibrated_metrics=calibrated_metrics,
            readable_metrics=readable_metrics,
        ),
        "raw_metrics": {
            "wpm": observed_wpm,
            "pitch_variance_std": observed_pitch_std,
            "is_monotone_delivery": is_monotone
        },
        "debug": {
            "word_timeline": words_data,
            "segment_metrics": segment_metrics,
            "pitch_timeline_sample": pitch_timeline[::200] # Subsample data array for viewability
        }
    }

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Analyze a WAV, MP3, or M4A presentation audio file.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "audio_file",
        nargs="?",
        default=None,
        help="Path to a .wav, .mp3, or .m4a audio file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Path for the output JSON file. Defaults to <audio-stem>_analysis.json.",
    )
    parser.add_argument(
        "--input-dir",
        "--input",
        dest="input_dir",
        default=None,
        help="Folder containing .mp3/.m4a files to process in batch mode.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Folder for generated *_analysis.json files.",
    )
    args = parser.parse_args(argv)

    if args.output and args.output_dir:
        parser.error("Use either --output for one exact JSON file or --output-dir for a results folder.")

    input_dir = Path(args.input_dir) if args.input_dir else Path.cwd()
    output_dir = Path(args.output_dir) if args.output_dir else None
    audio_files = [Path(args.audio_file)] if args.audio_file else list_local_audio_files(input_dir)

    try:
        if not audio_files:
            raise FileNotFoundError(resolve_default_audio_file(input_dir))

        output_path = args.output if args.audio_file else None
        if args.audio_file:
            process_audio_files(audio_files, output_path=output_path, output_dir=output_dir)
        else:
            process_benchmark_audio_files(audio_files, output_dir=output_dir)
    except FileNotFoundError:
        print("Please place one or more .mp3/.m4a files in the input folder or pass a specific audio file.")
    except ValueError as exc:
        print(exc)

if __name__ == "__main__":
    main()
