from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from itspeak.api import app
from itspeak.auth import AuthPrincipal, get_auth_principal
from itspeak.persistence import InMemoryPersistence, set_persistence


class ProjectApiTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryPersistence()
        set_persistence(self.repo)
        app.dependency_overrides[get_auth_principal] = lambda: AuthPrincipal("clerk-api-user", "API User")
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        set_persistence(None)

    def test_owned_project_crud(self):
        created = self.client.post("/projects", json={"name": "Conference rehearsal", "goal": "Deliver the methods clearly", "improvement_areas": ["pacing", "eye_contact"]})
        self.assertEqual(created.status_code, 201)
        project = created.json()
        self.assertEqual(project["session_count"], 0)
        self.assertEqual(project["improvement_areas"], ["pacing", "eye_contact"])

        listed = self.client.get("/projects")
        self.assertEqual([row["id"] for row in listed.json()], [project["id"]])

        updated = self.client.patch(f'/projects/{project["id"]}', json={"pinned": True, "deadline": "2026-12-01", "improvement_areas": ["gestures"]})
        self.assertEqual(updated.status_code, 200)
        self.assertTrue(updated.json()["pinned"])
        self.assertEqual(updated.json()["improvement_areas"], ["gestures"])

        deleted = self.client.delete(f'/projects/{project["id"]}')
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get("/projects").json(), [])

    def test_enabled_archetype_can_be_selected(self):
        response = self.client.post("/projects", json={"name": "Pitch", "default_archetype_key": "startup_pitch"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["default_archetype_key"], "startup_pitch")

    def test_unsupported_archetype_cannot_be_selected(self):
        response = self.client.post("/projects", json={"name": "Pitch", "default_archetype_key": "not_a_real_archetype"})
        self.assertEqual(response.status_code, 422)

    def test_project_requires_one_or_more_unique_improvement_areas(self):
        empty = self.client.post("/projects", json={"name": "Pitch", "improvement_areas": []})
        duplicate = self.client.post("/projects", json={"name": "Pitch", "improvement_areas": ["pacing", "pacing"]})
        unsupported = self.client.post("/projects", json={"name": "Pitch", "improvement_areas": ["slides"]})
        self.assertEqual(empty.status_code, 422)
        self.assertEqual(duplicate.status_code, 422)
        self.assertEqual(unsupported.status_code, 422)


if __name__ == "__main__":
    unittest.main()
