"""Grading mode "python-exec".

Extracts the Python submission from a ``code-flatten-list`` result file,
runs it against the fixture battery in
``harness/fixtures/code-flatten-list/cases.json`` and returns the D1 verdict
dict ``{prompt_id, model, mode, pass, detail}``.

Hygiene: the extracted code is written to a fresh temporary directory and
executed as a subprocess (``sys.executable -I``) with cwd inside that
directory, a fixed 10 s timeout and captured stdout/stderr.  This is
subprocess isolation, not a security sandbox: the submission is untrusted
model output and is treated as data.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MODE = "python-exec"
TIMEOUT_S = 10  # fixed generous cap; not tuned per the package non-goals
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "code-flatten-list" / "cases.json"

_FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\n(.*?)```", re.DOTALL)
PY_FENCE = re.compile(r"```[ \t]*python[ \t]*\n(.*?)```", re.DOTALL)

# Runner written into the temp dir next to the submission and executed with
# ``-I``.  It imports the submission via importlib (so an
# ``if __name__ == "__main__"`` self-test is NOT executed) and evaluates the
# battery.  It always prints a single JSON verdict on stdout.
_RUNNER = '''
import importlib.util
import json
import sys
import traceback


def expand(case):
    if "deep" in case:
        depth = case["deep"]["depth"]
        value = case["deep"]["leaf"]
        for _ in range(depth):
            value = [value]
        return value
    return case["input"]


def main():
    submission, cases_path = sys.argv[1], sys.argv[2]
    with open(cases_path, encoding="utf-8") as fh:
        cases = json.load(fh)["cases"]

    spec = importlib.util.spec_from_file_location("submission", submission)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except BaseException as exc:  # noqa: BLE001 - report, never crash the runner
        print(json.dumps({"pass": False, "detail": "import failed: %s: %s" % (type(exc).__name__, exc)}))
        return

    flatten = getattr(module, "flatten", None)
    if not callable(flatten):
        print(json.dumps({"pass": False, "detail": "no callable `flatten` defined"}))
        return

    failures = []
    for case in cases:
        try:
            got = flatten(expand(case))
        except BaseException as exc:  # noqa: BLE001 - report, never crash the runner
            failures.append("%s: raised %s: %s\\n%s" % (case["name"], type(exc).__name__, exc, traceback.format_exc(limit=3)))
            continue
        if got != case["expected"]:
            failures.append("%s: expected %r, got %r" % (case["name"], case["expected"], got))

    if failures:
        print(json.dumps({"pass": False, "detail": " | ".join(failures)}))
    else:
        print(json.dumps({"pass": True, "detail": "all %d cases passed" % len(cases)}))


main()
'''


def derive_model(result_path: Path, prompt: dict) -> str:
    """Model tag from the filename: stem minus the declared/derived prefix."""
    stem = result_path.stem
    prefix = prompt.get("file_prefix") or result_path.parent.name
    if prefix and stem.startswith(prefix + "_"):
        return stem[len(prefix) + 1 :]
    return stem


def extract_code(text: str) -> str | None:
    """First ```python fenced block, falling back to the first fenced block."""
    match = PY_FENCE.search(text)
    if match:
        return match.group(1)
    match = _FENCE.search(text)
    if match:
        return match.group(2)
    return None


def _run(submission_path: Path, cases_path: Path, workdir: Path) -> dict:
    runner_path = workdir / "runner.py"
    runner_path.write_text(_RUNNER, encoding="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(runner_path), str(submission_path), str(cases_path)],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {"pass": False, "detail": "timed out after %ds" % TIMEOUT_S}
    except OSError as exc:
        return {"pass": False, "detail": "could not run submission: %s: %s" % (type(exc).__name__, exc)}

    if proc.returncode != 0:
        captured = (proc.stderr or proc.stdout or "").strip()
        return {"pass": False, "detail": "runner exited %d: %s" % (proc.returncode, captured)}
    try:
        out = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"pass": False, "detail": "runner produced no verdict: %r" % (proc.stdout[-500:],)}
    return {"pass": bool(out.get("pass")), "detail": str(out.get("detail", ""))}


def grade(result_path, grading, prompt) -> dict:
    result_path = Path(result_path)
    verdict = {
        "prompt_id": prompt.get("id"),
        "model": derive_model(result_path, prompt),
        "mode": MODE,
        "pass": False,
        "detail": "",
    }

    code = extract_code(result_path.read_text(encoding="utf-8", errors="replace"))
    if code is None:
        verdict["detail"] = "no code block found"
        return verdict

    with tempfile.TemporaryDirectory(prefix="python-exec-") as tmp:
        workdir = Path(tmp)
        submission_path = workdir / "submission.py"
        submission_path.write_text(code, encoding="utf-8")
        outcome = _run(submission_path, FIXTURES, workdir)

    verdict["pass"] = outcome["pass"]
    verdict["detail"] = outcome["detail"]
    return verdict
