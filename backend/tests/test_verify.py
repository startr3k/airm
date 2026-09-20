"""verify.py must surface a bad extraction rather than wave it through.

The verifier's judgement comes from the API, so these tests feed it a hand-saved
response and check what our code does with it. No network call is made.
"""

from __future__ import annotations

from conftest import load_fixture

from mindforge_assess.ingest.verify import blocking_failures, summarise, write_report
from mindforge_assess.llm import Usage


def test_bad_quote_is_detected() -> None:
    findings = load_fixture("verification_wrong_quote")
    item = summarise("dimensions_taxonomy", findings)

    assert item["quotes_checked"] == 3
    assert item["quotes_failed"] == 2
    failed = {q["item"] for q in item["failed_quotes"]}
    assert "Hallucination/ Fabrication/ Confabulation" in failed, "invented quote not caught"
    assert "Prompt injection" in failed, "right quote on the wrong page not caught"
    assert "Unrepresentative or biased data inputs" not in failed


def test_quote_found_on_another_page_records_where() -> None:
    item = summarise("dimensions_taxonomy", load_fixture("verification_wrong_quote"))
    moved = next(q for q in item["failed_quotes"] if q["item"] == "Prompt injection")
    assert moved["cited_page"] == 137
    assert moved["found_on_page"] == 138


def test_row_shortfall_blocks_the_build() -> None:
    item = summarise("dimensions_taxonomy", load_fixture("verification_wrong_quote"))
    assert item["rows_short"] is True

    reasons = blocking_failures([item])
    assert any("41" in reason and "40" in reason for reason in reasons), reasons
    assert any("Model inference attacks" in reason for reason in reasons), reasons


def test_only_meaning_errors_block() -> None:
    """A punctuation difference must not fail the build; a wrong value must."""
    item = summarise("dimensions_taxonomy", load_fixture("verification_wrong_quote"))
    severities = {error["severity"] for error in item["factual_errors"]}
    assert severities == {"wording", "wrong"}
    assert [e["severity"] for e in item["meaning_errors"]] == ["wrong"]

    reasons = blocking_failures([item])
    assert any("Fairness & Bias risk count" in reason for reason in reasons)
    assert not any("Lack of AI risk awareness" in reason for reason in reasons)


def test_clean_verification_blocks_nothing() -> None:
    clean = {
        "quote_checks": [
            {
                "item": "x",
                "cited_page": 131,
                "quote": "q",
                "found_on_cited_page": True,
                "found_on_page": None,
                "note": None,
            }
        ],
        "missing_rows": [],
        "unreadable_figures": [],
        "verifier_counted_rows": 41,
        "extracted_rows": 41,
        "factual_errors": [],
        "verdict": "pass",
        "summary": "All good.",
    }
    assert blocking_failures([summarise("dimensions_taxonomy", clean)]) == []


def test_extracted_more_rows_than_counted_does_not_block() -> None:
    """Only a shortfall means dropped rows; a surplus is the verifier undercounting."""
    findings = load_fixture("verification_wrong_quote")
    findings["extracted_rows"] = 42
    findings["missing_rows"] = []
    findings["factual_errors"] = []
    item = summarise("dimensions_taxonomy", findings)
    assert item["rows_short"] is False
    assert blocking_failures([item]) == []


def test_report_names_the_failures(tmp_path, monkeypatch) -> None:
    import mindforge_assess.ingest.verify as verify

    target = tmp_path / "verification_report.md"
    monkeypatch.setattr(verify, "REPORT_PATH", target)
    item = summarise("dimensions_taxonomy", load_fixture("verification_wrong_quote"))
    write_report([item], "claude-opus-5", Usage(input_tokens=10, output_tokens=5, calls=1))

    report = target.read_text()
    assert "Blocking failures: **3**" in report
    assert "Model inference attacks" in report
    assert "Hallucination/ Fabrication/ Confabulation" in report
    assert "**wrong**" in report and "**wording**" in report
