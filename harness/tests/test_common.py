"""Unit tests for the helpers shared by the grading modes.

D1a pins model-id derivation to the prompt's ``file_prefix`` (with the
prompt id as fallback), not the results-directory name — prefixes and
directory names diverge from prompt ids across the corpus.
"""

import unittest
from pathlib import Path

from harness.modes._common import EFFORT_LEVELS, derive_model, model_tag, run_tag, session_effort


class DeriveModelTest(unittest.TestCase):
    def test_file_prefix_is_used_when_it_diverges_from_the_prompt_id(self):
        prompt = {"id": "probe-follow-spec", "file_prefix": "follow-spec"}
        result = Path("results/probe-follow-spec/follow-spec_glm_5_3_flash.txt")

        self.assertEqual(derive_model(result, prompt), "glm_5_3_flash")

    def test_servicenow_catalog_stories_divergent_prefix(self):
        prompt = {
            "id": "servicenow-loaner-request",
            "file_prefix": "servicenow-loaner-stories",
        }
        result = Path(
            "results/servicenow/servicenow-catalog-stories_glm_5_3_flash.md"
        )

        self.assertEqual(derive_model(result, prompt), "glm_5_3_flash")

    def test_falls_back_to_the_prompt_id_when_no_file_prefix_is_declared(self):
        prompt = {"id": "math-addition"}
        result = Path("results/math-addition/math-addition_glm_5_3_flash.txt")

        self.assertEqual(derive_model(result, prompt), "glm_5_3_flash")

    def test_falls_back_to_the_first_underscore_when_nothing_matches(self):
        prompt = {"id": "game-melon-jelly"}
        result = Path("results/melon-jelly/melon-jelly_glm_5_3_flash.html")

        self.assertEqual(derive_model(result, prompt), "glm_5_3_flash")

    def test_model_keeps_embedded_underscores_and_name_suffixes(self):
        prompt = {"id": "melon-jelly", "file_prefix": "melon-jelly"}
        result = Path("results/melon-jelly/melon-jelly_claude_haiku_5_5-v2.html")

        self.assertEqual(derive_model(result, prompt), "claude_haiku_5_5-v2")

    def test_returns_empty_string_when_the_stem_has_no_underscore(self):
        prompt = {"id": "solo"}
        result = Path("results/solo/zebra.txt")

        self.assertEqual(derive_model(result, prompt), "")


class ModelTagTest(unittest.TestCase):
    def test_fable_id_becomes_underscore_tag(self):
        self.assertEqual(model_tag("claude-fable-5-2"), "claude_fable_5_2")

    def test_trailing_date_stamp_is_dropped(self):
        self.assertEqual(model_tag("claude-haiku-4-5-20251001"), "claude_haiku_4_5")

    def test_trailing_bracket_suffix_is_dropped(self):
        self.assertEqual(model_tag("claude-opus-4-8[1m]"), "claude_opus_4_8")

    def test_case_is_folded_and_separators_collapse(self):
        self.assertEqual(model_tag("  GLM.5//Flash "), "glm_5_flash")

    def test_unusable_id_raises_value_error(self):
        for bad in ("", "5-2", "---"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    model_tag(bad)


class EffortTest(unittest.TestCase):
    def test_session_effort_returns_every_known_level(self):
        for level in EFFORT_LEVELS:
            with self.subTest(level=level):
                self.assertEqual(session_effort({"CLAUDE_EFFORT": level}), level)

    def test_session_effort_never_defaults(self):
        for environ in ({}, {"CLAUDE_EFFORT": ""}, {"CLAUDE_EFFORT": "ultra"}, {"CLAUDE_EFFORT": "High"}):
            with self.subTest(environ=environ):
                with self.assertRaises(ValueError) as caught:
                    session_effort(environ)
                self.assertIn("CLAUDE_EFFORT", str(caught.exception))

    def test_run_tag_is_the_model_tag_then_the_effort(self):
        self.assertEqual(run_tag("claude-fable-5-2[1m]", "xhigh"), "claude_fable_5_2_xhigh")

    def test_run_tag_rejects_an_unknown_effort_or_model(self):
        for model, effort in (("claude-fable-5-2", "ultra"), ("claude-fable-5-2", ""), ("---", "high")):
            with self.subTest(model=model, effort=effort):
                with self.assertRaises(ValueError):
                    run_tag(model, effort)

    def test_derive_model_gives_the_run_tag_back(self):
        result = Path("results/melon-jelly/melon-jelly_%s.html" % run_tag("claude-fable-5-2", "high"))
        self.assertEqual(derive_model(result, {"id": "game-melon-jelly", "file_prefix": "melon-jelly"}),
                         "claude_fable_5_2_high")


if __name__ == "__main__":
    unittest.main()
