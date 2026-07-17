import { reportToSession } from "./reportAdapter";
export { formatDate, getDaysUntilDeadline, projectFromApi } from "./persistenceUi.mjs";

export function sessionFromApi(session) {
  const result = session.analysis_result;
  if (!result?.report) return null;
  const view = reportToSession(result.report, session.id, session.project_id, session.quality_gate);
  return {
    ...view,
    name: `Session ${session.sequence_number}`,
    sequenceNumber: session.sequence_number,
    isBaseline: session.sequence_number === 1,
    date: (session.completed_at || session.created_at).slice(0, 10),
    overallScore: Math.round(Number(result.overall_score ?? view.overallScore)),
    score: Math.round(Number(result.overall_score ?? view.overallScore)),
    tone: Math.round(Number(result.vocal_score ?? view.tone)),
    face: Math.round(Number(result.face_score ?? view.face)),
    body: Math.round(Number(result.body_score ?? view.body)),
  };
}
