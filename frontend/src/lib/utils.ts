import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type Tier = "low" | "medium" | "high";

/** Tier colours carry semantic meaning only; every badge also carries its text. */
export const tierStyles: Record<Tier, string> = {
  low: "bg-low-soft text-low border-low-line",
  medium: "bg-medium-soft text-medium border-medium-line",
  high: "bg-high-soft text-high border-high-line",
};

export const tierBorder: Record<Tier, string> = {
  low: "border-l-low",
  medium: "border-l-medium",
  high: "border-l-high",
};

export const tierLabel: Record<Tier, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

export const oversightLabel: Record<string, string> = {
  human_in_the_loop: "Human in the loop",
  human_over_the_loop: "Human over the loop",
  human_out_of_the_loop: "Human out of the loop",
};

export const aiTypeLabel: Record<string, string> = {
  traditional: "Traditional AI",
  gen_ai: "Generative AI",
  agentic: "Agentic AI",
};

export function formatTokens(n: number): string {
  return n.toLocaleString("en-GB");
}
