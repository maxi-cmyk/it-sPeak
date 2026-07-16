import { formatDate } from "@/lib/data";

export default function SessionCard({ session, onClick, prev }) {
  const improved = prev ? session.score > prev.score : null;

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 hover:border-zinc-600 rounded-xl p-4 transition-all group"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-center w-12">
            <span className="text-2xl font-bold text-violet-400">{session.score}</span>
            {improved !== null && (
              <span className={`text-xs font-medium ${improved ? "text-emerald-400" : "text-red-400"}`}>
                {improved ? "▲" : "▼"}
              </span>
            )}
          </div>
          <div>
            <p className="font-medium text-zinc-100 text-sm group-hover:text-violet-400 transition-colors">
              {session.name}
            </p>
            <div className="flex items-center gap-3 mt-1 text-xs text-zinc-500">
              <span>Tone: <span className="text-zinc-300">{session.tone}</span></span>
              <span>Body: <span className="text-zinc-300">{session.body}</span></span>
              <span>Face: <span className="text-zinc-300">{session.face}</span></span>
            </div>
          </div>
        </div>
        <span className="text-xs text-zinc-500 flex-shrink-0">{formatDate(session.date)}</span>
      </div>
    </button>
  );
}
