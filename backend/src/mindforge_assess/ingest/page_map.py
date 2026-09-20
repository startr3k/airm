"""Read framework/page_map.json and resolve sections to physical page ranges."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .pdf_index import PAGE_MAP_PATH
from .pdf_slice import PageRange


class PageMapError(RuntimeError):
    pass


@dataclass(frozen=True)
class PageMap:
    raw: dict[str, Any]

    @property
    def offset(self) -> int:
        value = self.raw["calibration"]["printed_to_pdf_offset"]
        if not isinstance(value, int):
            raise PageMapError("page_map.json has no constant printed->pdf offset")
        return value

    @property
    def pdf_sha256(self) -> str:
        return str(self.raw["pdf_sha256"])

    @property
    def total_pages(self) -> int:
        return int(self.raw["pdf_physical_pages"])

    def printed_to_pdf(self, printed: int) -> int:
        return printed + self.offset

    def pdf_to_printed(self, pdf_page: int) -> int:
        return pdf_page - self.offset

    def section(self, section_id: str) -> dict[str, Any]:
        wanted = section_id.strip().casefold()
        for entry in self.raw["sections"]:
            if str(entry.get("section_id") or "").strip().casefold() == wanted:
                return dict(entry)
        raise PageMapError(f"no section {section_id!r} in page_map.json")

    def section_by_title(self, fragment: str) -> dict[str, Any]:
        needle = fragment.strip().casefold()
        for entry in self.raw["sections"]:
            if needle in str(entry.get("title", "")).casefold():
                return dict(entry)
        raise PageMapError(f"no section whose title contains {fragment!r}")

    def range_for(self, section_id: str) -> PageRange:
        entry = self.section(section_id)
        return PageRange(int(entry["pdf_start"]), int(entry["pdf_end"]))

    def range_for_title(self, fragment: str) -> PageRange:
        entry = self.section_by_title(fragment)
        return PageRange(int(entry["pdf_start"]), int(entry["pdf_end"]))

    def figure(self, label_fragment: str) -> dict[str, Any] | None:
        needle = label_fragment.strip().casefold()
        for key in ("figures", "tables", "illustrations"):
            for item in self.raw.get(key, []):
                if needle in str(item.get("label", "")).casefold():
                    return dict(item)
        return None


@lru_cache(maxsize=1)
def load_page_map() -> PageMap:
    if not PAGE_MAP_PATH.is_file():
        raise PageMapError(
            f"{PAGE_MAP_PATH} not found. Run: python -m mindforge_assess.ingest.pdf_index"
        )
    return PageMap(json.loads(PAGE_MAP_PATH.read_text()))
