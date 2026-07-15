"""Asynchronous video analysis pipeline.

This module owns three things:

1. **Frame extraction** — ffmpeg downsamples the source to ``sample_fps`` (2 fps
   default, ~93% fewer frames than 30 fps) and pipes raw RGB frames into numpy.
2. **MediaPipe analysis loops** — a Face module (Face Mesh) and a Body module
   (BlazePose) run *in parallel threads* over the same frame stream. MediaPipe's
   inference releases the GIL, so threads give genuine concurrency on CPU.
3. **Orchestration** — a Celery task chains extraction -> parallel analysis ->
   archetype normalization -> LLM coaching, and FastAPI endpoints enqueue jobs
   and poll results.

Every stage degrades gracefully: missing faces, low-confidence tracking or a
short clip produce *warnings* and neutral fallback scores instead of raising.
"""

from __future__ import annotations

import json
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import numpy as np
from fastapi import FastAPI, HTTPException

from .celery_app import celery_app
from .config import compute_progress, normalize_scores
from .models import (
    AnalyzeAccepted,
    AnalyzeRequest,
    Archetype,
    BodyMetrics,
    CoachingReport,
    FaceMetrics,
    JobStatus,
    NormalizedScores,
    VideoAnalysisResult,
)
from .settings import get_settings

logger = logging.getLogger("itspeak.pipeline")

# --------------------------------------------------------------------------- #
# MediaPipe landmark index constants
# --------------------------------------------------------------------------- #
# Face Mesh (with refine_landmarks=True -> 478 points, incl. irises)
_NOSE_TIP = 1
# Eye A (image-left): outer/inner corners, top/bottom lids, iris center
_EYE_A = {"out": 33, "in": 133, "top": 159, "bot": 145, "iris": 468}
# Eye B (image-right)
_EYE_B = {"out": 263, "in": 362, "top": 386, "bot": 374, "iris": 473}
_MOUTH_L, _MOUTH_R = 61, 291       # mouth corners
_LIP_TOP, _LIP_BOT = 13, 14        # inner lip gap
_BROW_L, _BROW_R = 105, 334        # inner eyebrow points
_EYE_REF_L, _EYE_REF_R = 159, 386  # upper-lid reference for brow-raise

# Pose (BlazePose, 33 landmarks)
_L_SHO, _R_SHO = 11, 12
_L_HIP, _R_HIP = 23, 24
_L_WRI, _R_WRI = 15, 16


# --------------------------------------------------------------------------- #
# 1. Frame extraction (ffmpeg)
# --------------------------------------------------------------------------- #
@dataclass
class FrameBatch:
    """Extracted frames plus timing metadata."""

    frames: np.ndarray  # shape (N, H, W, 3), dtype uint8, RGB
    fps: float
    duration_seconds: float
    warnings: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return int(self.frames.shape[0]) if self.frames.size else 0


def _probe_dimensions(path: str) -> tuple[int, int]:
    """Return (width, height) of the first video stream via ffprobe."""
    s = get_settings()
    cmd = [
        s.ffprobe_bin,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        path,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(out.stdout)
    stream = info["streams"][0]
    return int(stream["width"]), int(stream["height"])


def extract_frames(
    video_path: str, sample_fps: float | None = None
) -> FrameBatch:
    """Extract frames at ``sample_fps`` into an in-memory RGB numpy array.

    ffmpeg does the heavy lifting: it decodes, applies the ``fps`` filter (drops
    ~28 of every 30 frames), downscales for CPU, and streams raw ``rgb24`` bytes
    to stdout which we reshape into ``(N, H, W, 3)``.

    Raises
    ------
    RuntimeError
        Only for hard failures (file missing / ffmpeg absent / no decodable
        video). Callers treat this as a fatal, non-degradable error.
    """
    s = get_settings()
    fps = sample_fps or s.sample_fps

    try:
        width, height = _probe_dimensions(video_path)
    except (subprocess.CalledProcessError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not probe video '{video_path}': {exc}") from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"ffprobe binary '{s.ffprobe_bin}' not found on PATH."
        ) from exc

    # Compute downscaled, even dimensions (ffmpeg rawvideo needs exact size).
    out_w, out_h = width, height
    if s.max_frame_width and width > s.max_frame_width:
        scale = s.max_frame_width / width
        out_w = (int(width * scale) // 2) * 2
        out_h = (int(height * scale) // 2) * 2

    cmd = [
        s.ffmpeg_bin,
        "-v", "error",
        "-i", video_path,
        "-vf", f"fps={fps},scale={out_w}:{out_h}",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "pipe:1",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"ffmpeg binary '{s.ffmpeg_bin}' not found on PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"ffmpeg failed for '{video_path}': {exc.stderr.decode(errors='ignore')}"
        ) from exc

    frame_bytes = out_w * out_h * 3
    raw = proc.stdout
    n_frames = len(raw) // frame_bytes if frame_bytes else 0

    warnings: list[str] = []
    if n_frames == 0:
        raise RuntimeError(
            f"No frames decoded from '{video_path}'. Is it a valid video?"
        )
    usable = raw[: n_frames * frame_bytes]
    frames = np.frombuffer(usable, dtype=np.uint8).reshape(
        (n_frames, out_h, out_w, 3)
    )

    duration = n_frames / fps
    if n_frames < 4:
        warnings.append(
            f"Only {n_frames} frames sampled ({duration:.1f}s); temporal "
            "metrics (variance/stability) will be unreliable."
        )
    logger.info("Extracted %d frames @ %.1f fps (%dx%d)", n_frames, fps, out_w, out_h)
    return FrameBatch(frames=frames, fps=fps, duration_seconds=duration, warnings=warnings)


# --------------------------------------------------------------------------- #
# 2a. Face module (MediaPipe Face Mesh)
# --------------------------------------------------------------------------- #
def analyze_face(batch: FrameBatch) -> FaceMetrics:
    """Run Face Mesh over the frame stream and derive face metrics.

    Metrics
    -------
    * eye_contact_ratio : fraction of frames whose iris sat inside the
      camera-center tolerance box (gaze-on-camera proxy).
    * expression_variance : temporal std of mouth width, lip gap and brow raise,
      squashed into an expressiveness index in [0, 1].
    * head_stability : 1 - normalised std of the nose-tip position.
    """
    import mediapipe as mp

    s = get_settings()
    warnings: list[str] = []

    gaze_hits = 0
    face_frames = 0
    nose_pts: list[tuple[float, float]] = []
    expr_feats: list[tuple[float, float, float]] = []

    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,          # sampled frames aren't a continuous 30fps stream
        max_num_faces=1,
        refine_landmarks=True,           # iris landmarks for gaze
        min_detection_confidence=s.min_detection_confidence,
    )
    try:
        for i in range(batch.count):
            frame = batch.frames[i]
            try:
                result = face_mesh.process(frame)
            except Exception as exc:  # noqa: BLE001 - never let one frame crash the loop
                logger.warning("Face Mesh failed on frame %d: %s", i, exc)
                continue
            if not result.multi_face_landmarks:
                continue
            face_frames += 1
            lm = result.multi_face_landmarks[0].landmark

            # --- Eye contact / gaze ---
            if _is_gaze_on_camera(lm):
                gaze_hits += 1

            # --- Head position (normalised by inter-ocular distance) ---
            iod = _dist(lm[_EYE_A["out"]], lm[_EYE_B["out"]]) or 1e-6
            nose_pts.append((lm[_NOSE_TIP].x / iod, lm[_NOSE_TIP].y / iod))

            # --- Expression features (all normalised by IOD) ---
            mouth_w = _dist(lm[_MOUTH_L], lm[_MOUTH_R]) / iod
            lip_gap = _dist(lm[_LIP_TOP], lm[_LIP_BOT]) / iod
            brow_raise = (
                _dist(lm[_BROW_L], lm[_EYE_REF_L]) + _dist(lm[_BROW_R], lm[_EYE_REF_R])
            ) / (2 * iod)
            expr_feats.append((mouth_w, lip_gap, brow_raise))
    finally:
        face_mesh.close()

    # --- Graceful degradation ---
    if face_frames == 0:
        warnings.append("No face detected in any frame; face scores default to neutral.")
        logger.warning(warnings[-1])
        return FaceMetrics(
            eye_contact_ratio=0.0,
            expression_variance=0.5,
            head_stability=0.5,
            frames_with_face=0,
        )

    valid_ratio = face_frames / max(batch.count, 1)
    if valid_ratio < s.min_valid_frame_ratio:
        warnings.append(
            f"Face detected in only {valid_ratio:.0%} of frames; low confidence."
        )
        logger.warning(warnings[-1])

    eye_contact_ratio = gaze_hits / face_frames
    expression_variance = _expression_index(expr_feats)
    head_stability = _head_stability(nose_pts)

    return FaceMetrics(
        eye_contact_ratio=round(eye_contact_ratio, 4),
        expression_variance=round(expression_variance, 4),
        head_stability=round(head_stability, 4),
        frames_with_face=face_frames,
    )


def _is_gaze_on_camera(lm) -> bool:
    """Iris-centering heuristic: is the gaze roughly toward the camera?"""
    def eye_ratio(eye: dict) -> tuple[float, float]:
        xs = [lm[eye["out"]].x, lm[eye["in"]].x]
        lo_x, hi_x = min(xs), max(xs)
        h = (lm[eye["iris"]].x - lo_x) / ((hi_x - lo_x) or 1e-6)
        top_y, bot_y = lm[eye["top"]].y, lm[eye["bot"]].y
        v = (lm[eye["iris"]].y - top_y) / ((bot_y - top_y) or 1e-6)
        return h, v

    ha, va = eye_ratio(_EYE_A)
    hb, vb = eye_ratio(_EYE_B)
    h = (ha + hb) / 2.0
    v = (va + vb) / 2.0
    # Centered iris -> ~0.5 on both axes. Vertical is noisier -> looser bound.
    return abs(h - 0.5) < 0.18 and abs(v - 0.5) < 0.30


def _expression_index(feats: list[tuple[float, float, float]]) -> float:
    """Map temporal variance of expression features to an index in [0, 1]."""
    if len(feats) < 2:
        return 0.5  # not enough data to judge -> neutral
    arr = np.asarray(feats, dtype=np.float64)
    stds = arr.std(axis=0)  # per-feature temporal std (already IOD-normalised)
    # Empirically-tuned squashing: ~0.15 combined std reads as "very animated".
    raw = float(stds.sum())
    return float(np.clip(raw / 0.15, 0.0, 1.0))


def _head_stability(pts: list[tuple[float, float]]) -> float:
    """1 - normalised positional std of the nose tip (1=steady, 0=swaying)."""
    if len(pts) < 2:
        return 0.5
    arr = np.asarray(pts, dtype=np.float64)
    spread = float(np.sqrt((arr.std(axis=0) ** 2).sum()))
    # ~0.20 IOD-normalised spread reads as heavy sway.
    return float(np.clip(1.0 - spread / 0.20, 0.0, 1.0))


# --------------------------------------------------------------------------- #
# 2b. Body module (MediaPipe BlazePose)
# --------------------------------------------------------------------------- #
def analyze_body(batch: FrameBatch) -> BodyMetrics:
    """Run BlazePose over the frame stream and derive body metrics.

    Metrics
    -------
    * posture_alignment : spine verticality (shoulder-midpoint -> hip-midpoint
      angle vs. the vertical baseline).
    * gesture_frequency : per-second wrist travel, torso-normalised.
    * gesture_range : bounding-box spread of wrist positions, torso-normalised.
    * openness_ratio : fraction of frames with wrists away from the body midline.
    """
    import mediapipe as mp

    s = get_settings()
    warnings: list[str] = []

    pose_frames = 0
    posture_samples: list[float] = []
    wrist_track: list[tuple[float, float, float, float]] = []  # lx, ly, rx, ry (torso-norm)
    open_hits = 0

    pose = mp.solutions.pose.Pose(
        static_image_mode=True,
        model_complexity=1,  # 1 is the CPU sweet spot for BlazePose
        enable_segmentation=False,
        min_detection_confidence=s.min_detection_confidence,
        min_tracking_confidence=s.min_tracking_confidence,
    )
    try:
        for i in range(batch.count):
            frame = batch.frames[i]
            try:
                result = pose.process(frame)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Pose failed on frame %d: %s", i, exc)
                continue
            if not result.pose_landmarks:
                continue
            lm = result.pose_landmarks.landmark

            # Confidence gate on the core torso landmarks.
            core = [_L_SHO, _R_SHO, _L_HIP, _R_HIP]
            if any(lm[j].visibility < s.min_tracking_confidence for j in core):
                continue
            pose_frames += 1

            sho_mid = _mid(lm[_L_SHO], lm[_R_SHO])
            hip_mid = _mid(lm[_L_HIP], lm[_R_HIP])
            torso_len = _dist_xy(sho_mid, hip_mid) or 1e-6
            sho_w = _dist(lm[_L_SHO], lm[_R_SHO]) or 1e-6

            # --- Posture: angle of spine vs. vertical ---
            posture_samples.append(_verticality(sho_mid, hip_mid))

            # --- Wrists, torso-normalised, origin at shoulder midpoint ---
            lx = (lm[_L_WRI].x - sho_mid[0]) / torso_len
            ly = (lm[_L_WRI].y - sho_mid[1]) / torso_len
            rx = (lm[_R_WRI].x - sho_mid[0]) / torso_len
            ry = (lm[_R_WRI].y - sho_mid[1]) / torso_len
            wrist_track.append((lx, ly, rx, ry))

            # --- Openness: wrists laterally away from the body midline ---
            midline_x = sho_mid[0]
            spread = (abs(lm[_L_WRI].x - midline_x) + abs(lm[_R_WRI].x - midline_x))
            if spread / sho_w > 0.9:  # wrists well outside shoulder line
                open_hits += 1
    finally:
        pose.close()

    if pose_frames == 0:
        warnings.append("No body pose detected in any frame; body scores default to neutral.")
        logger.warning(warnings[-1])
        return BodyMetrics(
            posture_alignment=0.5,
            gesture_frequency=0.0,
            gesture_range=0.0,
            openness_ratio=0.5,
            frames_with_pose=0,
        )

    valid_ratio = pose_frames / max(batch.count, 1)
    if valid_ratio < s.min_valid_frame_ratio:
        warnings.append(
            f"Pose detected in only {valid_ratio:.0%} of frames; low confidence."
        )
        logger.warning(warnings[-1])

    posture_alignment = float(np.mean(posture_samples)) if posture_samples else 0.5
    gesture_frequency = _gesture_frequency(wrist_track, batch.fps)
    gesture_range = _gesture_range(wrist_track)
    openness_ratio = open_hits / pose_frames

    return BodyMetrics(
        posture_alignment=round(posture_alignment, 4),
        gesture_frequency=round(gesture_frequency, 4),
        gesture_range=round(gesture_range, 4),
        openness_ratio=round(openness_ratio, 4),
        frames_with_pose=pose_frames,
    )


def _verticality(sho_mid: tuple[float, float], hip_mid: tuple[float, float]) -> float:
    """1 when the spine is perfectly vertical, decaying with lean angle."""
    dx = sho_mid[0] - hip_mid[0]
    dy = sho_mid[1] - hip_mid[1]
    # angle from vertical, in radians (image y grows downward, hips below shoulders)
    angle = np.arctan2(abs(dx), abs(dy) + 1e-6)
    # 0 rad -> 1.0 ; ~30deg (0.52 rad) lean -> ~0.0
    return float(np.clip(1.0 - angle / 0.52, 0.0, 1.0))


def _gesture_frequency(track: list[tuple[float, float, float, float]], fps: float) -> float:
    """Mean per-second wrist travel (torso-normalised)."""
    if len(track) < 2:
        return 0.0
    arr = np.asarray(track, dtype=np.float64)
    # frame-to-frame displacement of both wrists
    d = np.diff(arr, axis=0)
    left_move = np.sqrt(d[:, 0] ** 2 + d[:, 1] ** 2)
    right_move = np.sqrt(d[:, 2] ** 2 + d[:, 3] ** 2)
    per_frame = (left_move + right_move) / 2.0
    return float(per_frame.mean() * fps)


def _gesture_range(track: list[tuple[float, float, float, float]]) -> float:
    """Bounding-box diagonal spanned by wrist positions (torso-normalised)."""
    if not track:
        return 0.0
    arr = np.asarray(track, dtype=np.float64)
    xs = np.concatenate([arr[:, 0], arr[:, 2]])
    ys = np.concatenate([arr[:, 1], arr[:, 3]])
    w = float(xs.max() - xs.min())
    h = float(ys.max() - ys.min())
    return float(np.sqrt(w * w + h * h))


# --------------------------------------------------------------------------- #
# 2c. Parallel driver
# --------------------------------------------------------------------------- #
def analyze_frames(batch: FrameBatch) -> VideoAnalysisResult:
    """Run the Face and Body modules concurrently over the same frames.

    MediaPipe inference is C++ and releases the GIL, so a 2-thread pool gives
    real parallelism for the two CPU-bound modules.
    """
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="itspeak") as pool:
        face_future = pool.submit(analyze_face, batch)
        body_future = pool.submit(analyze_body, batch)
        face = face_future.result()
        body = body_future.result()

    warnings = list(batch.warnings)
    if face.frames_with_face == 0:
        warnings.append("Face module produced fallback (neutral) scores.")
    if body.frames_with_pose == 0:
        warnings.append("Body module produced fallback (neutral) scores.")

    return VideoAnalysisResult(
        face=face,
        body=body,
        frames_analyzed=batch.count,
        sample_fps=batch.fps,
        duration_seconds=round(batch.duration_seconds, 2),
        warnings=warnings,
    )


# --------------------------------------------------------------------------- #
# 3. Celery orchestration task
# --------------------------------------------------------------------------- #
@celery_app.task(name="itspeak.analyze_video", bind=True)
def analyze_video_task(
    self,
    video_path: str,
    archetype: str,
    audience_context: str,
    baseline_scores: dict | None = None,
) -> dict:
    """Full pipeline: extract -> parallel analyze -> normalize -> coach.

    Returns a JSON-serialisable ``CoachingReport`` dict (Celery result backend).
    """
    # Imported lazily so the FastAPI process needn't load the LLM SDK.
    from .coaching import CoachingService

    arch = Archetype(archetype)
    baseline = NormalizedScores(**baseline_scores) if baseline_scores else None

    batch = extract_frames(video_path)
    analysis = analyze_frames(batch)
    scores = normalize_scores(analysis, arch)

    service = CoachingService()
    cards = service.generate_cards(
        scores=scores,
        archetype=arch,
        audience_context=audience_context,
        analysis=analysis,
        baseline=baseline,
    )

    report = CoachingReport(
        archetype=arch,
        scores=scores,
        raw_analysis=analysis,
        cards=cards,
        progress=compute_progress(scores, baseline),
    )
    return report.model_dump(mode="json")


# --------------------------------------------------------------------------- #
# 4. FastAPI surface
# --------------------------------------------------------------------------- #
app = FastAPI(title="it'sPEAK Analysis API", version="0.1.0")


@app.post("/analyze", response_model=AnalyzeAccepted, status_code=202)
def enqueue_analysis(req: AnalyzeRequest) -> AnalyzeAccepted:
    """Enqueue a video for asynchronous analysis + coaching."""
    baseline = req.baseline_scores.model_dump(mode="json") if req.baseline_scores else None
    async_result = analyze_video_task.delay(
        video_path=req.video_path,
        archetype=req.archetype.value,
        audience_context=req.audience_context,
        baseline_scores=baseline,
    )
    return AnalyzeAccepted(task_id=async_result.id)


@app.get("/result/{task_id}", response_model=JobStatus)
def get_result(task_id: str) -> JobStatus:
    """Poll a previously-enqueued analysis job."""
    async_result = celery_app.AsyncResult(task_id)
    status = async_result.status

    if status == "SUCCESS":
        return JobStatus(
            task_id=task_id,
            status=status,
            result=CoachingReport(**async_result.result),
        )
    if status == "FAILURE":
        return JobStatus(task_id=task_id, status=status, error=str(async_result.result))
    return JobStatus(task_id=task_id, status=status)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
# Geometry helpers (operate on MediaPipe NormalizedLandmark objects)
# --------------------------------------------------------------------------- #
def _dist(a, b) -> float:
    return float(np.hypot(a.x - b.x, a.y - b.y))


def _dist_xy(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def _mid(a, b) -> tuple[float, float]:
    return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)
