import { improvementAreaLabels, improvementAreaModuleByValue, improvementAreaValues } from "./improvementAreas.mjs";

export const COACHING_THRESHOLD = 80;

const averageAvailable = (...values) => {
  const available = values.filter((value) => Number.isFinite(value));
  return available.length ? Math.round(available.reduce((sum, value) => sum + value, 0) / available.length) : null;
};

function nonProficientMessage(area, score, report) {
  const metrics = report.audio?.readable_metrics || {};
  const face = report.raw_analysis?.face || {};
  const body = report.raw_analysis?.body || {};
  if (area === "pacing" && metrics.pace) {
    const pace = metrics.pace;
    return `Your pace measured ${pace.value} ${pace.unit} (${pace.label.toLowerCase()}), outside the ${pace.target_range} target. ${pace.meaning}`;
  }
  if (area === "intonation" && metrics.intonation) {
    const intonation = metrics.intonation;
    return `Pitch variation measured ${intonation.value} ${intonation.unit} (${intonation.label.toLowerCase()}), against a target of ${intonation.target_range}. ${intonation.meaning}`;
  }
  if (area === "filler_words" && metrics.fillers) {
    const fillers = metrics.fillers;
    return `${fillers.value} filler words flagged (${fillers.label.toLowerCase()}), above the ${fillers.target_range} target. ${fillers.meaning}`;
  }
  if (area === "eye_contact" && Number.isFinite(face.eye_contact_ratio)) {
    return `You held eye contact for ${Math.round(face.eye_contact_ratio * 100)}% of tracked frames — building toward sustained camera connection will strengthen audience trust.`;
  }
  if (area === "facial_expression" && Number.isFinite(face.expression_variance)) {
    return `Facial expression variance measured ${Math.round(face.expression_variance * 100)}% — more visible range will help your key moments land.`;
  }
  if (area === "posture" && Number.isFinite(body.posture_alignment)) {
    return `Postural alignment measured ${Math.round(body.posture_alignment * 100)}% — a more grounded stance will project confidence.`;
  }
  if (area === "gestures" && Number.isFinite(body.gesture_frequency) && Number.isFinite(body.gesture_range)) {
    return `Gestures averaged ${body.gesture_frequency.toFixed(1)} per minute across ${Math.round(body.gesture_range * 100)}% of your range — widen your movements for more purposeful emphasis.`;
  }
  return `This area scored ${Math.round(score)}/100, below the ${COACHING_THRESHOLD}/100 coaching threshold — prioritise it in your next rehearsal.`;
}

function proficientMessage(area, score, report, nextArea) {
  const metrics = report.audio?.readable_metrics || {};
  const face = report.raw_analysis?.face || {};
  const body = report.raw_analysis?.body || {};
  let base;
  if (area === "pacing" && metrics.pace) {
    const pace = metrics.pace;
    base = `Your pace held at ${pace.value} ${pace.unit} (${pace.label.toLowerCase()}), inside the ${pace.target_range} target.`;
  } else if (area === "intonation" && metrics.intonation) {
    const intonation = metrics.intonation;
    base = `Pitch variation measured ${intonation.value} ${intonation.unit} (${intonation.label.toLowerCase()}), within the ${intonation.target_range} target.`;
  } else if (area === "filler_words" && metrics.fillers) {
    const fillers = metrics.fillers;
    base = `Only ${fillers.value} filler words detected (${fillers.label.toLowerCase()}), under the ${fillers.target_range} target.`;
  } else if (area === "eye_contact" && Number.isFinite(face.eye_contact_ratio)) {
    base = `You held eye contact for ${Math.round(face.eye_contact_ratio * 100)}% of tracked frames, well above the coaching threshold.`;
  } else if (area === "facial_expression" && Number.isFinite(face.expression_variance)) {
    base = `Facial expression variance measured ${Math.round(face.expression_variance * 100)}%, a strong, visible range.`;
  } else if (area === "posture" && Number.isFinite(body.posture_alignment)) {
    base = `Postural alignment measured ${Math.round(body.posture_alignment * 100)}%, grounded and consistent.`;
  } else if (area === "gestures" && Number.isFinite(body.gesture_frequency) && Number.isFinite(body.gesture_range)) {
    base = `Gestures averaged ${body.gesture_frequency.toFixed(1)} per minute across ${Math.round(body.gesture_range * 100)}% of your range, purposeful and controlled.`;
  } else {
    base = `You are proficient in ${improvementAreaLabels[area]} at ${Math.round(score)}/100.`;
  }
  return nextArea
    ? `${base} Prioritise ${improvementAreaLabels[nextArea]}, your lowest-scoring other selected area.`
    : `${base} Maintain this strength and select another area for your next growth target.`;
}

function buildImprovementGuidance(report, scores) {
  const selected = report.improvement_areas || improvementAreaValues;
  const ranked = selected
    .filter((area) => Number.isFinite(scores[area]))
    .sort((left, right) => scores[left] - scores[right]);
  if (report.improvement_guidance?.length) {
    return report.improvement_guidance.map((item) => {
      const proficient = item.score >= COACHING_THRESHOLD;
      if (proficient === item.proficient) return item;
      const nextArea = ranked.find((candidate) => candidate !== item.area);
      return {
        ...item,
        proficient,
        message: proficient
          ? proficientMessage(item.area, item.score, report, nextArea)
          : nonProficientMessage(item.area, item.score, report),
      };
    });
  }
  return ranked.map((area, index) => {
    const proficient = scores[area] >= COACHING_THRESHOLD;
    const nextArea = ranked.find((candidate) => candidate !== area);
    return {
      area,
      score: scores[area],
      priority: index + 1,
      proficient,
      message: proficient ? proficientMessage(area, scores[area], report, nextArea) : nonProficientMessage(area, scores[area], report),
    };
  });
}

function buildObservedFeedback(report, scores) {
  const selected = new Set(report.improvement_areas || improvementAreaValues);
  return improvementAreaValues
    .filter((area) => !selected.has(area) && Number.isFinite(scores[area]) && scores[area] < COACHING_THRESHOLD)
    .sort((left, right) => scores[left] - scores[right])
    .map((area) => ({
      area,
      module: improvementAreaModuleByValue[area],
      score: scores[area],
      text: `We observed that ${improvementAreaLabels[area]} scored ${Math.round(scores[area])}/100, which is below the ${COACHING_THRESHOLD}/100 coaching threshold.`,
      tip: `${nonProficientMessage(area, scores[area], report)} Consider adding ${improvementAreaLabels[area]} to your selected focus.`,
    }));
}

export function reportToSession(report, sessionId, projectId = "1", qualityGate = null) {
  const face = averageAvailable(report.scores.eye_contact_score, report.scores.expression_score);
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
  const observedFeedback = buildObservedFeedback(report, scoresByArea);
  const activeModules = new Set(improvementGuidance.filter((item) => !item.proficient && item.score < COACHING_THRESHOLD).map((item) => improvementAreaModuleByValue[item.area]));
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
    ["Eye contact", report.scores.eye_contact_score], ["Facial expressions", report.scores.expression_score],
    ["Posture", report.scores.posture_score],
    ["Gesture", report.scores.gesture_score], ["Movement", report.scores.movement_purposefulness_score],
    ["Spatial use", report.scores.spatial_use_score], ["Voice", tone],
  ].filter(([, score]) => Number.isFinite(score));
  return {
    id: sessionId, projectId, name: "Latest analysis", overallScore: averageAvailable(...pillars), score: averageAvailable(...pillars), tone, body: body ?? 0, face: face ?? 0,
    targetTone: 85, targetBody: 85, targetFace: 85, date: new Date().toISOString().slice(0, 10),
    duration: `${Math.round(report.raw_analysis.duration_seconds)}s`, feedback, observedFeedback, improvementGuidance,
    transcript: report.audio.transcript.text, audioMetrics: report.audio.readable_metrics,
    warnings: report.raw_analysis.warnings, rawAnalysis: report.raw_analysis, qualityGate, report,
    radarData: scoreEntries.map(([subject, score]) => ({ subject, score, fullMark: 100 })),
  };
}
