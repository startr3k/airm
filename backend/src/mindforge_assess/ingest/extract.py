"""CLI for running the handbook extractors.

    python -m mindforge_assess.ingest.extract [names...]
"""

from __future__ import annotations

from .engine import (
    EXTRACT_DIR,
    ExtractionResult,
    Pass,
    describe_pages,
    load_extraction,
    printed_pages_of,
    run_extractor,
    write_extraction,
)
from .extractors import EXTRACTORS

__all__ = [
    "EXTRACTORS",
    "EXTRACT_DIR",
    "ExtractionResult",
    "Pass",
    "describe_pages",
    "load_extraction",
    "printed_pages_of",
    "run_extractor",
    "write_extraction",
]

# ------------------------------------------------------------------------------ cli


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from ..config import ConfigError, get_settings
    from ..llm import ApiUnavailableError, Usage, get_client
    from .page_map import load_page_map

    parser = argparse.ArgumentParser(description="Run one or more handbook extractors.")
    parser.add_argument(
        "names",
        nargs="*",
        default=[],
        help=f"extractors to run (default: all). Available: {', '.join(EXTRACTORS)}",
    )
    args = parser.parse_args(argv)
    names = args.names or list(EXTRACTORS)

    unknown = [n for n in names if n not in EXTRACTORS]
    if unknown:
        print(f"error: unknown extractor(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    try:
        settings = get_settings()
        pdf = settings.require_handbook()
        page_map = load_page_map()
        client = get_client(settings)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    model, effort = settings.ingest_model, settings.ingest_effort
    total = Usage()
    done: list[str] = []
    for name in names:
        extractor = EXTRACTORS[name]
        pages = extractor.resolve(page_map)
        printed = describe_pages(printed_pages_of(page_map, pages))
        print(f"\n== {name} ==")
        print(f"   {extractor.description}")
        print(f"   printed pp. {printed}  (pdf pp. {describe_pages(pages)}, {len(pages)} pages)")
        def report(attempt: int, problems: list[str]) -> None:
            if problems:
                print(f"   attempt {attempt}: {len(problems)} problem(s) -> retrying")
                for problem in problems[:4]:
                    print(f"      - {problem}")
            else:
                print(f"   attempt {attempt}: validation passed")

        try:
            result = run_extractor(
                client, extractor, pdf, page_map, model=model, effort=effort, on_attempt=report
            )
        except ApiUnavailableError as exc:
            print(f"\n{exc}", file=sys.stderr)
            print(f"Stopped before {name}; {len(done)} extractor(s) completed.", file=sys.stderr)
            return 3
        path = write_extraction(result, model)
        done.append(name)
        total.merge(result.usage)
        for warning in result.warnings:
            print(f"   WARNING {warning}")
        u = result.usage
        total_in = u.total_input_tokens
        print(
            f"   {u.calls} request(s) over {result.attempts} attempt(s), "
            f"{total_in:,} input tokens "
            f"({u.cache_creation_input_tokens:,} cache write, {u.cache_read_input_tokens:,} "
            f"cache read), {u.output_tokens:,} output, "
            f"{u.latency_ms / 1000:.1f}s, ~${u.cost_usd(model):.2f}"
        )
        print(f"   -> {path}")

    grand_in = total.total_input_tokens
    print(
        f"\nTotal: {total.calls} requests, {grand_in:,} input tokens "
        f"({total.cache_creation_input_tokens:,} cache write, "
        f"{total.cache_read_input_tokens:,} cache read), "
        f"{total.output_tokens:,} output tokens, ~${total.cost_usd(model):.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
