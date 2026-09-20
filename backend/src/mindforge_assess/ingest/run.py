"""The whole offline ingestion pipeline, with one guard in front of it.

`make ingest` is idempotent: if a pack already exists and was built from the same PDF,
the run is skipped. Re-ingesting the same book costs real money and tens of minutes and
can only produce the pack that is already there, so the default is to do nothing and
say so. `--force` overrides it, and a different handbook is detected by its hash rather
than by anyone remembering to pass a flag.

Run:  python -m mindforge_assess.ingest.run [--force] [--allow-unverified]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..config import ConfigError, get_settings, sha256_file
from ..llm import ApiUnavailableError
from ..pack import PACK_PATH
from . import build_pack, extract, notes, pdf_index, verify

STEPS = ("page map", "extract", "verify", "pack", "notes")


def pack_fingerprint(path: Path = PACK_PATH) -> str | None:
    """The PDF hash the existing pack was built from, if there is one."""
    if not path.is_file():
        return None
    import json

    try:
        return str(json.loads(path.read_text())["provenance"]["pdf_sha256"])
    except (ValueError, KeyError):
        return None


def up_to_date(pdf: Path, path: Path = PACK_PATH) -> bool:
    built_from = pack_fingerprint(path)
    return built_from is not None and built_from == sha256_file(pdf)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the framework pack from the handbook.")
    parser.add_argument("--force", action="store_true", help="re-ingest even if up to date")
    parser.add_argument(
        "--allow-unverified", action="store_true", help="build the pack despite verifier failures"
    )
    args = parser.parse_args(argv)

    try:
        settings = get_settings()
        pdf = settings.require_handbook()
        settings.require_api_key()
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if up_to_date(pdf) and not args.force:
        print(f"{PACK_PATH.name} was built from this exact PDF ({sha256_file(pdf)[:12]}).")
        print("Nothing to do. Re-run with --force to ingest it again.")
        return 0

    if pack_fingerprint() is not None and not args.force:
        print("The handbook has changed since the pack was built. Re-ingesting.")

    stages: list[tuple[str, list[str]]] = [
        ("page map", []),
        ("extract", []),
        ("verify", []),
        ("pack", ["--allow-unverified"] if args.allow_unverified else []),
        ("notes", []),
    ]
    mains = {
        "page map": pdf_index.main,
        "extract": extract.main,
        "verify": verify.main,
        "pack": build_pack.main,
        "notes": notes.main,
    }

    for name, stage_args in stages:
        print(f"\n=== {name} " + "=" * (60 - len(name)))
        try:
            code = mains[name](stage_args)
        except ApiUnavailableError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 3
        if code != 0:
            print(f"\ningestion stopped at '{name}' (exit {code}).", file=sys.stderr)
            return code

    print("\nIngestion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
