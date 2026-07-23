import assert from "node:assert/strict";
import test from "node:test";
import { buildProgressData, CURRENT_AUDIO_SCORING_VERSION } from "../lib/progressData.mjs";

test("mixed scoring versions omit legacy Tone points but keep face and body history", () => {
  const data = buildProgressData([
    { name: "Session 2", tone: 88, face: 82, body: 84, audioScoringVersion: CURRENT_AUDIO_SCORING_VERSION },
    { name: "Session 1", tone: 91, face: 75, body: 77, audioScoringVersion: "pyin-hz-v1" },
  ]);

  assert.deepEqual(data, [
    { session: "Session 1", "Facial expressions": 75, Tone: undefined, Body: 77 },
    { session: "Session 2", "Facial expressions": 82, Tone: 88, Body: 84 },
  ]);
});

test("projects containing only legacy reports retain their historical Tone line", () => {
  const data = buildProgressData([
    { name: "Session 2", tone: 80, face: 82, body: 84, audioScoringVersion: "pyin-hz-v1" },
    { name: "Session 1", tone: 70, face: 75, body: 77, audioScoringVersion: "pyin-hz-v1" },
  ]);

  assert.deepEqual(data.map((point) => point.Tone), [70, 80]);
});
