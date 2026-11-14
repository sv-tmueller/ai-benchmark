"""Unit tests for ``harness/dashboard.py``: row collection, rendering, CLI.

Every test builds its own repo root in a temporary directory, so nothing
depends on the real ``results/`` tree. The sorting and grouping script is
exercised under ``node`` when it is installed (and skipped otherwise); the
click wiring that rebuilds the table body is not exercised without a browser.
"""

import base64
import contextlib
import hashlib
import html
import html.parser
import io
import json
import re
import shutil
import subprocess
import tempfile
import unittest
import urllib.parse
from pathlib import Path

from harness import dashboard

DASH = "—"


def _write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _add_result(root, folder, name, meta=None, run=None, deliverable="<html></html>"):
    """Create ``results/<folder>/<name>`` plus optional meta and run files.

    ``name`` is the deliverable's file name; ``meta`` and ``run`` may be a dict
    (written as JSON) or a str (written verbatim). ``None`` writes no file.
    """
    directory = root / "results" / folder
    stem = Path(name).stem
    if deliverable is not None:
        _write(directory / name, deliverable)
    for suffix, payload in ((".meta.json", meta), (".run.json", run)):
        if payload is None:
            continue
        text = payload if isinstance(payload, str) else json.dumps(payload)
        _write(directory / (stem + suffix), text)
    return directory / name


class TempRootCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)


class CollectRowsTest(TempRootCase):
    def test_one_row_per_deliverable_with_a_meta(self):
        _add_result(
            self.root, "alpha", "alpha_claude_opus_4_8_high.html",
            meta={
                "prompt_id": "game-alpha",
                "title": "Alpha game",
                "model": "claude-opus-4-8",
                "params": {"reasoning_effort": "high"},
                "generated_utc": "2026-11-14T18:00:00Z",
            },
            run={"duration_seconds": 754, "output_tokens": 12345, "cost_usd": 1.234},
        )
        _add_result(self.root, "alpha", "alpha_claude_fable_5_2_low.html", meta={})
        # No meta: not a result row.
        _add_result(self.root, "alpha", "alpha_orphan.html")
        # Meta without a deliverable: no row.
        _add_result(self.root, "alpha", "alpha_gone.html", meta={}, deliverable=None)
        # Harness output sitting next to the results.
        _write(self.root / "results" / "alpha" / "alpha_x_grading.json", "{}")
        _write(self.root / "results" / "alpha" / "alpha_x_review.html", "<p>")
        _write(self.root / "results" / "alpha" / "alpha_x.run.json", "{}")
        _write(self.root / "results" / "alpha" / "alpha_x.meta.json", "{}")
        # Directly under results/: not a result.
        _write(self.root / "results" / "loose.html", "<p>")
        _write(self.root / "results" / "loose.meta.json", "{}")

        rows, warnings = dashboard.collect_rows(self.root)

        self.assertEqual(warnings, [])
        self.assertEqual(
            [r.file for r in rows],
            ["alpha_claude_fable_5_2_low.html", "alpha_claude_opus_4_8_high.html"],
        )
        opus = rows[1]
        self.assertEqual(opus.prompt, "game-alpha")
        self.assertEqual(opus.title, "Alpha game")
        self.assertEqual(opus.model, "claude-opus-4-8")
        self.assertEqual(opus.effort, "high")
        self.assertEqual(opus.generated, "2026-11-14T18:00:00Z")
        self.assertEqual(opus.duration, 754)
        self.assertEqual(opus.output_tokens, 12345)
        self.assertEqual(opus.cost, 1.234)
        self.assertEqual(opus.relpath, "results/alpha/alpha_claude_opus_4_8_high.html")

    def test_run_file_next_to_a_meta_is_never_its_own_row(self):
        _add_result(self.root, "alpha", "alpha_m_low.html", meta={}, run={})
        _write(self.root / "results" / "alpha" / "alpha_m_low.run.meta.json", "{}")
        rows, _ = dashboard.collect_rows(self.root)
        self.assertEqual([r.file for r in rows], ["alpha_m_low.html"])

    def test_meta_fallbacks_come_from_folder_and_file_name(self):
        _add_result(self.root, "melon-jelly", "melon-jelly_claude_opus_4_8_high.html", meta={})
        _add_result(self.root, "melon-jelly", "melon-jelly_claude_fable_5_2.html", meta={})
        _add_result(
            self.root, "melon-jelly", "melon-jelly_glm_5.html",
            meta={"prompt_id": "", "model": 7, "params": "oops", "generated_utc": "pre-meta-convention"},
        )

        rows, warnings = dashboard.collect_rows(self.root)

        self.assertEqual(warnings, [])
        by_file = {r.file: r for r in rows}
        high = by_file["melon-jelly_claude_opus_4_8_high.html"]
        self.assertEqual((high.prompt, high.model, high.effort, high.generated),
                         ("melon-jelly", "claude_opus_4_8", "high", None))
        self.assertEqual(high.title, None)
        fable = by_file["melon-jelly_claude_fable_5_2.html"]
        self.assertEqual((fable.model, fable.effort), ("claude_fable_5_2", None))
        glm = by_file["melon-jelly_glm_5.html"]
        self.assertEqual((glm.prompt, glm.model, glm.effort, glm.generated),
                         ("melon-jelly", "glm_5", None, None))

    def test_effort_from_meta_params_wins_over_the_file_name(self):
        _add_result(
            self.root, "alpha", "alpha_m_low.html",
            meta={"params": {"reasoning_effort": "max"}, "model": "m"},
        )
        rows, _ = dashboard.collect_rows(self.root)
        self.assertEqual((rows[0].model, rows[0].effort), ("m", "max"))

    def test_invalid_meta_json_still_gives_a_row_and_a_warning(self):
        _add_result(self.root, "alpha", "alpha_m_low.html", meta="{not json")
        _add_result(self.root, "alpha", "alpha_n_low.html", meta="[1, 2]")

        rows, warnings = dashboard.collect_rows(self.root)

        self.assertEqual([r.file for r in rows], ["alpha_m_low.html", "alpha_n_low.html"])
        self.assertEqual(rows[0].prompt, "alpha")
        self.assertEqual((rows[0].model, rows[0].effort), ("m", "low"))
        self.assertEqual(len(warnings), 2)
        self.assertTrue(warnings[0].startswith("results/alpha/alpha_m_low.meta.json: "))

    def test_starting_order_is_prompt_model_effort_then_file_name(self):
        for name in ("b_zeta_low.html", "b_alpha_high.html", "b_alpha_low.html",
                     "b_alpha.html", "a_zeta_low.html"):
            _add_result(self.root, "b" if name.startswith("b") else "a", name,
                        meta={"model": name.split("_")[1]})
        rows, _ = dashboard.collect_rows(self.root)
        self.assertEqual(
            [r.file for r in rows],
            ["a_zeta_low.html", "b_alpha_low.html", "b_alpha_high.html",
             "b_alpha.html", "b_zeta_low.html"],
        )
        self.assertEqual([r.index for r in rows], [0, 1, 2, 3, 4])


class RunFileTest(TempRootCase):
    def _row(self, run):
        _add_result(self.root, "alpha", "alpha_m_low.html", meta={}, run=run)
        rows, warnings = dashboard.collect_rows(self.root)
        return rows[0], warnings

    def test_missing_run_file_gives_missing_metrics_without_a_warning(self):
        row, warnings = self._row(None)
        self.assertEqual((row.duration, row.output_tokens, row.cost), (None, None, None))
        self.assertEqual(warnings, [])

    def test_bad_run_json_gives_missing_metrics_and_a_warning(self):
        for text in ("{nope", "[1]"):
            with self.subTest(text=text):
                row, warnings = self._row(text)
                self.assertEqual((row.duration, row.output_tokens, row.cost), (None, None, None))
                self.assertEqual(len(warnings), 1)
                self.assertTrue(warnings[0].startswith("results/alpha/alpha_m_low.run.json: "))

    def test_each_bad_value_blanks_only_its_own_cell(self):
        cases = {
            "duration_seconds": ["12", -1, True, float("nan"), float("inf"), None],
            "output_tokens": ["12", -1, False, float("nan")],
            "cost_usd": ["0.5", -0.01, True, float("-inf")],
        }
        good = {"duration_seconds": 5, "output_tokens": 6, "cost_usd": 0.5}
        for key, bad_values in cases.items():
            for bad in bad_values:
                with self.subTest(key=key, bad=bad):
                    if (self.root / "results").exists():
                        shutil.rmtree(self.root / "results")
                    row, warnings = self._row(dict(good, **{key: bad}))
                    got = {"duration_seconds": row.duration, "output_tokens": row.output_tokens,
                           "cost_usd": row.cost}
                    for other in good:
                        expected = None if other == key else good[other]
                        self.assertEqual(got[other], expected, other)
                    self.assertEqual(len(warnings), 1)
                    self.assertIn(key, warnings[0])

    def test_absent_key_is_missing_without_a_warning_and_zero_is_valid(self):
        row, warnings = self._row({"duration_seconds": 0, "cost_usd": 0})
        self.assertEqual((row.duration, row.output_tokens, row.cost), (0, None, 0))
        self.assertEqual(warnings, [])

    def test_other_run_keys_are_not_read(self):
        row, warnings = self._row({"input_tokens": "junk", "cache_read_tokens": -5})
        self.assertEqual(warnings, [])


class FormatTest(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(dashboard.format_duration(45), "45s")
        self.assertEqual(dashboard.format_duration(754), "12m 34s")
        self.assertEqual(dashboard.format_duration(3723), "1h 02m 03s")
        self.assertEqual(dashboard.format_duration(0), "0s")
        self.assertEqual(dashboard.format_duration(45.4), "45s")
        self.assertEqual(dashboard.format_duration(59.6), "1m 00s")
        self.assertEqual(dashboard.format_duration(604), "10m 04s")

    def test_tokens_cost_and_date(self):
        self.assertEqual(dashboard.format_tokens(12345), "12,345")
        self.assertEqual(dashboard.format_tokens(0), "0")
        self.assertEqual(dashboard.format_cost(1.234), "$1.23")
        self.assertEqual(dashboard.format_cost(0), "$0.00")
        self.assertEqual(dashboard.format_cost(0.004), "<$0.01")
        self.assertEqual(dashboard.format_cost(0.01), "$0.01")
        self.assertEqual(dashboard.format_generated("2026-11-14T18:00:59Z"), "2026-11-14 18:00")
