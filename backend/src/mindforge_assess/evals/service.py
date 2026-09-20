"""In-process job state for eval runs triggered from the UI.

One run at a time, deliberately. An eval run makes tens of paid API calls over several
minutes; letting a page refresh start a second one would double the bill and interleave
two sets of results. A second request gets a 409 and the status of the run in flight.

State lives in memory because it belongs to the process that is doing the work -- a
restart mid-run loses the progress counter, which is the correct outcome, since the run
itself is gone too.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..llm import ApiUnavailableError
from .gold import GoldCase, load_gold
from .runner import build_result, run_suite, write_result
from .scoring import RunGrade


class EvalBusyError(RuntimeError):
    """A run is already in flight."""


@dataclass
class JobState:
    state: str = "idle"  # idle | running | done | error
    model: str | None = None
    n: int = 0
    total: int = 0
    completed: int = 0
    errors: int = 0
    retries: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    last_event: str | None = None
    run_id: str | None = None
    detail: str | None = None
    result_path: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self.state,
                "model": self.model,
                "n": self.n,
                "total": self.total,
                "completed": self.completed,
                "errors": self.errors,
                "retries": self.retries,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "last_event": self.last_event,
                "run_id": self.run_id,
                "detail": self.detail,
                "progress": self.completed / self.total if self.total else None,
            }


_JOB = JobState()


def status() -> dict[str, Any]:
    return _JOB.snapshot()


def is_running() -> bool:
    return _JOB.state == "running"


def start(
    *,
    model: str | None = None,
    n: int = 3,
    case_ids: list[str] | None = None,
    concurrency: int = 4,
    results_dir: Path | None = None,
) -> dict[str, Any]:
    """Launch a run in a background thread and return the initial status."""
    settings = get_settings()
    with _JOB._lock:
        if _JOB.state == "running":
            raise EvalBusyError("An eval run is already in progress.")
        cases = _select(load_gold(), case_ids)
        _JOB.state = "running"
        _JOB.model = model or settings.assess_model
        _JOB.n = n
        _JOB.total = len(cases) * n
        _JOB.completed = 0
        _JOB.errors = 0
        _JOB.retries = 0
        _JOB.started_at = datetime.now(UTC).isoformat()
        _JOB.finished_at = None
        _JOB.last_event = "starting"
        _JOB.run_id = None
        _JOB.detail = None
        _JOB.result_path = None

    thread = threading.Thread(
        target=_work,
        args=(cases, _JOB.model, n, concurrency, results_dir),
        name="eval-run",
        daemon=True,
    )
    thread.start()
    return status()


def _select(cases: list[GoldCase], case_ids: list[str] | None) -> list[GoldCase]:
    if not case_ids:
        return cases
    wanted = set(case_ids)
    unknown = wanted - {c.id for c in cases}
    if unknown:
        raise ValueError(f"unknown case id(s): {sorted(unknown)}")
    return [c for c in cases if c.id in wanted]


def _work(
    cases: list[GoldCase],
    model: str,
    n: int,
    concurrency: int,
    results_dir: Path | None,
) -> None:
    settings = get_settings()
    started = datetime.now(UTC)
    clock = datetime.now(UTC)

    def on_event(event: str, case_id: str, run: int, payload: Any) -> None:
        with _JOB._lock:
            if event == "retry":
                _JOB.retries += 1
                _JOB.last_event = f"{case_id} run {run}: {payload}"
            elif event == "done":
                _JOB.completed += 1
                if isinstance(payload, RunGrade) and payload.error:
                    _JOB.errors += 1
                _JOB.last_event = f"{case_id} run {run} finished"
            elif event == "start":
                _JOB.last_event = f"{case_id} run {run} started"

    try:
        grades = run_suite(
            cases,
            model=model,
            n=n,
            concurrency=concurrency,
            settings=settings,
            on_event=on_event,
        )
        duration = (datetime.now(UTC) - clock).total_seconds()
        result = build_result(
            cases, grades, model=model, n=n, effort=settings.assess_effort,
            started=started, duration_s=duration,
        )
        json_path, _ = write_result(result, results_dir)
    except (ApiUnavailableError, Exception) as exc:  # noqa: BLE001 - reported, not raised
        with _JOB._lock:
            _JOB.state = "error"
            _JOB.detail = f"{type(exc).__name__}: {exc}"
            _JOB.finished_at = datetime.now(UTC).isoformat()
        return

    with _JOB._lock:
        _JOB.state = "done"
        _JOB.run_id = result["run_id"]
        _JOB.result_path = str(json_path)
        _JOB.finished_at = datetime.now(UTC).isoformat()
        _JOB.last_event = "complete"


def reset() -> None:
    """Return to idle. Used by the tests; harmless in production."""
    global _JOB
    _JOB = JobState()
