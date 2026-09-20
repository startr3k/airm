import type { AssessResponse, Assessment } from "@/lib/api";

const DIMENSIONS = [
  "Fairness & Bias",
  "Ethics",
  "Accountability & Governance",
  "Transparency",
  "Legal & Regulatory",
  "Robustness & Stability",
  "Cyber & Data Security",
] as const;

export function makeAssessment(overrides: Partial<Assessment> = {}): Assessment {
  return {
    use_case_summary: "A model that scores personal loan applications.",
    ai_in_scope: true,
    ai_type: "traditional",
    materiality_factors: [
      {
        factor: "Options for recourse",
        rating: "high",
        rationale: "Declines are hard to appeal.",
      },
      { factor: "Reputational risk", rating: "medium", rationale: "Visible to customers." },
    ],
    inherent_risk_tier: "high",
    risk_dimensions: DIMENSIONS.map((dimension) => ({
      dimension,
      rating: dimension === "Fairness & Bias" ? ("high" as const) : ("medium" as const),
      key_risks:
        dimension === "Fairness & Bias" ? ["Unrepresentative or biased data inputs"] : [],
      rationale: `Why ${dimension} rates as it does.`,
    })),
    top_10_flags: ["Unrepresentative or biased data inputs"],
    recommended_oversight_mode: "human_in_the_loop",
    recommended_guardrails: [
      { guardrail: "Red teaming", handbook_ref: "Appendix G, p. 156", why: "Probe for bias." },
    ],
    recommended_metrics: ["Disparate Impact Ratio (DIR)"],
    agentic_considerations: null,
    relevant_considerations: [5, 7],
    confidence: "medium",
    assessor_notes: "The description does not say how declines are appealed.",
    ...overrides,
  };
}

export function makeResponse(overrides: Partial<AssessResponse> = {}): AssessResponse {
  return {
    assessment: makeAssessment(),
    policy_overrides: [],
    model: "claude-sonnet-5",
    usage: {
      input_tokens: 400,
      output_tokens: 2800,
      cache_creation_input_tokens: 0,
      cache_read_input_tokens: 9394,
    },
    latency_ms: 31900,
    assessment_id: "abc123abc123abc1",
    pack_version: 1,
    pdf_sha256: "c".repeat(64),
    ...overrides,
  };
}
