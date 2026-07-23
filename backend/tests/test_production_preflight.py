import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from itspeak.preflight import production_configuration_errors
from itspeak.settings import Settings


class ProductionPreflightTest(unittest.TestCase):
    def test_development_does_not_require_deployment_services(self):
        self.assertEqual(production_configuration_errors(Settings(_env_file=None)), [])

    def test_production_rejects_local_and_missing_services(self):
        settings = Settings(
            _env_file=None,
            environment="production",
            redis_url="redis://localhost:6379/0",
            frontend_origin="http://localhost:3000",
            artifact_dir="/tmp/itspeak-sessions",
            clerk_secret_key="",
            supabase_url="",
            supabase_secret_key="",
            openai_api_key="",
        )
        errors = production_configuration_errors(settings)
        self.assertIn("ITSPEAK_REDIS_URL must point to the managed Redis service", errors)
        self.assertIn("ITSPEAK_FRONTEND_ORIGIN must be the deployed frontend origin", errors)
        self.assertIn("CLERK_SECRET_KEY is required", errors)
        self.assertIn("ITSPEAK_SUPABASE_URL is required", errors)
        self.assertIn("ITSPEAK_SUPABASE_SECRET_KEY is required", errors)
        self.assertIn("ITSPEAK_OPENAI_API_KEY is required", errors)
        self.assertIn("ITSPEAK_ARTIFACT_DIR must use the mounted persistent volume", errors)

    def test_complete_production_configuration_passes(self):
        with tempfile.TemporaryDirectory() as artifact_dir:
            settings = Settings(
                _env_file=None,
                environment="production",
                redis_url="rediss://redis.example.test:6380/0",
                frontend_origin="https://app.example.test",
                clerk_secret_key="clerk-test",
                supabase_url="https://supabase.example.test",
                supabase_secret_key="supabase-test",
                openai_api_key="openai-test",
                artifact_dir=artifact_dir,
            )
            with (
                patch("itspeak.preflight.shutil.which", return_value="/usr/bin/tool"),
                patch.dict("os.environ", {"CELERY_WORKER_CONCURRENCY": "1"}),
            ):
                self.assertEqual(production_configuration_errors(settings), [])

    def test_artifact_directory_must_be_writable(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifact_file = Path(temporary) / "not-a-directory"
            artifact_file.write_text("occupied")
            settings = Settings(
                _env_file=None,
                environment="production",
                redis_url="rediss://redis.example.test:6380/0",
                frontend_origin="https://app.example.test",
                clerk_secret_key="clerk-test",
                supabase_url="https://supabase.example.test",
                supabase_secret_key="supabase-test",
                openai_api_key="openai-test",
                artifact_dir=str(artifact_file),
            )
            with patch("itspeak.preflight.shutil.which", return_value="/usr/bin/tool"):
                errors = production_configuration_errors(settings)
            self.assertTrue(any("not writable" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
