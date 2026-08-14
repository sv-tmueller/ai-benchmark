"""Automated response grading for benchmark prompts.

Four grading modes are supported:

* ``exact``     – stripped-string equality against ``expected``
* ``regex``     – compiled ``pattern`` searched against the response
* ``contains``  – substring presence of ``expected`` in the response
* ``judge``     – delegate scoring to a judge LLM via a caller callable

Public API
-----------
``has_grading(prompt_data)``
    Detect whether a prompt dict carries a ``[grading]`` section.

``grade_result(response_text, grading_config, judge_caller=None)``
    Dispatch to the correct mode and return ``(grade, details)``.

Stdlib only — no external dependencies.
"""

from __future__ import annotations

import re
from typing import Callable, Sequence


# Type alias for the judge-model invocation callable.
JudgeCaller = Callable[[str, Sequence[dict]], str]


# --------------------------------------------------------------------------- #
# Public helpers                                                              #
# --------------------------------------------------------------------------- #

def has_grading(prompt_data: dict) -> bool:
    """Return True iff *prompt_data* contains a non-empty ``grading`` section."""
    section = prompt_data.get("grading")
    if section is None:
        return False
    # An empty dict/table is treated as "no grading".
    if isinstance(section, dict):
        return len(section) > 0
    return bool(section)


def grade_result(
    response_text: str,
    grading_config: dict | None,
    judge_caller: JudgeCaller | None = None,
) -> tuple[float | None, str]:
    """Grade *response_text* according to *grading_config*.

    Parameters
    ----------
    response_text :
        The raw model response to evaluate.
    grading_config :
        Dict with keys ``mode``, ``expected``, ``pattern``, ``judge_model``,
        ``judge_criteria``.  May be ``None`` or empty to indicate "no grading".
    judge_caller :
        Optional callable ``(model_key, messages) -> str`` used only for
        ``judge`` mode.

    Returns
    -------
    (grade, details)
        ``grade`` is ``1.0`` (pass) / ``0.0`` (fail) for the deterministic
        modes, a normalized ``float`` in ``[0, 1]`` for judge mode, or
        ``None`` when no grading config is supplied.  ``details`` is always a
        short human-readable explanation string.
    """
    if not grading_config:
        return None, "No grading configuration provided"

    mode = (grading_config.get("mode") or "").strip().lower()

    dispatch = {
        "exact": _grade_exact,
        "regex": _grade_regex,
        "contains": _grade_contains,
        "judge": _grade_judge,
    }

    handler = dispatch.get(mode)
    if handler is None:
        return None, f"Unknown grading mode: {mode!r}"

    return handler(response_text, grading_config, judge_caller)


# --------------------------------------------------------------------------- #
# Mode handlers                                                               #
# --------------------------------------------------------------------------- #

def _grade_exact(
    response_text: str,
    config: dict,
    _caller: JudgeCaller | None,
) -> tuple[float, str]:
    """Stripped-whitespace string equality."""
    expected = config.get("expected", "")
    resp = (response_text or "").strip()
    exp = (expected or "").strip()
    passed = resp == exp
    grade = 1.0 if passed else 0.0
    details = (
        f"exact match: PASS (response == expected)"
        if passed
        else f"exact match: FAIL (got {resp[:200]!r}, expected {exp[:200]!r})"
    )
    return grade, details


def _grade_regex(
    response_text: str,
    config: dict,
    _caller: JudgeCaller | None,
) -> tuple[float, str]:
    """Compile *pattern* and search against the response."""
    pattern_str = config.get("pattern", "")
    if not pattern_str:
        return 0.0, "regex match: FAIL (no pattern specified)"
    flags = re.MULTILINE | re.DOTALL
    try:
        regex = re.compile(pattern_str, flags)
    except re.error as exc:
        return 0.0, f"regex match: ERROR compiling pattern ({exc})"
    match = regex.search(response_text or "")
    passed = match is not None
    grade = 1.0 if passed else 0.0
    details = (
        f"regex match: PASS (matched {match.group(0)[:200]!r})"
        if passed
        else f"regex match: FAIL (pattern {pattern_str!r} not found)"
    )
    return grade, details


def _grade_contains(
    response_text: str,
    config: dict,
    _caller: JudgeCaller | None,
) -> tuple[float, str]:
    """Case-sensitive substring check."""
    needle = config.get("expected", "") or ""
    haystack = response_text or ""
    passed = needle != "" and needle in haystack
    grade = 1.0 if passed else 0.0
    details = (
        f"contains: PASS (found {needle[:200]!r})"
        if passed
        else f"contains: FAIL (substring {needle[:200]!r} not present)"
    )
    return grade, details


def _grade_judge(
    response_text: str,
    config: dict,
    judge_caller: JudgeCaller | None,
) -> tuple[float, str]:
    """Delegate scoring to a judge LLM and parse its numeric verdict."""
    if judge_caller is None:
        return 0.0, "judge: FAIL (no judge_caller provided)"

    model_key = config.get("judge_model", "")
    criteria = config.get("judge_criteria", "")

    if not model_key:
        return 0.0, "judge: FAIL (no judge_model specified)"

    messages = [
        {
            "role": "system",
            "content": (
                "You are an impartial judge evaluating an AI response. "
                "Respond with ONLY a single numeric score."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Evaluation criteria:\n{criteria}\n\n"
                f"Response to evaluate:\n{response_text or ''}\n\n"
                "Score the response on a scale of 0 to 10 where 10 is best. "
                "Reply with ONLY the number."
            ),
        },
    ]

    try:
        judge_response = judge_caller(model_key, messages)
    except Exception as exc:  # noqa: BLE001 - surface any caller failure
        return 0.0, f"judge: ERROR calling judge model ({exc})"

    score, raw = _parse_judge_score(judge_response)

    if score is None:
        return 0.0, f"judge: FAIL (could not parse score from {raw!r})"

    details = f"judge: score={score:.3f} (raw={raw!r})"
    return score, details


# --------------------------------------------------------------------------- #
# Score parsing                                                                #
# --------------------------------------------------------------------------- #

# Capture a number optionally written as "X/Y".  Group 1 is the numerator;
# group 2 (optional) is the denominator.
_SCORE_RE = re.compile(
    r"(?<![\d.])(\d{1,2}(?:\.\d+)?)\s*(?:/\s*(\d+(?:\.\d+)?))?(?![\d.])"
)


def _parse_judge_score(text: str) -> tuple[float | None, str]:
    """Extract a numeric score from *text* and normalize to ``[0, 1]``.

    Heuristic order::

        1. Explicit denominator ("8/10", "0.9/1") → numerator ÷ denominator.
        2. Value > 1.0                                  → 0-10 scale (÷ 10).
        3. Value ≤ 1.0                                 → 0-1 scale (as-is).

    Returns ``(normalized_score, raw_token)`` or ``(None, text_stripped)``.
    """
    if not text:
        return None, ""

    stripped = text.strip()

    candidates: list[tuple[float, float, float]] = []  # (norm, denom_hint, raw)
    for m in _SCORE_RE.finditer(stripped):
        num_tok = m.group(1)
        den_tok = m.group(2)
        try:
            num = float(num_tok)
        except ValueError:
            continue

        if den_tok is not None:
            try:
                den = float(den_tok)
            except ValueError:
                den = None
            if den and den > 0:
                norm = max(0.0, min(1.0, num / den))
                candidates.append((norm, den, num))
                continue

        # No explicit denominator — infer from magnitude.
        if num > 1.0:
            candidates.append((num / 10.0, 10.0, num))
        elif 0.0 <= num <= 1.0:
            candidates.append((num, 1.0, num))

    if candidates:
        # Prefer explicit denominators, then the median-ish value.
        # Sort: explicit (den≠10 inferred-from->1) handled by preferring
        # any candidate whose normalized value sits nearest 0.5 among the
        # highest-confidence picks.  Simpler: choose the candidate closest
        # to the middle of the pack.
        candidates.sort(key=lambda c: c[0])
        best_norm = candidates[len(candidates) // 2][0]
        return best_norm, stripped

    return None, stripped


# --------------------------------------------------------------------------- #
# Self-test                                                                    #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    # Quick smoke checks (stdlib assert).
    assert has_grading({"grading": {"mode": "exact"}}) is True
    assert has_grading({"grading": {}}) is False
    assert has_grading({}) is False

    g, d = grade_result("hello world", {"mode": "exact", "expected": "hello world"})
    assert g == 1.0, d

    g, d = grade_result(" hello world ", {"mode": "exact", "expected": "hello world"})
    assert g == 1.0, d

    g, d = grade_result("goodbye", {"mode": "exact", "expected": "hello world"})
    assert g == 0.0, d

    g, d = grade_result("foo bar baz", {"mode": "regex", "pattern": r"ba[rz]"})
    assert g == 1.0, d

    g, d = grade_result("nothing here", {"mode": "regex", "pattern": r"\d+"})
    assert g == 0.0, d

    g, d = grade_result("the quick brown fox", {"mode": "contains", "expected": "brown"})
    assert g == 1.0, d

    g, d = grade_result("the quick red fox", {"mode": "contains", "expected": "brown"})
    assert g == 0.0, d

    g, d = grade_result("", {})
    assert g is None

    g, d = grade_result("anything", {"mode": "weird"})
    assert g is None

    # Judge-mode parser sanity.
    s, _ = _parse_judge_score("Score: 8")
    assert s == 0.8, s
    s, _ = _parse_judge_score("Rating: 7.5/10")
    assert s == 0.75, s
    s, _ = _parse_judge_score("Final grade: 0.9")
    assert s == 0.9, s

    # Judge integration with a fake caller.
    def fake_caller(key, msgs):
        return "8"

    g, d = grade_result(
        "some response",
        {"mode": "judge", "judge_model": "test-judge", "judge_criteria": "be good"},
        judge_caller=fake_caller,
    )
    assert g == 0.8, d

    g, d = grade_result(
        "some response",
        {"mode": "judge", "judge_model": "", "judge_criteria": ""},
        judge_caller=fake_caller,
    )
    assert g == 0.0, d

    g, d = grade_result(
        "some response",
        {"mode": "judge", "judge_model": "test-judge", "judge_criteria": ""},
        judge_caller=None,
    )
    assert g == 0.0, d

    print("bench.grader self-tests passed.")
