"""The single tool the assessor is forced to call.

Structured output comes from tool use, not from parsing free text: one tool, a strict
schema, and `tool_choice` pinned to it. That matters more than usual here because
`temperature` is rejected by these models, so the schema is the only thing constraining
the shape of the answer.

Field order is deliberate. `materiality_factors` is declared before `inherent_risk_tier`
so the model rates each factor before committing to an overall tier, rather than picking
a tier and back-filling justifications. (The spec's illustrative JSON listed the tier
first; its prose asks for factors first, which is what is implemented.)
"""

from __future__ import annotations

from typing import Any

from .pack import AI_TYPES, DIMENSIONS, OVERSIGHT_MODES, RATINGS

TOOL_NAME = "record_risk_assessment"


def _key(dimension: str) -> str:
    return dimension.lower().replace(" & ", "_and_").replace(" ", "_")


# The seven dimensions as fixed object keys rather than array elements. Strict tool use
# enforces `required` on object properties, but it will not accept a `minItems` above 1
# ("For 'array' type, 'minItems' values other than 0 or 1 are not supported"), so an
# array could not be made to hold seven entries. With an array the model returned a
# single dimension in roughly a third of runs -- the eval harness caught it. As object
# keys the decoding grammar cannot emit fewer than seven.
#
# The named risks live in one flat `key_risks` array rather than inside each of the
# seven: repeating a nested array seven times pushes the compiled grammar over the
# API's size limit ("The compiled grammar is too large"). The assessor merges the two
# back together, so nothing downstream sees the split.
DIMENSION_KEYS: dict[str, str] = {_key(name): name for name in DIMENSIONS}


def _obj(properties: dict[str, Any], description: str | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }
    if description:
        schema["description"] = description
    return schema


def _str(description: str) -> dict[str, Any]:
    return {"type": "string", "description": description}


def _enum(values: tuple[str, ...] | list[str], description: str) -> dict[str, Any]:
    return {"type": "string", "enum": list(values), "description": description}


def _arr(items: dict[str, Any], description: str) -> dict[str, Any]:
    return {"type": "array", "items": items, "description": description}


def assessment_tool() -> dict[str, Any]:
    materiality_factor = _obj(
        {
            "factor": _str(
                "The Section 2.4 factor being rated, using the handbook's own wording."
            ),
            "rating": _enum(RATINGS, "How this factor rates for this use case."),
            "rationale": _str(
                "One or two sentences tied to the described use case. If the description "
                "does not say, rate conservatively and say so here."
            ),
        }
    )

    def risk_dimension(name: str) -> dict[str, Any]:
        return _obj(
            {
                "rating": _enum(RATINGS, f"How exposed this use case is on {name}."),
                "rationale": _str(f"Why {name} rates as it does, for this use case."),
            },
            f"Appendix B dimension: {name}.",
        )

    risk_dimensions = _obj(
        {key: risk_dimension(name) for key, name in DIMENSION_KEYS.items()},
        "All seven Appendix B dimensions. Every one is rated, every time.",
    )

    guardrail = _obj(
        {
            "guardrail": _str(
                "The guardrail's name from the Appendix G library, copied exactly."
            ),
            "handbook_ref": _str(
                "Where it comes from, e.g. 'Appendix G, p. 154' or 'Consideration 11'."
            ),
            "why": _str("Why this guardrail suits this use case at this tier."),
        }
    )

    agentic = {
        "type": ["object", "null"],
        "description": (
            "Agentic-specific analysis. Null unless ai_type is 'agentic' or the use case "
            "gives an AI system tools that act on the world."
        ),
        "properties": {
            "tool_access_risk": _str(
                "What the agent can reach and what could go wrong, including the attack "
                "surface its tools create."
            ),
            "least_privilege_recommendations": _arr(
                _str("A specific scoping or permission restriction."),
                "How to narrow the agent's access to the minimum it needs.",
            ),
            "interruption_controls": _arr(
                _str("A control that can stop or pause the agent."),
                "Kill switches, timeouts, rate limits, distributed or human approvals.",
            ),
            "never_delegate_flags": _arr(
                _str("An action this system must not take without a human decision."),
                "Actions to keep out of the agent's hands, e.g. authorising transactions "
                "or making employment decisions.",
            ),
        },
        "required": [
            "tool_access_risk",
            "least_privilege_recommendations",
            "interruption_controls",
            "never_delegate_flags",
        ],
        "additionalProperties": False,
    }

    schema = _obj(
        {
            "use_case_summary": _str(
                "One or two neutral sentences restating the use case. Do not add facts "
                "the description does not contain."
            ),
            "ai_in_scope": {
                "type": "boolean",
                "description": (
                    "Whether this meets the Section 1.1 definition of AI. Purely "
                    "rule-based, deterministic or menu-driven automation is NOT in scope."
                ),
            },
            "ai_type": _enum(
                AI_TYPES,
                "'agentic' when the system plans and acts through tools; 'gen_ai' for "
                "generative models without tool-driven autonomy; 'traditional' otherwise.",
            ),
            # Rated first, so the tier follows from the factors rather than the reverse.
            "materiality_factors": _arr(
                materiality_factor,
                "Rate EVERY Section 2.4 inherent-risk factor before choosing a tier.",
            ),
            "inherent_risk_tier": _enum(
                RATINGS,
                "The overall inherent risk materiality tier implied by the factors above.",
            ),
            "risk_dimensions": risk_dimensions,
            "key_risks": _arr(
                _obj(
                    {
                        "dimension": _enum(
                            DIMENSIONS, "Which dimension this risk belongs to."
                        ),
                        "risk": _str(
                            "The risk's name from the Appendix B taxonomy, copied exactly."
                        ),
                    }
                ),
                "The specific named risks driving the ratings above, at least one for "
                "every dimension you rated medium or high.",
            ),
            "top_10_flags": _arr(
                _str("The name of an applicable ABS top-10 risk."),
                "Which ABS top-10 risks apply. Empty array if none do.",
            ),
            "recommended_oversight_mode": _enum(
                OVERSIGHT_MODES, "The Section 3.1 oversight mode this use case warrants."
            ),
            "recommended_guardrails": _arr(
                guardrail, "Guardrails proportionate to the tier, named from Appendix G."
            ),
            "recommended_metrics": _arr(
                _str("A metric name from the Appendix F library, copied exactly."),
                "Metrics to monitor this use case against.",
            ),
            "agentic_considerations": agentic,
            "relevant_considerations": _arr(
                {
                    "type": "integer",
                    # `minimum`/`maximum` are rejected under strict tool use ("For
                    # 'integer' type, properties maximum, minimum are not supported"),
                    # so the range lives in the description and is enforced in code.
                    "description": "A Consideration number from Appendix H, from 1 to 17.",
                },
                "Which of the 17 Considerations bear most on this use case. "
                "Each number must be between 1 and 17 inclusive.",
            ),
            "confidence": _enum(
                RATINGS,
                "How confident you are, given how much the description actually says. "
                "A thin description means low confidence, not a confident guess.",
            ),
            "assessor_notes": _str(
                "What a human reviewer should check. State plainly where the description "
                "was insufficient rather than inventing facts to fill the gap."
            ),
        }
    )

    return {
        "name": TOOL_NAME,
        "description": (
            "Record a MindForge AI risk materiality assessment for one AI use case."
        ),
        "input_schema": schema,
        "strict": True,
    }
