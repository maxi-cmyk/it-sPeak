"""Clerk session-token authentication for the FastAPI boundary."""

from __future__ import annotations

from dataclasses import dataclass

from clerk_backend_api import AuthenticateRequestOptions, authenticate_request
from fastapi import HTTPException, Request

from .settings import get_settings


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: str
    display_name: str | None = None
    avatar_url: str | None = None


def get_auth_principal(request: Request) -> AuthPrincipal:
    """Verify a Clerk session token and return its stable user identity."""
    settings = get_settings()
    if not settings.clerk_secret_key:
        raise HTTPException(status_code=503, detail="Clerk authentication is not configured")

    try:
        state = authenticate_request(
            request,
            AuthenticateRequestOptions(
                secret_key=settings.clerk_secret_key,
                jwt_key=settings.clerk_jwt_key or None,
                authorized_parties=[settings.frontend_origin],
                accepts_token=["session_token"],
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Clerk authentication is temporarily unavailable") from exc

    payload = state.payload or {}
    user_id = payload.get("sub")
    if not state.is_signed_in or not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Clerk session token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthPrincipal(user_id=user_id)
