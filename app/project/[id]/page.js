"use client";
import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Navbar from "@/components/Navbar";
import ScoreRing from "@/components/ScoreRing";
import RatingBar from "@/components/RatingBar";
import SessionCard from "@/components/SessionCard";
import AllSessionsModal from "@/components/AllSessionsModal";
import AddSessionModal from "@/components/AddSessionModal";
import ProcessingModal from "@/components/ProcessingModal";
import {
  initialProjects,
  getSessionsForProject,
  getDaysUntilDeadline,
  formatDate,
} from "@/lib/data";

export default function ProjectPage() {
  const { id } = useParams();
  const router = useRouter();
  const [modal, setModal] = useState(null); // null | "allSessions" | "addSession" | "processing"

  const project = initialProjects.find((p) => p.id === id);
  const sessions = getSessionsForProject(id);
  const latest = sessions[0] || null;
  const days = project ? getDaysUntilDeadline(project.deadline) : 0;
  const recentSessions = sessions.slice(0, 3);

  if (!project) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center text-zinc-500">
        Project not found.
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950">
      <Navbar backHref="/" />
      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 flex flex-col gap-6">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-bold text-zinc-50">{project.name}</h1>
              </div>
              <p className="text-zinc-400 text-sm leading-relaxed">{project.description}</p>
            </div>

            <div className="flex items-center gap-2">
              <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border ${
                days <= 14 ? "bg-amber-500/10 border-amber-500/30 text-amber-400" : "bg-zinc-800 border-zinc-700 text-zinc-400"
              }`}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                {days > 0 ? `${days} days till deadline` : "Deadline passed"} — {formatDate(project.deadline)}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-semibold text-zinc-200">Sessions</h2>
                <button
                  onClick={() => setModal("allSessions")}
                  className="text-xs text-violet-400 hover:text-violet-300 border border-violet-500/30 hover:border-violet-500/60 px-3 py-1.5 rounded-lg transition-colors"
                >
                  + All Sessions
                </button>
              </div>

              {sessions.length === 0 ? (
                <div className="bg-zinc-900 border border-zinc-800 border-dashed rounded-xl p-8 text-center">
                  <p className="text-zinc-500 text-sm mb-3">No sessions recorded yet</p>
                  <button
                    onClick={() => setModal("addSession")}
                    className="text-violet-400 hover:text-violet-300 text-sm transition-colors"
                  >
                    Start your first session →
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {recentSessions.map((session, i) => (
                    <SessionCard
                      key={session.id}
                      session={session}
                      prev={recentSessions[i + 1]}
                      onClick={() => router.push(`/session/${session.id}`)}
                    />
                  ))}
                  {sessions.length > 3 && (
                    <button
                      onClick={() => setModal("allSessions")}
                      className="text-xs text-zinc-500 hover:text-zinc-300 text-center py-2 transition-colors"
                    >
                      View all {sessions.length} sessions →
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-5">
            {latest ? (
              <>
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
                  <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-4">Current Rating</h3>
                  <div className="flex justify-center mb-4">
                    <ScoreRing score={latest.overallScore} />
                  </div>
                  <div className="flex flex-col gap-3">
                    <RatingBar label="Tone" value={latest.tone} target={latest.targetTone} />
                    <RatingBar label="Body" value={latest.body} target={latest.targetBody} />
                    <RatingBar label="Face" value={latest.face} target={latest.targetFace} />
                  </div>
                </div>

                <div className={`rounded-xl p-4 border text-sm font-medium text-center ${
                  latest.overallScore >= 80
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                    : "bg-red-500/10 border-red-500/30 text-red-400"
                }`}>
                  Verdict: {latest.verdict}
                </div>

                <button
                  onClick={() => setModal("addSession")}
                  className="w-full py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium text-sm transition-colors flex items-center justify-center gap-2"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                  New Session
                </button>
              </>
            ) : (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 text-center">
                <p className="text-zinc-500 text-sm mb-4">No data yet. Add a session to see your rating.</p>
                <button
                  onClick={() => setModal("addSession")}
                  className="w-full py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium text-sm transition-colors"
                >
                  + Add Session
                </button>
              </div>
            )}
          </div>
        </div>
      </main>

      {modal === "allSessions" && (
        <AllSessionsModal
          sessions={sessions}
          projectId={id}
          onClose={() => setModal(null)}
          onAddSession={() => setModal("addSession")}
        />
      )}
      {modal === "addSession" && (
        <AddSessionModal
          onClose={() => setModal(null)}
          onConfirm={() => setModal("processing")}
        />
      )}
      {modal === "processing" && (
        <ProcessingModal
          onComplete={() => router.push("/session/s2")}
          onCancel={() => setModal(null)}
        />
      )}
    </div>
  );
}
