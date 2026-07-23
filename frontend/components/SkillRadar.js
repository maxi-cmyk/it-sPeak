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
  const summary = (data || []).map((item) => `${item.subject} ${Math.round(item.score)} out of 100`).join(", ");
  return (
    <div role="img" aria-label={`Skill breakdown. ${summary}`}>
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data} outerRadius="64%" margin={{ top: 16, right: 56, bottom: 16, left: 56 }}>
          <PolarGrid stroke="var(--border-strong)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: "var(--text-subtle)", fontSize: 14 }}
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
    </div>
  );
}
