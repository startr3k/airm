"""Page *selection* for the handbook PDF, plus a Files API upload cache.

The Messages API has no page-range parameter on a `document` block, and the docs'
own advice for large PDFs is to "split large PDFs into chunks when needed". pypdf is
used here strictly to copy whole page objects into a smaller PDF: no text is read out
of the file, no OCR is performed, and every page still reaches Claude as an image plus
its embedded text layer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import anthropic
from pypdf import PdfReader, PdfWriter

from ..config import FRAMEWORK_DIR, sha256_file
from ..llm import upload_pdf

CACHE_DIR = FRAMEWORK_DIR / "_cache"
SLICE_DIR = CACHE_DIR / "slices"
UPLOAD_INDEX = CACHE_DIR / "uploads.json"


def page_count(pdf: Path) -> int:
    """Number of physical pages in the PDF (structure only, no content read)."""
    return len(PdfReader(str(pdf)).pages)


@dataclass(frozen=True)
class PageRange:
    """An inclusive, 1-based range of *physical* PDF pages."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 1 or self.end < self.start:
            raise ValueError(f"invalid page range {self.start}-{self.end}")

    @property
    def pages(self) -> list[int]:
        return list(range(self.start, self.end + 1))

    def __len__(self) -> int:
        return self.end - self.start + 1

    def __str__(self) -> str:
        return f"{self.start}-{self.end}"


def slice_pdf(pdf: Path, pages: list[int], out_path: Path) -> Path:
    """Write a new PDF containing exactly `pages` (1-based physical indices), in order."""
    reader = PdfReader(str(pdf))
    total = len(reader.pages)
    writer = PdfWriter()
    for page_no in pages:
        if not 1 <= page_no <= total:
            raise ValueError(f"page {page_no} out of range (PDF has {total} pages)")
        writer.add_page(reader.pages[page_no - 1])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as handle:
        writer.write(handle)
    return out_path


def _load_index() -> dict[str, str]:
    if UPLOAD_INDEX.is_file():
        return dict(json.loads(UPLOAD_INDEX.read_text()))
    return {}


def _save_index(index: dict[str, str]) -> None:
    UPLOAD_INDEX.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_INDEX.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")


def upload_pages(
    client: anthropic.Anthropic,
    pdf: Path,
    pages: list[int],
    *,
    label: str,
    pdf_sha: str | None = None,
) -> tuple[str, Path]:
    """Slice `pages` out of `pdf`, upload once, and return (file_id, slice_path).

    Uploads are memoised on disk by (source sha256, page list) so that re-running an
    extractor reuses the same file_id -- which also keeps the prompt-cache prefix stable.
    """
    pdf_sha = pdf_sha or sha256_file(pdf)
    key = f"{pdf_sha}:{','.join(str(p) for p in pages)}"
    slice_path = SLICE_DIR / f"{label}_{pages[0]}-{pages[-1]}.pdf"

    index = _load_index()
    cached = index.get(key)
    if cached:
        if not slice_path.is_file():
            slice_pdf(pdf, pages, slice_path)
        return cached, slice_path

    slice_pdf(pdf, pages, slice_path)
    file_id = upload_pdf(client, slice_path)
    index[key] = file_id
    _save_index(index)
    return file_id, slice_path


def upload_range(
    client: anthropic.Anthropic,
    pdf: Path,
    page_range: PageRange,
    *,
    label: str,
    pdf_sha: str | None = None,
) -> tuple[str, Path]:
    return upload_pages(client, pdf, page_range.pages, label=label, pdf_sha=pdf_sha)
