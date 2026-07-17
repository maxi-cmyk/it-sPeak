from __future__ import annotations

import unittest
from unittest.mock import patch

from pydantic import ValidationError

from itspeak.auth import get_auth_principal
from itspeak.settings import Settings


class AuthBoundaryTest(unittest.TestCase):
    def test_development_identity_is_explicit(self):
        settings = Settings(_env_file=None, environment="development", dev_user_id="dev-clerk-sub")
        with patch("itspeak.auth.get_settings", return_value=settings):
            self.assertEqual(get_auth_principal().user_id, "dev-clerk-sub")

    def test_production_rejects_development_identity(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, environment="production", dev_user_id="dev-clerk-sub")


if __name__ == "__main__":
    unittest.main()
