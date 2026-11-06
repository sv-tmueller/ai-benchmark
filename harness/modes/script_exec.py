"""Grading mode "script-exec".

Extracts the Node.js submission from a ``probe-follow-spec`` result file,
writes it as ``count-lines.js`` into a fresh temporary directory and runs it
once per fixture case (``harness/fixtures/probe-follow-spec/cases.json``)
with the case's argv, comparing stdout lines, stderr lines and exit code.
Returns the D1 verdict dict ``{prompt_id, model, mode, pass, detail}``.

Hygiene: each case runs as a subprocess (``node``) with cwd inside the temp
directory, a fixed 10 s timeout and captured stdout/stderr.  This is
subprocess isolation, not a security sandbox: the submission is untrusted
model output and is treated as data.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

MODE = "script-exec"
TIMEOUT_S = 10  # fixed generous cap; not tuned per the package non-goals
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "probe-follow-spec" / "cases.json"
SCRIPT_NAME = "count-lines.js"

_FENCE = re.compile(r"```[ \t]*[A-Za-z0-9_+-]*[ \t]*\n(.*?)```", re.DOTALL)


def derive_model(result_path: Path, prompt: dict) -> str:
    """Model tag from the filename: stem minus the declared/derived prefix."""
    stem = result_path.stem
    prefix = prompt.get("file_prefix") or result_path.parent.name
    if prefix and stem.startswith(prefix + "_"):
        return stem[len(prefix) + 1 :]
    return stem


def extract_script(text: str) -> str | None:
    """Whole file when unfenced; the first fenced block when fenced."""
    stripped = text.strip()
    if not stripped:
        return None
    if "```" not in stripped:
        return text
    match = _FENCE.search(text)
    if match:
        return match.group(1)
    return None


def _lines(value: str) -> list:
    return value.splitlines()


def _syntax_check(workdir: Path) -> str:
    """``node --check`` on the submission; "" when it parses, else the error."""
    try:
        proc = subprocess.run(
            ["node", "--check", SCRIPT_NAME],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return "timed out after %ds while syntax-checking" % TIMEOUT_S
    except OSError as exc:
        return "could not run node: %s: %s" % (type(exc).__name__, exc)
    if proc.returncode != 0:
        return (proc.stderr or proc.stdout or "syntax error").strip()
    return ""


def _run_case(workdir: Path, argv: list, case: dict, syntax_error: str) -> dict:
    if syntax_error:
        return {"pass": False, "detail": "%s: %s" % (case["name"], syntax_error)}
    try:
        proc = subprocess.run(
            ["node", SCRIPT_NAME, *argv],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {"pass": False, "detail": "%s: timed out after %ds" % (case["name"], TIMEOUT_S)}
    except OSError as exc:
        return {"pass": False, "detail": "%s: could not run node: %s: %s" % (case["name"], type(exc).__name__, exc)}

    got_stdout = _lines(proc.stdout)
    got_stderr = _lines(proc.stderr)
    if got_stdout != case["stdout"]:
        return {"pass": False, "detail": "%s: stdout expected %r, got %r" % (case["name"], case["stdout"], got_stdout)}
    if got_stderr != case["stderr"]:
        return {"pass": False, "detail": "%s: stderr expected %r, got %r" % (case["name"], case["stderr"], got_stderr)}
    if proc.returncode != case["exit_code"]:
        return {"pass": False, "detail": "%s: exit code expected %d, got %d" % (case["name"], case["exit_code"], proc.returncode)}
    return {"pass": True, "detail": ""}


def grade(result_path, grading, prompt) -> dict:
    result_path = Path(result_path)
    verdict = {
        "prompt_id": prompt.get("id"),
        "model": derive_model(result_path, prompt),
        "mode": MODE,
        "pass": False,
        "detail": "",
    }

    script = extract_script(result_path.read_text(encoding="utf-8", errors="replace"))
    if script is None:
        verdict["detail"] = "no script found"
        return verdict

    with open(FIXTURES, encoding="utf-8") as fh:
        cases = json.load(fh)["cases"]

    with tempfile.TemporaryDirectory(prefix="script-exec-") as tmp:
        workdir = Path(tmp)
        (workdir / SCRIPT_NAME).write_text(script, encoding="utf-8")
        syntax_error = _syntax_check(workdir)
        for case in cases:
            for name in case["files"]:
                (workdir / name).write_text(case["files"][name], encoding="utf-8")
            outcome = _run_case(workdir, case["argv"], case, syntax_error)
            if not outcome["pass"]:
                verdict["detail"] = outcome["detail"]
                return verdict

    verdict["pass"] = True
    verdict["detail"] = "all %d cases passed" % len(cases)
    return verdict
