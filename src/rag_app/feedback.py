"""Store employee reports about incorrect or outdated answers in a local SQLite database."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .config import settings

ISSUE_TYPES = ["Incorrect", "Outdated", "Missing information", "Other"]
STATUSES = ["open", "in review", "resolved", "dismissed"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,              -- UTC, ISO 8601
    reporter    TEXT NOT NULL,
    question    TEXT NOT NULL,
    answer      TEXT,                       -- NULL when reported from search-only mode
    sources     TEXT NOT NULL,              -- JSON list of source file names shown
    issue_type  TEXT NOT NULL,
    affected    TEXT NOT NULL,              -- JSON list of sources the reporter flagged
    description TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open'
)
"""


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or settings.feedback_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def add_report(
    *,
    reporter: str,
    question: str,
    answer: str | None,
    sources: list[str],
    issue_type: str,
    affected: list[str],
    description: str,
    db_path: Path | None = None,
) -> int:
    """Save a report and return its id."""
    if issue_type not in ISSUE_TYPES:
        raise ValueError(f"issue_type must be one of {ISSUE_TYPES}")
    if not reporter.strip() or not description.strip():
        raise ValueError("reporter and description are required")
    with closing(_connect(db_path)) as conn, conn:
        cur = conn.execute(
            "INSERT INTO reports (created_at, reporter, question, answer, sources,"
            " issue_type, affected, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                reporter.strip(),
                question,
                answer,
                json.dumps(sources),
                issue_type,
                json.dumps(affected),
                description.strip(),
            ),
        )
        return int(cur.lastrowid)


def list_reports(status: str | None = None, db_path: Path | None = None) -> list[dict]:
    """Return reports newest first, optionally filtered by status."""
    sql = "SELECT * FROM reports"
    params: tuple = ()
    if status:
        sql += " WHERE status = ?"
        params = (status,)
    sql += " ORDER BY id DESC"
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(sql, params).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["sources"] = json.loads(d["sources"])
        d["affected"] = json.loads(d["affected"])
        out.append(d)
    return out


def set_status(report_id: int, status: str, db_path: Path | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    with closing(_connect(db_path)) as conn, conn:
        conn.execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))
