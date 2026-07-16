"""Persistence ports for the future Supabase and Cloudflare R2 adapters."""

from __future__ import annotations

from typing import Any, Protocol


class SessionRepository(Protocol):
    def create_pending(self, project_id: str, task_id: str, storage_key: str) -> None: ...

    def save_report(self, task_id: str, report: dict[str, Any]) -> None: ...

    def get_report(self, task_id: str) -> dict[str, Any] | None: ...


class VideoStorage(Protocol):
    def create_upload_url(self, project_id: str, filename: str) -> dict[str, str]: ...

    def delete(self, storage_key: str) -> None: ...


class PersistenceNotConfigured(RuntimeError):
    """Raised if a production persistence adapter is requested before configuration."""
