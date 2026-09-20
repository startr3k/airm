"""The extraction validators are the defence against a lazy or truncated response.

These models reject `temperature`, so an extraction cannot be pinned by sampling: an
identically-configured run really can return a stub one time and the full table the next.
Each validator therefore encodes an invariant that a stub violates.
"""

from __future__ import annotations

from typing import Any

import pytest

from mindforge_assess.ingest.engine import DIMENSIONS
from mindforge_assess.ingest.extractors import validate_dimensions, validate_materiality


def _source(page: int = 133) -> dict[str, Any]:
    return {"page": page, "section": "Appendix B", "quote": "a sufficiently long quote here"}


def _risk(name: str = "Some risk") -> dict[str, Any]:
    return {
        "name": name,
        "description": "d",
        "ai_specific_elements": None,
        "secondary_dimensions": [],
        "lifecycle_stages": [],
        "is_abs_top_10": False,
        "source": _source(),
    }


def _full_taxonomy(risks_per_dimension: int = 2) -> dict[str, Any]:
    dimensions = [
        {
            "dimension": name,
            "printed_name": name,
            "definition": None,
            "risks": [_risk(f"{name} risk {i}") for i in range(risks_per_dimension)],
            "source": _source(),
        }
        for name in DIMENSIONS
    ]
    return {
        "dimensions": dimensions,
        "table_columns": [],
        "abs_top_10_risks": [],
        "dimension_renaming": [],
        "risk_changes": [],
        "lifecycle_stage_legend": [],
        "total_risk_rows_counted": len(DIMENSIONS) * risks_per_dimension,
        "unreadable_items": [],
    }


def test_full_taxonomy_passes(page_map, appendix_b_pages) -> None:
    assert validate_dimensions(_full_taxonomy(), page_map, appendix_b_pages) == []


def test_stub_response_is_rejected(page_map, appendix_b_pages) -> None:
    """The exact shape a lazy run returned in practice: one dimension, no risks."""
    stub = {
        "dimensions": [
            {
                "dimension": "Fairness & Bias",
                "printed_name": "Fairness & Bias",
                "definition": None,
                "risks": [],
                "source": _source(),
            }
        ],
        "table_columns": [],
        "abs_top_10_risks": [],
        "total_risk_rows_counted": 0,
        "unreadable_items": [],
    }
    problems = validate_dimensions(stub, page_map, appendix_b_pages)
    assert any("expected 7 dimensions, got 1" in p for p in problems)
    assert any("has no risks" in p for p in problems)
    assert any("total_risk_rows_counted is 0" in p for p in problems)


def test_dropped_row_is_caught(page_map, appendix_b_pages) -> None:
    """The model counts rows separately from transcribing them, so a drop shows up."""
    data = _full_taxonomy()
    data["dimensions"][0]["risks"].pop()
    problems = validate_dimensions(data, page_map, appendix_b_pages)
    assert any("counted 14 risk rows but returned only 13" in p for p in problems)


def test_surplus_rows_do_not_trigger_a_retry(page_map, appendix_b_pages) -> None:
    """Transcribing more rows than you counted means you miscounted, not that rows are
    missing. `metrics` did exactly this (53 returned, 52 counted) and burned three
    retries on an extraction that was already complete."""
    data = _full_taxonomy()
    data["total_risk_rows_counted"] = 13
    assert validate_dimensions(data, page_map, appendix_b_pages) == []


def test_citation_outside_the_supplied_pages_is_caught(page_map, appendix_b_pages) -> None:
    data = _full_taxonomy()
    data["dimensions"][0]["risks"][0]["source"] = _source(page=12)
    problems = validate_dimensions(data, page_map, appendix_b_pages)
    assert any("cited page 12 not among printed 131-138" in p for p in problems)


def test_unverifiably_short_quote_is_caught(page_map, appendix_b_pages) -> None:
    data = _full_taxonomy()
    data["dimensions"][0]["risks"][0]["source"] = {
        "page": 133,
        "section": "Appendix B",
        "quote": "bias",
    }
    problems = validate_dimensions(data, page_map, appendix_b_pages)
    assert any("quote too short to verify" in p for p in problems)


def test_missing_lifecycle_legend_is_caught(page_map, appendix_b_pages) -> None:
    """Numeric lifecycle cells are meaningless without the legend that decodes them."""
    data = _full_taxonomy()
    data["dimensions"][0]["risks"][0]["lifecycle_stages"] = ["2", "3"]
    problems = validate_dimensions(data, page_map, appendix_b_pages)
    assert any("numeric lifecycle stages but no legend" in p for p in problems)


# --------------------------------------------------------------------- materiality


def _matrix(cells: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    default = [
        {
            "inherent_tier": tier,
            "evaluation_result": result,
            "residual_label": label,
            "residual_tiers": tiers,
            "note": None,
        }
        for tier, result, label, tiers in [
            ("low", "Min.", "Low Risk", ["low"]),
            ("medium", "Min.", "Medium Risk", ["medium"]),
            ("high", "Min.", "High Risk", ["high"]),
            ("low", "Exceeds Min.", "Low Risk", ["low"]),
            ("medium", "Exceeds Min.", "Medium Risk", ["medium"]),
            ("high", "Exceeds Min.", "High Risk", ["high"]),
            ("low", "Best Practice", "Low Risk", ["low"]),
            ("medium", "Best Practice", "Low Risk", ["low"]),
            ("high", "Best Practice", "Medium Risk/High Risk", ["medium", "high"]),
        ]
    ]
    return {
        "label": "Figure 2.4.3",
        "caption": "c",
        "read_successfully": True,
        "axis_inherent_values": ["Low Risk", "Medium Risk", "High Risk"],
        "axis_evaluation_values": ["Min.", "Exceeds Min.", "Best Practice"],
        "cells": default if cells is None else cells,
        "always_high_note": "some use cases may always have a high residual risk",
        "always_high_note_applies_to": "high inherent / best practice",
        "failure_to_meet_minimum_note": "Use cases that fail to meet minimums do not proceed.",
        "source": _source(page=51),
    }


def _materiality(**overrides: Any) -> dict[str, Any]:
    data = {
        "inherent_risk_factors": [
            {
                "factor": "Reputational risk",
                "description": "d",
                "sub_criteria": [],
                "low_guidance": None,
                "medium_guidance": None,
                "high_guidance": None,
                "source": _source(page=47),
            }
        ],
        "tiers": [
            {
                "tier": tier,
                "printed_name": tier.title(),
                "definition": "d",
                "governance_implications": None,
                "source": _source(page=46),
            }
            for tier in ("low", "medium", "high")
        ],
        "tiering_method": None,
        "residual_risk_logic": None,
        "agentic_or_genai_factors": [],
        "total_factors_counted": 1,
        "figure_2_4_3": _matrix(),
        "unreadable_items": [],
    }
    data.update(overrides)
    return data


@pytest.fixture
def section_24_pages() -> list[int]:
    return list(range(52, 67))


def test_materiality_passes(page_map, section_24_pages) -> None:
    assert validate_materiality(_materiality(), page_map, section_24_pages) == []


def test_dual_valued_cell_collapsed_to_one_tier_is_caught(page_map, section_24_pages) -> None:
    """The real bug: 'Medium Risk/High Risk' recorded as a single tier.

    Two identically-configured runs disagreed on this cell -- one said high, one said
    medium -- because the schema only allowed one. The label and the tiers it names are
    now stored separately, and a '/' in the label must yield at least two tiers.
    """
    cells = _matrix()["cells"]
    cells[-1]["residual_tiers"] = ["medium"]
    problems = validate_materiality(
        _materiality(figure_2_4_3=_matrix(cells)), page_map, section_24_pages
    )
    assert any("collapsed to ['medium']" in p for p in problems), problems


def test_incomplete_matrix_is_caught(page_map, section_24_pages) -> None:
    cells = _matrix()["cells"][:6]
    problems = validate_materiality(
        _materiality(figure_2_4_3=_matrix(cells)), page_map, section_24_pages
    )
    assert any("3x3 axes but 6 cells" in p for p in problems), problems


def test_unread_figure_is_caught(page_map, section_24_pages) -> None:
    matrix = _matrix()
    matrix["read_successfully"] = False
    problems = validate_materiality(
        _materiality(figure_2_4_3=matrix), page_map, section_24_pages
    )
    assert any("not read successfully" in p for p in problems)


def test_missing_tier_is_caught(page_map, section_24_pages) -> None:
    data = _materiality()
    data["tiers"] = data["tiers"][:2]
    problems = validate_materiality(data, page_map, section_24_pages)
    assert any("expected tiers" in p for p in problems)


# ------------------------------------------------- chunk boundaries (considerations)


def _consideration(number: int, practices: int, page: int = 159) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"Consideration {number}",
        "handbook_section": None,
        "implementation_practices": [
            {"reference": str(i + 1), "text": "do the thing properly", "source": _source(page)}
            for i in range(practices)
        ],
        "source": _source(page),
    }


def _considerations(practices_each: int = 3, **overrides: Any) -> dict[str, Any]:
    items = [_consideration(n, practices_each) for n in range(1, 18)]
    data = {
        "considerations": items,
        "total_considerations_counted": 17,
        "total_practices_counted": 17 * practices_each,
        "unreadable_items": [],
    }
    data.update(overrides)
    return data


@pytest.fixture
def appendix_h_pages() -> list[int]:
    return list(range(166, 172))


def test_complete_considerations_pass(page_map, appendix_h_pages) -> None:
    from mindforge_assess.ingest.extractors import validate_considerations

    assert validate_considerations(_considerations(), page_map, appendix_h_pages) == []


def test_practices_lost_at_a_chunk_boundary_are_caught(page_map, appendix_h_pages) -> None:
    """The real defect: splitting Appendix H across requests stranded Consideration 5's
    practices 4-6, leaving 57 returned against a counted 59."""
    from mindforge_assess.ingest.extractors import validate_considerations

    data = _considerations()
    data["considerations"][4]["implementation_practices"] = data["considerations"][4][
        "implementation_practices"
    ][:1]
    problems = validate_considerations(data, page_map, appendix_h_pages)
    assert any("returned only 49" in p for p in problems), problems


def test_practices_described_instead_of_extracted_are_caught(
    page_map, appendix_h_pages
) -> None:
    """The model told us it had seen practices it did not return. That is a failure,
    not a note."""
    from mindforge_assess.ingest.extractors import validate_considerations

    data = _considerations(
        unreadable_items=[
            "Page 161 begins mid-Consideration with Implementation Practices 4, 5 and 6"
        ]
    )
    problems = validate_considerations(data, page_map, appendix_h_pages)
    assert any("reported as unread rather than extracted" in p for p in problems), problems


def test_missing_consideration_number_is_caught(page_map, appendix_h_pages) -> None:
    from mindforge_assess.ingest.extractors import validate_considerations

    data = _considerations()
    data["considerations"].pop()
    problems = validate_considerations(data, page_map, appendix_h_pages)
    assert any("expected Considerations 1-17" in p for p in problems)
