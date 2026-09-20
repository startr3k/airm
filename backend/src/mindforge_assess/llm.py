"""Thin wrapper over the Anthropic Python SDK.

Three API facts drive the shape of this module, all verified against docs.claude.com
rather than assumed:

1.  `temperature` / `top_p` / `top_k` return a 400 on claude-opus-5 and claude-sonnet-5
    "regardless of whether thinking is used". There is no sampling knob to pin to 0.
    Determinism comes from forced `tool_choice` plus a strict schema instead.
2.  Forced tool use (`tool_choice={"type": "tool"}`) is incompatible with *manual*
    extended thinking, but works with *adaptive* thinking. `budget_tokens` is rejected
    with a 400 on both models; depth is set via `output_config.effort`.
3.  The Files API is out of beta: `client.files.upload`, and a `document` block with
    `source={"type": "file", "file_id": ...}` needs no beta header.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anthropic

from .config import Settings, get_settings, sha256_file

# USD per million tokens. Cache writes bill at 1.25x input, cache reads at 0.1x input.
PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


@dataclass
class Usage:
    """Token accounting for one or more API calls."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    calls: int = 0
    latency_ms: int = 0

    def add(self, raw: Any) -> None:
        self.calls += 1
        self.input_tokens += getattr(raw, "input_tokens", 0) or 0
        self.output_tokens += getattr(raw, "output_tokens", 0) or 0
        self.cache_creation_input_tokens += getattr(raw, "cache_creation_input_tokens", 0) or 0
        self.cache_read_input_tokens += getattr(raw, "cache_read_input_tokens", 0) or 0

    def merge(self, other: Usage) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_creation_input_tokens += other.cache_creation_input_tokens
        self.cache_read_input_tokens += other.cache_read_input_tokens
        self.calls += other.calls
        self.latency_ms += other.latency_ms

    @property
    def total_input_tokens(self) -> int:
        """Every input token billed: fresh, cache writes and cache reads."""
        return (
            self.input_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
        )

    def cost_usd(self, model: str) -> float:
        rate_in, rate_out = PRICING.get(model, (0.0, 0.0))
        return (
            self.input_tokens * rate_in
            + self.cache_creation_input_tokens * rate_in * 1.25
            + self.cache_read_input_tokens * rate_in * 0.1
            + self.output_tokens * rate_out
        ) / 1_000_000

    def as_dict(self, model: str | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "calls": self.calls,
            "latency_ms": self.latency_ms,
        }
        if model:
            out["estimated_cost_usd"] = round(self.cost_usd(model), 4)
        return out


@dataclass
class ToolCallResult:
    """The parsed input of a forced tool call, plus accounting."""

    data: dict[str, Any]
    usage: Usage
    model: str
    stop_reason: str | None = None
    thinking: list[str] = field(default_factory=list)


class ToolNotCalledError(RuntimeError):
    """The model returned without emitting the forced tool call."""


class OutputTruncatedError(RuntimeError):
    """The response hit `max_tokens` before the tool call was finished.

    This is the failure mode that looks like a success. Every request here is streamed,
    and a streamed tool input is reassembled client-side from `input_json_delta` chunks
    with a *tolerant* parser -- so a cut-off response does not raise, it yields a dict
    that is plausible but wrong: a half-written array arrives as the string `'["'`, and
    every field after it is simply absent. The stop reason is the only reliable signal,
    which is why it is checked before the input is read.
    """


class ApiUnavailableError(RuntimeError):
    """The API rejected the request for a reason retrying will not fix.

    Credit exhaustion and bad credentials both surface as a 400/401 that would
    otherwise abort a long ingestion run with a raw traceback, discarding the
    extractors that had already succeeded.
    """


def classify_api_error(exc: Exception) -> ApiUnavailableError | None:
    """Turn a terminal API error into something the CLI can report cleanly."""
    message = str(getattr(exc, "message", "") or exc)
    lowered = message.lower()
    if "credit balance is too low" in lowered:
        return ApiUnavailableError(
            "The Anthropic API rejected the request: credit balance is too low. "
            "Top up at console.anthropic.com (Plans & Billing), then re-run -- "
            "extractions already on disk are kept and will not be repeated."
        )
    if "authentication" in lowered or "invalid x-api-key" in lowered:
        return ApiUnavailableError(
            "The Anthropic API rejected the credentials. Check ANTHROPIC_API_KEY "
            "in backend/.env."
        )
    return None


def get_client(settings: Settings | None = None) -> anthropic.Anthropic:
    settings = settings or get_settings()
    return anthropic.Anthropic(api_key=settings.require_api_key())


def upload_pdf(client: anthropic.Anthropic, path: Path) -> str:
    """Upload a PDF to the Files API and return its file_id."""
    uploaded = client.files.upload(
        file=(path.name, path.open("rb"), "application/pdf"),
    )
    return str(uploaded.id)


def document_block(
    file_id: str,
    *,
    title: str | None = None,
    context: str | None = None,
    cache: bool = True,
) -> dict[str, Any]:
    """A `document` content block referencing an uploaded PDF, cached by default."""
    block: dict[str, Any] = {
        "type": "document",
        "source": {"type": "file", "file_id": file_id},
    }
    if title:
        block["title"] = title
    if context:
        block["context"] = context
    if cache:
        block["cache_control"] = {"type": "ephemeral"}
    return block


def call_tool(
    client: anthropic.Anthropic,
    *,
    model: str,
    tool: dict[str, Any],
    content: list[dict[str, Any]],
    system: str | list[dict[str, Any]] | None = None,
    effort: str = "high",
    max_tokens: int = 32_000,
) -> ToolCallResult:
    """Make one request that is forced to answer by calling `tool`, and parse its input.

    Note the deliberate absences: no `temperature` (400 on these models) and no
    `budget_tokens` (also 400). Adaptive thinking plus forced tool choice is a
    supported combination.
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": effort},
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": tool["name"]},
        "messages": [{"role": "user", "content": content}],
    }
    if system is not None:
        kwargs["system"] = system

    started = time.perf_counter()
    try:
        with client.messages.stream(**kwargs) as stream:
            message = stream.get_final_message()
    except anthropic.APIStatusError as exc:
        terminal = classify_api_error(exc)
        if terminal is not None:
            raise terminal from exc
        raise
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    usage = Usage(latency_ms=elapsed_ms)
    usage.add(message.usage)

    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        raise ToolNotCalledError(f"Request was refused: {details}")

    if message.stop_reason == "max_tokens":
        raise OutputTruncatedError(
            f"The response was cut off at max_tokens ({max_tokens:,}) before "
            f"{tool['name']!r} was complete. Thinking counts towards this budget."
        )

    thinking: list[str] = []
    for block in message.content:
        if block.type == "thinking" and block.thinking:
            thinking.append(block.thinking)
        if block.type == "tool_use" and block.name == tool["name"]:
            # Tool inputs are already decoded by the SDK, but round-trip through JSON
            # so callers always get plain dicts/lists rather than SDK model objects.
            data = json.loads(json.dumps(block.input))
            return ToolCallResult(
                data=data,
                usage=usage,
                model=model,
                stop_reason=message.stop_reason,
                thinking=thinking,
            )

    raise ToolNotCalledError(
        f"Model stopped with {message.stop_reason!r} without calling {tool['name']!r}."
    )


def pdf_fingerprint(path: Path) -> str:
    return sha256_file(path)
