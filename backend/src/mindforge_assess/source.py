"""Show the reader the page a claim came from.

This is the only place in the project that opens the handbook PDF at request time, and
the only place local PDF tooling is used at all. It renders a page to a PNG **for
display**. It does not read text, extract content or parse structure -- everything the
tool knows about the handbook came from the offline ingestion run and lives in the pack.
Rendering here exists so a reviewer can see the page and check the quote with their own
eyes, which is the point of a citation.

Page numbers crossing this boundary are always the PRINTED page. The pack carries the
calibrated printed-to-PDF offset, and it is applied in exactly one place: `pdf_index()`.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import FRAMEWORK_DIR, Settings, get_settings
from .pack import Pack, load_pack

CACHE_DIR = FRAMEWORK_DIR / "_cache" / "pages"
DEFAULT_SCALE = 2
MAX_SCALE = 4


class SourceUnavailableError(RuntimeError):
    """The handbook PDF is not on disk, so no page image can be rendered.

    The citation itself still resolves: the printed page, section and quote all come
    from the pack. Only the picture is missing.
    """


@dataclass(frozen=True)
class Citation:
    item_id: str
    kind: str
    label: str
    page: int | None
    section: str | None
    quote: str | None

    def as_dict(self, *, pdf_page: int | None, image_url: str | None) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "kind": self.kind,
            "label": self.label,
            # Always the number printed on the page, never the PDF's index.
            "page": self.page,
            "pdf_page": pdf_page,
            "section": self.section,
            "quote": self.quote,
            "image_url": image_url,
        }


def citation(item_id: str, pack: Pack | None = None) -> Citation | None:
    pack = pack or load_pack()
    entry = pack.item(item_id)
    if entry is None:
        return None
    source = entry["item"].get("source") or {}
    page = source.get("page")
    return Citation(
        item_id=item_id,
        kind=str(entry["kind"]),
        label=str(entry["label"]),
        page=int(page) if isinstance(page, int) else None,
        section=source.get("section"),
        quote=source.get("quote"),
    )


def pdf_index(printed_page: int, pack: Pack | None = None) -> int:
    """Printed page -> zero-based index into the PDF."""
    pack = pack or load_pack()
    return pack.printed_to_pdf(printed_page) - 1


def handbook_path(settings: Settings | None = None) -> Path | None:
    settings = settings or get_settings()
    return settings.handbook_pdf if settings.handbook_pdf.is_file() else None


@lru_cache(maxsize=1)
def page_count(path: Path) -> int:
    # pypdfium2 ships no py.typed marker; the untyped boundary is this one call.
    import pypdfium2 as pdfium  # type: ignore[import-untyped]

    document = pdfium.PdfDocument(path)
    try:
        return len(document)
    finally:
        document.close()


def render_page(
    printed_page: int,
    *,
    scale: int = DEFAULT_SCALE,
    settings: Settings | None = None,
    pack: Pack | None = None,
) -> bytes:
    """Render one printed page to PNG bytes, memoised on disk.

    Rendering a page costs tens of milliseconds and the handbook never changes within a
    run, so the result is cached under the PDF's own hash -- a different handbook can
    never be served a previous one's pages.
    """
    settings = settings or get_settings()
    pack = pack or load_pack()
    path = handbook_path(settings)
    if path is None:
        raise SourceUnavailableError(
            f"The handbook PDF is not at {settings.handbook_pdf}. The citation still "
            f"resolves; only the page image is unavailable."
        )

    scale = max(1, min(int(scale), MAX_SCALE))
    index = pdf_index(printed_page, pack)
    total = page_count(path)
    if not 0 <= index < total:
        raise SourceUnavailableError(
            f"Printed page {printed_page} maps to PDF page {index + 1}, "
            f"outside this {total}-page document."
        )

    cached = CACHE_DIR / f"{pack.pdf_sha256[:16]}-p{printed_page}-s{scale}.png"
    if cached.is_file():
        return cached.read_bytes()

    # pypdfium2 ships no py.typed marker; the untyped boundary is this one call.
    import pypdfium2 as pdfium  # type: ignore[import-untyped]

    document = pdfium.PdfDocument(path)
    try:
        image = document[index].render(scale=scale).to_pil()
    finally:
        document.close()

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    data = buffer.getvalue()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(data)
    return data
