from __future__ import annotations

import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
