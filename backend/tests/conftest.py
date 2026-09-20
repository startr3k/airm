"""Shared fixtures. No test in this suite makes a network call."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    return dict(json.loads((FIXTURES / f"{name}.json").read_text()))


@pytest.fixture
def page_map() -> Any:
    """A page map with the handbook's real +7 offset, built without touching disk."""
    from mindforge_assess.ingest.page_map import PageMap

    return PageMap(
        {
            "page_map_version": 1,
            "pdf_sha256": "0" * 64,
            "pdf_physical_pages": 173,
            "calibration": {"printed_to_pdf_offset": 7, "constant": True},
            "sections": [
                {
                    "section_id": "B",
                    "title": "MindForge AI Risk Taxonomy",
                    "kind": "appendix",
                    "level": 2,
                    "printed_start": 131,
                    "printed_end": 138,
                    "pdf_start": 138,
                    "pdf_end": 145,
                }
            ],
            "figures": [],
            "tables": [],
            "illustrations": [{"label": "Illustration 2.3.1", "printed_page": 44}],
        }
    )


@pytest.fixture
def appendix_b_pages() -> list[int]:
    """Physical pages for Appendix B: printed 131-138 at offset +7."""
    return list(range(138, 146))
