import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import type { Assessment } from "@/lib/api";

const SCORE: Record<string, number> = { low: 1, medium: 2, high: 3 };

const SHORT: Record<string, string> = {
  "Fairness & Bias": "Fairness",
  Ethics: "Ethics",
  "Accountability & Governance": "Accountability",
  Transparency: "Transparency",
  "Legal & Regulatory": "Legal",
  "Robustness & Stability": "Robustness",
  "Cyber & Data Security": "Cyber",
};

export function DimensionRadar({ dimensions }: { dimensions: Assessment["risk_dimensions"] }) {
  const data = dimensions.map((d) => ({
    axis: SHORT[d.dimension] ?? d.dimension,
    score: SCORE[d.rating] ?? 0,
  }));

  return (
    <div
      className="h-64 w-full"
      role="img"
      aria-label="Risk ratings across the seven dimensions"
    >
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="var(--color-line)" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fill: "var(--color-ink-muted)", fontSize: 11 }}
          />
          <PolarRadiusAxis domain={[0, 3]} tickCount={4} tick={false} axisLine={false} />
          <Radar
            dataKey="score"
            stroke="var(--color-accent)"
            fill="var(--color-accent)"
            fillOpacity={0.16}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
