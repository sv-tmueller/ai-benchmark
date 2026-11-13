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
import shlex
import shutil
import signal
import subprocess
import sys
import tomllib
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
    # The resolver is a script, one rule per mode. `grade` is deliberately
    # absent (no arm prompt has [grading]; ArmDataTest asserts it) and so is
    # bench_run_all.py itself, so a child cannot start another batch.
    "Bash(python3 harness/bench_run.py plan *)",
    "Bash(python3 harness/bench_run.py meta *)",
    "Bash(python3 harness/bench_run.py prompt *)",
    "Bash(python3 harness/bench_run.py issue-body *)",
    "Bash(python3 harness/bench_run.py pr-body *)",
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


# --- prompts, skip checks, tree state ---------------------------------------


MERGE_SCRIPT = "harness/merge_results.py"
MERGE_TIMEOUT = 1800
MERGE_OPT_IN = "--post-statuses"  # one-shot result status exception (#253)


def _prompt_data(repo_root, pid):
    for path in sorted(Path(repo_root, "prompts").glob("*.toml")):
        if path.name.endswith(".fixtures.toml"):
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if data.get("id") == pid:
            return data
    raise LookupError("no prompts/*.toml has id %r" % pid)


def expected_base(repo_root, pid, model):
    """``<file_prefix>_<tag>``, built from the prompt file alone."""
    data = _prompt_data(repo_root, pid)
    if not data.get("file_prefix") or not data.get("save_as"):
        raise LookupError("%s sets no file_prefix or save_as" % pid)
    return "%s_%s" % (data["file_prefix"], model_tag(model)), data["save_as"]


def expected_name(repo_root, pid, model):
    """Deliverable file name the child would write, e.g. ``melon-jelly_claude_fable_5_2.html``."""
    base, ext = expected_base(repo_root, pid, model)
    return "%s.%s" % (base, ext)


def planned_names(repo_root, pid, model):
    """The deliverable, meta and grading sidecar names of one run."""
    base, ext = expected_base(repo_root, pid, model)
    return {"%s.%s" % (base, ext), base + ".meta.json", base + "_grading.json"}


class GitError(RuntimeError):
    pass


@dataclass
class Snapshot:
    main_names: set
    prs: list  # (number, url, set of file names)


def snapshot(repo_root):
    """File names on origin/main and in open PRs. Names only, never content."""
    ls = _run(["git", "ls-tree", "-r", "--name-only", "origin/main", "--", "results/"], cwd=repo_root)
    if ls.returncode:
        raise GitError("git ls-tree failed: " + ls.stderr.strip())
    main_names = {Path(line).name for line in ls.stdout.splitlines() if line.strip()}
    pr = _run(["gh", "pr", "list", "--state", "open", "--limit", "200", "--json", "number,url,files"],
              cwd=repo_root)
    if pr.returncode:
        raise GitError("gh pr list failed: " + pr.stderr.strip())
    try:
        rows = json.loads(pr.stdout)
        prs = [(r["number"], r["url"], {Path(f["path"]).name for f in r["files"]}) for r in rows]
    except (ValueError, KeyError, TypeError):
        raise GitError("gh pr list printed output of an unexpected shape")
    return Snapshot(main_names, prs)


def lookup(snap, name):
    """Return ``("origin/main", None, None)``, ``("pr", number, url)`` or None."""
    if name in snap.main_names:
        return ("origin/main", None, None)
    for number, url, names in snap.prs:
        if name in names:
            return ("pr", number, url)
    return None


@dataclass
class Tree:
    branch: str
    lines: list


def tree_state(repo_root):
    status = _run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo_root)
    branch = _run(["git", "branch", "--show-current"], cwd=repo_root)
    if status.returncode or branch.returncode:
        raise GitError("git status or git branch failed")
    return Tree(branch.stdout.strip(), [ln for ln in status.stdout.splitlines() if ln.strip()])


def settle(repo_root, log_dir, pid, model):
    """Leave a clean tree on main between children; return a halt reason or None.

    Only two leftovers are tolerated: this prompt's own planned paths, still
    untracked (moved into the log folder, never deleted or opened), and a clean
    tree on another branch (switched back to main). Anything else halts.
    """
    halt = "tree dirty after %s" % pid
    tree = tree_state(repo_root)
    if tree.lines:
        planned = planned_names(repo_root, pid, model)
        own = []
        for line in tree.lines:
            path = line[3:]
            if not (line.startswith("?? ") and path.startswith("results/") and '"' not in path
                    and Path(path).name in planned):
                return halt
            own.append(path)
        for path in own:
            dest = log_dir / "leftovers" / pid
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(Path(repo_root, path)), str(dest / Path(path).name))
        if tree_state(repo_root).lines:
            return halt
    if tree.branch != "main":
        _run(["git", "switch", "main"], cwd=repo_root)
        if tree_state(repo_root).branch != "main":
            return "could not return to main after %s" % pid
    return None


# --- preflight --------------------------------------------------------------


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def _first_line(text):
    lines = text.strip().splitlines()
    return lines[0] if lines else ""


def _git_out(repo_root, *cmd):
    done = _run(["git", *cmd], cwd=repo_root)
    return done.stdout.strip() if done.returncode == 0 else None


def preflight(args, environ, repo_root):
    checks = []
    err = check_model(args.model)
    checks.append(Check("model", err is None, err or args.model))
    err = check_effort(args.claude, environ)
    checks.append(Check("effort", err is None, err or environ.get("CLAUDE_EFFORT", "")))
    problems = []
    if checks[0].ok:
        for pid in ARM_PROMPTS:
            try:
                expected_name(repo_root, pid, args.model)
            except (LookupError, ValueError, OSError) as exc:
                problems.append("%s: %s" % (pid, exc))
    checks.append(Check("prompts", not problems and checks[0].ok,
                        "; ".join(problems) or ("%d prompt files" % len(ARM_PROMPTS) if checks[0].ok
                                                else "skipped, model unusable")))
    fetch = _run(["git", "fetch", "origin", "main"], cwd=repo_root)
    checks.append(Check("fetch", fetch.returncode == 0, "" if fetch.returncode == 0 else _first_line(fetch.stderr)))
    branch = _git_out(repo_root, "branch", "--show-current")
    checks.append(Check("on main", branch == "main", "on %r" % branch))
    head, origin = _git_out(repo_root, "rev-parse", "HEAD"), _git_out(repo_root, "rev-parse", "origin/main")
    checks.append(Check("HEAD == origin/main", bool(head) and head == origin,
                        "HEAD %s, origin/main %s" % (head, origin)))
    try:
        dirty = tree_state(repo_root).lines
        checks.append(Check("clean tree", not dirty, "%d changed or untracked paths" % len(dirty)))
    except GitError as exc:
        checks.append(Check("clean tree", False, str(exc)))
    auth = _run(["gh", "auth", "status"], cwd=repo_root)
    checks.append(Check("gh auth", auth.returncode == 0,
                        "" if auth.returncode == 0 else _first_line(auth.stderr or auth.stdout)))
    return checks


# --- batch ------------------------------------------------------------------


def _say(text=""):
    print(text, flush=True)


def describe(summary, pr):
    """Outcome string and PR url for one finished child."""
    if pr is not None:
        outcome = "pr-opened #%d" % pr[1]
    elif summary.timed_out:
        outcome = "timed-out"
    elif summary.exit_code != 0:
        outcome = "failed: exit %d" % summary.exit_code
    elif summary.is_error:
        outcome = "failed: %s" % (summary.subtype or "is_error")
    else:
        outcome = "ended without PR"
    notes = []
    if summary.stop_line:
        notes.append(summary.stop_line)
    if summary.void_line:
        notes.append(summary.void_line)
    if summary.denied_tools:
        notes.append("denied: " + ", ".join(summary.denied_tools))
    if summary.model_ok is False:
        notes.append("model usage lacks the requested id, has: " + ", ".join(summary.model_usage))
    if not summary.parsed and not summary.timed_out:
        notes.append("no parseable JSON output")
    if notes:
        outcome += " (" + "; ".join(notes) + ")"
    return outcome, (pr[2] if pr else "-")


def run_batch(args, environ, repo_root, log_dir):
    """The loop: skip check, child, outcome, cleanup. Returns (rows, halt reason)."""
    rows, halt = [], None
    total = len(ARM_PROMPTS)
    for i, pid in enumerate(ARM_PROMPTS, 1):
        if halt:
            rows.append((pid, "not-started: " + halt, "-"))
            continue
        name = expected_name(repo_root, pid, args.model)
        try:
            hit = lookup(snapshot(repo_root), name)
        except GitError as exc:
            halt = "skip check failed before %s: %s" % (pid, exc)
            rows.append((pid, "not-started: " + halt, "-"))
            continue
        if hit:
            outcome = "skipped: on origin/main" if hit[0] == "origin/main" else "skipped: open PR #%d" % hit[1]
            rows.append((pid, outcome, hit[2] or "-"))
            _say("[%d/%d] %s  %s" % (i, total, pid, outcome))
            continue
        _say("[%d/%d] %s  running ..." % (i, total, pid))
        run = launch(args.claude, "/bench-run " + pid, args.model, environ["CLAUDE_EFFORT"],
                     args.timeout, repo_root, environ)
        write_child_log(log_dir, pid, run)
        summary = summarize(run, args.model)
        try:
            after = lookup(snapshot(repo_root), name)
        except GitError:
            after = None
        pr = after if after and after[0] == "pr" else None
        outcome, url = describe(summary, pr)
        rows.append((pid, outcome, url))
        _say("[%d/%d] %s  %s" % (i, total, pid, outcome))
        try:
            halt = settle(repo_root, log_dir, pid, args.model)
        except GitError as exc:
            halt = "tree check failed after %s: %s" % (pid, exc)
    return rows, halt


def merge_step(args, repo_root, halt):
    """Run the gated merge command if it exists, else list the open PRs. Returns ok."""
    if halt:
        _say("merge step: skipped (%s)" % halt)
        return False
    if Path(repo_root, MERGE_SCRIPT).is_file():
        try:
            tree = tree_state(repo_root)
        except GitError as exc:
            _say("merge step: skipped (%s)" % exc)
            return False
        if tree.lines or tree.branch != "main":
            _say("merge step: skipped (tree not clean on main)")
            return False
        try:
            done = _run([sys.executable, MERGE_SCRIPT, "--model", args.model, MERGE_OPT_IN],
                        cwd=repo_root, timeout=MERGE_TIMEOUT)
        except subprocess.TimeoutExpired:
            _say("merge step: ran %s, timed out after %d s" % (MERGE_SCRIPT, MERGE_TIMEOUT))
            return False
        sys.stdout.write(done.stdout)
        sys.stdout.write(done.stderr)
        _say("merge step: ran %s, exit %d" % (MERGE_SCRIPT, done.returncode))
        return done.returncode == 0
    _say("merge step: %s not present; open PRs for this arm:" % MERGE_SCRIPT)
    try:
        snap = snapshot(repo_root)
    except GitError as exc:
        _say("  cannot list: %s" % exc)
        return False
    by_name = {expected_name(repo_root, pid, args.model): pid for pid in ARM_PROMPTS}
    found = [(n, u, by_name[nm]) for n, u, names in snap.prs for nm in sorted(names) if nm in by_name]
    for number, url, pid in found:
        _say("  #%d %s (%s)" % (number, url, pid))
    if not found:
        _say("  none")
    return True


CATEGORIES = ("pr-opened", "skipped", "timed-out", "failed", "ended without PR", "not-started")


def report(rows, log_dir):
    _say()
    _say("report")
    for pid, outcome, url in rows:
        _say("%s  %s  %s" % (pid, outcome, url))
    _say()
    for cat in CATEGORIES:
        n = sum(1 for _, outcome, _ in rows if outcome.startswith(cat))
        if n:
            _say("%s: %d" % (cat, n))
    _say("log folder: %s" % log_dir)


def run_dry(args, environ, repo_root, checks):
    _say("dry-run: no child will be started")
    for c in checks:
        _say("check %s: %s%s" % ("ok" if c.ok else "FAIL", c.name, (" - " + c.detail) if c.detail else ""))
    for c in checks:
        if not c.ok:
            _say("STOP: %s: %s" % (c.name, c.detail))
    if all(c.ok for c in checks if c.name in ("model", "prompts")):
        try:
            snap = snapshot(repo_root)
        except GitError as exc:
            _say("check FAIL: skip lookup - %s" % exc)
            snap = None
            checks.append(Check("skip lookup", False, str(exc)))
        if snap is not None:
            for pid in ARM_PROMPTS:
                name = expected_name(repo_root, pid, args.model)
                hit = lookup(snap, name)
                what = "run" if not hit else (
                    "skip (on origin/main)" if hit[0] == "origin/main" else "skip (open PR #%d)" % hit[1])
                _say("prompt %s: %s  %s" % (pid, what, name))
    effort = environ.get("CLAUDE_EFFORT") or "<CLAUDE_EFFORT>"
    _say("child command: " + shlex.join(build_command(args.claude, "/bench-run <prompt-id>", args.model, effort)))
    if Path(repo_root, MERGE_SCRIPT).is_file():
        _say("merge step: would run python3 %s --model %s %s" % (
            MERGE_SCRIPT, args.model, MERGE_OPT_IN))
    else:
        _say("merge step: would list open PRs (%s not present)" % MERGE_SCRIPT)
    return 0 if all(c.ok for c in checks) else 1


def run_all(args, environ, repo_root):
    checks = preflight(args, environ, repo_root)
    if args.dry_run:
        return run_dry(args, environ, repo_root, checks)
    failed = [c for c in checks if not c.ok]
    if failed:
        for c in failed:
            _say("STOP: %s: %s" % (c.name, c.detail))
        return 2
    log_dir = make_log_dir(args.log_dir)
    rows, halt = run_batch(args, environ, repo_root, log_dir)
    merge_ok = merge_step(args, repo_root, halt)
    report(rows, log_dir)
    clean = all(o.startswith(("pr-opened", "skipped")) for _, o, _ in rows)
    return 0 if clean and merge_ok and not halt else 1


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
    return run_all(args, environ, repo_root)


if __name__ == "__main__":
    sys.exit(main())
