"use client";
import { useRouter } from "next/navigation";
import SessionCard from "./SessionCard";

export default function AllSessionsModal({ sessions, projectId, onClose, onAddSession }) {
  const router = useRouter();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg shadow-2xl flex flex-col max-h-[80vh]">
        <div className="flex items-center justify-between p-5 border-b border-zinc-800">
          <h2 className="text-lg font-semibold text-zinc-50">All Sessions</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 transition-colors">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-3">
          {sessions.length === 0 ? (
            <p className="text-zinc-500 text-sm text-center py-8">No sessions yet. Add your first one!</p>
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

        <div className="p-5 border-t border-zinc-800">
          <button
            onClick={onAddSession}
            className="w-full py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium text-sm transition-colors flex items-center justify-center gap-2"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Add Session
          </button>
        </div>
      </div>
    </div>
  );
}
