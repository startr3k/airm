"""Second-pass verification of each extractor's output.

Re-sends the same pages -- so the prompt cache is warm -- together with the JSON that was
extracted from them, and asks Claude to check its own work against the page: does each
verbatim quote actually appear on the page it cites, did any table row get dropped, and
was any figure unreadable.

The check that can fail `make ingest` is the row count: if the verifier counts more rows
on an appendix table than the extraction returned, rows were silently dropped and the
pack must not be built from it.

Run:  python -m mindforge_assess.ingest.verify [names...]
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anthropic

from ..config import FRAMEWORK_DIR
from ..llm import Usage, call_tool, document_block
from . import schema_util as s
from .engine import (
    EXTRACT_DIR,
    Extractor,
    describe_pages,
    load_extraction,
    printed_pages_of,
)
from .extractors import EXTRACTORS
from .page_map import PageMap
from .pdf_slice import upload_pages

REPORT_PATH = FRAMEWORK_DIR / "verification_report.md"
RESULTS_PATH = FRAMEWORK_DIR / "verification.json"

VERDICTS = ["pass", "pass_with_warnings", "fail"]


def _verify_tool() -> dict[str, Any]:
    quote_check = s.obj(
        {
            "item": s.string("The name of the extracted item this quote belongs to."),
            "cited_page": s.integer("The printed page number the extraction cited."),
            "quote": s.string("The quote as extracted."),
            "found_on_cited_page": {
                "type": "boolean",
                "description": (
                    "True only if this exact wording appears on that printed page. "
                    "Minor whitespace or line-break differences are acceptable; "
                    "different wording is not."
                ),
            },
            "found_on_page": s.nullable_integer(
                "If the quote appears on a DIFFERENT page in this extract, its printed "
                "page number. Null if it appears on the cited page or nowhere."
            ),
            "note": s.nullable_string("What is wrong, if anything. Null if the quote is fine."),
        }
    )
    missing = s.obj(
        {
            "table_or_section": s.string("Which table or section is short."),
            "printed_page": s.nullable_integer("Printed page where the gap is, else null."),
            "missing_items": s.arr(
                s.string("Name of a row or item present on the page but absent from the JSON."),
                description="Items visible on the page that the extraction did not return.",
            ),
            "note": s.string("What is missing and how you know."),
        }
    )
    unreadable = s.obj(
        {
            "label": s.string("Figure or table label, e.g. 'Figure 2.4.3'."),
            "printed_page": s.nullable_integer("Its printed page, else null."),
            "what_could_not_be_read": s.string("Exactly which part was illegible."),
        }
    )
    return s.tool(
        "record_verification",
        "Record the result of checking an extraction against the pages it came from.",
        s.obj(
            {
                "quote_checks": s.arr(
                    quote_check,
                    description="One entry per quote you checked. Check every quote given.",
                ),
                "missing_rows": s.arr(
                    missing,
                    description=(
                        "Items WITHIN THE EXTRACTOR'S STATED SCOPE that are on the page "
                        "but absent from the JSON. Empty array if nothing in scope is "
                        "missing. Content the extractor was never asked to capture "
                        "belongs in out_of_scope_observations, not here."
                    ),
                ),
                "out_of_scope_observations": s.arr(
                    s.string("Something on these pages the extractor's scope excludes."),
                    description=(
                        "Notable content on the pages that falls outside what this "
                        "extractor was asked for. Not a defect -- it tells the author "
                        "whether the schema has a gap worth filling. Empty if none."
                    ),
                ),
                "unreadable_figures": s.arr(
                    unreadable, description="Empty array if every figure was legible."
                ),
                "verifier_counted_rows": s.integer(
                    "Your own count, made from the pages, of the total number of rows or "
                    "items that the extraction was supposed to capture."
                ),
                "extracted_rows": s.integer(
                    "The number of such rows or items actually present in the supplied JSON."
                ),
                "factual_errors": s.arr(
                    s.obj(
                        {
                            "item": s.string("Which extracted value is at issue."),
                            "printed_page": s.nullable_integer("Its printed page, else null."),
                            "extracted_value": s.string("What the JSON says."),
                            "page_value": s.string("What the page actually says."),
                            "severity": s.enum(
                                ["wrong", "wording", "ordering"],
                                "'wrong' only when the meaning differs from the page. "
                                "'wording' for punctuation or article differences that do "
                                "not change meaning. 'ordering' when items are correct but "
                                "sequenced differently.",
                            ),
                        }
                    ),
                    description=(
                        "Only genuine discrepancies. If you examine something and conclude "
                        "it is correct, do NOT list it here -- an empty array is the right "
                        "answer when nothing is wrong."
                    ),
                ),
                "verdict": s.enum(
                    VERDICTS,
                    "'fail' if rows are missing or values are wrong; 'pass_with_warnings' "
                    "for quote-wording problems only; 'pass' if everything checks out.",
                ),
                "summary": s.string("Two or three sentences a human reviewer can act on."),
            }
        ),
    )


VERIFY_INSTRUCTION = """\
Below is JSON that was extracted from exactly these pages by an earlier pass. Check it
against the pages themselves. You are looking for mistakes, so be sceptical: an
extraction that looks plausible can still have dropped rows.

Judge it against WHAT THIS EXTRACTOR WAS ASKED TO CAPTURE, which is quoted below, and
not against everything printed on the pages. These pages were selected for one purpose
and will contain other material -- figures, tables and prose belonging to other
extractors. That other material is not missing data. If it looks like something the
schema should have had a place for, say so in `out_of_scope_observations`; do not record
it as a missing row.

Do three things.

1. QUOTES. Every item carries `source.page` (a PRINTED page number) and `source.quote`.
   For each one, find that page in this extract and confirm the quote appears on it
   verbatim. Set `found_on_cited_page` to false if the wording differs, if the quote is
   on a different page, or if it does not appear at all. Report every quote you check.

2. COMPLETENESS, WITHIN SCOPE. Count the in-scope rows or items on the pages yourself,
   then compare with what the JSON contains. List anything in scope that is present on
   the page but absent from the JSON in `missing_rows`. `verifier_counted_rows` is YOUR
   count of IN-SCOPE items from the page, and `extracted_rows` is what the JSON has --
   they must be independent, so count first. Before calling something missing, check
   whether it is already present under a different field or a different wording.

3. FIGURES AND VALUES. If a figure or matrix was transcribed, check the transcription
   cell by cell against the figure. Report any cell whose value is wrong in
   `factual_errors`, and anything illegible in `unreadable_figures`.

Return `fail` if rows are missing or if a value's MEANING contradicts the page. Do not be
charitable about omissions -- the point of this pass is to catch what the extraction pass
missed.

But `factual_errors` is for genuine discrepancies about the HANDBOOK'S CONTENT only.
Grade each one: `wrong` when the meaning differs, `wording` for punctuation or an article
that changes nothing, `ordering` when the items are right but sequenced differently. If
you check something and find it correct, leave it out entirely rather than recording it
with a note saying it is fine.

Fields named `total_..._counted` are the extraction pass's own working notes -- it was
asked to count before transcribing so that a shortfall would be visible. They are not
claims about the handbook and are not copied into the pack. If such a field disagrees
with the number of items actually returned, ignore it: your own independent count in
`verifier_counted_rows` against `extracted_rows` is what settles completeness.

"""


SCOPE_PREAMBLE = """\
WHAT THIS EXTRACTOR WAS ASKED TO CAPTURE
=========================================
Purpose: {description}

It was given this instruction:
-----
{instruction}
-----

Anything on these pages outside that remit is out of scope for this check.

EXTRACTED JSON:
"""


def verify_extractor(
    client: anthropic.Anthropic,
    extractor: Extractor,
    pdf: Path,
    page_map: PageMap,
    *,
    model: str,
    effort: str,
) -> tuple[dict[str, Any], Usage]:
    payload = load_extraction(extractor.name)
    pages = extractor.resolve(page_map)
    printed = describe_pages(printed_pages_of(page_map, pages))
    # Same label and pages as the extraction, so this reuses the cached upload.
    file_id, _ = upload_pages(
        client, pdf, pages, label=extractor.name, pdf_sha=page_map.pdf_sha256
    )
    result = call_tool(
        client,
        model=model,
        effort=effort,
        tool=_verify_tool(),
        content=[
            document_block(
                file_id,
                title=f"{extractor.section_label}, printed pages {printed}",
                context=(
                    f"{extractor.extra_context} These are printed pages {printed} "
                    f"(physical PDF pages {describe_pages(pages)})."
                ),
            ),
            {
                "type": "text",
                "text": VERIFY_INSTRUCTION
                + SCOPE_PREAMBLE.format(
                    description=extractor.description,
                    instruction="\n\n".join(
                        step.instruction for step in extractor.passes
                    ),
                )
                + json.dumps(payload["data"], indent=2, ensure_ascii=False),
            },
        ],
    )
    return result.data, result.usage


# ----------------------------------------------------------------------- reporting


def esc(text: object, limit: int = 300) -> str:
    """Make a value safe for a Markdown table cell or list item."""
    flat = " ".join(str(text or "").split())
    if len(flat) > limit:
        flat = flat[: limit - 1].rstrip() + "\u2026"
    return flat.replace("|", "\\|")


def _bad_quotes(findings: dict[str, Any]) -> list[dict[str, Any]]:
    return [q for q in findings.get("quote_checks", []) if not q.get("found_on_cited_page")]


def summarise(name: str, findings: dict[str, Any]) -> dict[str, Any]:
    checks = findings.get("quote_checks", [])
    bad = _bad_quotes(findings)
    counted = findings.get("verifier_counted_rows")
    extracted = findings.get("extracted_rows")
    rows_short = isinstance(counted, int) and isinstance(extracted, int) and counted > extracted
    return {
        "extractor": name,
        "verdict": findings.get("verdict"),
        "quotes_checked": len(checks),
        "quotes_failed": len(bad),
        "verifier_counted_rows": counted,
        "extracted_rows": extracted,
        "rows_short": rows_short,
        "missing_rows": findings.get("missing_rows", []),
        "out_of_scope_observations": findings.get("out_of_scope_observations", []),
        "unreadable_figures": findings.get("unreadable_figures", []),
        "factual_errors": findings.get("factual_errors", []),
        "meaning_errors": [
            e for e in findings.get("factual_errors", []) if e.get("severity") == "wrong"
        ],
        "summary": findings.get("summary", ""),
        "failed_quotes": bad,
    }


def blocking_failures(summaries: Iterable[dict[str, Any]]) -> list[str]:
    """Reasons `make ingest` must stop. Row shortfalls are blocking; wording is not."""
    blocking: list[str] = []
    for item in summaries:
        if item["rows_short"]:
            blocking.append(
                f"{item['extractor']}: verifier counted {item['verifier_counted_rows']} rows "
                f"but only {item['extracted_rows']} were extracted"
            )
        for missing in item["missing_rows"]:
            names = ", ".join(missing.get("missing_items", [])) or missing.get("note", "")
            blocking.append(
                f"{item['extractor']}: missing from {missing['table_or_section']}: {names}"
            )
        wrong = [e for e in item["factual_errors"] if e.get("severity") == "wrong"]
        for error in wrong:
            blocking.append(
                f"{item['extractor']}: {error['item']} (p. {error.get('printed_page') or '?'}) "
                f"-- extracted {error['extracted_value']!r}, page says {error['page_value']!r}"
            )
    return blocking


def write_report(summaries: list[dict[str, Any]], model: str, usage: Usage) -> Path:
    blocking = blocking_failures(summaries)
    lines: list[str] = [
        "# Framework extraction — verification report",
        "",
        "Generated by `mindforge_assess.ingest.verify`. Each extractor's output was sent back",
        "to Claude together with the same handbook pages it came from, and checked against",
        "them. This file is generated; do not edit it by hand.",
        "",
        f"- Verifier model: `{model}`",
        f"- Generated: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"- Extractors verified: {len(summaries)}",
        f"- Blocking failures: **{len(blocking)}**",
        "",
        "## Summary",
        "",
        "| Extractor | Verdict | Quotes OK | Rows (verifier / extracted) | Missing "
        "| Figures unread |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in summaries:
        ok = item["quotes_checked"] - item["quotes_failed"]
        lines.append(
            f"| `{item['extractor']}` | {item['verdict']} | {ok}/{item['quotes_checked']} | "
            f"{item['verifier_counted_rows']} / {item['extracted_rows']} | "
            f"{len(item['missing_rows'])} | {len(item['unreadable_figures'])} |"
        )

    lines += [
        "",
        "Each extraction is judged against what that extractor was asked to capture, not",
        "against everything printed on its pages -- those pages carry other extractors'",
        "material too. Content outside an extractor's remit is listed separately and does",
        "not block the build.",
        "",
        "## Blocking failures",
        "",
    ]
    if blocking:
        lines += [f"- {reason}" for reason in blocking]
    else:
        lines.append("None. Every appendix table returned at least as many rows as the")
        lines.append("verifier counted on the page, and no extracted value contradicts it.")

    for item in summaries:
        lines += ["", f"## `{item['extractor']}`", "", item["summary"], ""]
        if item["failed_quotes"]:
            lines += [
                "### Quotes that did not match the cited page",
                "",
                "| Item | Cited p. | Found on p. | Note |",
                "| --- | --- | --- | --- |",
            ]
            for quote in item["failed_quotes"]:
                note = str(quote.get("note") or "").replace("|", "\\|")
                lines.append(
                    f"| {quote['item']} | {quote['cited_page']} | "
                    f"{quote.get('found_on_page') or '—'} | {note} |"
                )
            lines.append("")
        else:
            lines += ["Every quote was found verbatim on the page it cites.", ""]
        if item["missing_rows"]:
            lines += ["### Missing rows", ""]
            for missing in item["missing_rows"]:
                names = ", ".join(missing.get("missing_items", [])) or "—"
                lines.append(
                    f"- **{missing['table_or_section']}** (p. "
                    f"{missing.get('printed_page') or '?'}): {names} — {missing.get('note', '')}"
                )
            lines.append("")
        if item["out_of_scope_observations"]:
            lines += [
                "### On the page but outside this extractor's scope",
                "",
                "_Not defects. These say whether the schema has a gap worth filling._",
                "",
            ]
            lines += [f"- {esc(note)}" for note in item["out_of_scope_observations"]]
            lines.append("")
        if item["factual_errors"]:
            lines += [
                "### Discrepancies against the page",
                "",
                "| Severity | Item | p. | Extracted | Page says |",
                "| --- | --- | --- | --- | --- |",
            ]
            for error in sorted(
                item["factual_errors"],
                key=lambda e: {"wrong": 0, "wording": 1, "ordering": 2}.get(
                    e.get("severity", "wording"), 3
                ),
            ):

                def clean(value: object) -> str:
                    return str(value).replace("|", "\\|").replace("\n", " ")[:140]

                lines.append(
                    f"| **{error.get('severity')}** | {clean(error.get('item'))} | "
                    f"{error.get('printed_page') or '—'} | "
                    f"{clean(error.get('extracted_value'))} | "
                    f"{clean(error.get('page_value'))} |"
                )
            lines.append("")
            lines.append(
                "Only rows marked **wrong** block `make ingest`; wording and ordering "
                "differences are recorded for review."
            )
            lines.append("")
        if item["unreadable_figures"]:
            lines += ["### Figures that could not be read", ""]
            for figure in item["unreadable_figures"]:
                lines.append(
                    f"- **{figure['label']}** (p. {figure.get('printed_page') or '?'}): "
                    f"{figure['what_could_not_be_read']}"
                )
            lines.append("")

    lines += [
        "## Verification cost",
        "",
        f"- Requests: {usage.calls}",
        f"- Input tokens: {usage.total_input_tokens:,} "
        f"({usage.cache_creation_input_tokens:,} cache write, "
        f"{usage.cache_read_input_tokens:,} cache read)",
        f"- Output tokens: {usage.output_tokens:,}",
        f"- Estimated cost: ${usage.cost_usd(model):.2f}",
        "",
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines))
    return REPORT_PATH


# ------------------------------------------------------------------------------ cli


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from ..config import ConfigError, get_settings
    from ..llm import ApiUnavailableError, get_client
    from .page_map import load_page_map

    parser = argparse.ArgumentParser(description="Verify extractions against the handbook.")
    parser.add_argument("names", nargs="*", default=[], help="extractors to verify")
    args = parser.parse_args(argv)

    available = [n for n in EXTRACTORS if (EXTRACT_DIR / f"{n}.json").is_file()]
    names = args.names or available
    missing = [n for n in names if not (EXTRACT_DIR / f"{n}.json").is_file()]
    if missing:
        print(f"error: no extraction on disk for: {', '.join(missing)}", file=sys.stderr)
        return 2

    try:
        settings = get_settings()
        pdf = settings.require_handbook()
        page_map = load_page_map()
        client = get_client(settings)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    model, effort = settings.ingest_model, settings.ingest_effort
    summaries: list[dict[str, Any]] = []
    total = Usage()
    raw: dict[str, Any] = {}

    for name in names:
        print(f"\n== verifying {name} ==")
        try:
            findings, usage = verify_extractor(
                client, EXTRACTORS[name], pdf, page_map, model=model, effort=effort
            )
        except ApiUnavailableError as exc:
            print(f"\n{exc}", file=sys.stderr)
            return 3
        total.merge(usage)
        raw[name] = findings
        item = summarise(name, findings)
        summaries.append(item)
        ok = item["quotes_checked"] - item["quotes_failed"]
        print(
            f"   verdict={item['verdict']}  quotes {ok}/{item['quotes_checked']} ok  "
            f"rows {item['extracted_rows']}/{item['verifier_counted_rows']} (verifier)  "
            f"missing={len(item['missing_rows'])}  "
            f"errors={len(item['meaning_errors'])} meaning / "
            f"{len(item['factual_errors'])} total"
        )
        print(
            f"   {usage.cache_read_input_tokens:,} tokens served from cache, "
            f"~${usage.cost_usd(model):.2f}"
        )

    # Verifying a subset must update those entries, not discard the rest: re-checking
    # one extractor should never silently un-verify the other eight.
    previous: dict[str, Any] = {}
    if RESULTS_PATH.is_file():
        previous = json.loads(RESULTS_PATH.read_text())
    merged_summaries = {item["extractor"]: item for item in previous.get("summaries", [])}
    merged_summaries.update({item["extractor"]: item for item in summaries})
    merged_raw = dict(previous.get("raw", {}))
    merged_raw.update(raw)

    order = list(EXTRACTORS)
    all_summaries = sorted(
        merged_summaries.values(),
        key=lambda item: order.index(item["extractor"])
        if item["extractor"] in order
        else len(order),
    )

    report = write_report(all_summaries, model, total)
    RESULTS_PATH.write_text(
        json.dumps(
            {
                "model": model,
                "verified_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "verified_now": names,
                "summaries": all_summaries,
                "raw": merged_raw,
                "usage": total.as_dict(model),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    blocking = blocking_failures(all_summaries)
    print(f"\nWrote {report}")
    if blocking:
        print(f"\n{len(blocking)} BLOCKING failure(s):")
        for reason in blocking:
            print(f"  - {reason}")
        return 1
    print("\nNo blocking failures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
