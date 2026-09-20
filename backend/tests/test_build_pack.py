"""Pack assembly: stable ids, schema conformance, and honest completeness."""

from __future__ import annotations

import json

import jsonschema
import pytest

from mindforge_assess.ingest.build_pack import SCHEMA_PATH, _ids, counts, slug


def test_slug_is_stable_and_url_safe() -> None:
    assert slug("Fairness & Bias") == "fairness-bias"
    assert (
        slug("Hallucination/ Fabrication/ Confabulation")
        == "hallucination-fabrication-confabulation"
    )
    assert slug("  Monetary and financial impact  ") == "monetary-and-financial-impact"
    assert slug("") == "item"


def test_item_ids_are_unique_when_names_collide() -> None:
    items = [{"name": "Data quality"}, {"name": "Data quality"}, {"name": "Other"}]
    result = _ids("metric", items, "name")
    ids = [item["item_id"] for item in result]
    assert ids == ["metric:data-quality", "metric:data-quality-2", "metric:other"]
    assert len(set(ids)) == len(ids)


def test_item_ids_match_the_schema_pattern() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    pattern = schema["$defs"]["item_id"]["pattern"]
    validator = jsonschema.Draft202012Validator({"type": "string", "pattern": pattern})
    for item in _ids("dimension", [{"dimension": "Cyber & Data Security"}], "dimension"):
        validator.validate(item["item_id"])


def test_schema_requires_dual_valued_matrix_cells_to_keep_both_tiers() -> None:
    """residual_tiers must have at least one entry; the label is kept verbatim."""
    schema = json.loads(SCHEMA_PATH.read_text())
    matrix = schema["properties"]["materiality"]["properties"]["matrix"]
    # Carry $defs across so the extracted sub-schema can still resolve its $refs.
    cell_schema = {**matrix["properties"]["cells"]["items"], "$defs": schema["$defs"]}
    validator = jsonschema.Draft202012Validator(cell_schema)
    validator.validate(
        {
            "inherent_tier": "high",
            "evaluation_result": "Best Practice",
            "residual_label": "Medium Risk/High Risk",
            "residual_tiers": ["medium", "high"],
        }
    )
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(
            {
                "inherent_tier": "high",
                "evaluation_result": "Best Practice",
                "residual_label": "Medium Risk/High Risk",
                "residual_tiers": [],
            }
        )


def test_counts_reports_zero_for_absent_sections() -> None:
    empty = {
        "dimensions": [],
        "materiality": {"factors": [], "matrix": {"cells": []}},
        "oversight_modes": [],
        "monitoring": {"sampling_methodologies": [], "interruption_controls": []},
        "metrics": [],
        "guardrails": [],
        "considerations": [],
        "illustrations": [],
        "agentic": {"agentic_risk_factors": []},
    }
    assert counts(empty)["dimensions"] == 0
    assert counts(empty)["implementation_practices"] == 0


def test_the_real_pack_matches_its_schema() -> None:
    """Whatever is on disk must always validate; a partial pack is still a valid pack."""
    from mindforge_assess.ingest.build_pack import PACK_PATH

    if not PACK_PATH.is_file():
        pytest.skip("no pack built yet")
    pack = json.loads(PACK_PATH.read_text())
    jsonschema.Draft202012Validator(json.loads(SCHEMA_PATH.read_text())).validate(pack)
    completeness = pack["provenance"]["completeness"]
    assert set(completeness["present"]) | set(completeness["missing"]) == set(
        completeness["expected"]
    )


# ------------------------------------------------------- ingestion idempotency


def test_ingestion_is_skipped_when_the_pack_matches_the_pdf(tmp_path, monkeypatch) -> None:
    """Re-ingesting the same book costs money and minutes and can only reproduce the
    pack that is already there."""
    import json

    from mindforge_assess.ingest.run import pack_fingerprint, up_to_date

    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-1.7\nnot a real pdf, but it hashes\n")

    from mindforge_assess.config import sha256_file

    pack = tmp_path / "pack.v1.json"
    pack.write_text(json.dumps({"provenance": {"pdf_sha256": sha256_file(pdf)}}))

    assert pack_fingerprint(pack) == sha256_file(pdf)
    assert up_to_date(pdf, pack) is True


def test_a_different_handbook_is_detected_by_its_hash(tmp_path) -> None:
    import json

    from mindforge_assess.ingest.run import up_to_date

    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-1.7\nedition one\n")
    pack = tmp_path / "pack.v1.json"
    pack.write_text(json.dumps({"provenance": {"pdf_sha256": "0" * 64}}))
    assert up_to_date(pdf, pack) is False


def test_a_missing_or_malformed_pack_means_not_up_to_date(tmp_path) -> None:
    from mindforge_assess.ingest.run import pack_fingerprint, up_to_date

    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    assert pack_fingerprint(tmp_path / "absent.json") is None
    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    assert pack_fingerprint(broken) is None
    assert up_to_date(pdf, broken) is False
