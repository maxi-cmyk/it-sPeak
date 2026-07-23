import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from itspeak.audio import _configure_numba_cache


class NumbaCacheTests(unittest.TestCase):
    def test_configured_cache_directory_is_created_and_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            configured = Path(temporary) / "persistent-numba-cache"
            with patch.dict(os.environ, {"NUMBA_CACHE_DIR": str(configured)}):
                actual = _configure_numba_cache()

                self.assertEqual(actual, configured)
                self.assertEqual(os.environ["NUMBA_CACHE_DIR"], str(configured))
                self.assertTrue(configured.is_dir())


if __name__ == "__main__":
    unittest.main()
