"""Unit tests for harness.modes.sympy_check (mode string "sympy-check").

The symbolic comparison needs sympy, which is not importable under the
system python used for the stdlib check suite; those tests skip there and
run under the shared venv.
"""

import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.modes import sympy_check  # noqa: E402

DATA = Path(__file__).resolve().parent / "data" / "math-second-derivative"
PROMPT_TOML = ROOT / "prompts" / "math-second-derivative.toml"
REAL_RESULT = ROOT / "results" / "math-second-derivative" / "math-second-derivative_glm_5_3_flash.md"

try:
    import sympy  # noqa: F401

    HAVE_SYMPY = True
except ImportError:  # pragma: no cover - depends on the interpreter
    HAVE_SYMPY = False

requires_sympy = unittest.skipUnless(HAVE_SYMPY, "sympy is not importable")


def load_prompt():
    with open(PROMPT_TOML, "rb") as fh:
        return tomllib.load(fh)


class ExtractionTests(unittest.TestCase):
    """Pure-text extraction needs no sympy."""

    def test_derives_model_from_filename(self):
        prompt = load_prompt()
        self.assertEqual(sympy_check.derive_model(REAL_RESULT, prompt), "glm_5_3_flash")

    def test_extracts_unicode_prime_boxed_answer(self):
        # U+2032 PRIME twice, as the model writes them in prose.
        text = "$$\\boxed{f′′(x) = 36x^2 - 30x + 4}$$\n\n$$\\boxed{f′′(2) = 88}$$"
        expr, point, value = sympy_check.extract_answer(text)
        self.assertEqual(expr, "36x^2 - 30x + 4")
        self.assertEqual(point, "2")
        self.assertEqual(value, "88")

    def test_extracts_ascii_prime_boxed_answer(self):
        text = "$$\\boxed{f''(x) = 36x^2 - 30x + 4}$$\n\n$$\\boxed{f''(2) = 88}$$"
        expr, point, value = sympy_check.extract_answer(text)
        self.assertEqual(expr, "36x^2 - 30x + 4")
        self.assertEqual(point, "2")
        self.assertEqual(value, "88")

    def test_extracts_single_double_prime_u2033_expression_box(self):
        # U+2033 DOUBLE PRIME is a single character; "f″(x)" is one prime glyph.
        text = "$$\\boxed{f″(x) = 36x^2 - 30x + 4}$$\n\n$$\\boxed{f″(2) = 88}$$"
        expr, point, value = sympy_check.extract_answer(text)
        self.assertEqual(expr, "36x^2 - 30x + 4")
        self.assertEqual(point, "2")
        self.assertEqual(value, "88")

    def test_extracts_single_double_prime_u2033_point_box(self):
        # U+2033 in the point/value box only; the expression box uses plain primes.
        text = "$$\\boxed{f''(x) = 36x^2 - 30x + 4}$$\n\n$$\\boxed{f″(2) = 88}$$"
        expr, point, value = sympy_check.extract_answer(text)
        self.assertEqual(expr, "36x^2 - 30x + 4")
        self.assertEqual(point, "2")
        self.assertEqual(value, "88")

    def test_extracts_braced_exponent_expression_box(self):
        # x^{2} is legitimate LaTeX; the capture must not stop at the brace.
        text = "$$\\boxed{f''(x) = 36x^{2} - 30x + 4}$$\n\n$$\\boxed{f''(2) = 88}$$"
        expr, point, value = sympy_check.extract_answer(text)
        self.assertEqual(expr, "36x^2 - 30x + 4")
        self.assertEqual(point, "2")
        self.assertEqual(value, "88")

    def test_missing_box_is_none(self):
        expr, point, value = sympy_check.extract_answer("no boxes here")
        self.assertEqual((expr, point, value), (None, None, None))


class GradeSympyCheckTests(unittest.TestCase):
    @requires_sympy
    def test_schema_and_model_on_real_result(self):
        verdict = sympy_check.grade(REAL_RESULT, {}, load_prompt())
        self.assertEqual(sorted(verdict), ["detail", "mode", "model", "pass", "prompt_id"])
        self.assertEqual(verdict["prompt_id"], "math-calculus-derivative")
        self.assertEqual(verdict["mode"], "sympy-check")
        self.assertEqual(verdict["model"], "glm_5_3_flash")

    def test_missing_box_is_pass_false(self):
        verdict = sympy_check.grade(DATA / "math-second-derivative_noboxes.md", {}, load_prompt())
        self.assertIs(verdict["pass"], False)

    @requires_sympy
    def test_correct_answer_passes(self):
        verdict = sympy_check.grade(DATA / "math-second-derivative_test_model.md", {}, load_prompt())
        self.assertIs(verdict["pass"], True, verdict["detail"])
        self.assertEqual(verdict["model"], "test_model")

    @requires_sympy
    def test_wrong_expression_fails_and_names_it(self):
        verdict = sympy_check.grade(DATA / "math-second-derivative_wrongexpr.md", {}, load_prompt())
        self.assertIs(verdict["pass"], False)
        self.assertIn("expression", verdict["detail"])

    @requires_sympy
    def test_wrong_evaluation_fails_and_names_it(self):
        verdict = sympy_check.grade(DATA / "math-second-derivative_wrongvalue.md", {}, load_prompt())
        self.assertIs(verdict["pass"], False)
        self.assertIn("f''(2)", verdict["detail"])

    @requires_sympy
    def test_double_prime_u2033_answer_passes(self):
        # U+2033 spelling of f''(x), as the model uses in prose.
        verdict = sympy_check.grade(
            DATA / "math-second-derivative_doubleprime.md", {}, load_prompt()
        )
        self.assertIs(verdict["pass"], True, verdict["detail"])

    @requires_sympy
    def test_braced_exponent_answer_passes(self):
        # x^{2}: braces must be tolerated (stripped) so the answer still grades.
        verdict = sympy_check.grade(
            DATA / "math-second-derivative_braced.md", {}, load_prompt()
        )
        self.assertIs(verdict["pass"], True, verdict["detail"])

    @requires_sympy
    def test_real_committed_result_passes(self):
        verdict = sympy_check.grade(REAL_RESULT, {}, load_prompt())
        self.assertIs(verdict["pass"], True, verdict["detail"])
        self.assertEqual(verdict["model"], "glm_5_3_flash")


if __name__ == "__main__":
    unittest.main()
