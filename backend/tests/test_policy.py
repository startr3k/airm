"""The policy layer is the part that must hold regardless of what the model says."""

from __future__ import annotations

from typing import Any

import pytest

from mindforge_assess.models import AgenticConsiderations, Assessment, AssessRequest
from mindforge_assess.policy import apply_policy, detect_domains, detect_tool_hazards


def make_assessment(**overrides: Any) -> Assessment:
    base: dict[str, Any] = {
        "use_case_summary": "A system that does a thing.",
        "ai_in_scope": True,
        "ai_type": "gen_ai",
        "materiality_factors": [
            {"factor": "Reputational risk", "rating": "low", "rationale": "r"}
        ],
        "inherent_risk_tier": "low",
        "risk_dimensions": [
            {"dimension": "Fairness & Bias", "rating": "low", "key_risks": [], "rationale": "r"}
        ],
        "top_10_flags": [],
        "recommended_oversight_mode": "human_over_the_loop",
        "recommended_guardrails": [
            {"guardrail": "Input validation", "handbook_ref": "Appendix G", "why": "w"}
        ],
        "recommended_metrics": ["Accuracy"],
        "agentic_considerations": None,
        "relevant_considerations": [5],
        "confidence": "medium",
        "assessor_notes": "Initial notes.",
    }
    base.update(overrides)
    return Assessment.model_validate(base)


def request(description: str, **kwargs: Any) -> AssessRequest:
    return AssessRequest(description=description, **kwargs)


# ------------------------------------------------- rule 1: high-risk domain floor


@pytest.mark.parametrize(
    ("description", "domain"),
    [
        ("A model that scores creditworthiness for loan applications", "credit_lending"),
        ("Automates credit decisioning for SME lending", "credit_lending"),
        ("Assists with insurance underwriting for motor policies", "insurance_underwriting"),
        ("Sets premium pricing for health cover", "insurance_underwriting"),
        ("Screens CVs and ranks candidates for hiring", "employment"),
        ("Supports promotion decisions for staff", "employment"),
        ("Uses facial recognition to verify customers", "biometric"),
        ("Performs a liveness check during onboarding", "biometric"),
        ("Executes trades on behalf of clients", "autonomous_transactions"),
        ("Initiates payments to suppliers automatically", "autonomous_transactions"),
    ],
)
def test_high_risk_domains_are_detected(description: str, domain: str) -> None:
    assert domain in {d.key for d in detect_domains(request(description))}


@pytest.mark.parametrize(
    "description",
    [
        "An internal knowledge chatbot answering HR policy questions",
        "Summarises meeting notes for relationship managers",
        "Classifies incoming support tickets by topic",
        "A dashboard that displays historical trade volumes",
    ],
)
def test_benign_use_cases_are_not_floored(description: str) -> None:
    assert detect_domains(request(description)) == []
    _, overrides = apply_policy(make_assessment(), request(description))
    assert overrides == []


def test_tier_is_floored_at_high_and_recorded() -> None:
    req = request("Automates credit decisions for personal loan applications")
    result, overrides = apply_policy(make_assessment(inherent_risk_tier="low"), req)

    assert result.inherent_risk_tier == "high"
    floor = next(o for o in overrides if o.rule == "high_risk_domain_floor")
    assert floor.field == "inherent_risk_tier"
    assert floor.before == "low"
    assert floor.after == "high"
    assert "credit or lending decisions" in floor.reason
    assert "POLICY:" in result.assessor_notes
    assert "Initial notes." in result.assessor_notes, "must not discard the model's notes"


def test_a_high_rating_is_left_alone() -> None:
    """The floor raises; it never lowers, and it records nothing when it changes nothing."""
    req = request("Automates credit decisions")
    result, overrides = apply_policy(make_assessment(inherent_risk_tier="high"), req)
    assert result.inherent_risk_tier == "high"
    assert [o for o in overrides if o.rule == "high_risk_domain_floor"] == []


def test_tools_also_trigger_the_domain_floor() -> None:
    req = request(
        "An assistant for relationship managers",
        is_agentic=True,
        tools_accessible=["execute_trade", "read_portfolio"],
    )
    result, _ = apply_policy(make_assessment(), req)
    assert result.inherent_risk_tier == "high"


# ------------------------------------------------ rule 2: agentic tool hazards


@pytest.mark.parametrize(
    ("tool", "hazard"),
    [
        ("send_payment", "spends_money"),
        ("place_order", "spends_money"),
        ("send_email_to_client", "external_comms"),
        ("post_message_to_slack", "external_comms"),
        ("update_crm_record", "production_writes"),
        ("write_to_ledger", "production_writes"),
    ],
)
def test_tool_hazards_are_detected(tool: str, hazard: str) -> None:
    req = request("An agent", is_agentic=True, tools_accessible=[tool])
    assert hazard in {h.key for h in detect_tool_hazards(req)}


def test_hazards_need_declared_tools_not_just_prose() -> None:
    """The description is too loose a signal for tool hazards; the tool list is not."""
    assert detect_tool_hazards(request("it can send emails and make payments")) == []


def test_interruption_control_is_added_when_missing() -> None:
    req = request(
        "An agent that reconciles invoices",
        is_agentic=True,
        tools_accessible=["issue_payment"],
    )
    result, overrides = apply_policy(make_assessment(ai_type="agentic"), req)

    assert result.agentic_considerations is not None
    assert len(result.agentic_considerations.interruption_controls) >= 1
    assert any(o.rule == "interruption_control_required" for o in overrides)


def test_existing_interruption_controls_are_preserved() -> None:
    req = request("An agent", is_agentic=True, tools_accessible=["issue_payment"])
    agentic = AgenticConsiderations(
        tool_access_risk="risky",
        least_privilege_recommendations=[],
        interruption_controls=["Human approval above $1,000"],
        never_delegate_flags=[],
    )
    result, overrides = apply_policy(
        make_assessment(ai_type="agentic", agentic_considerations=agentic), req
    )
    assert result.agentic_considerations is not None
    assert result.agentic_considerations.interruption_controls == ["Human approval above $1,000"]
    assert not any(o.rule == "interruption_control_required" for o in overrides)


def test_never_delegate_is_flagged_for_money_tools() -> None:
    req = request("An agent", is_agentic=True, tools_accessible=["transfer_funds"])
    result, overrides = apply_policy(make_assessment(ai_type="agentic"), req)

    assert result.agentic_considerations is not None
    flags = result.agentic_considerations.never_delegate_flags
    assert "Authorising financial transactions" in flags
    assert any(o.rule == "never_delegate_flag" for o in overrides)


def test_never_delegate_flags_are_not_duplicated() -> None:
    req = request("An agent", is_agentic=True, tools_accessible=["transfer_funds", "pay_invoice"])
    agentic = AgenticConsiderations(
        tool_access_risk="r",
        least_privilege_recommendations=[],
        interruption_controls=["kill switch"],
        never_delegate_flags=["authorising financial transactions"],
    )
    result, _ = apply_policy(
        make_assessment(ai_type="agentic", agentic_considerations=agentic), req
    )
    assert result.agentic_considerations is not None
    flags = [f.casefold() for f in result.agentic_considerations.never_delegate_flags]
    assert flags.count("authorising financial transactions") == 1


def test_non_agentic_use_cases_get_no_agentic_overrides() -> None:
    req = request("A chatbot", is_agentic=False, tools_accessible=["send_email"])
    result, overrides = apply_policy(make_assessment(ai_type="gen_ai"), req)
    assert result.agentic_considerations is None
    assert overrides == []


def test_agentic_without_hazardous_tools_is_left_alone() -> None:
    req = request("An agent", is_agentic=True, tools_accessible=["search_knowledge_base"])
    _, overrides = apply_policy(make_assessment(ai_type="agentic"), req)
    assert overrides == []


# ---------------------------------------------- rule 3: out-of-scope short circuit


def test_out_of_scope_clears_the_analysis() -> None:
    req = request("A rule-based RPA bot that copies values between two spreadsheets")
    result, overrides = apply_policy(make_assessment(ai_in_scope=False), req)

    assert result.ai_in_scope is False
    assert result.risk_dimensions == []
    assert result.recommended_guardrails == []
    assert result.recommended_metrics == []
    assert result.relevant_considerations == []
    assert any(o.rule == "out_of_scope_short_circuit" for o in overrides)
    assert "Section 1.1" in result.assessor_notes


def test_out_of_scope_skips_the_other_rules() -> None:
    """An out-of-scope RPA bot must not also be floored to 'high' for mentioning credit."""
    req = request("A deterministic RPA macro that rekeys approved credit decisions")
    result, overrides = apply_policy(make_assessment(ai_in_scope=False), req)
    assert {o.rule for o in overrides} == {"out_of_scope_short_circuit"}
    assert result.inherent_risk_tier == "low"


def test_policy_never_mutates_the_model_s_answer_in_place() -> None:
    original = make_assessment(inherent_risk_tier="low")
    apply_policy(original, request("Automates credit decisions"))
    assert original.inherent_risk_tier == "low", "the original must be left untouched"
