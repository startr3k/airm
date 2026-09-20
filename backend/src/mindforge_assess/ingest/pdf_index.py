"""Build framework/page_map.json: the printed-page <-> PDF-page calibration.

The handbook's printed page numbers (what a reader sees in the footer) do not match the
PDF's physical page indices, because the front matter is unnumbered. Every later
extractor addresses pages by *physical* index; every citation shown to a user quotes the
*printed* number. This module establishes both, and the offset between them, by having
Claude read the contents pages and then read the footers of sample pages.

Run:  python -m mindforge_assess.ingest.pdf_index [--force]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anthropic

from ..config import FRAMEWORK_DIR, ConfigError, get_settings, sha256_file
from ..llm import Usage, call_tool, document_block, get_client
from . import schema_util as s
from .pdf_slice import page_count, upload_pages

PAGE_MAP_PATH = FRAMEWORK_DIR / "page_map.json"
PAGE_MAP_VERSION = 1

# The contents / list-of-figures / list-of-tables pages live in the first stretch of
# front matter. Reading a few extra pages is cheap and avoids a second round trip.
FRONT_MATTER_PAGES = 14

SECTION_KINDS = ["front_matter", "section", "subsection", "appendix", "back_matter"]


# --------------------------------------------------------------------------- tools


def _contents_tool() -> dict[str, Any]:
    entry = s.obj(
        {
            "section_id": s.nullable_string(
                "Section number exactly as printed, e.g. '1.1', '2.4', 'B', 'H'. "
                "Null for unnumbered entries such as 'Foreword'."
            ),
            "title": s.string("Entry title exactly as printed in the contents listing."),
            "printed_start": s.nullable_integer(
                "The printed page number shown against this entry in the contents. "
                "Null if the listing shows no page number."
            ),
            "kind": s.enum(SECTION_KINDS, "What sort of entry this is."),
            "level": s.integer("Nesting depth in the contents: 1 for top level, 2, 3..."),
        }
    )
    figure = s.obj(
        {
            "label": s.string("Identifier as printed, e.g. 'Figure 2.4.3', 'Table 3.5.1'."),
            "caption": s.string("Caption text as printed."),
            "printed_page": s.nullable_integer("Printed page number listed for this item."),
        }
    )
    return s.tool(
        "record_contents",
        "Record the handbook's front-matter metadata and its contents listing.",
        s.obj(
            {
                "document_title": s.string("Full title from the cover page."),
                "document_subtitle": s.nullable_string("Subtitle or strapline, else null."),
                "publisher": s.nullable_string("Issuing body or publisher, else null."),
                "publication_date": s.nullable_string("Date as printed, else null."),
                "edition_or_version": s.nullable_string("Edition/version string, else null."),
                "highest_printed_page_seen": s.nullable_integer(
                    "The largest printed page number appearing anywhere in the contents "
                    "listing, or null if none are shown."
                ),
                "contents": s.arr(entry, description="Every contents entry, in printed order."),
                "figures": s.arr(figure, description="Every entry in the list of figures."),
                "tables": s.arr(figure, description="Every entry in the list of tables."),
                "illustrations": s.arr(
                    figure, description="Every entry in the list of illustrations."
                ),
            }
        ),
    )


def _footer_tool() -> dict[str, Any]:
    probe = s.obj(
        {
            "document_label": s.string(
                "The label given in the title of the document block you are reading, "
                "e.g. 'PHYSICAL PAGE 26'."
            ),
            "printed_page": s.nullable_integer(
                "The page number printed in this page's footer or header. Null if the "
                "page carries no printed number. Do not infer it from neighbouring pages."
            ),
            "running_header": s.nullable_string(
                "Any running header or section name printed on the page, else null."
            ),
            "first_heading": s.nullable_string(
                "The first heading printed on the page, else null."
            ),
            "snippet": s.string("The first 15 or so words of body text on the page."),
        }
    )
    return s.tool(
        "record_page_footers",
        "Record the printed page number visible on each supplied page.",
        s.obj({"pages": s.arr(probe, description="One entry per document block supplied.")}),
    )


# ----------------------------------------------------------------------- extraction


def read_contents(
    client: anthropic.Anthropic,
    pdf: Path,
    pdf_sha: str,
    *,
    model: str,
    effort: str,
    front_pages: int,
) -> tuple[dict[str, Any], Usage]:
    pages = list(range(1, front_pages + 1))
    file_id, _ = upload_pages(client, pdf, pages, label="front", pdf_sha=pdf_sha)
    result = call_tool(
        client,
        model=model,
        effort=effort,
        tool=_contents_tool(),
        content=[
            document_block(
                file_id,
                title=f"Handbook front matter (physical PDF pages 1-{front_pages})",
                context=(
                    "These are the first pages of the handbook: cover, then the contents "
                    "listing and any lists of figures, tables and illustrations."
                ),
            ),
            {
                "type": "text",
                "text": (
                    "Read the cover and the contents listing.\n\n"
                    "Transcribe EVERY entry in the contents, in the order printed, "
                    "including appendices and any 'Future Perspectives' style sections. "
                    "Also transcribe the lists of figures, tables and illustrations if "
                    "they are present on these pages.\n\n"
                    "`printed_start` is the page number PRINTED NEXT TO THE ENTRY in the "
                    "contents listing -- not the position of the page in this PDF. If an "
                    "entry shows no page number, return null. If a list of figures, tables "
                    "or illustrations is not present on these pages, return an empty array "
                    "for it. Never invent a page number."
                ),
            },
        ],
    )
    return result.data, result.usage


def probe_footers(
    client: anthropic.Anthropic,
    pdf: Path,
    pdf_sha: str,
    physical_pages: list[int],
    *,
    model: str,
    effort: str,
) -> tuple[list[dict[str, Any]], Usage]:
    """Ask Claude to read the printed page number off each of several single pages."""
    content: list[dict[str, Any]] = []
    for page in physical_pages:
        file_id, _ = upload_pages(client, pdf, [page], label="probe", pdf_sha=pdf_sha)
        content.append(
            document_block(
                file_id,
                title=f"PHYSICAL PAGE {page}",
                context=f"Physical page {page} of the PDF, supplied on its own.",
                cache=False,
            )
        )
    content.append(
        {
            "type": "text",
            "text": (
                "Each document above is a single page, titled with its physical index in "
                "the PDF. For each one, report the page number PRINTED on the page itself "
                "(usually in the footer). Return null for `printed_page` if the page shows "
                "no printed number -- do not infer one from the physical index or from "
                "other pages. Return one entry per document, using the exact title as "
                "`document_label`."
            ),
        }
    )
    result = call_tool(
        client,
        model=model,
        effort=effort,
        tool=_footer_tool(),
        content=content,
        max_tokens=8_000,
    )
    return list(result.data.get("pages", [])), result.usage


# ---------------------------------------------------------------------- calibration


def choose_probe_pages(total: int, count: int = 5) -> list[int]:
    """Physical pages spread across the body, avoiding the unnumbered front matter."""
    fractions = [0.15, 0.35, 0.55, 0.75, 0.92][:count]
    pages = sorted({max(1, min(total, round(total * f))) for f in fractions})
    return pages


def derive_offset(probes: list[dict[str, Any]]) -> dict[str, Any]:
    """offset = physical page - printed page. Report whether it is constant."""
    observations: list[dict[str, Any]] = []
    for probe in probes:
        label = str(probe.get("document_label", ""))
        digits = "".join(ch for ch in label if ch.isdigit())
        if not digits:
            continue
        physical = int(digits)
        printed = probe.get("printed_page")
        observations.append(
            {
                "pdf_page": physical,
                "printed_page": printed,
                "offset": (physical - printed) if isinstance(printed, int) else None,
                "running_header": probe.get("running_header"),
                "first_heading": probe.get("first_heading"),
                "snippet": probe.get("snippet"),
            }
        )
    offsets = [o["offset"] for o in observations if o["offset"] is not None]
    unique = sorted(set(offsets))
    return {
        "observations": sorted(observations, key=lambda o: o["pdf_page"]),
        "offsets_seen": unique,
        "constant": len(unique) == 1,
        "printed_to_pdf": unique[0] if len(unique) == 1 else None,
    }


def build_sections(
    contents: list[dict[str, Any]], offset: int | None, last_printed: int | None
) -> list[dict[str, Any]]:
    """Give every contents entry a printed and physical page span.

    An entry runs until the next entry at the same or a shallower nesting level, so a
    parent section spans all of its children rather than stopping where its first child
    stops. Ties on `printed_start` are kept (a heading and its first subsection can share
    a page); only a strictly later start closes the span.
    """
    numbered = [c for c in contents if isinstance(c.get("printed_start"), int)]
    sections: list[dict[str, Any]] = []
    for index, entry in enumerate(numbered):
        start = int(entry["printed_start"])
        level = int(entry.get("level") or 1)
        printed_end: int | None = None
        for following in numbered[index + 1 :]:
            nxt = int(following["printed_start"])
            if int(following.get("level") or 1) <= level and nxt > start:
                printed_end = nxt - 1
                break
        if printed_end is None:
            printed_end = last_printed if isinstance(last_printed, int) else start
        section = {
            "section_id": entry.get("section_id"),
            "title": entry.get("title"),
            "kind": entry.get("kind"),
            "level": entry.get("level"),
            "printed_start": start,
            "printed_end": max(start, printed_end),
            "pdf_start": None,
            "pdf_end": None,
        }
        if offset is not None:
            section["pdf_start"] = start + offset
            section["pdf_end"] = max(start, printed_end) + offset
        sections.append(section)
    return sections


def confirm_anchors(
    client: anthropic.Anthropic,
    pdf: Path,
    pdf_sha: str,
    anchors: list[tuple[int, str]],
    offset: int,
    total_pages: int,
    *,
    model: str,
    effort: str,
) -> tuple[list[dict[str, Any]], Usage]:
    """Spot-check the offset: for a known printed page, does that PDF page print it?"""
    wanted = [(printed, printed + offset, why) for printed, why in anchors]
    wanted = [(p, pdf_page, why) for p, pdf_page, why in wanted if 1 <= pdf_page <= total_pages]
    if not wanted:
        return [], Usage()
    probes, usage = probe_footers(
        client, pdf, pdf_sha, [pdf_page for _, pdf_page, _ in wanted], model=model, effort=effort
    )
    by_page = {}
    for probe in probes:
        digits = "".join(ch for ch in str(probe.get("document_label", "")) if ch.isdigit())
        if digits:
            by_page[int(digits)] = probe
    checks: list[dict[str, Any]] = []
    for printed, pdf_page, why in wanted:
        probe = by_page.get(pdf_page, {})
        observed = probe.get("printed_page")
        checks.append(
            {
                "reason": why,
                "expected_printed_page": printed,
                "pdf_page": pdf_page,
                "observed_printed_page": observed,
                "match": observed == printed,
                "first_heading": probe.get("first_heading"),
                "snippet": probe.get("snippet"),
            }
        )
    return checks, usage


def pick_anchors(payload: dict[str, Any], sections: list[dict[str, Any]]) -> list[tuple[int, str]]:
    """Two or three known printed pages to re-read, drawn from what the contents said."""
    anchors: list[tuple[int, str]] = []
    for item in payload.get("illustrations", []) or []:
        label = str(item.get("label", ""))
        if "2.3.1" in label and isinstance(item.get("printed_page"), int):
            anchors.append((int(item["printed_page"]), f"{label} (from list of illustrations)"))
            break
    for section in sections:
        if str(section.get("section_id") or "").strip().upper() in {"B", "APPENDIX B"}:
            anchors.append((section["printed_start"], "Appendix B start (from contents)"))
            break
    for item in payload.get("figures", []) or []:
        label = str(item.get("label", ""))
        if "2.4.3" in label and isinstance(item.get("printed_page"), int):
            anchors.append((int(item["printed_page"]), f"{label} (from list of figures)"))
            break
    if not anchors and sections:
        mid = sections[len(sections) // 2]
        anchors.append((mid["printed_start"], f"{mid['title']} start (from contents)"))
    return anchors[:3]


# ------------------------------------------------------------------------------ cli


def build_page_map(*, force: bool = False, probe_count: int = 5) -> dict[str, Any]:
    settings = get_settings()
    pdf = settings.require_handbook()
    pdf_sha = sha256_file(pdf)
    total_pages = page_count(pdf)

    if PAGE_MAP_PATH.is_file() and not force:
        existing = json.loads(PAGE_MAP_PATH.read_text())
        if existing.get("pdf_sha256") == pdf_sha:
            print(f"page_map.json is current for {pdf.name} (sha {pdf_sha[:12]}). Use --force.")
            return dict(existing)

    client = get_client(settings)
    model, effort = settings.ingest_model, settings.ingest_effort
    total_usage = Usage()

    print(f"PDF: {pdf.name}")
    print(f"  sha256 {pdf_sha}")
    print(f"  {total_pages} physical pages")
    print(f"  model  {model} (effort={effort})\n")

    print(f"[1/3] Reading cover + contents (physical pages 1-{FRONT_MATTER_PAGES})...")
    payload, usage = read_contents(
        client, pdf, pdf_sha, model=model, effort=effort, front_pages=FRONT_MATTER_PAGES
    )
    total_usage.merge(usage)
    print(
        f"      {len(payload.get('contents', []))} contents entries, "
        f"{len(payload.get('figures', []))} figures, "
        f"{len(payload.get('tables', []))} tables, "
        f"{len(payload.get('illustrations', []))} illustrations "
        f"({usage.latency_ms} ms)"
    )

    probe_pages = choose_probe_pages(total_pages, probe_count)
    print(f"\n[2/3] Reading footers of physical pages {probe_pages} to calibrate the offset...")
    probes, usage = probe_footers(client, pdf, pdf_sha, probe_pages, model=model, effort=effort)
    total_usage.merge(usage)
    calibration = derive_offset(probes)
    for obs in calibration["observations"]:
        print(
            f"      pdf p.{obs['pdf_page']:>3} prints "
            f"{str(obs['printed_page']):>6}  offset {obs['offset']}"
        )
    offset = calibration["printed_to_pdf"]
    if calibration["constant"]:
        print(f"      constant offset: pdf_page = printed_page + {offset}")
    else:
        print(f"      WARNING offset is not constant: {calibration['offsets_seen']}")

    sections = build_sections(
        payload.get("contents", []), offset, payload.get("highest_printed_page_seen")
    )

    checks: list[dict[str, Any]] = []
    if offset is not None:
        anchors = pick_anchors(payload, sections)
        print(f"\n[3/3] Confirming the offset against {len(anchors)} known anchor(s)...")
        checks, usage = confirm_anchors(
            client, pdf, pdf_sha, anchors, offset, total_pages, model=model, effort=effort
        )
        total_usage.merge(usage)
        for check in checks:
            mark = "OK  " if check["match"] else "FAIL"
            print(
                f"      {mark} printed p.{check['expected_printed_page']} -> "
                f"pdf p.{check['pdf_page']}, footer read as "
                f"{check['observed_printed_page']}  [{check['reason']}]"
            )
    else:
        print("\n[3/3] Skipped anchor confirmation: no constant offset to confirm.")

    page_map = {
        "page_map_version": PAGE_MAP_VERSION,
        "pdf_path": str(pdf.relative_to(pdf.parents[1])),
        "pdf_sha256": pdf_sha,
        "pdf_physical_pages": total_pages,
        "model": model,
        "effort": effort,
        "extracted_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "document": {
            "title": payload.get("document_title"),
            "subtitle": payload.get("document_subtitle"),
            "publisher": payload.get("publisher"),
            "publication_date": payload.get("publication_date"),
            "edition_or_version": payload.get("edition_or_version"),
            "highest_printed_page_in_contents": payload.get("highest_printed_page_seen"),
        },
        "calibration": {
            "printed_to_pdf_offset": offset,
            "constant": calibration["constant"],
            "offsets_seen": calibration["offsets_seen"],
            "probes": calibration["observations"],
            "anchor_checks": checks,
            "all_anchors_matched": bool(checks) and all(c["match"] for c in checks),
            "formula": "pdf_page = printed_page + printed_to_pdf_offset",
        },
        "sections": sections,
        "figures": payload.get("figures", []),
        "tables": payload.get("tables", []),
        "illustrations": payload.get("illustrations", []),
        "usage": total_usage.as_dict(model),
    }

    PAGE_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    PAGE_MAP_PATH.write_text(json.dumps(page_map, indent=2, ensure_ascii=False) + "\n")
    print(f"\nWrote {PAGE_MAP_PATH.relative_to(pdf.parents[1])}")
    print(
        f"Ingestion cost so far: {total_usage.calls} calls, "
        f"{total_usage.input_tokens + total_usage.cache_read_input_tokens:,} input tokens "
        f"({total_usage.cache_read_input_tokens:,} from cache), "
        f"{total_usage.output_tokens:,} output tokens, "
        f"~${total_usage.cost_usd(model):.2f}"
    )
    return page_map


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-extract even if up to date")
    parser.add_argument("--probes", type=int, default=5, help="calibration probe pages (max 5)")
    args = parser.parse_args(argv)
    try:
        build_page_map(force=args.force, probe_count=max(2, min(5, args.probes)))
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
