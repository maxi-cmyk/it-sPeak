"""Persistence and private-object-storage adapters for Supabase and tests."""

from __future__ import annotations

import threading
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote
from uuid import uuid4

import httpx

from .models import ImprovementArea
from .settings import get_settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PersistenceError(RuntimeError):
    pass


class NotFoundError(PersistenceError):
    pass


class ReplacementRequired(PersistenceError):
    def __init__(self, candidates: list[dict[str, Any]]):
        super().__init__("A retained session must be selected for replacement")
        self.candidates = candidates


class Persistence(Protocol):
    def ensure_profile(self, owner_id: str, display_name: str | None = None, avatar_url: str | None = None) -> None: ...
    def list_projects(self, owner_id: str) -> list[dict[str, Any]]: ...
    def create_project(self, owner_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    def get_project(self, owner_id: str, project_id: str) -> dict[str, Any] | None: ...
    def update_project(self, owner_id: str, project_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    def delete_project(self, owner_id: str, project_id: str) -> list[str]: ...
    def list_sessions(self, owner_id: str, project_id: str, active_only: bool = True) -> list[dict[str, Any]]: ...
    def get_session(self, owner_id: str, session_id: str) -> dict[str, Any] | None: ...
    def replacement_candidates(self, owner_id: str, project_id: str) -> list[dict[str, Any]]: ...
    def create_pending_session(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def update_session(self, session_id: str, payload: dict[str, Any]) -> None: ...
    def upload_artifacts(self, session_id: str, video: Path, landmarks: Path) -> dict[str, str]: ...
    def commit_session(self, session_id: str, report: dict[str, Any], cards: list[dict[str, Any]], aggregates: dict[str, float | None]) -> dict[str, Any]: ...
    def signed_artifacts(self, owner_id: str, session_id: str) -> dict[str, str]: ...
    def delete_objects(self, paths: list[str]) -> None: ...
    def retry_pending_cleanup(self) -> int: ...


class InMemoryPersistence:
    """Thread-safe adapter used by unit tests and local development without Supabase."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.profiles: dict[str, dict[str, Any]] = {}
        self.projects: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.results: dict[str, dict[str, Any]] = {}
        self.cards: dict[str, list[dict[str, Any]]] = {}

    def ensure_profile(self, owner_id: str, display_name: str | None = None, avatar_url: str | None = None) -> None:
        with self._lock:
            existing = self.profiles.get(owner_id, {})
            self.profiles[owner_id] = {
                "id": owner_id,
                "display_name": display_name or existing.get("display_name"),
                "avatar_url": avatar_url or existing.get("avatar_url"),
            }

    def _project_view(self, project: dict[str, Any]) -> dict[str, Any]:
        sessions = self.list_sessions(project["owner_id"], project["id"])
        return {**deepcopy(project), "session_count": len(sessions), "latest_session": sessions[0] if sessions else None}

    def list_projects(self, owner_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = [self._project_view(p) for p in self.projects.values() if p["owner_id"] == owner_id]
            return sorted(rows, key=lambda p: (not p["pinned"], p["updated_at"]), reverse=False)

    def create_project(self, owner_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            project_id = str(uuid4())
            now = _now()
            row = {
                "id": project_id, "owner_id": owner_id, "name": payload["name"].strip(),
                "goal": payload.get("goal"), "default_archetype_key": payload.get("default_archetype_key", "corporate_board"),
                "improvement_areas": deepcopy(payload.get("improvement_areas", [area.value for area in ImprovementArea])),
                "default_archetype_version": 1, "deadline": payload.get("deadline"), "pinned": bool(payload.get("pinned", False)),
                "reset_generation": 1, "next_sequence_number": 1, "baseline_session_id": None,
                "created_at": now, "updated_at": now,
            }
            self.projects[project_id] = row
            return self._project_view(row)

    def get_project(self, owner_id: str, project_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.projects.get(project_id)
            return self._project_view(row) if row and row["owner_id"] == owner_id else None

    def update_project(self, owner_id: str, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            row = self.projects.get(project_id)
            if not row or row["owner_id"] != owner_id:
                raise NotFoundError("Project not found")
            row.update(payload)
            row["updated_at"] = _now()
            return self._project_view(row)

    def delete_project(self, owner_id: str, project_id: str) -> list[str]:
        with self._lock:
            row = self.projects.get(project_id)
            if not row or row["owner_id"] != owner_id:
                raise NotFoundError("Project not found")
            paths: list[str] = []
            for session in list(self.sessions.values()):
                if session["project_id"] == project_id:
                    paths.extend(p for p in (session.get("video_object_path"), session.get("landmarks_object_path")) if p)
                    self.results.pop(session["id"], None); self.cards.pop(session["id"], None); self.sessions.pop(session["id"], None)
            self.projects.pop(project_id)
            return paths

    def _session_view(self, session: dict[str, Any]) -> dict[str, Any]:
        result = self.results.get(session["id"])
        return {**deepcopy(session), "analysis_result": deepcopy(result), "coaching_cards": deepcopy(self.cards.get(session["id"], []))}

    def list_sessions(self, owner_id: str, project_id: str, active_only: bool = True) -> list[dict[str, Any]]:
        with self._lock:
            rows = [s for s in self.sessions.values() if s["owner_id"] == owner_id and s["project_id"] == project_id]
            if active_only:
                rows = [s for s in rows if s["status"] == "success" and not s.get("retired_at")]
            return [self._session_view(s) for s in sorted(rows, key=lambda s: s.get("sequence_number") or 0, reverse=True)]

    def get_session(self, owner_id: str, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.sessions.get(session_id)
            return self._session_view(row) if row and row["owner_id"] == owner_id else None

    def replacement_candidates(self, owner_id: str, project_id: str) -> list[dict[str, Any]]:
        project = self.get_project(owner_id, project_id)
        if not project:
            raise NotFoundError("Project not found")
        return [s for s in self.list_sessions(owner_id, project_id) if s["id"] != project.get("baseline_session_id")]

    def create_pending_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            project = self.projects.get(payload["project_id"])
            if not project or project["owner_id"] != payload["owner_id"]:
                raise NotFoundError("Project not found")
            active = self.list_sessions(payload["owner_id"], payload["project_id"])
            candidates = self.replacement_candidates(payload["owner_id"], payload["project_id"])
            replacement_id = payload.get("replace_session_id")
            if len(active) >= 5 and replacement_id not in {s["id"] for s in candidates}:
                raise ReplacementRequired(candidates)
            now = _now()
            row = {
                "id": payload["id"], "project_id": project["id"], "owner_id": project["owner_id"],
                "task_id": payload.get("task_id"), "status": "quality_check", "stage": "Checking recording quality", "error": None,
                "generation": project["reset_generation"], "sequence_number": None,
                "archetype_key": payload.get("archetype_key", project["default_archetype_key"]), "archetype_version": 1,
                "audience_context": payload.get("audience_context", ""), "replace_session_id": replacement_id,
                "quality_gate": None, "video_object_path": None, "landmarks_object_path": None,
                "retained_at": None, "retired_at": None, "created_at": now, "updated_at": now, "completed_at": None,
            }
            self.sessions[row["id"]] = row
            return deepcopy(row)

    def update_session(self, session_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id].update(deepcopy(payload)); self.sessions[session_id]["updated_at"] = _now()

    def upload_artifacts(self, session_id: str, video: Path, landmarks: Path) -> dict[str, str]:
        with self._lock:
            session = self.sessions[session_id]
            root = f'{session["owner_id"]}/{session["project_id"]}/{session_id}'
            paths = {"video_object_path": f"{root}/video{video.suffix.lower()}", "landmarks_object_path": f"{root}/landmarks.v1.json.gz"}
            session.update(paths)
            return paths

    def commit_session(self, session_id: str, report: dict[str, Any], cards: list[dict[str, Any]], aggregates: dict[str, float | None]) -> dict[str, Any]:
        with self._lock:
            session = self.sessions[session_id]; project = self.projects[session["project_id"]]
            active = self.list_sessions(session["owner_id"], session["project_id"])
            replacement = None
            if len(active) >= 5:
                replacement = self.sessions.get(session.get("replace_session_id"))
                if not replacement or replacement["id"] == project.get("baseline_session_id") or replacement.get("retired_at"):
                    raise ReplacementRequired(self.replacement_candidates(session["owner_id"], session["project_id"]))
                replacement.update(status="replaced", retired_at=_now(), retired_reason="replaced")
            sequence = project["next_sequence_number"]; project["next_sequence_number"] += 1
            session.update(status="success", stage="Analysis complete", sequence_number=sequence, retained_at=_now(), completed_at=_now())
            self.results[session_id] = {"session_id": session_id, **aggregates, "normalized_scores": report.get("scores", {}), "metric_confidence": report.get("raw_analysis", {}).get("metric_confidence", {}), "report": deepcopy(report)}
            self.cards[session_id] = deepcopy(cards)
            baseline = project["baseline_session_id"] is None
            if baseline: project["baseline_session_id"] = session_id
            return {"session_id": session_id, "sequence_number": sequence, "baseline": baseline, "replaced_session_id": replacement and replacement["id"], "old_video_object_path": replacement and replacement.get("video_object_path"), "old_landmarks_object_path": replacement and replacement.get("landmarks_object_path")}

    def signed_artifacts(self, owner_id: str, session_id: str) -> dict[str, str]:
        session = self.get_session(owner_id, session_id)
        if not session or session["status"] != "success": raise NotFoundError("Session not found")
        return {}

    def delete_objects(self, paths: list[str]) -> None:
        return None

    def retry_pending_cleanup(self) -> int:
        return 0


class SupabasePersistence:
    def __init__(self, url: str, secret_key: str, bucket: str) -> None:
        self.url = url.rstrip("/"); self.secret_key = secret_key; self.bucket = bucket
        headers = {"apikey": secret_key, "Content-Type": "application/json"}
        if not secret_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {secret_key}"
        self.client = httpx.Client(headers=headers, timeout=60.0)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        response = self.client.request(method, f"{self.url}{path}", **kwargs)
        if response.status_code >= 400:
            raise PersistenceError(f"Supabase {response.status_code}: {response.text[:500]}")
        if not response.content: return None
        return response.json()

    def _rows(self, table: str, params: dict[str, str], *, method: str = "GET", json: Any = None, prefer: str | None = None) -> list[dict[str, Any]]:
        headers = {"Prefer": prefer} if prefer else None
        return self._request(method, f"/rest/v1/{table}", params=params, json=json, headers=headers) or []

    def ensure_profile(self, owner_id: str, display_name: str | None = None, avatar_url: str | None = None) -> None:
        payload = {"id": owner_id, "display_name": display_name, "avatar_url": avatar_url}
        self._rows("profiles", {"on_conflict": "id"}, method="POST", json=payload, prefer="resolution=merge-duplicates")

    def _decorate_projects(self, owner_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for row in rows:
            sessions = self.list_sessions(owner_id, row["id"])
            row["session_count"] = len(sessions); row["latest_session"] = sessions[0] if sessions else None
        return rows

    def list_projects(self, owner_id: str) -> list[dict[str, Any]]:
        rows = self._rows("projects", {"select": "*", "owner_id": f"eq.{owner_id}", "order": "pinned.desc,updated_at.desc"})
        return self._decorate_projects(owner_id, rows)

    def create_project(self, owner_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = {"owner_id": owner_id, "name": payload["name"].strip(), "goal": payload.get("goal"), "deadline": payload.get("deadline"), "pinned": payload.get("pinned", False), "default_archetype_key": payload.get("default_archetype_key", "corporate_board"), "improvement_areas": payload.get("improvement_areas", [area.value for area in ImprovementArea])}
        rows = self._rows("projects", {"select": "*"}, method="POST", json=row, prefer="return=representation")
        return self._decorate_projects(owner_id, rows)[0]

    def get_project(self, owner_id: str, project_id: str) -> dict[str, Any] | None:
        rows = self._rows("projects", {"select": "*", "id": f"eq.{project_id}", "owner_id": f"eq.{owner_id}", "limit": "1"})
        return self._decorate_projects(owner_id, rows)[0] if rows else None

    def update_project(self, owner_id: str, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._rows("projects", {"id": f"eq.{project_id}", "owner_id": f"eq.{owner_id}", "select": "*"}, method="PATCH", json=payload, prefer="return=representation")
        if not rows: raise NotFoundError("Project not found")
        return self._decorate_projects(owner_id, rows)[0]

    def delete_project(self, owner_id: str, project_id: str) -> list[str]:
        sessions = self.list_sessions(owner_id, project_id, active_only=False)
        paths = [path for s in sessions for path in (s.get("video_object_path"), s.get("landmarks_object_path")) if path]
        rows = self._rows("projects", {"id": f"eq.{project_id}", "owner_id": f"eq.{owner_id}", "select": "id"}, method="DELETE", prefer="return=representation")
        if not rows: raise NotFoundError("Project not found")
        return paths

    def _session_select(self) -> str:
        return "*,analysis_result:analysis_results(*),coaching_cards(*)"

    def list_sessions(self, owner_id: str, project_id: str, active_only: bool = True) -> list[dict[str, Any]]:
        params = {"select": self._session_select(), "owner_id": f"eq.{owner_id}", "project_id": f"eq.{project_id}", "order": "sequence_number.desc.nullslast"}
        if active_only: params.update({"status": "eq.success", "retired_at": "is.null"})
        return self._rows("sessions", params)

    def get_session(self, owner_id: str, session_id: str) -> dict[str, Any] | None:
        rows = self._rows("sessions", {"select": self._session_select(), "owner_id": f"eq.{owner_id}", "id": f"eq.{session_id}", "limit": "1"})
        return rows[0] if rows else None

    def replacement_candidates(self, owner_id: str, project_id: str) -> list[dict[str, Any]]:
        project = self.get_project(owner_id, project_id)
        if not project: raise NotFoundError("Project not found")
        return [s for s in self.list_sessions(owner_id, project_id) if s["id"] != project.get("baseline_session_id")]

    def create_pending_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        project = self.get_project(payload["owner_id"], payload["project_id"])
        if not project: raise NotFoundError("Project not found")
        candidates = self.replacement_candidates(payload["owner_id"], payload["project_id"])
        if project["session_count"] >= 5 and payload.get("replace_session_id") not in {c["id"] for c in candidates}:
            raise ReplacementRequired(candidates)
        row = {"id": payload["id"], "project_id": project["id"], "owner_id": project["owner_id"], "status": "quality_check", "stage": "Checking recording quality", "generation": project["reset_generation"], "archetype_key": payload.get("archetype_key", project["default_archetype_key"]), "archetype_version": 1, "audience_context": payload.get("audience_context", ""), "replace_session_id": payload.get("replace_session_id")}
        return self._rows("sessions", {"select": "*"}, method="POST", json=row, prefer="return=representation")[0]

    def update_session(self, session_id: str, payload: dict[str, Any]) -> None:
        self._rows("sessions", {"id": f"eq.{session_id}"}, method="PATCH", json=payload)

    def _storage_path(self, path: str) -> str:
        return "/".join(quote(part, safe="") for part in path.split("/"))

    def upload_artifacts(self, session_id: str, video: Path, landmarks: Path) -> dict[str, str]:
        rows = self._rows("sessions", {"select": "owner_id,project_id", "id": f"eq.{session_id}", "limit": "1"})
        if not rows: raise NotFoundError("Session not found")
        session = rows[0]; root = f'{session["owner_id"]}/{session["project_id"]}/{session_id}'
        paths = {"video_object_path": f"{root}/video{video.suffix.lower()}", "landmarks_object_path": f"{root}/landmarks.v1.json.gz"}
        for key, source in (("video_object_path", video), ("landmarks_object_path", landmarks)):
            headers = {"Content-Type": "application/octet-stream", "x-upsert": "true"}
            self._request("POST", f"/storage/v1/object/{quote(self.bucket, safe='')}/{self._storage_path(paths[key])}", content=source.read_bytes(), headers=headers)
        self.update_session(session_id, paths)
        return paths

    def commit_session(self, session_id: str, report: dict[str, Any], cards: list[dict[str, Any]], aggregates: dict[str, float | None]) -> dict[str, Any]:
        return self._request("POST", "/rest/v1/rpc/commit_analysis_session", json={"p_session_id": session_id, "p_report": report, "p_cards": cards, "p_overall_score": aggregates.get("overall_score"), "p_vocal_score": aggregates.get("vocal_score"), "p_face_score": aggregates.get("face_score"), "p_body_score": aggregates.get("body_score")})

    def signed_artifacts(self, owner_id: str, session_id: str) -> dict[str, str]:
        session = self.get_session(owner_id, session_id)
        if not session or session["status"] != "success": raise NotFoundError("Session not found")
        ttl = get_settings().signed_url_ttl_seconds; result: dict[str, str] = {}
        for label, key in (("video", "video_object_path"), ("landmarks", "landmarks_object_path")):
            path = session.get(key)
            if path:
                payload = self._request("POST", f"/storage/v1/object/sign/{quote(self.bucket, safe='')}/{self._storage_path(path)}", json={"expiresIn": ttl})
                signed = payload.get("signedURL") or payload.get("signedUrl")
                result[label] = signed if signed and signed.startswith("http") else f"{self.url}/storage/v1{signed}"
        result["expires_in"] = ttl
        return result

    def delete_objects(self, paths: list[str]) -> None:
        if paths: self._request("DELETE", f"/storage/v1/object/{quote(self.bucket, safe='')}", json={"prefixes": paths})

    def retry_pending_cleanup(self) -> int:
        events = self._rows("session_events", {"select": "id,payload", "event_type": "eq.artifact_cleanup_pending", "order": "created_at.asc", "limit": "100"})
        completed = 0
        for event in events:
            paths = [path for path in event.get("payload", {}).get("paths", []) if path]
            self.delete_objects(paths)
            self._rows("session_events", {"id": f'eq.{event["id"]}'}, method="PATCH", json={"event_type": "artifact_cleanup_complete"})
            completed += 1
        return completed


_runtime: Persistence | None = None


def get_persistence() -> Persistence:
    global _runtime
    if _runtime is None:
        settings = get_settings()
        _runtime = SupabasePersistence(settings.supabase_url, settings.supabase_secret_key, settings.supabase_storage_bucket) if settings.supabase_configured else InMemoryPersistence()
    return _runtime


def set_persistence(adapter: Persistence | None) -> None:
    global _runtime
    _runtime = adapter


class PersistenceNotConfigured(RuntimeError):
    """Kept for compatibility with earlier imports."""
