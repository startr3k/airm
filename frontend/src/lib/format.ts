/** Formatting and scoring helpers shared by the eval views. */

export function pct(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export type Tone = "low" | "medium" | "high" | "none";

/** Green above 90, amber 70-90, red below. Never the only signal: the number is there. */
export function scoreTone(value: number | null): Tone {
  if (value === null) return "none";
  if (value >= 0.9) return "low";
  if (value >= 0.7) return "medium";
  return "high";
}
