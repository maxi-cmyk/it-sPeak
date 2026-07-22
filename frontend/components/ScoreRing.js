export default function ScoreRing({ score, size = 130 }) {
  const strokeWidth = 10;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(score, 100) / 100) * circumference;
  const cx = size / 2;
  const cy = size / 2;

  const color = score >= 80 ? "var(--score-proficient)" : score >= 60 ? "var(--score-developing)" : "var(--score-low)";

  return (
    <div className="flex flex-col items-center gap-1" role="img" aria-label={`Overall score ${Number(score).toFixed(1)} out of 100`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
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
          <span className="text-3xl font-bold tracking-tight" style={{ color }}>{Number(score).toFixed(1)}</span>
          <span className="text-xs text-zinc-500">/ 100</span>
        </div>
      </div>
    </div>
  );
}
