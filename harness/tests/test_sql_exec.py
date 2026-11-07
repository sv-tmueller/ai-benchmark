"""Unit tests for harness/modes/sql_exec.py (the ``sql-exec`` grading mode).

This branch has no ``harness/grade.py`` (package #231 builds it), so the mode
is exercised by direct import against the D1 interface.

Import bootstrap: put ``harness/`` on ``sys.path`` so ``modes.sql_exec``
resolves as a namespace package.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HARNESS_DIR.parent
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

from modes.sql_exec import grade  # noqa: E402

PROMPT_TOML = REPO_ROOT / "prompts" / "sql-country-analytics.toml"
FIXTURE = "harness/fixtures/sql_country_analytics/seed.sql"
ANSWER_KEY = "harness/fixtures/sql_country_analytics/expected_rows.json"

CORRECT_QUERY = """WITH country_metrics AS (
    SELECT c.country,
           SUM(o.total_amount) AS total_revenue,
           COUNT(*)            AS num_orders,
           AVG(o.total_amount) AS avg_order_value
    FROM orders o JOIN customers c ON c.id = o.customer_id
    GROUP BY c.country
),
product_revenue AS (
    SELECT c.country, i.product_name,
           SUM(i.quantity * i.unit_price) AS product_rev
    FROM order_items i JOIN orders o ON o.id = i.order_id
    JOIN customers c ON c.id = o.customer_id
    GROUP BY c.country, i.product_name
),
ranked AS (
    SELECT country, product_name,
           ROW_NUMBER() OVER (PARTITION BY country ORDER BY product_rev DESC, product_name ASC) AS rn
    FROM product_revenue
)
SELECT m.country, m.total_revenue, m.num_orders, m.avg_order_value,
       r.product_name AS top_product
FROM country_metrics m
LEFT JOIN ranked r ON r.country = m.country AND r.rn = 1
WHERE m.num_orders >= 10
ORDER BY m.total_revenue DESC;"""

# Executes cleanly and returns all five key columns, but the values are wrong
# (includes Spain, drops the >= 10 filter, mis-ranks top_product).
WRONG_ROWS_QUERY = """SELECT c.country,
       SUM(o.total_amount) AS total_revenue,
       COUNT(*)            AS num_orders,
       AVG(o.total_amount) AS avg_order_value,
       MIN(i.product_name) AS top_product
FROM orders o
JOIN customers c ON c.id = o.customer_id
JOIN order_items i ON i.order_id = o.id
GROUP BY c.country
ORDER BY total_revenue DESC;"""

SYNTAX_ERROR_QUERY = "SELECT FROM WHERE;"

NO_BLOCK_MARKDOWN = "I cannot answer that without more context."

# Statements that execute cleanly but return no result set (cur.description
# is None). Each must produce a verdict, never a TypeError.
NO_RESULT_SET_STATEMENTS = {
    "create_table": "CREATE TABLE scratch (id INTEGER);",
    "begin": "BEGIN;",
}

# Columns selected in a different order than the answer key.
REORDERED_COLUMNS_QUERY = """SELECT product_name AS top_product,
       country,
       num_orders,
       avg_order_value,
       total_revenue
FROM (
    SELECT m.country,
           m.total_revenue,
           m.num_orders,
           m.avg_order_value,
           r.product_name
    FROM (
        SELECT c.country,
               SUM(o.total_amount) AS total_revenue,
               COUNT(*)            AS num_orders,
               AVG(o.total_amount) AS avg_order_value
        FROM orders o JOIN customers c ON c.id = o.customer_id
        GROUP BY c.country
    ) m
    LEFT JOIN (
        SELECT country, product_name,
               ROW_NUMBER() OVER (
                   PARTITION BY country
                   ORDER BY SUM(quantity * unit_price) DESC, product_name ASC
               ) AS rn
        FROM order_items i
        JOIN orders o    ON o.id = i.order_id
        JOIN customers c ON c.id = o.customer_id
        GROUP BY country, product_name
    ) r ON r.country = m.country AND r.rn = 1
    WHERE m.num_orders >= 10
) ORDER BY total_revenue DESC;"""

# Same rows as CORRECT_QUERY, but avg_order_value derived as SUM/COUNT rather
# than AVG: the two computations must be accepted as equivalent.
SUM_OVER_COUNT_QUERY = """WITH country_metrics AS (
    SELECT c.country,
           SUM(o.total_amount)                          AS total_revenue,
           COUNT(*)                                     AS num_orders,
           SUM(o.total_amount) * 1.0 / COUNT(o.total_amount) AS avg_order_value
    FROM orders o JOIN customers c ON c.id = o.customer_id
    GROUP BY c.country
),
ranked AS (
    SELECT country, product_name,
           ROW_NUMBER() OVER (
               PARTITION BY country
               ORDER BY SUM(quantity * unit_price) DESC, product_name ASC
           ) AS rn
    FROM order_items i
    JOIN orders o    ON o.id = i.order_id
    JOIN customers c ON c.id = o.customer_id
    GROUP BY country, product_name
)
SELECT m.country, m.total_revenue, m.num_orders, m.avg_order_value,
       r.product_name AS top_product
FROM country_metrics m
LEFT JOIN ranked r ON r.country = m.country AND r.rn = 1
WHERE m.num_orders >= 10
ORDER BY m.total_revenue DESC;"""

# CORRECT_QUERY with a 1e-9 perturbation on avg_order_value: the raw float
# differs from the answer key, but it agrees after 6-decimal rounding, so it
# must still pass. Without the rounding step this would be a row mismatch.
SUB_SIX_DECIMAL_PERTURBATION_QUERY = (
    SUM_OVER_COUNT_QUERY.replace(
        "SUM(o.total_amount) * 1.0 / COUNT(o.total_amount) AS avg_order_value",
        "AVG(o.total_amount) + 1e-9 AS avg_order_value",
    )
)

RESULT_REL = "results/sql-country-analytics/sql-country-analytics_glm_5_3_flash.md"
SIDECAR_REL = (
    "results/sql-country-analytics/"
    "sql-country-analytics_glm_5_3_flash_grading.json"
)


def _prompt() -> dict:
    with PROMPT_TOML.open("rb") as fh:
        return tomllib.load(fh)


def _grading() -> dict:
    return {"mode": "sql-exec", "fixture": FIXTURE, "answer_key": ANSWER_KEY}


class SqlExecModeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def _write_result(self, body: str, *, filename: str = "sql-country-analytics_glm_5_3_flash.md") -> Path:
        d = self.tmp / "sql-country-analytics"
        d.mkdir(exist_ok=True)
        p = d / filename
        p.write_text(body, encoding="utf-8")
        return p

    def _markdown(self, query: str) -> str:
        return f"Here is my answer.\n\n```sql\n{query}\n```\n\nSome notes.\n"

    # --- contract shape ---------------------------------------------------

    def test_returns_exactly_the_five_contract_keys(self):
        result = grade(self._write_result(self._markdown(CORRECT_QUERY)), _grading(), _prompt())
        self.assertEqual(
            set(result.keys()),
            {"prompt_id", "model", "mode", "pass", "detail"},
        )

    def test_prompt_id_comes_from_prompt_toml_not_filename(self):
        # Filename prefix is the directory name, not the prompt id.
        result = grade(self._write_result(self._markdown(CORRECT_QUERY)), _grading(), _prompt())
        self.assertEqual(result["prompt_id"], "sql-write-query")

    def test_model_is_stem_remainder_after_directory_name(self):
        result = grade(self._write_result(self._markdown(CORRECT_QUERY)), _grading(), _prompt())
        self.assertEqual(result["model"], "glm_5_3_flash")

    def test_mode_value_is_sql_exec(self):
        result = grade(self._write_result(self._markdown(CORRECT_QUERY)), _grading(), _prompt())
        self.assertEqual(result["mode"], "sql-exec")

    # --- acceptance criteria ---------------------------------------------

    def test_correct_query_passes(self):
        result = grade(self._write_result(self._markdown(CORRECT_QUERY)), _grading(), _prompt())
        self.assertTrue(result["pass"], result["detail"])

    def test_canonical_query_matches_committed_answer_key(self):
        # Explicitly cross-check the mode's comparison against the JSON key.
        key = json.loads((REPO_ROOT / ANSWER_KEY).read_text(encoding="utf-8"))
        result = grade(self._write_result(self._markdown(CORRECT_QUERY)), _grading(), _prompt())
        self.assertTrue(result["pass"])
        self.assertEqual(len(key), 2)

    def test_wrong_rows_fail_with_row_diff_in_detail(self):
        result = grade(self._write_result(self._markdown(WRONG_ROWS_QUERY)), _grading(), _prompt())
        self.assertFalse(result["pass"])
        self.assertIn("Germany", result["detail"])  # expected row shown in diff

    def test_query_error_fails_with_db_error_not_crash(self):
        result = grade(self._write_result(self._markdown(SYNTAX_ERROR_QUERY)), _grading(), _prompt())
        self.assertFalse(result["pass"])
        self.assertTrue(result["detail"].strip())

    def test_missing_sql_block_fails_without_crash(self):
        result = grade(self._write_result(NO_BLOCK_MARKDOWN), _grading(), _prompt())
        self.assertFalse(result["pass"])
        self.assertIn("no SQL code block", result["detail"])

    # --- extraction -------------------------------------------------------

    def test_extracts_first_sql_block_only(self):
        body = (
            "```sql\nSELECT 1 AS n;\n```\n\nand later\n\n"
            "```sql\nSELECT 999;\n```\n"
        )
        result = grade(self._write_result(body), _grading(), _prompt())
        # Single-column result cannot match the five-column key -> fails, but
        # it must fail on row mismatch, not because two blocks confused it.
        self.assertFalse(result["pass"])

    def test_trailing_semicolon_is_accepted(self):
        self.assertTrue(CORRECT_QUERY.rstrip().endswith(";"))
        result = grade(self._write_result(self._markdown(CORRECT_QUERY)), _grading(), _prompt())
        self.assertTrue(result["pass"])

    # --- no-result-set statements (round-1 finding 1) ----------------------

    def _assert_no_result_set_verdict(self, body: str):
        result = grade(self._write_result(body), _grading(), _prompt())
        self.assertEqual(
            set(result.keys()),
            {"prompt_id", "model", "mode", "pass", "detail"},
        )
        self.assertFalse(result["pass"])
        self.assertIn("no result set", result["detail"].lower())

    def test_empty_sql_fence_is_a_verdict_not_a_crash(self):
        self._assert_no_result_set_verdict("Answer.\n\n```sql\n```\n")

    def test_whitespace_only_sql_fence_is_a_verdict_not_a_crash(self):
        self._assert_no_result_set_verdict("Answer.\n\n```sql\n   \n\t\n```\n")

    def test_comment_only_sql_fence_is_a_verdict_not_a_crash(self):
        self._assert_no_result_set_verdict("Answer.\n\n```sql\n-- nothing here\n```\n")

    def test_non_select_statement_is_a_verdict_not_a_crash(self):
        self._assert_no_result_set_verdict(
            self._markdown(NO_RESULT_SET_STATEMENTS["create_table"])
        )

    def test_begin_statement_is_a_verdict_not_a_crash(self):
        self._assert_no_result_set_verdict(self._markdown(NO_RESULT_SET_STATEMENTS["begin"]))

    # --- missing result file (round-1 finding 2) --------------------------

    def test_missing_result_file_is_a_verdict_naming_the_file(self):
        missing = self.tmp / "sql-country-analytics" / "does-not-exist.md"
        result = grade(missing, _grading(), _prompt())
        self.assertFalse(result["pass"])
        self.assertIn("does-not-exist.md", result["detail"])
        self.assertIn("not found", result["detail"].lower())

    # --- rounding and column-order equivalence ----------------------------

    def test_sum_over_count_derivation_is_accepted(self):
        # An alternative correct derivation of avg_order_value (SUM/COUNT
        # instead of AVG) must be accepted as equivalent to the answer key.
        result = grade(
            self._write_result(self._markdown(SUM_OVER_COUNT_QUERY)), _grading(), _prompt()
        )
        self.assertTrue(result["pass"], result["detail"])

    def test_six_decimal_rounding_absorbs_last_bit_difference(self):
        # avg_order_value differs from the answer key by 1e-9 as a raw float,
        # so this is green only because the mode rounds to 6 decimals first.
        self.assertIn("+ 1e-9", SUB_SIX_DECIMAL_PERTURBATION_QUERY)
        self.assertNotEqual(
            SUB_SIX_DECIMAL_PERTURBATION_QUERY, SUM_OVER_COUNT_QUERY
        )
        result = grade(
            self._write_result(self._markdown(SUB_SIX_DECIMAL_PERTURBATION_QUERY)),
            _grading(),
            _prompt(),
        )
        self.assertTrue(result["pass"], result["detail"])

    def test_reordered_columns_compare_by_name(self):
        # Confirm the query really returns the key columns in a different order,
        # so green here means the mode reordered by name, not by position.
        seed = (REPO_ROOT / "harness/fixtures/sql_country_analytics/seed.sql").read_text(
            encoding="utf-8"
        )
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.executescript(seed)
        returned = [
            d[0] for d in conn.execute(REORDERED_COLUMNS_QUERY).description
        ]
        key = json.loads((REPO_ROOT / ANSWER_KEY).read_text(encoding="utf-8"))
        key_columns = list(key[0].keys())
        self.assertEqual(sorted(returned), sorted(key_columns))
        self.assertNotEqual(returned, key_columns)

        result = grade(
            self._write_result(self._markdown(REORDERED_COLUMNS_QUERY)), _grading(), _prompt()
        )
        self.assertTrue(result["pass"], result["detail"])


class IoAndParseBoundaryTests(unittest.TestCase):
    """Every I/O and parse boundary is a verdict, never a crash (round-2 findings).

    The ``every failure mode is a verdict`` contract needs a guard at the file
    decode, the answer-key JSON parse, and the fixture load — not only around
    the query execution.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.results_dir = self.tmp / "sql-country-analytics"
        self.results_dir.mkdir()

    def _result_bytes(self, payload: bytes) -> Path:
        p = self.results_dir / "sql-country-analytics_glm_5_3_flash.md"
        p.write_bytes(payload)
        return p

    def _good_markdown_result(self) -> Path:
        body = f"Here is my answer.\n\n```sql\n{CORRECT_QUERY}\n```\n".encode()
        return self._result_bytes(body)

    def _grading(self, *, fixture: str = FIXTURE, answer_key: str = ANSWER_KEY) -> dict:
        return {"mode": "sql-exec", "fixture": fixture, "answer_key": answer_key}

    def test_non_utf8_result_file_is_a_verdict_not_a_crash(self):
        # Round-2 finding 1: invalid bytes in a model deliverable must yield a
        # pass:false verdict naming the decode error, not UnicodeDecodeError.
        path = self._result_bytes(b"Answer.\n\n```sql\nSELECT 1;\n```\n\xff\xfe bad\n")
        self.assertRaises(UnicodeDecodeError, path.read_text, "utf-8")
        result = grade(path, self._grading(), _prompt())
        self.assertEqual(
            set(result.keys()),
            {"prompt_id", "model", "mode", "pass", "detail"},
        )
        self.assertFalse(result["pass"])
        self.assertIn("decode", result["detail"].lower())

    def test_malformed_answer_key_is_a_verdict_not_a_crash(self):
        # Round-2 finding 2: unparseable JSON must yield a pass:false verdict
        # carrying the parse error, not a JSONDecodeError traceback.
        bad_key = self.tmp / "expected_rows_bad.json"
        bad_key.write_text('{"unterminated": ', encoding="utf-8")
        result = grade(
            self._good_markdown_result(),
            self._grading(answer_key=str(bad_key)),
            _prompt(),
        )
        self.assertEqual(
            set(result.keys()),
            {"prompt_id", "model", "mode", "pass", "detail"},
        )
        self.assertFalse(result["pass"])
        self.assertIn("answer key", result["detail"].lower())
        self.assertIn("json", result["detail"].lower())

    def test_truncated_answer_key_is_a_verdict_not_a_crash(self):
        # Second malformed-JSON shape: syntactically truncated array.
        bad_key = self.tmp / "expected_rows_truncated.json"
        bad_key.write_text('[{"country": "Germany",', encoding="utf-8")
        result = grade(
            self._good_markdown_result(),
            self._grading(answer_key=str(bad_key)),
            _prompt(),
        )
        self.assertFalse(result["pass"])
        self.assertIn("answer key", result["detail"].lower())

    def test_malformed_fixture_is_a_verdict_not_a_crash(self):
        # Round-2 finding 3: a garbage SQL fixture must yield a pass:false
        # verdict carrying the DB error, not OperationalError from executescript.
        bad_fixture = self.tmp / "seed_bad.sql"
        bad_fixture.write_text("THIS IS NOT VALID SQL;", encoding="utf-8")
        result = grade(
            self._good_markdown_result(),
            self._grading(fixture=str(bad_fixture)),
            _prompt(),
        )
        self.assertEqual(
            set(result.keys()),
            {"prompt_id", "model", "mode", "pass", "detail"},
        )
        self.assertFalse(result["pass"])
        self.assertIn("fixture", result["detail"].lower())

    def test_non_utf8_fixture_is_a_verdict_not_a_crash(self):
        # A fixture file with invalid bytes cannot be decoded into SQL text.
        bad_fixture = self.tmp / "seed_nonutf8.sql"
        bad_fixture.write_bytes(b"CREATE TABLE t (id INTEGER);\n\xff\xfe\n")
        result = grade(
            self._good_markdown_result(),
            self._grading(fixture=str(bad_fixture)),
            _prompt(),
        )
        self.assertFalse(result["pass"])
        self.assertIn("fixture", result["detail"].lower())

    def test_non_utf8_answer_key_is_a_verdict_not_a_crash(self):
        bad_key = self.tmp / "expected_rows_nonutf8.json"
        bad_key.write_bytes(b'[{"country": "Germany"}\xff\xfe]')
        result = grade(
            self._good_markdown_result(),
            self._grading(answer_key=str(bad_key)),
            _prompt(),
        )
        self.assertFalse(result["pass"])
        self.assertIn("answer key", result["detail"].lower())


class ShapeBoundaryTests(unittest.TestCase):
    """Round-3 findings 1-2: wrong-shaped JSON keys and non-string grading values.

    A parse boundary has two stages: decode/parse the text, then validate the
    *shape* of what was parsed. Round 2 guarded the first (JSONDecodeError);
    these tests pin the second. The contract is total: no input to this mode,
    however malformed, may raise.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.results_dir = self.tmp / "sql-country-analytics"
        self.results_dir.mkdir()

    def _good_result(self) -> Path:
        p = self.results_dir / "sql-country-analytics_glm_5_3_flash.md"
        p.write_text(f"Here is my answer.\n\n```sql\n{CORRECT_QUERY}\n```\n", encoding="utf-8")
        return p

    def _write_json_key(self, obj, name: str) -> str:
        p = self.tmp / name
        p.write_text(json.dumps(obj), encoding="utf-8")
        return str(p)

    def _grading(self, *, fixture=FIXTURE, answer_key=ANSWER_KEY) -> dict:
        return {"mode": "sql-exec", "fixture": fixture, "answer_key": answer_key}

    def _assert_verdict_shape(self, result: dict):
        self.assertEqual(
            set(result.keys()),
            {"prompt_id", "model", "mode", "pass", "detail"},
        )
        self.assertFalse(result["pass"])

    # --- finding 1: syntactically valid but wrong-SHAPED answer key -------

    def _assert_wrong_shape_is_a_verdict(self, label: str, key_obj):
        key_path = self._write_json_key(key_obj, f"key_{label}.json")
        result = grade(
            self._good_result(),
            self._grading(answer_key=key_path),
            _prompt(),
        )
        self._assert_verdict_shape(result)
        self.assertIn("answer key", result["detail"].lower())
        self.assertIn("shape", result["detail"].lower())

    def test_list_of_lists_answer_key_is_a_verdict_not_a_crash(self):
        self._assert_wrong_shape_is_a_verdict("list_of_lists", [[1, 2, 3]])

    def test_bare_dict_answer_key_is_a_verdict_not_a_crash(self):
        self._assert_wrong_shape_is_a_verdict("bare_dict", {"country": "Germany"})

    def test_scalar_string_answer_key_is_a_verdict_not_a_crash(self):
        self._assert_wrong_shape_is_a_verdict("scalar_string", "not a key")

    def test_scalar_number_answer_key_is_a_verdict_not_a_crash(self):
        self._assert_wrong_shape_is_a_verdict("scalar_number", 42)

    def test_numeric_row_answer_key_is_a_verdict_not_a_crash(self):
        # A flat numeric list (a "row" of values, not objects).
        self._assert_wrong_shape_is_a_verdict("numeric_row", [1, 2, 3])

    def test_mixed_list_answer_key_is_a_verdict_not_a_crash(self):
        self._assert_wrong_shape_is_a_verdict("mixed_list", [{"c": 1}, 5])

    def test_bool_answer_key_is_a_verdict_not_a_crash(self):
        self._assert_wrong_shape_is_a_verdict("bool", True)

    def test_list_of_strings_answer_key_is_a_verdict_not_a_crash(self):
        self._assert_wrong_shape_is_a_verdict("list_of_strings", ["a", "b"])

    def test_null_answer_key_is_a_verdict_not_a_crash(self):
        self._assert_wrong_shape_is_a_verdict("null", None)

    # --- finding 2: non-string fixture / answer_key grading values --------

    def test_non_string_fixture_is_a_verdict_not_a_crash(self):
        result = grade(
            self._good_result(),
            self._grading(fixture=42),
            _prompt(),
        )
        self._assert_verdict_shape(result)
        self.assertIn("string", result["detail"].lower())
        self.assertIn("fixture", result["detail"].lower())

    def test_non_string_fixture_list_is_a_verdict_not_a_crash(self):
        result = grade(
            self._good_result(),
            self._grading(fixture=["a.sql"]),
            _prompt(),
        )
        self._assert_verdict_shape(result)
        self.assertIn("string", result["detail"].lower())

    def test_non_string_answer_key_is_a_verdict_not_a_crash(self):
        result = grade(
            self._good_result(),
            self._grading(answer_key=7),
            _prompt(),
        )
        self._assert_verdict_shape(result)
        self.assertIn("string", result["detail"].lower())
        self.assertIn("answer key", result["detail"].lower())

    def test_non_string_answer_key_list_is_a_verdict_not_a_crash(self):
        result = grade(
            self._good_result(),
            self._grading(answer_key=["key.json"]),
            _prompt(),
        )
        self._assert_verdict_shape(result)
        self.assertIn("string", result["detail"].lower())

    # --- other uncontrolled-shape data on this path -----------------------

    def test_fixture_with_nul_byte_is_a_verdict_not_a_crash(self):
        # sqlite3 raises ValueError (not sqlite3.Error) for NUL bytes, so the
        # executescript guard alone does not cover it.
        bad = self.tmp / "nul_seed.sql"
        bad.write_bytes(b"CREATE TABLE t (id INTEGER);\x00\n")
        result = grade(
            self._good_result(),
            self._grading(fixture=str(bad)),
            _prompt(),
        )
        self._assert_verdict_shape(result)
        self.assertIn("fixture", result["detail"].lower())

    def test_key_with_nul_byte_is_a_verdict_not_a_crash(self):
        bad = self.tmp / "nul_key.json"
        bad.write_bytes(b'[{"country": "Germany"}\x00]')
        result = grade(
            self._good_result(),
            self._grading(answer_key=str(bad)),
            _prompt(),
        )
        self._assert_verdict_shape(result)
        self.assertIn("answer key", result["detail"].lower())

    def test_non_dict_grading_argument_is_a_verdict_not_a_crash(self):
        for label, grading in [
            ("none", None),
            ("list", []),
            ("scalar", 42),
            ("string", "fixture"),
        ]:
            with self.subTest(grading=label):
                result = grade(self._good_result(), grading, _prompt())
                self._assert_verdict_shape(result)
                self.assertIn("grading", result["detail"].lower())

    def test_non_dict_prompt_argument_is_a_verdict_not_a_crash(self):
        result = grade(self._good_result(), self._grading(), None)
        self._assert_verdict_shape(result)
        self.assertIn("prompt", result["detail"].lower())

    def test_non_pathlike_result_path_is_a_verdict_not_a_crash(self):
        result = grade(42, self._grading(), _prompt())
        self._assert_verdict_shape(result)

    def test_non_string_prompt_id_is_a_verdict_not_a_crash(self):
        # prompt_id only ever lands in the verdict dict; a non-string must not
        # break the contract of returning the five keys.
        result = grade(self._good_result(), self._grading(), {"id": 123})
        self.assertEqual(
            set(result.keys()),
            {"prompt_id", "model", "mode", "pass", "detail"},
        )


class SidecarFidelityTests(unittest.TestCase):
    """The committed sidecar must be reproducible from the committed inputs."""

    def test_committed_sidecar_matches_fresh_grade(self):
        result_path = REPO_ROOT / RESULT_REL
        sidecar_path = REPO_ROOT / SIDECAR_REL
        self.assertTrue(result_path.is_file(), result_path)
        self.assertTrue(sidecar_path.is_file(), sidecar_path)

        committed = json.loads(sidecar_path.read_text(encoding="utf-8"))

        with PROMPT_TOML.open("rb") as fh:
            prompt = tomllib.load(fh)
        regenerated = grade(result_path, prompt["grading"], prompt)

        self.assertEqual(regenerated, committed)


class FixtureVerificationTests(unittest.TestCase):
    def test_committed_answer_key_matches_canonical_query(self):
        # Acceptance criterion 1 as a unit test: the committed key is
        # reproducible from the committed seed.
        import importlib.util

        verify_path = REPO_ROOT / "harness" / "fixtures" / "sql_country_analytics" / "verify_fixture.py"
        spec = importlib.util.spec_from_file_location("verify_fixture", verify_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        expected = json.loads((REPO_ROOT / ANSWER_KEY).read_text(encoding="utf-8"))
        conn = module.build_connection()
        actual = module.canonical_rows(conn)
        normalized = [{k: (round(v, 6) if isinstance(v, float) else v) for k, v in row.items()} for row in expected]
        self.assertEqual(actual, normalized)


if __name__ == "__main__":
    unittest.main()
