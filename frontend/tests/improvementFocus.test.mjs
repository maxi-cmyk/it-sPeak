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
  assert.doesNotMatch(session.improvementGuidance[2].message, /Prioritise/);
  assert.deepEqual(session.feedback.map((item) => item.module), ["audio", "body"]);
  assert.equal(session.feedback.some((item) => item.text === "Face advice"), false);
  assert.deepEqual(session.observedFeedback.map((item) => item.area), ["filler_words", "gestures", "intonation"]);
  assert.equal(session.observedFeedback[0].text, "We observed that Filler words scored 65/100, which is below the 80/100 coaching threshold.");
  assert.match(session.observedFeedback[0].tip, /Consider adding Filler words to your selected focus/);
  assert.equal(session.face, 85);
  assert.equal(session.radarData.some((item) => item.subject === "Facial expressions"), true);
  assert.equal(session.radarData.some((item) => item.subject === "Expression"), false);
  assert.equal(session.radarData.some((item) => item.subject === "Smile proxy"), false);
});

test("a score of 80 is proficient and does not generate coaching feedback", () => {
  const session = reportToSession({
    improvement_areas: ["facial_expression"],
    improvement_guidance: [{ area: "facial_expression", score: 80, priority: 1, proficient: false, message: "Old coaching message" }],
    scores: {
      eye_contact_score: 80,
      expression_score: 80,
      posture_score: 85,
      gesture_score: 85,
    },
    cards: [{ module: "face", problem: "Face advice", actionable_fix: "Face drill" }],
    audio: {
      performance_scores: { aggregate_vocal_rating: 85, pacing_alignment: 85, vocal_intonation_variety: 85, word_choice_efficiency: 85 },
      actionable_coaching_cards: [],
      transcript: { text: "Hello" },
      readable_metrics: {},
    },
    raw_analysis: { duration_seconds: 30, warnings: [] },
  }, "session-2", "project-1");

  assert.equal(session.improvementGuidance[0].proficient, true);
  assert.equal(session.feedback.length, 0);
  assert.equal(session.observedFeedback.some((item) => item.area === "eye_contact"), false);
});

test("observed facial-expression feedback uses the below-threshold wording", () => {
  const session = reportToSession({
    improvement_areas: ["pacing"],
    scores: {
      eye_contact_score: 85,
      expression_score: 0,
      posture_score: 85,
      gesture_score: 85,
    },
    cards: [],
    audio: {
      performance_scores: { aggregate_vocal_rating: 85, pacing_alignment: 85, vocal_intonation_variety: 85, word_choice_efficiency: 85 },
      actionable_coaching_cards: [],
      transcript: { text: "Hello" },
      readable_metrics: {},
    },
    raw_analysis: { duration_seconds: 30, warnings: [] },
  }, "session-3", "project-1");

  assert.equal(
    session.observedFeedback.find((item) => item.area === "facial_expression")?.text,
    "We observed that Facial expressions scored 0/100, which is below the 80/100 coaching threshold.",
  );
});

test("a legacy too-fast pace is moved below proficiency and described as outside target", () => {
  const session = reportToSession({
    improvement_areas: ["pacing"],
    improvement_guidance: [{ area: "pacing", score: 85, priority: 1, proficient: true, message: "Old inside-target message" }],
    scores: { eye_contact_score: 85, expression_score: 85, posture_score: 85, gesture_score: 85 },
    cards: [],
    audio: {
      performance_scores: { aggregate_vocal_rating: 85, pacing_alignment: 85, vocal_intonation_variety: 85, word_choice_efficiency: 85 },
      actionable_coaching_cards: [],
      transcript: { text: "Hello" },
      readable_metrics: {
        pace: {
          value: 190.9,
          unit: "words per minute",
          label: "Too fast",
          target_range: "148.7-172.7 words per minute",
          meaning: "The delivery may feel rushed.",
        },
      },
    },
    raw_analysis: { duration_seconds: 30, warnings: [] },
  }, "session-4", "project-1");

  assert.equal(session.improvementGuidance[0].score, 79);
  assert.equal(session.improvementGuidance[0].proficient, false);
  assert.match(session.improvementGuidance[0].message, /outside the 148\.7-172\.7 words per minute target/);
  assert.doesNotMatch(session.improvementGuidance[0].message, /inside the/);
});

test("proficient eye contact names the score threshold without another priority", () => {
  const session = reportToSession({
    improvement_areas: ["eye_contact"],
    scores: { eye_contact_score: 87, expression_score: 85, posture_score: 85, gesture_score: 85 },
    cards: [],
    audio: {
      performance_scores: { aggregate_vocal_rating: 85, pacing_alignment: 85, vocal_intonation_variety: 85, word_choice_efficiency: 85 },
      actionable_coaching_cards: [],
      transcript: { text: "Hello" },
      readable_metrics: {},
    },
    raw_analysis: { duration_seconds: 30, warnings: [], face: { eye_contact_ratio: 0.74 } },
  }, "session-5", "project-1");

  assert.match(session.improvementGuidance[0].message, /87\/100 against the 80\/100 coaching threshold/);
  assert.doesNotMatch(session.improvementGuidance[0].message, /Prioritise/);
});

test("filler feedback names at most three distinct detected examples", () => {
  const session = reportToSession({
    improvement_areas: ["filler_words"],
    scores: { eye_contact_score: 85, expression_score: 85, posture_score: 85, gesture_score: 85 },
    cards: [],
    audio: {
      performance_scores: { aggregate_vocal_rating: 79, pacing_alignment: 85, vocal_intonation_variety: 85, word_choice_efficiency: 79 },
      actionable_coaching_cards: [],
      transcript: { text: "Um, like, um, so, actually" },
      readable_metrics: {
        fillers: { value: 5, rate_per_100_words: 5, label: "Some fillers", target_range: "0-2 per 100 words", meaning: "They are noticeable." },
      },
      speech_issues: {
        filler_words: [{ phrase: "Um," }, { phrase: "like" }, { phrase: "um" }, { phrase: "so" }, { phrase: "actually" }],
      },
    },
    raw_analysis: { duration_seconds: 30, warnings: [] },
  }, "session-6", "project-1");

  assert.match(session.improvementGuidance[0].message, /Examples: “um”, “like”, and “so”\./);
  assert.doesNotMatch(session.improvementGuidance[0].message, /actually/);
});
