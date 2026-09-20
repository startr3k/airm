"""Generate the assessor's system prompt from the framework pack.

The prompt is generated rather than hand-written so it cannot drift from the pack, and
the rendered result is checked into `system.rendered.md` so a pack change shows up as a
reviewable diff rather than a silent behaviour change.

It is the cached prefix of every assessment request, so it must be stable byte-for-byte:
no timestamps, no per-request text, deterministic ordering throughout.

Run:  python -m mindforge_assess.prompts.build_system_prompt [--check]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..pack import DIMENSIONS, Pack, load_pack

RENDERED_PATH = Path(__file__).parent / "system.rendered.md"

# Budget for the cached prefix. Roughly 4 characters per token is close enough to catch
# a prompt that has doubled; the exact count is verified with the API in --check.
TOKEN_BUDGET = 6000
# Measured against the API's count_tokens on this prompt: the usual 4 chars/token rule
# underestimated by ~28%, because dense semicolon-separated name lists tokenise poorly.
CHARS_PER_TOKEN = 2.9


def _trim(text: object, words: int) -> str:
    """Condense handbook prose to its first clause, keeping the prompt compact."""
    flat = " ".join(str(text or "").split())
    parts = flat.split()
    if len(parts) <= words:
        return flat
    return " ".join(parts[:words]).rstrip(",;:") + "…"


def _dimension_lines(pack: Pack) -> list[str]:
    by_name = {str(d["dimension"]): d for d in pack.dimensions}
    lines: list[str] = []
    for name in DIMENSIONS:
        dimension = by_name.get(name)
        if not dimension:
            continue
        risks = [str(r["name"]) for r in dimension.get("risks", [])]
        top10 = [str(r["name"]) for r in dimension.get("risks", []) if r.get("is_abs_top_10")]
        definition = _trim(dimension.get("definition") or "", 16)
        detail = f" {definition}" if definition else ""
        lines.append(f"- **{name}**.{detail}")
        lines.append(f"  Risks: {'; '.join(risks)}.")
        if top10:
            lines.append(f"  ABS top-10 among these: {'; '.join(top10)}.")
    return lines


def _matrix_lines(pack: Pack) -> list[str]:
    matrix = pack.matrix
    rows = matrix.get("axis_evaluation_values") or []
    order = {"low": 0, "medium": 1, "high": 2}
    tiers = sorted(
        {str(c["inherent_tier"]) for c in matrix.get("cells", [])},
        key=lambda t: order.get(t, 9),
    )
    lookup = {
        (str(c["inherent_tier"]), str(c["evaluation_result"])): c
        for c in matrix.get("cells", [])
    }
    lines = [f"| Evaluation result \\ Inherent | {' | '.join(tiers)} |"]
    lines.append("| --- | " + " | ".join("---" for _ in tiers) + " |")
    for row in rows:
        values = [
            str(lookup[(tier, row)]["residual_label"]) if (tier, row) in lookup else "—"
            for tier in tiers
        ]
        lines.append(f"| {row} | {' | '.join(values)} |")
    return lines


def _example(
    title: str,
    description: str,
    ai_type: str,
    tier: str,
    oversight: str,
    reasoning: str,
) -> list[str]:
    return [
        f"**{title}**",
        f"> {description}",
        f"`ai_type`: {ai_type} · `inherent_risk_tier`: **{tier}** · "
        f"`recommended_oversight_mode`: {oversight}",
        f"{reasoning}",
        "",
    ]


def _worked_examples(pack: Pack) -> list[str]:
    """Few-shot examples, grounded in the handbook's own FI illustrations."""
    by_institution = {str(i["institution"]): i for i in pack.illustrations}

    def cite(institution: str) -> str:
        item = by_institution.get(institution)
        if not item:
            return ""
        return f" (cf. {item['label']}, {institution}, p. {item['source']['page']})"

    lines: list[str] = ["## Worked examples", ""]
    lines += _example(
        "Internal knowledge chatbot",
        "A RAG assistant over internal HR and IT policy documents, used by staff only. "
        "It answers questions and cites the source document. No customer contact.",
        "gen_ai",
        "low",
        "human_over_the_loop",
        "Few stakeholders, no customer impact, no personal data beyond the employee's own "
        "question, and an employee can simply check the cited document. The handbook uses "
        "this exact case as its example of a use case whose limited potential for harm "
        "keeps it low regardless of evaluation results (Figure 2.4.3 discussion, p. 51). "
        "Transparency and Robustness still rate medium because staff may act on a "
        "hallucinated policy answer.",
    )
    lines += _example(
        "Insurance claims triage with a human decision-maker",
        "A model that scores incoming motor claims for likely fraud and routes them, with "
        "every declined or escalated claim decided by a human assessor."
        + cite("Income Insurance"),
        "traditional",
        "medium",
        "human_in_the_loop",
        "Real financial and recourse impact on customers, and Fairness & Bias matters "
        "because training data may under-represent some groups. It is medium rather than "
        "high because a human makes every adverse decision, so the customer retains "
        "recourse and the automation is bounded. Had the model auto-declined claims, this "
        "would be high.",
    )
    lines += _example(
        "Credit underwriting",
        "A model that assesses creditworthiness and recommends approve/decline on personal "
        "loan applications, with adverse decisions reviewed by a credit officer.",
        "traditional",
        "high",
        "human_in_the_loop",
        "The handbook names credit decisioning as its example of a use case that stays "
        "high unless it achieves a particularly high standard of fairness, accuracy and "
        "reliability (p. 51). Severe impact on individuals, limited recourse, direct "
        "regulatory exposure, and Fairness & Bias is the dominant dimension. Human review "
        "of adverse decisions does not reduce the INHERENT tier -- it is a control, and "
        "controls bear on residual risk, not inherent risk.",
    )
    lines += _example(
        "Agentic relationship-manager assistant with trade execution",
        "A multi-agent assistant that researches client portfolios, drafts proposals, "
        "emails clients and can place trades within preset limits."
        + cite("UOB"),
        "agentic",
        "high",
        "human_in_the_loop",
        "Agenticness, tool access and attack surface all compound (Future Perspectives). "
        "It acts on the world irreversibly: trades settle and emails cannot be unsent. "
        "Accountability follows control, so the firm remains accountable for what the "
        "agent does. Placing trades and sending client communications belong in "
        "`never_delegate_flags`; the assessment must name concrete interruption controls "
        "and least-privilege scoping.",
    )
    return lines


def build(pack: Pack | None = None) -> str:
    pack = pack or load_pack()
    definitions = pack.definitions
    materiality = pack.materiality
    provenance = pack.provenance

    ai_definition = _trim((definitions.get("ai_definition") or {}).get("definition"), 70)
    out_of_scope = [
        f"{_trim(x.get('example'), 14)} (p. {x['source']['page']})"
        for x in definitions.get("out_of_scope_examples", [])[:6]
    ]
    in_scope = [_trim(x.get("example"), 12) for x in definitions.get("in_scope_examples", [])[:5]]

    lines: list[str] = [
        "# Role",
        "",
        "You are an AI risk analyst at a Singapore financial institution. You classify a "
        "described AI use case against the MindForge AI Risk Management Operationalisation "
        f"Handbook ({provenance['document'].get('publisher', 'MindForge')}, "
        f"{provenance['document'].get('publication_date', 'Jan 2026')}), and you record "
        f"your assessment by calling the `record_risk_assessment` tool.",
        "",
        "You assess **inherent** risk materiality: the risk before controls. Do not lower a "
        "rating because a control is described -- controls bear on residual risk, which "
        "needs real evaluation evidence you do not have.",
        "",
        "Work in this order: restate the use case, decide whether it is AI at all, rate "
        "every materiality factor, and only then choose an overall tier. The tier must "
        "follow from the factors you rated, not the other way round.",
        "",
        "Where the description does not say something, say so in `assessor_notes` and rate "
        "conservatively. Never invent facts about the system to fill a gap, and never "
        "invent a guardrail, metric or risk name -- use the handbook's names, given below.",
        "",
        "## What counts as AI (Section 1.1)",
        "",
        f"{_trim(ai_definition, 55)}",
        "",
        "**In scope**: " + "; ".join(in_scope) + ".",
        "",
        "**NOT in scope** — set `ai_in_scope` to false for these:",
    ]
    lines += [f"- {item}" for item in out_of_scope]
    lines += [
        "",
        "If it is not in scope, say why in `assessor_notes`; the rest of the assessment "
        "will be withheld automatically.",
        "",
        "`ai_type` classifies *how* it works, not how risky it is. Computer vision, OCR, "
        "face matching, liveness detection, scoring and classification models are "
        "**traditional** even when the risk is severe. **gen_ai** means a model that "
        "generates language, images or code. **agentic** means it plans and acts through "
        "tools.",
        "",
        "## Inherent risk materiality factors (Section 2.4)",
        "",
        "Rate EVERY factor below, using the handbook's wording for `factor`:",
        "",
    ]
    lines += [
        f"- **{_trim(f['factor'], 12)}** — {_trim(f['description'], 20)}"
        for f in materiality["factors"]
    ]
    lines += [
        "",
        "For Gen AI and agentic use cases, weight complexity, degree of autonomy, tool "
        "access and attack surface more heavily (Future Perspectives). A customer-facing "
        "use case with no human in the loop rates higher on reliance and automation.",
        "",
        "### Choosing the tier",
        "",
        "- **low** — limited potential for harm; few stakeholders; easy recourse.",
        "- **medium** — real impact on customers or the firm, but bounded, with recourse "
        "and a human in the decision path.",
        "- **high** — severe or irreversible impact on individuals, limited recourse, "
        "direct regulatory exposure, or autonomous consequential action.",
        "",
        "Figure 2.4.3 constrains how inherent materiality maps to residual materiality. "
        "You are not assessing residual risk, but this fixes the shape of the framework:",
        "",
    ]
    lines += _matrix_lines(pack)
    matrix = pack.matrix
    lines += [
        "",
        f"Read it as: a low-inherent use case cannot become high no matter how well it "
        f"evaluates, and a high-inherent use case stays high unless it meets best "
        f"practice — and even then the handbook records "
        f"'{_trim(matrix.get('always_high_note'), 24)}'",
        "",
        "## The seven risk dimensions (Appendix B)",
        "",
        "Rate all seven, every time. Use these taxonomy names in `key_risks`:",
        "",
    ]
    lines += _dimension_lines(pack)
    lines += [
        "",
        f"`top_10_flags` may only contain these ABS top-10 risks: "
        f"{'; '.join(pack.abs_top_10())}.",
        "",
        "## Human oversight modes (Section 3.1)",
        "",
    ]
    lines += [
        f"- **{m['mode']}** ({m.get('printed_name')}) — {_trim(m.get('definition'), 26)}"
        for m in pack.oversight_modes
    ]
    lines += [
        "",
        "Higher materiality warrants a human closer to the decision. A high-tier use case "
        "should not be human_out_of_the_loop.",
        "",
        "## Libraries you must cite from",
        "",
        "`recommended_guardrails[].guardrail` must be a name from Appendix G:",
        "",
        "  " + "; ".join(pack.guardrail_names()),
        "",
        "`recommended_metrics[]` must be a name from Appendix F:",
        "",
        "  " + "; ".join(pack.metric_names()),
        "",
        "Recommend guardrails and metrics proportionate to the tier: a handful for low, "
        "more and stricter for high. Cite the appendix and printed page in `handbook_ref`.",
        "",
        "`relevant_considerations[]` are numbers from Appendix H:",
        "",
    ]
    lines += [
        f"{c['number']}. {_trim(c['title'], 11)}" for c in pack.considerations
    ]
    lines += ["", *_worked_examples(pack)]
    lines += [
        "## Calibration",
        "",
        "- Do not inflate everything to high; a low-risk internal tool rated high is as "
        "wrong as a credit model rated low, and makes the tool useless.",
        "- `confidence` reflects how much the description actually told you. A two-line "
        "description cannot support high confidence.",
        "- `agentic_considerations` is null unless the system plans and acts through tools.",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def estimate_tokens(prompt: str) -> int:
    return int(len(prompt) / CHARS_PER_TOKEN)


def count_tokens_via_api(prompt: str, model: str) -> int | None:
    """Exact count via the API when a key is available; None when it is not."""
    try:
        from ..config import get_settings
        from ..llm import get_client

        client = get_client(get_settings())
        result = client.messages.count_tokens(
            model=model,
            system=[{"type": "text", "text": prompt}],
            messages=[{"role": "user", "content": "x"}],
        )
        return int(result.input_tokens)
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail if the rendered file is out of date"
    )
    args = parser.parse_args(argv)

    prompt = build()
    estimated = estimate_tokens(prompt)

    if args.check:
        if not RENDERED_PATH.is_file():
            print(f"error: {RENDERED_PATH.name} has never been rendered", file=sys.stderr)
            return 1
        if RENDERED_PATH.read_text() != prompt:
            print(
                f"error: {RENDERED_PATH.name} is out of date with the pack. "
                "Run: python -m mindforge_assess.prompts.build_system_prompt",
                file=sys.stderr,
            )
            return 1
        print(f"{RENDERED_PATH.name} is current ({estimated:,} tokens estimated)")
        return 0

    RENDERED_PATH.write_text(prompt)
    print(f"Wrote {RENDERED_PATH}")
    print(f"  {len(prompt):,} characters, ~{estimated:,} tokens estimated")

    from ..config import get_settings

    settings = get_settings()
    if settings.has_api_key:
        exact = count_tokens_via_api(prompt, settings.assess_model)
        if exact is not None:
            print(f"  {exact:,} tokens exactly (count_tokens, {settings.assess_model})")
            estimated = exact
    if estimated > TOKEN_BUDGET:
        print(f"  WARNING over the {TOKEN_BUDGET:,}-token budget for the cached prefix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
