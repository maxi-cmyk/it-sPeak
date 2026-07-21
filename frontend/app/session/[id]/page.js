"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import RatingBar from "@/components/RatingBar";
import ScoreRing from "@/components/ScoreRing";
import VideoAnalysisPlayer from "@/components/VideoAnalysisPlayer";
import useApi from "@/hooks/useApi";
import { formatDate } from "@/lib/data";
import { reportToSession } from "@/lib/reportAdapter";

const SkillRadar = dynamic(() => import("@/components/SkillRadar"), { ssr: false });

export default function SessionSummaryPage() {
  const { id } = useParams();
  const { authReady, getSessionAnalysis, updateTranscript } = useApi();
  const [session, setSession] = useState(null);
  const [error, setError] = useState(null);
  const [editingTranscript, setEditingTranscript] = useState(false);
  const [transcriptDraft, setTranscriptDraft] = useState("");
  const [savingTranscript, setSavingTranscript] = useState(false);

  const startEditingTranscript = () => { setTranscriptDraft(session.transcript); setEditingTranscript(true); };
  const cancelEditingTranscript = () => setEditingTranscript(false);
  const saveTranscript = async () => {
    setSavingTranscript(true);
    try { await updateTranscript(id, transcriptDraft); setSession((current) => ({ ...current, transcript: transcriptDraft })); setEditingTranscript(false); }
    catch (requestError) { setError(requestError.message); }
    finally { setSavingTranscript(false); }
  };

  useEffect(() => {
    if (!authReady) return undefined;
    const controller = new AbortController();
    getSessionAnalysis(id, controller.signal)
      .then((payload) => {
        if (payload.status !== "success" || !payload.result) {
          throw new Error("This analysis is not ready yet.");
        }
        const view = reportToSession(payload.result, id, payload.project_id, payload.quality_gate);
        setSession({ ...view, name: payload.sequence_number ? `Session ${payload.sequence_number}` : view.name, score: payload.aggregates?.overall_score ?? view.score, overallScore: payload.aggregates?.overall_score ?? view.overallScore, tone: payload.aggregates?.vocal_score ?? view.tone, face: payload.aggregates?.face_score ?? view.face, body: payload.aggregates?.body_score ?? view.body });
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      });
    return () => controller.abort();
  }, [id, authReady]);

  if (!session) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center gap-3 text-zinc-400">
        <span className={`h-2.5 w-2.5 rounded-full ${error ? "bg-red-400" : "bg-violet-400 animate-pulse"}`} />
        <p>{error || "Loading your analysis…"}</p>
      </div>
    );
  }

  const projectHref = `/project/${session.projectId}`;
  return (
    <div className="min-h-screen bg-zinc-950">
      <Navbar backHref={projectHref} />
      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-start justify-between mb-8">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.22em] text-violet-400 mb-2">Combined analysis</p>
            <h1 className="text-2xl font-bold text-zinc-50">{session.name}</h1>
            <p className="text-zinc-500 text-sm mt-1">{session.duration} &bull; {formatDate(session.date)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-zinc-500 mb-1">Overall Score</p>
            <ScoreRing score={session.overallScore} size={110} />
          </div>
        </div>

        <VideoAnalysisPlayer sessionId={id} analysis={session.rawAnalysis} qualityGate={session.qualityGate} />

        <section className="mb-6 overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900">
          <div className="border-b border-zinc-800 px-5 py-4">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-violet-400">Your selected focus</p>
            <h2 className="mt-1 text-base font-semibold text-zinc-100">Lowest score leads the next rehearsal</h2>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-zinc-800">
            <div className="bg-zinc-900 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-amber-300">Needs improvement</p>
              <div className="flex flex-col gap-4">
                {session.improvementGuidance.filter((item) => !item.proficient).length === 0 && <p className="text-sm text-zinc-500">Nothing below the coaching threshold right now.</p>}
                {session.improvementGuidance.filter((item) => !item.proficient).map((item) => (
                  <div key={item.area}>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">Priority {item.priority}</span>
                      <span className={`text-lg font-semibold ${item.priority === 1 ? "text-amber-300" : "text-zinc-200"}`}>{Math.round(item.score)}</span>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-zinc-300">{item.message}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-zinc-900 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-emerald-400">Done well</p>
              <div className="flex flex-col gap-4">
                {session.improvementGuidance.filter((item) => item.proficient).length === 0 && <p className="text-sm text-zinc-500">No areas above the coaching threshold yet.</p>}
                {session.improvementGuidance.filter((item) => item.proficient).map((item) => (
                  <div key={item.area}>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">Priority {item.priority}</span>
                      <span className="text-lg font-semibold text-emerald-400">{Math.round(item.score)}</span>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-emerald-200">{item.message}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Coaching priorities</h2>
            <div className="flex flex-col gap-4">
              {session.feedback.length === 0 && <p className="text-sm leading-6 text-emerald-300">Your selected areas are above the coaching threshold. Maintain them or add another improvement field to your project.</p>}
              {session.feedback.map((item, index) => (
                <div key={`${item.text}-${index}`} className="flex gap-3">
                  <span className="text-lg flex-shrink-0 mt-0.5">{item.icon}</span>
                  <div>
                    <p className="text-sm font-medium text-zinc-200">{item.text}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">→ {item.tip}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Current rating vs target</h2>
            <div className="flex flex-col gap-4">
              <RatingBar label="Tone" value={session.tone} target={session.targetTone} />
              <RatingBar label="Body" value={session.body} target={session.targetBody} />
              <RatingBar label="Face" value={session.face} target={session.targetFace} />
            </div>
          </section>
        </div>

        {session.audioMetrics && (
          <section className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
            {Object.entries(session.audioMetrics).map(([key, metric]) => (
              <div key={key} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
                <p className="text-xs uppercase tracking-wider text-zinc-500">{key}</p>
                <p className="mt-2 text-xl font-semibold text-zinc-100">{metric.value}</p>
                <p className="mt-1 text-xs text-zinc-500">{metric.label} · score {Math.round(metric.score)}</p>
              </div>
            ))}
          </section>
        )}

        {session.transcript && (
          <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Transcript</h2>
              {!editingTranscript && (
                <button onClick={startEditingTranscript} aria-label="Edit transcript" className="text-zinc-500 hover:text-violet-300 transition-colors">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
                  </svg>
                </button>
              )}
            </div>
            {editingTranscript ? (
              <div className="flex flex-col gap-3">
                <textarea
                  rows={6}
                  value={transcriptDraft}
                  onChange={(e) => setTranscriptDraft(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm leading-7 text-zinc-100 focus:outline-none focus:border-violet-500 transition-colors resize-y"
                />
                <div className="flex gap-3">
                  <button onClick={cancelEditingTranscript} disabled={savingTranscript} className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 transition-colors disabled:opacity-50">Cancel</button>
                  <button onClick={saveTranscript} disabled={savingTranscript || !transcriptDraft.trim()} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 transition-colors disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-500">{savingTranscript ? "Saving…" : "Save"}</button>
                </div>
              </div>
            ) : (
              <p className="text-sm leading-7 text-zinc-300">{session.transcript}</p>
            )}
          </section>
        )}

        <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Skill breakdown</h2>
          <SkillRadar data={session.radarData} />
        </section>
      </main>
    </div>
  );
}
