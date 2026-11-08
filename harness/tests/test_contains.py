"""Unit tests for the ``contains`` grading mode."""

import tempfile
import unittest
from pathlib import Path

from harness.modes.contains import grade

SCHEMA_KEYS = {"prompt_id", "model", "mode", "pass", "detail"}


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class ContainsModeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.prompt = {
            "id": "math-addition",
            "grading": {"mode": "contains", "expected": "42"},
        }
        self.grading = self.prompt["grading"]

    def tearDown(self):
        self._tmp.cleanup()

    def _result(self, text: str, name: str = "math-addition_glm_5_3_flash.txt") -> Path:
        return _write(self.tmp / "math-addition" / name, text)

    def test_expected_substring_passes(self):
        verdict = grade(self._result("42\n"), self.grading, self.prompt)

        self.assertIs(verdict["pass"], True)
        self.assertEqual(verdict["detail"], 'expected "42" found')

    def test_missing_substring_fails(self):
        verdict = grade(self._result("41\n"), self.grading, self.prompt)

        self.assertIs(verdict["pass"], False)
        self.assertEqual(verdict["detail"], 'expected "42" not found')

    def test_substring_match_scans_the_whole_document(self):
        verdict = grade(
            self._result("The answer is:\n\n42\n\nbecause 17 + 25.\n"),
            self.grading,
            self.prompt,
        )

        self.assertIs(verdict["pass"], True)

    def test_verdict_carries_exactly_the_schema_keys(self):
        verdict = grade(self._result("42\n"), self.grading, self.prompt)

        self.assertEqual(set(verdict), SCHEMA_KEYS)
        self.assertEqual(verdict["prompt_id"], "math-addition")
        self.assertEqual(verdict["model"], "glm_5_3_flash")
        self.assertEqual(verdict["mode"], "contains")
        self.assertIsInstance(verdict["detail"], str)

    def test_model_keeps_underscores_and_suffixes(self):
        verdict = grade(
            self._result("42\n", "math-addition_glm_5_3_flash-v2.txt"),
            self.grading,
            self.prompt,
        )

        self.assertEqual(verdict["model"], "glm_5_3_flash-v2")

    def test_missing_result_file_fails_without_raising(self):
        missing = self.tmp / "math-addition" / "math-addition_gone.txt"

        verdict = grade(missing, self.grading, self.prompt)

        self.assertIs(verdict["pass"], False)
        self.assertIn("not found", verdict["detail"])

    def test_expected_is_compared_as_text(self):
        prompt = {"id": "vision-shape-count", "grading": {"mode": "contains", "expected": 5}}
        result = _write(
            self.tmp / "vision-shape-count" / "vision-shape-count_glm_5_3_flash.md",
            "5\n",
        )

        verdict = grade(result, prompt["grading"], prompt)

        self.assertIs(verdict["pass"], True)


if __name__ == "__main__":
    unittest.main()
