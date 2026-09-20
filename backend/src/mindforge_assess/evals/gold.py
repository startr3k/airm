"""The gold set: hand-written use cases and what a correct assessment must say.

Every expectation is deliberately partial. Nobody can write the "one true" list of
guardrails for a use case, so the gold set grades only the things the handbook actually
settles: scope, type, tier, oversight mode, whether specific dimensions are rated at
least as high as they must be, and whether the risks and Considerations that genuinely
apply were cited. Fields that are a matter of judgement are left ungraded rather than
scored against one analyst's opinion.

Ungraded fields are *absent* from a case's `expect` block, not null -- so adding a new
expectation to one case never silently penalises the other nine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import EVALS_DIR
from ..models import AssessRequest
from ..pack import Pack, load_pack

GOLD_PATH = EVALS_DIR / "gold.jsonl"

RATING_ORDER = {"low": 0, "medium": 1, "high": 2}


class GoldSetError(RuntimeError):
    """The gold set does not agree with the framework pack or the schema."""


@dataclass(frozen=True)
class Expectation:
    ai_in_scope: bool | None = None
    ai_type: str | None = None
    tier: str | None = None
    tier_accepted: tuple[str, ...] = ()
    oversight_modes: tuple[str, ...] = ()
    max_confidence: str | None = None
    min_dimension_ratings: dict[str, str] = field(default_factory=dict)
    top_10_flags: tuple[str, ...] = ()
    considerations: tuple[int, ...] = ()
    policy_rules: tuple[str, ...] = ()
    agentic_analysis_required: bool | None = None
    empty_risk_analysis: bool = False

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> Expectation:
        unknown = set(raw) - {f for f in cls.__dataclass_fields__}
        if unknown:
            raise GoldSetError(f"unknown expectation key(s): {sorted(unknown)}")
        return cls(
            ai_in_scope=raw.get("ai_in_scope"),
            ai_type=raw.get("ai_type"),
            tier=raw.get("tier"),
            tier_accepted=tuple(raw.get("tier_accepted", ())),
            oversight_modes=tuple(raw.get("oversight_modes", ())),
            max_confidence=raw.get("max_confidence"),
            min_dimension_ratings=dict(raw.get("min_dimension_ratings", {})),
            top_10_flags=tuple(raw.get("top_10_flags", ())),
            considerations=tuple(raw.get("considerations", ())),
            policy_rules=tuple(raw.get("policy_rules", ())),
            agentic_analysis_required=raw.get("agentic_analysis_required"),
            empty_risk_analysis=bool(raw.get("empty_risk_analysis", False)),
        )

    @property
    def accepted_tiers(self) -> tuple[str, ...]:
        """Tiers that count as correct. Defaults to the single expected tier."""
        if self.tier_accepted:
            return self.tier_accepted
        return (self.tier,) if self.tier else ()


@dataclass(frozen=True)
class GoldCase:
    id: str
    title: str
    tests: str
    request: AssessRequest
    expect: Expectation

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> GoldCase:
        return cls(
            id=str(raw["id"]),
            title=str(raw["title"]),
            tests=str(raw["tests"]),
            request=AssessRequest.model_validate(raw["request"]),
            expect=Expectation.from_json(dict(raw.get("expect", {}))),
        )


def load_gold(path: Path | None = None) -> list[GoldCase]:
    source = path or GOLD_PATH
    if not source.is_file():
        raise GoldSetError(f"{source} not found.")
    cases: list[GoldCase] = []
    for number, line in enumerate(source.read_text().splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        try:
            cases.append(GoldCase.from_json(json.loads(line)))
        except Exception as exc:  # noqa: BLE001 - re-raised with the line number
            raise GoldSetError(f"{source.name} line {number}: {exc}") from exc

    seen = [case.id for case in cases]
    duplicates = {i for i in seen if seen.count(i) > 1}
    if duplicates:
        raise GoldSetError(f"duplicate case id(s): {sorted(duplicates)}")
    return cases


def validate_gold(cases: list[GoldCase], pack: Pack | None = None) -> list[str]:
    """Check every expectation against the pack, so a typo fails fast rather than
    silently scoring zero for the rest of the project's life."""
    pack = pack or load_pack()
    dimensions = {d["dimension"] for d in pack.dimensions}
    top_10 = set(pack.abs_top_10())
    consideration_numbers = {int(c["number"]) for c in pack.considerations}
    modes = {str(m["mode"]) for m in pack.oversight_modes}
    problems: list[str] = []

    for case in cases:
        e = case.expect
        where = f"{case.id}:"
        for rating in (e.tier, *e.tier_accepted, e.max_confidence):
            if rating is not None and rating not in RATING_ORDER:
                problems.append(f"{where} {rating!r} is not a rating")
        if e.tier and e.tier_accepted and e.tier not in e.tier_accepted:
            problems.append(f"{where} expected tier {e.tier!r} is not in tier_accepted")
        if e.ai_type is not None and e.ai_type not in ("traditional", "gen_ai", "agentic"):
            problems.append(f"{where} {e.ai_type!r} is not an ai_type")
        for mode in e.oversight_modes:
            if mode not in modes:
                problems.append(f"{where} {mode!r} is not an oversight mode in the pack")
        for name, rating in e.min_dimension_ratings.items():
            if name not in dimensions:
                problems.append(f"{where} {name!r} is not a dimension in the pack")
            if rating not in RATING_ORDER:
                problems.append(f"{where} {name}: {rating!r} is not a rating")
        for flag in e.top_10_flags:
            if flag not in top_10:
                problems.append(f"{where} {flag!r} is not an ABS top-10 risk in the pack")
        for number in e.considerations:
            if number not in consideration_numbers:
                problems.append(f"{where} Consideration {number} does not exist")
    return problems
