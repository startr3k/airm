"""Run the gold set against a model and write a results file.

Two things here exist because of what the API actually did during development:

*   **Retries.** Transient upstream 500s appeared several times over a few hours of
    work. A 30-call run that dies on call 19 and reports nothing is useless, so API
    failures are retried with backoff and, if they still fail, recorded as errors
    against that run rather than scored as wrong answers.
*   **A warm-up call.** The system prompt is a ~6k-token cached prefix. Fire the whole
    set off in parallel from cold and every worker writes its own cache entry, which
    both inflates the cost and makes the cache-hit numbers meaningless. The first case
    runs alone to write the cache; everything after it reads.

Run: python backend/evals/run_evals.py --model claude-sonnet-5 -n 3
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anthropic

from ..assessor import AssessmentError, assess
from ..config import ConfigError, Settings, get_settings, sha256_file
from ..llm import ApiUnavailableError, OutputTruncatedError, ToolNotCalledError, get_client
from ..models import AssessResponse
from ..pack import load_pack
from ..prompts.build_system_prompt import RENDERED_PATH
from ..schema import assessment_tool
from . import report
from .gold import GOLD_PATH, GoldCase, GoldSetError, load_gold, validate_gold
from .scoring import RunGrade, aggregate, failed_run, grade

MAX_ATTEMPTS = 4
BACKOFF_SECONDS = (2.0, 8.0, 20.0)


# An upstream fault that arrives *during* a stream is reported inside the event
# stream, and the SDK raises it carrying the status of the stream response itself --
# which was a 200. Both failures in the first Sonnet run looked like this, and a
# status-code check alone let them through unretried. The body is the only signal.
TRANSIENT_MARKERS = (
    "api_error",
    "overloaded",
    "internal server error",
    "service unavailable",
    "timeout",
)


def _retryable(exc: Exception) -> bool:
    """Worth trying again: upstream 5xx, rate limits, dropped connections."""
    if isinstance(exc, ApiUnavailableError):
        return False  # no credit or bad key -- retrying just burns time
    if isinstance(exc, anthropic.RateLimitError | anthropic.APIConnectionError):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        if exc.status_code >= 500:
            return True
        body = str(exc).lower()
        return any(marker in body for marker in TRANSIENT_MARKERS)
    # A truncated response is worth one more try: how far adaptive thinking runs varies
    # run to run, so the same request usually finishes inside the budget next time.
    return isinstance(exc, ToolNotCalledError | OutputTruncatedError)


def run_case(
    case: GoldCase,
    *,
    run: int,
    model: str,
    client: anthropic.Anthropic,
    settings: Settings,
    pack: Any,
    on_event: Any = None,
) -> RunGrade:
    """One assessment, retried on transient API failures."""
    request = case.request.model_copy(update={"model": model})
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response: AssessResponse = assess(
                request, client=client, settings=settings, pack=pack
            )
        except (AssessmentError, ValueError) as exc:
            # The model answered but the answer did not validate. That is a result
            # about the model, not a flaky network, so it is not retried.
            return failed_run(
                case,
                run=run,
                error=f"invalid assessment: {exc}",
                attempts=attempt,
                kind="invalid_assessment",
            )
        except Exception as exc:  # noqa: BLE001 - classified immediately below
            last_error = exc
            if not _retryable(exc) or attempt == MAX_ATTEMPTS:
                return failed_run(
                    case, run=run, error=f"{type(exc).__name__}: {exc}", attempts=attempt
                )
            delay = BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)]
            if on_event:
                on_event("retry", case.id, run, f"{type(exc).__name__}, retrying in {delay:.0f}s")
            time.sleep(delay)
            continue
        return grade(case, response, run=run, attempts=attempt)

    return failed_run(
        case, run=run, error=f"{type(last_error).__name__}: {last_error}", attempts=MAX_ATTEMPTS
    )


def run_suite(
    cases: list[GoldCase],
    *,
    model: str,
    n: int,
    concurrency: int,
    settings: Settings,
    on_event: Any = None,
) -> list[RunGrade]:
    client = get_client(settings)
    pack = load_pack()
    jobs = [(case, run) for run in range(1, n + 1) for case in cases]
    grades: list[RunGrade] = []

    def execute(job: tuple[GoldCase, int]) -> RunGrade:
        case, run = job
        if on_event:
            on_event("start", case.id, run, None)
        result = run_case(
            case, run=run, model=model, client=client, settings=settings, pack=pack,
            on_event=on_event,
        )
        if on_event:
            on_event("done", case.id, run, result)
        return result

    # The first job runs alone so it writes the prompt cache the rest will read.
    if jobs:
        grades.append(execute(jobs[0]))
        jobs = jobs[1:]

    if concurrency <= 1:
        grades.extend(execute(job) for job in jobs)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            grades.extend(pool.map(execute, jobs))

    order = {(case.id, run): i for i, (case, run) in enumerate(
        [(c, r) for r in range(1, n + 1) for c in cases]
    )}
    grades.sort(key=lambda g: order.get((g.case_id, g.run), 0))
    return grades


def build_result(
    cases: list[GoldCase],
    grades: list[RunGrade],
    *,
    model: str,
    n: int,
    effort: str,
    started: datetime,
    duration_s: float,
) -> dict[str, Any]:
    pack = load_pack()
    return {
        "run_id": started.strftime("%Y-%m-%dT%H-%M-%SZ"),
        "model": model,
        "effort": effort,
        "n": n,
        "cases": len(cases),
        "started_at": started.isoformat(),
        "duration_s": round(duration_s, 1),
        "pack_version": pack.version,
        "pdf_sha256": pack.pdf_sha256,
        # Which prompt produced these numbers. Change the prompt, the hash moves, and
        # an old results file can no longer be mistaken for a current one.
        "prompt_sha256": sha256_file(RENDERED_PATH) if RENDERED_PATH.is_file() else None,
        # The tool schema constrains the answer as much as the prompt does, so it is
        # fingerprinted too -- changing it invalidates a comparison just as surely.
        "tool_sha256": hashlib.sha256(
            json.dumps(assessment_tool(), sort_keys=True).encode()
        ).hexdigest(),
        "gold_sha256": sha256_file(GOLD_PATH),
        "summary": aggregate(cases, grades),
        "runs": [g.as_dict() for g in grades],
    }


def write_result(result: dict[str, Any], results_dir: Path | None = None) -> tuple[Path, Path]:
    directory = (results_dir or report.RESULTS_DIR) / report.slug(result["model"])
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"{result['run_id']}.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    md_path = json_path.with_suffix(".md")
    md_path.write_text(report.render(result))
    return json_path, md_path


# ------------------------------------------------------------------------ CLI


def _progress(event: str, case_id: str, run: int, payload: Any) -> None:
    if event == "retry":
        print(f"  ! {case_id} run {run}: {payload}", file=sys.stderr)
    elif event == "done":
        assert isinstance(payload, RunGrade)
        if payload.error:
            mark, detail = "ERR", payload.error
        else:
            failed = payload.failures
            mark = "ok " if not failed else "MISS"
            detail = (
                f"tier={payload.tier} {payload.latency_ms / 1000:.1f}s"
                + (f"  failed: {', '.join(c.field for c in failed)}" if failed else "")
            )
        print(f"  {mark} {case_id} run {run}  {detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the gold set against a model.")
    parser.add_argument("--model", default=None, help="model id (default: ASSESS_MODEL)")
    parser.add_argument("-n", "--runs", type=int, default=3, help="runs per case (default 3)")
    parser.add_argument("--case", action="append", default=[], help="only these case ids")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--validate-only", action="store_true", help="check the gold set and exit")
    parser.add_argument("--compare", action="store_true", help="re-render the model comparison")
    args = parser.parse_args(argv)

    try:
        cases = load_gold()
        problems = validate_gold(cases)
    except GoldSetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if problems:
        print("The gold set does not match the framework pack:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2

    if args.compare:
        return _write_comparison()

    if args.validate_only:
        print(f"{len(cases)} gold cases validate against pack v{load_pack().version}.")
        return 0

    if args.case:
        wanted = set(args.case)
        unknown = wanted - {c.id for c in cases}
        if unknown:
            print(f"error: unknown case id(s): {sorted(unknown)}", file=sys.stderr)
            return 2
        cases = [c for c in cases if c.id in wanted]

    try:
        settings = get_settings()
        settings.require_api_key()
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    model = args.model or settings.assess_model
    total = len(cases) * args.runs
    print(
        f"{model} · {len(cases)} cases × {args.runs} runs = {total} assessments "
        f"· effort {settings.assess_effort} · concurrency {args.concurrency}"
    )

    started = datetime.now(UTC)
    clock = time.perf_counter()
    try:
        grades = run_suite(
            cases,
            model=model,
            n=args.runs,
            concurrency=args.concurrency,
            settings=settings,
            on_event=_progress,
        )
    except ApiUnavailableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    duration = time.perf_counter() - clock

    result = build_result(
        cases, grades, model=model, n=args.runs, effort=settings.assess_effort,
        started=started, duration_s=duration,
    )
    json_path, md_path = write_result(result)
    summary = result["summary"]
    print("\n" + _headline(summary, duration))
    print(f"{json_path}\n{md_path}")
    _write_comparison()
    return 0


def _field(summary: dict[str, Any], name: str) -> str:
    block = summary["field_accuracy"].get(name)
    return f"{block['accuracy']:.0%}" if block else "—"


def _headline(summary: dict[str, Any], duration: float) -> str:
    """One line for the terminal. Every part can be absent if every run failed."""
    accuracy = summary["overall_accuracy"]
    agreement = summary["tier_consistency"]["mean_modal_agreement"]
    parts = [
        f"{accuracy:.1%} of {summary['checks_graded']} checks"
        if accuracy is not None
        else f"no graded checks ({summary['runs_errored']} run(s) failed)",
        f"tier exact {_field(summary, 'inherent_risk_tier')}",
        f"consistency {agreement:.0%}" if agreement is not None else "consistency —",
        f"${summary['cost_usd']['total']:.2f}",
        f"{duration / 60:.1f} min",
    ]
    return " · ".join(parts)


def _write_comparison() -> int:
    results = report.all_latest()
    path = report.RESULTS_DIR / "comparison.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.compare(results))
    print(f"{path}  ({len(results)} model(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
