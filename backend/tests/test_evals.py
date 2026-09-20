"""The eval harness, graded against synthetic responses. Never calls the API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import anthropic

# The Anthropic SDK is built on httpx2; constructing its errors with the other
# httpx works at runtime but is a different type, which mypy rightly objects to.
import httpx2 as httpx
import pytest
from test_policy import make_assessment

from mindforge_assess.evals import report
from mindforge_assess.evals.gold import (
    Expectation,
    GoldCase,
    GoldSetError,
    load_gold,
    validate_gold,
)
from mindforge_assess.evals.runner import _retryable, build_result
from mindforge_assess.evals.scoring import aggregate, failed_run, grade, model_tier_of
from mindforge_assess.models import AssessRequest, AssessResponse, PolicyOverride, Usage

# ------------------------------------------------------------------ the gold set


def test_gold_set_loads() -> None:
    cases = load_gold()
    assert len(cases) == 10
    assert len({c.id for c in cases}) == 10


def test_every_gold_expectation_exists_in_the_pack() -> None:
    """A mistyped dimension or a Consideration number that does not exist would
    otherwise score zero forever without anyone noticing."""
    assert validate_gold(load_gold()) == []


def test_gold_set_covers_the_tricky_shapes() -> None:
    cases = {c.id: c for c in load_gold()}
    assert cases["rpa-invoice-reconciliation"].expect.ai_in_scope is False
    assert cases["underspecified-login-invoice"].expect.max_confidence == "medium"
    assert cases["agentic-rm-assistant"].expect.agentic_analysis_required is True
    tiers = [c.expect.tier for c in cases.values() if c.expect.tier]
    assert set(tiers) == {"low", "medium", "high"}


def test_unknown_expectation_key_is_rejected() -> None:
    with pytest.raises(GoldSetError, match="unknown expectation key"):
        Expectation.from_json({"inherant_risk_tier": "high"})


def test_typo_in_an_expectation_is_caught_by_validation() -> None:
    case = GoldCase(
        id="typo",
        title="t",
        tests="t",
        request=AssessRequest(description="d"),
        expect=Expectation(
            min_dimension_ratings={"Fairness and Bias": "high"},  # '&' in the real name
            considerations=(99,),
            top_10_flags=("Not a real risk",),
        ),
    )
    problems = validate_gold([case])
    assert len(problems) == 3
    assert any("Fairness and Bias" in p for p in problems)
    assert any("Consideration 99" in p for p in problems)


# ------------------------------------------------------------------- grading


def response(assessment: Any, **kwargs: Any) -> AssessResponse:
    defaults: dict[str, Any] = {
        "assessment": assessment,
        "policy_overrides": [],
        "model": "claude-sonnet-5",
        "usage": Usage(input_tokens=300, output_tokens=2000, cache_read_input_tokens=6000),
        "latency_ms": 20_000,
        "assessment_id": "abc",
        "pack_version": 1,
        "pdf_sha256": "0" * 64,
    }
    defaults.update(kwargs)
    return AssessResponse.model_validate(defaults)


def case(**expect: Any) -> GoldCase:
    return GoldCase(
        id="c1",
        title="t",
        tests="t",
        request=AssessRequest(description="d"),
        expect=Expectation(**expect),
    )


def test_a_correct_response_passes_every_check() -> None:
    assessment = make_assessment(
        inherent_risk_tier="high",
        ai_type="traditional",
        recommended_oversight_mode="human_in_the_loop",
        confidence="low",
        risk_dimensions=[
            {"dimension": "Fairness & Bias", "rating": "high", "key_risks": [], "rationale": "r"}
        ],
        top_10_flags=["Overconfidence"],
        relevant_considerations=[5, 7],
    )
    result = grade(
        case(
            ai_in_scope=True,
            ai_type="traditional",
            tier="high",
            tier_accepted=("high",),
            oversight_modes=("human_in_the_loop",),
            max_confidence="medium",
            min_dimension_ratings={"Fairness & Bias": "high"},
            top_10_flags=("Overconfidence",),
            considerations=(5, 7),
        ),
        response(assessment),
        run=1,
    )
    assert result.failures == []
    assert all(r.ratio == 1.0 for r in result.recalls.values() if r.expected)


def test_ungraded_expectations_produce_no_checks() -> None:
    """Leaving a field out of `expect` must not quietly count as a pass or a fail."""
    result = grade(case(tier="high"), response(make_assessment(inherent_risk_tier="high")), run=1)
    assert [c.field for c in result.checks] == ["inherent_risk_tier", "tier_within_tolerance"]


def test_a_tier_inside_tolerance_still_fails_the_exact_check() -> None:
    result = grade(
        case(tier="medium", tier_accepted=("low", "medium")),
        response(make_assessment(inherent_risk_tier="low")),
        run=1,
    )
    passed = {c.field: c.passed for c in result.checks}
    assert passed == {"inherent_risk_tier": False, "tier_within_tolerance": True}


def test_a_dimension_rated_below_its_floor_is_recorded_as_missing() -> None:
    assessment = make_assessment(
        risk_dimensions=[
            {"dimension": "Fairness & Bias", "rating": "medium", "key_risks": [], "rationale": "r"}
        ]
    )
    result = grade(
        case(min_dimension_ratings={"Fairness & Bias": "high"}), response(assessment), run=1
    )
    recall = result.recalls["dimension_floors"]
    assert recall.ratio == 0.0
    assert recall.missing == ["Fairness & Bias >= high (got medium)"]


def test_an_absent_dimension_counts_as_missing_not_as_a_crash() -> None:
    result = grade(
        case(min_dimension_ratings={"Ethics": "low"}),
        response(make_assessment(risk_dimensions=[])),
        run=1,
    )
    assert result.recalls["dimension_floors"].missing == ["Ethics >= low (got absent)"]


def test_confidence_above_the_cap_fails() -> None:
    result = grade(
        case(max_confidence="medium"), response(make_assessment(confidence="high")), run=1
    )
    assert result.failures[0].field == "confidence_calibrated"


def test_withheld_analysis_is_what_the_out_of_scope_case_checks() -> None:
    withheld = make_assessment(
        ai_in_scope=False, risk_dimensions=[], recommended_guardrails=[], recommended_metrics=[]
    )
    expectation = case(ai_in_scope=False, empty_risk_analysis=True)
    assert grade(expectation, response(withheld), run=1).failures == []
    assert grade(expectation, response(make_assessment(ai_in_scope=False)), run=1).failures


def test_the_models_own_tier_is_recovered_from_the_override_log() -> None:
    """The floor rules make the final tier trivially right, so the report has to be
    able to show what the model said on its own."""
    floored = response(
        make_assessment(inherent_risk_tier="high"),
        policy_overrides=[
            PolicyOverride(
                rule="high_risk_domain_floor",
                field="inherent_risk_tier",
                before="medium",
                after="high",
                reason="r",
            )
        ],
    )
    assert model_tier_of(floored) == "medium"
    assert grade(case(tier="high"), floored, run=1).model_tier == "medium"
    assert model_tier_of(response(make_assessment(inherent_risk_tier="low"))) == "low"


def test_a_required_policy_rule_that_did_not_fire_is_recorded() -> None:
    result = grade(case(policy_rules=("never_delegate_flag",)), response(make_assessment()), run=1)
    assert result.recalls["policy_rules"].missing == ["never_delegate_flag"]


# --------------------------------------------------------------- aggregation


def grades_for(tiers: list[str], expected: str = "high") -> tuple[list[GoldCase], list[Any]]:
    gold = [case(tier=expected)]
    return gold, [
        grade(gold[0], response(make_assessment(inherent_risk_tier=t)), run=i + 1)
        for i, t in enumerate(tiers)
    ]


def test_consistency_is_measured_separately_from_accuracy() -> None:
    """Three runs that all say the same wrong thing are 100% consistent and 0% right."""
    cases, grades = grades_for(["low", "low", "low"], expected="high")
    summary = aggregate(cases, grades)
    assert summary["tier_consistency"]["mean_modal_agreement"] == 1.0
    assert summary["field_accuracy"]["inherent_risk_tier"]["accuracy"] == 0.0


def test_disagreeing_runs_lower_the_consistency_score() -> None:
    cases, grades = grades_for(["high", "high", "medium"])
    summary = aggregate(cases, grades)
    assert summary["tier_consistency"]["mean_modal_agreement"] == pytest.approx(2 / 3)
    assert summary["tier_consistency"]["unanimous_cases"] == 0
    assert summary["field_accuracy"]["inherent_risk_tier"]["accuracy"] == pytest.approx(2 / 3)


def test_the_confusion_matrix_counts_gold_against_returned() -> None:
    cases, grades = grades_for(["high", "medium", "medium"])
    assert aggregate(cases, grades)["tier_confusion"] == {"high": {"high": 1, "medium": 2}}


def test_an_api_failure_is_an_error_not_a_wrong_answer() -> None:
    cases, grades = grades_for(["high", "high"])
    grades.append(failed_run(cases[0], run=3, error="APIStatusError: 500", attempts=4))
    summary = aggregate(cases, grades)
    assert summary["runs_errored"] == 1
    assert summary["retries"] == 3
    assert summary["field_accuracy"]["inherent_risk_tier"]["accuracy"] == 1.0
    assert summary["errors"][0]["run"] == 3


def test_an_invalid_assessment_is_counted_apart_from_an_api_failure() -> None:
    """One says the upstream failed; the other says the model did. They are not the
    same finding and the report must not blend them."""
    cases, grades = grades_for(["high"])
    grades.append(failed_run(cases[0], run=2, error="bad schema", attempts=1,
                             kind="invalid_assessment"))
    grades.append(failed_run(cases[0], run=3, error="500", attempts=2))
    summary = aggregate(cases, grades)
    assert summary["errors_by_kind"] == {"invalid_assessment": 1, "api": 1}


def test_cost_and_latency_are_rolled_up() -> None:
    cases, grades = grades_for(["high", "high"])
    summary = aggregate(cases, grades)
    assert summary["latency_ms"]["p50"] == 20_000
    assert summary["cost_usd"]["total"] > 0
    assert summary["tokens"]["cache_hit_rate"] == 1.0


# ------------------------------------------------------------ retry + report


def api_error(status: int) -> anthropic.APIStatusError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIStatusError(
        "boom", response=httpx.Response(status, request=request), body=None
    )


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (api_error(500), True),
        (api_error(529), True),
        (api_error(400), False),
        (anthropic.APIConnectionError(request=httpx.Request("POST", "https://x")), True),
    ],
)
def test_only_transient_failures_are_retried(exc: Exception, expected: bool) -> None:
    assert _retryable(exc) is expected


def test_a_fault_raised_mid_stream_is_retried_despite_its_200() -> None:
    """Both API failures in the first live run arrived inside the event stream, so the
    exception carried the stream's own 200 and a status check alone missed them."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    mid_stream = anthropic.APIStatusError(
        "{'type': 'error', 'error': {'type': 'api_error', 'message': 'Internal server error'}}",
        response=httpx.Response(200, request=request),
        body=None,
    )
    assert _retryable(mid_stream) is True


def test_a_genuine_bad_request_is_still_not_retried() -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    bad = anthropic.APIStatusError(
        "tools.0.custom: minItems is not supported",
        response=httpx.Response(400, request=request),
        body=None,
    )
    assert _retryable(bad) is False


def test_credit_exhaustion_is_not_retried() -> None:
    from mindforge_assess.llm import ApiUnavailableError

    assert _retryable(ApiUnavailableError("credit balance is too low")) is False


def test_the_markdown_report_renders_every_section() -> None:
    cases, grades = grades_for(["high", "medium"])
    result = build_result(
        cases, grades, model="claude-sonnet-5", n=2, effort="medium",
        started=datetime.now(UTC), duration_s=42.0,
    )
    markdown = report.render(result)
    headings = ("# Eval run", "## Per-field accuracy", "## Tier confusion matrix", "## Per case")
    for heading in headings:
        assert heading in markdown
    assert result["prompt_sha256"]


def test_the_comparison_table_names_the_disagreements() -> None:
    cases, sonnet = grades_for(["high", "high"])
    _, opus = grades_for(["medium", "medium"])
    started = datetime.now(UTC)
    results = [
        build_result(cases, sonnet, model="claude-sonnet-5", n=2, effort="medium",
                     started=started, duration_s=1.0),
        build_result(cases, opus, model="claude-opus-5", n=2, effort="medium",
                     started=started, duration_s=1.0),
    ]
    markdown = report.compare(results)
    assert "claude-opus-5" in markdown
    assert "Where they disagree" in markdown
    assert "| `c1` | high ×2 | medium ×2 |" in markdown


def test_a_truncated_response_is_retried() -> None:
    """How far adaptive thinking runs varies run to run, so the same request usually
    finishes inside the budget on a second attempt."""
    from mindforge_assess.llm import OutputTruncatedError

    assert _retryable(OutputTruncatedError("cut off at max_tokens (32,000)")) is True
