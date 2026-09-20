"""Deterministic conservative defaults applied after the model answers.

The model is good but not reliable enough to be the only safeguard on the cases that
matter most, and with `temperature` unavailable on these models its answer is not even
reproducible run to run. So the rules that must always hold live here, in code, where
they are testable without an API key and cannot drift with a prompt change.

Nothing here silently rewrites the answer: every adjustment is returned as a
`PolicyOverride` recording the rule, the field, the before and after values, and why --
so the UI can show "the model said X, the policy layer said Y".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .models import (
    AgenticConsiderations,
    Assessment,
    AssessRequest,
    PolicyOverride,
)

# --------------------------------------------------------------------- patterns


@dataclass(frozen=True)
class Domain:
    """A use-case domain whose inherent risk is floored at 'high' regardless of model."""

    key: str
    label: str
    pattern: re.Pattern[str]
    never_delegate: str | None = None


_SEPARATORS = re.compile(r"[_\-./\\:]+")


def normalise(text: str) -> str:
    """Make identifier-style text matchable.

    Tool names arrive as `send_payment` or `execute-trade`. Underscores and hyphens are
    word characters to `re`, so `\bpayment\b` does not match inside `send_payment`.
    Flattening the separators to spaces lets one set of patterns cover prose and
    identifiers alike.
    """
    return _SEPARATORS.sub(" ", text)


def _p(*alternatives: str) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(alternatives) + r")\b", re.IGNORECASE)


HIGH_RISK_DOMAINS: tuple[Domain, ...] = (
    Domain(
        "credit_lending",
        "credit or lending decisions",
        _p(
            r"credit (?:decisions?|scor\w*|risk|limits?|assessments?|approvals?|decisioning)",
            r"creditworthiness",
            r"loan (?:approvals?|decisions?|applications?|underwrit\w*|origination)",
            r"lending (?:decisions?|criteria)",
            r"mortgage (?:approvals?|decisions?|underwrit\w*)",
            r"(?:approve|decline|reject)\w* (?:a )?(?:loan|credit|mortgage)",
        ),
        never_delegate="Approving or declining credit",
    ),
    Domain(
        "insurance_underwriting",
        "insurance underwriting or pricing",
        _p(
            r"insurance underwrit\w*",
            r"underwrit\w* (?:a )?(?:polic\w+|insurance|risk)",
            r"premiums? (?:pricing|setting|calculations?|determination)",
            r"polic\w+ pricing",
            r"actuarial pricing",
            r"rat(?:e|ing) (?:an )?insurance",
        ),
        never_delegate="Setting insurance premiums or underwriting decisions",
    ),
    Domain(
        "employment",
        "employment or hiring decisions",
        _p(
            r"hiring",
            r"recruit\w*",
            r"candidate (?:screen\w*|rank\w*|select\w*|shortlist\w*)",
            r"(?:resum|cv|c\.v\.)\w* (?:screen\w*|scor\w*|rank\w*|filter\w*|pars\w*)",
            r"employment decisions?",
            r"job applicants?",
            r"promotion decisions?",
            r"(?:terminat\w*|dismiss\w*|fir\w+) (?:an )?employee",
            r"performance (?:reviews?|appraisals?) (?:decisions?|outcomes?)",
        ),
        never_delegate="Making employment decisions",
    ),
    Domain(
        "biometric",
        "biometric identification",
        _p(
            r"biometric\w*",
            r"fac(?:e|ial) (?:recognition|matching|verification|identification)",
            r"fingerprints?",
            r"voice ?print\w*",
            r"iris scan\w*",
            r"liveness (?:check|detection)",
        ),
        never_delegate="Identifying a person from biometrics without human confirmation",
    ),
    Domain(
        "autonomous_transactions",
        "autonomous execution of financial transactions",
        _p(
            r"execut\w* (?:a )?(?:trade|transaction|payment|order|deal)s?",
            r"trade execution",
            r"plac\w* (?:an? )?(?:order|trade)s?",
            r"initiat\w* (?:a )?(?:payment|transfer|wire|remittance)s?",
            r"transfer\w* funds?",
            r"mov\w* money",
            r"auto\w*[ -]?(?:execut\w*|trad\w*)",
            r"settle\w* (?:a )?trades?",
        ),
        never_delegate="Authorising financial transactions",
    ),
)


@dataclass(frozen=True)
class ToolHazard:
    key: str
    label: str
    pattern: re.Pattern[str]
    never_delegate: str


TOOL_HAZARDS: tuple[ToolHazard, ...] = (
    ToolHazard(
        "spends_money",
        "spends money or moves funds",
        _p(
            r"payment\w*", r"pay", r"purchas\w*", r"buy", r"invoic\w*", r"billing",
            r"checkout", r"refund\w*", r"disburs\w*", r"transfer\w*", r"wire",
            r"trade\w*", r"trading", r"order\w*", r"broker\w*", r"settle\w*",
            r"card", r"treasury", r"payout\w*",
        ),
        never_delegate="Authorising financial transactions",
    ),
    ToolHazard(
        "external_comms",
        "sends communications outside the firm",
        _p(
            r"e-?mail\w*", r"sms", r"messag\w*", r"notif\w*", r"send", r"publish\w*",
            r"post\w*", r"slack", r"teams", r"whatsapp", r"chat", r"call",
            r"correspond\w*", r"outreach", r"broadcast\w*",
        ),
        never_delegate="Sending external communications to customers without review",
    ),
    ToolHazard(
        "production_writes",
        "writes to production systems",
        _p(
            r"writ\w*", r"updat\w*", r"delet\w*", r"insert\w*", r"modif\w*", r"creat\w*",
            r"crm", r"database", r"db", r"ledger", r"core banking", r"booking",
            r"deploy\w*", r"provision\w*", r"production", r"record\w*", r"system of record",
        ),
        never_delegate="Writing to systems of record without human confirmation",
    ),
)

DEFAULT_INTERRUPTION_CONTROL = (
    "Kill switch: an operator must be able to deactivate this agent immediately, "
    "with a defined owner and escalation path (handbook s.3.4)."
)


# ------------------------------------------------------------------- detection


def _haystack(request: AssessRequest) -> str:
    """Rules read the user's own words plus the declared tools, never the model's."""
    return normalise(" \n ".join([request.description, *request.tools_accessible]))


def detect_domains(request: AssessRequest) -> list[Domain]:
    text = _haystack(request)
    return [domain for domain in HIGH_RISK_DOMAINS if domain.pattern.search(text)]


def detect_tool_hazards(request: AssessRequest) -> list[ToolHazard]:
    """Hazards are matched against declared tools; the description alone is too loose."""
    if not request.tools_accessible:
        return []
    text = normalise(" \n ".join(request.tools_accessible))
    return [hazard for hazard in TOOL_HAZARDS if hazard.pattern.search(text)]


def _is_agentic(assessment: Assessment, request: AssessRequest) -> bool:
    return bool(request.is_agentic or assessment.ai_type == "agentic")


def _append_note(assessment: Assessment, line: str) -> None:
    existing = assessment.assessor_notes.rstrip()
    assessment.assessor_notes = f"{existing}\n\n{line}" if existing else line


_TIER_ORDER = {"low": 0, "medium": 1, "high": 2}


# ----------------------------------------------------------------------- rules


def apply_policy(
    assessment: Assessment, request: AssessRequest
) -> tuple[Assessment, list[PolicyOverride]]:
    """Apply the conservative defaults. Returns the adjusted assessment and the record."""
    result = assessment.model_copy(deep=True)
    overrides: list[PolicyOverride] = []

    # Rule 3 runs first: if this is not AI under Section 1.1, the rest of the analysis
    # is not just unnecessary but misleading, so it is cleared rather than shown.
    if not result.ai_in_scope:
        overrides.extend(_short_circuit_out_of_scope(result))
        return result, overrides

    overrides.extend(_floor_high_risk_domains(result, request))
    overrides.extend(_require_agentic_controls(result, request))
    return result, overrides


def _short_circuit_out_of_scope(result: Assessment) -> list[PolicyOverride]:
    overrides: list[PolicyOverride] = []
    cleared: dict[str, Any] = {
        "risk_dimensions": [],
        "recommended_guardrails": [],
        "recommended_metrics": [],
        "top_10_flags": [],
        "relevant_considerations": [],
        "agentic_considerations": None,
    }
    for field, empty in cleared.items():
        before = getattr(result, field)
        if before in (empty, None) or (isinstance(before, list) and not before):
            continue
        setattr(result, field, empty)
        overrides.append(
            PolicyOverride(
                rule="out_of_scope_short_circuit",
                field=field,
                before=_summarise(before),
                after=_summarise(empty),
                reason=(
                    "The use case does not meet the Section 1.1 definition of AI, so a "
                    "full AI risk assessment does not apply and would be misleading. "
                    "The handbook's other risk frameworks still apply to it."
                ),
            )
        )
    if overrides:
        _append_note(
            result,
            "POLICY: assessed as out of scope for the AI framework under Section 1.1. "
            "The detailed AI risk analysis has been withheld. Confirm the system really "
            "is purely rule-based -- if any component learns or infers, it is in scope.",
        )
    return overrides


def _floor_high_risk_domains(
    result: Assessment, request: AssessRequest
) -> list[PolicyOverride]:
    domains = detect_domains(request)
    if not domains:
        return []

    labels = ", ".join(domain.label for domain in domains)
    overrides: list[PolicyOverride] = []

    if _TIER_ORDER[result.inherent_risk_tier] < _TIER_ORDER["high"]:
        before = result.inherent_risk_tier
        result.inherent_risk_tier = "high"
        overrides.append(
            PolicyOverride(
                rule="high_risk_domain_floor",
                field="inherent_risk_tier",
                before=before,
                after="high",
                reason=(
                    f"The description involves {labels}. The policy layer floors inherent "
                    f"risk materiality at 'high' for these domains regardless of the "
                    f"model's rating, because the impact on individuals, the limited "
                    f"options for recourse and the regulatory exposure are severe by "
                    f"nature (Section 2.4)."
                ),
            )
        )
        _append_note(
            result,
            f"POLICY: inherent risk tier raised from '{before}' to 'high' because the "
            f"use case involves {labels}. Check whether the model's lower rating "
            f"reflects something the policy layer cannot see, and record the rationale "
            f"either way.",
        )
    return overrides


def _require_agentic_controls(
    result: Assessment, request: AssessRequest
) -> list[PolicyOverride]:
    if not _is_agentic(result, request):
        return []
    hazards = detect_tool_hazards(request)
    if not hazards:
        return []

    overrides: list[PolicyOverride] = []
    hazard_labels = ", ".join(hazard.label for hazard in hazards)

    if result.agentic_considerations is None:
        result.agentic_considerations = AgenticConsiderations(
            tool_access_risk=(
                f"The agent can reach tools that {hazard_labels}. Every such tool is a "
                f"path to an irreversible action taken without a human in the loop."
            ),
            least_privilege_recommendations=[],
            interruption_controls=[],
            never_delegate_flags=[],
        )
        overrides.append(
            PolicyOverride(
                rule="agentic_analysis_required",
                field="agentic_considerations",
                before=None,
                after="created",
                reason=(
                    f"The use case is agentic and its tools {hazard_labels}, but the "
                    f"model returned no agentic analysis."
                ),
            )
        )

    agentic = result.agentic_considerations
    assert agentic is not None

    if not agentic.interruption_controls:
        before = list(agentic.interruption_controls)
        agentic.interruption_controls = [DEFAULT_INTERRUPTION_CONTROL]
        overrides.append(
            PolicyOverride(
                rule="interruption_control_required",
                field="agentic_considerations.interruption_controls",
                before=before,
                after=agentic.interruption_controls,
                reason=(
                    f"An agent with tools that {hazard_labels} must have at least one "
                    f"way to be stopped. The model proposed none, so a kill switch is "
                    f"added as the minimum."
                ),
            )
        )

    existing = {flag.strip().casefold() for flag in agentic.never_delegate_flags}
    added: list[str] = []
    for hazard in hazards:
        if hazard.never_delegate.casefold() not in existing:
            added.append(hazard.never_delegate)
            existing.add(hazard.never_delegate.casefold())
    for domain in detect_domains(request):
        if domain.never_delegate and domain.never_delegate.casefold() not in existing:
            added.append(domain.never_delegate)
            existing.add(domain.never_delegate.casefold())

    if added:
        before = list(agentic.never_delegate_flags)
        agentic.never_delegate_flags = [*before, *added]
        overrides.append(
            PolicyOverride(
                rule="never_delegate_flag",
                field="agentic_considerations.never_delegate_flags",
                before=before,
                after=agentic.never_delegate_flags,
                reason=(
                    "Accountability follows control: these actions carry consequences "
                    "the firm cannot unwind, so they require a human decision rather "
                    "than agent autonomy (Future Perspectives)."
                ),
            )
        )

    if overrides:
        _append_note(
            result,
            f"POLICY: this agent's tools {hazard_labels}. Confirm the interruption "
            f"controls and never-delegate boundaries listed are actually implemented, "
            f"and that tool permissions are scoped to the minimum needed.",
        )
    return overrides


def _summarise(value: Any) -> Any:
    """Keep override records readable when the 'before' value was a large list."""
    if isinstance(value, list):
        return f"{len(value)} item(s)" if value else []
    return value
