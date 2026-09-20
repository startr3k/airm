"""Generate docs/FRAMEWORK_NOTES.md from the framework pack.

The notes are generated, never hand-written, so they cannot drift from the pack the
assessor actually reads. Every claim carries the printed page it came from.

Run:  python -m mindforge_assess.ingest.notes
"""

from __future__ import annotations

import sys
from typing import Any

from ..config import DOCS_DIR, REPO_ROOT
from .build_pack import PACK_PATH, PackError, counts, load_pack

NOTES_PATH = DOCS_DIR / "FRAMEWORK_NOTES.md"


def cite(source: dict[str, Any] | None) -> str:
    if not source or not source.get("page"):
        return ""
    return f" (p. {source['page']})"


def esc(text: object, limit: int = 300) -> str:
    """Make a value safe for a Markdown table cell."""
    flat = " ".join(str(text or "").split())
    if len(flat) > limit:
        flat = flat[: limit - 1].rstrip() + "…"
    return flat.replace("|", "\\|")


def _matrix_table(matrix: dict[str, Any]) -> list[str]:
    cells = matrix.get("cells") or []
    if not cells:
        return ["_The matrix was not extracted._", ""]
    rows = matrix.get("axis_evaluation_values") or sorted(
        {str(c["evaluation_result"]) for c in cells}
    )
    order = {"low": 0, "medium": 1, "high": 2}
    tiers = sorted({str(c["inherent_tier"]) for c in cells}, key=lambda t: order.get(t, 9))
    lookup = {(str(c["inherent_tier"]), str(c["evaluation_result"])): c for c in cells}

    header = "| Evaluation result \\ Inherent materiality | " + " | ".join(
        f"**{t}**" for t in tiers
    ) + " |"
    lines = [header, "| --- | " + " | ".join("---" for _ in tiers) + " |"]
    for row in rows:
        values = []
        for tier in tiers:
            cell = lookup.get((tier, row))
            values.append(esc(cell["residual_label"]) if cell else "—")
        lines.append(f"| {esc(row)} | " + " | ".join(values) + " |")
    lines.append("")
    if matrix.get("failure_to_meet_minimum_note"):
        lines += [f"> {esc(matrix['failure_to_meet_minimum_note'], 400)}", ""]
    if matrix.get("always_high_note"):
        applies = matrix.get("always_high_note_applies_to")
        suffix = f" — printed against {esc(applies, 200)}" if applies else ""
        lines += [f"> {esc(matrix['always_high_note'], 400)}{suffix}", ""]
    return lines


def render(pack: dict[str, Any]) -> str:
    p = pack["provenance"]
    doc = p.get("document", {})
    completeness = p["completeness"]
    stats = counts(pack)
    lines: list[str] = [
        "# Framework notes",
        "",
        "<!-- GENERATED FILE -- do not edit by hand.",
        "     Regenerate with: python -m mindforge_assess.ingest.notes -->",
        "",
        f"What the tool encodes from *{doc.get('title') or 'the handbook'}*",
        f"({doc.get('publisher') or 'unknown publisher'}, "
        f"{doc.get('publication_date') or 'n.d.'}).",
        "",
        "Page numbers are **printed** page numbers — what a reader sees in the footer.",
        f"The PDF's physical pages run {p['printed_to_pdf_offset']} ahead "
        f"(`pdf_page = printed_page + {p['printed_to_pdf_offset']}`).",
        "",
        "## Provenance",
        "",
        "| | |",
        "| --- | --- |",
        f"| Source PDF | `{p['pdf_filename']}` |",
        f"| SHA-256 | `{p['pdf_sha256']}` |",
        f"| Physical pages | {p['pdf_physical_pages']} |",
        f"| Extraction model | `{p['model']}` |",
        f"| Extracted | {p.get('extracted_at')} |",
        f"| Pack built | {p.get('built_at')} |",
        f"| Sections present | {len(completeness['present'])} of {len(completeness['expected'])} |",
        "",
    ]
    verification = p.get("verification") or {}
    if verification:
        lines += [
            f"Verified by `{verification.get('model')}` on {verification.get('verified_at')}: "
            f"**{verification.get('blocking_failures', 0)}** blocking failure(s). "
            "See [verification_report.md](../backend/framework/verification_report.md).",
            "",
        ]
    if completeness["partial"]:
        lines += [
            "> **This pack is partial.** Not yet extracted: "
            + ", ".join(f"`{n}`" for n in completeness["missing"])
            + ". Sections below that depend on them are empty.",
            "",
        ]

    lines += ["## What was extracted", "", "| Item | Count |", "| --- | --- |"]
    lines += [f"| {k.replace('_', ' ').capitalize()} | {v} |" for k, v in stats.items()]
    lines.append("")

    # --- scope ---------------------------------------------------------------
    definitions = pack["definitions"]
    lines += ["## Scope: what counts as AI (Section 1.1)", ""]
    ai_def = definitions.get("ai_definition") or {}
    if ai_def.get("definition"):
        lines += [f"> {esc(ai_def['definition'], 800)}{cite(ai_def.get('source'))}", ""]
    else:
        lines += ["_Not yet extracted._", ""]
    if definitions.get("out_of_scope_examples"):
        lines += [
            "Out of scope — an `ai_in_scope: false` short-circuit in the assessor:",
            "",
        ]
        for item in definitions["out_of_scope_examples"]:
            why = f" — {esc(item.get('why'), 200)}" if item.get("why") else ""
            lines.append(f"- {esc(item.get('example'))}{why}{cite(item.get('source'))}")
        lines.append("")
    if definitions.get("in_scope_examples"):
        lines += ["In scope:", ""]
        for item in definitions["in_scope_examples"]:
            lines.append(f"- {esc(item.get('example'))}{cite(item.get('source'))}")
        lines.append("")
    if definitions.get("terms"):
        lines += ["| Term | Definition | Page |", "| --- | --- | --- |"]
        for term in definitions["terms"]:
            page = (term.get("source") or {}).get("page", "")
            lines.append(f"| {esc(term.get('term'))} | {esc(term.get('definition'))} | {page} |")
        lines.append("")

    # --- materiality ---------------------------------------------------------
    materiality = pack["materiality"]
    lines += ["## Inherent risk materiality (Section 2.4)", ""]
    if materiality["factors"]:
        lines += ["| Factor | What it covers | Page |", "| --- | --- | --- |"]
        for factor in materiality["factors"]:
            page = (factor.get("source") or {}).get("page", "")
            lines.append(
                f"| **{esc(factor.get('factor'), 120)}** | "
                f"{esc(factor.get('description'), 260)} | {page} |"
            )
        lines.append("")
    else:
        lines += ["_Not yet extracted._", ""]
    if materiality.get("tiering_method"):
        lines += [f"**Combining factors:** {esc(materiality['tiering_method'], 600)}", ""]
    if materiality["tiers"]:
        lines += ["| Tier | Printed as | Definition | Page |", "| --- | --- | --- | --- |"]
        for tier in materiality["tiers"]:
            page = (tier.get("source") or {}).get("page", "")
            lines.append(
                f"| `{tier.get('tier')}` | {esc(tier.get('printed_name'))} | "
                f"{esc(tier.get('definition'), 240)} | {page} |"
            )
        lines.append("")

    matrix = materiality["matrix"]
    lines += [
        f"### {matrix.get('label', 'Figure 2.4.3')}: inherent → residual"
        f"{cite(matrix.get('source'))}",
        "",
        f"_{esc(matrix.get('caption'), 200)}_",
        "",
    ]
    lines += _matrix_table(matrix)
    if materiality.get("residual_risk_logic"):
        lines += [
            "**How residual materiality is derived:** "
            + esc(materiality["residual_risk_logic"], 900),
            "",
        ]

    # --- dimensions ----------------------------------------------------------
    lines += ["## Risk dimensions (Appendix B)", ""]
    if pack["dimensions"]:
        lines += ["| Dimension | Risks | ABS top-10 | Page |", "| --- | --- | --- | --- |"]
        for dimension in pack["dimensions"]:
            risks = dimension.get("risks", [])
            top10 = sum(1 for r in risks if r.get("is_abs_top_10"))
            page = (dimension.get("source") or {}).get("page", "")
            lines.append(
                f"| **{esc(dimension['dimension'])}** | {len(risks)} | {top10} | {page} |"
            )
        lines.append("")
        for dimension in pack["dimensions"]:
            lines += [f"### {dimension['dimension']}", ""]
            for risk in dimension.get("risks", []):
                flag = " **[ABS top-10]**" if risk.get("is_abs_top_10") else ""
                lines.append(
                    f"- **{esc(risk.get('name'), 120)}**{flag} — "
                    f"{esc(risk.get('description'), 260)}{cite(risk.get('source'))}"
                )
            lines.append("")
    else:
        lines += ["_Not yet extracted._", ""]

    # --- oversight and monitoring -------------------------------------------
    lines += ["## Human oversight modes (Section 3.1)", ""]
    if pack["oversight_modes"]:
        lines += ["| Mode | Printed as | Definition | Page |", "| --- | --- | --- | --- |"]
        for mode in pack["oversight_modes"]:
            page = (mode.get("source") or {}).get("page", "")
            lines.append(
                f"| `{mode['mode']}` | {esc(mode.get('printed_name'))} | "
                f"{esc(mode.get('definition'), 240)} | {page} |"
            )
        lines.append("")
    else:
        lines += ["_Not yet extracted._", ""]

    monitoring = pack["monitoring"]
    if monitoring["sampling_methodologies"] or monitoring["interruption_controls"]:
        lines += ["## Monitoring and interruption (Sections 3.4–3.5)", ""]
        if monitoring["sampling_methodologies"]:
            label = monitoring.get("sampling_table_label") or "Sampling methodologies"
            lines += [f"**{esc(label)}**", "", "| Method | Description | Page |",
                      "| --- | --- | --- |"]
            for method in monitoring["sampling_methodologies"]:
                page = (method.get("source") or {}).get("page", "")
                description = esc(method.get("description"), 240)
                lines.append(f"| {esc(method.get('name'))} | {description} | {page} |")
            lines.append("")
        if monitoring["interruption_controls"]:
            lines += ["**Interruption controls** (what an agentic use case must have):", ""]
            for control in monitoring["interruption_controls"]:
                lines.append(
                    f"- **{esc(control.get('control'), 120)}** — "
                    f"{esc(control.get('description'), 240)}{cite(control.get('source'))}"
                )
            lines.append("")

    # --- libraries -----------------------------------------------------------
    for key, title, name_field, desc_field in (
        ("metrics", "Metrics library (Appendix F)", "name", "definition"),
        ("guardrails", "Guardrails library (Appendix G)", "name", "description"),
    ):
        lines += [f"## {title}", ""]
        items = pack[key]
        if items:
            lines += ["| Name | Description | AI types | Page |", "| --- | --- | --- | --- |"]
            for item in items:
                page = (item.get("source") or {}).get("page", "")
                types = ", ".join(item.get("ai_types") or []) or "—"
                lines.append(
                    f"| **{esc(item.get(name_field), 90)}** | "
                    f"{esc(item.get(desc_field), 220)} | {esc(types, 60)} | {page} |"
                )
            lines.append("")
        else:
            lines += ["_Not yet extracted._", ""]

    if pack.get("interpretability_typology"):
        lines += ["### Interpretability typology", ""]
        for item in pack["interpretability_typology"]:
            lines.append(
                f"- **{esc(item.get('name'))}** — "
                f"{esc(item.get('definition'), 260)}{cite(item.get('source'))}"
            )
        lines.append("")

    # --- considerations ------------------------------------------------------
    lines += ["## The Considerations (Appendix H)", ""]
    if pack["considerations"]:
        for consideration in pack["considerations"]:
            practices = consideration.get("implementation_practices", [])
            lines += [
                f"### {consideration['number']}. {esc(consideration.get('title'), 200)}"
                f"{cite(consideration.get('source'))}",
                "",
            ]
            for practice in practices:
                ref = f"**{esc(practice['reference'])}** " if practice.get("reference") else ""
                lines.append(f"- {ref}{esc(practice.get('text'), 400)}")
            lines.append("")
    else:
        lines += ["_Not yet extracted._", ""]

    # --- agentic -------------------------------------------------------------
    agentic = pack["agentic"]
    lines += ["## Agentic AI (Future Perspectives)", ""]
    if agentic.get("accountability_principle"):
        lines += [f"> {esc(agentic['accountability_principle'], 600)}", ""]
    for key, heading in (
        ("agentic_risk_factors", "Risk factors"),
        ("tool_access_risks", "Tool-access risks"),
    ):
        if agentic.get(key):
            lines += [f"**{heading}**", ""]
            for item in agentic[key]:
                lines.append(
                    f"- **{esc(item.get('factor'), 120)}** — "
                    f"{esc(item.get('description'), 240)}{cite(item.get('source'))}"
                )
            lines.append("")
    if agentic.get("never_delegate_examples"):
        lines += ["**Never delegate** — activities the handbook says keep a human decision:", ""]
        for item in agentic["never_delegate_examples"]:
            why = f" — {esc(item.get('why'), 200)}" if item.get("why") else ""
            lines.append(f"- {esc(item.get('activity'))}{why}{cite(item.get('source'))}")
        lines.append("")
    if agentic.get("interruption_controls"):
        lines += ["**Interruption controls**", ""]
        for item in agentic["interruption_controls"]:
            lines.append(
                f"- **{esc(item.get('control'), 120)}** — "
                f"{esc(item.get('description'), 240)}{cite(item.get('source'))}"
            )
        lines.append("")
    if not any(agentic.get(k) for k in ("agentic_risk_factors", "interruption_controls")):
        lines += ["_Not yet extracted._", ""]

    # --- illustrations -------------------------------------------------------
    lines += ["## Financial-institution illustrations", "",
              "Used as few-shot material for the assessor.", ""]
    if pack["illustrations"]:
        for item in pack["illustrations"]:
            lines += [
                f"### {esc(item.get('label'))}: {esc(item.get('institution'))}"
                f"{cite(item.get('source'))}",
                "",
                esc(item.get("summary"), 900),
                "",
            ]
            for practice in item.get("practices", []):
                lines.append(f"- {esc(practice, 300)}")
            lines.append("")
    else:
        lines += ["_Not yet extracted._", ""]

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    try:
        pack = load_pack()
    except PackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTES_PATH.write_text(render(pack))
    relative = NOTES_PATH.relative_to(REPO_ROOT)
    print(f"Wrote {relative} from {PACK_PATH.name}")
    print(f"  {len(NOTES_PATH.read_text().splitlines())} lines")
    if pack["provenance"]["completeness"]["partial"]:
        missing = ", ".join(pack["provenance"]["completeness"]["missing"])
        print(f"  NOTE: partial pack -- sections not yet extracted: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
