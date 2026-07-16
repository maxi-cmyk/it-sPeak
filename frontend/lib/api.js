const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || payload.error || "The analysis service returned an error.");
  return payload;
}

const auth = (token) => ({ Authorization: `Bearer ${token}` });

export async function uploadSession({ file, projectId, archetype, audienceContext, signal }) {
  const body = new FormData();
  body.append("file", file);
  body.append("project_id", projectId);
  body.append("archetype", archetype);
  body.append("audience_context", audienceContext || "");
  return parseResponse(await fetch(`${API_BASE_URL}/sessions`, { method: "POST", body, signal }));
}

export async function getSessionAnalysis(sessionId, token, signal) {
  return parseResponse(await fetch(`${API_BASE_URL}/sessions/${sessionId}`, { cache: "no-store", headers: auth(token), signal }));
}

export async function confirmSession(sessionId, token) {
  return parseResponse(await fetch(`${API_BASE_URL}/sessions/${sessionId}/confirm`, { method: "POST", headers: auth(token) }));
}

export async function getLandmarks(sessionId, token, signal) {
  return parseResponse(await fetch(`${API_BASE_URL}/sessions/${sessionId}/landmarks`, { headers: auth(token), signal }));
}

export function getVideoUrl(sessionId, token) {
  return `${API_BASE_URL}/sessions/${sessionId}/video?access_token=${encodeURIComponent(token)}`;
}
