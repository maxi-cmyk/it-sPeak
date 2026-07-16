"""Celery phases: quality gate, full analysis, and retention cleanup."""

from __future__ import annotations

from pathlib import Path

from .artifact_store import cleanup_expired, read_manifest, update_manifest, video_path, write_landmarks
from .audio import analyze_audio
from .celery_app import celery_app
from .coaching import CoachingService
from .config import compute_progress, normalize_scores
from .media import extract_audio_track
from .models import AudioAnalysisResult, Archetype, ArtifactLinks, CoachingReport, NormalizedScores, QualityDisposition
from .pipeline import analyze_frames_with_artifacts, extract_frames
from .quality import run_quality_gate


def _enqueue_analysis(session_id: str):
    result = analyze_session_task.delay(session_id)
    update_manifest(session_id, status="queued", stage="Waiting for full analysis", analysis_task_id=result.id)
    return result


@celery_app.task(name="itspeak.quality_check", bind=True)
def quality_check_task(self, session_id: str) -> dict:
    try:
        update_manifest(session_id, status="quality_check", stage="Checking lighting, framing and audio")
        report = run_quality_gate(video_path(session_id))
        payload = report.model_dump(mode="json")
        if report.disposition == QualityDisposition.REJECT:
            update_manifest(session_id, status="rejected", stage="Recording needs to be replaced", quality_gate=payload)
        elif report.disposition == QualityDisposition.CONFIRM:
            update_manifest(session_id, status="needs_confirmation", stage="Review recording warnings", quality_gate=payload)
        else:
            update_manifest(session_id, quality_gate=payload)
            _enqueue_analysis(session_id)
        return payload
    except Exception as exc:
        update_manifest(session_id, status="failure", stage="Quality check failed", error=str(exc))
        raise


@celery_app.task(name="itspeak.analyze_session", bind=True)
def analyze_session_task(self, session_id: str) -> dict:
    manifest = read_manifest(session_id)
    extracted_audio: Path | None = None
    try:
        update_manifest(session_id, status="processing", stage="Analyzing facial presence and body movement")
        archetype = Archetype(manifest["archetype"])
        baseline_payload = manifest.get("baseline_scores")
        baseline = NormalizedScores(**baseline_payload) if baseline_payload else None
        visual, landmarks = analyze_frames_with_artifacts(extract_frames(str(video_path(session_id))))
        write_landmarks(session_id, landmarks)
        scores = normalize_scores(visual, archetype)

        update_manifest(session_id, status="processing", stage="Analyzing voice and transcript")
        extracted_audio = extract_audio_track(str(video_path(session_id)))
        audio = AudioAnalysisResult.model_validate(analyze_audio(extracted_audio))

        update_manifest(session_id, status="processing", stage="Generating grounded coaching")
        cards = CoachingService().generate_cards(scores=scores, archetype=archetype, audience_context=manifest.get("audience_context", ""), analysis=visual, baseline=baseline)
        report = CoachingReport(
            archetype=archetype,
            scores=scores,
            raw_analysis=visual,
            audio=audio,
            cards=cards,
            progress=compute_progress(scores, baseline),
            artifacts=ArtifactLinks(video=f"/sessions/{session_id}/video", landmarks=f"/sessions/{session_id}/landmarks"),
        )
        payload = report.model_dump(mode="json")
        update_manifest(session_id, status="success", stage="Analysis complete", report=payload, error=None)
        return payload
    except Exception as exc:
        update_manifest(session_id, status="failure", stage="Analysis failed", error=str(exc))
        raise
    finally:
        if extracted_audio:
            extracted_audio.unlink(missing_ok=True)


@celery_app.task(name="itspeak.cleanup_expired")
def cleanup_expired_task() -> int:
    return cleanup_expired()
