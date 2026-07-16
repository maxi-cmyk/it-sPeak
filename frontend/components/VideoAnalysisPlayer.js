"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { getLandmarks, getVideoUrl } from "@/lib/api";
import { containViewport, decodePoint, eyeContactIntervals, frameAtTime } from "@/lib/overlayMath.mjs";

const POSE_CONNECTIONS = [[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28]];
const STATE_COLORS = { on_camera: "#34d399", away: "#f59e0b", unknown: "#52525b" };

export default function VideoAnalysisPlayer({ sessionId, token, analysis, qualityGate }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const [artifact, setArtifact] = useState(null);
  const [error, setError] = useState(null);
  const [toggles, setToggles] = useState({ face: true, skeleton: true, eye: true });
  const videoUrl = useMemo(() => getVideoUrl(sessionId, token), [sessionId, token]);
  const intervals = useMemo(() => eyeContactIntervals(artifact?.frames, artifact?.duration_seconds), [artifact]);

  useEffect(() => {
    const controller = new AbortController();
    getLandmarks(sessionId, token, controller.signal).then(setArtifact).catch((requestError) => { if (requestError.name !== "AbortError") setError(requestError.message); });
    return () => controller.abort();
  }, [sessionId, token]);

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !artifact) return undefined;
    const draw = (_, metadata = {}) => {
      const rect = video.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      if (canvas.width !== Math.round(rect.width * dpr) || canvas.height !== Math.round(rect.height * dpr)) {
        canvas.width = Math.round(rect.width * dpr); canvas.height = Math.round(rect.height * dpr);
      }
      const context = canvas.getContext("2d");
      context.setTransform(dpr, 0, 0, dpr, 0, 0); context.clearRect(0, 0, rect.width, rect.height);
      const frame = frameAtTime(artifact.frames, metadata.mediaTime ?? video.currentTime, 2.25 / artifact.sample_fps);
      if (!frame) return;
      const viewport = containViewport(rect.width, rect.height, video.videoWidth, video.videoHeight);
      const map = (encoded) => { const point = decodePoint(encoded); return [viewport.x + point.x * viewport.width, viewport.y + point.y * viewport.height, point.visibility]; };
      if (toggles.face && frame.face && frame.confidence >= .25) {
        context.fillStyle = "rgba(167,139,250,.72)";
        for (let index = 0; index < frame.face.length; index += 2) { const [x, y] = map(frame.face[index]); context.beginPath(); context.arc(x, y, 0.8, 0, Math.PI * 2); context.fill(); }
      }
      if (toggles.skeleton && frame.pose && frame.pose_confidence >= .25) {
        context.strokeStyle = "rgba(34,211,238,.9)"; context.lineWidth = 2;
        for (const [from, to] of POSE_CONNECTIONS) { const a = map(frame.pose[from]); const b = map(frame.pose[to]); if (a[2] < .45 || b[2] < .45) continue; context.beginPath(); context.moveTo(a[0], a[1]); context.lineTo(b[0], b[1]); context.stroke(); }
      }
      if (toggles.eye && frame.face_box && frame.confidence >= .25) {
        const [x1, y1] = map([frame.face_box[0], frame.face_box[1]]); const [x2, y2] = map([frame.face_box[2], frame.face_box[3]]);
        context.strokeStyle = STATE_COLORS[frame.eye_contact] || STATE_COLORS.unknown; context.lineWidth = 2; context.strokeRect(x1, y1, x2 - x1, y2 - y1);
      }
    };
    const fallback = () => draw();
    if (typeof video.requestVideoFrameCallback === "function") {
      const loop = (now, metadata) => { draw(now, metadata); animationRef.current = video.requestVideoFrameCallback(loop); };
      animationRef.current = video.requestVideoFrameCallback(loop);
    } else video.addEventListener("timeupdate", fallback);
    window.addEventListener("resize", fallback);
    return () => { if (animationRef.current && video.cancelVideoFrameCallback) video.cancelVideoFrameCallback(animationRef.current); video.removeEventListener("timeupdate", fallback); window.removeEventListener("resize", fallback); };
  }, [artifact, toggles]);

  const confidence = analysis?.metric_confidence || {};
  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 mb-6">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
        <div><p className="text-xs uppercase tracking-[0.18em] text-violet-400">Frame-by-frame evidence</p><h2 className="mt-1 text-lg font-semibold text-zinc-100">Review what the analysis saw</h2></div>
        <div className="flex gap-2" aria-label="Overlay controls">{Object.entries({ face: "Face", skeleton: "Skeleton", eye: "Eye contact" }).map(([key, label]) => <button key={key} aria-pressed={toggles[key]} onClick={() => setToggles((current) => ({ ...current, [key]: !current[key] }))} className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${toggles[key] ? "border-violet-400/60 bg-violet-500/15 text-violet-200" : "border-zinc-700 text-zinc-500"}`}>{label}</button>)}</div>
      </div>
      <div className="relative overflow-hidden rounded-xl bg-black aspect-video">
        <video ref={videoRef} src={videoUrl} controls preload="metadata" playsInline crossOrigin="anonymous" referrerPolicy="no-referrer" className="h-full w-full object-contain" />
        <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true" />
      </div>
      {error && <p className="mt-3 text-xs text-red-300">Overlays unavailable: {error}</p>}
      {intervals.length > 0 && <div className="mt-4"><div className="flex items-center justify-between mb-2"><p className="text-xs font-medium text-zinc-400">Eye-contact timeline</p><div className="flex gap-3 text-[10px] text-zinc-500">{Object.entries(STATE_COLORS).map(([state, color]) => <span key={state} className="flex items-center gap-1"><i className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />{state.replace("_", " ")}</span>)}</div></div><div className="flex h-4 overflow-hidden rounded-full bg-zinc-800">{intervals.map((interval, index) => <button key={`${interval.start}-${index}`} title={`${interval.state.replace("_", " ")} · ${interval.start.toFixed(1)}s`} aria-label={`Seek to ${interval.start.toFixed(1)} seconds, ${interval.state}`} onClick={() => { videoRef.current.currentTime = interval.start; }} style={{ width: `${Math.max(0.5, (interval.end - interval.start) / artifact.duration_seconds * 100)}%`, backgroundColor: STATE_COLORS[interval.state] }} className="h-full opacity-80 hover:opacity-100" />)}</div></div>}
      <div className="mt-4 grid gap-2 sm:grid-cols-4">{[["Eye contact", confidence.eye_contact],["Smile proxy", confidence.smile_naturalness],["Movement", confidence.movement_purposefulness],["Spatial use", confidence.spatial_use]].map(([label, value]) => <div key={label} className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3"><p className="text-[10px] uppercase tracking-wider text-zinc-600">{label}</p><p className="mt-1 text-xs font-medium text-zinc-300">{(value || "insufficient_data").replace("_", " ")}</p></div>)}</div>
      {[...(qualityGate?.limitations || []), ...(analysis?.warnings || [])].slice(0, 4).map((warning) => <p key={warning} className="mt-2 text-xs text-zinc-500">• {warning}</p>)}
    </section>
  );
}
