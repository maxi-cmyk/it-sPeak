import { improvementAreaLabels, improvementAreaModuleByValue, improvementAreaValues } from "./improvementAreas.mjs";

export const COACHING_THRESHOLD = 80;
const OUTSIDE_TARGET_SCORE_CAP = COACHING_THRESHOLD - 1;

const formatTimestamp = (seconds) => {
  const total = Math.max(0, Math.round(seconds));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
};

const averageAvailable = (...values) => {
  const available = values.filter((value) => Number.isFinite(value));
  return available.length ? Math.round(available.reduce((sum, value) => sum + value, 0) / available.length) : null;
};

function audioMetricMatchesTarget(area, report) {
  const metrics = report.audio?.readable_metrics || {};
  if (area === "pacing" && metrics.pace?.label) return metrics.pace.label.toLowerCase() === "on target";
  if (area === "intonation" && metrics.intonation?.label) return metrics.intonation.label.toLowerCase() === "on target";
  if (area === "filler_words" && metrics.fillers?.label) return metrics.fillers.label.toLowerCase() === "clean";
  return null;
}

function effectiveAreaScore(area, score, report) {
  if (!Number.isFinite(score)) return score;
  return audioMetricMatchesTarget(area, report) === false
    ? Math.min(score, OUTSIDE_TARGET_SCORE_CAP)
    : score;
}

function fillerObservation(fillers) {
  return Number.isFinite(fillers.rate_per_100_words)
    ? `${fillers.value} filler words (${fillers.rate_per_100_words} per 100 words)`
    : `${fillers.value} filler words`;
}

function fillerExamples(fillers, report) {
  const supplied = Array.isArray(fillers.examples) && fillers.examples.length
    ? fillers.examples
    : (report.audio?.speech_issues?.filler_words || []).map((issue) => issue.phrase);
  const examples = [];
  for (const value of supplied) {
    const clean = String(value || "").trim().toLowerCase().replace(/^[^a-z]+|[^a-z]+$/g, "");
    if (clean && !examples.includes(clean)) examples.push(clean);
    if (examples.length === 3) break;
  }
  return examples;
}

function fillerExamplesText(fillers, report) {
  const examples = fillerExamples(fillers, report).map((example) => `“${example}”`);
  if (!examples.length) return "";
  if (examples.length === 1) return ` Example: ${examples[0]}.`;
  const joined = examples.length === 2
    ? `${examples[0]} and ${examples[1]}`
    : `${examples.slice(0, -1).join(", ")}, and ${examples.at(-1)}`;
  return ` Examples: ${joined}.`;
}

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
    return `${fillerObservation(fillers)} flagged (${fillers.label.toLowerCase()}). The target is ${fillers.target_range}.${fillerExamplesText(fillers, report)} ${fillers.meaning}`;
  }
  if (area === "eye_contact" && Number.isFinite(face.eye_contact_ratio)) {
    const lapseStart = face.worst_eye_contact_lapse_start;
    const lapseEnd = face.worst_eye_contact_lapse_end;
    if (Number.isFinite(lapseStart) && Number.isFinite(lapseEnd) && lapseEnd - lapseStart >= 2) {
      return `You held eye contact for ${Math.round(face.eye_contact_ratio * 100)}% of tracked frames. Your longest lapse ran from ${formatTimestamp(lapseStart)} to ${formatTimestamp(lapseEnd)}, where your gaze drifted off camera — bringing it back during that stretch is the fastest way to strengthen audience connection.`;
    }
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

function proficientMessage(area, score, report) {
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
    base = `${fillerObservation(fillers)} detected (${fillers.label.toLowerCase()}), within the ${fillers.target_range} target.${fillerExamplesText(fillers, report)}`;
  } else if (area === "eye_contact" && Number.isFinite(face.eye_contact_ratio)) {
    base = `You held eye contact for ${Math.round(face.eye_contact_ratio * 100)}% of tracked frames. This area scored ${Math.round(score)}/100 against the ${COACHING_THRESHOLD}/100 coaching threshold.`;
  } else if (area === "facial_expression" && Number.isFinite(face.expression_variance)) {
    base = `Facial expression variance measured ${Math.round(face.expression_variance * 100)}%, a strong, visible range.`;
  } else if (area === "posture" && Number.isFinite(body.posture_alignment)) {
    base = `Postural alignment measured ${Math.round(body.posture_alignment * 100)}%, grounded and consistent.`;
  } else if (area === "gestures" && Number.isFinite(body.gesture_frequency) && Number.isFinite(body.gesture_range)) {
    base = `Gestures averaged ${body.gesture_frequency.toFixed(1)} per minute across ${Math.round(body.gesture_range * 100)}% of your range, purposeful and controlled.`;
  } else {
    base = `You are proficient in ${improvementAreaLabels[area]} at ${Math.round(score)}/100.`;
  }
  return base;
}

function buildImprovementGuidance(report, scores) {
  const selected = report.improvement_areas || improvementAreaValues;
  const effectiveScores = Object.fromEntries(
    Object.entries(scores).map(([area, score]) => [area, effectiveAreaScore(area, score, report)]),
  );
  const ranked = selected
    .filter((area) => Number.isFinite(effectiveScores[area]))
    .sort((left, right) => effectiveScores[left] - effectiveScores[right]);
  if (report.improvement_guidance?.length) {
    return report.improvement_guidance.map((item) => {
      const sourceScore = Number.isFinite(effectiveScores[item.area]) ? effectiveScores[item.area] : effectiveAreaScore(item.area, item.score, report);
      const proficient = sourceScore >= COACHING_THRESHOLD;
      return {
        ...item,
        score: sourceScore,
        proficient,
        message: proficient
          ? proficientMessage(item.area, sourceScore, report)
          : nonProficientMessage(item.area, sourceScore, report),
      };
    }).sort((left, right) => left.score - right.score).map((item, index) => ({ ...item, priority: index + 1 }));
  }
  return ranked.map((area, index) => {
    const score = effectiveScores[area];
    const proficient = score >= COACHING_THRESHOLD;
    return {
      area,
      score,
      priority: index + 1,
      proficient,
      message: proficient ? proficientMessage(area, score, report) : nonProficientMessage(area, score, report),
    };
  });
}

function buildObservedFeedback(report, scores) {
  const selected = new Set(report.improvement_areas || improvementAreaValues);
  const effectiveScores = Object.fromEntries(
    Object.entries(scores).map(([area, score]) => [area, effectiveAreaScore(area, score, report)]),
  );
  return improvementAreaValues
    .filter((area) => !selected.has(area) && Number.isFinite(effectiveScores[area]) && effectiveScores[area] < COACHING_THRESHOLD)
    .sort((left, right) => effectiveScores[left] - effectiveScores[right])
    .map((area) => ({
      area,
      module: improvementAreaModuleByValue[area],
      score: effectiveScores[area],
      text: `We observed that ${improvementAreaLabels[area]} scored ${Math.round(effectiveScores[area])}/100, which is below the ${COACHING_THRESHOLD}/100 coaching threshold.`,
      tip: `${nonProficientMessage(area, effectiveScores[area], report)} Consider adding ${improvementAreaLabels[area]} to your selected focus.`,
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
    ...report.cards.map((card) => ({ module: card.module, text: card.problem, tip: card.actionable_fix })),
    ...report.audio.actionable_coaching_cards.map((card) => ({ module: "audio", text: card, tip: "Rehearse this in your next session." })),
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
