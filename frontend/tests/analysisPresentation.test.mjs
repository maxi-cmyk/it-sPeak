import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { analysisProgress, monotonicProgressValue, splitMetricPhrases, visibleAnalysisWarnings } from "../lib/analysisPresentation.mjs";

test("analysis progress prefers reported progress without showing completion early", () => {
  assert.deepEqual(analysisProgress({ status: "processing", progress: { percent: 72.4 } }), { value: 72, source: "reported" });
  assert.deepEqual(analysisProgress({ status: "processing", progressPercent: 100 }), { value: 99, source: "reported" });
  assert.deepEqual(analysisProgress({ status: "success", progressPercent: 55 }), { value: 100, source: "status" });
});

test("analysis progress follows known backend stages when no percentage is supplied", () => {
  assert.equal(analysisProgress({ status: "quality_check" }).value, 30);
  assert.equal(analysisProgress({ status: "processing", stage: "Analyzing voice and transcript" }).value, 75);
  assert.equal(analysisProgress({ status: "processing", stage: "Generating grounded coaching" }).value, 90);
});

test("analysis progress never regresses while polling the same session", () => {
  assert.equal(monotonicProgressValue(75, 60), 75);
  assert.equal(monotonicProgressValue(75, 90), 90);
  assert.equal(monotonicProgressValue(undefined, 30), 30);
});

test("metric phrase splitting marks measured values without altering surrounding copy", () => {
  const copy = "You scored 191 words per min, with 4 filler words, 82% eye contact and 3.5 per minute gesture frequency.";
  const parts = splitMetricPhrases(copy);
  assert.deepEqual(parts.filter((part) => part.metric).map((part) => part.text), ["191 words per min", "4 filler words", "82%", "3.5 per minute"]);
  assert.equal(parts.map((part) => part.text).join(""), copy);
});

test("metric phrase splitting supports score and range formats", () => {
  const parts = splitMetricPhrases("Pace was 145–165 words per minute and the score was 78/100.");
  assert.deepEqual(parts.filter((part) => part.metric).map((part) => part.text), ["145–165 words per minute", "78/100"]);
});

test("technical camera and proxy caveats are hidden from the analysis UI", () => {
  const warnings = visibleAnalysisWarnings(
    { limitations: [
      "Spatial-use estimates assume a stationary camera.",
      "Smile AU6/AU12 values are geometric proxies, not trained FACS detections.",
      "Face visibility was intermittent.",
    ] },
    { warnings: [
      "Spatial-use scoring assumes a stationary camera.",
      "Face visibility was intermittent.",
      "Audio confidence is low.",
    ] },
  );
  assert.deepEqual(warnings, ["Face visibility was intermittent.", "Audio confidence is low."]);
});

test("combined analysis presents one threshold and recoverable result states", async () => {
  const page = await readFile(new URL("../app/session/[id]/page.js", import.meta.url), "utf8");
  const player = await readFile(new URL("../components/VideoAnalysisPlayer.js", import.meta.url), "utf8");

  assert.equal(page.includes('RatingBar label="Voice"'), true);
  assert.equal(page.includes("target={session.targetTone}"), false);
  assert.equal(page.includes("setTranscriptError(requestError.message)"), true);
  assert.equal(page.includes("setLoadVersion((current) => current + 1)"), true);
  assert.equal(page.includes("const showCoaching = selectedNeedsWork.length > 0 || observedFeedback.length > 0"), true);
  assert.equal(player.includes(">Warning</p>"), true);
});
