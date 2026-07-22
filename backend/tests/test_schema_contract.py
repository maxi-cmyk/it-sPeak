from __future__ import annotations

import unittest
from pathlib import Path


class SchemaContractTest(unittest.TestCase):
    def test_master_schema_tracks_the_latest_migration(self):
        backend = Path(__file__).resolve().parents[1]
        snapshot = (backend / "persistence" / "schema.sql").read_text(encoding="utf-8")
        migrations = sorted((backend.parent / "supabase" / "migrations").glob("*.sql"))

        self.assertTrue(migrations, "Expected at least one Supabase migration")
        latest_migration = migrations[-1].stem
        self.assertIn(
            f"Consolidated through Supabase migration: {latest_migration}.",
            snapshot,
        )

    def test_schema_contains_required_security_and_lifecycle_guards(self):
        backend = Path(__file__).resolve().parents[1]
        sql = (backend / "persistence" / "schema.sql").read_text(encoding="utf-8").lower()
        for table in ("profiles", "archetypes", "archetype_configs", "projects", "sessions", "analysis_results", "coaching_cards", "session_events"):
            self.assertIn(f"create table public.{table}", sql)
            self.assertIn(f"alter table public.{table} enable row level security", sql)
        self.assertIn("auth.jwt()->>'sub'", sql)
        self.assertIn("prevent_baseline_retirement", sql)
        self.assertIn("commit_analysis_session", sql)
        self.assertIn("session-artifacts", sql)
        self.assertIn("improvement_areas text[] not null", sql)
        self.assertIn("set search_path = public, extensions", sql)

    def test_master_schema_contains_the_latest_visual_scoring_bands(self):
        backend = Path(__file__).resolve().parents[1]
        sql = (backend / "persistence" / "schema.sql").read_text(encoding="utf-8")

        self.assertIn(
            '"gesture_frequency":{"kind":"target","ideal":0.70,"tol_low":0.90,"tol_high":0.90}',
            sql,
        )
        self.assertIn(
            '"expression":{"kind":"floor","low":0.02,"ideal":0.12}',
            sql,
        )

    def test_every_archetype_has_a_populated_scoring_config(self):
        backend = Path(__file__).resolve().parents[1]
        sql = (backend / "persistence" / "schema.sql").read_text(encoding="utf-8")
        for archetype in (
            "corporate_board",
            "motivational_keynote",
            "startup_pitch",
            "academic_conference",
            "informal_team",
            "job_interview",
        ):
            self.assertIn(f"('{archetype}', 1, '{{\"eye_contact\"", sql)


if __name__ == "__main__":
    unittest.main()
