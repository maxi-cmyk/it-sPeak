const STATUS_PROGRESS = {
  idle: 0,
  uploading: 10,
  quality_check: 30,
  needs_confirmation: 35,
  queued: 45,
  processing: 60,
  success: 100,
};

const PROCESSING_STAGE_PROGRESS = [
  [/facial|body movement/i, 60],
  [/voice|transcript/i, 75],
  [/coaching/i, 90],
];

const HIDDEN_ANALYSIS_WARNINGS = new Set([
  "Spatial-use estimates assume a stationary camera.",
  "Smile AU6/AU12 values are geometric proxies, not trained FACS detections.",
  "Spatial-use scoring assumes a stationary camera.",
]);

function numericProgress(job) {
  const candidates = [
    job?.progressPercent,
    job?.progress_percentage,
    typeof job?.progress === "number" ? job.progress : null,
    job?.progress?.percent,
    job?.progress?.percentage,
  ];
  return candidates.find(Number.isFinite);
}

export function analysisProgress(job = {}) {
  if (job.status === "success") return { value: 100, source: "status" };

  const reported = numericProgress(job);
  if (Number.isFinite(reported)) {
    return { value: Math.min(99, Math.max(0, Math.round(reported))), source: "reported" };
  }

  if (job.status === "processing") {
    const stageMatch = PROCESSING_STAGE_PROGRESS.find(([pattern]) => pattern.test(job.stage || ""));
    if (stageMatch) return { value: stageMatch[1], source: "stage" };
  }

  return {
    value: STATUS_PROGRESS[job.status] ?? 5,
    source: "status",
  };
}

export function visibleAnalysisWarnings(qualityGate, analysis) {
  const warnings = [
    ...(qualityGate?.limitations || []),
    ...(analysis?.warnings || []),
  ];
  return [...new Set(warnings)].filter((warning) => !HIDDEN_ANALYSIS_WARNINGS.has(String(warning).trim()));
}

const METRIC_PATTERN = /-?\d[\d,]*(?:\.\d+)?(?:\s*[–—-]\s*-?\d[\d,]*(?:\.\d+)?)?\s*(?:%|\/\s*\d+|words?\s+(?:per|\/)\s+(?:minute|min|second|sec)|filler\s+words?|fillers?|gestures?(?:\s+per\s+(?:minute|min|second|sec))?|per\s+(?:minute|min|second|sec)|(?:wpm|hz|st|dbfs|db|seconds?|secs?|minutes?|mins?|frames?|pixels?|px|degrees?))(?=\s|[.,;:!?)]|$)/gi;

export function splitMetricPhrases(value) {
  const text = String(value ?? "");
  const parts = [];
  let cursor = 0;

  for (const match of text.matchAll(METRIC_PATTERN)) {
    if (match.index > cursor) parts.push({ text: text.slice(cursor, match.index), metric: false });
    parts.push({ text: match[0], metric: true });
    cursor = match.index + match[0].length;
  }

  if (cursor < text.length) parts.push({ text: text.slice(cursor), metric: false });
  return parts.length ? parts : [{ text, metric: false }];
}
