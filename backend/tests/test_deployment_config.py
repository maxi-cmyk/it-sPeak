from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from itspeak.jobs import _request_worker_recycle


class DeploymentConfigTest(unittest.TestCase):
    def test_production_worker_uses_single_process_solo_pool(self):
        config = (
            Path(__file__).resolve().parents[1]
            / "deploy"
            / "supervisord.conf"
        ).read_text()

        worker_line = next(
            line for line in config.splitlines()
            if line.startswith("command=python -m celery")
            and " worker " in line
        )
        self.assertIn("--pool=solo", worker_line)
        self.assertIn("--concurrency=%(ENV_CELERY_WORKER_CONCURRENCY)s", worker_line)

        worker_block = config.split("[program:worker]", 1)[1].split("[program:beat]", 1)[0]
        self.assertIn("autorestart=true", worker_block)

    def test_production_analysis_recycles_only_its_worker(self):
        task = SimpleNamespace(request=SimpleNamespace(hostname="celery@worker-1"))
        shutdown = Mock()
        with (
            patch("itspeak.jobs.get_settings", return_value=SimpleNamespace(environment="production")),
            patch.object(__import__("itspeak.jobs", fromlist=["celery_app"]).celery_app.control, "shutdown", shutdown),
        ):
            _request_worker_recycle(task)

        shutdown.assert_called_once_with(destination=["celery@worker-1"])

    def test_development_analysis_does_not_recycle_worker(self):
        task = SimpleNamespace(request=SimpleNamespace(hostname="celery@worker-1"))
        shutdown = Mock()
        with (
            patch("itspeak.jobs.get_settings", return_value=SimpleNamespace(environment="development")),
            patch.object(__import__("itspeak.jobs", fromlist=["celery_app"]).celery_app.control, "shutdown", shutdown),
        ):
            _request_worker_recycle(task)

        shutdown.assert_not_called()

    def test_api_dispatch_does_not_import_heavy_analysis_jobs(self):
        api_source = (
            Path(__file__).resolve().parents[1]
            / "itspeak"
            / "api.py"
        ).read_text()

        self.assertNotIn("from .jobs import", api_source)
        self.assertIn("from .task_dispatch import", api_source)


if __name__ == "__main__":
    unittest.main()
