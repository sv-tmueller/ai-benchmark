#!/usr/bin/env python3
"""Verify the sql-country-analytics fixture against its recorded answer key.

Builds an in-memory SQLite DB from ``seed.sql``, runs the canonical reference
query, and asserts the result matches ``expected_rows.json`` exactly. This is
the bidirectional check behind acceptance criterion 1: the committed key is
reproducible from the committed seed.

Usage:
    python harness/fixtures/sql_country_analytics/verify_fixture.py

Exit code 0 when the key matches, 1 otherwise. Stdlib only.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = HERE / "seed.sql"
KEY = HERE / "expected_rows.json"

# Canonical reference query: the prompt's stated output columns and filters,
# with ties (none in this seed) broken deterministically.
CANONICAL_QUERY = """
WITH country_metrics AS (
    SELECT c.country,
           SUM(o.total_amount) AS total_revenue,
           COUNT(*)            AS num_orders,
           AVG(o.total_amount) AS avg_order_value
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    GROUP BY c.country
),
product_revenue AS (
    SELECT c.country,
           i.product_name,
           SUM(i.quantity * i.unit_price) AS product_rev
    FROM order_items i
    JOIN orders o    ON o.id = i.order_id
    JOIN customers c ON c.id = o.customer_id
    GROUP BY c.country, i.product_name
),
ranked AS (
    SELECT country, product_name,
           ROW_NUMBER() OVER (
               PARTITION BY country
               ORDER BY product_rev DESC, product_name ASC
           ) AS rn
    FROM product_revenue
)
SELECT m.country,
       m.total_revenue,
       m.num_orders,
       m.avg_order_value,
       r.product_name AS top_product
FROM country_metrics m
LEFT JOIN ranked r ON r.country = m.country AND r.rn = 1
WHERE m.num_orders >= 10
ORDER BY m.total_revenue DESC;
"""

ROUND_DECIMALS = 6


def _round(value):
    if isinstance(value, float):
        return round(value, ROUND_DECIMALS)
    return value


def build_connection(seed_path: Path = SEED) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(seed_path.read_text(encoding="utf-8"))
    return conn


def canonical_rows(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.execute(CANONICAL_QUERY)
    cols = [d[0] for d in cur.description]
    return [{c: _round(row[i]) for i, c in enumerate(cols)} for row in cur.fetchall()]


def main() -> int:
    expected = json.loads(KEY.read_text(encoding="utf-8"))
    expected = [{k: _round(v) for k, v in row.items()} for row in expected]

    conn = build_connection()
    actual = canonical_rows(conn)

    if actual != expected:
        print("MISMATCH between seed.sql canonical query and expected_rows.json")
        print(f"  expected: {json.dumps(expected, sort_keys=True)}")
        print(f"  actual:   {json.dumps(actual, sort_keys=True)}")
        return 1

    print(f"OK: canonical query returns the {len(expected)} recorded row(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
