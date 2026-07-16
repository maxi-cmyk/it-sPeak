export function containViewport(containerWidth, containerHeight, videoWidth, videoHeight) {
  if (!containerWidth || !containerHeight || !videoWidth || !videoHeight) return { x: 0, y: 0, width: 0, height: 0 };
  const scale = Math.min(containerWidth / videoWidth, containerHeight / videoHeight);
  const width = videoWidth * scale;
  const height = videoHeight * scale;
  return { x: (containerWidth - width) / 2, y: (containerHeight - height) / 2, width, height };
}

export const decodePoint = (point) => ({ x: point[0] / 65535, y: point[1] / 65535, visibility: point[2] === undefined ? 1 : point[2] / 255 });

export function frameAtTime(frames, time, maxGap = 0.45) {
  if (!frames?.length) return null;
  if (time < frames[0].t - maxGap / 2 || time > frames.at(-1).t + maxGap / 2) return null;
  let low = 0;
  let high = frames.length - 1;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    if (frames[mid].t < time) low = mid + 1;
    else high = mid - 1;
  }
  const before = frames[Math.max(0, low - 1)];
  const after = frames[Math.min(frames.length - 1, low)];
  const beforeAnyConfidence = Math.max(before?.confidence || 0, before?.pose_confidence || 0);
  const afterAnyConfidence = Math.max(after?.confidence || 0, after?.pose_confidence || 0);
  if (!before || !after || after.t - before.t > maxGap || Math.min(beforeAnyConfidence, afterAnyConfidence) < 0.25) {
    const nearest = !after || (before && time - before.t <= after.t - time) ? before : after;
    return nearest && Math.abs(nearest.t - time) <= maxGap / 2 && Math.max(nearest.confidence || 0, nearest.pose_confidence || 0) >= 0.25 ? nearest : null;
  }
  if (before === after || after.t === before.t) return before;
  const mix = (time - before.t) / (after.t - before.t);
  const interpolate = (a, b) => a && b && a.length === b.length && a.every(Array.isArray) && b.every(Array.isArray) ? a.map((point, index) => point.map((value, coordinate) => Math.round(value + (b[index][coordinate] - value) * mix))) : (mix < 0.5 ? a : b);
  const faceBox = before.face_box && after.face_box ? interpolate([before.face_box], [after.face_box])?.[0] : (mix < 0.5 ? before.face_box : after.face_box);
  return { ...before, t: time, face: interpolate(before.face, after.face), pose: interpolate(before.pose, after.pose), face_box: faceBox, eye_contact: mix < 0.5 ? before.eye_contact : after.eye_contact, confidence: Math.min(before.confidence || 0, after.confidence || 0), pose_confidence: Math.min(before.pose_confidence || 0, after.pose_confidence || 0) };
}

export function eyeContactIntervals(frames, duration) {
  if (!frames?.length) return [];
  const intervals = [];
  let state = frames[0].eye_contact || "unknown";
  let start = 0;
  for (let index = 1; index < frames.length; index += 1) {
    const next = frames[index].eye_contact || "unknown";
    if (next !== state) {
      intervals.push({ state, start, end: frames[index].t });
      state = next;
      start = frames[index].t;
    }
  }
  intervals.push({ state, start, end: duration || frames.at(-1).t });
  return intervals;
}
