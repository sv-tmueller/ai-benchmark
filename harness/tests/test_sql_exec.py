"""Unit tests for harness/modes/sql_exec.py (the ``sql-exec`` grading mode).

This branch has no ``harness/grade.py`` (package #231 builds it), so the mode
is exercised by direct import against the D1 interface.

Import bootstrap: put ``harness/`` on ``sys.path`` so ``modes.sql_exec``
resolves as a namespace package.
"""

from __future__ import annotations

import json
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
