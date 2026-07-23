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

export default function SessionSummaryPage() {
  const { id } = useParams();
  const { authReady, getSessionAnalysis, updateTranscript } = useApi();
  const [session, setSession] = useState(null);
  const [error, setError] = useState(null);
  const [loadVersion, setLoadVersion] = useState(0);
  const [editingTranscript, setEditingTranscript] = useState(false);
  const [transcriptDraft, setTranscriptDraft] = useState("");
  const [savingTranscript, setSavingTranscript] = useState(false);
  const [transcriptError, setTranscriptError] = useState(null);

  const startEditingTranscript = () => { setTranscriptDraft(session.transcript); setTranscriptError(null); setEditingTranscript(true); };
  const cancelEditingTranscript = () => { setTranscriptError(null); setEditingTranscript(false); };
  const saveTranscript = async () => {
    setSavingTranscript(true);
    setTranscriptError(null);
    try { await updateTranscript(id, transcriptDraft); setSession((current) => ({ ...current, transcript: transcriptDraft })); setEditingTranscript(false); }
    catch (requestError) { setTranscriptError(requestError.message); }
    finally { setSavingTranscript(false); }
  };

  useEffect(() => {
    if (!authReady) return undefined;
    const controller = new AbortController();
    setError(null);
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
  }, [id, authReady, loadVersion]);

  if (!session) {
    return (
      <div className="app-shell">
        <Navbar backHref="/" />
        <main className="page-container flex min-h-[calc(100vh-4rem)] items-center justify-center py-10">
          <section className="surface-card w-full max-w-lg px-6 py-10 text-center" role={error ? "alert" : "status"} aria-live="polite">
            <span className={`mx-auto mb-5 block h-3 w-3 rounded-full ${error ? "bg-red-500" : "animate-pulse bg-blue-500"}`} aria-hidden="true" />
            <h1 className="text-lg font-semibold text-zinc-100">{error ? "Analysis could not be opened" : "Loading combined analysis"}</h1>
            <p className={`mx-auto mt-2 max-w-sm text-sm leading-6 ${error ? "text-red-700" : "text-zinc-400"}`}>{error || "Retrieving your scores, coaching, recording evidence, and transcript…"}</p>
            {error && <button type="button" onClick={() => setLoadVersion((current) => current + 1)} className="btn-primary mt-6">Try again</button>}
          </section>
        </main>
      </div>
    );
  }

  const projectHref = `/project/${session.projectId}`;
  const selectedNeedsWork = session.improvementGuidance.filter((item) => !item.proficient);
  const selectedProficient = session.improvementGuidance.filter((item) => item.proficient);
  const observedFeedback = session.observedFeedback || [];
  const showCoaching = selectedNeedsWork.length > 0 || observedFeedback.length > 0;
  return (
    <div className="app-shell">
      <Navbar backHref={projectHref} />
      <main className="page-container">
        <header className="mb-6 border-b border-zinc-800 pb-6">
          <p className="page-kicker">Combined analysis</p>
          <h1 className="page-title">{session.name}</h1>
          <p className="mt-1 text-sm text-zinc-400">{session.duration} <span aria-hidden="true">·</span> {formatDate(session.date)}</p>
        </header>

        <section className="surface-card mb-6" aria-labelledby="score-summary-heading">
          <div className="grid gap-6 lg:grid-cols-[11rem_1fr] lg:items-center">
            <div className="flex flex-col items-center border-b border-zinc-800 pb-6 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-6">
              <h2 id="score-summary-heading" className="section-label mb-3">Overall score</h2>
              <ScoreRing score={session.overallScore} size={124} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-100">Current rating</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">The coaching threshold is <strong className="font-semibold text-zinc-200">{COACHING_THRESHOLD}/100</strong>. Scores at or above it are proficient.</p>
              <div className="mt-5 grid gap-5 sm:grid-cols-3">
                <RatingBar label="Voice" value={session.tone} />
                <RatingBar label="Body" value={session.body} />
                <RatingBar label="Facial expressions" value={session.face} />
              </div>
            </div>
          </div>
        </section>

        <VideoAnalysisPlayer sessionId={id} analysis={session.rawAnalysis} qualityGate={session.qualityGate} />

        <section className="mb-6 overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900" aria-labelledby="selected-focus-heading">
          <div className="border-b border-zinc-800 px-5 py-4">
            <h2 id="selected-focus-heading" className="text-base font-semibold text-zinc-100">Your selected focus</h2>
            <p className="mt-1 text-sm leading-6 text-zinc-400">Areas below {COACHING_THRESHOLD}/100 are ranked lowest-score first. Proficient areas remain visible without generating coaching.</p>
          </div>
          <div className="grid grid-cols-1 gap-px bg-zinc-800 lg:grid-cols-2">
            <div className="bg-zinc-900 p-5">
              <h3 className="text-readiness mb-3 text-sm font-semibold">Needs improvement</h3>
              <div className="divide-y divide-zinc-800">
                {selectedNeedsWork.length === 0 && <p className="py-2 text-sm text-emerald-700">No selected areas are below {COACHING_THRESHOLD}/100 right now.</p>}
                {selectedNeedsWork.map((item, index) => (
                  <div key={item.area} className={index === 0 ? "pb-4" : "py-4"}>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-semibold text-zinc-300">Priority {item.priority} <span className="text-zinc-500" aria-hidden="true">·</span> {improvementAreaLabels[item.area] || item.area}</span>
                      <span className={`text-lg font-semibold ${item.priority === 1 ? "text-readiness" : "text-zinc-200"}`}>{Math.round(item.score)}<span className="text-xs font-normal text-zinc-400">/100</span></span>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-zinc-300"><MetricText>{item.message}</MetricText></p>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-zinc-900 p-5">
              <h3 className="mb-3 text-sm font-semibold text-emerald-700">Done well</h3>
              <div className="divide-y divide-zinc-800">
                {selectedProficient.length === 0 && <p className="py-2 text-sm text-zinc-400">No selected areas are at or above {COACHING_THRESHOLD}/100 yet.</p>}
                {selectedProficient.map((item, index) => (
                  <div key={item.area} className={index === 0 ? "pb-4" : "py-4"}>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-semibold text-zinc-300">{improvementAreaLabels[item.area] || item.area}</span>
                      <span className="text-lg font-semibold text-emerald-700">{Math.round(item.score)}<span className="text-xs font-normal text-zinc-400">/100</span></span>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-zinc-300"><MetricText>{item.message}</MetricText></p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {showCoaching && <section className="surface-card mb-6" aria-labelledby="coaching-priorities-heading">
            <h2 id="coaching-priorities-heading" className="text-base font-semibold text-zinc-100">Coaching priorities</h2>
            <p className="mb-5 mt-1 text-sm leading-6 text-zinc-400">Selected focuses stay primary. Other low-scoring areas are noted separately so you can decide whether to add them next.</p>
            <div className="flex flex-col gap-4">
              {selectedNeedsWork.length > 0 && session.feedback.length === 0 && <p className="text-sm leading-6 text-zinc-400">Your selected areas needing work are detailed above. No additional coaching card was generated for this analysis.</p>}
              {session.feedback.map((item, index) => (
                <div key={`${item.text}-${index}`} className="flex gap-3">
                  <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-blue-400" aria-hidden="true" />
                  <div>
                    <p className="text-sm font-medium text-zinc-200"><MetricText>{item.text}</MetricText></p>
                    <p className="mt-1 text-sm leading-6 text-zinc-400"><span aria-hidden="true">→</span> <MetricText>{item.tip}</MetricText></p>
                  </div>
                </div>
              ))}
              {observedFeedback.length > 0 && (
                <div className="border-t border-zinc-800 pt-4">
                  <h3 className="mb-1 text-sm font-semibold text-zinc-200">Other areas observed</h3>
                  <p className="mb-4 text-sm leading-6 text-zinc-400">These were not selected as project focuses, but they scored below {COACHING_THRESHOLD}/100.</p>
                  <div className="flex flex-col gap-4">
                    {observedFeedback.map((item) => (
                      <div key={item.area} className="flex gap-3">
                        <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-zinc-600" aria-hidden="true" />
                        <div>
                          <p className="text-sm font-medium text-zinc-200"><MetricText>{item.text}</MetricText></p>
                          <p className="mt-1 text-sm leading-6 text-zinc-400"><span aria-hidden="true">→</span> <MetricText>{item.tip}</MetricText></p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>}

        <section className="surface-card mb-6">
          <h2 className="text-base font-semibold text-zinc-100">Skill breakdown</h2>
          <p className="mt-1 text-sm leading-6 text-zinc-400">A combined view of the scored voice and visual delivery metrics available for this session.</p>
          <div className="mt-3"><SkillRadar data={session.radarData} /></div>
        </section>

        {session.transcript && (
          <section className="surface-card mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-zinc-100">Transcript</h2>
              {!editingTranscript && (
                <button onClick={startEditingTranscript} aria-label="Edit transcript" className="icon-button -mr-2">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
                  </svg>
                </button>
              )}
            </div>
            {editingTranscript ? (
              <div className="flex flex-col gap-3">
                {transcriptError && <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-sm text-red-700">Transcript could not be saved. {transcriptError}</div>}
                <label htmlFor="session-transcript" className="sr-only">Session transcript</label>
                <textarea
                  id="session-transcript"
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
