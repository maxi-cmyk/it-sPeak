export default function RatingBar({ label, value, target }) {
  const numericValue = Number(value);
  const normalizedValue = Number.isFinite(numericValue) ? Math.min(100, Math.max(0, numericValue)) : 0;
  const normalizedTarget = Number.isFinite(Number(target)) ? Math.min(100, Math.max(0, Number(target))) : null;
  const barColor = normalizedValue >= (normalizedTarget ?? 80) ? "bg-emerald-500" : normalizedValue < 60 ? "bg-red-500" : "bg-blue-600";
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-zinc-400">{label}</span>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-zinc-50">{Math.round(normalizedValue)}</span>
          <span className="text-xs text-zinc-400">/ 100</span>
          {normalizedTarget !== null && <span className="text-[10px] text-zinc-400">(target {Math.round(normalizedTarget)})</span>}
        </div>
      </div>
      <div className="relative h-2 overflow-hidden rounded-full bg-zinc-800" role="meter" aria-label={`${label} score`} aria-valuemin="0" aria-valuemax="100" aria-valuenow={normalizedValue} aria-valuetext={`${Math.round(normalizedValue)} out of 100`}>
        <div
          className={`h-full rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${normalizedValue}%` }}
        />
        {normalizedTarget !== null && (
          <div
            className="absolute top-0 h-full w-0.5 bg-zinc-300"
            style={{ left: `${normalizedTarget}%` }}
          />
        )}
      </div>
    </div>
  );
}
