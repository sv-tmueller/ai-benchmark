"""Unit tests for harness.modes.python_exec (mode string "python-exec")."""

import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.modes import python_exec  # noqa: E402

DATA = Path(__file__).resolve().parent / "data" / "code-flatten-list"
PROMPT_TOML = ROOT / "prompts" / "code-flatten-list.toml"
REAL_RESULT = ROOT / "results" / "code-flatten-list" / "code-flatten-list_glm_5_3_flash.md"


def load_prompt():
    with open(PROMPT_TOML, "rb") as fh:
        return tomllib.load(fh)


class GradePythonExecTests(unittest.TestCase):
    def test_valid_submission_passes_and_reports_schema(self):
        verdict = python_exec.grade(DATA / "code-flatten-list_test_model.md", {}, load_prompt())

        self.assertEqual(
            sorted(verdict), ["detail", "mode", "model", "pass", "prompt_id"]
        )
        self.assertEqual(verdict["prompt_id"], "code-python-function")
        self.assertEqual(verdict["mode"], "python-exec")
        self.assertEqual(verdict["model"], "test_model")
        self.assertIs(verdict["pass"], True)
        self.assertIsInstance(verdict["detail"], str)

    def test_submission_with_broken_syntax_is_pass_false_without_crashing(self):
        verdict = python_exec.grade(DATA / "code-flatten-list_broken.md", {}, load_prompt())

        self.assertIs(verdict["pass"], False)
        self.assertIn("SyntaxError", verdict["detail"])

    def test_missing_code_block_is_pass_false(self):
        verdict = python_exec.grade(DATA / "code-flatten-list_nocode.md", {}, load_prompt())

        self.assertIs(verdict["pass"], False)
        self.assertIn("no code block found", verdict["detail"])

    def test_recursive_submission_fails_the_deep_nesting_case(self):
        verdict = python_exec.grade(DATA / "code-flatten-list_recursive.md", {}, load_prompt())

        self.assertIs(verdict["pass"], False)

    def test_real_committed_result_passes(self):
        verdict = python_exec.grade(REAL_RESULT, {}, load_prompt())

        self.assertIs(verdict["pass"], True, verdict["detail"])
        self.assertEqual(verdict["model"], "glm_5_3_flash")
        self.assertEqual(verdict["prompt_id"], "code-python-function")
        self.assertEqual(verdict["mode"], "python-exec")


if __name__ == "__main__":
    unittest.main()
