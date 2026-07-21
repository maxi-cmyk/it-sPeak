from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from itspeak.persistence import InMemoryPersistence, ReplacementRequired


def report(score: float) -> dict:
    return {
        "version": "1.0",
        "scores": {"eye_contact_score": score},
        "raw_analysis": {"metric_confidence": {"eye_contact": "high"}},
    }


class PersistenceFoundationTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryPersistence()
        self.repo.ensure_profile("clerk-user-a", "A")
        self.repo.ensure_profile("clerk-user-b", "B")
        self.project = self.repo.create_project("clerk-user-a", {"name": "Pitch", "default_archetype_key": "corporate_board"})

    def commit(self, replacement_id=None):
        session_id = str(uuid4())
        self.repo.create_pending_session({"id": session_id, "project_id": self.project["id"], "owner_id": "clerk-user-a", "archetype_key": "corporate_board", "replace_session_id": replacement_id})
        with TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"; video.write_bytes(b"video")
            landmarks = Path(directory) / "landmarks.gz"; landmarks.write_bytes(b"landmarks")
            self.repo.upload_artifacts(session_id, video, landmarks)
        return self.repo.commit_session(session_id, report(75), [], {"overall_score": 75, "vocal_score": 75, "face_score": 75, "body_score": 75})

    def test_first_success_is_protected_baseline(self):
        committed = self.commit()
        project = self.repo.get_project("clerk-user-a", self.project["id"])
        self.assertTrue(committed["baseline"])
        self.assertEqual(project["baseline_session_id"], committed["session_id"])

    def test_update_transcript_rewrites_stored_report(self):
        committed = self.commit()
        session = self.repo.update_transcript("clerk-user-a", committed["session_id"], "Corrected transcript text.")
        self.assertEqual(session["analysis_result"]["report"]["audio"]["transcript"]["text"], "Corrected transcript text.")

    def test_update_transcript_rejects_other_owners(self):
        committed = self.commit()
        with self.assertRaises(Exception):
            self.repo.update_transcript("clerk-user-b", committed["session_id"], "Hijacked transcript.")

    def test_sixth_session_requires_non_baseline_replacement(self):
        committed = [self.commit() for _ in range(5)]
        with self.assertRaises(ReplacementRequired) as context:
            self.repo.create_pending_session({"id": str(uuid4()), "project_id": self.project["id"], "owner_id": "clerk-user-a", "archetype_key": "corporate_board"})
        candidate_ids = {candidate["id"] for candidate in context.exception.candidates}
        self.assertNotIn(committed[0]["session_id"], candidate_ids)
        sixth = self.commit(committed[1]["session_id"])
        self.assertEqual(sixth["sequence_number"], 6)
        active = self.repo.list_sessions("clerk-user-a", self.project["id"])
        self.assertEqual(len(active), 5)
        self.assertIn(committed[0]["session_id"], {session["id"] for session in active})

    def test_owner_isolation(self):
        self.commit()
        self.assertIsNone(self.repo.get_project("clerk-user-b", self.project["id"]))
        self.assertEqual(self.repo.list_sessions("clerk-user-b", self.project["id"]), [])


if __name__ == "__main__":
    unittest.main()
