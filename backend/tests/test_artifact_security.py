import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from itspeak.api import app
from itspeak.artifact_store import create_session, update_manifest


class ArtifactSecurityTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.settings = SimpleNamespace(artifact_dir=self.temporary.name, artifact_retention_seconds=86400)
        self.patch = patch("itspeak.artifact_store.get_settings", return_value=self.settings)
        self.patch.start()
        self.manifest, self.token = create_session({"project_id": "p", "archetype": "corporate_board"})
        directory = Path(self.temporary.name) / self.manifest["session_id"]
        (directory / "opaque.mp4").write_bytes(b"0123456789")
        update_manifest(self.manifest["session_id"], video_filename="opaque.mp4")
        self.client = TestClient(app)

    def tearDown(self):
        self.patch.stop(); self.temporary.cleanup()

    def test_unauthorized_and_valid_range_access(self):
        url = f"/sessions/{self.manifest['session_id']}/video"
        self.assertEqual(self.client.get(url).status_code, 401)
        response = self.client.get(f"{url}?access_token={self.token}", headers={"Range": "bytes=2-5"})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, b"2345")
        self.assertEqual(response.headers["accept-ranges"], "bytes")
        invalid = self.client.get(f"{url}?access_token={self.token}", headers={"Range": "bytes=99-100"})
        self.assertEqual(invalid.status_code, 416)


if __name__ == "__main__":
    unittest.main()
