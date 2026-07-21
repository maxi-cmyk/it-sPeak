import { improvementAreaLabels, improvementAreaModuleByValue, improvementAreaValues } from "./improvementAreas.mjs";

const averageAvailable = (...values) => {
  const available = values.filter((value) => Number.isFinite(value));
  return available.length ? Math.round(available.reduce((sum, value) => sum + value, 0) / available.length) : null;
};

function buildImprovementGuidance(report, scores) {
  if (report.improvement_guidance?.length) return report.improvement_guidance;
  const selected = report.improvement_areas || improvementAreaValues;
  const ranked = selected
    .filter((area) => Number.isFinite(scores[area]))
    .sort((left, right) => scores[left] - scores[right]);
  return ranked.map((area, index) => {
    const proficient = scores[area] > 80;
    const nextArea = ranked.find((candidate) => candidate !== area);
    return {
      area,
      score: scores[area],
      priority: index + 1,
      proficient,
      message: proficient
        ? nextArea
          ? `You are proficient in ${improvementAreaLabels[area]} at ${Math.round(scores[area])}. Prioritise ${improvementAreaLabels[nextArea]}, your lowest-scoring other selected area.`
          : `You are proficient in ${improvementAreaLabels[area]} at ${Math.round(scores[area])}. Maintain this strength and select another area for your next growth target.`
        : `Priority ${index + 1}: improve ${improvementAreaLabels[area]} (${Math.round(scores[area])}), starting with the lowest-scoring selected area.`,
    };
  });
}

export function reportToSession(report, sessionId, projectId = "1", qualityGate = null) {
  const face = averageAvailable(report.scores.eye_contact_score, report.scores.expression_score, report.scores.smile_naturalness_score);
  const body = averageAvailable(report.scores.posture_score, report.scores.gesture_score, report.scores.movement_purposefulness_score, report.scores.spatial_use_score);
  const tone = Math.round(report.audio.performance_scores.aggregate_vocal_rating);
  const pillars = [face, body, tone].filter(Number.isFinite);
  const scoresByArea = {
    pacing: report.audio.performance_scores.pacing_alignment,
    intonation: report.audio.performance_scores.vocal_intonation_variety,
    filler_words: report.audio.performance_scores.word_choice_efficiency,
    eye_contact: report.scores.eye_contact_score,
    facial_expression: report.scores.expression_score,
    posture: report.scores.posture_score,
    gestures: report.scores.gesture_score,
  };
  const improvementGuidance = buildImprovementGuidance(report, scoresByArea);
  const activeModules = new Set(improvementGuidance.filter((item) => !item.proficient && item.score <= 80).map((item) => improvementAreaModuleByValue[item.area]));
  const priorityByModule = Object.fromEntries(
    ["audio", "face", "body"].map((module) => [module, Math.min(...improvementGuidance.filter((item) => improvementAreaModuleByValue[item.area] === module && !item.proficient).map((item) => item.priority), 99)]),
  );
  const feedback = [
    ...report.cards.map((card) => ({ module: card.module, icon: card.module === "face" ? "◉" : "↗", text: card.problem, tip: card.actionable_fix })),
    ...report.audio.actionable_coaching_cards.map((card) => ({ module: "audio", icon: "◌", text: card, tip: "Rehearse this in your next session." })),
  ]
    .filter((item) => activeModules.has(item.module))
    .sort((left, right) => priorityByModule[left.module] - priorityByModule[right.module])
    .slice(0, 6);
  const scoreEntries = [
    ["Eye contact", report.scores.eye_contact_score], ["Expression", report.scores.expression_score],
    ["Smile proxy", report.scores.smile_naturalness_score], ["Posture", report.scores.posture_score],
    ["Gesture", report.scores.gesture_score], ["Movement", report.scores.movement_purposefulness_score],
    ["Spatial use", report.scores.spatial_use_score], ["Voice", tone],
  ].filter(([, score]) => Number.isFinite(score));
  return {
    id: sessionId, projectId, name: "Latest analysis", overallScore: averageAvailable(...pillars), score: averageAvailable(...pillars), tone, body: body ?? 0, face: face ?? 0,
    targetTone: 85, targetBody: 85, targetFace: 85, date: new Date().toISOString().slice(0, 10),
    duration: `${Math.round(report.raw_analysis.duration_seconds)}s`, feedback, improvementGuidance,
    transcript: report.audio.transcript.text, audioMetrics: report.audio.readable_metrics,
    warnings: report.raw_analysis.warnings, rawAnalysis: report.raw_analysis, qualityGate, report,
    radarData: scoreEntries.map(([subject, score]) => ({ subject, score, fullMark: 100 })),
    timelineData: [{ session: "Current", Facial: face ?? 0, Tone: tone, Body: body ?? 0 }],
  };
}
