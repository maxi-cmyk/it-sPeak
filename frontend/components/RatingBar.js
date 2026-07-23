export default function RatingBar({ label, value, target }) {
  const barColor = value >= (target || 80) ? "bg-emerald-500" : value < 60 ? "bg-red-500" : "bg-blue-600";
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-zinc-400">{label}</span>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-zinc-50">{value}</span>
          <span className="text-zinc-600 text-xs">/ 100</span>
        </div>
      </div>
      <div className="relative h-2 overflow-hidden rounded-full bg-zinc-800" role="meter" aria-label={`${label} score`} aria-valuemin="0" aria-valuemax="100" aria-valuenow={value}>
        <div
          className={`h-full rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${value}%` }}
        />
        {target && (
          <div
            className="absolute top-0 h-full w-0.5 bg-zinc-300"
            style={{ left: `${target}%` }}
          />
        )}
      </div>
    </div>
  );
}
