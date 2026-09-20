"""Grading and aggregation. Pure functions -- no API key, no network, no clock.

Two things are measured separately and should not be conflated:

*   **Accuracy** -- did the run get a field right, against an expectation the handbook
    settles.
*   **Consistency** -- did the N runs of the same case agree with *each other*. These
    models have no temperature knob, so run-to-run variance is a real property of the
    system and the only way to see it is to measure it.

A run can be perfectly consistent and consistently wrong, so both are reported.
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

from ..models import AssessResponse
from .gold import RATING_ORDER, GoldCase

# Fields reported in the per-field accuracy table, in reading order.
FIELDS: tuple[str, ...] = (
    "ai_in_scope",
    "ai_type",
    "inherent_risk_tier",
    "tier_within_tolerance",
    "recommended_oversight_mode",
    "confidence_calibrated",
    "agentic_analysis",
    "risk_analysis_withheld",
)

# Recall metrics, each a ratio of (matched, expected) summed across runs.
RECALLS: tuple[str, ...] = (
    "dimension_floors",
    "top_10_flags",
    "considerations",
    "policy_rules",
)


@dataclass
class Check:
    """One graded assertion about one run."""

    field: str
    passed: bool
    expected: Any
    actual: Any


@dataclass
class Recall:
    matched: int
    expected: int
    missing: list[str] = field(default_factory=list)

    @property
    def ratio(self) -> float | None:
        return self.matched / self.expected if self.expected else None


@dataclass
class RunGrade:
    """The graded outcome of one assessment of one case."""

    case_id: str
    run: int
    checks: list[Check]
    recalls: dict[str, Recall]
    tier: str | None
    model_tier: str | None
    policy_rules_fired: list[str]
    latency_ms: int
    cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    attempts: int = 1
    error: str | None = None
    error_kind: str | None = None  # "api" or "invalid_assessment"

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "run": self.run,
            "error": self.error,
            "error_kind": self.error_kind,
            "attempts": self.attempts,
            "tier": self.tier,
            "model_tier": self.model_tier,
            "policy_rules_fired": self.policy_rules_fired,
            "latency_ms": self.latency_ms,
            "cost_usd": round(self.cost_usd, 6),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "checks": [asdict(c) for c in self.checks],
            "recalls": {k: asdict(v) for k, v in self.recalls.items()},
        }


def _at_least(actual: str | None, minimum: str) -> bool:
    if actual is None:
        return False
    return RATING_ORDER[actual] >= RATING_ORDER[minimum]


def model_tier_of(response: AssessResponse) -> str:
    """What the model said before the policy layer touched it.

    The floor rules record their `before` value, so the model's own tier is recoverable
    from the override log -- which is the whole point of logging them.
    """
    for override in response.policy_overrides:
        if override.field == "inherent_risk_tier":
            return str(override.before)
    return response.assessment.inherent_risk_tier


def grade(case: GoldCase, response: AssessResponse, *, run: int, attempts: int = 1) -> RunGrade:
    """Grade one response against one case. Ungraded expectations produce no check."""
    a = response.assessment
    e = case.expect
    checks: list[Check] = []

    def check(field_name: str, passed: bool, expected: Any, actual: Any) -> None:
        checks.append(Check(field=field_name, passed=passed, expected=expected, actual=actual))

    if e.ai_in_scope is not None:
        check("ai_in_scope", a.ai_in_scope == e.ai_in_scope, e.ai_in_scope, a.ai_in_scope)
    if e.ai_type is not None:
        check("ai_type", a.ai_type == e.ai_type, e.ai_type, a.ai_type)
    if e.tier is not None:
        check("inherent_risk_tier", a.inherent_risk_tier == e.tier, e.tier, a.inherent_risk_tier)
    if e.accepted_tiers:
        check(
            "tier_within_tolerance",
            a.inherent_risk_tier in e.accepted_tiers,
            list(e.accepted_tiers),
            a.inherent_risk_tier,
        )
    if e.oversight_modes:
        check(
            "recommended_oversight_mode",
            a.recommended_oversight_mode in e.oversight_modes,
            list(e.oversight_modes),
            a.recommended_oversight_mode,
        )
    if e.max_confidence is not None:
        check(
            "confidence_calibrated",
            RATING_ORDER[a.confidence] <= RATING_ORDER[e.max_confidence],
            f"<= {e.max_confidence}",
            a.confidence,
        )
    if e.agentic_analysis_required is not None:
        present = a.agentic_considerations is not None
        check(
            "agentic_analysis",
            present == e.agentic_analysis_required,
            "present" if e.agentic_analysis_required else "absent",
            "present" if present else "absent",
        )
    if e.empty_risk_analysis:
        withheld = not a.risk_dimensions and not a.recommended_guardrails
        check("risk_analysis_withheld", withheld, "withheld", "withheld" if withheld else "present")

    # Keyed by plain string: the gold set names dimensions in its own JSON, and a
    # name that is not in the taxonomy must read as "absent" rather than fail to type.
    ratings: dict[str, str] = {str(d.dimension): str(d.rating) for d in a.risk_dimensions}
    missing_floors = [
        f"{name} >= {minimum} (got {ratings.get(name, 'absent')})"
        for name, minimum in e.min_dimension_ratings.items()
        if not _at_least(ratings.get(name), minimum)
    ]
    flagged = set(a.top_10_flags)
    cited = set(a.relevant_considerations)
    fired = [o.rule for o in response.policy_overrides]

    recalls = {
        "dimension_floors": Recall(
            matched=len(e.min_dimension_ratings) - len(missing_floors),
            expected=len(e.min_dimension_ratings),
            missing=missing_floors,
        ),
        "top_10_flags": Recall(
            matched=sum(1 for f in e.top_10_flags if f in flagged),
            expected=len(e.top_10_flags),
            missing=[f for f in e.top_10_flags if f not in flagged],
        ),
        "considerations": Recall(
            matched=sum(1 for n in e.considerations if n in cited),
            expected=len(e.considerations),
            missing=[f"Consideration {n}" for n in e.considerations if n not in cited],
        ),
        "policy_rules": Recall(
            matched=sum(1 for r in e.policy_rules if r in fired),
            expected=len(e.policy_rules),
            missing=[r for r in e.policy_rules if r not in fired],
        ),
    }

    usage = response.usage
    return RunGrade(
        case_id=case.id,
        run=run,
        checks=checks,
        recalls=recalls,
        tier=a.inherent_risk_tier,
        model_tier=model_tier_of(response),
        policy_rules_fired=sorted(set(fired)),
        latency_ms=response.latency_ms,
        cost_usd=_cost(response),
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read_tokens=usage.cache_read_input_tokens,
        attempts=attempts,
    )


def _cost(response: AssessResponse) -> float:
    from ..llm import Usage as RawUsage

    raw = RawUsage(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cache_creation_input_tokens=response.usage.cache_creation_input_tokens,
        cache_read_input_tokens=response.usage.cache_read_input_tokens,
    )
    return raw.cost_usd(response.model)


def failed_run(
    case: GoldCase, *, run: int, error: str, attempts: int, kind: str = "api"
) -> RunGrade:
    """A run that produced no gradeable answer. An error, never a wrong answer.

    `kind` separates the two causes, which mean very different things: "api" is the
    upstream failing, "invalid_assessment" is the model returning something the schema
    rejects -- a fact about the model that belongs in the report, not in the noise.
    """
    return RunGrade(
        case_id=case.id,
        run=run,
        checks=[],
        recalls={},
        tier=None,
        model_tier=None,
        policy_rules_fired=[],
        latency_ms=0,
        cost_usd=0.0,
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=0,
        attempts=attempts,
        error=error,
        error_kind=kind,
    )


# ----------------------------------------------------------------- aggregation


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
    return ordered[index]


def aggregate(cases: list[GoldCase], grades: list[RunGrade]) -> dict[str, Any]:
    """Roll per-run grades into the numbers the report and the Evals page show."""
    by_case = {case.id: case for case in cases}
    ok = [g for g in grades if g.ok]
    errored = [g for g in grades if not g.ok]

    field_accuracy: dict[str, dict[str, Any]] = {}
    for name in FIELDS:
        graded = [c for g in ok for c in g.checks if c.field == name]
        if graded:
            passed = sum(1 for c in graded if c.passed)
            field_accuracy[name] = {
                "passed": passed,
                "graded": len(graded),
                "accuracy": passed / len(graded),
            }

    recall_totals: dict[str, dict[str, Any]] = {}
    for name in RECALLS:
        matched = sum(g.recalls[name].matched for g in ok if name in g.recalls)
        expected = sum(g.recalls[name].expected for g in ok if name in g.recalls)
        if expected:
            recall_totals[name] = {
                "matched": matched,
                "expected": expected,
                "recall": matched / expected,
            }

    # Consistency: how often the N runs of a case agreed with each other.
    consistency: dict[str, Any] = {}
    agreements: list[float] = []
    unanimous = 0
    for case_id, case_grades in _group(ok).items():
        tiers = [g.tier for g in case_grades if g.tier]
        if not tiers:
            continue
        modal = Counter(tiers).most_common(1)[0][1]
        ratio = modal / len(tiers)
        agreements.append(ratio)
        unanimous += int(ratio == 1.0)
        consistency[case_id] = {
            "tiers": tiers,
            "modal_agreement": ratio,
            "unanimous": ratio == 1.0,
        }

    matrix: dict[str, dict[str, int]] = {}
    for grade_ in ok:
        expected_tier = by_case[grade_.case_id].expect.tier
        if not expected_tier or not grade_.tier:
            continue
        matrix.setdefault(expected_tier, {}).setdefault(grade_.tier, 0)
        matrix[expected_tier][grade_.tier] += 1

    per_case: list[dict[str, Any]] = []
    for case in cases:
        case_grades = _group(grades).get(case.id, [])
        graded_checks = [c for g in case_grades if g.ok for c in g.checks]
        passed = sum(1 for c in graded_checks if c.passed)
        failures = Counter(c.field for g in case_grades if g.ok for c in g.failures)
        missing = sorted(
            {m for g in case_grades if g.ok for r in g.recalls.values() for m in r.missing}
        )
        per_case.append(
            {
                "case_id": case.id,
                "title": case.title,
                "tests": case.tests,
                "runs": len(case_grades),
                "errors": sum(1 for g in case_grades if not g.ok),
                "checks_passed": passed,
                "checks_graded": len(graded_checks),
                "pass_rate": passed / len(graded_checks) if graded_checks else None,
                "expected_tier": case.expect.tier,
                "tiers": [g.tier for g in case_grades if g.ok],
                "model_tiers": [g.model_tier for g in case_grades if g.ok],
                "failed_fields": dict(failures),
                "missing": missing,
            }
        )

    latencies = [g.latency_ms for g in ok]
    all_checks = [c for g in ok for c in g.checks]
    return {
        "runs": len(grades),
        "runs_ok": len(ok),
        "runs_errored": len(errored),
        "retries": sum(g.attempts - 1 for g in grades),
        "overall_accuracy": (
            sum(1 for c in all_checks if c.passed) / len(all_checks) if all_checks else None
        ),
        "checks_graded": len(all_checks),
        "field_accuracy": field_accuracy,
        "recall": recall_totals,
        "tier_consistency": {
            "mean_modal_agreement": statistics.fmean(agreements) if agreements else None,
            "unanimous_cases": unanimous,
            "cases": consistency,
        },
        "tier_confusion": matrix,
        "latency_ms": {
            "mean": int(statistics.fmean(latencies)) if latencies else 0,
            "p50": _percentile(latencies, 0.5),
            "p95": _percentile(latencies, 0.95),
            "min": min(latencies, default=0),
            "max": max(latencies, default=0),
        },
        "cost_usd": {
            "total": round(sum(g.cost_usd for g in ok), 4),
            "per_assessment": round(statistics.fmean([g.cost_usd for g in ok]), 5) if ok else 0.0,
        },
        "tokens": {
            "input": sum(g.input_tokens for g in ok),
            "output": sum(g.output_tokens for g in ok),
            "cache_read": sum(g.cache_read_tokens for g in ok),
            "cache_hit_rate": (
                sum(1 for g in ok if g.cache_read_tokens > 0) / len(ok) if ok else None
            ),
        },
        "per_case": per_case,
        "errors": [
            {"case_id": g.case_id, "run": g.run, "kind": g.error_kind, "error": g.error}
            for g in errored
        ],
        "errors_by_kind": dict(Counter(g.error_kind or "api" for g in errored)),
    }


def _group(grades: list[RunGrade]) -> dict[str, list[RunGrade]]:
    grouped: dict[str, list[RunGrade]] = {}
    for grade_ in grades:
        grouped.setdefault(grade_.case_id, []).append(grade_)
    return grouped
