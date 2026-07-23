"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import ImprovementAreaIcon from "@/components/ImprovementAreaIcon";
import Navbar from "@/components/Navbar";
import RatingBar from "@/components/RatingBar";
import ScoreRing from "@/components/ScoreRing";
import VideoAnalysisPlayer from "@/components/VideoAnalysisPlayer";
import useApi from "@/hooks/useApi";
import { formatDate } from "@/lib/data";
import { splitMetricPhrases } from "@/lib/analysisPresentation.mjs";
import { improvementAreaLabels } from "@/lib/improvementAreas.mjs";
import { COACHING_THRESHOLD, reportToSession } from "@/lib/reportAdapter";

const SkillRadar = dynamic(() => import("@/components/SkillRadar"), { ssr: false });

function MetricText({ children }) {
  return splitMetricPhrases(children).map((part, index) => (
    part.metric
      ? <strong key={`${part.text}-${index}`} className="font-bold text-inherit">{part.text}</strong>
      : <span key={`${part.text}-${index}`}>{part.text}</span>
  ));
}

function stripPriorityPrefix(text) {
  if (typeof text !== "string") return text;
  const stripped = text.replace(/^priority\s*\d+\s*:\s*/i, "");
  return stripped === text ? text : stripped.charAt(0).toUpperCase() + stripped.slice(1);
}

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
      <div className="app-shell flex flex-col items-center justify-center gap-3 px-6 text-center text-zinc-400">
        {error
          ? <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
          : <span className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-700 border-t-blue-400" aria-hidden="true" />}
        <p className={error ? "text-red-700" : ""}>{error || "Loading your analysis…"}</p>
      </div>
    );
  }

  const projectHref = `/project/${session.projectId}`;
  const selectedNeedsWork = session.improvementGuidance.filter((item) => !item.proficient);
  const observedFeedback = session.observedFeedback || [];
  return (
    <div className="app-shell">
      <Navbar backHref={projectHref} />
      <main className="page-container">
        <header className="mb-8 flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="page-kicker">Combined analysis</p>
            <h1 className="page-title">{session.name}</h1>
            <p className="text-zinc-500 text-sm mt-3">{session.duration} &bull; {formatDate(session.date)}</p>
          </div>
          <div className="self-start sm:text-right">
            <p className="section-label mb-1">Overall score</p>
            <ScoreRing score={session.overallScore} size={110} />
          </div>
        </header>

        <VideoAnalysisPlayer sessionId={id} analysis={session.rawAnalysis} qualityGate={session.qualityGate} />

        <section className="mb-6 overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900">
          <div className="border-b border-zinc-800 px-6 py-4">
            <p className="page-kicker mb-1">Your selected focus</p>
            <p className="text-xs leading-5 text-zinc-500">Coaching threshold: {COACHING_THRESHOLD}/100. Scores of {COACHING_THRESHOLD} or above are proficient; scores below {COACHING_THRESHOLD} receive coaching.</p>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-zinc-800">
            <div className="bg-zinc-900 p-4">
              <p className="text-readiness mb-4 text-xs font-semibold uppercase tracking-wider">Needs improvement</p>
              <div className="flex flex-col gap-4">
                {selectedNeedsWork.length === 0 && <p className="text-sm text-zinc-500">No selected areas are below {COACHING_THRESHOLD}/100 right now.</p>}
                {selectedNeedsWork.map((item) => (
                  <details key={item.area} className="group">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 [&::-webkit-details-marker]:hidden">
                      <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">{improvementAreaLabels[item.area] || item.area}</span>
                      <span className={`text-lg font-semibold ${item.priority === 1 ? "text-readiness" : "text-zinc-200"}`}>{Math.round(item.score)}<span className="text-xs font-normal text-zinc-600">/100</span></span>
                    </summary>
                    <p className="mt-1 text-sm leading-6 text-zinc-300"><MetricText>{stripPriorityPrefix(item.message)}</MetricText></p>
                  </details>
                ))}
              </div>
            </div>
            <div className="bg-zinc-900 p-4">
              <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-emerald-700">Done well</p>
              <div className="flex flex-col gap-4">
                {session.improvementGuidance.filter((item) => item.proficient).length === 0 && <p className="text-sm text-zinc-500">No selected areas are at or above {COACHING_THRESHOLD}/100 yet.</p>}
                {session.improvementGuidance.filter((item) => item.proficient).map((item) => (
                  <details key={item.area} className="group">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 [&::-webkit-details-marker]:hidden">
                      <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">{improvementAreaLabels[item.area] || item.area}</span>
                      <span className="text-lg font-semibold text-emerald-700">{Math.round(item.score)}<span className="text-xs font-normal text-zinc-600">/100</span></span>
                    </summary>
                    <p className="mt-1 text-sm leading-6 text-emerald-700"><MetricText>{stripPriorityPrefix(item.message)}</MetricText></p>
                  </details>
                ))}
              </div>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <section className="surface-card">
            <h2 className="section-label mb-1">Coaching priorities</h2>
            <p className="mb-4 text-xs leading-5 text-zinc-500">Selected focuses stay primary. Other low-scoring areas are noted separately so you can decide whether to add them next.</p>
            <div className="flex flex-col gap-4">
              {selectedNeedsWork.length === 0 && <p className="text-sm leading-6 text-emerald-700">Your selected areas are at or above {COACHING_THRESHOLD}/100. Maintain them or add another improvement field to your project.</p>}
              {selectedNeedsWork.length > 0 && session.feedback.length === 0 && <p className="text-sm leading-6 text-zinc-500">Your selected areas needing work are detailed above. No additional coaching card was generated for this analysis.</p>}
              {session.feedback.map((item, index) => (
                <div key={`${item.text}-${index}`}>
                  <div className="flex items-center gap-3">
                    <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center text-zinc-200"><ImprovementAreaIcon area={item.module} /></span>
                    <p className="text-sm font-medium text-zinc-200"><MetricText>{item.text}</MetricText></p>
                  </div>
                  <p className="text-xs text-zinc-500 mt-0.5 pl-8">→ <MetricText>{item.tip}</MetricText></p>
                </div>
              ))}
              {observedFeedback.length > 0 && (
                <div className="border-t border-zinc-800 pt-4">
                  <h3 className="mb-1 text-sm font-semibold text-zinc-200">Other areas observed</h3>
                  <p className="mb-4 text-xs leading-5 text-zinc-500">These were not selected as project focuses, but they scored below {COACHING_THRESHOLD}/100.</p>
                  <div className="flex flex-col gap-4">
                    {observedFeedback.map((item) => (
                      <div key={item.area}>
                        <div className="flex items-center gap-3">
                          <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center text-zinc-200"><ImprovementAreaIcon area={item.module} /></span>
                          <p className="text-sm font-medium text-zinc-200"><MetricText>{item.text}</MetricText></p>
                        </div>
                        <p className="mt-0.5 pl-8 text-xs leading-5 text-zinc-500">→ <MetricText>{item.tip}</MetricText></p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>

          <section className="surface-card flex flex-col">
            <h2 className="section-label mb-4">Current rating</h2>
            <div className="flex flex-col gap-4">
              <RatingBar label="Tone" value={session.tone} target={session.targetTone} />
              <RatingBar label="Body" value={session.body} target={session.targetBody} />
              <RatingBar label="Facial expressions" value={session.face} target={session.targetFace} />
            </div>
            <div className="mt-6 flex flex-1 flex-col">
              <h3 className="section-label mb-4">Skill breakdown</h3>
              <div className="min-h-[280px] flex-1">
                <SkillRadar data={session.radarData} />
              </div>
            </div>
          </section>
        </div>

        {session.transcript && (
          <section className="surface-card mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="section-label">Transcript</h2>
              {!editingTranscript && (
                <button onClick={startEditingTranscript} aria-label="Edit transcript" className="icon-button -mr-2">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
                  </svg>
                </button>
              )}
            </div>
            {editingTranscript ? (
              <div className="flex flex-col gap-4">
                <textarea
                  rows={6}
                  value={transcriptDraft}
                  onChange={(e) => setTranscriptDraft(e.target.value)}
                  className="field-control resize-y leading-7"
                />
                <div className="flex gap-3">
                  <button onClick={cancelEditingTranscript} disabled={savingTranscript} className="btn-secondary">Cancel</button>
                  <button onClick={saveTranscript} disabled={savingTranscript || !transcriptDraft.trim()} className="btn-primary">{savingTranscript ? "Saving…" : "Save transcript"}</button>
                </div>
              </div>
            ) : (
              <p className="text-sm leading-7 text-zinc-300">{session.transcript}</p>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
