from __future__ import annotations

import unittest
from pathlib import Path


class SchemaContractTest(unittest.TestCase):
    def test_sql_editor_snapshot_matches_initial_migration(self):
        backend = Path(__file__).resolve().parents[1]
        snapshot = (backend / "persistence" / "schema.sql").read_text(encoding="utf-8")
        migration = (backend.parent / "supabase" / "migrations" / "202607170001_initial_persistence.sql").read_text(encoding="utf-8")
        self.assertEqual(snapshot, migration)

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


if __name__ == "__main__":
    unittest.main()
