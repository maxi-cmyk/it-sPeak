const averageAvailable = (...values) => {
  const available = values.filter((value) => Number.isFinite(value));
  return available.length ? Math.round(available.reduce((sum, value) => sum + value, 0) / available.length) : null;
};

export function reportToSession(report, sessionId, projectId = "1", qualityGate = null) {
  const face = averageAvailable(report.scores.eye_contact_score, report.scores.expression_score, report.scores.smile_naturalness_score);
  const body = averageAvailable(report.scores.posture_score, report.scores.gesture_score, report.scores.movement_purposefulness_score, report.scores.spatial_use_score);
  const tone = Math.round(report.audio.performance_scores.aggregate_vocal_rating);
  const pillars = [face, body, tone].filter(Number.isFinite);
  const feedback = [
    ...report.cards.map((card) => ({ icon: card.module === "face" ? "◉" : "↗", text: card.problem, tip: card.actionable_fix })),
    ...report.audio.actionable_coaching_cards.map((card) => ({ icon: "◌", text: card, tip: "Rehearse this in your next session." })),
  ].slice(0, 6);
  const scoreEntries = [
    ["Eye contact", report.scores.eye_contact_score], ["Expression", report.scores.expression_score],
    ["Smile proxy", report.scores.smile_naturalness_score], ["Posture", report.scores.posture_score],
    ["Gesture", report.scores.gesture_score], ["Movement", report.scores.movement_purposefulness_score],
    ["Spatial use", report.scores.spatial_use_score], ["Voice", tone],
  ].filter(([, score]) => Number.isFinite(score));
  return {
    id: sessionId, projectId, name: "Latest analysis", overallScore: averageAvailable(...pillars), score: averageAvailable(...pillars), tone, body: body ?? 0, face: face ?? 0,
    targetTone: 85, targetBody: 85, targetFace: 85, date: new Date().toISOString().slice(0, 10),
    duration: `${Math.round(report.raw_analysis.duration_seconds)}s`, feedback,
    transcript: report.audio.transcript.text, audioMetrics: report.audio.readable_metrics,
    warnings: report.raw_analysis.warnings, rawAnalysis: report.raw_analysis, qualityGate, report,
    radarData: scoreEntries.map(([subject, score]) => ({ subject, score, fullMark: 100 })),
    timelineData: [{ session: "Current", Facial: face ?? 0, Tone: tone, Body: body ?? 0 }],
  };
}
