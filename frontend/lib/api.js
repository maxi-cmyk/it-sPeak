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

export function createApiClient(getToken) {
  async function request(path, options = {}) {
    const token = await getToken();
    if (!token) throw new ApiError("Your session has expired. Sign in again.", { status: 401 });
    const headers = {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...options.headers,
      Authorization: `Bearer ${token}`,
    };
    return parseResponse(await fetch(`${API_BASE_URL}${path}`, { cache: "no-store", ...options, headers }));
  }

  return {
    listProjects: () => request("/projects"),
    getProject: (id, signal) => request(`/projects/${id}`, { signal }),
    createProject: (payload) => request("/projects", { method: "POST", body: JSON.stringify(payload) }),
    updateProject: (id, payload) => request(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
    deleteProject: (id) => request(`/projects/${id}`, { method: "DELETE" }),
    listProjectSessions: (id, signal) => request(`/projects/${id}/sessions`, { signal }),
    uploadSession: async ({ file, projectId, archetype, audienceContext, replaceSessionId, signal }) => {
      const body = new FormData();
      body.append("file", file);
      body.append("project_id", projectId);
      body.append("archetype", archetype);
      body.append("audience_context", audienceContext || "");
      if (replaceSessionId) body.append("replace_session_id", replaceSessionId);
      return request("/sessions", { method: "POST", body, signal });
    },
    getSessionAnalysis: (sessionId, signal) => request(`/sessions/${sessionId}`, { signal }),
    confirmSession: (sessionId) => request(`/sessions/${sessionId}/confirm`, { method: "POST" }),
    getSessionArtifacts: (sessionId, signal) => request(`/sessions/${sessionId}/artifacts`, { signal }),
  };
}

export async function getLandmarksFromUrl(url, signal) {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new ApiError("Landmark overlays are unavailable.", { status: response.status });
  return response.json();
}
