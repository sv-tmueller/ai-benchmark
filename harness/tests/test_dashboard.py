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
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

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

    def test_generated_utc_counts_only_in_the_zero_padded_form(self):
        cases = {
            "2026-11-14T18:00:00Z": "2026-11-14T18:00:00Z",
            "2026-1-1T1:2:3Z": None,
            "2026-9-1T00:00:00Z": None,
            "2026-11-14T18:00:00": None,
            "2026-11-14T18:00:00Z\n": None,
            "2026-02-30T00:00:00Z": None,
            "٢026-11-14T18:00:00Z": None,
            " 2026-11-14T18:00:00Z": None,
            20261114: None,
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                if (self.root / "results").exists():
                    shutil.rmtree(self.root / "results")
                _add_result(self.root, "alpha", "alpha_m_low.html",
                            meta={"generated_utc": value})
                rows, _ = dashboard.collect_rows(self.root)
                self.assertEqual(rows[0].generated, expected)

    def test_starting_order_is_prompt_model_effort_then_file_name(self):
        for name in ("b_zeta_low.html", "b_alpha_high.html", "b_alpha_low.html",
                     "b_alpha.html", "a_zeta_low.html"):
            _add_result(self.root, "b" if name.startswith("b") else "a", name,
                        meta={"model": Path(name).stem.split("_")[1]})
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

    def test_integer_too_large_for_a_float_blanks_its_cell_with_a_warning(self):
        text = '{"duration_seconds": 1%s, "output_tokens": 5}' % ("0" * 400)
        row, warnings = self._row(text)
        self.assertEqual((row.duration, row.output_tokens, row.cost), (None, 5, None))
        self.assertEqual(len(warnings), 1)
        self.assertTrue(warnings[0].startswith("results/alpha/alpha_m_low.run.json: "))
        self.assertIn("duration_seconds", warnings[0])

    def test_negative_zero_is_treated_as_zero_for_every_metric(self):
        row, warnings = self._row(
            '{"duration_seconds": -0.0, "output_tokens": -0.0, "cost_usd": -0.0}')
        self.assertEqual(warnings, [])
        for value in (row.duration, row.output_tokens, row.cost):
            self.assertEqual(value, 0)
            self.assertEqual(math.copysign(1, value), 1.0)
        page = dashboard.render([row])
        self.assertIn('<td class="num" data-sort="0.0">$0.00</td>', page)
        self.assertNotIn('data-sort="-', page)
        self.assertNotIn("$-", page)

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


class PageParser(html.parser.HTMLParser):
    """Collect the parts of a rendered page the tests look at."""

    def __init__(self):
        super().__init__()
        self.csp = None
        self.scripts = []
        self.styles = []
        self.headers = []      # attrs of the <th> cells in <thead>
        self.rows = []         # {"attrs", "cells": [{"attrs", "text", "links"}]}
        self.headings = []     # group-heading rows (there are none at load)
        self.options = []      # (value, label) of the <option> elements
        self.selects = []      # attrs of the <select> elements
        self.empty = []        # text of <p class="empty">
        self.tags = []
        self._capture = None
        self._in_thead = False
        self._row = None
        self._cell = None
        self._option = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy":
            self.csp = attrs["content"]
        elif tag in ("script", "style"):
            self._capture = []
            (self.scripts if tag == "script" else self.styles).append(self._capture)
        elif tag == "thead":
            self._in_thead = True
        elif tag == "th" and self._in_thead:
            self.headers.append(attrs)
        elif tag == "tr" and not self._in_thead:
            if attrs.get("class") == "group-heading":
                self.headings.append(attrs)
            else:
                self._row = {"attrs": attrs, "cells": []}
                self.rows.append(self._row)
        elif tag == "td" and self._row is not None:
            self._cell = {"attrs": attrs, "text": "", "links": []}
            self._row["cells"].append(self._cell)
        elif tag == "a" and self._cell is not None:
            self._cell["links"].append(attrs)
        elif tag == "select":
            self.selects.append(attrs)
        elif tag == "option":
            self._option = [attrs.get("value"), ""]
            self.options.append(self._option)
        elif tag == "p" and attrs.get("class") == "empty":
            self._capture = []
            self.empty.append(self._capture)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "p"):
            self._capture = None
        elif tag == "thead":
            self._in_thead = False
        elif tag == "td":
            self._cell = None
        elif tag == "tr":
            self._row = None
        elif tag == "option":
            self._option = None

    def handle_data(self, data):
        if self._capture is not None:
            self._capture.append(data)
        if self._cell is not None:
            self._cell["text"] += data
        if self._option is not None:
            self._option[1] += data

    def script_text(self):
        return ["".join(parts) for parts in self.scripts]

    def style_text(self):
        return ["".join(parts) for parts in self.styles]


def _parse(page):
    parser = PageParser()
    parser.feed(page)
    parser.close()
    return parser


def _page(root):
    rows, _ = dashboard.collect_rows(root)
    return dashboard.render(rows)


class RenderTest(TempRootCase):
    def _fixture(self):
        _add_result(
            self.root, "alpha", "alpha_claude_opus_4_8_high.html",
            meta={"prompt_id": "game-alpha", "title": "Alpha game", "model": "claude-opus-4-8",
                  "params": {"reasoning_effort": "high"}, "generated_utc": "2026-11-14T18:00:00Z"},
            run={"duration_seconds": 754, "output_tokens": 12345, "cost_usd": 1.234},
        )
        _add_result(self.root, "alpha", "alpha_glm_5_low.html", meta={},
                    run={"duration_seconds": 45, "output_tokens": 9, "cost_usd": 0.004})
        _add_result(self.root, "beta", "beta_glm_5.html", meta={})

    def test_page_structure(self):
        self._fixture()
        page = _page(self.root)
        parsed = _parse(page)

        self.assertEqual(
            [(h["data-key"], h["data-type"]) for h in parsed.headers],
            [("prompt", "text"), ("model", "text"), ("effort", "num"), ("generated", "text"),
             ("duration", "num"), ("output_tokens", "num"), ("cost", "num"), ("file", "text")],
        )
        self.assertEqual(len(parsed.rows), 3)
        self.assertEqual([r["attrs"]["data-index"] for r in parsed.rows], ["0", "1", "2"])
        for row in parsed.rows:
            self.assertEqual(len(row["cells"]), 8)
        for header, cell in zip(parsed.headers, parsed.rows[0]["cells"]):
            if header["data-type"] == "num" and "data-sort" in cell["attrs"]:
                float(cell["attrs"]["data-sort"])
        self.assertEqual([tuple(o) for o in parsed.options],
                         [("", "none"), ("prompt", "prompt"), ("model", "model"), ("effort", "effort")])
        self.assertIn("3 results from results/ in this checkout.", page)
        self.assertEqual(parsed.headings, [])

    def test_group_by_select_opts_out_of_form_restoring(self):
        # The script never renders at load, so a browser-restored choice would
        # show above an ungrouped table.
        self._fixture()
        selects = _parse(_page(self.root)).selects
        self.assertEqual(len(selects), 1)
        self.assertEqual(selects[0].get("id"), "group-by")
        self.assertEqual(selects[0].get("autocomplete"), "off")

    def test_cells_show_formatted_values_and_sort_by_raw_ones(self):
        self._fixture()
        parsed = _parse(_page(self.root))
        # Rows start sorted by prompt (alpha before game-alpha is not the case:
        # "alpha" < "beta" < "game-alpha"), then model, then effort.
        texts = [[c["text"] for c in r["cells"]] for r in parsed.rows]
        self.assertEqual(texts[0][:7],
                         ["alpha", "glm_5", "low", DASH, "45s", "9", "<$0.01"])
        self.assertEqual(texts[1][:7], ["beta", "glm_5", DASH, DASH, DASH, DASH, DASH])
        self.assertEqual(texts[2][:7],
                         ["game-alpha", "claude-opus-4-8", "high", "2026-11-14 18:00",
                          "12m 34s", "12,345", "$1.23"])
        attrs = [[c["attrs"] for c in r["cells"]] for r in parsed.rows]
        self.assertEqual(attrs[0][2]["data-sort"], "0")          # low
        self.assertEqual(attrs[2][2]["data-sort"], "2")          # high
        self.assertEqual(attrs[2][3]["data-sort"], "2026-11-14T18:00:00Z")
        self.assertEqual(float(attrs[2][4]["data-sort"]), 754)
        self.assertEqual(float(attrs[2][5]["data-sort"]), 12345)
        self.assertEqual(float(attrs[2][6]["data-sort"]), 1.234)
        self.assertEqual(attrs[2][0]["title"], "Alpha game")
        self.assertEqual(attrs[2][0]["data-sort"], "game-alpha")
        self.assertEqual(attrs[0][7]["data-sort"], "alpha_glm_5_low.html")
        # Missing values have no data-sort at all.
        for cell in range(2, 7):
            self.assertNotIn("data-sort", attrs[1][cell])
        self.assertIn("&lt;$0.01", _page(self.root))
        self.assertNotIn("<$0.01", _page(self.root))

    def test_unknown_effort_is_shown_but_sorts_as_missing(self):
        _add_result(self.root, "alpha", "alpha_m_low.html",
                    meta={"params": {"reasoning_effort": "turbo"}})
        parsed = _parse(_page(self.root))
        cell = parsed.rows[0]["cells"][2]
        self.assertEqual(cell["text"], "turbo")
        self.assertNotIn("data-sort", cell["attrs"])

    def test_values_from_disk_are_escaped_everywhere(self):
        evil = "<script>alert(1)</script></script>\"'&amp;"
        _add_result(
            self.root, "we&ird", "we&ird_m_low.html",
            meta={"prompt_id": evil, "title": evil, "model": evil,
                  "params": {"reasoning_effort": evil}},
        )
        _add_result(self.root, "plain", "plain_m'<i>_low.html", meta={})
        page = _page(self.root)

        self.assertNotIn(evil, page)
        self.assertIn(html.escape(evil, quote=True), page)
        self.assertNotIn("alert(1)</script>", page)
        self.assertNotIn("<i>", page)
        self.assertIn("plain_m&#x27;&lt;i&gt;_low.html", page)
        self.assertIn("we&amp;ird", page)
        self.assertEqual(page.count("<script"), 1)
        self.assertEqual(_parse(page).script_text(), [dashboard.SCRIPT])
        self.assertEqual(_parse(page).style_text(), [dashboard.STYLE])

    def test_deliverable_contents_never_reach_the_page(self):
        marker = "DELIVERABLE-MARKER-9f3a"
        _add_result(self.root, "alpha", "alpha_m_low.html", meta={},
                    deliverable="<script>%s</script>" % marker)
        self.assertNotIn(marker, _page(self.root))

    def test_links_open_in_a_new_tab_with_percent_encoded_relative_hrefs(self):
        self._fixture()
        weird_folder = "we ird#?%'\":x"
        weird_name = "we ird#?%'\":x_m ?%'\"#:_low.html"
        _add_result(self.root, weird_folder, weird_name, meta={})
        parsed = _parse(_page(self.root))

        links = [link for row in parsed.rows for cell in row["cells"] for link in cell["links"]]
        self.assertEqual(len(links), 4)
        for link in links:
            self.assertEqual(link["target"], "_blank")
            self.assertEqual(link["rel"], "noopener noreferrer")
            self.assertTrue(link["href"].startswith("results/"), link["href"])
            self.assertRegex(link["href"], r"^[A-Za-z0-9_.~%/-]+$")
            target = self.root / urllib.parse.unquote(link["href"])
            self.assertTrue(target.is_file(), link["href"])
        weird = [l for l in links if "%23" in l["href"]]
        self.assertEqual(len(weird), 1)
        self.assertEqual(urllib.parse.unquote(weird[0]["href"]),
                         "results/%s/%s" % (weird_folder, weird_name))
        self.assertEqual(
            [c["text"] for r in parsed.rows for c in r["cells"][7:]].count(weird_name), 1)

    def test_page_is_self_contained_and_uses_no_unsafe_script_apis(self):
        self._fixture()
        page = _page(self.root)
        for needle in ("http:", "https:", "src=", "<link", "@import", "url(",
                       "innerHTML", "insertAdjacentHTML", "document.write", "eval"):
            self.assertNotIn(needle, page)

    def test_csp_hashes_match_the_emitted_script_and_style(self):
        self._fixture()
        parsed = _parse(_page(self.root))

        def sha(text):
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            return "'sha256-%s'" % base64.b64encode(digest).decode("ascii")

        self.assertEqual(
            parsed.csp,
            "default-src 'none'; script-src %s; style-src %s"
            % (sha(parsed.script_text()[0]), sha(parsed.style_text()[0])),
        )

    def test_page_without_results_says_so_and_has_no_table_or_script(self):
        page = dashboard.render([])
        parsed = _parse(page)
        self.assertEqual(["".join(p) for p in parsed.empty],
                         ["No results found under results/ in this checkout."])
        self.assertIn("<h1>", page)
        for needle in ("<table", "<select", "<script"):
            self.assertNotIn(needle, page)
        self.assertEqual(
            parsed.csp,
            "default-src 'none'; style-src 'sha256-%s'"
            % base64.b64encode(hashlib.sha256(dashboard.STYLE.encode("utf-8")).digest()).decode("ascii"),
        )

    def test_render_is_deterministic(self):
        self._fixture()
        self.assertEqual(_page(self.root), _page(self.root))


# Items as the page script builds them from the table: data-sort values (null
# when the cell has none) and the displayed text, per column key.
_NODE_ITEMS = [
    {"index": 0, "values": {"n": "10", "t": "b10", "effort": "2"},
     "texts": {"n": "10", "t": "b10", "effort": "high"}},
    {"index": 1, "values": {"n": "9", "t": "a", "effort": "0"},
     "texts": {"n": "9", "t": "a", "effort": "low"}},
    {"index": 2, "values": {"n": None, "t": None, "effort": None},
     "texts": {"n": "—", "t": "—", "effort": "turbo"}},
    {"index": 3, "values": {"n": "100", "t": "b9", "effort": "0"},
     "texts": {"n": "100", "t": "b9", "effort": "low"}},
    {"index": 4, "values": {"n": "9", "t": "b9", "effort": "4"},
     "texts": {"n": "9", "t": "b9", "effort": "max"}},
    {"index": 5, "values": {"n": "10", "t": "a", "effort": "2"},
     "texts": {"n": "10", "t": "a", "effort": "high"}},
]

_NODE_SNIPPET = """
var types = {n: "num", t: "text", effort: "num"};
var items = %s;
function run(sortKey, sortDir, groupKey) {
  var r = orderRows(items, sortKey, sortDir, groupKey, types);
  return {order: r.items.map(function (i) { return i.index; }), groups: r.groups};
}
console.log(JSON.stringify({
  unsorted: run(null, "asc", ""),
  numAsc: run("n", "asc", ""),
  numDesc: run("n", "desc", ""),
  textAsc: run("t", "asc", ""),
  textDesc: run("t", "desc", ""),
  byEffort: run(null, "asc", "effort"),
  byEffortThenNumDesc: run("n", "desc", "effort"),
  compare: [compareValues("9", "10", "num"), compareValues("b9", "b10", "text"),
            compareValues(null, "1", "num"), compareValues("1", null, "text"),
            compareValues(null, null, "num")]
}));
"""


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class ScriptUnderNodeTest(TempRootCase):
    def _script(self):
        _add_result(self.root, "alpha", "alpha_m_low.html", meta={})
        return _parse(_page(self.root)).script_text()[0]

    def _run_node(self, source):
        path = self.root / "script.js"
        path.write_text(source, encoding="utf-8")
        return subprocess.run(["node", str(path)], capture_output=True, text=True,
                              timeout=30, check=True)

    def test_script_is_valid_javascript(self):
        path = self.root / "check.js"
        path.write_text(self._script(), encoding="utf-8")
        subprocess.run(["node", "--check", str(path)], capture_output=True, text=True,
                       timeout=30, check=True)

    def test_sorting_and_grouping(self):
        result = self._run_node(self._script() + _NODE_SNIPPET % json.dumps(_NODE_ITEMS))
        out = json.loads(result.stdout)

        self.assertEqual(out["unsorted"], {"order": [0, 1, 2, 3, 4, 5], "groups": []})
        # Numbers sort as numbers (9 < 10 < 100); missing is last in both
        # directions; ties (9, 9 and 10, 10) fall back to the starting index.
        self.assertEqual(out["numAsc"]["order"], [1, 4, 0, 5, 3, 2])
        self.assertEqual(out["numDesc"]["order"], [3, 0, 5, 1, 4, 2])
        # Text sorts naturally (b9 < b10), also with ties by index.
        self.assertEqual(out["textAsc"]["order"], [1, 5, 3, 4, 0, 2])
        self.assertEqual(out["textDesc"]["order"], [0, 3, 4, 1, 5, 2])
        # Effort groups run low to max, missing last, with label and count.
        self.assertEqual(out["byEffort"]["groups"], [
            {"label": "low", "count": 2}, {"label": "high", "count": 2},
            {"label": "max", "count": 1}, {"label": "—", "count": 1}])
        self.assertEqual(out["byEffort"]["order"], [1, 3, 0, 5, 4, 2])
        # Rows inside a group follow the column sort.
        self.assertEqual(out["byEffortThenNumDesc"]["order"], [3, 1, 0, 5, 4, 2])
        self.assertEqual(out["compare"][0], -1)
        self.assertLess(out["compare"][1], 0)
        self.assertEqual(out["compare"][2:], [1, -1, 0])


class MainTest(TempRootCase):
    def _main(self, argv=()):
        out, err = io.StringIO(), io.StringIO()
        code = dashboard.main(list(argv), repo_root=self.root, out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_writes_the_page_at_the_repo_root_and_prints_its_path(self):
        _add_result(self.root, "alpha", "alpha_m_low.html", meta={})
        code, out, err = self._main()

        target = self.root / "dashboard.html"
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "%s\n" % target)
        self.assertEqual(target.read_text(encoding="utf-8"), _page(self.root))

    def test_second_run_overwrites_and_is_byte_identical_for_the_same_input(self):
        _add_result(self.root, "alpha", "alpha_m_low.html", meta={})
        self._main()
        first = (self.root / "dashboard.html").read_bytes()
        (self.root / "dashboard.html").write_text("PLANTED-MARKER", encoding="utf-8")

        code, _, _ = self._main()

        self.assertEqual(code, 0)
        self.assertEqual((self.root / "dashboard.html").read_bytes(), first)
        self.assertNotIn(b"PLANTED-MARKER", first)

    def test_no_results_still_writes_the_empty_page_and_exits_zero(self):
        for setup in ("gitkeep only", "no results folder"):
            with self.subTest(setup):
                if (self.root / "results").exists():
                    shutil.rmtree(self.root / "results")
                if setup == "gitkeep only":
                    _write(self.root / "results" / ".gitkeep")
                else:
                    self.assertFalse((self.root / "results").exists())
                code, out, err = self._main()
                page = (self.root / "dashboard.html").read_text(encoding="utf-8")
                self.assertEqual((code, err), (0, ""))
                self.assertIn("No results found under results/ in this checkout.", page)
                self.assertNotIn("<table", page)

    def test_bad_sidecars_warn_on_stderr_and_still_exit_zero(self):
        _add_result(self.root, "alpha", "alpha_m_low.html", meta="{nope", run="[1]")
        code, _, err = self._main()
        self.assertEqual(code, 0)
        self.assertEqual(
            sorted(err.splitlines()),
            sorted(["warning: results/alpha/alpha_m_low.meta.json: cannot read meta file",
                    "warning: results/alpha/alpha_m_low.run.json: run file is not a JSON object"]),
        )

    def test_huge_run_file_integer_warns_and_still_writes_the_row(self):
        _add_result(self.root, "alpha", "alpha_m_low.html", meta={},
                    run='{"duration_seconds": 1%s, "output_tokens": 5}' % ("0" * 400))
        code, _, err = self._main()
        self.assertEqual(code, 0)
        self.assertEqual(len(err.splitlines()), 1)
        self.assertTrue(err.startswith("warning: results/alpha/alpha_m_low.run.json: "))
        row = _parse((self.root / "dashboard.html").read_text(encoding="utf-8")).rows[0]
        self.assertEqual([c["text"] for c in row["cells"]][4:6], [DASH, "5"])

    def test_non_utf8_names_still_get_one_row_each_and_never_a_traceback(self):
        root_b = os.fsencode(self.root)
        deliverables = (
            (b"bad\xffdir", b"bad\xffdir_claude_low"),
            (b"good", b"g\xff_claude_low"),
            (b"good", b"good_cl\xffaude_low"),
        )
        try:
            for directory, stem in deliverables:
                os.makedirs(os.path.join(root_b, b"results", directory), exist_ok=True)
                for suffix, content in ((b".html", b"<html></html>"), (b".meta.json", b"{}")):
                    with open(os.path.join(root_b, b"results", directory, stem + suffix), "wb") as f:
                        f.write(content)
        except (OSError, UnicodeError) as exc:
            self.skipTest("filesystem refuses non-UTF-8 names: %s" % exc)

        # Strict encoders: a surrogate reaching stdout or stderr would raise.
        out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="strict")
        err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="strict")
        code = dashboard.main([], repo_root=self.root, out=out, err=err)
        out.flush()
        err.flush()
        err_text = err.buffer.getvalue().decode("utf-8")

        self.assertEqual(code, 0)
        self.assertEqual(len(err_text.splitlines()), 3, err_text)
        for line in err_text.splitlines():
            self.assertTrue(line.startswith("warning: results/"), line)
        page = (self.root / "dashboard.html").read_bytes().decode("utf-8")
        parsed = _parse(page)
        self.assertEqual(len(parsed.rows), 3)
        shown = {}
        for row in parsed.rows:
            cells = row["cells"]
            link = cells[7]["links"][0]
            self.assertRegex(link["href"], r"^[A-Za-z0-9_.~%/-]+$")
            raw = urllib.parse.unquote_to_bytes(link["href"])
            self.assertTrue(os.path.isfile(os.path.join(root_b, raw)), link["href"])
            shown[raw] = [c["text"] for c in cells[:3]] + [cells[7]["text"]]
        self.assertEqual(
            shown[b"results/bad\xffdir/bad\xffdir_claude_low.html"],
            ["bad�dir", "claude", "low", "bad�dir_claude_low.html"])
        self.assertEqual(
            shown[b"results/good/g\xff_claude_low.html"],
            ["good", "claude", "low", "g�_claude_low.html"])
        # A bad byte inside the tag reaches the model cell, cleaned.
        self.assertEqual(
            shown[b"results/good/good_cl\xffaude_low.html"],
            ["good", "cl�aude", "low", "good_cl�aude_low.html"])

    def test_lone_surrogate_in_meta_text_is_cleaned_and_never_a_traceback(self):
        # JSON "\\udcff" decodes to a lone surrogate that no UTF-8 stream can encode.
        _add_result(
            self.root, "alpha", "alpha_m_low.html",
            meta='{"prompt_id": "p\\udcffid", "title": "t\\udcffitle", '
                 '"model": "m\\udcffodel", "params": {"reasoning_effort": "\\udcff"}}')
        out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="strict")
        err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="strict")

        code = dashboard.main([], repo_root=self.root, out=out, err=err)

        self.assertEqual(code, 0)
        page = (self.root / "dashboard.html").read_bytes().decode("utf-8")
        row = _parse(page).rows[0]
        self.assertEqual([c["text"] for c in row["cells"]][:3], ["p�id", "m�odel", "�"])
        self.assertEqual(row["cells"][0]["attrs"]["title"], "t�itle")

    def test_deeply_nested_run_file_warns_and_still_writes_the_row(self):
        _add_result(self.root, "alpha", "alpha_m_low.html", meta={}, run="[" * 100000)
        code, _, err = self._main()
        self.assertEqual(code, 0)
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertTrue(err.startswith("warning: results/alpha/alpha_m_low.run.json: "), err)
        row = _parse((self.root / "dashboard.html").read_text(encoding="utf-8")).rows[0]
        self.assertEqual([c["text"] for c in row["cells"]][4:7], [DASH, DASH, DASH])

    def test_deeply_nested_meta_file_warns_and_still_writes_the_row(self):
        _add_result(self.root, "alpha", "alpha_m_low.html", meta="[" * 100000)
        code, _, err = self._main()
        self.assertEqual(code, 0)
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertTrue(err.startswith("warning: results/alpha/alpha_m_low.meta.json: "), err)
        row = _parse((self.root / "dashboard.html").read_text(encoding="utf-8")).rows[0]
        self.assertEqual([c["text"] for c in row["cells"]][:3], ["alpha", "m", "low"])

    def test_unwritable_target_exits_one_with_one_line_on_stderr(self):
        (self.root / "dashboard.html").mkdir()
        code, out, err = self._main()
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(len(err.splitlines()), 1)
        self.assertTrue(err.startswith("error: "))

    def test_unexpected_argument_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                self._main(["--output", "x.html"])
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse((self.root / "dashboard.html").exists())

    def test_script_runs_directly_from_any_directory(self):
        script = Path(dashboard.__file__)
        result = subprocess.run([sys.executable, str(script), "-h"], cwd=self.root,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dashboard.html", result.stdout)


# --- reading the results from a git tree --------------------------------------

def _blob_oid(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class FakeGit:
    """The two git commands ``collect_rows_at`` may issue, answered from ``entries``.

    ``entries`` is a list of ``(path bytes, content bytes)`` or
    ``(path bytes, content bytes, mode)``; the mode defaults to ``100644``. A
    ``160000`` entry is a gitlink: it lists with type ``commit`` and has no
    blob. The listing is in byte order, which is git's order for these names
    (folder ``a.b`` before folder ``a``). Anything but the two commands, with
    exactly the expected arguments, fails the test.
    """

    def __init__(self, entries, missing=()):
        self.entries = sorted((e + (b"100644",) if len(e) == 2 else e) for e in entries)
        self.missing = set(missing)
        self.calls = []

    def ls_tree_output(self):
        out = b""
        for path, content, mode in self.entries:
            kind, oid = (b"commit", b"%040x" % 7) if mode == b"160000" else (
                b"blob", _blob_oid(content).encode("ascii"))
            out += b"%s %s %s\t%s\0" % (mode, kind, oid, path)
        return out

    def cat_file_output(self, request):
        blobs = {_blob_oid(c): c for _, c, mode in self.entries if mode != b"160000"}
        out = b""
        for oid in request.decode("ascii").split("\n")[:-1]:
            if oid in self.missing or oid not in blobs:
                out += b"%s missing\n" % oid.encode("ascii")
            else:
                out += b"%s blob %d\n%s\n" % (oid.encode("ascii"), len(blobs[oid]), blobs[oid])
        return out

    def __call__(self, args, input=None):
        self.calls.append((list(args), input))
        if args == ["ls-tree", "-r", "-z", "REV", "--", "results"]:
            return self.ls_tree_output()
        if args == ["cat-file", "--batch"]:
            return self.cat_file_output(input)
        raise AssertionError("unexpected git call: %r" % (args,))

    def cat_file_requests(self):
        return [input for args, input in self.calls if args == ["cat-file", "--batch"]]


def _json_bytes(value):
    return json.dumps(value).encode("utf-8")


def _meta(prompt="p", model="m", effort="low", title="T"):
    return _json_bytes({"prompt_id": prompt, "model": model, "title": title,
                        "params": {"reasoning_effort": effort},
                        "generated_utc": "2026-11-14T18:00:00Z"})


def _write_entries(root, entries):
    """Write ``(path bytes, content[, mode])`` entries under ``root`` as regular files."""
    root_b = os.fsencode(root)
    for entry in entries:
        path, content = entry[0], entry[1]
        full = os.path.join(root_b, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(content)


def _parity_entries():
    run = _json_bytes({"duration_seconds": 754, "output_tokens": 12345, "cost_usd": 1.234})
    return [
        # Folders a and a.b hold results that tie on every sort key but the folder.
        (b"results/a/p_m_low.html", b"<html>a</html>"),
        (b"results/a/p_m_low.meta.json", _meta()),
        (b"results/a/p_m_low.run.json", run),
        (b"results/a.b/p_m_low.html", b"<html>a.b</html>"),
        (b"results/a.b/p_m_low.meta.json", _meta()),
        (b"results/a.b/p_m_low.run.json", run),
        # A second row in the same folder, with a non-ASCII title.
        (b"results/a/p_m_high.html", b"<html>h</html>"),
        (b"results/a/p_m_high.meta.json", _meta(effort="high", title="Größe ✓")),
        # Not results: harness output, no meta, meta without a deliverable.
        (b"results/a/p_m_low_grading.json", b"{}"),
        (b"results/a/p_m_low_review.html", b"<p>"),
        (b"results/a/p_m_low.png", b"\x89PNG"),
        (b"results/a/orphan.html", b"<p>"),
        (b"results/a/gone.meta.json", b"{}"),
        # Directly under results/ and below a results folder: not results.
        (b"results/loose.html", b"<p>"),
        (b"results/loose.meta.json", b"{}"),
        (b"results/a/deeper/x.html", b"<p>"),
        (b"results/a/deeper/x.meta.json", b"{}"),
        # Sidecars that cannot be read: still rows, with warnings.
        (b"results/b/q_n_low.html", b"<p>"),
        (b"results/b/q_n_low.meta.json", b"{not json"),
        (b"results/b/q_n_low.run.json", b"[1]"),
        (b"results/b/q_o_low.html", b"<p>"),
        (b"results/b/q_o_low.meta.json", b"[1, 2]"),
        (b"results/b/q_o_low.run.json", b'{"duration_seconds": 1%s}' % (b"0" * 400)),
        (b"results/b/q_u_low.html", b"<p>"),
        (b"results/b/q_u_low.meta.json", json.dumps({"model": "u"}).encode("utf-16")),
        (b"results/b/q_u_low.run.json", b"\xff\xfe"),
        (b"results/b/q_deep_low.html", b"<p>"),
        (b"results/b/q_deep_low.meta.json", b"[" * 100000),
    ]


class ReaderParityTest(TempRootCase):
    """The working-tree reader and the git-tree reader share one core."""

    def _both(self, entries, **fake_kwargs):
        _write_entries(self.root, entries)
        fake = FakeGit(entries, **fake_kwargs)
        return dashboard.collect_rows(self.root), dashboard.collect_rows_at("REV", fake), fake

    def test_same_rows_and_warnings_for_the_same_files(self):
        by_hand, from_git, _ = self._both(_parity_entries())
        self.assertEqual(from_git, by_hand)
        rows, warnings = from_git
        self.assertEqual(len(rows), 7)
        self.assertEqual(len(warnings), 7)
        self.assertEqual(dashboard.render(rows), dashboard.render(by_hand[0]))

    def test_rows_that_tie_keep_the_folder_name_order_not_git_tree_order(self):
        _, (rows, _), fake = self._both(_parity_entries())
        # git lists results/a.b/ before results/a/ ...
        listed = [e[0] for e in fake.entries if e[0].endswith(b"p_m_low.html")]
        self.assertEqual(listed, [b"results/a.b/p_m_low.html", b"results/a/p_m_low.html"])
        # ... the rows must come out folder a first, as a directory walk gives them.
        tied = [r.relpath for r in rows if r.file == "p_m_low.html"]
        self.assertEqual(tied, ["results/a/p_m_low.html", "results/a.b/p_m_low.html"])

    def test_non_utf8_names_give_the_same_rows_in_both_readers(self):
        entries = [
            (b"results/bad\xffdir/bad\xffdir_claude_low.html", b"<p>"),
            (b"results/bad\xffdir/bad\xffdir_claude_low.meta.json", b"{}"),
            (b"results/good/g\xff_claude_low.html", b"<p>"),
            (b"results/good/g\xff_claude_low.meta.json", b"{}"),
        ]
        try:
            _write_entries(self.root, entries)
        except (OSError, UnicodeError) as exc:
            self.skipTest("filesystem refuses non-UTF-8 names: %s" % exc)
        by_hand = dashboard.collect_rows(self.root)
        from_git = dashboard.collect_rows_at("REV", FakeGit(entries))
        self.assertEqual(from_git, by_hand)
        self.assertEqual(len(from_git[0]), 2)
        self.assertEqual(len(from_git[1]), 2)

    def test_no_results_gives_no_rows(self):
        rows, warnings = dashboard.collect_rows_at("REV", FakeGit([]))
        self.assertEqual((rows, warnings), ([], []))

    def test_a_missing_run_file_has_no_warning_and_a_missing_meta_blob_has_one(self):
        entries = [
            (b"results/a/p_m_low.html", b"<p>"),
            (b"results/a/p_m_low.meta.json", _meta()),
            (b"results/a/p_m_low.run.json", b'{"output_tokens": 3}'),
        ]
        meta_oid = _blob_oid(_meta())
        rows, warnings = dashboard.collect_rows_at("REV", FakeGit(entries, missing={meta_oid}))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].output_tokens, 3)
        self.assertEqual(warnings, ["results/a/p_m_low.meta.json: cannot read meta file"])
        run_oid = _blob_oid(b'{"output_tokens": 3}')
        rows, warnings = dashboard.collect_rows_at("REV", FakeGit(entries, missing={run_oid}))
        self.assertEqual(rows[0].output_tokens, None)
        self.assertEqual(len(warnings), 1)
        self.assertTrue(warnings[0].startswith("results/a/p_m_low.run.json: cannot read run file ("))


class SymlinkTest(TempRootCase):
    """A symlink under ``results/`` is never a result, in either reader."""

    def _link(self, link, target):
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("cannot create symlinks: %s" % exc)

    def test_a_symlinked_deliverable_is_not_a_result(self):
        outside = _write(self.root / "outside.html", "<p>")
        _write(self.root / "results" / "a" / "p_m_low.meta.json", "{}")
        self._link(self.root / "results" / "a" / "p_m_low.html", outside)
        self.assertEqual(dashboard.collect_rows(self.root), ([], []))

    def test_a_symlinked_meta_file_is_not_a_pairing(self):
        outside = _write(self.root / "outside.json", "{}")
        _write(self.root / "results" / "a" / "p_m_low.html", "<p>")
        self._link(self.root / "results" / "a" / "p_m_low.meta.json", outside)
        self.assertEqual(dashboard.collect_rows(self.root), ([], []))

    def test_a_symlinked_run_file_is_not_read(self):
        outside = _write(self.root / "outside.json", '{"output_tokens": 99}')
        _add_result(self.root, "a", "p_m_low.html", meta={})
        self._link(self.root / "results" / "a" / "p_m_low.run.json", outside)
        rows, warnings = dashboard.collect_rows(self.root)
        self.assertEqual((len(rows), warnings), (1, []))
        self.assertIsNone(rows[0].output_tokens)

    def test_a_symlinked_folder_is_not_walked(self):
        _add_result(self.root, "real", "p_m_low.html", meta={})
        self._link(self.root / "results" / "alias", self.root / "results" / "real")
        rows, _ = dashboard.collect_rows(self.root)
        self.assertEqual([r.relpath for r in rows], ["results/real/p_m_low.html"])

    def test_git_symlinks_and_gitlinks_are_not_results(self):
        meta = _meta()
        entries = [
            (b"results/real/p_m_low.html", b"<p>", b"100755"),
            (b"results/real/p_m_low.meta.json", meta),
            # a symlink deliverable, a symlink meta, a gitlink
            (b"results/link/p_m_low.html", b"../real/p_m_low.html", b"120000"),
            (b"results/link/p_m_low.meta.json", meta),
            (b"results/linkmeta/p_m_low.html", b"<p>"),
            (b"results/linkmeta/p_m_low.meta.json", b"../real/p_m_low.meta.json", b"120000"),
            (b"results/sub/p_m_low.html", b"", b"160000"),
            (b"results/sub/p_m_low.meta.json", b"", b"160000"),
        ]
        fake = FakeGit(entries)
        rows, warnings = dashboard.collect_rows_at("REV", fake)
        self.assertEqual([r.relpath for r in rows], ["results/real/p_m_low.html"])
        self.assertEqual(warnings, [])
        # Only the regular meta blob was requested: never a symlink's or a gitlink's.
        requested = fake.cat_file_requests()
        self.assertEqual(len(requested), 1)
        self.assertEqual(requested[0].decode("ascii").split("\n")[:-1], [_blob_oid(meta)])


class GitReaderTest(unittest.TestCase):
    def test_ls_tree_is_asked_for_results_only_with_nul_separated_output(self):
        fake = FakeGit([])
        dashboard.collect_rows_at("REV", fake)
        self.assertEqual(fake.calls, [(["ls-tree", "-r", "-z", "REV", "--", "results"], None)])

    def test_only_meta_and_run_blobs_are_requested_once_in_one_call(self):
        meta, run = _meta(), _json_bytes({"output_tokens": 1})
        entries = [
            (b"results/a/p_m_low.html", b"DELIVERABLE-ONE"),
            (b"results/a/p_m_low.meta.json", meta),
            (b"results/a/p_m_low.run.json", run),
            (b"results/a/p_m_high.html", b"DELIVERABLE-TWO"),
            (b"results/a/p_m_high.meta.json", meta),  # the same blob again
            (b"results/a/p_m_low_grading.json", b"GRADING"),
            (b"results/a/p_m_low.png", b"PNG"),
        ]
        fake = FakeGit(entries)
        rows, warnings = dashboard.collect_rows_at("REV", fake)
        self.assertEqual((len(rows), warnings), (2, []))
        requests = fake.cat_file_requests()
        self.assertEqual(len(requests), 1)
        asked = requests[0].decode("ascii").split("\n")[:-1]
        self.assertEqual(sorted(asked), sorted({_blob_oid(meta), _blob_oid(run)}))
        for other in (b"DELIVERABLE-ONE", b"DELIVERABLE-TWO", b"GRADING", b"PNG"):
            self.assertNotIn(_blob_oid(other), asked)

    def test_no_meta_or_run_blobs_means_no_cat_file_call(self):
        fake = FakeGit([(b"results/a/p_m_low.html", b"<p>")])
        self.assertEqual(dashboard.collect_rows_at("REV", fake), ([], []))
        self.assertEqual(fake.cat_file_requests(), [])

    def test_blob_sizes_are_counted_in_bytes_not_characters(self):
        title = "Größe ✓ 日本語"
        entries = [(b"results/a/p_m_low.html", b"<p>"),
                   (b"results/a/p_m_low.meta.json", _json_bytes({"title": title})),
                   (b"results/a/p_m_low.run.json", b'{"output_tokens": 7}')]
        rows, warnings = dashboard.collect_rows_at("REV", FakeGit(entries))
        self.assertEqual((rows[0].title, rows[0].output_tokens, warnings), (title, 7, []))

    def test_a_blob_whose_content_looks_like_a_header_is_still_read_by_size(self):
        tricky = b'{"title": "x"}\n' + _blob_oid(b"y").encode("ascii") + b" missing\n"
        entries = [(b"results/a/p_m_low.html", b"<p>"),
                   (b"results/a/p_m_low.meta.json", tricky),
                   (b"results/a/p_m_low.run.json", b'{"output_tokens": 7}')]
        rows, warnings = dashboard.collect_rows_at("REV", FakeGit(entries))
        # The extra text after the JSON value makes the meta unreadable; the run file
        # that follows it in the stream is read correctly.
        self.assertEqual(rows[0].output_tokens, 7)
        self.assertEqual(warnings, ["results/a/p_m_low.meta.json: cannot read meta file"])

    def test_a_failing_git_call_propagates(self):
        def failing(args, input=None):
            raise dashboard.GitReadError("git ls-tree failed: boom")

        with self.assertRaises(dashboard.GitReadError):
            dashboard.collect_rows_at("REV", failing)

    def test_malformed_listing_and_stream_raise_git_read_error(self):
        meta = _meta()
        entries = [(b"results/a/p_m_low.html", b"<p>"), (b"results/a/p_m_low.meta.json", meta)]
        with self.assertRaises(dashboard.GitReadError):
            dashboard.collect_rows_at("REV", lambda args, input=None: b"not a listing\0")
        good = FakeGit(entries)
        complete = good.cat_file_output((_blob_oid(meta) + "\n").encode("ascii"))
        for broken in (b"", b"garbage\n", complete[:-8], complete[:-1] + b"X"):
            def git(args, input=None, broken=broken):
                return good.ls_tree_output() if args[0] == "ls-tree" else broken
            with self.subTest(stream=broken[:20]):
                with self.assertRaises(dashboard.GitReadError):
                    dashboard.collect_rows_at("REV", git)


class MainWritesBytesTest(TempRootCase):
    def test_the_page_is_written_with_lf_line_ends_and_no_translation(self):
        _add_result(self.root, "alpha", "alpha_m_low.html", meta={})
        real_write_text = type(self.root).write_text
        seen = []

        def spy(path, data, *args, **kwargs):
            seen.append(kwargs)
            return real_write_text(path, data, *args, **kwargs)

        with mock.patch.object(type(self.root), "write_text", spy):
            code = dashboard.main([], repo_root=self.root, out=io.StringIO(), err=io.StringIO())
        self.assertEqual(code, 0)
        # Platform newline translation is the one thing that could make two
        # machines write different bytes for the same page.
        self.assertEqual(seen, [{"encoding": "utf-8", "newline": "\n"}])
        data = (self.root / "dashboard.html").read_bytes()
        self.assertNotIn(b"\r", data)
        self.assertTrue(data.endswith(b"</html>\n"))


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class RealGitReaderTest(unittest.TestCase):
    """``collect_rows_at`` against real git in a throwaway repo (no remote)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name).resolve() / "repo"
        self.repo.mkdir()
        env = {"HOME": str(self.repo.parent), "GIT_CONFIG_GLOBAL": os.devnull,
               "GIT_CONFIG_SYSTEM": os.devnull,
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.test",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.test"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.git("init", "-q", "-b", "main")

    def git(self, *cmd, binary=False):
        done = subprocess.run(["git", *cmd], cwd=self.repo, capture_output=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout if binary else done.stdout.decode("utf-8").strip()

    def reader(self, args, input=None):
        done = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, input=input)
        if done.returncode:
            raise dashboard.GitReadError(done.stderr.decode("utf-8", "replace"))
        return done.stdout

    def test_git_tree_page_equals_the_page_main_writes_and_regenerating_changes_nothing(self):
        entries = _parity_entries()
        entries.append((b"results/.gitkeep", b""))
        _write_entries(self.repo, entries)
        # A symlink deliverable with a regular meta: not a result in either reader.
        try:
            os.symlink("p_m_low.html", self.repo / "results" / "a" / "link.html")
        except (OSError, NotImplementedError):
            pass
        (self.repo / "results" / "a" / "link.meta.json").write_text("{}")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "results")

        rows, _ = dashboard.collect_rows_at("HEAD", self.reader)
        from_git = dashboard.render(rows).encode("utf-8")

        code = dashboard.main([], repo_root=self.repo, out=io.StringIO(), err=io.StringIO())
        self.assertEqual(code, 0)
        self.assertEqual((self.repo / "dashboard.html").read_bytes(), from_git)
        self.assertNotIn("link.html", from_git.decode("utf-8"))

        # Committed, the file is exactly what a second run writes again.
        self.git("add", "dashboard.html")
        self.git("commit", "-q", "-m", "dashboard")
        code = dashboard.main([], repo_root=self.repo, out=io.StringIO(), err=io.StringIO())
        self.assertEqual(code, 0)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(self.git("show", "HEAD:dashboard.html", binary=True), from_git)

    def test_an_unknown_revision_is_a_git_read_error(self):
        self.git("commit", "-q", "--allow-empty", "-m", "empty")
        with self.assertRaises(dashboard.GitReadError):
            dashboard.collect_rows_at("no-such-rev", self.reader)
