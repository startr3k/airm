"""Merge verified extractions into the versioned framework pack.

The pack is the only thing the assessor, the API and the front end read at runtime --
the handbook PDF and an API key are needed for ingestion, never for serving a request.
Every item carries a stable `item_id` and its `source`, so a citation shown in the UI can
be traced back to a printed page and a verbatim quote.

Run:  python -m mindforge_assess.ingest.build_pack [--allow-partial] [--allow-unverified]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema

from ..config import FRAMEWORK_DIR, ConfigError, get_settings
from ..llm import Usage
from .engine import EXTRACT_DIR
from .page_map import load_page_map
from .verify import RESULTS_PATH as VERIFICATION_PATH

PACK_PATH = FRAMEWORK_DIR / "pack.v1.json"
SCHEMA_PATH = FRAMEWORK_DIR / "pack.schema.json"
PACK_VERSION = 1

# Every extractor whose output the pack expects.
EXPECTED = (
    "definitions",
    "materiality_factors",
    "dimensions_taxonomy",
    "oversight_modes",
    "metrics",
    "guardrails",
    "considerations",
    "agentic",
    "illustrations",
)


class PackError(RuntimeError):
    pass


def slug(text: str, limit: int = 60) -> str:
    """A stable, URL-safe id fragment derived from an item's printed name."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return (cleaned[:limit].rstrip("-")) or "item"


def _ids(kind: str, items: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    """Attach `item_id` to each item, disambiguating collisions deterministically."""
    seen: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    for item in items:
        base = f"{kind}:{slug(item.get(field, ''))}"
        seen[base] = seen.get(base, 0) + 1
        item_id = base if seen[base] == 1 else f"{base}-{seen[base]}"
        out.append({"item_id": item_id, **item})
    return out


def _load(name: str) -> dict[str, Any] | None:
    path = EXTRACT_DIR / f"{name}.json"
    if not path.is_file():
        return None
    return dict(json.loads(path.read_text()))


def _data(payload: dict[str, Any] | None) -> dict[str, Any]:
    return dict((payload or {}).get("data") or {})


def build(*, allow_partial: bool = False, allow_unverified: bool = False) -> dict[str, Any]:
    settings = get_settings()
    page_map = load_page_map()

    payloads = {name: _load(name) for name in EXPECTED}
    present = [name for name, payload in payloads.items() if payload]
    missing = [name for name in EXPECTED if name not in present]
    if missing and not allow_partial:
        raise PackError(
            "no extraction on disk for: "
            + ", ".join(missing)
            + ".\nRun `make extract` first, or pass --allow-partial to build a pack "
            "without them (the pack records which sections are missing)."
        )

    verification: dict[str, Any] = {}
    if VERIFICATION_PATH.is_file():
        raw = json.loads(VERIFICATION_PATH.read_text())
        summaries = raw.get("summaries", [])
        blocking = sum(
            1
            for item in summaries
            if item.get("rows_short")
            or item.get("missing_rows")
            or item.get("meaning_errors")
        )
        verification = {
            "verified_at": raw.get("verified_at"),
            "model": raw.get("model"),
            "blocking_failures": blocking,
            "verified_extractors": [item["extractor"] for item in summaries],
            "summaries": [
                {
                    "extractor": item["extractor"],
                    "verdict": item["verdict"],
                    "quotes_checked": item["quotes_checked"],
                    "quotes_failed": item["quotes_failed"],
                    "verifier_counted_rows": item["verifier_counted_rows"],
                    "extracted_rows": item["extracted_rows"],
                }
                for item in summaries
            ],
        }
        if blocking and not allow_unverified:
            raise PackError(
                f"verification reports {blocking} blocking failure(s). "
                "Fix them or pass --allow-unverified."
            )
    elif not allow_unverified:
        raise PackError(
            "no verification.json on disk. Run `make verify`, or pass --allow-unverified."
        )

    definitions = _data(payloads["definitions"])
    materiality = _data(payloads["materiality_factors"])
    taxonomy = _data(payloads["dimensions_taxonomy"])
    oversight = _data(payloads["oversight_modes"])
    metrics = _data(payloads["metrics"])
    guardrails = _data(payloads["guardrails"])
    considerations = _data(payloads["considerations"])
    agentic = _data(payloads["agentic"])
    illustrations = _data(payloads["illustrations"])

    pack: dict[str, Any] = {
        "pack_version": PACK_VERSION,
        "provenance": {},
        "definitions": {
            "ai_definition": definitions.get("ai_definition"),
            "in_scope_examples": definitions.get("in_scope_examples", []),
            "out_of_scope_examples": definitions.get("out_of_scope_examples", []),
            "terms": definitions.get("terms", []),
            "abs_top_risks": definitions.get("abs_top_risks", []),
            "scope_notes": definitions.get("scope_notes", []),
        },
        "materiality": {
            "factors": _ids("factor", materiality.get("inherent_risk_factors", []), "factor"),
            "tiers": materiality.get("tiers", []),
            "tiering_method": materiality.get("tiering_method"),
            "residual_risk_logic": materiality.get("residual_risk_logic"),
            "agentic_or_genai_factors": materiality.get("agentic_or_genai_factors", []),
            "matrix": materiality.get("figure_2_4_3") or {"label": "Figure 2.4.3", "cells": []},
        },
        "dimensions": _ids("dimension", taxonomy.get("dimensions", []), "dimension"),
        "oversight_modes": _ids("oversight", oversight.get("modes", []), "mode"),
        "monitoring": {
            "sampling_methodologies": oversight.get("sampling_methodologies", []),
            "sampling_table_label": oversight.get("sampling_table_label"),
            "monitoring_practices": oversight.get("monitoring_practices", []),
            "interruption_controls": oversight.get("interruption_controls", []),
            "selection_guidance": oversight.get("selection_guidance"),
        },
        "metrics": _ids("metric", metrics.get("metrics", []), "name"),
        "guardrails": _ids("guardrail", guardrails.get("guardrails", []), "name"),
        "interpretability_typology": guardrails.get("interpretability_typology", []),
        "considerations": sorted(
            (
                {"item_id": f"consideration:{c.get('number')}", **c}
                for c in considerations.get("considerations", [])
            ),
            key=lambda c: c.get("number") or 0,
        ),
        "agentic": {
            "agentic_risk_factors": agentic.get("agentic_risk_factors", []),
            "accountability_principle": agentic.get("accountability_principle"),
            "accountability_source": agentic.get("accountability_source"),
            "never_delegate_examples": agentic.get("never_delegate_examples", []),
            "interruption_controls": agentic.get("interruption_controls", []),
            "tool_access_risks": agentic.get("tool_access_risks", []),
            "framework_name": agentic.get("framework_name"),
            "risk_sources": agentic.get("risk_sources", []),
            "framework_dimensions": agentic.get("framework_dimensions", []),
            "gen_ai_vs_agentic": agentic.get("gen_ai_vs_agentic", []),
        },
        "illustrations": _ids("illustration", illustrations.get("illustrations", []), "label"),
    }

    # --- provenance -------------------------------------------------------------
    total = Usage()
    extractor_provenance: list[dict[str, Any]] = []
    for name in present:
        payload = payloads[name] or {}
        usage = payload.get("usage", {})
        total.input_tokens += usage.get("input_tokens", 0)
        total.output_tokens += usage.get("output_tokens", 0)
        total.cache_creation_input_tokens += usage.get("cache_creation_input_tokens", 0)
        total.cache_read_input_tokens += usage.get("cache_read_input_tokens", 0)
        total.calls += usage.get("calls", 0)
        total.latency_ms += usage.get("latency_ms", 0)
        extractor_provenance.append(
            {
                "name": name,
                "printed_pages": payload.get("printed_pages"),
                "pdf_pages": payload.get("pdf_pages"),
                "model": payload.get("model"),
                "extracted_at": payload.get("extracted_at"),
                "attempts": payload.get("attempts", 1),
                "requests": payload.get("requests", 1),
                "usage": usage,
            }
        )

    page_map_usage = page_map.raw.get("usage", {})
    for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                "cache_read_input_tokens", "calls", "latency_ms"):
        setattr(total, key, getattr(total, key) + page_map_usage.get(key, 0))

    pdf_name = Path(page_map.raw.get("pdf_path", settings.handbook_pdf.name)).name
    pack["provenance"] = {
        "pdf_sha256": page_map.pdf_sha256,
        "pdf_filename": pdf_name,
        "pdf_physical_pages": page_map.total_pages,
        "document": page_map.raw.get("document", {}),
        "model": settings.ingest_model,
        "extracted_at": max(
            (e["extracted_at"] for e in extractor_provenance if e.get("extracted_at")),
            default=page_map.raw.get("extracted_at"),
        ),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "page_map_version": page_map.raw.get("page_map_version", 1),
        "printed_to_pdf_offset": page_map.offset,
        "extractors": extractor_provenance,
        "verification": verification,
        "ingestion_usage": total.as_dict(settings.ingest_model),
        "completeness": {
            "expected": list(EXPECTED),
            "present": present,
            "missing": missing,
            "partial": bool(missing),
        },
    }
    return pack


def validate(pack: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator(schema).validate(pack)


def counts(pack: dict[str, Any]) -> dict[str, int]:
    return {
        "dimensions": len(pack["dimensions"]),
        "taxonomy_risks": sum(len(d.get("risks", [])) for d in pack["dimensions"]),
        "materiality_factors": len(pack["materiality"]["factors"]),
        "matrix_cells": len(pack["materiality"]["matrix"].get("cells", [])),
        "oversight_modes": len(pack["oversight_modes"]),
        "sampling_methodologies": len(pack["monitoring"]["sampling_methodologies"]),
        "interruption_controls": len(pack["monitoring"]["interruption_controls"]),
        "metrics": len(pack["metrics"]),
        "guardrails": len(pack["guardrails"]),
        "considerations": len(pack["considerations"]),
        "implementation_practices": sum(
            len(c.get("implementation_practices", [])) for c in pack["considerations"]
        ),
        "illustrations": len(pack["illustrations"]),
        "agentic_risk_factors": len(pack["agentic"]["agentic_risk_factors"]),
    }


def load_pack() -> dict[str, Any]:
    if not PACK_PATH.is_file():
        raise PackError(f"{PACK_PATH} not found. Run `make ingest`.")
    return dict(json.loads(PACK_PATH.read_text()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-partial", action="store_true", help="build even if extractors are missing"
    )
    parser.add_argument(
        "--allow-unverified", action="store_true", help="build despite verification failures"
    )
    args = parser.parse_args(argv)

    try:
        pack = build(
            allow_partial=args.allow_partial, allow_unverified=args.allow_unverified
        )
        validate(pack)
    except (PackError, ConfigError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except jsonschema.ValidationError as exc:
        location = "/".join(str(part) for part in exc.absolute_path)
        print(f"error: pack failed schema validation at {location or '<root>'}: {exc.message}",
              file=sys.stderr)
        return 2

    PACK_PATH.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n")
    provenance = pack["provenance"]
    completeness = provenance["completeness"]

    print(f"Wrote {PACK_PATH}")
    print(f"  pdf      {provenance['pdf_filename']}  sha {provenance['pdf_sha256'][:12]}")
    print(f"  model    {provenance['model']}   offset +{provenance['printed_to_pdf_offset']}")
    print(f"  sections {len(completeness['present'])}/{len(completeness['expected'])}"
          + (f"  MISSING: {', '.join(completeness['missing'])}" if completeness["missing"] else ""))
    print("\nContents:")
    for key, value in counts(pack).items():
        print(f"  {key:<26} {value}")
    usage = provenance["ingestion_usage"]
    total_in = (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )
    print(
        f"\nIngestion cost so far: {usage.get('calls', 0)} requests, "
        f"{total_in:,} input tokens, {usage.get('output_tokens', 0):,} output tokens, "
        f"~${usage.get('estimated_cost_usd', 0):.2f}"
    )
    if completeness["partial"]:
        print("\nNOTE: this is a PARTIAL pack. Missing sections are recorded in provenance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
