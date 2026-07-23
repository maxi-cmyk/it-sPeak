"use client";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

export default function SkillRadar({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%" minHeight={280}>
      <RadarChart data={data} outerRadius="80%" margin={{ top: 10, right: 32, bottom: 10, left: 32 }}>
        <PolarGrid stroke="var(--border-strong)" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: "var(--text-subtle)", fontSize: 12 }}
        />
        <Tooltip
          contentStyle={{ backgroundColor: "var(--surface)", border: "1px solid var(--border-strong)", borderRadius: 8 }}
          labelStyle={{ color: "var(--text-primary)" }}
          itemStyle={{ color: "#2563eb" }}
        />
        <Radar
          name="Score"
          dataKey="score"
          stroke="#2563eb"
          fill="#2563eb"
          fillOpacity={0.25}
          strokeWidth={2}
          dot={{ fill: "#2563eb", r: 3 }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
