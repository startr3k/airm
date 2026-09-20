import { z } from "zod";

/** Hand-written to mirror the backend's pydantic models. A schema change on either
 *  side shows up here as a parse failure rather than as undefined at render time. */

export const tierSchema = z.enum(["low", "medium", "high"]);
export const aiTypeSchema = z.enum(["traditional", "gen_ai", "agentic"]);
export const oversightSchema = z.enum([
  "human_in_the_loop",
  "human_over_the_loop",
  "human_out_of_the_loop",
]);
export const dimensionSchema = z.enum([
  "Fairness & Bias",
  "Ethics",
  "Accountability & Governance",
  "Transparency",
  "Legal & Regulatory",
  "Robustness & Stability",
  "Cyber & Data Security",
]);

export const assessmentSchema = z.object({
  use_case_summary: z.string(),
  ai_in_scope: z.boolean(),
  ai_type: aiTypeSchema,
  materiality_factors: z.array(
    z.object({ factor: z.string(), rating: tierSchema, rationale: z.string() }),
  ),
  inherent_risk_tier: tierSchema,
  risk_dimensions: z.array(
    z.object({
      dimension: dimensionSchema,
      rating: tierSchema,
      key_risks: z.array(z.string()),
      rationale: z.string(),
    }),
  ),
  top_10_flags: z.array(z.string()),
  recommended_oversight_mode: oversightSchema,
  recommended_guardrails: z.array(
    z.object({ guardrail: z.string(), handbook_ref: z.string(), why: z.string() }),
  ),
  recommended_metrics: z.array(z.string()),
  agentic_considerations: z
    .object({
      tool_access_risk: z.string(),
      least_privilege_recommendations: z.array(z.string()),
      interruption_controls: z.array(z.string()),
      never_delegate_flags: z.array(z.string()),
    })
    .nullable(),
  relevant_considerations: z.array(z.number()),
  confidence: tierSchema,
  assessor_notes: z.string(),
});

export const policyOverrideSchema = z.object({
  rule: z.string(),
  field: z.string(),
  before: z.unknown(),
  after: z.unknown(),
  reason: z.string(),
});

export const usageSchema = z.object({
  input_tokens: z.number(),
  output_tokens: z.number(),
  cache_creation_input_tokens: z.number(),
  cache_read_input_tokens: z.number(),
});

export const assessResponseSchema = z.object({
  assessment: assessmentSchema,
  policy_overrides: z.array(policyOverrideSchema),
  model: z.string(),
  usage: usageSchema,
  latency_ms: z.number(),
  assessment_id: z.string(),
  pack_version: z.number(),
  pdf_sha256: z.string(),
});

export const healthSchema = z.object({
  ok: z.boolean(),
  api_key_present: z.boolean(),
  pack_loaded: z.boolean(),
  pack_version: z.number().nullable(),
  pdf_sha256: z.string().nullable(),
  assess_model: z.string(),
  detail: z.string().nullable(),
});

export const historyRowSchema = z.object({
  id: z.string(),
  created_at: z.string(),
  summary: z.string(),
  ai_in_scope: z.boolean(),
  ai_type: aiTypeSchema,
  inherent_risk_tier: tierSchema,
  oversight_mode: oversightSchema,
  confidence: tierSchema,
  override_count: z.number(),
  model: z.string(),
  latency_ms: z.number(),
});

/* ---------------------------------------------------------------- framework */

/** The pack is large and mostly prose; only the fields the UI renders are declared,
 *  and `looseObject` keeps the rest rather than stripping it. */
const packSourceSchema = z.object({
  page: z.number().nullable().optional(),
  section: z.string().nullable().optional(),
  quote: z.string().nullable().optional(),
});

const citableSchema = z.looseObject({
  item_id: z.string(),
  source: packSourceSchema.optional(),
});

export const frameworkSchema = z.object({
  pack_version: z.number(),
  dimensions: z.array(
    citableSchema.extend({
      dimension: z.string(),
      definition: z.string().nullable().optional(),
      risks: z.array(
        z.looseObject({
          name: z.string(),
          description: z.string().nullable().optional(),
          is_abs_top_10: z.boolean().nullable().optional(),
        }),
      ),
    }),
  ),
  materiality: z.looseObject({
    factors: z.array(
      citableSchema.extend({
        factor: z.string(),
        description: z.string().nullable().optional(),
        low_guidance: z.string().nullable().optional(),
        medium_guidance: z.string().nullable().optional(),
        high_guidance: z.string().nullable().optional(),
      }),
    ),
    matrix: z.looseObject({}).optional(),
  }),
  oversight_modes: z.array(
    citableSchema.extend({
      mode: z.string(),
      printed_name: z.string().nullable().optional(),
      definition: z.string().nullable().optional(),
      when_appropriate: z.string().nullable().optional(),
    }),
  ),
  metrics: z.array(
    citableSchema.extend({
      name: z.string(),
      definition: z.string().nullable().optional(),
      dimension: z.string().nullable().optional(),
      ai_types: z.array(z.string()).nullable().optional(),
    }),
  ),
  guardrails: z.array(
    citableSchema.extend({
      name: z.string(),
      description: z.string().nullable().optional(),
      dimension: z.string().nullable().optional(),
      ai_types: z.array(z.string()).nullable().optional(),
    }),
  ),
  considerations: z.array(
    citableSchema.extend({
      number: z.number(),
      title: z.string(),
      handbook_section: z.string().nullable().optional(),
      implementation_practices: z.array(z.looseObject({})).nullable().optional(),
    }),
  ),
  illustrations: z.array(
    citableSchema.extend({
      label: z.string(),
      institution: z.string(),
      title: z.string().nullable().optional(),
      summary: z.string().nullable().optional(),
    }),
  ),
  definitions: z.looseObject({}),
});

export const provenanceSchema = z.looseObject({
  pdf_sha256: z.string(),
  model: z.string().nullable().optional(),
  extracted_at: z.string().nullable().optional(),
  page_map_version: z.number().nullable().optional(),
  printed_to_pdf_offset: z.number().nullable().optional(),
  verification: z.looseObject({
    quotes_checked: z.number(),
    quotes_failed: z.number(),
    extractors_passed: z.number(),
    extractors_total: z.number(),
  }),
});

export type Framework = z.infer<typeof frameworkSchema>;
export type Provenance = z.infer<typeof provenanceSchema>;

/* ---------------------------------------------------------------- citations */

export const sourceSchema = z.object({
  item_id: z.string(),
  kind: z.string(),
  label: z.string(),
  /** Always the number printed on the page, never the PDF's index. */
  page: z.number().nullable(),
  pdf_page: z.number().nullable(),
  section: z.string().nullable(),
  quote: z.string().nullable(),
  image_url: z.string().nullable(),
});

export type Source = z.infer<typeof sourceSchema>;

/* ------------------------------------------------------------------- evals */

const recallSchema = z.object({
  matched: z.number(),
  expected: z.number(),
  recall: z.number(),
});

export const evalSummarySchema = z.object({
  runs: z.number(),
  runs_ok: z.number(),
  runs_errored: z.number(),
  retries: z.number(),
  overall_accuracy: z.number().nullable(),
  checks_graded: z.number(),
  field_accuracy: z.record(
    z.string(),
    z.object({ passed: z.number(), graded: z.number(), accuracy: z.number() }),
  ),
  recall: z.record(z.string(), recallSchema),
  tier_consistency: z.object({
    mean_modal_agreement: z.number().nullable(),
    unanimous_cases: z.number(),
    cases: z.record(
      z.string(),
      z.object({
        tiers: z.array(z.string()),
        modal_agreement: z.number(),
        unanimous: z.boolean(),
      }),
    ),
  }),
  tier_confusion: z.record(z.string(), z.record(z.string(), z.number())),
  latency_ms: z.object({
    mean: z.number(),
    p50: z.number(),
    p95: z.number(),
    min: z.number(),
    max: z.number(),
  }),
  cost_usd: z.object({ total: z.number(), per_assessment: z.number() }),
  tokens: z.object({
    input: z.number(),
    output: z.number(),
    cache_read: z.number(),
    cache_hit_rate: z.number().nullable(),
  }),
  per_case: z.array(
    z.object({
      case_id: z.string(),
      title: z.string(),
      tests: z.string(),
      runs: z.number(),
      errors: z.number(),
      checks_passed: z.number(),
      checks_graded: z.number(),
      pass_rate: z.number().nullable(),
      expected_tier: tierSchema.nullable(),
      tiers: z.array(tierSchema),
      model_tiers: z.array(tierSchema),
      failed_fields: z.record(z.string(), z.number()),
      missing: z.array(z.string()),
    }),
  ),
  errors: z.array(
    z.object({
      case_id: z.string(),
      run: z.number(),
      kind: z.string().nullable().optional(),
      error: z.string().nullable(),
    }),
  ),
  errors_by_kind: z.record(z.string(), z.number()).optional(),
});

export const evalResultSchema = z.object({
  run_id: z.string(),
  model: z.string(),
  effort: z.string(),
  n: z.number(),
  cases: z.number(),
  started_at: z.string(),
  duration_s: z.number(),
  pack_version: z.number(),
  pdf_sha256: z.string(),
  prompt_sha256: z.string().nullable(),
  tool_sha256: z.string().optional(),
  gold_sha256: z.string(),
  summary: evalSummarySchema,
});

export const goldCaseSchema = z.object({
  id: z.string(),
  title: z.string(),
  tests: z.string(),
  description: z.string(),
  expect: z.object({
    ai_in_scope: z.boolean().nullable(),
    ai_type: aiTypeSchema.nullable(),
    tier: tierSchema.nullable(),
    tier_accepted: z.array(tierSchema),
    oversight_modes: z.array(oversightSchema),
  }),
});

export const evalsLatestSchema = z.object({
  models: z.array(evalResultSchema),
  gold: z.array(goldCaseSchema),
  gold_problems: z.array(z.string()),
  comparison_markdown: z.string().nullable(),
});

export const evalStatusSchema = z.object({
  state: z.enum(["idle", "running", "done", "error"]),
  model: z.string().nullable(),
  n: z.number(),
  total: z.number(),
  completed: z.number(),
  errors: z.number(),
  retries: z.number(),
  started_at: z.string().nullable(),
  finished_at: z.string().nullable(),
  last_event: z.string().nullable(),
  run_id: z.string().nullable(),
  detail: z.string().nullable(),
  progress: z.number().nullable(),
});

export type EvalResult = z.infer<typeof evalResultSchema>;
export type EvalSummary = z.infer<typeof evalSummarySchema>;
export type EvalsLatest = z.infer<typeof evalsLatestSchema>;
export type EvalStatus = z.infer<typeof evalStatusSchema>;
export type GoldCase = z.infer<typeof goldCaseSchema>;

/** A stored record: the response as it was returned, plus the request that produced it. */
export const storedAssessmentSchema = assessResponseSchema.extend({
  created_at: z.string(),
  request: z.looseObject({ description: z.string() }),
});

export type StoredAssessment = z.infer<typeof storedAssessmentSchema>;

export type Assessment = z.infer<typeof assessmentSchema>;
export type PolicyOverride = z.infer<typeof policyOverrideSchema>;
export type AssessResponse = z.infer<typeof assessResponseSchema>;
export type Health = z.infer<typeof healthSchema>;
export type HistoryRow = z.infer<typeof historyRowSchema>;
export type Tier = z.infer<typeof tierSchema>;

export interface AssessInput {
  description: string;
  deployment_pattern?: "build" | "onboard" | "onboard_with_customisation" | null;
  is_agentic?: boolean;
  tools_accessible?: string[];
  customer_facing?: boolean;
  model?: string | null;
}

export class ApiError extends Error {
  // Declared as a field rather than a constructor parameter property, which
  // `erasableSyntaxOnly` disallows.
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* the body was not JSON; keep the status message */
    }
    throw new ApiError(detail, response.status);
  }
  return schema.parse(await response.json());
}

export const api = {
  health: () => request("/api/health", healthSchema),
  assessments: () => request("/api/assessments", z.array(historyRowSchema)),
  framework: () => request("/api/framework", frameworkSchema),
  provenance: () => request("/api/framework/provenance", provenanceSchema),
  source: (itemId: string) =>
    request(`/api/framework/source/${encodeURIComponent(itemId)}`, sourceSchema),
  assessment: (id: string) => request(`/api/assessments/${id}`, storedAssessmentSchema),
  evalsLatest: () => request("/api/evals/latest", evalsLatestSchema),
  evalsStatus: () => request("/api/evals/status", evalStatusSchema),
  runEvals: (body: { model?: string; n?: number; cases?: string[] }) =>
    request("/api/evals/run", evalStatusSchema, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export interface StreamStatus {
  step: string;
  label: string;
  done: boolean;
}

/**
 * Consume the SSE endpoint. `fetch` is used rather than `EventSource` because the
 * request is a POST with a JSON body, which EventSource cannot send.
 */
export async function streamAssessment(
  input: AssessInput,
  handlers: {
    onStatus: (status: StreamStatus) => void;
    onResult: (result: AssessResponse) => void;
    onError: (message: string) => void;
  },
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch("/api/assess/stream", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });

  if (!response.ok || !response.body) {
    handlers.onError(`The assessor is unavailable (${response.status}).`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      let event = "message";
      const dataLines: string[] = [];
      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        else if (line.startsWith("data: ")) dataLines.push(line.slice(6));
      }
      if (dataLines.length === 0) continue;

      let payload: unknown;
      try {
        payload = JSON.parse(dataLines.join("\n"));
      } catch {
        continue;
      }

      if (event === "status") {
        handlers.onStatus(payload as StreamStatus);
      } else if (event === "result") {
        const parsed = assessResponseSchema.safeParse(payload);
        if (parsed.success) handlers.onResult(parsed.data);
        else handlers.onError("The assessor returned a result we could not read.");
      } else if (event === "error") {
        handlers.onError(String((payload as { detail?: string }).detail ?? "Unknown error"));
      }
    }
  }
}
