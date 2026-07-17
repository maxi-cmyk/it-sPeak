const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, { status, code, candidates } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.candidates = candidates || [];
  }
}

async function parseResponse(response) {
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || payload.error || {};
    throw new ApiError(
      typeof detail === "string" ? detail : detail.message || "The service returned an error.",
      { status: response.status, code: detail.code, candidates: detail.candidates }
    );
  }
  return payload;
}

async function request(path, options = {}) {
  const headers = options.body instanceof FormData ? options.headers : { "Content-Type": "application/json", ...options.headers };
  return parseResponse(await fetch(`${API_BASE_URL}${path}`, { cache: "no-store", ...options, headers }));
}

export const listProjects = () => request("/projects");
export const getProject = (id, signal) => request(`/projects/${id}`, { signal });
export const createProject = (payload) => request("/projects", { method: "POST", body: JSON.stringify(payload) });
export const updateProject = (id, payload) => request(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
export const deleteProject = (id) => request(`/projects/${id}`, { method: "DELETE" });
export const listProjectSessions = (id, signal) => request(`/projects/${id}/sessions`, { signal });

export async function uploadSession({ file, projectId, archetype, audienceContext, replaceSessionId, signal }) {
  const body = new FormData();
  body.append("file", file);
  body.append("project_id", projectId);
  body.append("archetype", archetype);
  body.append("audience_context", audienceContext || "");
  if (replaceSessionId) body.append("replace_session_id", replaceSessionId);
  return request("/sessions", { method: "POST", body, signal });
}

export const getSessionAnalysis = (sessionId, signal) => request(`/sessions/${sessionId}`, { signal });
export const confirmSession = (sessionId) => request(`/sessions/${sessionId}/confirm`, { method: "POST" });
export const getSessionArtifacts = (sessionId, signal) => request(`/sessions/${sessionId}/artifacts`, { signal });

export async function getLandmarksFromUrl(url, signal) {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new ApiError("Landmark overlays are unavailable.", { status: response.status });
  return response.json();
}
