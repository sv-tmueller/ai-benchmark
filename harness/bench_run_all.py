#!/usr/bin/env python3
"""Run the whole Claude Fable 5.2 one-shot arm, one headless child per prompt.

``/bench-run`` with no arguments calls this helper. For each prompt in
``ARM_PROMPTS`` it starts a fresh headless ``claude -p "/bench-run <id>"``
child with the same model and effort as the calling session, a narrow tool
allowlist and ``--permission-mode dontAsk``, so every generation is one
isolated one-shot session. The helper reads no result content: it looks at
file names, git and ``gh pr list`` only, and never merges anything itself.

Usage (from the repo root)::

    python3 harness/bench_run_all.py --model <exact-model-id> [--dry-run]
    python3 harness/bench_run_all.py --model <id> --smoke <prompt-id>

``--smoke`` starts exactly one child running ``/bench-run <id> --dry-run``,
which generates nothing. Stdlib only; Python 3.11+.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# `python3 harness/bench_run_all.py` puts harness/ on sys.path, not the repo
# root; make the `harness` package importable the same way grade.py does.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.modes._common import model_tag  # noqa: E402

# The 11 prompts of the Fable 5.2 arm, in ledger order. A unit test checks
# this against the README ledger table and the prompt files.
ARM_PROMPTS = (
    "game-melon-jelly",
    "game-lava-lamp",
    "game-minecraft",
    "game-meridian-launch",
    "game-sunset-ocean",
    "game-horror-house",
    "game-last-flight",
    "game-cities-skylines",
    "game-mario-kart",
    "app-stillwater",
    "game-weichensteller",
)

EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
MODEL_ALIASES = ("fable", "opus", "sonnet", "haiku")
DEFAULT_TIMEOUT = 3600

# One argument per rule. Under dontAsk anything not listed is refused, so a
# child cannot merge a PR, Read, or fetch. File writes are `Edit(...)` rules:
# the permission docs match every file-writing tool, Write included, against
# `Edit(path)` and never match `Write(path)`.
ALLOWED_TOOLS = (
    "Bash(git fetch origin main)",
    "Bash(git rev-parse *)",
    "Bash(git status *)",
    "Bash(git branch --show-current)",
    "Bash(git switch *)",
    "Bash(git add results/*)",
    "Bash(git diff --cached *)",
    "Bash(git commit *)",
    "Bash(git push -u origin feat/*)",
    "Bash(gh auth status)",
    "Bash(gh issue create *)",
    "Bash(gh pr create *)",
    # Known, accepted gap: these allow any inline Python. They exist because
    # the resolver and the prompt printer live inline in SKILL.md.
    "Bash(python3 - *)",
    "Bash(python3 -c *)",
    "Bash(python - *)",
    "Bash(python -c *)",
    "Edit(results/**)",
)

# Variables describing the calling session. Removed so the child's own
# CLAUDE_EFFORT can only come from its --effort flag; everything else (auth,
# PATH, gh) is kept.
STRIPPED_ENV = (
    "CLAUDE_EFFORT",
    "CLAUDECODE",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_SESSION_ATTENDED",
    "CLAUDE_PID",
    "CLAUDE_CODE_INVOKED_SKILLS",
    "CLAUDE_CODE_ENTRYPOINT",
)
STRIPPED_ENV_PREFIXES = ("CLAUDE_CODE_MESSAGING_",)


def _run(cmd, cwd=None, timeout=None):
    """Run a git or gh command. The one seam the tests patch."""
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


# --- checks -----------------------------------------------------------------


def check_model(model):
    """Return an error string if ``model`` is not an exact usable id, else None."""
    model = (model or "").strip()
    if not model:
        return "--model is empty; pass the exact model id from your system prompt"
    if model.lower() in MODEL_ALIASES:
        return "%r is an alias, not an exact model id; pass the exact id from your system prompt" % model
    try:
        model_tag(model)
    except ValueError as exc:
        return str(exc)
    return None


def _claude_help(claude_bin, environ):
    """Return ``claude --help`` output, or None if it cannot be run."""
    try:
        done = subprocess.run([claude_bin, "--help"], capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, env=dict(environ), timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout + done.stderr


def check_effort(claude_bin, environ):
    """Return an error string unless CLAUDE_EFFORT is a valid level the binary accepts."""
    effort = environ.get("CLAUDE_EFFORT", "")
    if not effort:
        return "CLAUDE_EFFORT is unset or empty; the effort level cannot be recorded or passed on"
    if effort not in EFFORT_LEVELS:
        return "CLAUDE_EFFORT=%r is not one of %s" % (effort, ", ".join(EFFORT_LEVELS))
    help_text = _claude_help(claude_bin, environ)
    if help_text is None:
        return "cannot run `%s --help` to check for --effort" % claude_bin
    if "--effort" not in help_text:
        return "`%s --help` lists no --effort flag; the child could not be given the effort level" % claude_bin
    return None


# --- child session ----------------------------------------------------------


def build_command(claude_bin, slash, model, effort):
    """Return the argv for one headless child.

    The prompt must come right after ``-p``: ``--tools`` and ``--allowedTools``
    take lists and would swallow a prompt placed after them. No fallback model,
    no extra system prompt, and no permission-skipping flag of any kind.
    """
    return [
        claude_bin, "-p", slash,
        "--model", model,
        "--effort", effort,
        "--tools", "Bash,Write",
        "--permission-mode", "dontAsk",
        "--output-format", "json",
        "--allowedTools", *ALLOWED_TOOLS,
    ]


def build_env(environ):
    """Return a copy of ``environ`` without the calling session's variables."""
    return {
        k: v for k, v in environ.items()
        if k not in STRIPPED_ENV and not k.startswith(STRIPPED_ENV_PREFIXES)
    }


@dataclass
class ChildRun:
    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str


def launch(claude_bin, slash, model, effort, timeout, repo_root, environ):
    """Start one child and wait for it; kill its whole process group on timeout."""
    cmd = build_command(claude_bin, slash, model, effort)
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(repo_root), env=build_env(environ), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True,
        )
    except OSError as exc:
        return ChildRun(127, False, "", "cannot start %s: %s" % (claude_bin, exc))
    try:
        out, err = proc.communicate(timeout=timeout)
        return ChildRun(proc.returncode, False, out, err)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
        return ChildRun(proc.returncode, True, out or "", err or "")


@dataclass
class ChildSummary:
    """What the helper keeps of a child: never the result text, only markers."""

    exit_code: int
    timed_out: bool
    parsed: bool = False
    is_error: bool = False
    subtype: str | None = None
    stop_line: str | None = None
    void_line: str | None = None
    denied_tools: list = field(default_factory=list)
    model_usage: list = field(default_factory=list)
    model_ok: bool | None = None


def _result_object(raw):
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if isinstance(data, list):
        results = [e for e in data if isinstance(e, dict) and e.get("type") == "result"]
        return results[-1] if results else None
    return data if isinstance(data, dict) else None


def summarize(run, model):
    """Reduce a child's output to exit state, markers and denied tool names.

    Only a ``STOP:`` line or a ``run void`` line is ever taken from the result
    text; the rest of it and every ``permission_denials[].tool_input`` (which
    can contain the deliverable) are dropped here.
    """
    out = ChildSummary(run.exit_code, run.timed_out)
    data = _result_object(run.stdout)
    if data is None:
        return out
    out.parsed = True
    out.is_error = bool(data.get("is_error"))
    subtype = data.get("subtype")
    out.subtype = subtype if isinstance(subtype, str) else None
    text = data.get("result")
    if isinstance(text, str):
        for line in text.splitlines():
            line = line.strip()
            if out.stop_line is None and line.startswith("STOP:"):
                out.stop_line = line[:300]
            if out.void_line is None and "run void" in line.lower():
                out.void_line = line[:300]
    denials = data.get("permission_denials")
    if isinstance(denials, list):
        out.denied_tools = sorted({d["tool_name"] for d in denials
                                   if isinstance(d, dict) and isinstance(d.get("tool_name"), str)})
    usage = data.get("modelUsage")
    if isinstance(usage, dict):
        out.model_usage = sorted(usage)
        out.model_ok = model in usage
    return out


# --- smoke ------------------------------------------------------------------


def make_log_dir(base=None):
    """Create and return the log folder, outside the repo tree."""
    if base is None:
        cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        base = Path(cache) / "bench-run" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    return base


def write_child_log(log_dir, name, run):
    (log_dir / (name + ".json")).write_text(run.stdout, encoding="utf-8")
    (log_dir / (name + ".stderr")).write_text(run.stderr, encoding="utf-8")


def _result_text(raw):
    data = _result_object(raw)
    text = data.get("result") if data else None
    return text if isinstance(text, str) else None


def run_smoke(args, environ, repo_root):
    """One real child running ``/bench-run <id> --dry-run``; it generates nothing."""
    if args.smoke not in ARM_PROMPTS:
        print("STOP: %s is not one of the %d arm prompts" % (args.smoke, len(ARM_PROMPTS)))
        return 2
    stops = [m for m in (check_model(args.model), check_effort(args.claude, environ)) if m]
    if stops:
        for msg in stops:
            print("STOP: " + msg)
        return 2
    log_dir = make_log_dir(args.log_dir)
    run = launch(args.claude, "/bench-run %s --dry-run" % args.smoke, args.model,
                 environ["CLAUDE_EFFORT"], args.timeout, repo_root, environ)
    write_child_log(log_dir, args.smoke + ".smoke", run)
    s = summarize(run, args.model)
    print("smoke: /bench-run %s --dry-run" % args.smoke)
    print("exit_code: %d" % run.exit_code)
    print("timed_out: %s" % str(run.timed_out).lower())
    print("is_error: %s" % str(s.is_error).lower())
    print("subtype: %s" % s.subtype)
    print("denied_tools: %s" % (", ".join(s.denied_tools) or "none"))
    print("model_usage: %s" % (", ".join(s.model_usage) or "none"))
    print("log: %s" % log_dir)
    print("--- child output (dry-run: paths and sidecar preview only) ---")
    print(_result_text(run.stdout) if s.parsed else "(no parseable JSON; see the log)")
    ok = run.exit_code == 0 and not run.timed_out and not s.is_error and s.parsed
    return 0 if ok else 1


# --- command line -----------------------------------------------------------


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--model", required=True, help="exact model id of the calling session")
    p.add_argument("--dry-run", action="store_true", help="show the checks and the plan; start no child")
    p.add_argument("--smoke", metavar="PROMPT_ID", help="start one /bench-run <id> --dry-run child")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="seconds per child (default 3600)")
    p.add_argument("--claude", default="claude", help="path to the claude binary")
    p.add_argument("--log-dir", help="log folder (default: ~/.cache/bench-run/<UTC>/)")
    return p.parse_args(argv)


def main(argv=None, environ=None, repo_root=REPO_ROOT):
    args = parse_args(argv)
    environ = os.environ if environ is None else environ
    repo_root = Path(repo_root)
    if args.smoke:
        return run_smoke(args, environ, repo_root)
    print("STOP: batch mode is not implemented yet")
    return 2


if __name__ == "__main__":
    sys.exit(main())
