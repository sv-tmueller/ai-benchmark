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
        self.assertIn("—", self.markdown)


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

    def test_model_row_key_is_the_winning_source_string_verbatim(self):
        # The legacy meta for weirdname_m1 carries a full route id, but its
        # sidecar wins with the short tag — no normalization either way.
        self.assertIn("m1", self.scorecard["graded"])


class GradabilityTests(ScorecardTestCase):
    def test_ungraded_prompts_are_listed_explicitly(self):
        self.assertIn("epsilon-prompt", self.scorecard["ungraded_prompts"])
        self.assertIn(UNGRADED_HEADING, self.markdown.lower())

    def test_ungraded_results_are_excluded_from_matrix_and_denominators(self):
        # No prompt id leaks into the matrix, and no ungraded result is ever
        # counted: the cat-epsilon column has an em-dash cell for every model.
        self.assertNotIn("epsilon-prompt", json.dumps(self.scorecard["graded"]))
        for row in self.scorecard["graded"].values():
            self.assertIsNone(row.get("cat-epsilon"))

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
