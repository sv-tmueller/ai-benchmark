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


def write_corpus(root, prompts, sidecars=(), metas=()):
    """Materialise a synthetic corpus under ``root``.

    ``prompts`` maps TOML filenames to their text. ``sidecars``/``metas`` are
    ``(family, filename, payload)`` triples serialised as JSON, so a test can
    hand the aggregator a corpus that no committed fixture covers.
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
    return results_dir, prompts_dir


def build_from(root, prompts, sidecars=(), metas=()):
    """Build a scorecard payload from a corpus written into ``root``."""
    results_dir, prompts_dir = write_corpus(root, prompts, sidecars, metas)
    return scorecard.build_scorecard(results_dir, prompts_dir)


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
