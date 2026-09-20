"""Extraction engine: page selection, forced tool calls, validation and retry.

Every extractor follows the same contract:

* the page list is supplied as a `document` block carrying `cache_control`;
* the answer comes back through a forced tool call with a strict schema -- never as
  free-text JSON;
* every extracted item carries `source: {page, section, quote}` where `page` is the
  PRINTED page number and `quote` is verbatim, so `verify.py` and a human can check it;
* a field that is not present on those pages is returned as null, not guessed.

The extractors themselves live in `extractors.py`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anthropic

from ..config import FRAMEWORK_DIR
from ..llm import Usage, call_tool, document_block
from . import schema_util as s
from .page_map import PageMap
from .pdf_slice import upload_pages

EXTRACT_DIR = FRAMEWORK_DIR / "extracted"

# One request per range of at most this many physical pages. Well inside the API's
# 600-page / 32 MB limits; the real constraint is keeping the model's attention on the
# pages that matter.
MAX_PAGES_PER_REQUEST = 20

DIMENSIONS = [
    "Fairness & Bias",
    "Ethics",
    "Accountability & Governance",
    "Transparency",
    "Legal & Regulatory",
    "Robustness & Stability",
    "Cyber & Data Security",
]

RATINGS = ["low", "medium", "high"]


def source_schema() -> dict[str, Any]:
    return s.obj(
        {
            "page": s.integer(
                "The PRINTED page number shown in the footer of the page this item "
                "came from -- not the position of the page within the supplied extract."
            ),
            "section": s.string("Section or appendix identifier, e.g. '2.4', 'Appendix B'."),
            "quote": s.string(
                "A short verbatim quote (5-25 words) copied exactly from that page, "
                "which a reader could search for to find this item."
            ),
        },
        description="Where in the handbook this item comes from.",
    )


# ------------------------------------------------------------------- extractor specs


# A validator inspects a merged extraction and returns a list of problems. An empty
# list means the extraction is self-consistent and worth keeping.
Validator = Callable[[dict[str, Any], "PageMap", list[int]], list[str]]

# These models reject `temperature`, so an extraction cannot be pinned by sampling.
# A lazy run that returns a stub instead of the full table is therefore a real and
# observed failure mode. The defence is structural: each extractor states its own
# consistency invariants (including a row count the model reports separately from the
# rows themselves), and a failing attempt is retried.
MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class Pass:
    """One request's worth of schema over an extractor's pages.

    `strict: true` compiles the schema into a decoding grammar, and the API rejects a
    grammar that grows too large. Splitting a broad extractor into several narrower
    passes keeps every schema strict instead of relaxing validation, and the later
    passes read the same pages, so they hit the prompt cache the first one populated.
    """

    key: str
    tool_factory: Callable[[], dict[str, Any]]
    instruction: str


@dataclass(frozen=True)
class Extractor:
    """One targeted extraction over a page range, in one or more passes."""

    name: str
    description: str
    section_label: str
    passes: tuple[Pass, ...]
    list_keys: tuple[str, ...]
    pages_resolver: Callable[[PageMap], list[int]]
    extra_context: str = ""
    validator: Validator | None = None
    max_pages_per_request: int = MAX_PAGES_PER_REQUEST
    """Lower this for extractors whose output is long (e.g. verbatim transcription),
    so a single response cannot run out of room part-way through a page."""

    chunk_overlap: int = 0
    """Pages each chunk repeats from the previous one. An item that straddles a chunk
    boundary is otherwise seen only in fragments: neither request has the whole of it,
    and the half without the heading has nothing to attach its rows to. One page of
    overlap gives at least one request the complete item. Requires `dedupe_keys`."""

    dedupe_keys: tuple[tuple[str, str], ...] = ()
    """(list field, identity field) pairs used to reconcile overlapping chunks, e.g.
    ("considerations", "number"). The richest version of each item wins."""

    def resolve(self, page_map: PageMap) -> list[int]:
        """The physical PDF pages this extractor reads, in order and deduplicated."""
        return sorted(set(self.pages_resolver(page_map)))


@dataclass
class ExtractionResult:
    name: str
    data: dict[str, Any]
    usage: Usage
    page_range: str
    printed_range: str
    chunks: int = 1
    warnings: list[str] = field(default_factory=list)
    attempts: int = 1
    problems: list[str] = field(default_factory=list)
    attempt_log: list[dict[str, Any]] = field(default_factory=list)


def _check_sources(
    items: list[dict[str, Any]], page_map: PageMap, pages: list[int], label: str
) -> list[str]:
    """Every cited printed page must be one of the pages the model was actually shown."""
    allowed = set(printed_pages_of(page_map, pages))
    shown = describe_pages(sorted(allowed))
    problems: list[str] = []
    for item in items:
        source = item.get("source") or {}
        page = source.get("page")
        quote = str(source.get("quote") or "").strip()
        name = str(
            item.get("name")
            or item.get("factor")
            or item.get("dimension")
            or item.get("title")
            or item.get("metric")
            or item.get("guardrail")
            or "?"
        )
        if not isinstance(page, int) or page not in allowed:
            problems.append(f"{label} {name!r}: cited page {page} not among printed {shown}")
        if len(quote.split()) < 3:
            problems.append(f"{label} {name!r}: quote too short to verify ({quote!r})")
    return problems


# --------------------------------------------------------------------------- running


def _chunk(
    pages: list[int], size: int = MAX_PAGES_PER_REQUEST, overlap: int = 0
) -> list[list[int]]:
    """Split a page list into request-sized groups, preserving order.

    With `overlap`, each chunk after the first repeats that many pages from the end of
    the previous one, so an item spanning a boundary is complete in at least one chunk.
    """
    if size <= 0:
        raise ValueError("chunk size must be positive")
    overlap = max(0, min(overlap, size - 1))
    step = size - overlap
    chunks: list[list[int]] = []
    start = 0
    while start < len(pages):
        chunks.append(pages[start : start + size])
        if start + size >= len(pages):
            break
        start += step
    return chunks


def _richness(item: dict[str, Any]) -> int:
    """How much an item actually carries, for choosing between overlapping copies."""
    score = 0
    for value in item.values():
        if isinstance(value, list):
            score += 10 * len(value)
        elif isinstance(value, str):
            score += len(value.split())
        elif value is not None:
            score += 1
    return score


def _dedupe(items: list[Any], identity: str) -> list[Any]:
    """Collapse items sharing an identity value, keeping the richest of each."""
    best: dict[Any, dict[str, Any]] = {}
    passthrough: list[Any] = []
    for item in items:
        if not isinstance(item, dict) or identity not in item:
            passthrough.append(item)
            continue
        key = item[identity]
        if key not in best or _richness(item) > _richness(best[key]):
            best[key] = item
    return [*best.values(), *passthrough]


def describe_pages(pages: list[int]) -> str:
    """Render a page list compactly: [52,53,54,58] -> '52-54, 58'."""
    if not pages:
        return "-"
    spans: list[tuple[int, int]] = []
    start = previous = pages[0]
    for page in pages[1:]:
        if page == previous + 1:
            previous = page
            continue
        spans.append((start, previous))
        start = previous = page
    spans.append((start, previous))
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in spans)


def printed_pages_of(page_map: PageMap, pages: list[int]) -> list[int]:
    return [page_map.pdf_to_printed(page) for page in pages]


def _merge(target: dict[str, Any], addition: dict[str, Any]) -> dict[str, Any]:
    """Merge a later chunk into an earlier one: concatenate lists, sum counts, keep first."""
    for key, value in addition.items():
        if key not in target or target[key] is None:
            target[key] = value
        elif isinstance(target[key], list) and isinstance(value, list):
            target[key].extend(value)
        elif isinstance(target[key], int) and isinstance(value, int) and key.endswith("counted"):
            target[key] += value
    return target


def _attempt(
    client: anthropic.Anthropic,
    extractor: Extractor,
    pdf: Path,
    page_map: PageMap,
    chunks: list[list[int]],
    *,
    model: str,
    effort: str,
) -> tuple[dict[str, Any], Usage]:
    """One full pass over every chunk of pages, for every pass of the extractor."""
    merged: dict[str, Any] = {}
    usage = Usage()
    for step in extractor.passes:
        for index, chunk in enumerate(chunks, start=1):
            printed = describe_pages(printed_pages_of(page_map, chunk))
            file_id, _ = upload_pages(
                client, pdf, chunk, label=extractor.name, pdf_sha=page_map.pdf_sha256
            )
            part = f" (part {index} of {len(chunks)})" if len(chunks) > 1 else ""
            result = call_tool(
                client,
                model=model,
                effort=effort,
                tool=step.tool_factory(),
                content=[
                    document_block(
                        file_id,
                        title=f"{extractor.section_label}, printed pages {printed}{part}",
                        context=(
                            f"{extractor.extra_context} These are printed pages {printed} "
                            f"of the handbook, supplied in order. The printed page number "
                            f"appears in each page's footer."
                        ),
                    ),
                    {"type": "text", "text": step.instruction},
                ],
            )
            usage.merge(result.usage)
            if not merged:
                merged = result.data
            else:
                _merge(merged, result.data)
    for list_key, identity in extractor.dedupe_keys:
        if isinstance(merged.get(list_key), list):
            merged[list_key] = _dedupe(merged[list_key], identity)
    if len(extractor.passes) > 1:
        merged.setdefault("_passes", [step.key for step in extractor.passes])
    return merged, usage


def run_extractor(
    client: anthropic.Anthropic,
    extractor: Extractor,
    pdf: Path,
    page_map: PageMap,
    *,
    model: str,
    effort: str,
    max_attempts: int = MAX_ATTEMPTS,
    on_attempt: Callable[[int, list[str]], None] | None = None,
) -> ExtractionResult:
    """Extract, validate, and retry while the result fails its own consistency checks.

    The best attempt wins, so a retry can never make the output worse than the first try.
    """
    pages = extractor.resolve(page_map)
    chunks = _chunk(pages, extractor.max_pages_per_request, extractor.chunk_overlap)
    usage = Usage()

    best_data: dict[str, Any] = {}
    best_problems: list[str] | None = None
    attempt_log: list[dict[str, Any]] = []
    attempts = 0

    for attempt in range(1, max_attempts + 1):
        attempts = attempt
        data, attempt_usage = _attempt(
            client, extractor, pdf, page_map, chunks, model=model, effort=effort
        )
        usage.merge(attempt_usage)
        problems = extractor.validator(data, page_map, pages) if extractor.validator else []
        attempt_log.append(
            {
                "attempt": attempt,
                "problems": list(problems),
                "output_tokens": attempt_usage.output_tokens,
                "latency_ms": attempt_usage.latency_ms,
            }
        )
        if on_attempt:
            on_attempt(attempt, problems)
        if best_problems is None or len(problems) < len(best_problems):
            best_data, best_problems = data, problems
        if not problems:
            break

    problems = best_problems or []
    warnings: list[str] = []
    for key in extractor.list_keys:
        if not best_data.get(key):
            warnings.append(f"'{key}' came back empty")
    for item in best_data.get("unreadable_items", []) or []:
        warnings.append(f"model could not read: {item}")
    if problems:
        warnings.append(f"kept best of {attempts} attempts with {len(problems)} problem(s)")

    return ExtractionResult(
        name=extractor.name,
        data=best_data,
        usage=usage,
        page_range=describe_pages(pages),
        printed_range=describe_pages(printed_pages_of(page_map, pages)),
        chunks=len(chunks),
        warnings=warnings,
        attempts=attempts,
        problems=problems,
        attempt_log=attempt_log,
    )


def write_extraction(result: ExtractionResult, model: str) -> Path:
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXTRACT_DIR / f"{result.name}.json"
    payload = {
        "extractor": result.name,
        "model": model,
        "extracted_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pdf_pages": result.page_range,
        "printed_pages": result.printed_range,
        "requests": result.chunks,
        "attempts": result.attempts,
        "attempt_log": result.attempt_log,
        "validation_problems": result.problems,
        "warnings": result.warnings,
        "usage": result.usage.as_dict(model),
        "data": result.data,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path


def load_extraction(name: str) -> dict[str, Any]:
    path = EXTRACT_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found; run the {name} extractor first")
    return dict(json.loads(path.read_text()))
