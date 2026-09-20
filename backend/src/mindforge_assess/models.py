"""Pydantic models mirroring the tool schema and the API surface.

These validate what the model returned before anything downstream trusts it, and they
are the contract the front end's zod types are written against.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Rating = Literal["low", "medium", "high"]
AiType = Literal["traditional", "gen_ai", "agentic"]
OversightMode = Literal["human_in_the_loop", "human_over_the_loop", "human_out_of_the_loop"]
DeploymentPattern = Literal["build", "onboard", "onboard_with_customisation"]
Dimension = Literal[
    "Fairness & Bias",
    "Ethics",
    "Accountability & Governance",
    "Transparency",
    "Legal & Regulatory",
    "Robustness & Stability",
    "Cyber & Data Security",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MaterialityFactor(Strict):
    factor: str
    rating: Rating
    rationale: str


class RiskDimension(Strict):
    dimension: Dimension
    rating: Rating
    key_risks: list[str]
    rationale: str


class Guardrail(Strict):
    guardrail: str
    handbook_ref: str
    why: str


class AgenticConsiderations(Strict):
    tool_access_risk: str
    least_privilege_recommendations: list[str]
    interruption_controls: list[str]
    never_delegate_flags: list[str]


class Assessment(Strict):
    """Exactly the tool schema, in the same field order."""

    use_case_summary: str
    ai_in_scope: bool
    ai_type: AiType
    materiality_factors: list[MaterialityFactor]
    inherent_risk_tier: Rating
    risk_dimensions: list[RiskDimension]
    top_10_flags: list[str]
    recommended_oversight_mode: OversightMode
    recommended_guardrails: list[Guardrail]
    recommended_metrics: list[str]
    agentic_considerations: AgenticConsiderations | None
    relevant_considerations: list[Annotated[int, Field(ge=1, le=17)]]
    confidence: Rating
    assessor_notes: str


class PolicyOverride(Strict):
    """One deterministic adjustment the policy layer made to the model's answer."""

    rule: str
    field: str
    before: Any
    after: Any
    reason: str


class AssessRequest(Strict):
    description: str = Field(min_length=1, max_length=20_000)
    deployment_pattern: DeploymentPattern | None = None
    is_agentic: bool = False
    tools_accessible: list[str] = Field(default_factory=list)
    customer_facing: bool = False
    model: str | None = Field(
        default=None, description="Override the assessor model for this request."
    )


class EvalRunRequest(Strict):
    """Start an eval run. Small `n` by default -- each run is a paid API call."""

    model: str | None = None
    n: int = Field(default=3, ge=1, le=5)
    cases: list[str] = Field(default_factory=list)


class Usage(Strict):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @property
    def cache_hit(self) -> bool:
        return self.cache_read_input_tokens > 0


class AssessResponse(Strict):
    assessment: Assessment
    policy_overrides: list[PolicyOverride]
    model: str
    usage: Usage
    latency_ms: int
    assessment_id: str
    pack_version: int
    pdf_sha256: str


class HealthResponse(Strict):
    ok: bool
    api_key_present: bool
    pack_loaded: bool
    pack_version: int | None
    pdf_sha256: str | None
    assess_model: str
    detail: str | None = None
