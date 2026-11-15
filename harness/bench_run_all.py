#!/usr/bin/env python3
"""Run the one-shot arm, or a chosen part of it, one headless child per prompt.

``/bench-run`` in batch mode calls this helper. For each selected prompt of
``ARM_PROMPTS`` (all of them unless ``--prompts`` narrows it) it starts a fresh
headless ``claude -p "/bench-run <id>"`` child with the same model and effort
as the calling session, a narrow tool allowlist and
``--permission-mode dontAsk``, so every generation is one isolated one-shot
session. The helper reads no result content: it looks at file names, git,
``gh pr list`` and, for a PR a child opened, ``gh pr view``, and never merges
anything itself. It does write once per such PR: it adds the run metrics of the
child (duration, tokens, cost, read from the child's JSON output after it
exited) as ``<deliverable stem>.run.json`` through the GitHub contents API, and
puts a "Run metrics" section into the PR description with ``gh pr edit``. A
failure there is a note in the report line, never a halt or a changed exit code.

A batch runs in a private git worktree for its model and effort level,
``.claude/worktrees/bench-run-<model_tag>_<effort>``, detached at
``origin/main``: the children, the between-children cleanup and the merge
step all run there, so the main checkout is never switched or written to and
batches for other models or effort levels can run from it at the same time.
An exclusive ``flock`` on ``<worktree>.lock`` (inherited by every child)
stops a second batch for the same model and effort while one is running. After
a run that ended without a halt the worktree is removed; after a halt it is
kept and the next run reuses it only if it is clean and not detached at a commit
not on ``origin/main``. ``--smoke`` and
``--dry-run`` create nothing.

Usage (from the repo root)::

    python3 harness/bench_run_all.py --model <exact-model-id> [--prompts IDS] [--dry-run]
    python3 harness/bench_run_all.py --model <id> --list
    python3 harness/bench_run_all.py --model <id> --select ANSWER
    python3 harness/bench_run_all.py --model <id> --smoke <prompt-id>

``--prompts`` takes comma-separated arm prompt ids, or ``all`` (the same as
leaving it out), and runs only those, in arm order. ``--list`` prints the arm's
prompts numbered, each marked with whether it already has a result on
``origin/main`` or in an open PR, using ``git fetch``, ``git ls-tree`` and
``gh pr list`` only. ``--select`` turns the user's raw answer to "which
prompts?" (``all``, ``2``, ``1,4,7``, ``3-6``) into a ``prompts: <ids>`` line
(``prompts: all`` for the whole arm) and calls no git, gh or claude. ``--smoke``
starts exactly one child running ``/bench-run <id> --dry-run``, which generates
nothing and runs in the main checkout; ``--smoke``, ``--list`` and ``--select``
exclude each other and ``--prompts``.

Exit codes: 0 clean, 1 something failed or was left undone, 2 a ``STOP:`` before
anything started (including a ``--prompts`` id that is not in the arm), 3 an
``INVALID:`` answer to ``--select`` (the caller asks again). Stdlib only;
Python 3.11+. Git and ``gh`` go through ``_run``, the one seam the unit tests
patch; the real-git tests exercise the worktree helpers with it unpatched.
"""

import argparse
import base64
import fcntl
import json
import math
import os
import re
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

from harness.modes._common import (EFFORT_LEVELS, model_tag, printable, run_tag,  # noqa: E402
                                    session_effort)

# The 14 prompts of the one-shot arm, in ledger order: every prompt under
# prompts/. A unit test checks this against the README ledger table and the
# prompt files.
ARM_PROMPTS = (
    "game-melon-jelly",
    "game-lava-lamp",
    "game-minecraft",
    "scene-meridian-launch",
    "scene-sunset-ocean",
    "game-horror-house",
    "game-last-flight",
    "game-cities-skylines",
    "game-mario-kart",
    "game-weichensteller",
    "game-rubiks-cube",
    "creative-water-bottle",
    "reasoning-seating-puzzle",
    "servicenow-loaner-request",
)



class SelectionError(ValueError):
    """A prompt selection that cannot be read; the message says why."""


_SELECTION_ITEM = re.compile(r"([0-9]+)(?:\s*-\s*([0-9]+))?")
_MAX_DIGITS = 6  # far above the arm size; also keeps int() away from its digit limit


def _position(digits):
    if len(digits) > _MAX_DIGITS or not 1 <= int(digits) <= len(ARM_PROMPTS):
        raise SelectionError("%s is not a prompt number from 1 to %d" % (digits[:20], len(ARM_PROMPTS)))
    return int(digits)


def parse_selection(text):
    """Turn the user's answer into arm prompt ids, in arm order, repeats collapsed.

    Accepted: ``all`` on its own (any case), or comma-separated items that are
    each ``N`` or ``N-M`` (ASCII digits, spaces allowed around items and around
    the dash). Anything else raises ``SelectionError``: the answer is never
    guessed at.
    """
    text = (text or "").strip()
    if not text:
        raise SelectionError("the answer is empty")
    if text.lower() == "all":
        return ARM_PROMPTS
    chosen = set()
    for item in text.split(","):
        item = item.strip()
        match = _SELECTION_ITEM.fullmatch(item)
        if not match:
            raise SelectionError("%r is not a number or a range such as 3-6" % item[:20])
        first = _position(match.group(1))
        last = first if match.group(2) is None else _position(match.group(2))
        if last < first:
            raise SelectionError("the range %s is backwards" % item)
        chosen.update(range(first, last + 1))
    return tuple(pid for i, pid in enumerate(ARM_PROMPTS, 1) if i in chosen)


def resolve_prompts(value):
    """Arm prompt ids for ``--prompts``: ``None`` or ``all`` is the whole arm.

    Otherwise comma-separated arm ids, returned in arm order with repeats
    collapsed. Anything else raises ``SelectionError``; there is no fallback to
    the whole arm.
    """
    if value is None or value == "all":
        return ARM_PROMPTS
    if value == "":
        raise SelectionError("--prompts is empty; pass arm prompt ids or all")
    wanted = set()
    for pid in value.split(","):
        if not pid:
            raise SelectionError("--prompts has an empty item")
        if pid not in ARM_PROMPTS:
            raise SelectionError("%s is not one of the %d arm prompts" % (pid[:60], len(ARM_PROMPTS)))
        wanted.add(pid)
    return tuple(pid for pid in ARM_PROMPTS if pid in wanted)


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
    try:
        session_effort(environ)
    except ValueError as exc:
        return str(exc)
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


def launch(claude_bin, slash, model, effort, timeout, repo_root, environ, pass_fds=()):
    """Start one child and wait for it; kill its whole process group on timeout.

    ``pass_fds`` stay open in the child. The batch passes its worktree lock, so
    a child that outlives a dead helper (it runs in its own session) keeps the
    worktree "in use" until it exits.
    """
    cmd = build_command(claude_bin, slash, model, effort)
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(repo_root), env=build_env(environ), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True, pass_fds=pass_fds,
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
    """What the helper keeps of a child: never the result text, only markers.

    ``metrics`` is the six run-file values (see ``run_metrics``), or ``None``
    when the child's output carries no usable usage data. ``metrics_error`` is
    the class name of an unexpected exception raised while deriving them
    (``metrics`` is then ``None``), else ``None``.
    """

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
    metrics: dict | None = None
    metrics_error: str | None = None


def _result_object(raw):
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if isinstance(data, list):
        results = [e for e in data if isinstance(e, dict) and e.get("type") == "result"]
        return results[-1] if results else None
    return data if isinstance(data, dict) else None


# The run file's keys, in contract order, with where each comes from.
METRIC_KEYS = ("duration_seconds", "input_tokens", "output_tokens",
               "cache_read_tokens", "cache_write_tokens", "cost_usd")
_TOKEN_FIELDS = (("input_tokens", "input_tokens"),
                 ("output_tokens", "output_tokens"),
                 ("cache_read_tokens", "cache_read_input_tokens"),
                 ("cache_write_tokens", "cache_creation_input_tokens"))


def _finite(value):
    """Whether ``value`` is a finite number; one too big for a float (``OverflowError``) is not."""
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _count(value):
    """``value`` if it is a non-negative finite ``int`` (never a ``bool``), else ``None``."""
    ok = isinstance(value, int) and not isinstance(value, bool) and value >= 0 and _finite(value)
    return value if ok else None


def _amount(value):
    """``value`` if it is a non-negative finite ``int`` or ``float`` (never a ``bool``), else ``None``."""
    ok = (isinstance(value, (int, float)) and not isinstance(value, bool)
          and _finite(value) and value >= 0)
    return value if ok else None


def run_metrics(data):
    """The six run-file values from a child's JSON result object, or ``None``.

    ``data`` is the parsed result. Usable means: ``usage`` is a dict whose four
    token fields are non-negative ints, ``duration_ms`` and ``total_cost_usd``
    are non-negative finite numbers (no bools anywhere; a number too big to be
    checked as a float is not finite), and the four token
    counts add up to more than zero, which excludes an API error before any
    model call. Anything else gives ``None``, never a partial result. Other
    fields, ``is_error`` and ``subtype`` do not matter.
    """
    if not isinstance(data, dict) or not isinstance(data.get("usage"), dict):
        return None
    usage = data["usage"]
    tokens = {key: _count(usage.get(source)) for key, source in _TOKEN_FIELDS}
    duration, cost = _amount(data.get("duration_ms")), _amount(data.get("total_cost_usd"))
    if None in tokens.values() or duration is None or cost is None or not sum(tokens.values()):
        return None
    return {"duration_seconds": round(duration / 1000, 1), **tokens, "cost_usd": round(float(cost), 6)}


def summarize(run, model):
    """Reduce a child's output to exit state, markers and denied tool names.

    Only a ``STOP:`` line or a ``run void`` line is ever taken from the result
    text; the rest of it and every ``permission_denials[].tool_input`` (which
    can contain the deliverable) are dropped here. The usage numbers become
    ``metrics``, except for a child that timed out. An unexpected exception
    while deriving them leaves ``metrics`` unset and its class name in
    ``metrics_error``; the rest of the summary is not affected.
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
    if not run.timed_out:
        try:
            out.metrics = run_metrics(data)
        except Exception as exc:  # the metrics must never stop the batch
            out.metrics, out.metrics_error = None, type(exc).__name__
    return out


# --- smoke ------------------------------------------------------------------


def make_log_dir(base=None, tag=None):
    """Create and return the log folder, outside the repo tree.

    The default name is ``<UTC>_<tag>``: two batches started in the same second
    (other model or effort) must not share a folder and overwrite each other's logs.
    """
    if base is None:
        cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ("_" + tag if tag else "")
        base = Path(cache) / "bench-run" / name
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


def expected_base(repo_root, pid, model, effort):
    """``<file_prefix>_<model_tag>_<effort>``, built from the prompt file alone."""
    data = _prompt_data(repo_root, pid)
    if not data.get("file_prefix") or not data.get("save_as"):
        raise LookupError("%s sets no file_prefix or save_as" % pid)
    return "%s_%s" % (data["file_prefix"], run_tag(model, effort)), data["save_as"]


def expected_name(repo_root, pid, model, effort):
    """Deliverable file name the child would write, e.g. ``melon-jelly_claude_fable_5_2_high.html``."""
    base, ext = expected_base(repo_root, pid, model, effort)
    return "%s.%s" % (base, ext)


def planned_names(repo_root, pid, model, effort):
    """The deliverable, meta and grading sidecar names of one run."""
    base, ext = expected_base(repo_root, pid, model, effort)
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


def sync_worktree(wt):
    """Put the worktree on a clean detached ``origin/main``; return an error string or None.

    A fetch updates the one ``origin/main`` all worktrees share. The result is
    verified: no branch, nothing changed or untracked, ``HEAD`` equal to
    ``origin/main``.
    """
    fetch = _run(["git", "fetch", "origin", "main"], cwd=wt)
    if fetch.returncode:
        return "git fetch failed: " + _first_line(fetch.stderr)
    switch = _run(["git", "switch", "--detach", "origin/main"], cwd=wt)
    if switch.returncode:
        return "git switch --detach failed: " + _first_line(switch.stderr)
    try:
        tree = tree_state(wt)
    except GitError as exc:
        return str(exc)
    head, origin = _git_out(wt, "rev-parse", "HEAD"), _git_out(wt, "rev-parse", "origin/main")
    if tree.branch or tree.lines or not head or head != origin:
        return "worktree is not a clean detached origin/main"
    return None


def settle(wt, log_dir, pid, model, effort, start):
    """Return the worktree to a clean detached ``origin/main`` between children.

    ``start`` is the commit the child began on. Tolerated leftovers: this
    prompt's own planned paths, still untracked (moved into the log folder,
    never deleted or opened), a clean tree on the child's branch (it keeps the
    commit) and a clean detached tree still at ``start``. Anything else halts,
    in particular a commit made without a branch, which switching away would orphan.
    Returns a halt reason or None.
    """
    halt = "tree dirty after %s" % pid
    tree = tree_state(wt)
    if tree.lines:
        planned = planned_names(wt, pid, model, effort)
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
            shutil.move(str(Path(wt, path)), str(dest / Path(path).name))
        if tree_state(wt).lines:
            return halt
    if not tree.branch and _git_out(wt, "rev-parse", "HEAD") != start:
        return "HEAD moved without a branch after %s" % pid
    if sync_worktree(wt):
        return "could not return to origin/main after %s" % pid
    return None


# --- the batch worktree -------------------------------------------------------


class WorktreeStop(Exception):
    """The batch worktree cannot be used; the message is the STOP detail."""


def worktree_path(repo_root, model, effort):
    """``<repo>/.claude/worktrees/bench-run-<model_tag>_<effort>``; one per model and effort."""
    return Path(repo_root) / ".claude" / "worktrees" / ("bench-run-" + run_tag(model, effort))


def lock_path(wt):
    """The lock file: a sibling of the worktree, so it never shows in its status."""
    return wt.with_name(wt.name + ".lock")


def acquire_lock(wt):
    """Take the exclusive lock for ``wt``; return the open fd, or None if it is taken.

    The OS drops the lock when the last holder exits, even on SIGKILL, so it
    cannot go stale. The file itself is never deleted.
    """
    path = lock_path(wt)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return fd


def lock_in_use(wt):
    """Whether another process holds the lock. Creates nothing."""
    try:
        fd = os.open(lock_path(wt), os.O_RDONLY)
    except FileNotFoundError:
        return False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def in_use_message(wt, model, effort):
    return "%s is in use by another batch run for %s at effort %s" % (wt, model, effort)


def _registered_worktrees(repo_root):
    """``{resolved path: prunable}`` from ``git worktree list --porcelain``."""
    done = _run(["git", "worktree", "list", "--porcelain"], cwd=repo_root)
    if done.returncode:
        raise WorktreeStop("git worktree list failed: " + _first_line(done.stderr))
    found, current = {}, None
    for line in done.stdout.splitlines():
        if line.startswith("worktree "):
            current = Path(line[len("worktree "):]).resolve()
            found[current] = False
        elif line.startswith("prunable") and current is not None:
            found[current] = True
    return found


def classify_worktree(repo_root, wt):
    """Decide what setup would do: ``create``, ``prune and create`` or ``reuse``.

    Raises ``WorktreeStop`` for a folder that is not a worktree of this checkout
    and for a kept worktree that is not clean or that is detached at a commit
    not on ``origin/main`` (switching away would orphan it; one on a branch is
    reusable, the branch keeps its commit). This runs before any git
    command inside ``wt``: in an unregistered folder git walks up to the main
    checkout and would act on that instead.
    """
    registered = _registered_worktrees(repo_root)
    key = Path(wt).resolve()
    if key not in registered:
        if Path(wt).exists():
            raise WorktreeStop("%s exists but is not a worktree of this checkout; remove it" % wt)
        return "create"
    if not Path(wt).exists():
        return "prune and create"
    top = _git_out(wt, "rev-parse", "--show-toplevel")
    if not top or Path(top).resolve() != key:
        raise WorktreeStop("%s exists but is not a worktree of this checkout; remove it" % wt)
    status = _run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=wt)
    if status.returncode:
        raise WorktreeStop("git status failed in %s: %s" % (wt, _first_line(status.stderr)))
    lines = [ln for ln in status.stdout.splitlines() if ln.strip()]
    if lines:
        raise WorktreeStop("%s has %d changed or untracked paths from an earlier run; "
                           "inspect it, then git worktree remove --force %s" % (wt, len(lines), wt))
    if not _git_out(wt, "branch", "--show-current"):
        head = _git_out(wt, "rev-parse", "HEAD")
        if not head:
            raise WorktreeStop("cannot read HEAD of %s" % wt)
        if _run(["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"], cwd=wt).returncode:
            raise WorktreeStop("%s is detached at %s, which is not on origin/main; inspect it, "
                               "put a branch on the commit to keep it, then git worktree remove %s"
                               % (wt, head, wt))
    return "reuse"


def setup_worktree(repo_root, wt):
    """Create or reuse the worktree and sync it to ``origin/main``; return the action taken."""
    action = classify_worktree(repo_root, wt)
    if action == "prune and create":
        _run(["git", "worktree", "prune"], cwd=repo_root)
    if action != "reuse":
        Path(wt).parent.mkdir(parents=True, exist_ok=True)
        add = _run(["git", "worktree", "add", "--detach", str(wt), "origin/main"], cwd=repo_root)
        if add.returncode:
            raise WorktreeStop("cannot create %s: %s" % (wt, _first_line(add.stderr)))
    err = sync_worktree(wt)
    if err:
        raise WorktreeStop("cannot sync %s to origin/main: %s" % (wt, err))
    return action


def finish_worktree(repo_root, wt, halt):
    """Remove the worktree after a run without a halt, else keep it. Returns the report line.

    Never ``--force``: ``git worktree remove`` refuses a worktree with
    untracked files and ignores git-ignored ones such as ``.bench-run/``.
    """
    if halt:
        return "worktree: kept %s (halted; the next run reuses it only if it is clean and on a branch or origin/main)" % wt
    done = _run(["git", "worktree", "remove", str(wt)], cwd=repo_root)
    if done.returncode == 0:
        return "worktree: removed %s" % wt
    return "worktree: kept %s (git worktree remove failed: %s)" % (wt, _first_line(done.stderr))


def check_worktree(args, environ, repo_root, usable):
    """The dry-run ``worktree`` check: where one would be created, or why it cannot be used."""
    if not usable:
        return Check("worktree", True, "skipped, model or effort unusable")
    effort = environ["CLAUDE_EFFORT"]
    wt = worktree_path(repo_root, args.model, effort)
    if lock_in_use(wt):
        return Check("worktree", False, in_use_message(wt, args.model, effort))
    try:
        return Check("worktree", True, "would %s %s" % (classify_worktree(repo_root, wt), wt))
    except WorktreeStop as exc:
        return Check("worktree", False, str(exc))


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
        # Any valid level will do here: this only proves every prompt file names a result.
        for pid in ARM_PROMPTS:
            try:
                expected_name(repo_root, pid, args.model, EFFORT_LEVELS[0])
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
    # Untracked files here are harmless: the children run in the worktree. Edited
    # tracked files are not: this checkout's helper code runs the batch.
    status = _run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo_root)
    if status.returncode:
        checks.append(Check("no tracked changes", False, "git status failed"))
    else:
        dirty = [ln for ln in status.stdout.splitlines() if ln.strip()]
        checks.append(Check("no tracked changes", not dirty, "%d tracked changes" % len(dirty)))
    auth = _run(["gh", "auth", "status"], cwd=repo_root)
    checks.append(Check("gh auth", auth.returncode == 0,
                        "" if auth.returncode == 0 else _first_line(auth.stderr or auth.stdout)))
    return checks


# --- batch ------------------------------------------------------------------


def _say(text=""):
    """Print one line. Text the output stream cannot encode (a lone surrogate, a non-ASCII
    character on an ASCII stream) is printed with backslash escapes instead of raising."""
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(str(text).encode(encoding, "backslashreplace").decode(encoding, "replace"), flush=True)


METRICS_START = "<!-- run-metrics -->"
METRICS_END = "<!-- /run-metrics -->"
_CLOSES_LINE = re.compile(r"(?m)^Closes #\d+\r?$")


def metrics_section(metrics, run_path):
    """The PR description's "Run metrics" section, between its two markers."""
    if metrics is None:
        lines = ["Unavailable: the JSON output of the batch session that generated this result "
                 "carried no usable usage data, so no run file was written."]
    else:
        lines = [
            "Duration %.1f s, {:,} output tokens, cost %.6f USD.".format(metrics["output_tokens"])
            % (metrics["duration_seconds"], metrics["cost_usd"]),
            "",
            "| Tokens | Count |",
            "|---|---:|",
            "| Input | {:,} |".format(metrics["input_tokens"]),
            "| Output | {:,} |".format(metrics["output_tokens"]),
            "| Cache read | {:,} |".format(metrics["cache_read_tokens"]),
            "| Cache write | {:,} |".format(metrics["cache_write_tokens"]),
            "",
            "Read by `harness/bench_run_all.py` from the JSON output of the batch session that "
            "generated this result, after it exited; that session cannot observe its own usage. "
            "Recorded in `%s`." % run_path,
        ]
    return "\n".join([METRICS_START, "## Run metrics", "", *lines, METRICS_END])


def splice_section(body, section):
    """Put ``section`` into a PR description and return the new text.

    A span between the two markers is replaced. Otherwise the section goes in
    front of the first line that is exactly ``Closes #<n>``, or at the end.
    """
    body = body or ""
    start = body.find(METRICS_START)
    end = body.find(METRICS_END, start + len(METRICS_START)) if start >= 0 else -1
    if start >= 0 and end >= 0:
        return body[:start] + section + body[end + len(METRICS_END):]
    closes = _CLOSES_LINE.search(body)
    if closes is None:
        head = body.rstrip("\n")
        return (head + "\n\n" if head else "") + section + "\n"
    head = body[:closes.start()].rstrip("\n")
    return (head + "\n\n" if head else "") + section + "\n\n" + body[closes.start():]


GH_TIMEOUT = 120
RUN_SUFFIX = ".run.json"
REASON_LIMIT = 200
_FAMILY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class _MetricsStop(Exception):
    """One step of ``record_metrics`` failed; the message is the one-line reason."""


def _reason(text, fallback):
    """First line of ``text`` on one line with single spaces, at most ``REASON_LIMIT`` characters."""
    line = " ".join(_first_line(text or "").split())[:REASON_LIMIT].rstrip()
    return line or fallback


def _gh(wt, *args):
    """Run ``gh`` in ``wt``; return its stdout or raise ``_MetricsStop`` with a one-line reason.

    The reason never includes the command line, which can carry the run file.
    """
    try:
        done = _run(["gh", *args], cwd=wt, timeout=GH_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise _MetricsStop("gh timed out after %d s" % GH_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        raise _MetricsStop(_reason(str(exc), type(exc).__name__))
    if done.returncode:
        raise _MetricsStop(_reason(done.stderr, "gh exited %d" % done.returncode))
    return done.stdout


def _read_result_pr(wt, number, prefix, base, name, model, effort):
    """Check PR ``number`` is this result's open, same-repo PR; return ``(head branch, body, run file path)``.

    Raises ``_MetricsStop`` before anything is written when it is not: not
    open, from a fork, on another branch, not holding exactly one file named
    like the deliverable under ``results/<family>/``, or already holding the
    run file.
    """
    out = _gh(wt, "pr", "view", str(number), "--json", "state,isCrossRepository,headRefName,body,files")
    try:
        info = json.loads(out)
        state, fork, head, body, files = (info["state"], info["isCrossRepository"], info["headRefName"],
                                          info["body"], info["files"])
        paths = [f["path"] for f in files]
        shaped = (isinstance(state, str) and isinstance(fork, bool) and isinstance(head, str)
                  and (body is None or isinstance(body, str)) and all(isinstance(p, str) for p in paths))
    except (ValueError, KeyError, TypeError):
        shaped = False
    if not shaped:
        raise _MetricsStop("PR #%d could not be read: unexpected gh output" % number)
    if state != "OPEN":
        raise _MetricsStop("PR #%d is not open" % number)
    if fork:
        raise _MetricsStop("PR #%d comes from a fork" % number)
    branch = r"feat/\d+-%s-%s-result" % (re.escape(prefix), re.escape(run_tag(model, effort).replace("_", "-")))
    if not re.fullmatch(branch, head):
        raise _MetricsStop(_reason("branch %s is not this result's branch" % head, ""))
    named = [p for p in paths if p.rsplit("/", 1)[-1] == name]
    parts = named[0].split("/") if len(named) == 1 else []
    if not (len(parts) == 3 and parts[0] == "results" and _FAMILY.fullmatch(parts[1]) and parts[2] == name):
        raise _MetricsStop("PR #%d does not have exactly one deliverable" % number)
    run_path = "results/%s/%s%s" % (parts[1], base, RUN_SUFFIX)
    if run_path in paths:
        raise _MetricsStop("PR #%d already has the run file" % number)
    return head, body or "", run_path


def _record_metrics(wt, log_dir, pid, model, effort, number, metrics):
    """Document one result PR's run metrics; return a report note, or ``None`` when all went well.

    Runs only for a PR this batch's child just opened. Checks the PR first,
    then adds ``<deliverable stem>.run.json`` to the PR's head branch with one
    contents-API PUT (a commit of its own; the worktree is never touched) and
    updates the PR description's marked "Run metrics" section. ``metrics`` of
    ``None`` writes no file and says "unavailable" in the description. Any
    failure leaves the PR as the child opened it, plus at most the one added
    file, and becomes a note; nothing is raised and nothing is printed. An
    unexpected exception becomes a note with its class name as the reason
    (``KeyboardInterrupt`` and ``SystemExit`` still propagate). A PR body and
    result text are never printed. The note is raw; ``record_metrics`` cleans it.
    """
    usable = metrics is not None
    not_added = "run file not added: %s" if usable else "run metrics unavailable, PR description not updated: %s"
    not_updated = ("run file added, PR description not updated: %s" if usable
                   else "run metrics unavailable, PR description not updated: %s")
    stage = not_added
    try:
        try:
            base, ext = expected_base(wt, pid, model, effort)
            prefix = _prompt_data(wt, pid)["file_prefix"]
        except (LookupError, ValueError, OSError) as exc:
            return "run file not added: " + _reason(str(exc), "prompt file unreadable")
        try:
            head, body, run_path = _read_result_pr(wt, number, prefix, base, "%s.%s" % (base, ext),
                                                   model, effort)
        except _MetricsStop as exc:
            return not_added % exc
        if usable:
            content = base64.b64encode((json.dumps(metrics, indent=2) + "\n").encode("utf-8")).decode("ascii")
            try:
                _gh(wt, "api", "--method", "PUT", "repos/{owner}/{repo}/contents/" + run_path,
                    "-f", "message=feat(results): add %s %s %s run metrics" % (prefix, model, effort),
                    "-f", "content=" + content, "-f", "branch=" + head)
            except _MetricsStop as exc:
                return not_added % exc
        stage = not_updated
        body_file = Path(log_dir) / (pid + ".pr-body.md")
        try:
            body_file.write_text(splice_section(body, metrics_section(metrics, run_path)), encoding="utf-8")
            _gh(wt, "pr", "edit", str(number), "--body-file", str(body_file))
        except UnicodeEncodeError:  # e.g. a lone surrogate; the body is never altered to fit
            return not_updated % "PR description is not valid UTF-8 text"
        except OSError as exc:
            return not_updated % _reason("cannot write the PR description file: %s" % exc.strerror,
                                         "write failed")
        except _MetricsStop as exc:
            return not_updated % exc
    except Exception as exc:  # the metrics step must never stop the batch
        return stage % type(exc).__name__
    return None if usable else "run metrics unavailable"


def _clean_note(text):
    """``text`` as one printable report-line fragment of at most ``REASON_LIMIT`` characters.

    Characters UTF-8 cannot encode (lone surrogates) become ``?``; control
    characters and every run of whitespace become one space, because the
    report line format splits on two spaces.
    """
    text = text.encode("utf-8", "replace").decode("utf-8")
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
    return " ".join(text.split())[:REASON_LIMIT].rstrip()


def record_metrics(wt, log_dir, pid, model, effort, number, metrics, metrics_error=None):
    """Document one result PR's run metrics; return a report note, or ``None`` when all went well.

    Does the work of ``_record_metrics`` (see there). ``metrics_error`` is the
    reason ``summarize`` could not derive ``metrics``; it ends the "unavailable"
    note. This is the single point where a note leaves the metrics step: the
    returned text is always printable on one line (see ``_clean_note``),
    whatever the exception messages, ``gh`` output, branch names or paths in it.
    """
    note = _record_metrics(wt, log_dir, pid, model, effort, number, metrics)
    if note == "run metrics unavailable" and metrics_error:
        note += ": " + metrics_error
    return None if note is None else _clean_note(note)


def describe(summary, pr, metrics_note=None):
    """Outcome string and PR url for one finished child.

    ``metrics_note`` (from ``record_metrics``) goes last inside the parentheses.
    """
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
    if metrics_note:
        notes.append(metrics_note)
    if notes:
        outcome += " (" + "; ".join(notes) + ")"
    return outcome, (pr[2] if pr else "-")


def run_batch(args, environ, wt, log_dir, lock_fd, prompts):
    """The loop over ``prompts`` in the worktree ``wt``: skip check, child, outcome, cleanup.

    Returns (rows, halt reason): one row per selected prompt. ``lock_fd`` is
    handed to every child (``None`` hands none). ``prompts`` has no default, so
    no caller can run the whole arm by leaving it out.
    """
    repo_root = wt
    rows, halt = [], None
    total = len(prompts)
    effort = environ["CLAUDE_EFFORT"]
    for i, pid in enumerate(prompts, 1):
        if halt:
            rows.append((pid, "not-started: " + halt, "-"))
            continue
        name = expected_name(repo_root, pid, args.model, effort)
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
        start = _git_out(wt, "rev-parse", "HEAD")
        if not start:
            halt = "cannot read HEAD before %s" % pid
            rows.append((pid, "not-started: " + halt, "-"))
            continue
        _say("[%d/%d] %s  running ..." % (i, total, pid))
        run = launch(args.claude, "/bench-run " + pid, args.model, effort,
                     args.timeout, wt, environ, pass_fds=() if lock_fd is None else (lock_fd,))
        write_child_log(log_dir, pid, run)
        summary = summarize(run, args.model)
        try:
            after = lookup(snapshot(repo_root), name)
        except GitError:
            after = None
        pr = after if after and after[0] == "pr" else None
        note = (record_metrics(wt, log_dir, pid, args.model, effort, pr[1], summary.metrics,
                               summary.metrics_error) if pr else None)
        outcome, url = describe(summary, pr, note)
        rows.append((pid, outcome, url))
        _say("[%d/%d] %s  %s" % (i, total, pid, outcome))
        try:
            halt = settle(wt, log_dir, pid, args.model, effort, start)
        except GitError as exc:
            halt = "tree check failed after %s: %s" % (pid, exc)
    return rows, halt


def merge_step(args, environ, repo_root, halt):
    """Run the gated merge command if it exists, else list the open PRs. Returns ok.

    ``repo_root`` is the batch worktree: the merge command runs its copy.
    """
    if halt:
        _say("merge step: skipped (%s)" % printable(halt))
        return False
    if Path(repo_root, MERGE_SCRIPT).is_file():
        try:
            tree = tree_state(repo_root)
        except GitError as exc:
            _say("merge step: skipped (%s)" % printable(exc))
            return False
        if tree.lines or tree.branch:
            _say("merge step: skipped (worktree not clean and detached)")
            return False
        try:
            done = _run([sys.executable, MERGE_SCRIPT, "--model", args.model, MERGE_OPT_IN],
                        cwd=repo_root, timeout=MERGE_TIMEOUT)
        except subprocess.TimeoutExpired:
            _say("merge step: ran %s, timed out after %d s" % (MERGE_SCRIPT, MERGE_TIMEOUT))
            return False
        for text in (done.stdout, done.stderr):
            # split("\n"), not splitlines(): \x85, \u2028 and \x1c-\x1e must not become lines.
            lines = text.split("\n")
            for line in lines[:-1] if lines[-1] == "" else lines:
                _say(printable(line))
        _say("merge step: ran %s, exit %d" % (MERGE_SCRIPT, done.returncode))
        return done.returncode == 0
    _say("merge step: %s not present; open PRs for this arm:" % MERGE_SCRIPT)
    try:
        snap = snapshot(repo_root)
    except GitError as exc:
        _say("  cannot list: %s" % printable(exc))
        return False
    by_name = {expected_name(repo_root, pid, args.model, environ["CLAUDE_EFFORT"]): pid
               for pid in ARM_PROMPTS}
    found = [(n, u, by_name[nm]) for n, u, names in snap.prs for nm in sorted(names) if nm in by_name]
    for number, url, pid in found:
        _say("  #%d %s (%s)" % (number, printable(url), pid))
    if not found:
        _say("  none")
    return True


CATEGORIES = ("pr-opened", "skipped", "timed-out", "failed", "ended without PR", "not-started")


def report(rows, log_dir, model, effort, worktree_line=None):
    _say()
    _say("report: %s at effort %s" % (model, effort))
    for pid, outcome, url in rows:
        _say("%s  %s  %s" % (pid, outcome, url))
    _say()
    for cat in CATEGORIES:
        n = sum(1 for _, outcome, _ in rows if outcome.startswith(cat))
        if n:
            _say("%s: %d" % (cat, n))
    _say("log folder: %s" % log_dir)
    if worktree_line:
        _say(worktree_line)


def run_dry(args, environ, repo_root, checks, prompts):
    _say("dry-run: no child will be started")
    for c in checks:
        _say("check %s: %s%s" % ("ok" if c.ok else "FAIL", c.name, (" - " + c.detail) if c.detail else ""))
    for c in checks:
        if not c.ok:
            _say("STOP: %s: %s" % (c.name, c.detail))
    if all(c.ok for c in checks if c.name in ("model", "effort", "prompts")):
        try:
            snap = snapshot(repo_root)
        except GitError as exc:
            _say("check FAIL: skip lookup - %s" % exc)
            snap = None
            checks.append(Check("skip lookup", False, str(exc)))
        if snap is not None:
            for pid in prompts:
                name = expected_name(repo_root, pid, args.model, environ["CLAUDE_EFFORT"])
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
    try:
        prompts = resolve_prompts(args.prompts)
    except SelectionError as exc:
        _say("STOP: %s" % exc)
        return 2
    checks = preflight(args, environ, repo_root)
    if args.dry_run:
        usable = all(c.ok for c in checks if c.name in ("model", "effort"))
        checks.append(check_worktree(args, environ, repo_root, usable))
        return run_dry(args, environ, repo_root, checks, prompts)
    failed = [c for c in checks if not c.ok]
    if failed:
        for c in failed:
            _say("STOP: %s: %s" % (c.name, c.detail))
        return 2
    effort = environ["CLAUDE_EFFORT"]
    wt = worktree_path(repo_root, args.model, effort)
    lock_fd = acquire_lock(wt)
    if lock_fd is None:
        _say("STOP: worktree: " + in_use_message(wt, args.model, effort))
        return 2
    try:
        try:
            setup_worktree(repo_root, wt)
        except WorktreeStop as exc:
            _say("STOP: worktree: %s" % exc)
            return 2
        log_dir = make_log_dir(args.log_dir, run_tag(args.model, effort))
        rows, halt = run_batch(args, environ, wt, log_dir, lock_fd, prompts)
        merge_ok = merge_step(args, environ, wt, halt)
        report(rows, log_dir, args.model, effort, finish_worktree(repo_root, wt, halt))
    finally:
        os.close(lock_fd)
    clean = all(o.startswith(("pr-opened", "skipped")) for _, o, _ in rows)
    return 0 if clean and merge_ok and not halt else 1


# --- list and select --------------------------------------------------------


def run_list(args, environ, repo_root):
    """Print the arm's prompts numbered, each marked with its result state.

    Read-only: one ``git fetch origin main`` and the ``snapshot`` calls, no
    worktree, lock, log folder or child. The effort level comes from
    ``session_effort``, not ``check_effort``: the binary is checked later, by
    the run itself.
    """
    stops, effort = [], None
    err = check_model(args.model)
    if err:
        stops.append(err)
    try:
        effort = session_effort(environ)
    except ValueError as exc:
        stops.append(str(exc))
    if stops:
        for msg in stops:
            _say("STOP: " + msg)
        return 2
    try:
        names = [expected_name(repo_root, pid, args.model, effort) for pid in ARM_PROMPTS]
    except (LookupError, ValueError, OSError) as exc:
        _say("STOP: prompts: %s" % exc)
        return 2
    fetch = _run(["git", "fetch", "origin", "main"], cwd=repo_root)
    if fetch.returncode:
        _say("STOP: git fetch failed: " + _first_line(fetch.stderr))
        return 2
    try:
        snap = snapshot(repo_root)
    except GitError as exc:
        _say("STOP: %s" % exc)
        return 2
    _say("arm: %d prompts for %s at effort %s" % (len(ARM_PROMPTS), args.model, effort))
    for i, (pid, name) in enumerate(zip(ARM_PROMPTS, names), 1):
        hit = lookup(snap, name)
        mark = "no result" if not hit else (
            "has result (on origin/main)" if hit[0] == "origin/main" else "has result (open PR #%d)" % hit[1])
        _say("%2d. %s  %s" % (i, pid, mark))
    return 0


def run_select(args):
    """Turn the raw answer in ``--select`` into a ``prompts:`` line. Calls no git, gh or claude."""
    try:
        chosen = parse_selection(args.select)
    except SelectionError as exc:
        _say("INVALID: %s" % exc)
        return 3
    _say("prompts: " + ("all" if chosen == ARM_PROMPTS else ",".join(chosen)))
    return 0


# --- command line -----------------------------------------------------------


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--model", required=True, help="exact model id of the calling session")
    p.add_argument("--dry-run", action="store_true", help="show the checks and the plan; start no child")
    modes = p.add_mutually_exclusive_group()
    modes.add_argument("--smoke", metavar="PROMPT_ID", help="start one /bench-run <id> --dry-run child")
    modes.add_argument("--list", action="store_true",
                       help="print the arm's prompts numbered, marked with their result state; start nothing")
    modes.add_argument("--select", metavar="ANSWER",
                       help="turn the user's answer (all, 2, 1,4,7, 3-6) into a prompts: line; start nothing")
    p.add_argument("--prompts", metavar="IDS",
                   help="run only these comma-separated arm prompt ids, or all (default: all)")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="seconds per child (default 3600)")
    p.add_argument("--claude", default="claude", help="path to the claude binary")
    p.add_argument("--log-dir", help="log folder (default: ~/.cache/bench-run/<UTC>_<run tag>/)")
    args = p.parse_args(argv)
    if args.prompts is not None and (args.list or args.select is not None or args.smoke is not None):
        p.error("--prompts cannot be combined with --smoke, --list or --select")
    return args


def main(argv=None, environ=None, repo_root=REPO_ROOT):
    args = parse_args(argv)
    environ = os.environ if environ is None else environ
    repo_root = Path(repo_root)
    if args.list:
        return run_list(args, environ, repo_root)
    if args.select is not None:
        return run_select(args)
    if args.smoke:
        return run_smoke(args, environ, repo_root)
    return run_all(args, environ, repo_root)


if __name__ == "__main__":
    sys.exit(main())
