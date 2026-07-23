"""Pre-analysis quality gate and independently testable measurement helpers."""

from __future__ import annotations

import json
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from .models import (
    MetricConfidence,
    QualityDisposition,
    QualityGateReport,
    QualityIssue,
    QualityMeasurements,
)
from .pipeline import extract_frames
from .settings import get_settings


# MediaPipe BlazePose landmark indices used only for *framing* classification
# (never fed back into the scoring engines).
_POSE_CORE = (11, 12, 23, 24)  # shoulders + hips
_POSE_LOWER_BODY = (25, 26, 27, 28)  # knees + ankles


@dataclass(frozen=True)
class MediaProbe:
    duration: float
    width: int
    height: int
    has_audio: bool
    format_name: str


def probe_media(path: str | Path) -> MediaProbe:
    s = get_settings()
    command = [s.ffprobe_bin, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)
        video = next(stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video")
        duration = float(payload.get("format", {}).get("duration") or video.get("duration") or 0)
        return MediaProbe(
            duration=duration,
            width=int(video["width"]),
            height=int(video["height"]),
            has_audio=any(stream.get("codec_type") == "audio" for stream in payload.get("streams", [])),
            format_name=str(payload.get("format", {}).get("format_name", "")),
        )
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as exc:
        raise RuntimeError(f"The uploaded file is not decodable video: {exc}") from exc


def frame_luminance(frame: np.ndarray) -> float:
    rgb = frame.astype(np.float32)
    return float(np.median(0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]))


def frame_contrast(frame: np.ndarray) -> float:
    gray = np.mean(frame.astype(np.float32), axis=2)
    return float(np.std(gray))


def blur_variance(frame: np.ndarray) -> float:
    gray = np.mean(frame.astype(np.float32), axis=2)
    lap = -4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    return float(np.var(lap)) if lap.size else 0.0


def bbox_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    intersection = max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(0.0, min(ay2, by2) - max(ay1, by1))
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - intersection
    return intersection / union if union > 0 else 0.0


def select_primary_face(
    candidates: Iterable[tuple[float, float, float, float]],
    previous: tuple[float, float, float, float] | None = None,
) -> tuple[tuple[float, float, float, float] | None, float]:
    """Rank area, centrality and continuity; confidence falls for near ties."""
    scored: list[tuple[float, tuple[float, float, float, float]]] = []
    for box in candidates:
        x1, y1, x2, y2 = box
        area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        centrality = max(0.0, 1.0 - math.hypot(cx - 0.5, cy - 0.5) / 0.707)
        continuity = bbox_iou(box, previous) if previous else 0.5
        scored.append((0.5 * min(1.0, area / 0.25) + 0.2 * centrality + 0.3 * continuity, box))
    if not scored:
        return None, 0.0
    scored.sort(reverse=True, key=lambda item: item[0])
    margin = scored[0][0] - (scored[1][0] if len(scored) > 1 else 0.0)
    confidence = min(1.0, 0.55 * scored[0][0] + 1.8 * margin)
    return scored[0][1], confidence


def _audio_stats(path: str | Path, duration: float) -> dict[str, float | None]:
    s = get_settings()
    command = [
        s.ffmpeg_bin, "-hide_banner", "-nostats", "-i", str(path),
        "-af", "astats=metadata=0:reset=0,silencedetect=noise=-50dB:d=0.5",
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise RuntimeError(f"Could not run FFmpeg audio checks: {exc}") from exc
    text = result.stderr
    def last(pattern: str) -> float | None:
        values = re.findall(pattern, text, re.IGNORECASE)
        finite = [float(value) for value in values if value.lower() not in {"-inf", "inf"}]
        return finite[-1] if finite else None
    silences = [float(value) for value in re.findall(r"silence_duration:\s*([\d.]+)", text)]
    return {
        "rms": last(r"RMS level dB:\s*(-?inf|-?[\d.]+)"),
        "peak": last(r"Peak level dB:\s*(-?inf|-?[\d.]+)"),
        "noise_floor": last(r"Noise floor dB:\s*(-?inf|-?[\d.]+)"),
        "silence_ratio": min(1.0, sum(silences) / duration) if duration > 0 else None,
    }


def _issue(code: str, severity: str, title: str, message: str, action: str) -> QualityIssue:
    return QualityIssue(code=code, severity=severity, title=title, message=message, action=action)


def evaluate_face_distance(
    *,
    median_face_width_px: float | None,
    median_face_height_px: float | None,
    face_tracking_confidence: float,
    full_body_ratio: float,
    head_to_body_ratio: float | None,
    min_face_px: float,
    min_tracking_confidence: float,
    full_body_min_ratio: float,
    head_ratio_bounds: tuple[float, float],
) -> QualityIssue | None:
    """Decide whether the speaker's face is usable, adapting to framing.

    Distance is judged *relative* to body visibility and facial tracking
    confidence rather than a fixed pixel floor, so a user who steps back to
    show their full posture is not falsely told their face is "too far":

    * Confidence first — if facial tracking confidence is at/above
      ``min_tracking_confidence`` the face is treated as fully readable no
      matter how small it appears (a full-body shot legitimately shrinks it).
    * Full body detected — the face is expected to be a small, proportional
      slice of standing height (~12-15%). A proportional face is never flagged
      as "too far"; a marginally low tracking confidence only produces a soft,
      non-blocking suggestion.
    * Upper-body / seated / mid-shot (no lower-body keypoints) — the face is
      compared against the mid-shot pixel reference and flagged only when it is
      *both* small and poorly tracked.

    All calculations are guarded against missing data / zero division and the
    worst outcome is a single non-blocking ``warning`` issue (never an
    ``error``), so this can never hard-block a standard-distance recording.
    """
    if median_face_width_px is None or median_face_height_px is None:
        # No face was measured at all — face-presence checks own that failure.
        return None

    readable = face_tracking_confidence >= min_tracking_confidence
    full_body = full_body_ratio >= full_body_min_ratio
    lo, hi = head_ratio_bounds
    proportional = head_to_body_ratio is not None and lo <= head_to_body_ratio <= hi

    if full_body:
        # A proportional full-body framing is correct on purpose.
        if proportional or readable:
            if readable:
                return None
            return _issue(
                "distance_precision",
                "warning",
                "Full body detected — face is naturally smaller",
                "Full body detected. Facial expression tracking precision may be slightly reduced due to distance.",
                "This is fine for posture and body-language analysis. To sharpen facial metrics you can optionally step a little closer.",
            )
        # Full body, but the face is disproportionately tiny and weakly tracked.
        return _issue(
            "distance_precision",
            "warning",
            "Face is small relative to the frame",
            "Facial expression tracking precision may be reduced at this distance.",
            "Keep your body in view but step slightly closer, or raise the camera to frame your upper body.",
        )

    # Upper-body / seated / mid-shot: trust confidence, fall back to pixels.
    if readable:
        return None
    if min(median_face_width_px, median_face_height_px) < min_face_px:
        return _issue(
            "face_pixels",
            "warning",
            "Face is too small for detailed analysis",
            f"Median face size is {median_face_width_px:.0f}×{median_face_height_px:.0f}px and tracking confidence is low.",
            f"Move closer so your face is at least {int(min_face_px)}×{int(min_face_px)} pixels.",
        )
    return None


def run_quality_gate(path: str | Path) -> QualityGateReport:
    """Sample at most 24 frames and return a pass/confirm/reject report."""
    import mediapipe as mp

    s = get_settings()
    issues: list[QualityIssue] = []
    try:
        probe = probe_media(path)
    except RuntimeError as exc:
        return QualityGateReport(
            disposition=QualityDisposition.REJECT,
            issues=[_issue("undecodable", "error", "Video cannot be read", str(exc), "Export the recording as MP4 (H.264/AAC) and upload it again.")],
            measurements=QualityMeasurements(),
        )
    if probe.duration > s.max_video_duration_seconds:
        issues.append(_issue("duration", "error", "Recording is over three minutes", f"Duration is {probe.duration:.1f} seconds.", "Trim the recording to three minutes or less."))
    if not probe.has_audio:
        issues.append(_issue("missing_audio", "error", "No audio track", "The recording has no decodable audio stream.", "Enable the microphone and record again."))

    gate_fps = min(s.gate_max_fps, s.gate_max_frames / max(probe.duration, 1.0))
    try:
        batch = extract_frames(str(path), sample_fps=max(gate_fps, 0.05))
    except RuntimeError as exc:
        return QualityGateReport(
            disposition=QualityDisposition.REJECT,
            issues=[_issue("undecodable", "error", "Video cannot be decoded", str(exc), "Export the recording as MP4 (H.264/AAC) and upload it again.")],
            measurements=QualityMeasurements(duration_seconds=probe.duration, source_width=probe.width, source_height=probe.height),
        )
    frames = batch.frames[: s.gate_max_frames]
    luminance = [frame_luminance(frame) for frame in frames]
    contrast = [frame_contrast(frame) for frame in frames]
    blur = [blur_variance(frame) for frame in frames]

    face_boxes: list[tuple[float, float, float, float]] = []
    face_widths: list[float] = []
    face_heights: list[float] = []
    face_confidences: list[float] = []
    max_faces = 0
    pose_hits = 0
    lower_body_hits = 0
    body_height_ratios: list[float] = []
    previous = None
    face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=False, max_num_faces=5, refine_landmarks=True, min_detection_confidence=s.min_detection_confidence, min_tracking_confidence=s.min_tracking_confidence)
    pose = mp.solutions.pose.Pose(static_image_mode=False, smooth_landmarks=True, min_detection_confidence=s.min_detection_confidence, min_tracking_confidence=s.min_tracking_confidence)
    try:
        for frame in frames:
            found = face_mesh.process(frame).multi_face_landmarks or []
            max_faces = max(max_faces, len(found))
            boxes = []
            for result in found:
                xs = [landmark.x for landmark in result.landmark]
                ys = [landmark.y for landmark in result.landmark]
                boxes.append((max(0.0, min(xs)), max(0.0, min(ys)), min(1.0, max(xs)), min(1.0, max(ys))))
            primary, confidence = select_primary_face(boxes, previous)
            if primary:
                previous = primary
                face_boxes.append(primary)
                face_confidences.append(confidence)
                face_widths.append((primary[2] - primary[0]) * probe.width)
                face_heights.append((primary[3] - primary[1]) * probe.height)
            pose_result = pose.process(frame).pose_landmarks
            if pose_result:
                lm = pose_result.landmark
                if np.mean([lm[i].visibility for i in _POSE_CORE]) >= 0.55:
                    pose_hits += 1
                if np.mean([lm[i].visibility for i in _POSE_LOWER_BODY]) >= 0.5:
                    lower_body_hits += 1
                visible_y = [lm[i].y for i in range(len(lm)) if lm[i].visibility >= 0.5]
                if visible_y:
                    body_height_ratios.append(max(0.0, max(visible_y) - min(visible_y)))
    finally:
        face_mesh.close()
        pose.close()

    audio = _audio_stats(path, probe.duration) if probe.has_audio else {"rms": None, "peak": None, "noise_floor": None, "silence_ratio": None}
    face_tracking_confidence = float(np.median(face_confidences)) if face_confidences else None
    median_body_height_ratio = float(np.median(body_height_ratios)) if body_height_ratios else None
    measurements = QualityMeasurements(
        duration_seconds=probe.duration, source_width=probe.width, source_height=probe.height,
        sampled_frames=len(frames), median_luminance=float(np.median(luminance)), median_contrast=float(np.median(contrast)),
        median_blur_variance=float(np.median(blur)), median_face_width_px=float(np.median(face_widths)) if face_widths else None,
        median_face_height_px=float(np.median(face_heights)) if face_heights else None,
        face_presence_ratio=len(face_boxes) / len(frames), pose_visibility_ratio=pose_hits / len(frames),
        full_body_ratio=lower_body_hits / len(frames), median_body_height_ratio=median_body_height_ratio,
        face_tracking_confidence=face_tracking_confidence, max_faces=max_faces,
        audio_rms_dbfs=audio["rms"], audio_peak_dbfs=audio["peak"], audio_noise_floor_dbfs=audio["noise_floor"], silence_ratio=audio["silence_ratio"],
    )
    if measurements.face_presence_ratio < s.min_valid_frame_ratio:
        issues.append(_issue("no_primary_face", "error", "No consistent speaker face", "A primary face could not be detected.", "Face the camera in even light and record again."))
    elif measurements.face_presence_ratio < s.gate_face_presence_min:
        issues.append(_issue("intermittent_face", "warning", "Face detection is intermittent", f"A face was visible in {measurements.face_presence_ratio:.0%} of checks.", "Keep your full face visible and avoid leaving frame."))
    if measurements.median_luminance is not None and not s.gate_luminance_low <= measurements.median_luminance <= s.gate_luminance_high:
        issues.append(_issue("lighting", "warning", "Lighting may reduce accuracy", f"Median luminance is {measurements.median_luminance:.0f}/255.", "Add soft front lighting and avoid a bright window behind you."))
    if measurements.median_contrast is not None and measurements.median_contrast < s.gate_contrast_min:
        issues.append(_issue("contrast", "warning", "Image contrast is low", f"Contrast deviation is {measurements.median_contrast:.1f}.", "Use more even lighting and clean the camera lens."))
    if measurements.median_blur_variance is not None and measurements.median_blur_variance < s.gate_blur_variance_min:
        issues.append(_issue("blur", "warning", "Video appears soft or blurred", "Facial detail may be unreliable.", "Stabilize the camera, clean the lens, and tap to focus."))
    if face_widths:
        head_to_body_ratio = None
        if measurements.median_face_height_px is not None and median_body_height_ratio and probe.height > 0:
            body_height_px = median_body_height_ratio * probe.height
            if body_height_px > 0:
                head_to_body_ratio = measurements.median_face_height_px / body_height_px
        distance_issue = evaluate_face_distance(
            median_face_width_px=measurements.median_face_width_px,
            median_face_height_px=measurements.median_face_height_px,
            face_tracking_confidence=face_tracking_confidence or 0.0,
            full_body_ratio=measurements.full_body_ratio,
            head_to_body_ratio=head_to_body_ratio,
            min_face_px=s.gate_face_pixels_min,
            min_tracking_confidence=s.gate_face_tracking_confidence_min,
            full_body_min_ratio=s.gate_full_body_min_ratio,
            head_ratio_bounds=(s.gate_head_height_ratio_min, s.gate_head_height_ratio_max),
        )
        if distance_issue is not None:
            issues.append(distance_issue)
    if measurements.pose_visibility_ratio < s.gate_pose_presence_min:
        issues.append(_issue("partial_body", "warning", "Upper body is not consistently visible", "Shoulders and hips are not visible often enough for body metrics.", "Frame your shoulders, torso and hands throughout the recording."))
    if max_faces > 1:
        issues.append(_issue("multiple_faces", "warning", "Multiple people detected", f"Up to {max_faces} faces appear in sampled frames.", "Confirm the selected central, persistent speaker or re-record alone."))
    if audio["rms"] is not None and audio["rms"] < s.gate_audio_rms_min_dbfs:
        issues.append(_issue("quiet_audio", "warning", "Audio is very quiet", f"RMS level is {audio['rms']:.1f} dBFS.", "Move closer to the microphone or increase input gain."))
    if audio["peak"] is not None and audio["peak"] > s.gate_audio_peak_max_dbfs:
        issues.append(_issue("clipped_audio", "warning", "Audio may clip", f"Peak level is {audio['peak']:.1f} dBFS.", "Lower microphone gain and leave headroom."))
    if audio["silence_ratio"] is not None and audio["silence_ratio"] > s.gate_silence_max_ratio:
        issues.append(_issue("excessive_silence", "warning", "Recording contains substantial silence", f"Silence covers {audio['silence_ratio']:.0%} of the recording.", "Trim long quiet sections or record a continuous delivery."))

    disposition = QualityDisposition.REJECT if any(i.severity == "error" for i in issues) else QualityDisposition.CONFIRM if issues else QualityDisposition.PASS
    mean_conf = float(np.mean(face_confidences)) if face_confidences else 0.0
    confidence = MetricConfidence.HIGH if mean_conf >= 0.75 else MetricConfidence.MEDIUM if mean_conf >= 0.5 else MetricConfidence.LOW if mean_conf else MetricConfidence.INSUFFICIENT
    return QualityGateReport(
        disposition=disposition, issues=issues, measurements=measurements,
        thresholds={"luminance_low": s.gate_luminance_low, "luminance_high": s.gate_luminance_high, "contrast_min": s.gate_contrast_min, "blur_variance_min": s.gate_blur_variance_min, "face_pixels_min": s.gate_face_pixels_min, "face_tracking_confidence_min": s.gate_face_tracking_confidence_min, "face_presence_min": s.gate_face_presence_min, "audio_rms_min_dbfs": s.gate_audio_rms_min_dbfs, "audio_peak_max_dbfs": s.gate_audio_peak_max_dbfs, "silence_max_ratio": s.gate_silence_max_ratio},
        primary_face_confidence=confidence,
        limitations=[],
    )
