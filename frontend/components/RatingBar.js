export default function RatingBar({ label, value, target }) {
  const barColor = value >= (target || 80) ? "bg-emerald-500" : "bg-violet-500";
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-zinc-400">{label}</span>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-zinc-50">{value}</span>
          <span className="text-zinc-600 text-xs">/ 100</span>
          {target && <span className="text-zinc-600 text-[10px]">(target {target})</span>}
        </div>
      </div>
      <div className="relative h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${value}%` }}
        />
        {target && (
          <div
            className="absolute top-0 h-full w-0.5 bg-zinc-500"
            style={{ left: `${target}%` }}
          />
        )}
      </div>
    </div>
  );
}
