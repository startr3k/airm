"""Configuration, loaded from backend/.env (never from committed files)."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# backend/src/mindforge_assess/config.py -> repo root is four parents up. That holds
# for an editable install, where the package still sits inside the checkout. It does
# NOT hold for a real install: in the container the package lives in site-packages and
# this would resolve to /usr/local/lib/backend. MINDFORGE_ROOT is how the image says
# where the data actually lives, and the derivation stays the default for development.
REPO_ROOT = Path(os.environ.get("MINDFORGE_ROOT") or Path(__file__).resolve().parents[3])
BACKEND_ROOT = REPO_ROOT / "backend"
FRAMEWORK_DIR = BACKEND_ROOT / "framework"
EVALS_DIR = BACKEND_ROOT / "evals"
DOCS_DIR = REPO_ROOT / "docs"

load_dotenv(BACKEND_ROOT / ".env")

DEFAULT_HANDBOOK = "docs/MindForge AI Risk Management Operationalisation Handbook.pdf"

# Effort levels accepted by claude-sonnet-5 / claude-opus-5 (output_config.effort).
VALID_EFFORTS = ("low", "medium", "high", "xhigh", "max")


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    assess_model: str
    ingest_model: str
    assess_effort: str
    ingest_effort: str
    handbook_pdf: Path

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def require_api_key(self) -> str:
        if not self.api_key:
            raise ConfigError(
                "ANTHROPIC_API_KEY is not set. Copy backend/.env.example to backend/.env "
                "and add your key."
            )
        return self.api_key

    def require_handbook(self) -> Path:
        if not self.handbook_pdf.is_file():
            raise ConfigError(
                f"Handbook PDF not found at {self.handbook_pdf}. "
                "Set HANDBOOK_PDF in backend/.env to its path relative to the repo root."
            )
        return self.handbook_pdf


def _effort(name: str, default: str) -> str:
    value = os.getenv(name, default).strip().lower()
    if value not in VALID_EFFORTS:
        raise ConfigError(f"{name}={value!r} is not one of {VALID_EFFORTS}")
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    raw_pdf = os.getenv("HANDBOOK_PDF", DEFAULT_HANDBOOK).strip()
    pdf_path = Path(raw_pdf)
    if not pdf_path.is_absolute():
        pdf_path = REPO_ROOT / pdf_path
    return Settings(
        api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        assess_model=os.getenv("ASSESS_MODEL", "claude-sonnet-5").strip(),
        ingest_model=os.getenv("INGEST_MODEL", "claude-opus-5").strip(),
        assess_effort=_effort("ASSESS_EFFORT", "medium"),
        ingest_effort=_effort("INGEST_EFFORT", "high"),
        handbook_pdf=pdf_path,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
