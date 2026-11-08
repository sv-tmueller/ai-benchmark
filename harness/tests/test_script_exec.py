"""Unit tests for harness.modes.script_exec (mode string "script-exec")."""

import shutil
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.modes import script_exec  # noqa: E402

DATA = Path(__file__).resolve().parent / "data" / "probe-follow-spec"
PROMPT_TOML = ROOT / "prompts" / "probe-follow-spec.toml"
REAL_RESULT = ROOT / "results" / "probe-follow-spec" / "follow-spec_glm_5_3_flash.txt"

requires_node = unittest.skipUnless(shutil.which("node"), "node is not installed")


def load_prompt():
    with open(PROMPT_TOML, "rb") as fh:
        return tomllib.load(fh)


class DeriveModelTests(unittest.TestCase):
    def test_uses_declared_file_prefix_over_directory_name(self):
        prompt = load_prompt()
        model = script_exec.derive_model(REAL_RESULT, prompt)
        self.assertEqual(model, "glm_5_3_flash")


@requires_node
class GradeScriptExecTests(unittest.TestCase):
    def test_valid_script_passes_and_reports_schema(self):
        verdict = script_exec.grade(DATA / "follow-spec_test_model.txt", {}, load_prompt())

        self.assertEqual(
            sorted(verdict), ["detail", "mode", "model", "pass", "prompt_id"]
        )
        self.assertEqual(verdict["prompt_id"], "probe-follow-spec")
        self.assertEqual(verdict["mode"], "script-exec")
        self.assertEqual(verdict["model"], "test_model")
        self.assertIs(verdict["pass"], True)
        self.assertIsInstance(verdict["detail"], str)

    def test_syntactically_invalid_script_is_pass_false_without_crashing(self):
        verdict = script_exec.grade(DATA / "follow-spec_broken.txt", {}, load_prompt())

        self.assertIs(verdict["pass"], False)
        self.assertIn("SyntaxError", verdict["detail"])

    def test_empty_result_is_pass_false(self):
        verdict = script_exec.grade(DATA / "follow-spec_empty.txt", {}, load_prompt())

        self.assertIs(verdict["pass"], False)

    def test_script_that_ignores_the_spec_fails(self):
        verdict = script_exec.grade(DATA / "follow-spec_wrong.txt", {}, load_prompt())

        self.assertIs(verdict["pass"], False)

    def test_real_committed_result_passes(self):
        verdict = script_exec.grade(REAL_RESULT, {}, load_prompt())

        self.assertIs(verdict["pass"], True, verdict["detail"])
        self.assertEqual(verdict["model"], "glm_5_3_flash")
        self.assertEqual(verdict["prompt_id"], "probe-follow-spec")
        self.assertEqual(verdict["mode"], "script-exec")


if __name__ == "__main__":
    unittest.main()
