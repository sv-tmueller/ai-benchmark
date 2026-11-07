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

Every failure mode is a verdict, not a crash: a missing result file, a result
file that is not valid UTF-8, a missing SQL block, an empty (or no-result-set)
SQL block, a SQL error, a malformed (or non-UTF-8) fixture, a malformed (or
non-UTF-8, or wrong-shaped) answer key, a non-string ``fixture``/``answer_key``
grading value, a non-mapping ``grading``/``prompt`` argument, a non-path-like
``result_path``, or a row mismatch all return ``pass: false`` with an
explanatory ``detail``. No input to this mode, however malformed, raises: each
I/O, parse, and shape boundary is guarded, not only the query execution.
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


def _verdict(prompt_id: str, model: str, passed: bool, detail: str) -> dict:
    """Build the D1 verdict dict; the single place its shape is defined."""
    return {
        "prompt_id": prompt_id,
        "model": model,
        "mode": MODE,
        "pass": passed,
        "detail": detail,
    }


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


def _type_name(value) -> str:
    """Human-readable JSON-ish type name for a detail message."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _answer_key_shape_error(parsed) -> str | None:
    """Return a detail string if ``parsed`` is not a list of flat objects.

    The answer key must decode to a list whose every element is a JSON object
    (``{column: value}``). Anything else -- a bare dict, a scalar, a list of
    lists, a numeric row, a mixed list such as ``[{"c": 1}, 5]`` -- must be a
    verdict, never an ``AttributeError``/``KeyError``/``TypeError``.
    """
    if not isinstance(parsed, list):
        return (
            "answer key has the wrong shape: expected a JSON list of objects "
            f"keyed by column name, got {_type_name(parsed)}"
        )
    for i, row in enumerate(parsed):
        if not isinstance(row, dict):
            return (
                "answer key has the wrong shape: expected every element to be "
                f"an object keyed by column name, but row {i} is "
                f"{_type_name(row)}"
            )
        for key in row:
            if not isinstance(key, str):
                return (
                    "answer key has the wrong shape: expected every column "
                    f"name to be a string, but row {i} has key of type "
                    f"{_type_name(key)}"
                )
    return None


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
    """Grade ``result_path`` against the fixture DB named by ``grading``.

    Returns the five contract keys for every input, valid or not; this
    function never raises.
    """

    # The arguments themselves are outside this mode's control: the runner
    # passes whatever the prompt TOML (or a caller) produced, and each must
    # degrade to a verdict rather than a traceback.
    if not isinstance(prompt, dict):
        return _verdict(
            "",
            "",
            False,
            "prompt is not a mapping: expected the parsed prompt TOML, got "
            f"{_type_name(prompt)}",
        )
    prompt_id = prompt.get("id", "")
    if not isinstance(prompt_id, str):
        # detail/prompt_id land in a JSON sidecar; keep them JSON-safe.
        prompt_id = str(prompt_id)

    if not isinstance(grading, dict):
        return _verdict(
            prompt_id,
            "",
            False,
            "grading table is not a mapping: expected a dict of 'fixture' and "
            f"'answer_key', got {_type_name(grading)}",
        )

    # Deriving the model id reads the result path's name; a non-path-like
    # value must not raise from Path()/`.stem`.
    try:
        result_path = Path(result_path)
    except TypeError:
        return _verdict(
            prompt_id,
            "",
            False,
            f"result_path is not path-like: got {_type_name(result_path)}",
        )

    model = _model_from_filename(result_path)

    fixture_rel = grading.get("fixture")
    key_rel = grading.get("answer_key")
    if not fixture_rel or not key_rel:
        return _verdict(
            prompt_id,
            model,
            False,
            "grading table is missing 'fixture' or 'answer_key'",
        )
    if not isinstance(fixture_rel, str):
        return _verdict(
            prompt_id,
            model,
            False,
            "fixture path in the grading table must be a string, got "
            f"{_type_name(fixture_rel)}: {fixture_rel!r}",
        )
    if not isinstance(key_rel, str):
        return _verdict(
            prompt_id,
            model,
            False,
            "answer key path in the grading table must be a string, got "
            f"{_type_name(key_rel)}: {key_rel!r}",
        )

    fixture_path = REPO_ROOT / fixture_rel
    key_path = REPO_ROOT / key_rel
    if not fixture_path.is_file():
        return _verdict(prompt_id, model, False, f"fixture file not found: {fixture_rel}")
    if not key_path.is_file():
        return _verdict(prompt_id, model, False, f"answer key file not found: {key_rel}")

    if not result_path.is_file():
        return _verdict(prompt_id, model, False, f"result file not found: {result_path}")

    # Decoding a model deliverable is an I/O boundary: invalid bytes must be a
    # verdict, not a UnicodeDecodeError escaping the runner.
    try:
        result_text = result_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return _verdict(
            prompt_id, model, False, f"result file could not be decoded as UTF-8: {exc}"
        )

    query = _extract_query(result_text)
    if query is None:
        return _verdict(prompt_id, model, False, "no SQL code block found")

    # Parsing the answer key is a parse boundary: a malformed or non-UTF-8 key
    # must be a verdict carrying the parse error, never a JSONDecodeError.
    try:
        expected_raw = json.loads(key_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, OSError) as exc:
        return _verdict(
            prompt_id, model, False, f"answer key could not be decoded as UTF-8: {exc}"
        )
    except json.JSONDecodeError as exc:
        return _verdict(
            prompt_id, model, False, f"answer key is not valid JSON: {exc}"
        )

    # A parse boundary has two stages: decode/parse the text (above), then
    # validate the *shape* of what was parsed. ``expected_raw[0].keys()`` and
    # ``row.items()`` below assume a list of flat objects; anything else must
    # be rejected here, never surfacing as AttributeError/KeyError/TypeError.
    shape_error = _answer_key_shape_error(expected_raw)
    if shape_error is not None:
        return _verdict(prompt_id, model, False, shape_error)

    key_columns = list(expected_raw[0].keys()) if expected_raw else []
    expected_rows = [
        {k: _normalize(v) for k, v in row.items()} for row in expected_raw
    ]

    # Loading the fixture is a parse boundary too: a malformed (or non-UTF-8)
    # seed must be a verdict carrying the DB error, not an OperationalError
    # from executescript escaping the runner. sqlite3 raises ValueError (not
    # sqlite3.Error) for an embedded NUL, so that class is guarded as well.
    try:
        fixture_sql = fixture_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return _verdict(
            prompt_id, model, False, f"fixture file could not be decoded as UTF-8: {exc}"
        )

    conn = sqlite3.connect(":memory:")
    try:
        try:
            conn.executescript(fixture_sql)
        except (sqlite3.Error, ValueError) as exc:
            return _verdict(prompt_id, model, False, f"fixture SQL error: {exc}")
        try:
            cur = conn.execute(query)
            actual_raw = cur.fetchall()
            if cur.description is None:
                # Statement executed but produced no result set (empty fence,
                # comment-only fence, INSERT/CREATE/BEGIN/UPDATE, ...).
                return _verdict(
                    prompt_id, model, False, "statement returned no result set"
                )
            actual_columns = [d[0] for d in cur.description]
        except (sqlite3.Error, ValueError) as exc:
            return _verdict(prompt_id, model, False, f"SQL error: {exc}")
    finally:
        conn.close()

    # Compare by column name: reorder the actual columns to the key's order.
    missing = [c for c in key_columns if c not in actual_columns]
    if missing:
        return _verdict(
            prompt_id,
            model,
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
        return _verdict(prompt_id, model, True, f"{len(expected_rows)} row(s) match the answer key")

    return _verdict(prompt_id, model, False, _diff_detail(expected_rows, actual_rows))

