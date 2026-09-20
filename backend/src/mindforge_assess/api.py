"""FastAPI app.

A request never reads the handbook PDF and never needs an ingestion run: everything the
API serves comes from the committed framework pack.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import storage
from .assessor import AssessmentError, assess, assess_stream
from .config import REPO_ROOT, ConfigError, get_settings
from .evals import report as eval_report
from .evals import service as eval_service
from .evals.gold import GoldSetError, load_gold, validate_gold
from .llm import OutputTruncatedError
from .models import AssessRequest, AssessResponse, EvalRunRequest, HealthResponse
from .pack import PackNotFoundError, load_pack
from .source import SourceUnavailableError, citation, pdf_index, render_page

# The Vite dev server; the Docker image serves the built front end same-origin.
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    # The backend refuses to start without a key: failing at boot is far kinder than
    # failing on the first user's request.
    settings.require_api_key()
    load_pack()
    storage.init_db()
    yield


app = FastAPI(
    title="MindForge Risk Assessor",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    try:
        pack = load_pack()
    except PackNotFoundError as exc:
        return HealthResponse(
            ok=False,
            api_key_present=settings.has_api_key,
            pack_loaded=False,
            pack_version=None,
            pdf_sha256=None,
            assess_model=settings.assess_model,
            detail=str(exc),
        )
    return HealthResponse(
        ok=settings.has_api_key,
        api_key_present=settings.has_api_key,
        pack_loaded=True,
        pack_version=pack.version,
        pdf_sha256=pack.pdf_sha256,
        assess_model=settings.assess_model,
        detail=None if settings.has_api_key else "ANTHROPIC_API_KEY is not set",
    )


@app.post("/api/assess", response_model=AssessResponse)
def post_assess(request: AssessRequest) -> AssessResponse:
    try:
        response = assess(request)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OutputTruncatedError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"{exc} Retrying usually succeeds.",
        ) from exc
    except AssessmentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # upstream failures, mapped most-specific first
        raise _upstream_error(exc) from exc
    storage.save(request, response)
    return response


def _upstream_error(exc: Exception) -> HTTPException:
    """Turn an Anthropic API failure into a status the UI can act on.

    The distinction that matters to a caller is whether retrying is worth it: a 429 or a
    5xx will likely succeed on a retry, a 401 or a 400 will not.
    """
    if isinstance(exc, anthropic.RateLimitError):
        return HTTPException(
            status_code=429,
            detail="The Anthropic API is rate limiting this key. Retry shortly.",
        )
    if isinstance(exc, anthropic.AuthenticationError):
        return HTTPException(
            status_code=503, detail="The Anthropic API rejected the credentials."
        )
    if isinstance(exc, anthropic.BadRequestError):
        message = str(getattr(exc, "message", "") or exc)
        if "credit balance is too low" in message.lower():
            return HTTPException(
                status_code=503,
                detail="The Anthropic account is out of credit.",
            )
        return HTTPException(status_code=502, detail=f"Request rejected: {message}")
    if isinstance(exc, anthropic.APIStatusError):
        # A fault raised mid-stream carries the status of the stream response, which
        # was a 200, so the number is only worth quoting when it is actually an error.
        status = getattr(exc, "status_code", 502)
        where = f" returned {status}" if status >= 400 else " failed mid-response"
        return HTTPException(
            status_code=502,
            detail=(
                f"The Anthropic API{where}. This is usually transient; "
                f"retrying is worthwhile."
            ),
        )
    if isinstance(exc, anthropic.APIConnectionError):
        return HTTPException(
            status_code=504, detail="Could not reach the Anthropic API."
        )
    raise exc


@app.post("/api/assess/stream")
def post_assess_stream(request: AssessRequest) -> StreamingResponse:
    """Server-Sent Events: `status` steps as the model works, then one `result`."""

    def events() -> Iterator[str]:
        saved = False
        try:
            for name, payload in assess_stream(request):
                if name == "result" and not saved:
                    storage.save(request, AssessResponse.model_validate(payload))
                    saved = True
                yield f"event: {name}\ndata: {json.dumps(payload)}\n\n"
        except ConfigError as exc:
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"
        except Exception as exc:  # noqa: BLE001 - the stream must close cleanly
            detail = _upstream_error(exc).detail if _is_upstream(exc) else str(exc)
            yield f"event: error\ndata: {json.dumps({'detail': detail})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Without this an nginx or similar in front would buffer the whole stream
            # and the stepper would arrive all at once at the end.
            "X-Accel-Buffering": "no",
        },
    )


def _is_upstream(exc: Exception) -> bool:
    return isinstance(exc, anthropic.APIError)


@app.get("/api/assessments")
def get_assessments(limit: int = 100) -> list[dict[str, Any]]:
    return storage.list_assessments(limit=min(max(limit, 1), 500))


@app.get("/api/assessments/{assessment_id}")
def get_assessment(assessment_id: str) -> dict[str, Any]:
    record = storage.get_assessment(assessment_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No assessment {assessment_id}")
    return record


# ----------------------------------------------------------------------- evals


@app.get("/api/evals/latest")
def get_evals_latest() -> dict[str, Any]:
    """The most recent run per model, plus the gold set itself.

    The per-run detail is left out: the page needs the summary and the per-case rows,
    and a full run file is a few hundred kilobytes of check records.
    """
    # The configured assessor leads, so the page opens on the model the tool actually
    # uses rather than on whichever model sorts first alphabetically.
    assess_model = get_settings().assess_model
    results = sorted(
        ({k: v for k, v in result.items() if k != "runs"} for result in eval_report.all_latest()),
        key=lambda result: (result["model"] != assess_model, result["model"]),
    )
    try:
        cases = load_gold()
        gold = [
            {
                "id": case.id,
                "title": case.title,
                "tests": case.tests,
                "description": case.request.description,
                "expect": {
                    "ai_in_scope": case.expect.ai_in_scope,
                    "ai_type": case.expect.ai_type,
                    "tier": case.expect.tier,
                    "tier_accepted": list(case.expect.accepted_tiers),
                    "oversight_modes": list(case.expect.oversight_modes),
                },
            }
            for case in cases
        ]
        gold_problems = validate_gold(cases)
    except GoldSetError as exc:
        gold, gold_problems = [], [str(exc)]

    return {
        "models": results,
        "gold": gold,
        "gold_problems": gold_problems,
        "comparison_markdown": eval_report.compare(results) if results else None,
    }


@app.post("/api/evals/run", status_code=202)
def post_evals_run(request: EvalRunRequest) -> dict[str, Any]:
    """Start a run in the background. Returns immediately; poll /api/evals/status."""
    try:
        return eval_service.start(
            model=request.model, n=request.n, case_ids=request.cases or None
        )
    except eval_service.EvalBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ValueError, GoldSetError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/evals/status")
def get_evals_status() -> dict[str, Any]:
    return eval_service.status()


@app.get("/api/framework")
def get_framework() -> dict[str, Any]:
    pack = load_pack()
    return {
        "pack_version": pack.version,
        "dimensions": pack.dimensions,
        "materiality": pack.materiality,
        "oversight_modes": pack.oversight_modes,
        "monitoring": pack.monitoring,
        "metrics": pack.metrics,
        "guardrails": pack.guardrails,
        "interpretability_typology": pack.raw.get("interpretability_typology", []),
        "considerations": pack.considerations,
        "agentic": pack.agentic,
        "illustrations": pack.illustrations,
        "definitions": pack.definitions,
    }


@app.get("/api/framework/provenance")
def get_provenance() -> dict[str, Any]:
    pack = load_pack()
    provenance = pack.provenance
    verification = provenance.get("verification", {})
    summaries = verification.get("summaries", [])
    return {
        **{k: v for k, v in provenance.items() if k != "verification"},
        "verification": {
            **{k: v for k, v in verification.items() if k != "summaries"},
            "summaries": summaries,
            "quotes_checked": sum(s.get("quotes_checked", 0) for s in summaries),
            "quotes_failed": sum(s.get("quotes_failed", 0) for s in summaries),
            "extractors_passed": sum(
                1 for s in summaries if s.get("verdict", "").startswith("pass")
            ),
            "extractors_total": len(summaries),
        },
    }


@app.get("/api/framework/index")
def get_framework_index() -> dict[str, Any]:
    """Name -> citable id, for turning an assessment's names back into citations.

    The full pack is ~200 kB and mostly prose. A results view only needs to know that
    "Red teaming" is `guardrail:red-teaming` on printed page 156, so that is all this
    returns. Names are exact: the assessor grounds every name against these libraries
    before the response leaves the server.
    """
    pack = load_pack()
    index: dict[str, dict[str, Any]] = {}
    for item_id in pack.item_ids():
        entry = pack.item(item_id)
        if entry is None:
            continue
        source = entry["item"].get("source") or {}
        index[item_id] = {"label": entry["label"], "page": source.get("page")}

    def by_name(items: list[dict[str, Any]], key: str) -> dict[str, str]:
        return {str(item[key]): str(item["item_id"]) for item in items if item.get("item_id")}

    return {
        "items": index,
        "guardrails": by_name(pack.guardrails, "name"),
        "metrics": by_name(pack.metrics, "name"),
        "dimensions": by_name(pack.dimensions, "dimension"),
        "factors": by_name(pack.materiality["factors"], "factor"),
        "oversight_modes": by_name(pack.oversight_modes, "mode"),
        "considerations": {
            str(item["number"]): str(item["item_id"])
            for item in pack.considerations
            if item.get("item_id")
        },
    }


@app.get("/api/framework/source/{item_id}")
def get_source(item_id: str) -> dict[str, Any]:
    """Where one dimension, factor, guardrail, metric or Consideration came from.

    The printed page, the section and the verbatim quote all come from the pack. The
    image is a separate request so the JSON stays small and the browser can cache the
    page picture on its own.
    """
    pack = load_pack()
    found = citation(item_id, pack)
    if found is None:
        raise HTTPException(
            status_code=404,
            detail=f"No citable item {item_id!r}. See /api/framework for what exists.",
        )
    page = found.page
    return found.as_dict(
        pdf_page=pdf_index(page, pack) + 1 if page is not None else None,
        image_url=f"/api/framework/source/{item_id}/page.png" if page is not None else None,
    )


@app.get("/api/framework/source/{item_id}/page.png")
def get_source_page(item_id: str, scale: int = 2) -> Response:
    """The cited page, rendered server-side for display only.

    This is the one place the handbook PDF is opened at request time, and it is never
    read -- only drawn. Nothing the tool asserts about the handbook comes from here.
    """
    pack = load_pack()
    found = citation(item_id, pack)
    if found is None:
        raise HTTPException(status_code=404, detail=f"No citable item {item_id!r}.")
    if found.page is None:
        raise HTTPException(
            status_code=404, detail=f"{item_id!r} carries no printed page number."
        )
    try:
        png = render_page(found.page, scale=scale, pack=pack)
    except SourceUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=png,
        media_type="image/png",
        headers={
            # The handbook does not change while the server runs, and the cache key
            # includes its hash, so this is safe to hold for a long time.
            "Cache-Control": "public, max-age=86400, immutable",
            "Content-Disposition": f'inline; filename="handbook-p{found.page}.png"',
        },
    )


# --------------------------------------------------------------- static front end

# In the container the built front end is served from this same app, so there is one
# port, one origin and no CORS in play. In development Vite serves it instead and this
# directory does not exist, which is why the mount is conditional rather than assumed.
STATIC_DIR = Path(os.environ.get("STATIC_DIR") or REPO_ROOT / "frontend" / "dist")

if (STATIC_DIR / "index.html").is_file():
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="assets",
    )

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        """Serve the built app, falling back to index.html for client-side routes.

        Registered last so every API route matches first. An unknown `/api/...` path is
        still a 404 rather than a page of HTML, which would otherwise turn a typo in a
        fetch into a confusing parse error.
        """
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail=f"No such endpoint: /{path}")
        candidate = (STATIC_DIR / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(STATIC_DIR.resolve()):
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
