"""Authentication boundary ready for a future Clerk JWT verifier."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

from .settings import get_settings


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: str
    display_name: str | None = None
    avatar_url: str | None = None


def get_auth_principal(authorization: str | None = Header(None)) -> AuthPrincipal:
    """Return the configured development identity.

    Clerk is deliberately behind this dependency boundary. Until its verifier is
    installed, production requests fail closed instead of trusting an unverified
    bearer token.
    """
    settings = get_settings()
    if settings.environment.lower() == "development" and settings.dev_user_id:
        return AuthPrincipal(user_id=settings.dev_user_id, display_name="Local developer")
    raise HTTPException(
        status_code=503,
        detail="Authentication is not configured. Install the Clerk AuthPrincipal adapter.",
    )
