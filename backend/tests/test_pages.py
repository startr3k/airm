"""Page arithmetic and page selection.

Citations shown to a user are PRINTED page numbers; extractors address PHYSICAL pages.
Getting the offset backwards would silently cite the wrong page everywhere, so the
conversion is pinned in both directions.
"""

from __future__ import annotations

import pytest
from pypdf import PdfReader, PdfWriter

from mindforge_assess.ingest.engine import _chunk, describe_pages, printed_pages_of
from mindforge_assess.ingest.page_map import PageMapError
from mindforge_assess.ingest.pdf_slice import PageRange, page_count, slice_pdf


def test_offset_converts_both_ways(page_map) -> None:
    # The handbook's real anchors: Illustration 2.3.1 and Appendix B.
    assert page_map.printed_to_pdf(44) == 51
    assert page_map.printed_to_pdf(131) == 138
    assert page_map.pdf_to_printed(51) == 44
    assert page_map.pdf_to_printed(138) == 131


def test_section_lookup_and_range(page_map) -> None:
    assert page_map.range_for("B") == PageRange(138, 145)
    assert page_map.section("b")["title"] == "MindForge AI Risk Taxonomy"
    with pytest.raises(PageMapError):
        page_map.section("ZZ")


def test_printed_pages_of(page_map) -> None:
    assert printed_pages_of(page_map, [138, 139, 145]) == [131, 132, 138]


@pytest.mark.parametrize(
    ("pages", "expected"),
    [
        ([], "-"),
        ([5], "5"),
        ([1, 2, 3], "1-3"),
        ([52, 53, 54, 58], "52-54, 58"),
        ([25, 26, 44, 45, 57, 58, 59], "25-26, 44-45, 57-59"),
    ],
)
def test_describe_pages(pages: list[int], expected: str) -> None:
    assert describe_pages(pages) == expected


def test_chunking_preserves_order_and_size() -> None:
    pages = list(range(1, 8))
    assert _chunk(pages, 3) == [[1, 2, 3], [4, 5, 6], [7]]
    assert _chunk(pages, 20) == [pages]
    # Disjoint page sets chunk just as well as contiguous ones.
    assert _chunk([25, 26, 44, 45], 2) == [[25, 26], [44, 45]]


def test_page_range_rejects_nonsense() -> None:
    with pytest.raises(ValueError):
        PageRange(5, 4)
    with pytest.raises(ValueError):
        PageRange(0, 3)


def _build_pdf(path, pages: int):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def test_slice_selects_exactly_the_requested_pages(tmp_path) -> None:
    source = _build_pdf(tmp_path / "source.pdf", 10)
    out = slice_pdf(source, [3, 4, 9], tmp_path / "out.pdf")
    assert page_count(out) == 3
    assert len(PdfReader(str(out)).pages) == 3


def test_slice_rejects_out_of_range_pages(tmp_path) -> None:
    source = _build_pdf(tmp_path / "source.pdf", 5)
    with pytest.raises(ValueError, match="out of range"):
        slice_pdf(source, [6], tmp_path / "out.pdf")


def test_page_range_pages_are_inclusive() -> None:
    assert PageRange(138, 140).pages == [138, 139, 140]
    assert len(PageRange(138, 145)) == 8
