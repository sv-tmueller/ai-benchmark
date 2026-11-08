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

That totality extends to *coercing* caller-supplied values. ``str()``,
``repr()``, f-string interpolation and ``Path()`` conversion all run code the
caller owns -- a hostile ``__str__``/``__repr__``/``__fspath__`` may raise
anything, and stringifying a deeply nested container exhausts the recursion
limit -- so every such site is routed through the helpers below rather than
called directly. A type test can also be *lied to*: an object whose
``__class__`` is a property returning ``str`` passes ``isinstance(_, str)``
without being a str, and the flatten then raises ``TypeError``. Every coercion
that trusts a preceding type test is therefore guarded at the coercion site
itself, not just at the test.
"""

from __future__ import annotations

import json
import os
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

    ``result_path`` can still be a ``Path`` holding caller-owned string
    subclasses (``Path()`` accepts those), so ``.stem``/``.parent`` are coercions
    too: any raise degrades to an empty model id rather than escaping.
    """
    try:
        stem = _safe_str(result_path.stem)
        parent = _safe_str(result_path.parent.name)
    except Exception:
        return ""
    prefix = f"{parent}_"
    if stem.startswith(prefix):
        return stem[len(prefix):]
    return stem


def _normalize(value):
    if isinstance(value, float):
        return round(value, _ROUND_DECIMALS)
    return value


# ---------------------------------------------------------------------------
# Coercion helpers.
#
# Every value these helpers touch comes from the caller, so each one is total:
# ``str()``, ``repr()``, ``type(...).__name__``, ``bool()`` and ``Path()`` all
# execute methods the caller owns -- a hostile ``__str__``/``__repr__``/
# ``__fspath__`` may raise anything, an overridden ``__class__`` breaks
# ``isinstance``, and stringifying a deeply nested container exhausts the
# recursion limit. ``Exception`` (not ``BaseException``) is the boundary:
# ``SystemExit``/``KeyboardInterrupt`` are control flow, not malformed data.
# ---------------------------------------------------------------------------


def _is_mapping(value) -> bool:
    """``isinstance(value, dict)``, tolerating a hostile ``__class__``."""
    try:
        return isinstance(value, dict)
    except Exception:
        return False


def _is_str(value) -> bool:
    """``isinstance(value, str)``, tolerating a hostile ``__class__``."""
    try:
        return isinstance(value, str)
    except Exception:
        return False


def _as_exact_str(value) -> str:
    """Return a ``str`` (or subclass) as an exact ``str`` without running it.

    ``"".join`` reads the underlying character buffer, so a subclass's
    ``__str__``/``__repr__``/``__getitem__``/``__bool__`` never run -- which
    matters, because those are exactly the methods a hostile value overrides.
    """
    return "".join([value])


def _type_name(value) -> str:
    """Human-readable JSON-ish type name for a detail message; never raises."""
    try:
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
        # A hostile metaclass may return a str subclass from __name__; flatten.
        return _as_exact_str(type(value).__name__)
    except Exception:
        return "object"


def _safe_str(value) -> str:
    """A JSON-safe exact ``str`` for the verdict; never raises.

    A real ``str`` (or subclass) is flattened without running any override, so
    a caller's legitimate id/value survives. Anything else goes through
    ``str()`` -- whose result may itself be a ``str`` subclass -- and is then
    flattened too, since the verdict is interpolated and JSON-encoded.
    """
    try:
        if _is_str(value):
            return _as_exact_str(value)
        return _as_exact_str(str(value))
    except Exception:
        return f"<unstringable {_type_name(value)}>"


def _safe_repr(value) -> str:
    """``repr(value)`` as an exact ``str`` for a detail message; never raises.

    ``repr()`` is allowed to return a ``str`` subclass, which an f-string would
    then hand to that subclass's ``__format__``; flatten before returning.
    """
    try:
        return _as_exact_str(repr(value))
    except Exception:
        return f"<unreprable {_type_name(value)}>"


def _is_falsy(value) -> bool:
    """``not value``, treating a hostile ``__bool__`` as truthy."""
    try:
        return not value
    except Exception:
        return False


def _safe_get(mapping, key, default):
    """``mapping.get(key, default)``, tolerating a hostile ``get`` override."""
    try:
        return mapping.get(key, default)
    except Exception:
        return default


def _safe_eq(a, b) -> bool:
    """``a == b``; deep containers from the answer key may blow the stack.

    Equality recurses over nested values, so a key parsed at the very edge of
    the JSON recursion limit can still raise ``RecursionError`` here. Treat
    "cannot compare" as "not equal": both the match test and the diff then
    take the conservative pass:false path instead of raising.
    """
    try:
        return a == b
    except Exception:
        return False


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
    # Expected rows come from the caller's answer key, so both ``!=`` and the
    # ``!r`` interpolation below are coercions of caller data: a key nested to
    # the JSON recursion limit may not survive either. Route both through the
    # total helpers so the diff -- the last thing between grade() and its
    # verdict -- cannot raise.
    parts = [
        f"row mismatch: expected {len(expected_rows)} row(s), got {len(actual_rows)}"
    ]
    shown = 0
    for i in range(max(len(expected_rows), len(actual_rows))):
        exp = expected_rows[i] if i < len(expected_rows) else None
        act = actual_rows[i] if i < len(actual_rows) else None
        if not _safe_eq(exp, act):
            parts.append(
                f"  row {i}: expected {_safe_repr(exp)} got {_safe_repr(act)}"
            )
            shown += 1
            if shown >= _MAX_DIFF_ROWS:
                remaining = sum(
                    1
                    for j in range(i + 1, max(len(expected_rows), len(actual_rows)))
                    if not _safe_eq(
                        expected_rows[j] if j < len(expected_rows) else None,
                        actual_rows[j] if j < len(actual_rows) else None,
                    )
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
    # degrade to a verdict rather than a traceback. Every coercion of those
    # arguments goes through the helpers above, because ``isinstance``,
    # ``dict.get``, ``str()`` and ``Path()`` all run caller-owned code.
    if not _is_mapping(prompt):
        return _verdict(
            "",
            "",
            False,
            "prompt is not a mapping: expected the parsed prompt TOML, got "
            f"{_type_name(prompt)}",
        )
    # detail/prompt_id land in a JSON sidecar; keep them JSON-safe. _safe_str
    # reduces a str subclass to an exact str without running its overrides.
    prompt_id = _safe_str(_safe_get(prompt, "id", ""))

    if not _is_mapping(grading):
        return _verdict(
            prompt_id,
            "",
            False,
            "grading table is not a mapping: expected a dict of 'fixture' and "
            f"'answer_key', got {_type_name(grading)}",
        )

    # Deriving the model id reads the result path's name. A non-path-like value
    # must not raise from Path(); nor may a caller-supplied __fspath__ (which
    # Path() calls) or a str subclass Path() preserves internally raise later.
    try:
        result_path = Path(result_path)
    except Exception:
        return _verdict(
            prompt_id,
            "",
            False,
            f"result_path is not path-like: got {_type_name(result_path)}",
        )
    try:
        # os.fspath() reaches the path's own text; flattening it to an exact
        # str drops any caller-owned subclass before .stem/.parent/read_text().
        result_path = Path(_as_exact_str(os.fspath(result_path)))
    except Exception:
        return _verdict(
            prompt_id,
            "",
            False,
            f"result_path is not path-like: got {_type_name(result_path)}",
        )

    model = _model_from_filename(result_path)

    fixture_rel = _safe_get(grading, "fixture", None)
    key_rel = _safe_get(grading, "answer_key", None)
    if _is_falsy(fixture_rel) or _is_falsy(key_rel):
        return _verdict(
            prompt_id,
            model,
            False,
            "grading table is missing 'fixture' or 'answer_key'",
        )
    if not _is_str(fixture_rel):
        return _verdict(
            prompt_id,
            model,
            False,
            "fixture path in the grading table must be a string, got "
            f"{_type_name(fixture_rel)}: {_safe_repr(fixture_rel)}",
        )
    if not _is_str(key_rel):
        return _verdict(
            prompt_id,
            model,
            False,
            "answer key path in the grading table must be a string, got "
            f"{_type_name(key_rel)}: {_safe_repr(key_rel)}",
        )
    # Flatten before the join and the detail f-strings, so neither the path
    # arithmetic nor __format__ can run a hostile subclass method. These two
    # sites pass the _is_str test above, but that test can be *lied to*: a
    # caller object whose ``__class__`` is a property returning ``str`` makes
    # ``isinstance(value, str)`` true without being a str, and the flatten then
    # raises TypeError. Guard it here exactly as the sibling coercions are, so
    # the lie degrades to the same pass:false verdict as any other bad value.
    try:
        fixture_rel = _as_exact_str(fixture_rel)
    except Exception:
        return _verdict(
            prompt_id,
            model,
            False,
            "fixture path in the grading table could not be coerced to a "
            f"string: {_safe_repr(fixture_rel)}",
        )
    try:
        key_rel = _as_exact_str(key_rel)
    except Exception:
        return _verdict(
            prompt_id,
            model,
            False,
            "answer key path in the grading table could not be coerced to a "
            f"string: {_safe_repr(key_rel)}",
        )

    fixture_path = REPO_ROOT / fixture_rel
    key_path = REPO_ROOT / key_rel
    # Path.is_file() only swallows ENOENT/ENOTDIR/EBADF/ELOOP: a path with a
    # component longer than NAME_MAX (or a total longer than PATH_MAX) raises
    # OSError(ENAMETOOLONG) at the stat boundary. An over-long path is treated
    # exactly like the missing-file case -- a verdict, never a traceback.
    try:
        fixture_is_file = fixture_path.is_file()
    except OSError:
        fixture_is_file = False
    if not fixture_is_file:
        return _verdict(prompt_id, model, False, f"fixture file not found: {fixture_rel}")
    try:
        key_is_file = key_path.is_file()
    except OSError:
        key_is_file = False
    if not key_is_file:
        return _verdict(prompt_id, model, False, f"answer key file not found: {key_rel}")

    try:
        result_is_file = result_path.is_file()
    except OSError:
        result_is_file = False
    if not result_is_file:
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
    # RecursionError is a RuntimeError, not a JSONDecodeError/OSError, and
    # json.loads recurses once per nesting level: a pathologically deep key
    # (>= ~10_000 levels) must also degrade to a verdict, not blow the stack.
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
    except RecursionError as exc:
        return _verdict(
            prompt_id, model, False, f"answer key is nested too deeply to parse: {exc}"
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

    # Both sides are caller-derived (the key via json.loads, the actual rows
    # via sqlite); _safe_eq keeps the match test total for the same reason the
    # diff below uses it.
    if _safe_eq(actual_rows, expected_rows):
        return _verdict(prompt_id, model, True, f"{len(expected_rows)} row(s) match the answer key")

    return _verdict(prompt_id, model, False, _diff_detail(expected_rows, actual_rows))

