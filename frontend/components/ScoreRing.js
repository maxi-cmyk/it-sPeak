export default function ScoreRing({ score, size = 130 }) {
  const numericScore = Number(score);
  const normalizedScore = Number.isFinite(numericScore) ? Math.min(100, Math.max(0, numericScore)) : 0;
  const strokeWidth = 10;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (normalizedScore / 100) * circumference;
  const cx = size / 2;
  const cy = size / 2;

  const color = normalizedScore >= 80 ? "var(--score-proficient)" : normalizedScore >= 60 ? "var(--score-developing)" : "var(--score-low)";

  return (
    <div className="flex flex-col items-center gap-1" role="img" aria-label={`Overall score ${normalizedScore.toFixed(1)} out of 100`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }} aria-hidden="true">
          <circle cx={cx} cy={cy} r={radius} fill="none" stroke="var(--border)" strokeWidth={strokeWidth} />
          <circle
            cx={cx} cy={cy} r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold tracking-tight" style={{ color }}>{normalizedScore.toFixed(1)}</span>
          <span className="text-xs text-zinc-400">/ 100</span>
        </div>
      </div>
    </div>
  );
}
