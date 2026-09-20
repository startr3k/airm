"""Check that the model cited real handbook names, and correct near-misses.

The prompt lists every guardrail, metric and ABS top-10 risk by name, but the model
still paraphrases or mistypes them ("Hallallucination/ Fabrication/ Confabulation").
A name that does not exist in the pack cannot be traced to a page, which defeats the
point of citing it, so each one is matched back to the library here.

Exact match wins; otherwise a normalised match (case, punctuation and spacing ignored)
corrects an obvious typo. Anything still unmatched is kept -- the model may have a
point -- but reported, so the eval harness can measure citation grounding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import get_close_matches

_NOISE = re.compile(r"[^a-z0-9]+")


def _key(name: str) -> str:
    return _NOISE.sub("", name.casefold())


@dataclass
class GroundingReport:
    corrected: list[tuple[str, str, str]] = field(default_factory=list)
    """(field, what the model said, what it was corrected to)"""

    unmatched: list[tuple[str, str]] = field(default_factory=list)
    """(field, a name that is not in the library at all)"""

    @property
    def clean(self) -> bool:
        return not self.corrected and not self.unmatched

    def notes(self) -> list[str]:
        lines: list[str] = []
        for where, said, became in self.corrected:
            lines.append(f"NOTE: {where} '{said}' matched to '{became}' in the handbook.")
        if self.unmatched:
            grouped: dict[str, list[str]] = {}
            for where, name in self.unmatched:
                grouped.setdefault(where, []).append(name)
            for where, names in grouped.items():
                joined = ", ".join(f"'{n}'" for n in names)
                lines.append(
                    f"NOTE: {where} {joined} do not appear in the handbook's library. "
                    f"Treat them as the assessor's own suggestion, not a citation."
                )
        return lines


class Library:
    """One named collection from the pack, matched leniently."""

    def __init__(self, names: list[str]) -> None:
        self.names = names
        self._by_key = {_key(n): n for n in names}

    def resolve(self, candidate: str) -> tuple[str | None, bool]:
        """Return (canonical name, was_corrected). (None, False) if no match."""
        raw = candidate.strip()
        if raw in self._by_key.values():
            return raw, False
        exact = self._by_key.get(_key(raw))
        if exact is not None:
            return exact, exact != raw
        close = get_close_matches(_key(raw), list(self._by_key), n=1, cutoff=0.82)
        if close:
            return self._by_key[close[0]], True
        return None, False


def ground_names(
    values: list[str], library: Library, where: str, report: GroundingReport
) -> list[str]:
    """Map each cited name onto the library, preserving order and dropping duplicates."""
    out: list[str] = []
    for value in values:
        resolved, corrected = library.resolve(value)
        if resolved is None:
            report.unmatched.append((where, value))
            out.append(value)
            continue
        if corrected:
            report.corrected.append((where, value, resolved))
        out.append(resolved)
    return list(dict.fromkeys(out))
