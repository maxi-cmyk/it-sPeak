"use client";
import { useRouter } from "next/navigation";
import SessionCard from "./SessionCard";

export default function AllSessionsModal({ sessions, projectId, onClose, onAddSession }) {
  const router = useRouter();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="sessions-dialog-title">
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal-panel flex max-h-[80vh] max-w-lg flex-col p-0">
        <div className="flex items-center justify-between p-6 border-b border-zinc-800">
          <div><p className="page-kicker mb-1">Rehearsal history</p><h2 id="sessions-dialog-title" className="text-lg font-semibold text-zinc-50">Retained sessions</h2></div>
          <button onClick={onClose} className="icon-button -mr-2" aria-label="Close retained sessions">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-4">
          {sessions.length === 0 ? (
            <p className="py-8 text-center text-sm leading-6 text-zinc-500">No successful sessions have been retained yet.</p>
          ) : (
            sessions.map((session, i) => (
              <SessionCard
                key={session.id}
                session={session}
                prev={sessions[i + 1]}
                onClick={() => {
                  onClose();
                  router.push(`/session/${session.id}`);
                }}
              />
            ))
          )}
        </div>

        <div className="p-6 border-t border-zinc-800">
          <button
            onClick={onAddSession}
            className="btn-primary w-full"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New session
          </button>
        </div>
      </div>
    </div>
  );
}
