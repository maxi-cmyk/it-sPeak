import { formatDate } from "@/lib/data";

export default function SessionCard({ session, onClick, prev }) {
  const improved = prev ? session.score > prev.score : null;

  return (
    <button
      onClick={onClick}
      className="group w-full rounded-xl border border-zinc-700 bg-zinc-800 p-4 text-left transition-[border-color,background-color] duration-150 hover:border-zinc-600 hover:bg-zinc-700"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-center w-12">
            <span className={`text-2xl font-bold ${session.score >= 80 ? "text-emerald-700" : session.score >= 60 ? "text-accent" : "text-red-700"}`}>{session.score}</span>
            {improved !== null && (
              <span className={`text-xs font-medium ${improved ? "text-emerald-700" : "text-red-700"}`}>
                {improved ? "Improved" : "Lower"}
              </span>
            )}
          </div>
          <div>
            <p className="group-hover-accent text-sm font-medium text-zinc-100 transition-colors">
              {session.name}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-500">
              <span>Tone: <span className="text-zinc-300">{session.tone}</span></span>
              <span>Body: <span className="text-zinc-300">{session.body}</span></span>
              <span>Facial expressions: <span className="text-zinc-300">{session.face}</span></span>
            </div>
          </div>
        </div>
        <span className="text-xs text-zinc-500 flex-shrink-0">{formatDate(session.date)}</span>
      </div>
    </button>
  );
}
