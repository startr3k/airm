"""Assessment history in a local SQLite file.

Plain `sqlite3` from the standard library: the schema is two tables and the access
pattern is insert-and-list, so an ORM would be more moving parts than the job needs.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import BACKEND_ROOT
from .models import AssessRequest, AssessResponse

# Overridable so the container can put the database on a mounted volume and keep
# history across rebuilds.
DB_PATH = Path(os.environ.get("MINDFORGE_DB") or BACKEND_ROOT / "assessments.sqlite3")

SCHEMA = """
CREATE TABLE IF NOT EXISTS assessments (
    id                  TEXT PRIMARY KEY,
    created_at          TEXT NOT NULL,
    description         TEXT NOT NULL,
    summary             TEXT NOT NULL,
    ai_in_scope         INTEGER NOT NULL,
    ai_type             TEXT NOT NULL,
    inherent_risk_tier  TEXT NOT NULL,
    oversight_mode      TEXT NOT NULL,
    confidence          TEXT NOT NULL,
    override_count      INTEGER NOT NULL,
    model               TEXT NOT NULL,
    latency_ms          INTEGER NOT NULL,
    pack_version        INTEGER NOT NULL,
    request_json        TEXT NOT NULL,
    response_json       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assessments_created ON assessments (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assessments_tier ON assessments (inherent_risk_tier);
"""


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(path or DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db(path: Path | None = None) -> None:
    with connect(path) as connection:
        connection.executescript(SCHEMA)


def save(
    request: AssessRequest, response: AssessResponse, path: Path | None = None
) -> None:
    assessment = response.assessment
    with connect(path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO assessments (
                id, created_at, description, summary, ai_in_scope, ai_type,
                inherent_risk_tier, oversight_mode, confidence, override_count,
                model, latency_ms, pack_version, request_json, response_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                response.assessment_id,
                datetime.now(UTC).isoformat(timespec="seconds"),
                request.description,
                assessment.use_case_summary,
                int(assessment.ai_in_scope),
                assessment.ai_type,
                assessment.inherent_risk_tier,
                assessment.recommended_oversight_mode,
                assessment.confidence,
                len(response.policy_overrides),
                response.model,
                response.latency_ms,
                response.pack_version,
                json.dumps(request.model_dump()),
                json.dumps(response.model_dump()),
            ),
        )


_LIST_COLUMNS = (
    "id, created_at, summary, ai_in_scope, ai_type, inherent_risk_tier, "
    "oversight_mode, confidence, override_count, model, latency_ms"
)


def list_assessments(
    limit: int = 100, path: Path | None = None
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        rows = connection.execute(
            f"SELECT {_LIST_COLUMNS} FROM assessments ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{**dict(row), "ai_in_scope": bool(row["ai_in_scope"])} for row in rows]


def get_assessment(
    assessment_id: str, path: Path | None = None
) -> dict[str, Any] | None:
    with connect(path) as connection:
        row = connection.execute(
            "SELECT created_at, request_json, response_json FROM assessments WHERE id = ?",
            (assessment_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "created_at": row["created_at"],
        "request": json.loads(row["request_json"]),
        **json.loads(row["response_json"]),
    }
