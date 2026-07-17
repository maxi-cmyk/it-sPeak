export function projectFromApi(project) {
  return { ...project, description: project.goal || "", deadline: project.deadline || "", archetype: project.default_archetype_key };
}

export function eligibleReplacementSessions(sessions, baselineSessionId = null) {
  return (sessions || []).filter((session) => session.id !== baselineSessionId && session.sequence_number !== 1 && session.status === "success" && !session.retired_at);
}

export function formatDate(dateStr) {
  if (!dateStr) return "No deadline";
  const date = new Date(`${dateStr}`.length === 10 ? `${dateStr}T00:00:00` : dateStr);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function getDaysUntilDeadline(deadline) {
  if (!deadline) return null;
  const deadlineDate = new Date(`${deadline}T00:00:00`);
  return Math.ceil((deadlineDate - new Date()) / (1000 * 60 * 60 * 24));
}
