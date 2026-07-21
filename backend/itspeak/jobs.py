"""Celery phases: quality gate, full analysis, and retention cleanup."""

from __future__ import annotations

from pathlib import Path

from .artifact_store import cleanup_expired, landmarks_path, read_manifest, update_manifest, video_path, write_landmarks
from .audio import analyze_audio
from .celery_app import celery_app
from .coaching import CoachingService
from .config import compute_progress, normalize_scores
from .media import extract_audio_track
from .models import AudioAnalysisResult, Archetype, ArtifactLinks, CoachingReport, ImprovementArea, ImprovementGuidance, Module, NormalizedScores, QualityDisposition
from .pipeline import analyze_frames_with_artifacts, extract_frames
from .persistence import get_persistence
from .progress import detect_stagnation
from .quality import run_quality_gate


def _enqueue_analysis(session_id: str):
    result = analyze_session_task.delay(session_id)
    update_manifest(session_id, status="queued", stage="Waiting for full analysis", analysis_task_id=result.id)
    get_persistence().update_session(session_id, {"status": "queued", "stage": "Waiting for full analysis", "task_id": result.id})
    return result


@celery_app.task(name="itspeak.quality_check", bind=True)
def quality_check_task(self, session_id: str) -> dict:
    try:
        update_manifest(session_id, status="quality_check", stage="Checking lighting, framing and audio")
        get_persistence().update_session(session_id, {"status": "quality_check", "stage": "Checking lighting, framing and audio"})
        report = run_quality_gate(video_path(session_id))
        payload = report.model_dump(mode="json")
        if report.disposition == QualityDisposition.REJECT:
            update_manifest(session_id, status="rejected", stage="Recording needs to be replaced", quality_gate=payload)
            get_persistence().update_session(session_id, {"status": "rejected", "stage": "Recording needs to be replaced", "quality_gate": payload})
        elif report.disposition == QualityDisposition.CONFIRM:
            update_manifest(session_id, status="needs_confirmation", stage="Review recording warnings", quality_gate=payload)
            get_persistence().update_session(session_id, {"status": "needs_confirmation", "stage": "Review recording warnings", "quality_gate": payload})
        else:
            update_manifest(session_id, quality_gate=payload)
            get_persistence().update_session(session_id, {"quality_gate": payload})
            _enqueue_analysis(session_id)
        return payload
    except Exception as exc:
        update_manifest(session_id, status="failure", stage="Quality check failed", error=str(exc))
        get_persistence().update_session(session_id, {"status": "failure", "stage": "Quality check failed", "error": str(exc)})
        raise


def _average(values: list[float | None]) -> float | None:
    available = [float(value) for value in values if value is not None]
    return round(sum(available) / len(available), 2) if available else None


def _aggregates(report: CoachingReport) -> dict[str, float | None]:
    face = _average([report.scores.eye_contact_score, report.scores.expression_score, report.scores.smile_naturalness_score])
    body = _average([report.scores.posture_score, report.scores.gesture_score, report.scores.movement_purposefulness_score, report.scores.spatial_use_score])
    vocal_raw = report.audio.performance_scores.get("aggregate_vocal_rating")
    vocal = round(float(vocal_raw), 2) if vocal_raw is not None else None
    return {"overall_score": _average([face, body, vocal]), "vocal_score": vocal, "face_score": face, "body_score": body}


def _apply_improvement_focus(report: CoachingReport, aggregates: dict[str, float | None] | None = None) -> CoachingReport:
    audio_scores = report.audio.performance_scores
    score_by_area = {
        ImprovementArea.PACING: audio_scores.get("pacing_alignment"),
        ImprovementArea.INTONATION: audio_scores.get("vocal_intonation_variety"),
        ImprovementArea.FILLER_WORDS: audio_scores.get("word_choice_efficiency"),
        ImprovementArea.EYE_CONTACT: report.scores.eye_contact_score,
        ImprovementArea.FACIAL_EXPRESSION: report.scores.expression_score,
        ImprovementArea.POSTURE: report.scores.posture_score,
        ImprovementArea.GESTURES: report.scores.gesture_score,
    }
    labels = {
        ImprovementArea.PACING: "Pacing",
        ImprovementArea.INTONATION: "Vocal variety",
        ImprovementArea.FILLER_WORDS: "Filler-word control",
        ImprovementArea.EYE_CONTACT: "Eye contact",
        ImprovementArea.FACIAL_EXPRESSION: "Facial expression",
        ImprovementArea.POSTURE: "Posture",
        ImprovementArea.GESTURES: "Gestures",
    }
    selected = list(dict.fromkeys(report.improvement_areas))
    def needs_work(area: ImprovementArea) -> bool:
        score = score_by_area.get(area)
        return score is not None and score <= 80

    ranked = sorted(selected, key=lambda area: score_by_area[area] if score_by_area[area] is not None else 101)
    guidance: list[ImprovementGuidance] = []
    for priority, area in enumerate(ranked, start=1):
        score = score_by_area[area]
        if score is None:
            continue
        proficient = score > 80
        next_area = next((candidate for candidate in ranked if candidate != area), None)
        if proficient and next_area:
            message = f"You are proficient in {labels[area]} at {score:.0f}. Prioritise {labels[next_area]}, your lowest-scoring other selected area."
        elif proficient:
            message = f"You are proficient in {labels[area]} at {score:.0f}. Maintain this strength and select another area for your next growth target."
        else:
            message = f"Priority {priority}: improve {labels[area]} ({score:.0f}), starting with the lowest-scoring selected area."
        guidance.append(ImprovementGuidance(area=area, score=score, priority=priority, proficient=proficient, message=message))

    priority_by_area = {item.area: item.priority for item in guidance}
    areas_by_module = {
        Module.FACE: {ImprovementArea.EYE_CONTACT, ImprovementArea.FACIAL_EXPRESSION},
        Module.BODY: {ImprovementArea.POSTURE, ImprovementArea.GESTURES},
    }
    priority_by_module = {
        module: min((priority_by_area[area] for area in areas if area in priority_by_area and needs_work(area)), default=99)
        for module, areas in areas_by_module.items()
    }
    focused_cards = []
    for card in report.cards:
        module_areas = areas_by_module.get(card.module, set())
        if any(area in selected and needs_work(area) for area in module_areas):
            focused_cards.append(card)
    report.cards = sorted(
        focused_cards,
        key=lambda card: priority_by_module.get(card.module, 99),
    )
    audio_actions = {
        ImprovementArea.PACING: "Rehearse with a metronome-like sentence rhythm, then repeat while keeping key phrases inside your target pace.",
        ImprovementArea.INTONATION: "Mark one emphasis word per sentence and deliberately vary pitch only on those words.",
        ImprovementArea.FILLER_WORDS: "Replace each filler word with a silent beat; pause, breathe, then begin the next phrase cleanly.",
    }
    report.audio.actionable_coaching_cards = [
        audio_actions[area]
        for area in ranked
        if area in audio_actions and needs_work(area)
    ]
    report.improvement_guidance = guidance
    return report


def _durable_cards(report: CoachingReport) -> list[dict]:
    cards = [card.model_dump(mode="json") for card in report.cards]
    cards.extend({"module": "audio", "problem": text, "importance": "This vocal pattern affects the clarity and impact of the rehearsal.", "actionable_fix": "Apply this cue deliberately in the next rehearsal."} for text in report.audio.actionable_coaching_cards)
    return cards


@celery_app.task(name="itspeak.analyze_session", bind=True)
def analyze_session_task(self, session_id: str) -> dict:
    manifest = read_manifest(session_id)
    extracted_audio: Path | None = None
    uploaded_paths: list[str] = []
    try:
        update_manifest(session_id, status="processing", stage="Analyzing facial presence and body movement")
        get_persistence().update_session(session_id, {"status": "processing", "stage": "Analyzing facial presence and body movement"})
        archetype = Archetype(manifest["archetype"])
        improvement_areas = [ImprovementArea(area) for area in manifest.get("improvement_areas", [area.value for area in ImprovementArea])]
        baseline_payload = manifest.get("baseline_scores")
        baseline = NormalizedScores(**baseline_payload) if baseline_payload else None
        visual, landmarks = analyze_frames_with_artifacts(extract_frames(str(video_path(session_id))))
        write_landmarks(session_id, landmarks)
        scores = normalize_scores(visual, archetype)

        update_manifest(session_id, status="processing", stage="Analyzing voice and transcript")
        get_persistence().update_session(session_id, {"status": "processing", "stage": "Analyzing voice and transcript"})
        extracted_audio = extract_audio_track(str(video_path(session_id)))
        audio = AudioAnalysisResult.model_validate(analyze_audio(extracted_audio))

        update_manifest(session_id, status="processing", stage="Generating grounded coaching")
        get_persistence().update_session(session_id, {"status": "processing", "stage": "Generating grounded coaching"})
        cards = CoachingService().generate_cards(scores=scores, archetype=archetype, audience_context=manifest.get("audience_context", ""), analysis=visual, baseline=baseline, improvement_areas=improvement_areas)
        report = CoachingReport(
            archetype=archetype,
            scores=scores,
            raw_analysis=visual,
            audio=audio,
            cards=cards,
            improvement_areas=improvement_areas,
            progress=compute_progress(scores, baseline),
            stagnation=detect_stagnation(scores, baseline, reference_label="your baseline session"),
            artifacts=ArtifactLinks(video=f"/sessions/{session_id}/video", landmarks=f"/sessions/{session_id}/landmarks"),
        )
        aggregates = _aggregates(report)
        report = _apply_improvement_focus(report, aggregates)
        payload = report.model_dump(mode="json")
        persistence = get_persistence()
        paths = persistence.upload_artifacts(session_id, video_path(session_id), landmarks_path(session_id))
        uploaded_paths = list(paths.values())
        committed = persistence.commit_session(session_id, payload, _durable_cards(report), aggregates)
        update_manifest(session_id, status="success", stage="Analysis complete", report=payload, error=None)
        if committed.get("replaced_session_id"):
            try:
                persistence.retry_pending_cleanup()
            except Exception:
                pass
        return payload
    except Exception as exc:
        update_manifest(session_id, status="failure", stage="Analysis failed", error=str(exc))
        try:
            if uploaded_paths:
                get_persistence().delete_objects(uploaded_paths)
            get_persistence().update_session(session_id, {"status": "failure", "stage": "Analysis failed", "error": str(exc)})
        except Exception:
            pass
        raise
    finally:
        if extracted_audio:
            extracted_audio.unlink(missing_ok=True)


@celery_app.task(name="itspeak.cleanup_expired")
def cleanup_expired_task() -> int:
    removed = cleanup_expired()
    try:
        get_persistence().retry_pending_cleanup()
    except Exception:
        pass
    return removed
