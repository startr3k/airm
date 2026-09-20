"""Run one assessment: cached system prompt, forced tool call, then the policy layer.

The system prompt is read from `prompts/system.rendered.md` -- the file that is checked
into the repo -- so what you diff is exactly what runs. It carries the cache breakpoint,
and everything that varies per request comes after it.

Run:  python -m mindforge_assess.assessor "<description>" [--agentic] [--tool X] ...
"""

from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import Iterator
from functools import lru_cache
from typing import Any

import anthropic
from pydantic import ValidationError

from .config import Settings, get_settings
from .grounding import GroundingReport, Library, ground_names
from .llm import Usage as RawUsage
from .llm import call_tool, classify_api_error, get_client
from .models import Assessment, AssessRequest, AssessResponse, Usage
from .pack import Pack, load_pack
from .policy import apply_policy
from .prompts.build_system_prompt import RENDERED_PATH, build
from .schema import DIMENSION_KEYS, assessment_tool


class AssessmentError(RuntimeError):
    pass


# Adaptive thinking is billed from the same budget as the answer, and a long excursion
# at 16k truncated the tool call outright in two of thirty eval runs. A finished
# assessment is ~3k tokens, so this is deep headroom rather than a real limit.
MAX_TOKENS = 32_000


@lru_cache(maxsize=1)
def system_prompt() -> str:
    """The checked-in rendered prompt, so the cached prefix is byte-stable."""
    if RENDERED_PATH.is_file():
        return RENDERED_PATH.read_text()
    prompt = build()
    RENDERED_PATH.write_text(prompt)
    return prompt


def system_blocks() -> list[dict[str, Any]]:
    """The cache breakpoint sits at the end of the system prompt.

    Order is tools -> system -> messages, and the tool definition is identical on every
    request, so a breakpoint here covers both the tool schema and the framework prose --
    about 7k tokens that never need to be re-read.
    """
    return [
        {
            "type": "text",
            "text": system_prompt(),
            "cache_control": {"type": "ephemeral"},
        }
    ]


def user_content(request: AssessRequest) -> list[dict[str, Any]]:
    """Everything that varies per request, placed after the cache breakpoint."""
    lines = [
        "Assess this AI use case.",
        "",
        "## Description",
        request.description.strip(),
        "",
        "## Declared metadata",
    ]
    if request.deployment_pattern:
        lines.append(f"- Deployment pattern: {request.deployment_pattern}")
    lines.append(f"- Agentic system: {'yes' if request.is_agentic else 'not declared'}")
    if request.tools_accessible:
        lines.append(
            "- Tools the system can call: " + ", ".join(request.tools_accessible)
        )
    lines.append(f"- Customer-facing: {'yes' if request.customer_facing else 'not declared'}")
    lines += [
        "",
        "Metadata the submitter did not declare is unknown, not absent -- treat it as a "
        "gap to note rather than evidence of low risk.",
        "",
        "Call `record_risk_assessment` with your assessment.",
    ]
    return [{"type": "text", "text": "\n".join(lines)}]


def assess(
    request: AssessRequest,
    *,
    client: anthropic.Anthropic | None = None,
    settings: Settings | None = None,
    pack: Pack | None = None,
) -> AssessResponse:
    settings = settings or get_settings()
    pack = pack or load_pack()
    client = client or get_client(settings)
    model = request.model or settings.assess_model

    started = time.perf_counter()
    result = call_tool(
        client,
        model=model,
        tool=assessment_tool(),
        content=user_content(request),
        system=system_blocks(),
        effort=settings.assess_effort,
        max_tokens=MAX_TOKENS,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    data, cleaning_notes = _sanitise(result.data)
    data, grounding = _ground(data, pack)
    cleaning_notes.extend(grounding.notes())
    try:
        assessment = Assessment.model_validate(data)
    except ValidationError as exc:
        raise AssessmentError(
            f"The model's tool call did not match the assessment schema: {exc}"
        ) from exc
    for note in cleaning_notes:
        assessment.assessor_notes = f"{assessment.assessor_notes.rstrip()}\n\n{note}"

    adjusted, overrides = apply_policy(assessment, request)
    return AssessResponse(
        assessment=adjusted,
        policy_overrides=overrides,
        model=model,
        usage=_usage(result.usage),
        latency_ms=latency_ms,
        assessment_id=uuid.uuid4().hex[:16],
        pack_version=pack.version,
        pdf_sha256=pack.pdf_sha256,
    )


def _sanitise(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Repair the few things a strict schema cannot express, transparently.

    Strict tool use rejects `minimum`/`maximum` on integers, so the 1-17 bound on
    Consideration numbers is only an instruction. Rather than fail the whole assessment
    over an out-of-range number, drop it and say so in the notes.
    """
    cleaned = dict(data)
    notes: list[str] = []
    if "risk_dimensions" in cleaned:
        cleaned["risk_dimensions"] = _dimension_list(
            cleaned["risk_dimensions"], cleaned.pop("key_risks", None)
        )
    cleaned.pop("key_risks", None)

    numbers = cleaned.get("relevant_considerations")
    if isinstance(numbers, list):
        valid = [n for n in numbers if isinstance(n, int) and 1 <= n <= 17]
        dropped = [n for n in numbers if n not in valid]
        # Preserve order, drop duplicates.
        deduped = list(dict.fromkeys(valid))
        if dropped:
            notes.append(
                f"NOTE: the model cited Consideration number(s) {dropped}, which do not "
                f"exist (Appendix H has 1-17). They were dropped."
            )
        cleaned["relevant_considerations"] = deduped

    return cleaned, notes


def _dimension_list(value: Any, key_risks: Any = None) -> Any:
    """Rebuild the ordered list of seven dimensions from the tool's two fields.

    The tool schema splits them -- seven required object keys for the ratings, one flat
    array for the named risks -- for reasons that are purely about what a strict schema
    can express and how large a grammar the API will compile. Nothing downstream (the
    models, the policy layer, the stored records, the front end) should have to know
    that, so the two are merged back here.
    """
    if not isinstance(value, dict):
        return value

    risks: dict[str, list[str]] = {}
    if isinstance(key_risks, list):
        for item in key_risks:
            if isinstance(item, dict) and item.get("risk"):
                risks.setdefault(str(item.get("dimension")), []).append(str(item["risk"]))

    ordered: list[dict[str, Any]] = []
    for key, name in DIMENSION_KEYS.items():
        entry = value.get(key)
        if isinstance(entry, dict):
            ordered.append({"dimension": name, "key_risks": risks.get(name, []), **entry})
    return ordered


def _ground(data: dict[str, Any], pack: Pack) -> tuple[dict[str, Any], GroundingReport]:
    """Match every cited name back to the pack so a citation can reach a page."""
    report = GroundingReport()
    cleaned = dict(data)

    libraries = {
        "recommended_metrics": (Library(pack.metric_names()), "metric"),
        "top_10_flags": (Library(pack.abs_top_10()), "ABS top-10 risk"),
    }
    for field_name, (library, label) in libraries.items():
        values = cleaned.get(field_name)
        if isinstance(values, list):
            cleaned[field_name] = ground_names(
                [str(v) for v in values], library, label, report
            )

    guardrails = cleaned.get("recommended_guardrails")
    if isinstance(guardrails, list):
        library = Library(pack.guardrail_names())
        grounded: list[dict[str, Any]] = []
        for item in guardrails:
            if not isinstance(item, dict):
                continue
            name = str(item.get("guardrail", ""))
            resolved, corrected = library.resolve(name)
            if resolved is None:
                report.unmatched.append(("guardrail", name))
            else:
                if corrected:
                    report.corrected.append(("guardrail", name, resolved))
                item = {**item, "guardrail": resolved}
            grounded.append(item)
        cleaned["recommended_guardrails"] = grounded

    return cleaned, report


def _usage(raw: RawUsage) -> Usage:
    return Usage(
        input_tokens=raw.input_tokens,
        output_tokens=raw.output_tokens,
        cache_creation_input_tokens=raw.cache_creation_input_tokens,
        cache_read_input_tokens=raw.cache_read_input_tokens,
    )


def summarise(response: AssessResponse) -> str:
    """A compact human-readable digest, for the CLI and for eval output."""
    a = response.assessment
    lines = [
        f"{a.use_case_summary}",
        "",
        f"  in scope    {a.ai_in_scope}",
        f"  ai_type     {a.ai_type}",
        f"  tier        {a.inherent_risk_tier.upper()}   confidence {a.confidence}",
        f"  oversight   {a.recommended_oversight_mode}",
        f"  top-10      {', '.join(a.top_10_flags) or '—'}",
        f"  considerations {a.relevant_considerations}",
    ]
    if a.risk_dimensions:
        lines.append("  dimensions:")
        for d in a.risk_dimensions:
            lines.append(f"    {d.rating.upper():<7} {d.dimension}")
    if response.policy_overrides:
        lines.append(f"  POLICY OVERRIDES ({len(response.policy_overrides)}):")
        for o in response.policy_overrides:
            lines.append(f"    [{o.rule}] {o.field}: {o.before!r} -> {o.after!r}")
    u = response.usage
    lines += [
        "",
        f"  {response.model}  {response.latency_ms} ms",
        f"  tokens: in={u.input_tokens} out={u.output_tokens} "
        f"cache_write={u.cache_creation_input_tokens} cache_read={u.cache_read_input_tokens}"
        f"{'  (CACHE HIT)' if u.cache_hit else ''}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from .config import ConfigError

    parser = argparse.ArgumentParser(description="Assess one AI use case.")
    parser.add_argument("description", help="plain-English description of the use case")
    parser.add_argument("--agentic", action="store_true")
    parser.add_argument("--customer-facing", action="store_true")
    parser.add_argument("--tool", action="append", default=[], dest="tools")
    parser.add_argument(
        "--deployment", choices=["build", "onboard", "onboard_with_customisation"]
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--json", action="store_true", help="print the full JSON response")
    args = parser.parse_args(argv)

    try:
        response = assess(
            AssessRequest(
                description=args.description,
                deployment_pattern=args.deployment,
                is_agentic=args.agentic,
                tools_accessible=args.tools,
                customer_facing=args.customer_facing,
                model=args.model,
            )
        )
    except (ConfigError, AssessmentError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))
    else:
        print(summarise(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# --------------------------------------------------------------------- streaming

# The assessor's own field order, mapped to something a person can read. Because the
# schema is emitted in order, the arrival of a key is genuine evidence of progress --
# these steps are read off the stream, not played back on a timer.
STREAM_STEPS: tuple[tuple[str, str], ...] = (
    ("use_case_summary", "Reading the use case"),
    ("ai_in_scope", "Checking scope under Section 1.1"),
    ("ai_type", "Classifying the AI type"),
    ("materiality_factors", "Rating materiality factors"),
    ("inherent_risk_tier", "Choosing the inherent risk tier"),
    ("risk_dimensions", "Rating the seven risk dimensions"),
    ("top_10_flags", "Flagging ABS top-10 risks"),
    ("recommended_oversight_mode", "Selecting the oversight mode"),
    ("recommended_guardrails", "Recommending guardrails"),
    ("recommended_metrics", "Recommending metrics"),
    ("agentic_considerations", "Assessing agentic controls"),
    ("relevant_considerations", "Mapping to the 17 Considerations"),
    ("confidence", "Judging confidence"),
    ("assessor_notes", "Writing reviewer notes"),
)

_KEY_PATTERN = re.compile(r'"([a-z_0-9]+)"\s*:')


def _steps_seen(buffer: str, already: set[str]) -> list[tuple[str, str]]:
    """Which named steps have appeared in the partial JSON since we last looked."""
    present = set(_KEY_PATTERN.findall(buffer))
    return [
        (key, label)
        for key, label in STREAM_STEPS
        if key in present and key not in already
    ]


def assess_stream(
    request: AssessRequest,
    *,
    client: anthropic.Anthropic | None = None,
    settings: Settings | None = None,
    pack: Pack | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (event, payload) pairs for Server-Sent Events.

    Statuses come from the model's own output as it is generated, so the stepper in the
    UI reflects what is actually happening rather than an animation.
    """
    settings = settings or get_settings()
    pack = pack or load_pack()
    client = client or get_client(settings)
    model = request.model or settings.assess_model
    # Without eager input streaming the server buffers the tool input and flushes it in
    # chunks, so progress events land in bursts at flush boundaries rather than as the
    # model generates. Measured on this prompt: a 76-second gap where the stepper looked
    # frozen, against ~10-second steps with it on. Either way the input is reassembled
    # client-side by a tolerant parser, so a truncated response returns a plausible dict
    # rather than raising -- hence the stop-reason check and the validation below.
    tool = {**assessment_tool(), "eager_input_streaming": True}

    yield "status", {"step": "framework", "label": "Loading the framework pack", "done": True}
    started = time.perf_counter()

    buffer = ""
    seen: set[str] = set()
    message: Any = None

    # Assembled as a plain dict, the same way `llm.call_tool` does it. The request
    # carries things the SDK's TypedDicts do not describe -- `eager_input_streaming` on
    # the tool, `cache_control` on a system block -- so casting to them would assert a
    # shape that is deliberately wider than they allow.
    stream_kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": settings.assess_effort},
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": tool["name"]},
        "system": system_blocks(),
        "messages": [{"role": "user", "content": user_content(request)}],
    }

    try:
        with client.messages.stream(**stream_kwargs) as stream:
            for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "input_json_delta":
                    buffer += event.delta.partial_json
                    for key, label in _steps_seen(buffer, seen):
                        seen.add(key)
                        yield "status", {"step": key, "label": label, "done": True}
            message = stream.get_final_message()
    except anthropic.APIStatusError as exc:
        terminal = classify_api_error(exc)
        yield "error", {"detail": str(terminal) if terminal else str(exc)}
        return

    latency_ms = int((time.perf_counter() - started) * 1000)

    if message.stop_reason == "refusal":
        yield "error", {"detail": "The request was refused by the API."}
        return
    if message.stop_reason == "max_tokens":
        # With eager streaming the SDK's tolerant parser returns what it has rather than
        # raising, so a truncated assessment would otherwise look like a valid one.
        yield "error", {
            "detail": "The assessment was cut off at max_tokens. Try a shorter description."
        }
        return

    payload: dict[str, Any] | None = None
    for block in message.content:
        if block.type == "tool_use" and block.name == tool["name"]:
            try:
                payload = json.loads(json.dumps(block.input))
            except (TypeError, ValueError):
                yield "error", {"detail": "The streamed assessment was not valid JSON."}
                return
    if payload is None:
        yield "error", {"detail": "The model did not return an assessment."}
        return

    yield "status", {
        "step": "policy",
        "label": "Applying the policy layer",
        "done": True,
    }

    data, notes = _sanitise(payload)
    data, grounding = _ground(data, pack)
    notes.extend(grounding.notes())
    try:
        assessment = Assessment.model_validate(data)
    except ValidationError as exc:
        yield "error", {"detail": f"The assessment did not match the schema: {exc}"}
        return
    for note in notes:
        assessment.assessor_notes = f"{assessment.assessor_notes.rstrip()}\n\n{note}"

    adjusted, overrides = apply_policy(assessment, request)
    usage = RawUsage()
    usage.add(message.usage)
    response = AssessResponse(
        assessment=adjusted,
        policy_overrides=overrides,
        model=model,
        usage=_usage(usage),
        latency_ms=latency_ms,
        assessment_id=uuid.uuid4().hex[:16],
        pack_version=pack.version,
        pdf_sha256=pack.pdf_sha256,
    )
    yield "result", response.model_dump()
