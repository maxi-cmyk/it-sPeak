from __future__ import annotations

import asyncio
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi import UploadFile

from itspeak.api import create_analysis_session
from itspeak.auth import AuthPrincipal
from itspeak.jobs import analyze_session_task, quality_check_task
from itspeak.models import Archetype, BodyMetrics, CoachingCard, FaceMetrics, Module, NormalizedScores, QualityDisposition, QualityGateReport, QualityMeasurements, VideoAnalysisResult
from itspeak.persistence import InMemoryPersistence, set_persistence


class SessionFlowContractTest(unittest.TestCase):
    def setUp(self):
        self.persistence = InMemoryPersistence()
        self.persistence.ensure_profile("user-1")
        self.project = self.persistence.create_project("user-1", {"name": "Board rehearsal", "default_archetype_key": "corporate_board"})
        set_persistence(self.persistence)

    def tearDown(self):
        set_persistence(None)

    def test_upload_creates_private_session_and_queues_gate(self):
        upload = UploadFile(filename="talk.mp4", file=BytesIO(b"video"))
        manifest = {"session_id": "a081b0b6-3264-40ac-8e42-ff03e907ca27", "expires_at": "2030-01-01T00:00:00+00:00"}
        with (
            patch("itspeak.api.create_session", return_value=(manifest, "secret")),
            patch("itspeak.api.save_session_video", new=AsyncMock(return_value=Path("/tmp/private.mp4"))),
            patch("itspeak.api.update_manifest"),
            patch("itspeak.api.quality_check_task.delay") as delay,
        ):
            accepted = asyncio.run(create_analysis_session(upload, self.project["id"], Archetype.CORPORATE_BOARD, "Board", None, AuthPrincipal("user-1")))
        self.assertEqual(accepted.session_id, manifest["session_id"])
        self.assertEqual(accepted.access_token, "secret")
        delay.assert_called_once_with(manifest["session_id"])

    def test_warning_gate_pauses_before_full_analysis(self):
        report = QualityGateReport(disposition=QualityDisposition.CONFIRM, measurements=QualityMeasurements(sampled_frames=10))
        with (
            patch("itspeak.jobs.video_path", return_value=Path("/tmp/video.mp4")),
            patch("itspeak.jobs.run_quality_gate", return_value=report),
            patch("itspeak.jobs.update_manifest") as update,
            patch("itspeak.jobs._enqueue_analysis") as enqueue,
        ):
            quality_check_task.run("a081b0b6-3264-40ac-8e42-ff03e907ca27")
        enqueue.assert_not_called()
        self.assertTrue(any(call.kwargs.get("status") == "needs_confirmation" for call in update.call_args_list))

    def test_full_job_keeps_video_and_writes_landmarks(self):
        visual = VideoAnalysisResult(
            face=FaceMetrics(eye_contact_ratio=.7, expression_variance=.5, head_stability=.8, frames_with_face=10),
            body=BodyMetrics(posture_alignment=.8, gesture_frequency=.3, gesture_range=.4, openness_ratio=.7, frames_with_pose=10),
            frames_analyzed=10, duration_seconds=5,
        )
        scores = NormalizedScores(eye_contact_score=80, expression_score=75, posture_score=85, gesture_score=70, archetype=Archetype.CORPORATE_BOARD)
        audio_payload = {"summary": {}, "performance_scores": {"aggregate_vocal_rating": 78.0}, "readable_metrics": {}, "transcript": {"text": "Hello"}, "pauses_timeline": [], "speech_issues": {}, "actionable_coaching_cards": []}
        card = CoachingCard(module=Module.FACE, problem="Gaze drops", importance="Connection", actionable_fix="Hold the lens")
        session_id = "a081b0b6-3264-40ac-8e42-ff03e907ca27"
        self.persistence.create_pending_session({"id": session_id, "project_id": self.project["id"], "owner_id": "user-1", "archetype_key": "corporate_board"})
        with tempfile.TemporaryDirectory() as temporary:
            video = Path(temporary) / "video.mp4"; video.write_bytes(b"video")
            audio = Path(temporary) / "audio.wav"; audio.write_bytes(b"audio")
            coach = Mock(); coach.generate_cards.return_value = [card]
            with (
                patch("itspeak.jobs.read_manifest", return_value={"archetype": "corporate_board", "audience_context": "Board"}),
                patch("itspeak.jobs.video_path", return_value=video), patch("itspeak.jobs.extract_frames", return_value=object()),
                patch("itspeak.jobs.analyze_frames_with_artifacts", return_value=(visual, {"version": "1.0", "frames": []})),
                patch("itspeak.jobs.write_landmarks") as write_landmarks, patch("itspeak.jobs.normalize_scores", return_value=scores),
                patch("itspeak.jobs.extract_audio_track", return_value=audio), patch("itspeak.jobs.analyze_audio", return_value=audio_payload),
                patch("itspeak.jobs.CoachingService", return_value=coach), patch("itspeak.jobs.update_manifest") as update,
            ):
                report = analyze_session_task.run(session_id)
            self.assertTrue(video.exists())
            self.assertFalse(audio.exists())
            self.assertEqual(report["raw_analysis"]["frames_analyzed"], 10)
            write_landmarks.assert_called_once()
            self.assertTrue(any(call.kwargs.get("status") == "success" for call in update.call_args_list))
            durable = self.persistence.get_session("user-1", session_id)
            self.assertEqual(durable["sequence_number"], 1)
            self.assertEqual(self.persistence.get_project("user-1", self.project["id"])["baseline_session_id"], session_id)


if __name__ == "__main__":
    unittest.main()
