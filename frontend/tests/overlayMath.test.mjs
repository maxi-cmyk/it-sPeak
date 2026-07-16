import test from "node:test";
import assert from "node:assert/strict";
import { containViewport, eyeContactIntervals, frameAtTime } from "../lib/overlayMath.mjs";

test("contain viewport maps a portrait source inside a wide player", () => {
  assert.deepEqual(containViewport(800, 450, 1080, 1920), { x: 273.4375, y: 0, width: 253.125, height: 450 });
});

test("short confident gaps interpolate and long gaps stay hidden", () => {
  const frames = [{ t: 0, confidence: 1, face: [[0, 0]] }, { t: .2, confidence: 1, face: [[100, 100]] }];
  assert.deepEqual(frameAtTime(frames, .1, .4).face, [[50, 50]]);
  assert.equal(frameAtTime(frames, 2, .4), null);
});

test("pose remains available when a face is not detected", () => {
  const frames = [{ t: 0, confidence: 0, pose_confidence: .9, pose: [[0, 0, 255]] }, { t: .2, confidence: 0, pose_confidence: .9, pose: [[100, 100, 255]] }];
  assert.deepEqual(frameAtTime(frames, .1, .4).pose, [[50, 50, 255]]);
});

test("eye contact intervals preserve unknown regions", () => {
  const intervals = eyeContactIntervals([{ t: 0, eye_contact: "on_camera" }, { t: 1, eye_contact: "unknown" }, { t: 2, eye_contact: "away" }], 3);
  assert.deepEqual(intervals.map((item) => item.state), ["on_camera", "unknown", "away"]);
});
