"""The request shape is load-bearing, so it is asserted rather than assumed.

Three facts about claude-opus-5 / claude-sonnet-5, verified against docs.claude.com:

* `temperature` (and `top_p` / `top_k`) return a 400 "regardless of whether thinking is
  used" -- so determinism must come from the forced tool call, not from sampling;
* forced `tool_choice` is incompatible with *manual* extended thinking but works with
  *adaptive* thinking;
* `budget_tokens` returns a 400; depth is `output_config.effort`.

A regression on any of these breaks every request, so they are pinned here.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from mindforge_assess.llm import (
    ApiUnavailableError,
    ToolNotCalledError,
    Usage,
    call_tool,
    classify_api_error,
    document_block,
)

TOOL: dict[str, Any] = {
    "name": "record_thing",
    "description": "d",
    "input_schema": {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
        "additionalProperties": False,
    },
    "strict": True,
}


class _Stream:
    def __init__(self, message: Any) -> None:
        self._message = message

    def __enter__(self) -> _Stream:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def get_final_message(self) -> Any:
        return self._message


class FakeMessages:
    """Records the kwargs it was called with and returns a canned message."""

    def __init__(self, message: Any) -> None:
        self.message = message
        self.kwargs: dict[str, Any] = {}

    def stream(self, **kwargs: Any) -> _Stream:
        self.kwargs = kwargs
        return _Stream(self.message)


def fake_client(content: list[Any], stop_reason: str = "tool_use") -> Any:
    message = SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        stop_details=None,
        usage=SimpleNamespace(
            input_tokens=11,
            output_tokens=22,
            cache_creation_input_tokens=33,
            cache_read_input_tokens=44,
        ),
    )
    return SimpleNamespace(messages=FakeMessages(message))


def tool_use_block(value: str = "ok") -> Any:
    return SimpleNamespace(type="tool_use", name="record_thing", input={"value": value})


def test_request_omits_temperature_and_budget_tokens() -> None:
    client = fake_client([tool_use_block()])
    call_tool(client, model="claude-sonnet-5", tool=TOOL, content=[{"type": "text", "text": "x"}])

    sent = client.messages.kwargs
    assert "temperature" not in sent, "temperature is a 400 on these models"
    assert "top_p" not in sent and "top_k" not in sent
    assert "budget_tokens" not in sent.get("thinking", {}), "budget_tokens is a 400"


def test_request_forces_the_tool_with_adaptive_thinking() -> None:
    client = fake_client([tool_use_block()])
    call_tool(
        client,
        model="claude-opus-5",
        tool=TOOL,
        content=[{"type": "text", "text": "x"}],
        effort="low",
    )

    sent = client.messages.kwargs
    assert sent["tool_choice"] == {"type": "tool", "name": "record_thing"}
    assert sent["thinking"] == {"type": "adaptive"}
    assert sent["output_config"] == {"effort": "low"}
    assert sent["tools"] == [TOOL]
    assert sent["tools"][0]["strict"] is True


def test_tool_input_is_parsed_and_usage_recorded() -> None:
    client = fake_client([tool_use_block("hello")])
    result = call_tool(
        client, model="claude-sonnet-5", tool=TOOL, content=[{"type": "text", "text": "x"}]
    )

    assert result.data == {"value": "hello"}
    assert result.usage.cache_read_input_tokens == 44
    assert result.usage.total_input_tokens == 11 + 33 + 44


def test_thinking_blocks_do_not_confuse_the_parser() -> None:
    thinking = SimpleNamespace(type="thinking", thinking="considering...")
    client = fake_client([thinking, tool_use_block("v")])
    result = call_tool(
        client, model="claude-opus-5", tool=TOOL, content=[{"type": "text", "text": "x"}]
    )
    assert result.data == {"value": "v"}
    assert result.thinking == ["considering..."]


def test_missing_tool_call_raises() -> None:
    text = SimpleNamespace(type="text", text="I would rather not")
    client = fake_client([text], stop_reason="end_turn")
    with pytest.raises(ToolNotCalledError):
        call_tool(
            client, model="claude-sonnet-5", tool=TOOL, content=[{"type": "text", "text": "x"}]
        )


def test_refusal_raises_before_parsing_content() -> None:
    client = fake_client([], stop_reason="refusal")
    with pytest.raises(ToolNotCalledError, match="refused"):
        call_tool(
            client, model="claude-opus-5", tool=TOOL, content=[{"type": "text", "text": "x"}]
        )


def test_document_block_is_cached_by_default() -> None:
    block = document_block("file_123", title="t", context="c")
    assert block["source"] == {"type": "file", "file_id": "file_123"}
    assert block["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in document_block("file_123", cache=False)


class FakeApiError(Exception):
    """Stands in for anthropic.APIStatusError, which needs a live httpx response."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def test_credit_exhaustion_is_classified_as_terminal() -> None:
    terminal = classify_api_error(
        FakeApiError("Your credit balance is too low to access the Anthropic API.")
    )
    assert isinstance(terminal, ApiUnavailableError)
    assert "credit balance is too low" in str(terminal)
    assert "already on disk are kept" in str(terminal)


def test_bad_credentials_are_classified_as_terminal() -> None:
    terminal = classify_api_error(FakeApiError("authentication_error: invalid x-api-key"))
    assert isinstance(terminal, ApiUnavailableError)
    assert "ANTHROPIC_API_KEY" in str(terminal)


def test_retryable_errors_are_not_swallowed() -> None:
    """A grammar-size 400 is actionable by changing the schema, not by topping up."""
    assert classify_api_error(FakeApiError("The compiled grammar is too large.")) is None
    assert classify_api_error(FakeApiError("overloaded_error")) is None


def test_cost_accounts_for_cache_write_premium_and_read_discount() -> None:
    """Cache writes bill at 1.25x input and reads at 0.1x."""
    usage = Usage(input_tokens=1_000_000)
    assert usage.cost_usd("claude-opus-5") == pytest.approx(5.0)

    write = Usage(cache_creation_input_tokens=1_000_000)
    assert write.cost_usd("claude-opus-5") == pytest.approx(6.25)

    read = Usage(cache_read_input_tokens=1_000_000)
    assert read.cost_usd("claude-opus-5") == pytest.approx(0.5)

    assert Usage(input_tokens=1_000_000).cost_usd("claude-sonnet-5") == pytest.approx(2.0)


def test_a_truncated_response_raises_rather_than_returning_a_partial_dict() -> None:
    """The failure that looks like a success: a streamed tool input is reassembled by a
    tolerant parser, so a response cut off at max_tokens yields a plausible-but-wrong
    dict instead of an error. The stop reason is the only reliable signal."""
    import pytest

    from mindforge_assess.llm import OutputTruncatedError, call_tool

    truncated = SimpleNamespace(
        content=[
            SimpleNamespace(type="tool_use", name="t", input={"a": '["'}),
        ],
        stop_reason="max_tokens",
        stop_details=None,
        usage=SimpleNamespace(
            input_tokens=1,
            output_tokens=16_000,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
    )
    # A stand-in transport, not a real client: nothing in this suite reaches the network.
    client = cast(Any, SimpleNamespace(messages=FakeMessages(truncated)))
    with pytest.raises(OutputTruncatedError, match="cut off at max_tokens"):
        call_tool(
            client,
            model="claude-sonnet-5",
            tool={"name": "t", "input_schema": {}},
            content=[{"type": "text", "text": "hi"}],
        )
