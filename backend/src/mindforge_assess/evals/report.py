"""Render eval results as Markdown: one run, or two models side by side."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ..config import EVALS_DIR

RESULTS_DIR = EVALS_DIR / "results"
TIERS = ("low", "medium", "high")


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def _ratio(block: dict[str, Any] | None, numerator: str, denominator: str) -> str:
    if not block:
        return "—"
    return f"{block[numerator]}/{block[denominator]}"


def render(result: dict[str, Any]) -> str:
    """A Markdown summary of one eval run."""
    summary = result["summary"]
    lines = [
        f"# Eval run — {result['model']}",
        "",
        f"`{result['run_id']}` · {result['cases']} cases × {result['n']} runs "
        f"· effort `{result['effort']}` · pack v{result['pack_version']}",
        "",
        "## Headline",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Overall check accuracy | **{_pct(summary['overall_accuracy'])}** "
        f"({summary['checks_graded']} graded assertions) |",
        f"| Tier exactly right | {_pct(_accuracy(summary, 'inherent_risk_tier'))} |",
        f"| Tier within tolerance | {_pct(_accuracy(summary, 'tier_within_tolerance'))} |",
        f"| Tier consistency across runs | "
        f"{_pct(summary['tier_consistency']['mean_modal_agreement'])} "
        f"({summary['tier_consistency']['unanimous_cases']}/{result['cases']} unanimous) |",
        f"| Median latency | {summary['latency_ms']['p50'] / 1000:.1f}s "
        f"(p95 {summary['latency_ms']['p95'] / 1000:.1f}s) |",
        f"| Cost per assessment | ${summary['cost_usd']['per_assessment']:.4f} "
        f"(${summary['cost_usd']['total']:.2f} for the run) |",
        f"| Prompt cache hit rate | {_pct(summary['tokens']['cache_hit_rate'])} |",
        f"| Runs with no answer | {_failures(summary)} |",
        "",
        "## Per-field accuracy",
        "",
        "| Field | Accuracy | Passed |",
        "| --- | --- | --- |",
    ]
    for name, block in summary["field_accuracy"].items():
        lines.append(
            f"| `{name}` | {_pct(block['accuracy'])} | {block['passed']}/{block['graded']} |"
        )

    lines += [
        "",
        "## Recall against the handbook",
        "",
        "| Metric | Recall | Matched |",
        "| --- | --- | --- |",
    ]
    for name, block in summary["recall"].items():
        lines.append(
            f"| {name.replace('_', ' ')} | {_pct(block['recall'])} | "
            f"{block['matched']}/{block['expected']} |"
        )

    lines += [
        "",
        "## Tier confusion matrix",
        "",
        "Rows are the gold tier, columns what the tool returned.",
        "",
    ]
    lines.append("| gold ＼ returned | " + " | ".join(TIERS) + " |")
    lines.append("| --- | " + " | ".join("---" for _ in TIERS) + " |")
    matrix = summary["tier_confusion"]
    for expected in TIERS:
        row = matrix.get(expected, {})
        cells = []
        for returned in TIERS:
            count = row.get(returned, 0)
            cells.append(f"**{count}**" if count and expected == returned else str(count))
        lines.append(f"| **{expected}** | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Per case",
        "",
        "| Case | Checks | Tiers returned | Model's own tier | Failed fields |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in summary["per_case"]:
        tiers = ", ".join(case["tiers"]) or "—"
        model_tiers = ", ".join(t for t in case["model_tiers"] if t) or "—"
        failed = ", ".join(f"`{k}`×{v}" for k, v in case["failed_fields"].items()) or "—"
        lines.append(
            f"| `{case['case_id']}` | {case['checks_passed']}/{case['checks_graded']} "
            f"| {tiers} | {model_tiers} | {failed} |"
        )

    misses = [c for c in summary["per_case"] if c["missing"] or c["failed_fields"]]
    if misses:
        lines += ["", "## What it missed", ""]
        for case in misses:
            lines.append(f"**`{case['case_id']}` — {case['title']}**")
            lines.append(f"> {case['tests']}")
            lines.append("")
            for field_name, count in case["failed_fields"].items():
                lines.append(f"- `{field_name}` wrong in {count} of {case['runs']} run(s)")
            for missing in case["missing"]:
                lines.append(f"- did not cite: {missing}")
            lines.append("")

    if summary["errors"]:
        lines += ["", "## API errors", ""]
        for error in summary["errors"]:
            kind = error.get("kind") or "api"
            lines.append(
                f"- `{error['case_id']}` run {error['run']} ({kind}): {error['error']}"
            )

    return "\n".join(lines).rstrip() + "\n"


def _failures(summary: dict[str, Any]) -> str:
    """Upstream faults and model-side schema failures, counted apart."""
    kinds = summary.get("errors_by_kind") or {}
    if not kinds:
        # Older results predate the upstream/model split; do not invent a breakdown.
        kinds = Counter(
            error["kind"] for error in summary["errors"] if error.get("kind")
        )
    retries = summary["retries"]
    # Retries are worth stating even at zero failures: they are the transient upstream
    # faults the run survived, and the reason the number above them is clean.
    retried = f"{retries} retr{'y' if retries == 1 else 'ies'} succeeded" if retries else ""
    if not summary["runs_errored"]:
        return f"0 of {summary['runs']}" + (f" ({retried})" if retried else "")
    parts = [
        f"{count} {'upstream' if kind == 'api' else kind.replace('_', ' ')}"
        for kind, count in sorted(kinds.items())
    ]
    if retried:
        parts.append(retried)
    detail = f" ({', '.join(parts)})" if parts else ""
    return f"{summary['runs_errored']} of {summary['runs']}{detail}"


def _accuracy(summary: dict[str, Any], field_name: str) -> float | None:
    block = summary["field_accuracy"].get(field_name)
    return block["accuracy"] if block else None


def _recall(result: dict[str, Any], name: str) -> float | None:
    block = result["summary"]["recall"].get(name)
    return block["recall"] if block else None


# ------------------------------------------------------------------ comparison


def latest_for(model: str, results_dir: Path | None = None) -> dict[str, Any] | None:
    directory = (results_dir or RESULTS_DIR) / slug(model)
    if not directory.is_dir():
        return None
    files = sorted(directory.glob("*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text())


def all_latest(results_dir: Path | None = None) -> list[dict[str, Any]]:
    directory = results_dir or RESULTS_DIR
    if not directory.is_dir():
        return []
    results = []
    for model_dir in sorted(directory.iterdir()):
        if not model_dir.is_dir():
            continue
        files = sorted(model_dir.glob("*.json"))
        if files:
            results.append(json.loads(files[-1].read_text()))
    return results


def compare(results: list[dict[str, Any]]) -> str:
    """Two or more models' latest runs, side by side."""
    if not results:
        return "# Model comparison\n\nNo eval results yet. Run `make evals`.\n"

    models = [r["model"] for r in results]
    header = "| Metric | " + " | ".join(f"`{m}`" for m in models) + " |"
    divider = "| --- | " + " | ".join("---" for _ in models) + " |"
    lines = [
        "# Model comparison",
        "",
        "Latest run per model, same gold set, same prompt, same policy layer.",
        "",
        header,
        divider,
    ]

    def row(label: str, fn: Any) -> None:
        lines.append(f"| {label} | " + " | ".join(fn(r) for r in results) + " |")

    row("Cases × runs", lambda r: f"{r['cases']} × {r['n']}")
    row("Effort", lambda r: f"`{r['effort']}`")
    row("Overall check accuracy", lambda r: _pct(r["summary"]["overall_accuracy"]))
    row("Tier exactly right", lambda r: _pct(_accuracy(r["summary"], "inherent_risk_tier")))
    row("Tier within tolerance", lambda r: _pct(_accuracy(r["summary"], "tier_within_tolerance")))
    row("Scope (`ai_in_scope`)", lambda r: _pct(_accuracy(r["summary"], "ai_in_scope")))
    row("AI type", lambda r: _pct(_accuracy(r["summary"], "ai_type")))
    row("Oversight mode", lambda r: _pct(_accuracy(r["summary"], "recommended_oversight_mode")))
    row("Dimension floors met", lambda r: _pct(_recall(r, "dimension_floors")))
    row("Top-10 recall", lambda r: _pct(_recall(r, "top_10_flags")))
    row("Consideration recall", lambda r: _pct(_recall(r, "considerations")))
    row(
        "Tier consistency",
        lambda r: _pct(r["summary"]["tier_consistency"]["mean_modal_agreement"]),
    )
    row("Median latency", lambda r: f"{r['summary']['latency_ms']['p50'] / 1000:.1f}s")
    row("p95 latency", lambda r: f"{r['summary']['latency_ms']['p95'] / 1000:.1f}s")
    row("Cost per assessment", lambda r: f"${r['summary']['cost_usd']['per_assessment']:.4f}")
    row("Output tokens (total)", lambda r: f"{r['summary']['tokens']['output']:,}")
    row("API errors", lambda r: str(r["summary"]["runs_errored"]))

    lines += [
        "",
        "## Where they disagree",
        "",
        "Cases where the models returned different tiers.",
        "",
    ]
    by_case: dict[str, dict[str, list[str]]] = {}
    for result in results:
        for case in result["summary"]["per_case"]:
            by_case.setdefault(case["case_id"], {})[result["model"]] = case["tiers"]

    disagreements = 0
    lines.append("| Case | " + " | ".join(f"`{m}`" for m in models) + " |")
    lines.append(divider)
    for case_id, tiers_by_model in by_case.items():
        distinct = {tuple(sorted(set(tiers_by_model.get(m, [])))) for m in models}
        if len(distinct) <= 1:
            continue
        disagreements += 1
        cells = [_tally(tiers_by_model.get(m, [])) for m in models]
        lines.append(f"| `{case_id}` | " + " | ".join(cells) + " |")
    if not disagreements:
        lines = lines[:-2]
        lines.append("_The models agreed on the tier for every case._")

    return "\n".join(lines).rstrip() + "\n"


def _tally(tiers: list[str]) -> str:
    """`high ×2, medium ×1` -- repeats matter here, they are the inconsistency."""
    counts = Counter(tiers)
    return ", ".join(f"{tier} ×{counts[tier]}" for tier in TIERS if tier in counts) or "—"


def slug(model: str) -> str:
    return model.replace("/", "-").replace(":", "-")
