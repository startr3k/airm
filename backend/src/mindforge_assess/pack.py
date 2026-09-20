"""Read-only access to the framework pack.

The pack is loaded once at import and treated as immutable. Nothing here touches the
handbook PDF or the Anthropic API -- ingestion is an offline step, and a request only
ever reads this file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .config import FRAMEWORK_DIR

PACK_PATH = FRAMEWORK_DIR / "pack.v1.json"

DIMENSIONS: tuple[str, ...] = (
    "Fairness & Bias",
    "Ethics",
    "Accountability & Governance",
    "Transparency",
    "Legal & Regulatory",
    "Robustness & Stability",
    "Cyber & Data Security",
)

OVERSIGHT_MODES: tuple[str, ...] = (
    "human_in_the_loop",
    "human_over_the_loop",
    "human_out_of_the_loop",
)

AI_TYPES: tuple[str, ...] = ("traditional", "gen_ai", "agentic")
RATINGS: tuple[str, ...] = ("low", "medium", "high")


class PackNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True, eq=False)
class Pack:
    """`eq=False` keeps identity hashing, so the cached index below works despite the
    dict field (a generated __eq__ would make the instance unhashable)."""

    raw: dict[str, Any]

    # --- provenance ---------------------------------------------------------
    @property
    def provenance(self) -> dict[str, Any]:
        return dict(self.raw["provenance"])

    @property
    def version(self) -> int:
        return int(self.raw["pack_version"])

    @property
    def pdf_sha256(self) -> str:
        return str(self.raw["provenance"]["pdf_sha256"])

    @property
    def offset(self) -> int:
        return int(self.raw["provenance"]["printed_to_pdf_offset"])

    def printed_to_pdf(self, printed: int) -> int:
        return printed + self.offset

    # --- content ------------------------------------------------------------
    @property
    def definitions(self) -> dict[str, Any]:
        return dict(self.raw["definitions"])

    @property
    def materiality(self) -> dict[str, Any]:
        return dict(self.raw["materiality"])

    @property
    def matrix(self) -> dict[str, Any]:
        return dict(self.raw["materiality"]["matrix"])

    @property
    def dimensions(self) -> list[dict[str, Any]]:
        return list(self.raw["dimensions"])

    @property
    def oversight_modes(self) -> list[dict[str, Any]]:
        return list(self.raw["oversight_modes"])

    @property
    def monitoring(self) -> dict[str, Any]:
        return dict(self.raw["monitoring"])

    @property
    def metrics(self) -> list[dict[str, Any]]:
        return list(self.raw["metrics"])

    @property
    def guardrails(self) -> list[dict[str, Any]]:
        return list(self.raw["guardrails"])

    @property
    def considerations(self) -> list[dict[str, Any]]:
        return list(self.raw["considerations"])

    @property
    def agentic(self) -> dict[str, Any]:
        return dict(self.raw["agentic"])

    @property
    def illustrations(self) -> list[dict[str, Any]]:
        return list(self.raw["illustrations"])

    # --- lookups ------------------------------------------------------------
    @lru_cache(maxsize=1)  # noqa: B019 - Pack is frozen and process-lived
    def _index(self) -> dict[str, dict[str, Any]]:
        """Every citable item by `item_id`, for /api/framework/source/{item_id}."""
        index: dict[str, dict[str, Any]] = {}

        def add(item: dict[str, Any], kind: str, label: str) -> None:
            item_id = item.get("item_id")
            if item_id:
                index[str(item_id)] = {"kind": kind, "label": label, "item": item}

        for item in self.dimensions:
            add(item, "dimension", str(item["dimension"]))
        for item in self.materiality["factors"]:
            add(item, "factor", str(item["factor"]))
        for item in self.oversight_modes:
            add(item, "oversight_mode", str(item.get("printed_name") or item["mode"]))
        for item in self.metrics:
            add(item, "metric", str(item["name"]))
        for item in self.guardrails:
            add(item, "guardrail", str(item["name"]))
        for item in self.considerations:
            add(item, "consideration", f"Consideration {item['number']}: {item['title']}")
        for item in self.illustrations:
            add(item, "illustration", f"{item['label']}: {item['institution']}")
        return index

    def item(self, item_id: str) -> dict[str, Any] | None:
        return self._index().get(item_id)

    def item_ids(self) -> list[str]:
        return sorted(self._index())

    def guardrail_names(self) -> list[str]:
        return [str(g["name"]) for g in self.guardrails]

    def metric_names(self) -> list[str]:
        return [str(m["name"]) for m in self.metrics]

    def abs_top_10(self) -> list[str]:
        """Risks the taxonomy marks as ABS 'top 10'."""
        named = [
            str(risk["name"])
            for dimension in self.dimensions
            for risk in dimension.get("risks", [])
            if risk.get("is_abs_top_10")
        ]
        if named:
            return named
        return [str(r["risk"]) for r in self.definitions.get("abs_top_risks", [])]

    def residual_tier(self, inherent: str, evaluation: str) -> list[str] | None:
        """Look up Figure 2.4.3. Returns every tier the printed cell names."""
        for cell in self.matrix.get("cells", []):
            if (
                str(cell["inherent_tier"]) == inherent
                and str(cell["evaluation_result"]) == evaluation
            ):
                return [str(t) for t in cell.get("residual_tiers", [])]
        return None


@lru_cache(maxsize=1)
def load_pack() -> Pack:
    if not PACK_PATH.is_file():
        raise PackNotFoundError(
            f"{PACK_PATH} not found. Run `make ingest` to build it from the handbook."
        )
    return Pack(json.loads(PACK_PATH.read_text()))
