"""Grading mode "sympy-check".

Extracts the final second-derivative answer from a ``math-second-derivative``
result file — the two ``\\boxed{...}`` statements — and verifies it
symbolically against ``harness/fixtures/math-second-derivative/expected.json``.
Returns the D1 verdict dict ``{prompt_id, model, mode, pass, detail}``.

sympy is imported lazily inside :func:`grade` so that auto-discovery of every
module in ``harness/modes/`` (by #231's ``grade.py``) stays green in
stdlib-only environments.  The LaTeX parser is deliberately not used (it needs
the antlr4 runtime); the expression is extracted by hand and parsed with
``sympy.parsing.sympy_parser.parse_expr`` using ``convert_xor`` (``^`` -> ``**``)
plus implicit multiplication (``36x^2`` -> ``36*x**2``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

MODE = "sympy-check"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "math-second-derivative" / "expected.json"

# Exactly two single-prime glyphs (ASCII apostrophe, U+2032 PRIME, curly
# variants), or one U+2033 DOUBLE PRIME glyph.  Deliberately not a braced
# quantifier: a run of three-or-more primes is f''', a different derivative,
# and must not be mistaken for the second-derivative marker.
PRIMES = "['\u2032\u2019\u2018]{2}|\u2033"
# Right-hand side of a boxed statement: plain text plus single-level braced
# groups, so braced exponents like ``x^{2}`` survive the capture (the braces are
# stripped in :func:`_clean` before parsing).
EXPR = r"(?:[^{}]|\{[^{}]*\})*?"
BOX = re.compile(
    r"\\boxed\s*\{\s*f\s*(?:" + PRIMES + r")\s*\(\s*([^)]*?)\s*\)\s*=\s*(" + EXPR + r")\s*\}",
    re.DOTALL,
)


def derive_model(result_path: Path, prompt: dict) -> str:
    """Model tag from the filename: stem minus the declared/derived prefix."""
    stem = result_path.stem
    prefix = prompt.get("file_prefix") or result_path.parent.name
    if prefix and stem.startswith(prefix + "_"):
        return stem[len(prefix) + 1 :]
    return stem


def _clean(expr: str) -> str:
    """Normalize a captured boxed fragment for ``parse_expr``.

    Braces are dropped: a braced exponent ``x^{2}`` becomes ``x^2``, which
    ``convert_xor`` handles.  ``parse_expr`` on the LaTeX-ish ``x^{2}`` form
    would fail, so this is what makes braced answers grade like unbraced ones.
    """
    return expr.replace("{", "").replace("}", "").replace("\\", " ").replace("$", " ").strip()


def extract_answer(text: str):
    """Return (expression, eval_point, eval_value) from the boxed statements.

    The boxed expression is the last ``\\boxed{f''(x) = ...}``; the evaluation
    is the last ``\\boxed{f''(<number>) = ...}``.  Missing pieces are ``None``.
    """
    expression = None
    point = None
    value = None
    for match in BOX.finditer(text):
        left, right = _clean(match.group(1)), _clean(match.group(2))
        if not right:
            continue
        if left == "x":
            expression = right
        else:
            point, value = left, right
    return expression, point, value


def grade(result_path, grading, prompt) -> dict:
    result_path = Path(result_path)
    verdict = {
        "prompt_id": prompt.get("id"),
        "model": derive_model(result_path, prompt),
        "mode": MODE,
        "pass": False,
        "detail": "",
    }

    expression, point, value = extract_answer(
        result_path.read_text(encoding="utf-8", errors="replace")
    )
    if expression is None or point is None or value is None:
        verdict["detail"] = (
            "could not find boxed f''(x) and f''(<n>) statements (expr=%r point=%r value=%r)"
            % (expression, point, value)
        )
        return verdict

    # Lazy import: keeps this module importable (auto-discovery) without sympy.
    from sympy import Symbol, simplify
    from sympy.parsing.sympy_parser import (
        convert_xor,
        implicit_multiplication_application,
        parse_expr,
        standard_transformations,
    )

    with open(FIXTURES, encoding="utf-8") as fh:
        expected = json.load(fh)

    transformations = standard_transformations + (
        convert_xor,
        implicit_multiplication_application,
    )
    x = Symbol("x")
    try:
        got_expr = parse_expr(expression, transformations=transformations)
    except Exception as exc:  # noqa: BLE001 - untrusted text becomes a verdict
        verdict["detail"] = "could not parse claimed expression %r: %s: %s" % (
            expression,
            type(exc).__name__,
            exc,
        )
        return verdict

    want_expr = parse_expr(expected["expression"], transformations=transformations)
    if simplify(got_expr - want_expr) != 0:
        verdict["detail"] = "expression mismatch: claimed %r, expected %r" % (
            expression,
            expected["expression"],
        )
        return verdict

    try:
        claimed_point = parse_expr(point, transformations=transformations)
        claimed_value = parse_expr(value, transformations=transformations)
    except Exception as exc:  # noqa: BLE001
        verdict["detail"] = "could not parse claimed evaluation %r = %r: %s: %s" % (
            point,
            value,
            type(exc).__name__,
            exc,
        )
        return verdict

    want_point = parse_expr(str(expected["eval_point"]), transformations=transformations)
    want_value = parse_expr(str(expected["eval_value"]), transformations=transformations)
    if simplify(claimed_point - want_point) != 0:
        verdict["detail"] = "f''(%s) mismatch: claimed evaluation point %r, expected %r" % (
            point,
            point,
            expected["eval_point"],
        )
        return verdict
    if simplify(claimed_value - want_value) != 0:
        verdict["detail"] = "f''(%s) mismatch: claimed %r, expected %r" % (
            point,
            value,
            expected["eval_value"],
        )
        return verdict

    verdict["pass"] = True
    verdict["detail"] = "expression and f''(%s) match" % expected["eval_point"]
    return verdict
