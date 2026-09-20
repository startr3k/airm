"""FastAPI routes, with the assessor stubbed. No API key and no network required."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_policy import make_assessment

from mindforge_assess import api, storage
from mindforge_assess.models import AssessRequest, AssessResponse, Usage


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-a-real-key")
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite3")

    from mindforge_assess.config import get_settings

    get_settings.cache_clear()
    with TestClient(api.app) as test_client:
        yield test_client
    get_settings.cache_clear()


def stub_response(**overrides: Any) -> AssessResponse:
    return AssessResponse(
        assessment=make_assessment(**overrides),
        policy_overrides=[],
        model="claude-sonnet-5",
        usage=Usage(input_tokens=10, output_tokens=20, cache_read_input_tokens=8269),
        latency_ms=1234,
        assessment_id="test0000test0000",
        pack_version=1,
        pdf_sha256="c" * 64,
    )


def test_health_reports_pack_and_key(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["api_key_present"] is True
    assert body["pack_loaded"] is True
    assert body["pack_version"] == 1
    assert len(body["pdf_sha256"]) == 64


def test_assess_returns_usage_and_persists(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(api, "assess", lambda request: stub_response())

    body = client.post("/api/assess", json={"description": "A chatbot"}).json()
    assert body["assessment"]["inherent_risk_tier"] == "low"
    assert body["usage"]["cache_read_input_tokens"] == 8269
    assert body["latency_ms"] == 1234
    assert body["assessment_id"] == "test0000test0000"

    history = client.get("/api/assessments").json()
    assert len(history) == 1
    assert history[0]["id"] == "test0000test0000"
    assert history[0]["ai_in_scope"] is True

    detail = client.get("/api/assessments/test0000test0000").json()
    assert detail["request"]["description"] == "A chatbot"
    assert detail["assessment"]["ai_type"] == "gen_ai"


def test_unknown_assessment_is_404(client: TestClient) -> None:
    assert client.get("/api/assessments/nope").status_code == 404


def test_assess_rejects_an_empty_description(client: TestClient) -> None:
    assert client.post("/api/assess", json={"description": ""}).status_code == 422


def test_assess_rejects_unknown_fields(client: TestClient) -> None:
    response = client.post(
        "/api/assess", json={"description": "x", "deployment_patern": "build"}
    )
    assert response.status_code == 422, "a typo'd field must not be silently ignored"


def test_assess_rejects_an_invalid_deployment_pattern(client: TestClient) -> None:
    response = client.post(
        "/api/assess", json={"description": "x", "deployment_pattern": "rent"}
    )
    assert response.status_code == 422


def test_assessment_failure_surfaces_as_502(client: TestClient, monkeypatch) -> None:
    from mindforge_assess.assessor import AssessmentError

    def boom(request: AssessRequest) -> AssessResponse:
        raise AssessmentError("schema mismatch")

    monkeypatch.setattr(api, "assess", boom)
    response = client.post("/api/assess", json={"description": "A chatbot"})
    assert response.status_code == 502
    assert "schema mismatch" in response.json()["detail"]


def test_missing_key_surfaces_as_503(client: TestClient, monkeypatch) -> None:
    from mindforge_assess.config import ConfigError

    def no_key(request: AssessRequest) -> AssessResponse:
        raise ConfigError("ANTHROPIC_API_KEY is not set")

    monkeypatch.setattr(api, "assess", no_key)
    assert client.post("/api/assess", json={"description": "x"}).status_code == 503


def test_framework_serves_the_whole_pack(client: TestClient) -> None:
    body = client.get("/api/framework").json()
    assert len(body["dimensions"]) == 7
    assert len(body["considerations"]) == 17
    assert len(body["oversight_modes"]) == 3
    assert body["metrics"] and body["guardrails"]
    assert len(body["materiality"]["matrix"]["cells"]) == 9


def test_provenance_exposes_the_audit_trail(client: TestClient) -> None:
    body = client.get("/api/framework/provenance").json()
    assert len(body["pdf_sha256"]) == 64
    assert body["printed_to_pdf_offset"] == 7
    assert body["verification"]["blocking_failures"] == 0
    assert body["verification"]["extractors_passed"] == body["verification"]["extractors_total"]
    assert body["verification"]["quotes_failed"] == 0
    assert body["completeness"]["partial"] is False


def test_history_orders_newest_first(client: TestClient, monkeypatch) -> None:
    for index in range(3):
        monkeypatch.setattr(
            api,
            "assess",
            lambda request, i=index: stub_response().model_copy(
                update={"assessment_id": f"id{i}"}
            ),
        )
        client.post("/api/assess", json={"description": f"case {index}"})
    ids = [row["id"] for row in client.get("/api/assessments").json()]
    assert set(ids) == {"id0", "id1", "id2"}


@pytest.mark.parametrize(
    ("exc_name", "message", "expected"),
    [
        ("RateLimitError", "slow down", 429),
        ("AuthenticationError", "invalid x-api-key", 503),
        ("BadRequestError", "Your credit balance is too low", 503),
        ("BadRequestError", "The compiled grammar is too large", 502),
        ("InternalServerError", "Internal server error", 502),
        ("APIConnectionError", "connection refused", 504),
    ],
)
def test_upstream_failures_map_to_actionable_statuses(
    client: TestClient, monkeypatch, exc_name: str, message: str, expected: int
) -> None:
    """A transient upstream 500 must not surface as a bare 500 from our own API.

    This happened for real: the Anthropic API returned an `api_error` mid-demo and the
    route leaked it as an unhandled 500 with no indication that a retry would work.
    """
    import anthropic

    class Fake(getattr(anthropic, exc_name)):  # type: ignore[misc]
        # Bypasses the SDK constructor, which requires a live httpx request object.
        def __init__(self) -> None:
            Exception.__init__(self, message)
            self.message = message
            self.status_code = 500

    def boom(request: AssessRequest) -> AssessResponse:
        raise Fake()

    monkeypatch.setattr(api, "assess", boom)
    assert client.post("/api/assess", json={"description": "x"}).status_code == expected


def test_an_unexpected_error_is_not_swallowed(client: TestClient, monkeypatch) -> None:
    """Only Anthropic failures are translated; a bug in our own code must still surface."""

    def boom(request: AssessRequest) -> AssessResponse:
        raise ZeroDivisionError("a real bug")

    monkeypatch.setattr(api, "assess", boom)
    with pytest.raises(ZeroDivisionError):
        client.post("/api/assess", json={"description": "x"})


# ----------------------------------------------------------------------- evals


def test_evals_latest_serves_the_gold_set_before_any_run(client: TestClient) -> None:
    body = client.get("/api/evals/latest").json()
    assert len(body["gold"]) == 10
    assert body["gold_problems"] == []
    assert {c["id"] for c in body["gold"]} >= {"credit-underwriting", "agentic-rm-assistant"}


def test_evals_latest_omits_the_per_run_detail(client: TestClient, tmp_path) -> None:
    """A full run file is large; the page only needs the summary and per-case rows."""
    from datetime import UTC, datetime

    from test_evals import grades_for

    from mindforge_assess.evals import report as eval_report
    from mindforge_assess.evals.runner import build_result, write_result

    cases, grades = grades_for(["high", "high"])
    result = build_result(
        cases, grades, model="claude-sonnet-5", n=2, effort="medium",
        started=datetime.now(UTC), duration_s=1.0,
    )
    write_result(result, tmp_path)

    original = eval_report.RESULTS_DIR
    eval_report.RESULTS_DIR = tmp_path
    try:
        body = client.get("/api/evals/latest").json()
    finally:
        eval_report.RESULTS_DIR = original

    assert [m["model"] for m in body["models"]] == ["claude-sonnet-5"]
    assert "runs" not in body["models"][0]
    assert body["models"][0]["summary"]["runs_ok"] == 2
    assert "Model comparison" in body["comparison_markdown"]


def test_a_second_eval_run_is_refused_while_one_is_in_flight(client: TestClient) -> None:
    """Each run is minutes of paid API calls; a double-click must not start two."""
    from mindforge_assess.evals import service

    service.reset()
    service._JOB.state = "running"
    try:
        response = client.post("/api/evals/run", json={"n": 1})
        assert response.status_code == 409
        assert client.get("/api/evals/status").json()["state"] == "running"
    finally:
        service.reset()


def test_an_unknown_case_id_is_a_400_not_a_500(client: TestClient) -> None:
    from mindforge_assess.evals import service

    service.reset()
    response = client.post("/api/evals/run", json={"cases": ["no-such-case"], "n": 1})
    assert response.status_code == 400
    assert "no-such-case" in response.json()["detail"]
    assert service.status()["state"] == "idle"


def test_eval_run_rejects_an_absurd_n(client: TestClient) -> None:
    assert client.post("/api/evals/run", json={"n": 50}).status_code == 422


def test_the_configured_assessor_model_leads_the_eval_results(client: TestClient, tmp_path) -> None:
    """The page should open on the model the tool actually uses, not on whichever one
    sorts first alphabetically."""
    from datetime import UTC, datetime

    from test_evals import grades_for

    from mindforge_assess.evals import report as eval_report
    from mindforge_assess.evals.runner import build_result, write_result

    cases, grades = grades_for(["high", "high"])
    started = datetime.now(UTC)
    for model in ("claude-opus-5", "claude-sonnet-5"):
        write_result(
            build_result(cases, grades, model=model, n=2, effort="medium",
                         started=started, duration_s=1.0),
            tmp_path,
        )

    original = eval_report.RESULTS_DIR
    eval_report.RESULTS_DIR = tmp_path
    try:
        body = client.get("/api/evals/latest").json()
    finally:
        eval_report.RESULTS_DIR = original

    assert [m["model"] for m in body["models"]] == ["claude-sonnet-5", "claude-opus-5"]


# ------------------------------------------------------------------- citations


def test_source_returns_the_printed_page_section_and_quote(client: TestClient) -> None:
    body = client.get("/api/framework/source/consideration:1").json()
    assert body["page"] == 159
    assert body["section"] == "Appendix H"
    assert body["quote"].startswith("Consideration 1.")
    # The PDF index is offset from the printed number and is reported separately.
    assert body["pdf_page"] == 166
    assert body["image_url"] == "/api/framework/source/consideration:1/page.png"


def test_an_unknown_item_id_is_a_404_that_says_where_to_look(client: TestClient) -> None:
    response = client.get("/api/framework/source/guardrail:not-a-thing")
    assert response.status_code == 404
    assert "/api/framework" in response.json()["detail"]


def test_a_missing_handbook_404s_the_image_but_not_the_citation(
    client: TestClient, monkeypatch, tmp_path
) -> None:
    """The quote comes from the pack, so a citation survives without the book."""
    import mindforge_assess.source as source

    monkeypatch.setattr(source, "handbook_path", lambda settings=None: None)
    assert client.get("/api/framework/source/dimension:fairness-bias").status_code == 200
    image = client.get("/api/framework/source/dimension:fairness-bias/page.png")
    assert image.status_code == 404
    assert "citation still resolves" in image.json()["detail"]


def test_the_database_location_can_be_moved_by_environment(monkeypatch, tmp_path) -> None:
    """The container puts it on a mounted volume so history survives a rebuild."""
    import importlib

    monkeypatch.setenv("MINDFORGE_DB", str(tmp_path / "elsewhere.sqlite3"))
    module = importlib.reload(storage)
    try:
        assert module.DB_PATH == tmp_path / "elsewhere.sqlite3"
    finally:
        monkeypatch.delenv("MINDFORGE_DB")
        importlib.reload(storage)
