import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ResultsView } from "../ResultsView";
import { makeAssessment, makeResponse } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

// The citation index is fetched; the chips it drives are not what these tests assert.
const CITATION_INDEX = {
  items: { "guardrail:red-teaming": { label: "Red teaming", page: 156 } },
  guardrails: { "Red teaming": "guardrail:red-teaming" },
  metrics: {},
  dimensions: {},
  factors: {},
  oversight_modes: {},
  considerations: {},
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(CITATION_INDEX), { status: 200 })),
  );
});

describe("the assessment header", () => {
  it("states the tier in words, not only in colour", () => {
    renderWithProviders(<ResultsView response={makeResponse()} />);
    // Colour is never the only signal: the tier is spelled out beside the badge, so a
    // reader who cannot distinguish the colours still gets the answer.
    const badge = screen.getByText(/inherent risk/i).parentElement;
    expect(badge).toHaveTextContent("High inherent risk");
  });

  it("shows the model, latency and whether the prompt cache was read", () => {
    renderWithProviders(<ResultsView response={makeResponse()} />);
    expect(screen.getByText(/claude-sonnet-5/)).toBeInTheDocument();
    expect(screen.getByText(/31\.9s/)).toBeInTheDocument();
    expect(screen.getByText(/cache/i)).toBeInTheDocument();
  });
});

describe("policy overrides", () => {
  it("shows what the model said and what the policy layer said instead", () => {
    const response = makeResponse({
      assessment: makeAssessment({ inherent_risk_tier: "high" }),
      policy_overrides: [
        {
          rule: "high_risk_domain_floor",
          field: "inherent_risk_tier",
          before: "medium",
          after: "high",
          reason: "The description involves credit or lending decisions.",
        },
      ],
    });
    renderWithProviders(<ResultsView response={response} />);

    expect(screen.getByText(/policy layer adjusted/i)).toBeInTheDocument();
    expect(screen.getByText("high_risk_domain_floor")).toBeInTheDocument();
    // Both sides of the adjustment are visible: nothing is rewritten silently.
    expect(screen.getByText(/model said/i)).toBeInTheDocument();
    expect(screen.getByText(/medium/)).toBeInTheDocument();
    expect(screen.getByText(/credit or lending decisions/)).toBeInTheDocument();
  });

  it("says nothing when the policy layer changed nothing", () => {
    renderWithProviders(<ResultsView response={makeResponse()} />);
    expect(screen.queryByText(/policy layer adjusted/i)).not.toBeInTheDocument();
  });
});

describe("an out-of-scope use case", () => {
  const outOfScope = makeResponse({
    assessment: makeAssessment({
      ai_in_scope: false,
      risk_dimensions: [],
      recommended_guardrails: [],
      recommended_metrics: [],
      top_10_flags: [],
      relevant_considerations: [],
      assessor_notes: "Purely rule-based: not AI under Section 1.1.",
    }),
  });

  it("withholds the risk analysis rather than showing an empty one", () => {
    renderWithProviders(<ResultsView response={outOfScope} />);
    expect(screen.queryByRole("heading", { name: "Risk dimensions" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /Recommended controls/ }),
    ).not.toBeInTheDocument();
  });

  it("still explains why, so the answer is not just an absence", () => {
    renderWithProviders(<ResultsView response={outOfScope} />);
    expect(screen.getByText(/not AI under Section 1\.1/)).toBeInTheDocument();
  });
});

describe("the seven risk dimensions", () => {
  it("lists every dimension with its rating", () => {
    renderWithProviders(<ResultsView response={makeResponse()} />);
    const list = screen.getByRole("heading", { name: "Risk dimensions" }).closest("div")
      ?.parentElement as HTMLElement;
    for (const dimension of [
      "Fairness & Bias",
      "Ethics",
      "Accountability & Governance",
      "Transparency",
      "Legal & Regulatory",
      "Robustness & Stability",
      "Cyber & Data Security",
    ]) {
      expect(within(list).getByText(dimension)).toBeInTheDocument();
    }
  });

  it("reveals the rationale when a dimension is expanded", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ResultsView response={makeResponse()} />);
    expect(screen.queryByText(/Why Ethics rates as it does/)).not.toBeInTheDocument();
    await user.click(screen.getByText("Ethics"));
    expect(screen.getByText(/Why Ethics rates as it does/)).toBeInTheDocument();
  });
});

describe("agentic analysis", () => {
  it("is absent for a use case that is not agentic", () => {
    renderWithProviders(<ResultsView response={makeResponse()} />);
    expect(screen.queryByText(/never delegate/i)).not.toBeInTheDocument();
  });

  it("names the actions that must not be delegated when it is", () => {
    const response = makeResponse({
      assessment: makeAssessment({
        ai_type: "agentic",
        agentic_considerations: {
          tool_access_risk: "The agent can place trades.",
          least_privilege_recommendations: ["Scope the execution API to a value limit."],
          interruption_controls: ["Kill switch with a named owner."],
          never_delegate_flags: ["Authorising financial transactions"],
        },
      }),
    });
    renderWithProviders(<ResultsView response={response} />);
    expect(screen.getByText("Authorising financial transactions")).toBeInTheDocument();
    expect(screen.getByText(/Kill switch with a named owner/)).toBeInTheDocument();
  });
});
