"use client";
import { eligibleReplacementSessions } from "@/lib/persistenceUi.mjs";
import { analysisProgress } from "@/lib/analysisPresentation.mjs";

const STEP_LABELS = { uploading: "Uploading securely", quality_check: "Checking recording quality", queued: "Queued for analysis", processing: "Full analysis in progress", success: "Analysis complete", failure: "Analysis stopped", rejected: "New recording required", needs_confirmation: "Review before continuing" };

export default function ProcessingModal({ job, onComplete, onConfirm, onCancel, onReplace }) {
  const done = job.status === "success";
  const failed = ["failure", "rejected"].includes(job.status);
  const waiting = job.status === "needs_confirmation";
  const replacing = job.status === "replacement_required";
  const progress = analysisProgress(job);
  const showProgress = !replacing && !failed;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="analysis-title">
      <div className="modal-backdrop" />
      <div className="modal-panel max-w-lg">
        <p className="page-kicker">Recording analysis</p>
        <h2 id="analysis-title" className="text-lg font-semibold text-zinc-50">{replacing ? "Choose a rehearsal to replace" : done ? "Your results are ready" : failed ? "This recording cannot continue" : waiting ? "A quick quality decision" : "Preparing a reliable analysis…"}</h2>
        {replacing && <p className="mt-2 text-sm leading-6 text-zinc-400">This project already holds five rehearsals. Session 1 is your protected baseline; choose one of the later sessions below. Nothing is removed unless the new analysis succeeds.</p>}
        {replacing && <div className="my-6 space-y-2">{eligibleReplacementSessions(job.replacement?.candidates).map((session) => { const result = session.analysis_result || {}; return <button key={session.id} onClick={() => onReplace(session.id)} className="w-full rounded-xl border border-zinc-700 bg-zinc-950/70 p-4 text-left transition hover:border-amber-400/60 hover:bg-amber-400/5"><div className="flex items-center justify-between"><span className="font-medium text-zinc-100">Session {session.sequence_number}</span><span className="text-xs text-zinc-500">{new Date(session.completed_at || session.created_at).toLocaleDateString()}</span></div><div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-400"><span>Overall {Math.round(result.overall_score ?? 0)}</span><span>Voice {Math.round(result.vocal_score ?? 0)}</span><span>Facial expressions {Math.round(result.face_score ?? 0)}</span><span>Body {Math.round(result.body_score ?? 0)}</span></div></button>; })}</div>}
        {!replacing && <>
        <div className={`my-6 rounded-xl border p-4 ${failed ? "border-red-500/30 bg-red-500/10" : waiting ? "border-amber-500/30 bg-amber-500/10" : "border-zinc-800 bg-zinc-950/60"}`}>
          <div className="flex items-start gap-3">
            <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${done ? "bg-emerald-400" : failed ? "bg-red-400" : waiting ? "bg-amber-400" : "bg-blue-400 animate-pulse"}`} />
            <div><p className="text-sm font-medium text-zinc-100">{STEP_LABELS[job.status] || "Preparing analysis"}</p><p className={`mt-1 text-xs ${failed ? "text-red-700" : "text-zinc-400"}`}>{job.error || job.stage || "Connecting to the analysis service"}</p></div>
          </div>
        </div>
        {showProgress && (
          <div className="mb-6" aria-live="polite">
            <div className="mb-2 flex items-center justify-between gap-4 text-xs">
              <span className="font-medium text-zinc-300">Analysis progress</span>
              <span className="tabular-nums text-zinc-500">{progress.value}%</span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-zinc-800"
              role="progressbar"
              aria-label="Recording analysis progress"
              aria-valuemin="0"
              aria-valuemax="100"
              aria-valuenow={progress.value}
              aria-valuetext={`${progress.value}% — ${job.stage || STEP_LABELS[job.status] || "Preparing analysis"}`}
            >
              <div
                className={`h-full rounded-full transition-[width] duration-500 ${done ? "bg-emerald-600" : waiting ? "bg-amber-600" : "bg-blue-600"}`}
                style={{ width: `${progress.value}%` }}
              />
            </div>
          </div>
        )}
        {job.qualityGate?.issues?.length > 0 && (
          <div className="space-y-2 mb-6">
            {job.qualityGate.issues.map((issue) => (
              <div key={issue.code} className="rounded-lg border border-zinc-800 bg-zinc-950/70 p-3">
                <div className="flex justify-between gap-3"><p className="text-sm font-medium text-zinc-200">{issue.title}</p><span className="text-[10px] uppercase tracking-wider text-red-700">{issue.severity}</span></div>
                <p className="mt-1 text-xs text-zinc-500">{issue.message}</p><p className="mt-2 text-xs text-zinc-300">Try: {issue.action}</p>
              </div>
            ))}
          </div>
        )}
        {waiting && <p className="mb-6 text-xs leading-5 text-zinc-500">Continuing keeps these limitations attached to your results. Re-recording will produce more trustworthy feedback.</p>}
        <div className="flex gap-3">
          {done ? <button onClick={onComplete} className="btn-primary w-full">View results <span aria-hidden="true">→</span></button> : waiting ? <><button onClick={onCancel} className="btn-secondary flex-1">Re-record</button><button onClick={onConfirm} className="inline-flex min-h-10 flex-1 items-center justify-center rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-zinc-50 transition-colors hover:bg-amber-400">Continue anyway</button></> : failed ? <button onClick={onCancel} className="inline-flex min-h-10 w-full items-center justify-center rounded-lg border border-red-500/40 px-4 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-500/10">Close and re-record</button> : <button onClick={onCancel} className="btn-secondary w-full">Cancel analysis</button>}
        </div>
        </>}
        {replacing && <button onClick={onCancel} className="btn-secondary w-full">Keep all current sessions</button>}
      </div>
    </div>
  );
}
