"""``sql-exec`` grading mode: run a model-written SQL query against a fixture DB.

Batch contract (D1): ``grade(result_path, grading, prompt) -> dict`` returning
exactly ``{"prompt_id", "model", "mode", "pass", "detail"}``.

Discovery in this mode's prompt TOML::

    [grading]
    mode       = "sql-exec"
    fixture    = "harness/fixtures/sql_country_analytics/seed.sql"
    answer_key = "harness/fixtures/sql_country_analytics/expected_rows.json"

``fixture`` and ``answer_key`` are repo-root-relative. The mode builds a fresh
``:memory:`` SQLite database from the text fixture on every call (no binary DB
in git, no cross-call state), extracts the first ```` ```sql ```` fenced block
from the Markdown deliverable, executes it once, and compares the returned rows
against the answer key by column name.

Every failure mode is a verdict, not a crash: a missing SQL block, a SQL error,
or a row mismatch all return ``pass: false`` with an explanatory ``detail``.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

# Repo root: this file is harness/modes/sql_exec.py -> parents[2].
REPO_ROOT = Path(__file__).resolve().parents[2]

MODE = "sql-exec"

# First ```sql ... ``` fenced block; fence case-insensitive, CRLF-tolerant.
_SQL_BLOCK_RE = re.compile(r"```sql[ \t]*\r?\n(.*?)```", re.IGNORECASE | re.DOTALL)

# avg_order_value is REAL; AVG vs SUM/COUNT can differ in the last bits.
_ROUND_DECIMALS = 6

# How many differing rows to show in the detail string.
_MAX_DIFF_ROWS = 5


def _extract_query(text: str) -> str | None:
    """Return the first ```` ```sql ```` block's body, or None if absent."""
    match = _SQL_BLOCK_RE.search(text)
    if match is None:
        return None
    return match.group(1).strip()


def _model_from_filename(result_path: Path) -> str:
    """Model id = filename stem remainder after ``<dirname>_``.

    The result files are named ``<family>_<model>.<ext>`` where the numeric
    prefix is the prompt *family* directory, not the prompt id (see sub-plan
    point 2), so ``sql-country-analytics_glm_5_3_flash.md`` -> ``glm_5_3_flash``.
    """
    stem = result_path.stem
    parent = result_path.parent.name
    prefix = f"{parent}_"
    if stem.startswith(prefix):
        return stem[len(prefix):]
    return stem


def _normalize(value):
    if isinstance(value, float):
        return round(value, _ROUND_DECIMALS)
    return value


def _row_as_dict(cols, row) -> dict:
    return {name: _normalize(row[i]) for i, name in enumerate(cols)}


def _format_row(row: dict) -> str:
    return "{" + ", ".join(f"{k}={row[k]!r}" for k in row) + "}"


def _diff_detail(expected_rows, actual_rows) -> str:
    parts = [
        f"row mismatch: expected {len(expected_rows)} row(s), got {len(actual_rows)}"
    ]
    shown = 0
    for i in range(max(len(expected_rows), len(actual_rows))):
        exp = expected_rows[i] if i < len(expected_rows) else None
        act = actual_rows[i] if i < len(actual_rows) else None
        if exp != act:
            parts.append(f"  row {i}: expected {exp!r} got {act!r}")
            shown += 1
            if shown >= _MAX_DIFF_ROWS:
                remaining = sum(
                    1
                    for j in range(i + 1, max(len(expected_rows), len(actual_rows)))
                    if (expected_rows[j] if j < len(expected_rows) else None)
                    != (actual_rows[j] if j < len(actual_rows) else None)
                )
                if remaining:
                    parts.append(f"  ... and {remaining} more differing row(s)")
                break
    return "\n".join(parts)


def grade(result_path: Path, grading: dict, prompt: dict) -> dict:
    result_path = Path(result_path)
    prompt_id = prompt.get("id", "")
    model = _model_from_filename(result_path)

    def verdict(passed: bool, detail: str) -> dict:
        return {
            "prompt_id": prompt_id,
            "model": model,
            "mode": MODE,
            "pass": passed,
            "detail": detail,
        }

    fixture_rel = grading.get("fixture")
    key_rel = grading.get("answer_key")
    if not fixture_rel or not key_rel:
        return verdict(False, "grading table is missing 'fixture' or 'answer_key'")

    fixture_path = REPO_ROOT / fixture_rel
    key_path = REPO_ROOT / key_rel
    if not fixture_path.is_file():
        return verdict(False, f"fixture file not found: {fixture_rel}")
    if not key_path.is_file():
        return verdict(False, f"answer key file not found: {key_rel}")

    query = _extract_query(result_path.read_text(encoding="utf-8"))
    if query is None:
        return verdict(False, "no SQL code block found")

    expected_raw = json.loads(key_path.read_text(encoding="utf-8"))
    key_columns = list(expected_raw[0].keys()) if expected_raw else []
    expected_rows = [
        {k: _normalize(v) for k, v in row.items()} for row in expected_raw
    ]

    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(fixture_path.read_text(encoding="utf-8"))
        try:
            cur = conn.execute(query)
            actual_raw = cur.fetchall()
            actual_columns = [d[0] for d in cur.description]
        except sqlite3.Error as exc:
            return verdict(False, f"SQL error: {exc}")
    finally:
        conn.close()

    # Compare by column name: reorder the actual columns to the key's order.
    missing = [c for c in key_columns if c not in actual_columns]
    if missing:
        return verdict(
            False,
            "result columns do not match the answer key: missing "
            + ", ".join(missing)
            + f" (got: {', '.join(actual_columns)})",
        )
    index_of = {name: i for i, name in enumerate(actual_columns)}
    actual_rows = [
        {col: _normalize(row[index_of[col]]) for col in key_columns}
        for row in actual_raw
    ]

    if actual_rows == expected_rows:
        return verdict(True, f"{len(expected_rows)} row(s) match the answer key")

    return verdict(False, _diff_detail(expected_rows, actual_rows))
