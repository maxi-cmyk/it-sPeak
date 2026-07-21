import assert from "node:assert/strict";
import test from "node:test";
import { reportToSession } from "../lib/reportAdapter.js";

test("selected improvement feedback is ranked lowest first and suppresses proficient areas", () => {
  const session = reportToSession({
    improvement_areas: ["pacing", "eye_contact", "posture"],
    scores: {
      eye_contact_score: 85,
      expression_score: 85,
      smile_naturalness_score: 0,
      posture_score: 70,
      gesture_score: 70,
    },
    cards: [
      { module: "face", problem: "Face advice", actionable_fix: "Face drill" },
      { module: "body", problem: "Body advice", actionable_fix: "Body drill" },
    ],
    audio: {
      performance_scores: { aggregate_vocal_rating: 65, pacing_alignment: 55, vocal_intonation_variety: 75, word_choice_efficiency: 65 },
      actionable_coaching_cards: ["Voice advice"],
      transcript: { text: "Hello" },
      readable_metrics: {},
    },
    raw_analysis: { duration_seconds: 30, warnings: [] },
  }, "session-1", "project-1");

  assert.deepEqual(session.improvementGuidance.map((item) => item.area), ["pacing", "posture", "eye_contact"]);
  assert.equal(session.improvementGuidance[2].proficient, true);
  assert.match(session.improvementGuidance[2].message, /Prioritise Pacing/);
  assert.deepEqual(session.feedback.map((item) => item.module), ["audio", "body"]);
  assert.equal(session.feedback.some((item) => item.text === "Face advice"), false);
  assert.equal(session.face, 85);
  assert.equal(session.radarData.some((item) => item.subject === "Smile proxy"), false);
});
