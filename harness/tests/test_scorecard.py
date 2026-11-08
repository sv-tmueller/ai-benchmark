"""Unit tests for ``scorecard.py``: corpus scan, matrix, markdown rendering.

The scorecard matrix is built from a synthetic fixture tree under
``harness/tests/data/scorecard/`` (``prompts/`` + ``results/``) so the tests
never touch the real ``results/`` corpus.
"""

import contextlib
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from harness import scorecard

FIXTURE = Path(__file__).resolve().parent / "data" / "scorecard"
UNGRADED_HEADING = "not graded by this harness"

# Minimal graded prompt TOMLs for the synthetic corpora built inside tmp trees.
GRADED_PROMPT_TOML = """id = "p"
category = "cat-p"

[grading]
mode = "contains"
expected = "x"
"""

# Hostile nesting, past the interpreter's parser limits. Written as raw bytes
# because the correspondng Python objects would blow the stack while being
# built/serialised — the aggregator must still read the *file*.
DEEP_TOML_PROMPT = (
    b'id = "deep"\ncategory = "cat-deep"\nx = '
    + b"[" * 600
    + b"]" * 600
    + b"\n"
)
DEEP_JSON_SIDECAR = (
    b'{"prompt_id": "deep", "model": "deep", "pass": true, "d": '
    + b"[" * 12000
    + b"]" * 12000
    + b"}"
)


def write_corpus(root, prompts, sidecars=(), metas=(), raw_sidecars=()):
    """Materialise a synthetic corpus under ``root``.

    ``prompts`` maps TOML filenames to their text. ``sidecars``/``metas`` are
    ``(family, filename, payload)`` triples serialised as JSON, so a test can
    hand the aggregator a corpus that no committed fixture covers.
    ``raw_sidecars`` are ``(family, filename, bytes)`` triples written verbatim,
    for sidecars whose content cannot be produced by ``json.dumps``.
    """
    prompts_dir = root / "prompts"
    results_dir = root / "results"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    for name, text in prompts.items():
        (prompts_dir / name).write_text(text, encoding="utf-8")
    for family, name, payload in tuple(sidecars) + tuple(metas):
        directory = results_dir / family
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(json.dumps(payload), encoding="utf-8")
    for family, name, blob in raw_sidecars:
        directory = results_dir / family
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_bytes(blob)
    return results_dir, prompts_dir


def build_from(root, prompts, sidecars=(), metas=(), raw_sidecars=()):
    """Build a scorecard payload from a corpus written into ``root``."""
    results_dir, prompts_dir = write_corpus(
        root, prompts, sidecars, metas, raw_sidecars
    )
    return scorecard.build_scorecard(results_dir, prompts_dir)


def run_cli(
    root, prompts, sidecars=(), metas=(), raw_prompts=None, raw_sidecars=()
):
    """Run ``scorecard.main`` against a corpus written under ``root``.

    Returns ``(exit_code, json payload, markdown, stdout)``. The payload and
    markdown are ``None`` when the run wrote nothing — the "no outputs at all"
    failure mode the malformed-input findings describe. ``raw_prompts`` writes
    prompt files as raw bytes, for corpora no text writer can produce.
    ``raw_sidecars`` does the same for result sidecar bytes.
    """
    results_dir, prompts_dir = write_corpus(
        root, prompts, sidecars, metas, raw_sidecars
    )
    for name, blob in (raw_prompts or {}).items():
        (prompts_dir / name).write_bytes(blob)
    out_json = root / "out" / "scorecard.json"
    out_md = root / "out" / "scorecard.md"
    try:
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = scorecard.main(
                [],
                results_dir=results_dir,
                prompts_dir=prompts_dir,
                out_json=out_json,
                out_md=out_md,
            )
        out = stdout.getvalue()
    except Exception as exc:  # the abort these findings are about
        return None, None, None, "{}: {}".format(type(exc).__name__, exc)
    payload = None
    if out_json.is_file():
        payload = json.loads(out_json.read_text(encoding="utf-8"))
    markdown = out_md.read_text(encoding="utf-8") if out_md.is_file() else None
    return code, payload, markdown, out


class ScorecardTestCase(unittest.TestCase):
    """Shared setup: build the scorecard from the committed fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.scorecard = scorecard.build_scorecard(
            FIXTURE / "results", FIXTURE / "prompts"
        )
        cls.markdown = scorecard.render_markdown(cls.scorecard)

    def cell(self, model, category):
        return self.scorecard["graded"][model][category]

    def markdown_categories(self):
        """Return the matrix column names, in render order."""
        for line in self.markdown.splitlines():
            if line.startswith("| model |"):
                return [part.strip() for part in line.strip().strip("|").split("|")][1:]
        self.fail("no matrix header row in markdown")

    def markdown_data_rows(self):
        """Return ``{model: [cell, ...]}`` for the matrix data rows only."""
        rows = {}
        for line in self.markdown.splitlines():
            if not line.startswith("| ") or line.startswith("| model |"):
                continue
            if line[2:5] == "---":  # the header separator
                continue
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            rows[parts[0]] = parts[1:]
        return rows

    def total_graded(self):
        return sum(
            counts["graded"]
            for row in self.scorecard["graded"].values()
            for counts in row.values()
            if counts is not None
        )

    def total_passed(self):
        return sum(
            counts["passed"]
            for row in self.scorecard["graded"].values()
            for counts in row.values()
            if counts is not None
        )


class MatrixShapeTests(ScorecardTestCase):
    def test_pass_rate_counts_passed_out_of_graded(self):
        self.assertEqual(self.cell("m1", "cat-alpha"), {"passed": 1, "graded": 1})
        self.assertEqual(self.cell("m2", "cat-alpha"), {"passed": 0, "graded": 1})

    def test_categories_come_from_prompt_toml_not_directory_names(self):
        # results live in alpha-dir/beta-dir/...; TOML categories are cat-*.
        self.assertEqual(
            sorted(self.scorecard["graded"]),
            ["m-delta", "m1", "m2", "vllm/qsu/m9-route"],
        )
        self.assertEqual(sorted(self.cell("m1", "cat-alpha")), ["graded", "passed"])
        # A category with no graded verdict still renders as a column (the
        # column set comes from the prompt TOMLs, not from the verdicts).
        self.assertIn("cat-epsilon", self.scorecard["graded"]["m1"])

    def test_model_with_no_verdicts_gets_no_row(self):
        # alpha_m3.md has a result but no sidecar and no meta grading verdict.
        for category in self.scorecard["graded"].get("m3", {}):
            self.fail("m3 must not appear as a row (category {!r})".format(category))
        self.assertNotIn("m3", self.scorecard["graded"])

    def test_empty_cell_is_null_in_json_never_zero_percent(self):
        self.assertIsNone(self.cell("m1", "cat-delta"))
        self.assertIsNone(self.cell("m2", "cat-beta"))
        for counts in self.scorecard["graded"]["m1"].values():
            if counts is None:
                continue
            self.assertNotIn(0, [counts["passed"], counts["graded"]])

    def test_missing_cell_renders_as_em_dash_in_markdown(self):
        # Pin the assertion to the specific matrix row/cell: find the data row
        # for m1, locate the cat-epsilon column, and require that exact cell to
        # be the em dash. (Asserting "—" anywhere in the blob is vacuous: the
        # H1 title and the Method paragraph already contain em dashes.)
        categories = self.markdown_categories()
        self.assertEqual(categories.count("cat-epsilon"), 1)
        index = categories.index("cat-epsilon")
        rows = self.markdown_data_rows()
        self.assertIn("m1", rows)
        self.assertEqual(rows["m1"][index], "—")
        # The corresponding JSON cell is null, and the neighbouring graded cell
        # in the same row is a real count — so the em dash is the empty cell,
        # not a broken renderer.
        self.assertIsNone(self.cell("m1", "cat-epsilon"))
        alpha = categories.index("cat-alpha")
        self.assertEqual(rows["m1"][alpha], "1/1")


class AssociationTests(ScorecardTestCase):
    def test_prompt_id_wins_over_directory_name(self):
        # cat-alpha is reachable only through prompt_id, never "alpha-dir".
        self.assertIn("cat-alpha", self.scorecard["graded"]["m1"])
        self.assertNotIn("alpha-dir", json.dumps(self.scorecard))

    def test_sidecar_wins_over_legacy_meta_for_the_same_stem(self):
        # alpha_m2 has a legacy meta verdict (pass) and a sidecar (fail);
        # the sidecar is the winner.
        self.assertEqual(self.cell("m2", "cat-alpha"), {"passed": 0, "graded": 1})

    def test_legacy_meta_grading_verdict_counts_when_no_sidecar(self):
        # legacy_m9 has only a meta grading verdict (pass) and no sidecar;
        # the row key is the meta's full route string, verbatim.
        self.assertEqual(
            self.cell("vllm/qsu/m9-route", "cat-alpha"), {"passed": 1, "graded": 1}
        )

    def test_playability_meta_verdict_counts_via_paired_sidecar(self):
        self.assertEqual(self.cell("m1", "cat-beta"), {"passed": 1, "graded": 1})

    def test_legacy_meta_null_grading_is_not_a_fail(self):
        # epsilon carries "grading": null and gets no verdict at all.
        self.assertNotIn("epsilon_glm_5_3_flash", json.dumps(self.scorecard["graded"]))

    def test_legacy_meta_null_grading_yields_no_row_and_no_counted_cell(self):
        # gamma_m4.meta.json carries a real (gradable) prompt but "grading":
        # null. It must contribute no row key and no counted cell anywhere.
        self.assertNotIn("vllm/qsu/gamma-null-route", self.scorecard["graded"])
        self.assertNotIn("gamma-null-route", json.dumps(self.scorecard["graded"]))
        self.assertNotIn("gamma-null-route", self.markdown)
        # Nothing from this meta leaks into the totals either.
        self.assertEqual(self.total_graded(), 6)
        self.assertEqual(self.total_passed(), 4)

    def test_model_row_key_is_the_winning_source_string_verbatim(self):
        # The legacy meta for weirdname_m1 carries a full route id, but its
        # sidecar wins with the short tag — no normalization either way.
        self.assertIn("m1", self.scorecard["graded"])


class GradabilityTests(ScorecardTestCase):
    def test_ungraded_prompts_are_listed_explicitly(self):
        self.assertIn("epsilon-prompt", self.scorecard["ungraded_prompts"])
        self.assertIn(UNGRADED_HEADING, self.markdown.lower())

    def test_ungraded_results_are_excluded_from_matrix_and_denominators(self):
        # epsilon-prompt has a [grading]-less TOML, but epsilon-dir carries a
        # *verdict sidecar* for it (a stray verdict on a prompt the harness
        # cannot grade). That verdict must be excluded from both the numerator
        # and the denominator: no epsilon row key, no counted cell, and the
        # corpus totals below must not move because of it.
        self.assertNotIn("epsilon-prompt", json.dumps(self.scorecard["graded"]))
        for row in self.scorecard["graded"].values():
            self.assertIsNone(row.get("cat-epsilon"))
        # The stray sidecar is the only verdict whose prompt_id is ungraded;
        # if it were counted, the totals would be inflated by exactly one and
        # m1's cat-epsilon cell would become a count instead of null.
        self.assertEqual(self.total_graded(), 6)
        self.assertTrue(self.scorecard["ungraded_prompts"])
        rows = self.markdown_data_rows()
        categories = self.markdown_categories()
        epsilon = categories.index("cat-epsilon")
        for model, cells in rows.items():
            self.assertEqual(
                cells[epsilon], "—",
                "ungraded column must be empty for {!r}".format(model),
            )

    def test_prompt_with_playability_meta_counts_as_gradable(self):
        # beta.toml has no [grading] block, but its result meta carries a
        # playability verdict, mirroring grade.py's gradability rule.
        self.assertNotIn("beta-prompt", self.scorecard["ungraded_prompts"])

    def test_fixtures_toml_is_skipped_entirely(self):
        self.assertNotIn("zeta-prompt", self.scorecard["ungraded_prompts"])
        self.assertNotIn("cat-zeta", json.dumps(self.scorecard["graded"]))

    def test_ungraded_prompt_never_becomes_a_zero_cell(self):
        # cat-epsilon may be a column, but its cells must all be em dashes —
        # never "0/0" or a 0% rate.
        for line in self.markdown.splitlines():
            if line.startswith("| m") or line.startswith("| vllm"):
                self.assertNotIn("0/0", line)


class CompositeIndexTests(ScorecardTestCase):
    def test_no_composite_index_number_appears_anywhere(self):
        blob = self.markdown + json.dumps(self.scorecard)
        self.assertNotIn("%", blob)
        for banned in ("overall", "composite", "index", "average", "total score"):
            self.assertNotIn(banned, blob.lower())


class MarkdownStyleTests(ScorecardTestCase):
    def test_markdown_has_title_method_header_and_matrix(self):
        self.assertTrue(self.markdown.startswith("# "))
        self.assertIn("**", self.markdown)
        self.assertIn("## Method", self.markdown)
        self.assertIn("|", self.markdown)

    def test_markdown_lists_every_ungraded_prompt(self):
        for prompt_id in self.scorecard["ungraded_prompts"]:
            self.assertIn(prompt_id, self.markdown)


class MalformedVerdictTests(unittest.TestCase):
    """A bad verdict is skipped gracefully, never a crash and never coerced."""

    def test_non_scalar_prompt_id_is_skipped_not_a_crash(self):
        # Finding 1: a sidecar whose prompt_id is a list used to raise
        # TypeError: unhashable type and abort the whole run, writing nothing.
        with tempfile.TemporaryDirectory() as tmp:
            score = build_from(
                Path(tmp),
                {"p.toml": GRADED_PROMPT_TOML},
                sidecars=[
                    (
                        "d",
                        "good_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": True},
                    ),
                    (
                        "d",
                        "bad_grading.json",
                        {"prompt_id": ["p"], "model": "m", "pass": True},
                    ),
                ],
            )
            self.assertEqual(score["graded"]["m"]["cat-p"], {"passed": 1, "graded": 1})

    def test_non_scalar_model_is_skipped_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            score = build_from(
                Path(tmp),
                {"p.toml": GRADED_PROMPT_TOML},
                sidecars=[
                    (
                        "d",
                        "good_grading.json",
                        {"prompt_id": "p", "model": "m2", "pass": True},
                    ),
                    (
                        "d",
                        "bad_grading.json",
                        {"prompt_id": "p", "model": {"x": 1}, "pass": True},
                    ),
                ],
            )
            self.assertEqual(sorted(score["graded"]), ["m2"])
            self.assertEqual(score["graded"]["m2"]["cat-p"], {"passed": 1, "graded": 1})

    def test_non_scalar_prompt_id_in_legacy_meta_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            score = build_from(
                Path(tmp),
                {"p.toml": GRADED_PROMPT_TOML},
                metas=[
                    (
                        "d",
                        "bad.meta.json",
                        {
                            "prompt_id": ["p"],
                            "model": "m",
                            "grading": {"pass": True},
                        },
                    )
                ],
            )
            self.assertEqual(score["graded"], {})

    def test_unhashable_verdict_does_not_stop_a_full_cli_run(self):
        # The CLI must still exit 0 and write both outputs when one sidecar in
        # the corpus is unhashable.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_json = root / "out" / "scorecard.json"
            out_md = root / "out" / "scorecard.md"
            results_dir, prompts_dir = write_corpus(
                root,
                {"p.toml": GRADED_PROMPT_TOML},
                sidecars=[
                    (
                        "d",
                        "good_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": False},
                    ),
                    (
                        "d",
                        "bad_grading.json",
                        {"prompt_id": ["p"], "model": "m", "pass": True},
                    ),
                ],
            )
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = scorecard.main(
                    [],
                    results_dir=results_dir,
                    prompts_dir=prompts_dir,
                    out_json=out_json,
                    out_md=out_md,
                )
            self.assertEqual(code, 0, stdout.getvalue())
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())


class NonBoolPassTests(unittest.TestCase):
    """A verdict's ``pass`` must be a real bool — never coerced with bool()."""

    def build_with_pass(self, value):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return build_from(
            Path(tmp.name),
            {"p.toml": GRADED_PROMPT_TOML},
            sidecars=[
                (
                    "d",
                    "v_grading.json",
                    {"prompt_id": "p", "model": "m", "pass": value},
                )
            ],
        )

    def test_string_false_is_rejected_not_recorded_as_a_pass(self):
        # Finding 2: bool("false") is True, so this used to record a PASS.
        score = self.build_with_pass("false")
        self.assertEqual(score["graded"], {})

    def test_null_pass_is_rejected(self):
        # bool(None) is False, so this used to silence a fail into a verdict.
        score = self.build_with_pass(None)
        self.assertEqual(score["graded"], {})

    def test_empty_list_pass_is_rejected(self):
        score = self.build_with_pass([])
        self.assertEqual(score["graded"], {})

    def test_string_true_is_also_rejected(self):
        score = self.build_with_pass("true")
        self.assertEqual(score["graded"], {})

    def test_non_bool_legacy_meta_pass_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            score = build_from(
                Path(tmp),
                {"p.toml": GRADED_PROMPT_TOML},
                metas=[
                    (
                        "d",
                        "v.meta.json",
                        {
                            "prompt_id": "p",
                            "model": "m",
                            "grading": {"pass": "false"},
                        },
                    )
                ],
            )
            self.assertEqual(score["graded"], {})

    def test_real_bools_still_count(self):
        # The guard must not throw out genuine verdicts: true passes, false
        # fails, and both stay in the denominator.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        score = build_from(
            Path(tmp.name),
            {"p.toml": GRADED_PROMPT_TOML},
            sidecars=[
                (
                    "d",
                    "yes_grading.json",
                    {"prompt_id": "p", "model": "m", "pass": True},
                ),
                (
                    "d",
                    "no_grading.json",
                    {"prompt_id": "p", "model": "m", "pass": False},
                ),
            ],
        )
        self.assertEqual(score["graded"]["m"]["cat-p"], {"passed": 1, "graded": 2})


class PromptTomlCategoryTests(unittest.TestCase):
    """A prompt TOML's ``category`` is untrusted input: normalize or skip it.

    These pin the prompt-TOML half of the malformed-input crash class (round-2
    findings 1-2). The column set and its sort must route through the same
    scalar-string normalization the verdict keys already use, so a non-scalar
    or mixed-type ``category`` can never reach ``sorted()``.
    """

    def test_non_scalar_category_is_skipped_not_a_crash(self):
        # Finding 1: category = ["c"] used to raise TypeError: unhashable
        # type: 'list' at the column set, aborting the run and writing nothing.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _markdown, out = run_cli(
                Path(tmp),
                {"p.toml": 'id = "p"\ncategory = ["c"]\n[user]\ntext = "x"\n'},
            )
            self.assertEqual(code, 0, out)
            self.assertEqual(payload["graded"], {})
            self.assertNotIn("c", json.dumps(payload["graded"]))

    def test_dict_category_is_skipped_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _markdown, out = run_cli(
                Path(tmp),
                {"p.toml": 'id = "p"\ncategory = {a = 1}\n[user]\ntext = "x"\n'},
            )
            self.assertEqual(code, 0, out)
            self.assertEqual(payload["graded"], {})

    def test_mixed_type_category_pair_does_not_break_the_column_sort(self):
        # Finding 2: an int category next to a str one used to raise
        # TypeError: '<' not supported between 'int' and 'str' at the column
        # sort. Only the string category may survive as a column.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _markdown, out = run_cli(
                Path(tmp),
                {
                    "p.toml": GRADED_PROMPT_TOML,
                    "q.toml": 'id = "q"\ncategory = 7\n[user]\ntext = "y"\n',
                },
                sidecars=[
                    (
                        "d",
                        "p_m1_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": True},
                    ),
                    (
                        "d",
                        "q_m1_grading.json",
                        {"prompt_id": "q", "model": "m", "pass": True},
                    ),
                ],
            )
            self.assertEqual(code, 0, out)
            self.assertEqual(
                payload["graded"], {"m": {"cat-p": {"passed": 1, "graded": 1}}}
            )

    def test_int_category_alone_is_not_a_column(self):
        # A gradable prompt with an int category: today that category becomes
        # a column keyed 7 and the verdict is counted under it — a column that
        # is not a category string. Normalization must drop both.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, markdown, out = run_cli(
                Path(tmp),
                {
                    "p.toml": 'id = "p"\ncategory = 7\n[grading]\nmode = "contains"\n[user]\ntext = "x"\n',
                },
                sidecars=[
                    (
                        "d",
                        "p_m1_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": True},
                    )
                ],
            )
            self.assertEqual(code, 0, out)
            self.assertEqual(payload["graded"], {})
            self.assertNotIn("| 7 ", markdown)

    def test_string_categories_still_form_sorted_columns(self):
        # The normalization must keep the normal case: string categories are
        # columns, in sorted order.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, markdown, out = run_cli(
                Path(tmp),
                {
                    "a.toml": 'id = "a"\ncategory = "cat-b"\n[grading]\nmode = "contains"\n[user]\ntext = "x"\n',
                    "b.toml": 'id = "b"\ncategory = "cat-a"\n[grading]\nmode = "contains"\n[user]\ntext = "x"\n',
                },
                sidecars=[
                    (
                        "d",
                        "a_m1_grading.json",
                        {"prompt_id": "a", "model": "m", "pass": True},
                    ),
                    (
                        "d",
                        "b_m1_grading.json",
                        {"prompt_id": "b", "model": "m", "pass": True},
                    ),
                ],
            )
            self.assertEqual(code, 0, out)
            for line in markdown.splitlines():
                if line.startswith("| model |"):
                    self.assertEqual(
                        [part.strip() for part in line.strip().strip("|").split("|")],
                        ["model", "cat-a", "cat-b"],
                    )
                    break
            else:
                self.fail("no matrix header row in markdown")


class PromptTomlIdTests(unittest.TestCase):
    """A prompt TOML's ``id`` is untrusted input too: a non-scalar skips it."""

    def test_non_scalar_id_is_skipped_not_a_crash(self):
        # Finding 3: id = ["p"] raised TypeError: unhashable type: 'list' at
        # load time, before any verdict was read.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _markdown, out = run_cli(
                Path(tmp),
                {"p.toml": 'id = ["p"]\ncategory = "cat-p"\n[user]\ntext = "x"\n'},
            )
            self.assertEqual(code, 0, out)
            self.assertEqual(payload["graded"], {})

    def test_non_scalar_id_does_not_brick_a_verdictless_corpus(self):
        # No sidecars and no metas: this must still exit 0 and write outputs.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _markdown, out = run_cli(
                Path(tmp),
                {"p.toml": 'id = ["p"]\ncategory = "cat-p"\n[user]\ntext = "x"\n'},
            )
            self.assertEqual(code, 0, out)
            self.assertIsNotNone(payload)
            self.assertEqual(payload["graded"], {})

    def test_non_string_id_is_skipped(self):
        # id = 5 is not a usable string prompt key either.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _markdown, out = run_cli(
                Path(tmp),
                {"p.toml": 'id = 5\ncategory = "cat-p"\n[user]\ntext = "x"\n'},
            )
            self.assertEqual(code, 0, out)
            self.assertEqual(payload["graded"], {})

    def test_good_prompts_survive_a_bad_sibling_id(self):
        # One unreadable prompt must not take the readable ones with it.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _markdown, out = run_cli(
                Path(tmp),
                {
                    "bad.toml": 'id = ["p"]\ncategory = "cat-x"\n[user]\ntext = "x"\n',
                    "good.toml": GRADED_PROMPT_TOML,
                },
                sidecars=[
                    (
                        "d",
                        "p_m1_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": True},
                    )
                ],
            )
            self.assertEqual(code, 0, out)
            self.assertEqual(
                payload["graded"], {"m": {"cat-p": {"passed": 1, "graded": 1}}}
            )


class UnparseablePromptTests(unittest.TestCase):
    """A prompt TOML that cannot be read is skipped, never a crash."""

    def test_unparseable_prompt_toml_is_skipped_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _markdown, out = run_cli(
                Path(tmp),
                {"p.toml": 'id = "p\n', "good.toml": GRADED_PROMPT_TOML},
                sidecars=[
                    (
                        "d",
                        "p_m1_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": True},
                    )
                ],
            )
            self.assertEqual(code, 0, out)
            self.assertEqual(
                payload["graded"], {"m": {"cat-p": {"passed": 1, "graded": 1}}}
            )

    def test_invalid_utf8_prompt_toml_is_skipped_gracefully(self):
        # tomllib decodes without a BOM as UTF-8, so a stray non-UTF-8 byte
        # raises UnicodeDecodeError — a sibling of the TOMLDecodeError path.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _markdown, out = run_cli(
                Path(tmp),
                {"good.toml": GRADED_PROMPT_TOML},
                sidecars=[
                    (
                        "d",
                        "p_m1_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": True},
                    )
                ],
                raw_prompts={
                    "bad.toml": b'id = "bad"\ncategory = "cat-bad"\n\xff\xfe\n'
                },
            )
            self.assertEqual(code, 0, out)
            self.assertEqual(
                payload["graded"], {"m": {"cat-p": {"passed": 1, "graded": 1}}}
            )


class HostileNestingTests(unittest.TestCase):
    """Over-deep untrusted input is skipped, never a crash.

    Round-3 findings: ``tomllib.load``/``json.loads`` raise ``RecursionError``
    (a ``RuntimeError`` subclass, not the ``ValueError`` family the earlier
    catches enumerated) once nesting passes the interpreter's parser limit.
    The lesson: enumerate what the parser can raise on hostile bytes — not the
    exception types the last finding happened to name — so every escape is
    inside a graceful-skip catch.
    """

    def test_deeply_nested_prompt_toml_is_skipped_never_a_crash(self):
        # Finding 1: a prompt TOML nested ~497+ levels deep raised
        # RecursionError out of load_prompts, aborting the run exit 1 with no
        # outputs. Expected: the prompt is skipped, the run exits 0.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _markdown, out = run_cli(
                Path(tmp),
                {"good.toml": GRADED_PROMPT_TOML},
                sidecars=[
                    (
                        "d",
                        "p_m1_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": True},
                    )
                ],
                raw_prompts={"deep.toml": DEEP_TOML_PROMPT},
            )
            self.assertEqual(code, 0, out)
            self.assertIsNotNone(payload, "the run aborted without writing the JSON")
            # The skipped prompt contributes nothing, and the good one survives.
            self.assertEqual(
                payload["graded"], {"m": {"cat-p": {"passed": 1, "graded": 1}}}
            )
            self.assertNotIn("deep", payload["ungraded_prompts"])

    def test_deeply_nested_json_sidecar_is_skipped_never_a_crash(self):
        # Finding 2: a sidecar with a ~9997-deep nested array raised
        # RecursionError out of _read_json -> exit 1, no outputs. Expected: the
        # sidecar is skipped like any other unreadable one, run exits 0.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_json = root / "out" / "scorecard.json"
            out_md = root / "out" / "scorecard.md"
            results_dir, prompts_dir = write_corpus(
                root,
                {"p.toml": GRADED_PROMPT_TOML},
                sidecars=[
                    (
                        "d",
                        "good_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": True},
                    )
                ],
                raw_sidecars=[("d", "deep_grading.json", DEEP_JSON_SIDECAR)],
            )
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = scorecard.main(
                    [],
                    results_dir=results_dir,
                    prompts_dir=prompts_dir,
                    out_json=out_json,
                    out_md=out_md,
                )
            self.assertEqual(code, 0, stdout.getvalue())
            self.assertTrue(out_json.is_file(), "the run wrote no JSON output")
            self.assertTrue(out_md.is_file(), "the run wrote no markdown output")
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["graded"], {"m": {"cat-p": {"passed": 1, "graded": 1}}}
            )

    def test_over_long_integer_prompt_is_skipped_never_a_crash(self):
        # Same class, third escape: tomllib raises a bare ValueError (the
        # 4300-digit int-conversion limit) that is NOT a TOMLDecodeError or
        # UnicodeDecodeError — so the old tuple let it abort the run too.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _markdown, out = run_cli(
                Path(tmp),
                {"good.toml": GRADED_PROMPT_TOML},
                sidecars=[
                    (
                        "d",
                        "p_m1_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": True},
                    )
                ],
                raw_prompts={
                    "big.toml": b'id = "p"\nx = ' + b"9" * 5000 + b"\n"
                },
            )
            self.assertEqual(code, 0, out)
            self.assertIsNotNone(payload, "the run aborted without writing the JSON")
            self.assertEqual(
                payload["graded"], {"m": {"cat-p": {"passed": 1, "graded": 1}}}
            )

    def test_deep_prompt_does_not_stop_build_scorecard(self):
        # The library entry point must be robust too, not just the CLI.
        with tempfile.TemporaryDirectory() as tmp:
            score = build_from(
                Path(tmp),
                {"good.toml": GRADED_PROMPT_TOML},
                sidecars=[
                    (
                        "d",
                        "p_m1_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": False},
                    )
                ],
                raw_sidecars=[("d", "deep_grading.json", DEEP_JSON_SIDECAR)],
            )
            self.assertEqual(
                score["graded"], {"m": {"cat-p": {"passed": 0, "graded": 1}}}
            )


class UnencodableKeyTests(unittest.TestCase):
    """A key that cannot be encoded as UTF-8 is unusable: skip it, never abort.

    Round-4 finding: ``json.loads`` accepts a lone surrogate escape
    (``"\\ud800"``) while ``tomllib`` rejects it, so the value survived the
    read-time guards, became a row key, and only failed at the *write* site —
    ``out_json`` was written while ``UnicodeEncodeError`` left ``out_md`` at
    0 bytes (exit 1, inconsistent partial outputs). The boundary guard must
    reject any key string that cannot be UTF-8 encoded, so the verdict is
    skipped like any other unusable value and both outputs stay consistent.
    """

    def run_corpus(self, root, sidecars=(), metas=()):
        return run_cli(
            root, {"p.toml": GRADED_PROMPT_TOML}, sidecars=sidecars, metas=metas
        )

    def markdown_rows(self, markdown):
        """Return the matrix row keys, in render order."""
        rows = []
        for line in markdown.splitlines():
            if not line.startswith("| ") or line.startswith("| model |"):
                continue
            if line[2:5] == "---":  # the header separator
                continue
            rows.append(line.strip().strip("|").split("|")[0].strip())
        return rows

    def assert_consistent_outputs(self, payload, markdown, out):
        """Both outputs are written, non-empty, and describe the same rows."""
        self.assertIsNotNone(payload, out)
        self.assertIsNotNone(markdown, out)
        self.assertTrue(markdown, "out.md was written but left empty: " + out)
        self.assertEqual(
            self.markdown_rows(markdown),
            sorted(payload["graded"]),
            "the markdown rows and the JSON row keys must agree: " + out,
        )

    def test_lone_surrogate_model_in_sidecar_does_not_abort_the_run(self):
        # The exact round-4 trigger: a sidecar whose model is "\ud800" aborted
        # at write_outputs after out.json had already been flushed.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, markdown, out = self.run_corpus(
                Path(tmp),
                sidecars=[
                    (
                        "d",
                        "good_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": True},
                    ),
                    (
                        "d",
                        "bad_grading.json",
                        {"prompt_id": "p", "model": "\ud800", "pass": True},
                    ),
                ],
            )
            self.assertEqual(code, 0, out)
            self.assert_consistent_outputs(payload, markdown, out)
            self.assertEqual(
                payload["graded"], {"m": {"cat-p": {"passed": 1, "graded": 1}}}
            )
            # The unencodable key is gone from the payload, not merely escaped
            # into it: json.dumps would render a surviving surrogate as the
            # six-character sequence \ud800.
            self.assertNotIn("\\ud800", json.dumps(payload))

    def test_lone_surrogate_model_in_legacy_meta_does_not_abort_the_run(self):
        # Same class through the legacy .meta.json grading path.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, markdown, out = self.run_corpus(
                Path(tmp),
                metas=[
                    (
                        "d",
                        "good.meta.json",
                        {"prompt_id": "p", "model": "m", "grading": {"pass": True}},
                    ),
                    (
                        "d",
                        "bad.meta.json",
                        {
                            "prompt_id": "p",
                            "model": "\ud800",
                            "grading": {"pass": True},
                        },
                    ),
                ],
            )
            self.assertEqual(code, 0, out)
            self.assert_consistent_outputs(payload, markdown, out)
            self.assertEqual(
                payload["graded"], {"m": {"cat-p": {"passed": 1, "graded": 1}}}
            )
            self.assertNotIn("\\ud800", json.dumps(payload))

    def test_lone_surrogate_prompt_id_is_skipped_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, markdown, out = self.run_corpus(
                Path(tmp),
                sidecars=[
                    (
                        "d",
                        "good_grading.json",
                        {"prompt_id": "p", "model": "m", "pass": True},
                    ),
                    (
                        "d",
                        "bad_grading.json",
                        {"prompt_id": "\ud800", "model": "m", "pass": True},
                    ),
                ],
            )
            self.assertEqual(code, 0, out)
            self.assert_consistent_outputs(payload, markdown, out)
            self.assertEqual(
                payload["graded"], {"m": {"cat-p": {"passed": 1, "graded": 1}}}
            )

    def test_corpus_of_only_unencodable_keys_still_writes_both_outputs(self):
        # No salvageable verdict at all: the matrix is empty, but both files
        # must still be written and consistent (never a 0-byte out.md).
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, markdown, out = self.run_corpus(
                Path(tmp),
                sidecars=[
                    (
                        "d",
                        "bad_grading.json",
                        {"prompt_id": "p", "model": "\ud800", "pass": True},
                    )
                ],
            )
            self.assertEqual(code, 0, out)
            self.assert_consistent_outputs(payload, markdown, out)
            self.assertEqual(payload["graded"], {})
            self.assertIn(UNGRADED_HEADING, markdown.lower())

    def test_astral_model_key_still_counts(self):
        # The guard must reject only *unpaired* surrogates: a legitimate
        # astral-plane character (written as a JSON surrogate pair, decoded by
        # json.loads to one scalar) is encodable and stays verbatim.
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, markdown, out = self.run_corpus(
                Path(tmp),
                sidecars=[
                    (
                        "d",
                        "emoji_grading.json",
                        {"prompt_id": "p", "model": "\U0001f600", "pass": True},
                    )
                ],
            )
            self.assertEqual(code, 0, out)
            self.assert_consistent_outputs(payload, markdown, out)
            self.assertEqual(
                payload["graded"], {"\U0001f600": {"cat-p": {"passed": 1, "graded": 1}}}
            )

    def test_boundary_guards_reject_unencodable_key_strings(self):
        # The predicate itself: what TOML cannot even produce (its decoder
        # rejects lone surrogates) must still be rejected at the key boundary.
        for bad in ("\ud800", "a\ud800b", "\udfff"):
            self.assertIsNone(scorecard._as_vendor_key(bad), repr(bad))
            self.assertIsNone(scorecard._as_category(bad), repr(bad))
        # ...while an ordinary non-ASCII key is encodable and survives intact.
        self.assertEqual(
            scorecard._as_vendor_key("münchen/モデル"), "münchen/モデル"
        )
        self.assertEqual(scorecard._as_category("katégorie"), "katégorie")


class CliTests(unittest.TestCase):
    def test_exit_zero_run_writes_both_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results_dir = root / "results"
            prompts_dir = root / "prompts"
            out_json = root / "out" / "scorecard.json"
            out_md = root / "out" / "scorecard.md"
            shutil.copytree(FIXTURE / "results", results_dir)
            shutil.copytree(FIXTURE / "prompts", prompts_dir)
            out_json.parent.mkdir(parents=True)

            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = scorecard.main(
                    [],
                    results_dir=results_dir,
                    prompts_dir=prompts_dir,
                    out_json=out_json,
                    out_md=out_md,
                )

            self.assertEqual(code, 0, stdout.getvalue())
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(sorted(payload), ["generated_utc", "graded", "ungraded_prompts"])

    def test_default_paths_point_at_repo_results_and_prompts(self):
        self.assertEqual(
            scorecard.DEFAULT_OUT_JSON.name, "scorecard.json"
        )
        self.assertEqual(
            scorecard.DEFAULT_RESULTS_DIR.name, "results"
        )
        self.assertEqual(
            scorecard.DEFAULT_PROMPTS_DIR.name, "prompts"
        )
        self.assertTrue(re.search(r"graded|scorecard", scorecard.__doc__ or ""))


if __name__ == "__main__":
    unittest.main()
