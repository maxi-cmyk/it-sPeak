"""Sequential MediaPipe video analysis and versioned display landmarks."""

from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass, field

import numpy as np

from .models import BodyMetrics, EyeContactState, FaceMetrics, MetricConfidence, VideoAnalysisResult
from .settings import get_settings

_NOSE = 1
_EYE_A = {"out": 33, "in": 133, "top": 159, "bot": 145, "iris": 468}
_EYE_B = {"out": 263, "in": 362, "top": 386, "bot": 374, "iris": 473}
_MOUTH_L, _MOUTH_R, _LIP_TOP, _LIP_BOT = 61, 291, 13, 14
_BROW_L, _BROW_R = 105, 334
_CHEEK_L, _CHEEK_R = 117, 346
_L_SHO, _R_SHO, _L_HIP, _R_HIP, _L_WRI, _R_WRI = 11, 12, 23, 24, 15, 16
_POSE_NOSE = 0


@dataclass
class FrameBatch:
    frames: np.ndarray
    fps: float
    duration_seconds: float
    source_width: int
    source_height: int
    warnings: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return int(self.frames.shape[0]) if self.frames.size else 0


def _probe_dimensions(path: str) -> tuple[int, int]:
    s = get_settings()
    result = subprocess.run([s.ffprobe_bin, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", path], capture_output=True, text=True, check=True)
    stream = json.loads(result.stdout)["streams"][0]
    return int(stream["width"]), int(stream["height"])


def extract_frames(video_path: str, sample_fps: float | None = None) -> FrameBatch:
    s = get_settings()
    fps = sample_fps or s.sample_fps
    try:
        width, height = _probe_dimensions(video_path)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not probe video: {exc}") from exc
    out_w, out_h = width, height
    if s.max_frame_width and width > s.max_frame_width:
        scale = s.max_frame_width / width
        out_w, out_h = max(2, int(width * scale) // 2 * 2), max(2, int(height * scale) // 2 * 2)
    command = [s.ffmpeg_bin, "-v", "error", "-i", video_path, "-vf", f"fps={fps},scale={out_w}:{out_h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    try:
        result = subprocess.run(command, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"")
        raise RuntimeError(f"FFmpeg could not decode the video: {detail.decode(errors='ignore') if isinstance(detail, bytes) else detail}") from exc
    frame_bytes = out_w * out_h * 3
    count = len(result.stdout) // frame_bytes
    if not count:
        raise RuntimeError("No video frames could be decoded")
    frames = np.frombuffer(result.stdout[: count * frame_bytes], dtype=np.uint8).reshape((count, out_h, out_w, 3))
    warnings = [] if count >= 10 else ["Short recording: temporal metrics have limited confidence."]
    return FrameBatch(frames, fps, count / fps, width, height, warnings)


def _distance(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def shoulder_alignment(left, right) -> float:
    """Score how level the shoulders are, regardless of image orientation."""
    horizontal_span = abs(right.x - left.x)
    vertical_offset = abs(right.y - left.y)
    shoulder_tilt = math.atan2(vertical_offset, horizontal_span)
    return max(0.0, 1.0 - shoulder_tilt / 0.45)


def posture_from_landmarks(lm) -> float | None:
    """Robust 0..1 posture proxy from pose landmarks.

    Blends two forgiving signals so a normal upright frame scores high and
    the value never collapses to zero from a single noisy measurement:

    * shoulder levelness - the shoulder line should be roughly horizontal.
    * torso uprightness - the neck (shoulder-center to nose) should be
      roughly vertical rather than leaning sideways.

    Both signals use generous tolerances (a level/upright person lands near
    1.0 and only a strong tilt or sideways lean pulls the score down).
    Returns ``None`` when the shoulders are not visible enough to judge
    posture at all, so the caller can decide how to handle missing data.
    """
    if min(lm[_L_SHO].visibility, lm[_R_SHO].visibility) < 0.25:
        return None
    span = math.hypot(lm[_R_SHO].x - lm[_L_SHO].x, lm[_R_SHO].y - lm[_L_SHO].y)
    vertical_offset = abs(lm[_R_SHO].y - lm[_L_SHO].y)
    # Tolerance of 0.5 => shoulders can slope ~27 degrees before levelness hits 0.
    levelness = 1.0 - min(1.0, (vertical_offset / max(span, 1e-4)) / 0.5)
    shoulder_cx = (lm[_L_SHO].x + lm[_R_SHO].x) / 2
    shoulder_cy = (lm[_L_SHO].y + lm[_R_SHO].y) / 2
    lean = abs(lm[_POSE_NOSE].x - shoulder_cx)
    rise = abs(shoulder_cy - lm[_POSE_NOSE].y)
    # Tolerance of 0.6 keeps a moderate head lean from tanking the score.
    uprightness = 1.0 - min(1.0, (lean / max(rise, 1e-4)) / 0.6)
    return float(max(0.0, min(1.0, 0.5 * levelness + 0.5 * uprightness)))


def _box(landmarks) -> tuple[float, float, float, float]:
    xs, ys = [p.x for p in landmarks], [p.y for p in landmarks]
    return max(0.0, min(xs)), max(0.0, min(ys)), min(1.0, max(xs)), min(1.0, max(ys))


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0.0


def _choose_face(results, previous):
    ranked = []
    for result in results:
        box = _box(result.landmark)
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        area = (box[2] - box[0]) * (box[3] - box[1])
        central = max(0, 1 - math.hypot(cx - 0.5, cy - 0.5) / 0.707)
        continuity = _iou(box, previous) if previous else 0.5
        ranked.append((0.5 * min(1, area / 0.25) + 0.2 * central + 0.3 * continuity, result, box))
    if not ranked:
        return None, None, 0.0
    ranked.sort(key=lambda row: row[0], reverse=True)
    margin = ranked[0][0] - (ranked[1][0] if len(ranked) > 1 else 0)
    confidence = min(1.0, ranked[0][0] * 0.55 + margin * 1.8)
    if previous and _iou(ranked[0][2], previous) < 0.05 and len(ranked) > 1:
        confidence *= 0.5
    return ranked[0][1], ranked[0][2], confidence


def _quantize(points, visibility=False):
    rows = []
    for point in points:
        row = [round(np.clip(point.x, 0, 1) * 65535), round(np.clip(point.y, 0, 1) * 65535)]
        if visibility:
            row.append(round(np.clip(getattr(point, "visibility", 0), 0, 1) * 255))
        rows.append(row)
    return rows


def _quantize_filtered(points, filters, fps, visibility=False):
    """Smooth only the coordinate copy exported for display overlays."""
    rows = []
    for index, point in enumerate(points):
        x_filter = filters.setdefault((index, "x"), OneEuro(fps))
        y_filter = filters.setdefault((index, "y"), OneEuro(fps))
        row = [round(np.clip(x_filter(point.x), 0, 1) * 65535), round(np.clip(y_filter(point.y), 0, 1) * 65535)]
        if visibility:
            row.append(round(np.clip(getattr(point, "visibility", 0), 0, 1) * 255))
        rows.append(row)
    return rows


def _metric_confidence(valid: int, total: int) -> MetricConfidence:
    ratio = valid / total if total else 0
    return MetricConfidence.HIGH if ratio >= 0.8 else MetricConfidence.MEDIUM if ratio >= 0.55 else MetricConfidence.LOW if ratio >= 0.3 else MetricConfidence.INSUFFICIENT


def _worst_eye_contact_lapse(rows: list[dict], fps: float) -> tuple[float | None, float | None]:
    """Longest continuous stretch where the speaker looked away from camera."""
    worst_start, worst_end = None, None
    run_start, state = None, None
    for row in rows:
        current = row["eye_contact"]
        if current != state:
            if state == EyeContactState.AWAY.value and run_start is not None:
                if worst_start is None or row["t"] - run_start > worst_end - worst_start:
                    worst_start, worst_end = run_start, row["t"]
            state, run_start = current, row["t"]
    if state == EyeContactState.AWAY.value and run_start is not None and rows:
        end = rows[-1]["t"] + (1 / fps if fps else 0)
        if worst_start is None or end - run_start > worst_end - worst_start:
            worst_start, worst_end = run_start, end
    return worst_start, worst_end


def _face_analysis(batch: FrameBatch):
    import mediapipe as mp

    s = get_settings()
    gaze_hits, face_count = 0, 0
    noses, expression = [], []
    proxy_rows, artifact = [], []
    previous = None
    display_filters = {}
    mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=False, max_num_faces=5, refine_landmarks=True, min_detection_confidence=s.min_detection_confidence, min_tracking_confidence=s.min_tracking_confidence)
    try:
        for index, frame in enumerate(batch.frames):
            found = mesh.process(frame).multi_face_landmarks or []
            result, box, identity_conf = _choose_face(found, previous)
            row = {"t": round(index / batch.fps, 3), "face": None, "face_box": None, "eye_contact": EyeContactState.UNKNOWN.value, "smile": None, "confidence": round(identity_conf, 3)}
            if result is None:
                artifact.append(row)
                continue
            lm = result.landmark
            if identity_conf < 0.25:
                row.update({"face": _quantize_filtered(lm, display_filters, batch.fps), "face_box": [round(v * 65535) for v in box]})
                artifact.append(row)
                continue
            previous = box
            face_count += 1
            eye_span = max(_distance(lm[_EYE_A["out"]], lm[_EYE_B["out"]]), 1e-5)
            iris_a = lm[_EYE_A["iris"]]
            iris_b = lm[_EYE_B["iris"]]
            def centered(eye, iris):
                left, right = lm[eye["out"]], lm[eye["in"]]
                top, bot = lm[eye["top"]], lm[eye["bot"]]
                xr = (iris.x - min(left.x, right.x)) / max(abs(right.x - left.x), 1e-5)
                yr = (iris.y - min(top.y, bot.y)) / max(abs(bot.y - top.y), 1e-5)
                return 0.25 <= xr <= 0.75 and 0.15 <= yr <= 0.85
            on_camera = centered(_EYE_A, iris_a) and centered(_EYE_B, iris_b)
            gaze_hits += int(on_camera)
            mouth_width = _distance(lm[_MOUTH_L], lm[_MOUTH_R]) / eye_span
            lip_gap = _distance(lm[_LIP_TOP], lm[_LIP_BOT]) / eye_span
            brow = (_distance(lm[_BROW_L], lm[_EYE_A["top"]]) + _distance(lm[_BROW_R], lm[_EYE_B["top"]])) / (2 * eye_span)
            expression.append((mouth_width, lip_gap, brow))
            noses.append((lm[_NOSE].x, lm[_NOSE].y))
            yaw = abs(((lm[_NOSE].x - lm[_EYE_A["out"]].x) / max(lm[_EYE_B["out"]].x - lm[_EYE_A["out"]].x, 1e-5)) - 0.5)
            face_px_w, face_px_h = (box[2] - box[0]) * batch.source_width, (box[3] - box[1]) * batch.source_height
            suitable = yaw < 0.18 and min(face_px_w, face_px_h) >= 200 and identity_conf >= 0.35
            corner_y = (lm[_MOUTH_L].y + lm[_MOUTH_R].y) / 2
            mouth_center_y = (lm[_LIP_TOP].y + lm[_LIP_BOT].y) / 2
            au12_raw = (mouth_center_y - corner_y) / eye_span
            aperture = (_distance(lm[_EYE_A["top"]], lm[_EYE_A["bot"]]) + _distance(lm[_EYE_B["top"]], lm[_EYE_B["bot"]])) / (2 * eye_span)
            cheek_gap = (_distance(lm[_CHEEK_L], lm[_EYE_A["bot"]]) + _distance(lm[_CHEEK_R], lm[_EYE_B["bot"]])) / (2 * eye_span)
            au6_raw = -(0.65 * aperture + 0.35 * cheek_gap)
            proxy_rows.append((index, au6_raw, au12_raw, suitable))
            row.update({"face": _quantize_filtered(lm, display_filters, batch.fps), "face_box": [round(v * 65535) for v in box], "eye_contact": EyeContactState.ON_CAMERA.value if on_camera else EyeContactState.AWAY.value})
            artifact.append(row)
    finally:
        mesh.close()

    suitable_rows = [row for row in proxy_rows if row[3]]
    au6 = au12 = natural = None
    if len(suitable_rows) >= max(5, math.ceil(batch.count * s.min_valid_frame_ratio)):
        raw6 = np.array([row[1] for row in suitable_rows])
        raw12 = np.array([row[2] for row in suitable_rows])
        base6, base12 = np.percentile(raw6, 20), np.percentile(raw12, 20)
        scaled6 = np.clip((raw6 - base6) / max(np.percentile(raw6, 90) - base6, 1e-4), 0, 1)
        scaled12 = np.clip((raw12 - base12) / max(np.percentile(raw12, 90) - base12, 1e-4), 0, 1)
        au6, au12 = float(np.mean(scaled6)), float(np.mean(scaled12))
        active = scaled12 > 0.25
        natural = float(np.mean(np.sqrt(scaled6[active] * scaled12[active]))) if active.any() else 0.0
        by_index = {row[0]: (float(a6), float(a12), float(math.sqrt(a6 * a12))) for row, a6, a12 in zip(suitable_rows, scaled6, scaled12)}
        for i, row in enumerate(artifact):
            if i in by_index:
                a6, a12, nat = by_index[i]
                row["smile"] = {"au6_proxy": round(a6, 4), "au12_proxy": round(a12, 4), "naturalness_proxy": round(nat, 4)}

    expr_score = 0.0
    if len(expression) > 1:
        expr_score = float(np.clip(np.mean(np.std(np.asarray(expression), axis=0)) * 18, 0, 1))
    stability = 0.0 if not noses else float(np.clip(1 - np.mean(np.std(np.asarray(noses), axis=0)) * 12, 0, 1))
    confidence = _metric_confidence(len(suitable_rows), batch.count)
    lapse_start, lapse_end = _worst_eye_contact_lapse(artifact, batch.fps)
    metrics = FaceMetrics(eye_contact_ratio=gaze_hits / face_count if face_count else 0, expression_variance=expr_score, head_stability=stability, au6_proxy=au6, au12_proxy=au12, smile_naturalness_proxy=natural, smile_confidence=confidence, frames_with_face=face_count, worst_eye_contact_lapse_start=lapse_start, worst_eye_contact_lapse_end=lapse_end)
    return metrics, artifact


class OneEuro:
    def __init__(self, frequency: float, min_cutoff=1.0, beta=0.02, derivative_cutoff=1.0):
        self.frequency, self.min_cutoff, self.beta, self.derivative_cutoff = frequency, min_cutoff, beta, derivative_cutoff
        self.value = self.derivative = None

    def _alpha(self, cutoff):
        tau = 1 / (2 * math.pi * cutoff)
        return 1 / (1 + tau * self.frequency)

    def __call__(self, value):
        derivative = 0 if self.value is None else (value - self.value) * self.frequency
        self.derivative = derivative if self.derivative is None else self._alpha(self.derivative_cutoff) * derivative + (1 - self._alpha(self.derivative_cutoff)) * self.derivative
        cutoff = self.min_cutoff + self.beta * abs(self.derivative)
        self.value = value if self.value is None else self._alpha(cutoff) * value + (1 - self._alpha(cutoff)) * self.value
        return self.value


def classify_movement(points: np.ndarray) -> tuple[str, float]:
    if len(points) < 8:
        return "insufficient_data", 0.0
    deltas = np.diff(points, axis=0)
    travel = float(np.sum(np.linalg.norm(deltas, axis=1)))
    displacement = float(np.linalg.norm(points[-1] - points[0]))
    if travel < 0.08:
        return "stable", 0.75
    directions = np.sign(deltas[:, 0])
    reversals = float(np.mean(directions[1:] * directions[:-1] < 0)) if len(directions) > 1 else 0
    if reversals > 0.35 and displacement / max(travel, 1e-5) < 0.35:
        return "repetitive_shifting", max(0.0, 1 - reversals)
    return "purposeful_translation", min(1.0, 0.5 + displacement / max(travel, 1e-5) / 2)


def spatial_coverage(boxes: np.ndarray) -> float | None:
    if len(boxes) < 5:
        return None
    x1, y1, x2, y2 = [np.percentile(boxes[:, i], [5, 95]) for i in range(4)]
    width = max(x2[1] - x1[0], 0)
    height = max(y2[1] - y1[0], 0)
    typical_scale = max(float(np.median(boxes[:, 2] - boxes[:, 0])), 1e-4)
    return float(np.clip((width * height) / (typical_scale * typical_scale * 6), 0, 1))


def _body_analysis(batch: FrameBatch):
    import mediapipe as mp

    s = get_settings()
    pose = mp.solutions.pose.Pose(static_image_mode=False, smooth_landmarks=True, min_detection_confidence=s.min_detection_confidence, min_tracking_confidence=s.min_tracking_confidence)
    artifacts, posture, wrists, openness, centers, boxes = [], [], [], [], [], []
    fx, fy = OneEuro(batch.fps), OneEuro(batch.fps)
    display_filters = {}
    cumulative_center = np.zeros(2, dtype=float)
    previous_center = None
    previous_torso = None
    pose_frames = 0
    try:
        for index, frame in enumerate(batch.frames):
            result = pose.process(frame).pose_landmarks
            row = {"t": round(index / batch.fps, 3), "pose": None, "confidence": 0.0}
            if not result:
                previous_center = previous_torso = None
                artifacts.append(row)
                continue
            pose_frames += 1
            lm = result.landmark
            posture_value = posture_from_landmarks(lm)
            if posture_value is not None:
                posture.append(posture_value)
            core_visibility = float(np.mean([lm[i].visibility for i in (_L_SHO, _R_SHO, _L_HIP, _R_HIP)]))
            if core_visibility < 0.45:
                previous_center = previous_torso = None
                artifacts.append(row)
                continue
            sx, sy = (lm[_L_SHO].x + lm[_R_SHO].x) / 2, (lm[_L_SHO].y + lm[_R_SHO].y) / 2
            hx, hy = (lm[_L_HIP].x + lm[_R_HIP].x) / 2, (lm[_L_HIP].y + lm[_R_HIP].y) / 2
            torso = max(math.hypot(sx - hx, sy - hy), 1e-4)
            wrists.append(((lm[_L_WRI].x, lm[_L_WRI].y), (lm[_R_WRI].x, lm[_R_WRI].y), torso))
            openness.append(float(abs(lm[_L_WRI].x - lm[_R_WRI].x) / torso > 1.0))
            current_center = np.array([(sx + hx) / 2, (sy + hy) / 2])
            if previous_center is not None:
                cumulative_center += (current_center - previous_center) / max((torso + previous_torso) / 2, 1e-4)
            centers.append((fx(float(cumulative_center[0])), fy(float(cumulative_center[1]))))
            previous_center, previous_torso = current_center, torso
            visible = [p for p in lm if p.visibility >= 0.5]
            boxes.append((min(p.x for p in visible), min(p.y for p in visible), max(p.x for p in visible), max(p.y for p in visible)))
            row.update({"pose": _quantize_filtered(lm, display_filters, batch.fps, visibility=True), "confidence": round(core_visibility, 3)})
            artifacts.append(row)
    finally:
        pose.close()
    gesture_frequency = gesture_range = 0.0
    if len(wrists) > 1:
        travel = []
        positions = []
        for side in (0, 1):
            pos = np.array([row[side] for row in wrists])
            scale = np.array([row[2] for row in wrists])
            travel.append(float(np.sum(np.linalg.norm(np.diff(pos, axis=0), axis=1) / scale[1:])))
            positions.append(pos / scale[:, None])
        gesture_frequency = float(np.mean(travel) / max(batch.duration_seconds, 1e-5))
        all_pos = np.concatenate(positions)
        gesture_range = float((np.percentile(all_pos[:, 0], 95) - np.percentile(all_pos[:, 0], 5)) * (np.percentile(all_pos[:, 1], 95) - np.percentile(all_pos[:, 1], 5)))
    movement_class, purposeful = classify_movement(np.asarray(centers))
    coverage = spatial_coverage(np.asarray(boxes)) if boxes else None
    confidence = _metric_confidence(len(centers), batch.count)
    if posture:
        posture_alignment = float(np.mean(posture))
    elif pose_frames:
        # A body was tracked but shoulders were never clear enough to measure
        # posture; assume a neutral-upright baseline instead of punishing with 0.
        posture_alignment = 0.7
    else:
        posture_alignment = 0.0
    metrics = BodyMetrics(posture_alignment=posture_alignment, gesture_frequency=max(0, gesture_frequency), gesture_range=max(0, gesture_range), openness_ratio=float(np.mean(openness)) if openness else 0, movement_purposefulness=None if movement_class == "insufficient_data" else purposeful, movement_classification=movement_class, movement_confidence=confidence, spatial_use=coverage, spatial_confidence=confidence if coverage is not None else MetricConfidence.INSUFFICIENT, frames_with_pose=len(posture))
    return metrics, artifacts


def analyze_frames_with_artifacts(batch: FrameBatch) -> tuple[VideoAnalysisResult, dict]:
    face, face_frames = _face_analysis(batch)
    body, body_frames = _body_analysis(batch)
    frames = []
    for index in range(batch.count):
        face_row, body_row = face_frames[index], body_frames[index]
        frames.append({**face_row, "pose": body_row["pose"], "pose_confidence": body_row["confidence"]})
    warnings = list(batch.warnings)
    if face.frames_with_face / batch.count < get_settings().min_valid_frame_ratio:
        warnings.append("Face metrics are low-confidence because detection was intermittent.")
    if body.frames_with_pose / batch.count < get_settings().min_valid_frame_ratio:
        warnings.append("Body metrics are low-confidence because shoulders/hips were not consistently visible.")
    analysis = VideoAnalysisResult(face=face, body=body, frames_analyzed=batch.count, sample_fps=batch.fps, duration_seconds=batch.duration_seconds, metric_confidence={"eye_contact": _metric_confidence(face.frames_with_face, batch.count), "smile_naturalness": face.smile_confidence, "movement_purposefulness": body.movement_confidence, "spatial_use": body.spatial_confidence}, warnings=warnings)
    artifact = {"version": "1.0", "coordinate_encoding": "uint16_normalized_xy", "visibility_encoding": "uint8", "sample_fps": batch.fps, "duration_seconds": batch.duration_seconds, "source": {"width": batch.source_width, "height": batch.source_height}, "frames": frames}
    return analysis, artifact


def analyze_frames(batch: FrameBatch) -> VideoAnalysisResult:
    return analyze_frames_with_artifacts(batch)[0]
