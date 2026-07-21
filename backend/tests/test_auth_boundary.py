from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException, Request

from itspeak.auth import get_auth_principal
from itspeak.settings import Settings


class AuthBoundaryTest(unittest.TestCase):
    @staticmethod
    def request(token: str = "session-token") -> Request:
        return Request({
            "type": "http",
            "method": "GET",
            "path": "/projects",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        })

    def test_valid_clerk_session_becomes_principal(self):
        settings = Settings(_env_file=None, clerk_secret_key="sk_test_value", frontend_origin="http://localhost:3000")
        state = SimpleNamespace(is_signed_in=True, payload={"sub": "user_clerk_123"}, reason=None)
        with (
            patch("itspeak.auth.get_settings", return_value=settings),
            patch("itspeak.auth.authenticate_request", return_value=state) as authenticate,
        ):
            principal = get_auth_principal(self.request())
        self.assertEqual(principal.user_id, "user_clerk_123")
        options = authenticate.call_args.args[1]
        self.assertEqual(options.authorized_parties, ["http://localhost:3000"])
        self.assertEqual(options.accepts_token, ["session_token"])

    def test_invalid_clerk_session_is_unauthorized(self):
        settings = Settings(_env_file=None, clerk_secret_key="sk_test_value")
        state = SimpleNamespace(is_signed_in=False, payload=None, reason="token-expired")
        with (
            patch("itspeak.auth.get_settings", return_value=settings),
            patch("itspeak.auth.authenticate_request", return_value=state),
            self.assertRaises(HTTPException) as context,
        ):
            get_auth_principal(self.request("expired"))
        self.assertEqual(context.exception.status_code, 401)

    def test_missing_clerk_configuration_fails_closed(self):
        settings = Settings(_env_file=None, clerk_secret_key="")
        with patch("itspeak.auth.get_settings", return_value=settings), self.assertRaises(HTTPException) as context:
            get_auth_principal(self.request())
        self.assertEqual(context.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
