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
    <ResponsiveContainer width="100%" height={260}>
      <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
        <PolarGrid stroke="#3f3f46" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: "#a1a1aa", fontSize: 12 }}
        />
        <Tooltip
          contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", borderRadius: 8 }}
          labelStyle={{ color: "#fafafa" }}
          itemStyle={{ color: "#a78bfa" }}
        />
        <Radar
          name="Score"
          dataKey="score"
          stroke="#a78bfa"
          fill="#a78bfa"
          fillOpacity={0.25}
          strokeWidth={2}
          dot={{ fill: "#a78bfa", r: 3 }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
