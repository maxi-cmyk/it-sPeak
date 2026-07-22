"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const LINES = [
  { key: "Facial expressions", color: "#2563eb" },
  { key: "Tone", color: "var(--chart-tone)" },
  { key: "Body", color: "var(--chart-body)" },
];

export default function TimelineChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="session" tick={{ fill: "var(--text-subtle)", fontSize: 12 }} />
        <YAxis domain={[0, 100]} tick={{ fill: "var(--text-subtle)", fontSize: 12 }} />
        <Tooltip
          contentStyle={{ backgroundColor: "var(--surface)", border: "1px solid var(--border-strong)", borderRadius: 8 }}
          labelStyle={{ color: "var(--text-primary)" }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
          formatter={(value) => <span style={{ color: "var(--text-subtle)" }}>{value}</span>}
        />
        {LINES.map(({ key, color }) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={color}
            strokeWidth={2}
            dot={{ fill: color, r: 4 }}
            activeDot={{ r: 6 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
