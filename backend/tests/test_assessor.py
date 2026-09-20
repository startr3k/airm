"""The assessor's request shape and its repairs, with a mocked client."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from test_llm import FakeMessages, _Stream  # noqa: F401  (shared fake transport)
from test_policy import make_assessment

from mindforge_assess.assessor import assess, system_blocks, system_prompt, user_content
from mindforge_assess.config import Settings
from mindforge_assess.models import AssessRequest
from mindforge_assess.pack import load_pack
from mindforge_assess.schema import TOOL_NAME


def fake_client(payload: dict[str, Any]) -> Any:
    message = SimpleNamespace(
        content=[SimpleNamespace(type="tool_use", name=TOOL_NAME, input=payload)],
        stop_reason="tool_use",
        stop_details=None,
        usage=SimpleNamespace(
            input_tokens=400,
            output_tokens=2000,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=8269,
        ),
    )
    return SimpleNamespace(messages=FakeMessages(message))


def settings() -> Settings:
    from pathlib import Path

    return Settings(
        api_key="test",
        assess_model="claude-sonnet-5",
        ingest_model="claude-opus-5",
        assess_effort="medium",
        ingest_effort="high",
        handbook_pdf=Path("/nonexistent.pdf"),
    )


def run(payload: dict[str, Any], request: AssessRequest | None = None) -> Any:
    client = fake_client(payload)
    response = assess(
        request or AssessRequest(description="A chatbot"),
        client=client,
        settings=settings(),
        pack=load_pack(),
    )
    return response, client.messages.kwargs


@pytest.fixture
def dimension_payload() -> dict[str, Any]:
    """A tool payload in the shape the API now returns: dimensions keyed by name."""
    from mindforge_assess.schema import DIMENSION_KEYS

    payload = make_assessment().model_dump()
    payload["risk_dimensions"] = {
        key: {"rating": "high" if index == 0 else "low", "rationale": "r"}
        for index, key in enumerate(DIMENSION_KEYS)
    }
    payload["key_risks"] = [
        {"dimension": "Fairness & Bias", "risk": "Unrepresentative or biased data inputs"}
    ]
    return payload


def test_system_prompt_is_the_checked_in_file() -> None:
    """What you diff in system.rendered.md is what actually runs."""
    from mindforge_assess.prompts.build_system_prompt import RENDERED_PATH, build

    assert system_prompt() == RENDERED_PATH.read_text()
    assert system_prompt() == build(), "system.rendered.md is stale; regenerate it"


def test_cache_breakpoint_is_on_the_system_prompt() -> None:
    blocks = system_blocks()
    assert len(blocks) == 1
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}


def test_request_shape(monkeypatch) -> None:
    _, sent = run(make_assessment().model_dump())
    assert sent["tool_choice"] == {"type": "tool", "name": TOOL_NAME}
    assert sent["thinking"] == {"type": "adaptive"}
    assert "temperature" not in sent
    assert sent["system"][0]["cache_control"] == {"type": "ephemeral"}
    # Volatile content must come after the breakpoint or it invalidates the cache.
    assert "A chatbot" not in sent["system"][0]["text"]


def test_usage_and_cache_hit_are_reported() -> None:
    response, _ = run(make_assessment().model_dump())
    assert response.usage.cache_read_input_tokens == 8269
    assert response.usage.cache_hit is True
    assert response.pack_version == 1


def test_out_of_range_consideration_numbers_are_dropped() -> None:
    """`minimum`/`maximum` are rejected under strict tool use, so this is enforced here.

    The payload is built as a raw dict on purpose: a model that ignores the instruction
    can return 23, and the point is that `_sanitise` repairs it before validation.
    """
    payload = make_assessment().model_dump()
    payload["relevant_considerations"] = [5, 23, 0, 17]
    response, _ = run(payload)
    assert response.assessment.relevant_considerations == [5, 17]
    assert "do not exist" in response.assessment.assessor_notes


def test_duplicate_consideration_numbers_are_collapsed() -> None:
    payload = make_assessment().model_dump()
    payload["relevant_considerations"] = [5, 5, 11]
    response, _ = run(payload)
    assert response.assessment.relevant_considerations == [5, 11]


def test_mistyped_taxonomy_names_are_grounded_to_the_pack() -> None:
    """Observed live: the model returned 'Hallallucination/ Fabrication/ Confabulation'."""
    payload = make_assessment(
        top_10_flags=["Hallallucination/ Fabrication/ Confabulation"]
    ).model_dump()
    response, _ = run(payload)
    assert response.assessment.top_10_flags == ["Hallucination/ Fabrication/ Confabulation"]
    assert "matched to" in response.assessment.assessor_notes


def test_invented_names_are_kept_but_flagged() -> None:
    payload = make_assessment(recommended_metrics=["Vibes Per Second"]).model_dump()
    response, _ = run(payload)
    assert response.assessment.recommended_metrics == ["Vibes Per Second"]
    assert "do not appear in the handbook" in response.assessment.assessor_notes


def test_guardrail_names_are_grounded() -> None:
    pack = load_pack()
    real = pack.guardrail_names()[0]
    payload = make_assessment(
        recommended_guardrails=[
            {"guardrail": real.upper(), "handbook_ref": "Appendix G", "why": "w"}
        ]
    ).model_dump()
    response, _ = run(payload)
    assert response.assessment.recommended_guardrails[0].guardrail == real


def test_schema_mismatch_raises_rather_than_returning_junk() -> None:
    from mindforge_assess.assessor import AssessmentError

    payload = make_assessment().model_dump()
    payload["inherent_risk_tier"] = "catastrophic"
    with pytest.raises(AssessmentError):
        run(payload)


def test_user_content_carries_declared_metadata() -> None:
    text = user_content(
        AssessRequest(
            description="An agent",
            is_agentic=True,
            tools_accessible=["execute_trade"],
            customer_facing=True,
            deployment_pattern="build",
        )
    )[0]["text"]
    assert "execute_trade" in text
    assert "Customer-facing: yes" in text
    assert "build" in text


def test_undeclared_metadata_is_not_treated_as_absent() -> None:
    text = user_content(AssessRequest(description="A chatbot"))[0]["text"]
    assert "not declared" in text
    assert "unknown, not absent" in text


def test_policy_layer_runs_on_the_model_s_answer() -> None:
    """A money-spending tool triggers the agentic controls but not the tier floor.

    The tier floor keys off the described DOMAIN (credit, underwriting, hiring,
    biometrics, autonomous execution); tool hazards key off the declared tool list and
    add controls and never-delegate flags. Keeping them separate stops every agent with
    a payment tool from being force-rated high on a domain basis.
    """
    request = AssessRequest(
        description="An agent that reconciles supplier invoices",
        is_agentic=True,
        tools_accessible=["issue_payment"],
    )
    response, _ = run(make_assessment(ai_type="agentic").model_dump(), request)
    rules = {o.rule for o in response.policy_overrides}
    assert rules == {
        # The stub returned no agentic analysis at all, so the layer creates one...
        "agentic_analysis_required",
        # ...then fills in the two things an agent with a payment tool must have.
        "interruption_control_required",
        "never_delegate_flag",
    }
    assert response.assessment.inherent_risk_tier == "low"


def test_described_autonomous_execution_does_floor_the_tier() -> None:
    request = AssessRequest(
        description="An agent that executes trades on the client's behalf",
        is_agentic=True,
        tools_accessible=["execute_trade"],
    )
    response, _ = run(make_assessment(ai_type="agentic").model_dump(), request)
    assert response.assessment.inherent_risk_tier == "high"
    assert "high_risk_domain_floor" in {o.rule for o in response.policy_overrides}


# ---------------------------------------------- the seven dimensions as fixed keys


def test_the_tool_requires_all_seven_dimension_keys() -> None:
    """An array could not be pinned to seven entries -- strict tool use rejects a
    `minItems` above 1 -- and with an array the model returned a single dimension in
    roughly a third of runs. Fixed object keys make that impossible to express."""
    from mindforge_assess.pack import DIMENSIONS
    from mindforge_assess.schema import DIMENSION_KEYS, assessment_tool

    block = assessment_tool()["input_schema"]["properties"]["risk_dimensions"]
    assert block["type"] == "object"
    assert block["additionalProperties"] is False
    assert block["required"] == list(DIMENSION_KEYS)
    assert len(DIMENSION_KEYS) == len(DIMENSIONS)
    assert list(DIMENSION_KEYS.values()) == list(DIMENSIONS)
    for dimension in block["properties"].values():
        assert dimension["required"] == ["rating", "rationale"]


def test_dimension_keys_become_the_ordered_list_the_app_uses(dimension_payload) -> None:
    from mindforge_assess.pack import DIMENSIONS

    response, _ = run(dimension_payload)
    returned = [d.dimension for d in response.assessment.risk_dimensions]
    assert returned == list(DIMENSIONS)
    assert response.assessment.risk_dimensions[0].rating == "high"
    # The flat key_risks array is merged back onto the dimension it names.
    assert response.assessment.risk_dimensions[0].key_risks == [
        "Unrepresentative or biased data inputs"
    ]
    assert response.assessment.risk_dimensions[1].key_risks == []


def test_a_dimension_the_model_left_out_is_simply_absent() -> None:
    """Defence in depth: the grammar should make this impossible, but if a key does go
    missing the rest of the assessment still validates rather than failing outright."""
    from mindforge_assess.assessor import _dimension_list

    ordered = _dimension_list({"ethics": {"rating": "low", "rationale": "r"}})
    assert [d["dimension"] for d in ordered] == ["Ethics"]


def test_an_older_array_shaped_payload_still_works() -> None:
    from mindforge_assess.assessor import _dimension_list

    array = [{"dimension": "Ethics", "rating": "low", "key_risks": [], "rationale": "r"}]
    assert _dimension_list(array) == array
