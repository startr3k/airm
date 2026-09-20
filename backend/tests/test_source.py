"""Citations, and the one place the PDF is opened at request time.

No test here touches the real handbook: rendering is exercised against a blank PDF
built in a temp directory, so the suite still runs without the book present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mindforge_assess.config import Settings
from mindforge_assess.pack import Pack, load_pack
from mindforge_assess.source import (
    SourceUnavailableError,
    citation,
    handbook_path,
    pdf_index,
    render_page,
)


def settings_for(pdf: Path) -> Settings:
    return Settings(
        api_key="test",
        assess_model="claude-sonnet-5",
        ingest_model="claude-opus-5",
        assess_effort="medium",
        ingest_effort="high",
        handbook_pdf=pdf,
    )


def blank_pdf(path: Path, pages: int = 3) -> Path:
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=300)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def stub_pack(offset: int = 0) -> Pack:
    return Pack(
        {
            "pack_version": 1,
            "provenance": {"pdf_sha256": "a" * 64, "printed_to_pdf_offset": offset},
        }
    )


# ------------------------------------------------------------------ citations


def test_every_citable_item_resolves() -> None:
    pack = load_pack()
    for item_id in pack.item_ids():
        found = citation(item_id, pack)
        assert found is not None
        assert found.label
        assert found.kind


def test_a_citation_carries_the_printed_page_not_the_pdf_index() -> None:
    pack = load_pack()
    found = citation("consideration:1", pack)
    assert found is not None and found.page is not None
    # The offset is applied in exactly one place, and it is not the citation.
    assert pdf_index(found.page, pack) == found.page + pack.offset - 1


def test_an_unknown_item_is_none_rather_than_an_exception() -> None:
    assert citation("nope:nope") is None


def test_the_pack_has_a_page_for_almost_everything() -> None:
    pack = load_pack()
    found = [citation(item_id, pack) for item_id in pack.item_ids()]
    assert all(c is not None for c in found)
    assert [c.item_id for c in found if c is not None and c.page is None] == []


# -------------------------------------------------------------------- rendering


def test_a_page_renders_to_a_png(tmp_path: Path) -> None:
    pdf = blank_pdf(tmp_path / "book.pdf")
    png = render_page(1, settings=settings_for(pdf), pack=stub_pack())
    assert png[:4] == b"\x89PNG"


def test_the_rendered_page_is_cached_on_disk(tmp_path: Path, monkeypatch) -> None:
    import mindforge_assess.source as source

    cache = tmp_path / "pages"
    monkeypatch.setattr(source, "CACHE_DIR", cache)
    pdf = blank_pdf(tmp_path / "book.pdf")
    first = render_page(2, settings=settings_for(pdf), pack=stub_pack())
    files = list(cache.glob("*.png"))
    assert len(files) == 1
    # The cache key carries the PDF's hash, so another handbook cannot be served this one.
    assert files[0].name.startswith("a" * 16)
    assert render_page(2, settings=settings_for(pdf), pack=stub_pack()) == first


def test_a_page_outside_the_document_is_refused(tmp_path: Path) -> None:
    pdf = blank_pdf(tmp_path / "book.pdf", pages=2)
    with pytest.raises(SourceUnavailableError, match="outside this 2-page document"):
        render_page(99, settings=settings_for(pdf), pack=stub_pack())


def test_a_missing_handbook_is_reported_not_crashed(tmp_path: Path) -> None:
    absent = settings_for(tmp_path / "not-here.pdf")
    assert handbook_path(absent) is None
    with pytest.raises(SourceUnavailableError, match="citation still resolves"):
        render_page(1, settings=absent, pack=stub_pack())


def test_the_scale_is_clamped_rather_than_trusted(tmp_path: Path, monkeypatch) -> None:
    """`scale` arrives from a query string; a large one would render a huge bitmap."""
    import mindforge_assess.source as source

    monkeypatch.setattr(source, "CACHE_DIR", tmp_path / "pages")
    pdf = blank_pdf(tmp_path / "book.pdf")
    render_page(1, scale=999, settings=settings_for(pdf), pack=stub_pack())
    rendered = list((tmp_path / "pages").glob("*.png"))
    assert rendered[0].name.endswith(f"-s{source.MAX_SCALE}.png")
