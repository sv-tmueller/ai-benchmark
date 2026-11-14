#!/usr/bin/env python3
"""Single-prompt helper behind the ``/bench-run`` skill.

Run from the repo root, one mode per call, ids unquoted::

    python3 harness/bench_run.py plan       <prompt-id> <model-id>
    python3 harness/bench_run.py meta       <prompt-id> <model-id>
    python3 harness/bench_run.py prompt     <prompt-id> <model-id>
    python3 harness/bench_run.py issue-body <prompt-id> <model-id>
    python3 harness/bench_run.py pr-body    <prompt-id> <model-id> <N> [--footer "<line>"]
    python3 harness/bench_run.py grade      <prompt-id> <model-id>

The mode comes first so a permission rule can name one mode. Multi-line
text (issue body, PR body, grade output) goes through files under
``.bench-run/`` (git-ignored) that this script writes, so the skill's steps
stay one-line commands.

Every mode except ``prompt`` reads the session's effort level from
``CLAUDE_EFFORT`` and stops if it is unset or unknown: the level is part of
the result file name (``<prefix>_<model_tag>_<effort>.<ext>``).

``plan`` and ``meta`` print only ``key: value`` lines and a sidecar preview,
never any content from a result file. Failures print one ``STOP: ...`` line
on stdout and exit 1. Stdlib only; Python 3.11+.
"""

import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# `python3 harness/bench_run.py` puts harness/ on sys.path, not the repo
# root; make the `harness` package importable the same way grade.py does.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.modes._common import derive_model, run_tag, session_effort  # noqa: E402

MODES = ("plan", "meta", "prompt", "issue-body", "pr-body", "grade")
WORK_DIR = ".bench-run"
KINDS = {"html": "single HTML file", "xml": "single XML file"}
NO_GRADING = "no [grading] rule; no playability verdict written; review pending"


class Stop(Exception):
    """A condition the skill must relay to the user and end on."""


def _run(cmd, cwd=None):
    """Run a read-only git or gh command. The one seam the tests replace."""
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


# --- resolving a prompt -----------------------------------------------------


@dataclass
class Plan:
    pid: str
    toml: str
    prompt: dict
    folder: str
    prefix: str
    ext: str
    kind: str
    model_id: str
    effort: str
    tag: str  # the run tag: model tag, "_", effort
    target: str
    meta_path: str
    grade_path: str
    gmode: str | None

    @property
    def base_name(self):
        return "%s_%s" % (self.prefix, self.tag)

    def work_path(self, suffix):
        return "%s/%s.%s" % (WORK_DIR, self.base_name, suffix)


def find_prompt(repo_root, arg):
    """Return ``(path, data)`` for the one non-parametrized prompt matching ``arg``."""
    tomls = [p for p in sorted(Path(repo_root, "prompts").glob("*.toml"))
             if not p.name.endswith(".fixtures.toml")]
    data = {p: tomllib.loads(p.read_text(encoding="utf-8")) for p in tomls}
    hits = [p for p in tomls if data[p].get("id") == arg] or [p for p in tomls if p.stem == arg]
    if len(hits) != 1:
        raise Stop("%d prompts match %r; need exactly one" % (len(hits), arg))
    path = hits[0]
    if Path(repo_root, "prompts", path.stem + ".fixtures.toml").exists():
        raise Stop("%s is parametrized (has a fixtures file); refusing" % data[path]["id"])
    return path, data[path]


def resolve(repo_root, arg, model, effort):
    """Resolve prompt, results folder, extension and paths. No overwrite checks."""
    tpath, prompt = find_prompt(repo_root, arg)
    pid = prompt["id"]

    # folder from the existing metas of this prompt, else the file prefix
    metas = []
    for m in sorted(Path(repo_root, "results").glob("*/*.meta.json")):
        try:
            meta = json.loads(m.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if meta.get("prompt_id") == pid:
            metas.append((m, meta))
    prefix = prompt.get("file_prefix") or tpath.stem
    folders = sorted({m.parent.name for m, _ in metas})
    if len(folders) > 1:
        raise Stop("%d results folders for %s %s; ask the user which one" % (len(folders), pid, folders))
    folder = folders[0] if folders else prefix
    exts = {Path(meta["outputs"]["deliverable"]).suffix.lstrip(".") for _, meta in metas
            if isinstance(meta.get("outputs"), dict) and meta["outputs"].get("deliverable")}
    ext = prompt.get("save_as") or (exts.pop() if len(exts) == 1 else None)
    if not ext:
        raise Stop("cannot determine the extension (save_as unset, metas give %s)" % sorted(exts))

    kind = KINDS.get(ext, "text answer")

    model_id = re.sub(r"\[[^\]]*\]$", "", model.strip()).strip()
    try:
        tag = run_tag(model_id, effort)
    except ValueError:
        raise Stop("run tag from model %r and effort %r is not usable" % (model, effort)) from None
    base = "results/%s/%s_%s" % (folder, prefix, tag)
    target = "%s.%s" % (base, ext)
    if derive_model(Path(target), prompt) != tag:
        raise Stop("harness derive_model disagrees with tag %s for %s" % (tag, target))
    gmode = (prompt.get("grading") or {}).get("mode")
    return Plan(pid, tpath.name, prompt, folder, prefix, ext, kind, model_id, effort, tag,
                target, base + ".meta.json", base + "_grading.json", gmode)


def check_free(repo_root, plan, mode, run):
    """No overwrite: not on disk, not on origin/main, not in an open PR."""
    for p in ((plan.target,) if mode == "plan" else ()) + (plan.meta_path, plan.grade_path):
        if Path(repo_root, p).exists():
            raise Stop("%s already exists on disk" % p)
    for p in (plan.target, plan.meta_path, plan.grade_path):
        if run(["git", "cat-file", "-e", "origin/main:" + p], cwd=repo_root).returncode == 0:
            raise Stop("%s already exists at origin/main" % p)
    prs = run(["gh", "pr", "list", "--state", "open", "--limit", "200", "--json", "number,files"],
              cwd=repo_root)
    if prs.returncode:
        raise Stop("gh pr list failed: " + prs.stderr.strip())
    try:
        open_prs = json.loads(prs.stdout)
    except ValueError:
        raise Stop("gh pr list printed non-JSON output") from None
    for pr in open_prs:
        if any(f["path"] == plan.target for f in pr["files"]):
            raise Stop("open PR #%d already touches %s" % (pr["number"], plan.target))
    if mode == "meta":
        target = Path(repo_root, plan.target)
        if not target.is_file() or target.stat().st_size == 0:
            raise Stop("%s is missing or empty; write the deliverable first" % plan.target)


# --- the meta sidecar and the plan output -----------------------------------


def meta_text(plan, environ, meta_mode):
    """The one-shot meta sidecar, as JSON text."""
    prompt = plan.prompt
    ctx = ("The Claude Code system context was present alongside the TOML system text."
           if "system" in prompt
           else "The TOML has no system text; the Claude Code system context was present.")

    def given(key, name):
        return "%s %s" % (name, prompt[key]) if key in prompt else "%s not set in the TOML" % name

    sidecar = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if meta_mode
        else "<UTC timestamp stamped in meta mode>",
        "toml": plan.toml,
        "prompt_id": plan.pid,
        "title": prompt.get("title"),
        "endpoint": "none (generated in-session by Claude Code via /bench-run, plain one-shot; no orchestrator, no agents, no repair round)",
        "model": plan.model_id,
        "one_shot": True,
        "edits_after_generation": 0,
        "params": {
            "temperature": None,
            "max_tokens_requested_initial": None,
            "reasoning_effort": plan.effort,
            "note": "Sampling settings from the TOML (%s) could not be applied in-session; session defaults applied. "
            "reasoning_effort is the CLAUDE_EFFORT level in effect when the run started. "
            "%s finish_reason and usage are not observable in-session." % (
                given("temperature", "temperature") + "; " + given("max_tokens", "max_tokens"), ctx),
        },
        "finish_reason": None,
        "truncated": False,
        "usage": None,
        "retries": [],
        "num_retry_api_calls": 0,
        "grading": None,
        "outputs": {"deliverable": plan.target},
    }
    return json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n"


def grade_command(plan):
    return "python3 harness/bench_run.py grade %s %s" % (plan.pid, plan.model_id)


def plan_fields(plan):
    """The ``key: value`` lines of the plan output, in order."""
    dash = plan.tag.replace("_", "-")
    return [
        ("prompt_id", plan.pid),
        ("toml", plan.toml),
        ("folder", "results/" + plan.folder),
        ("prefix", plan.prefix),
        ("extension", plan.ext),
        ("kind", plan.kind),
        ("effort", plan.effort),
        ("model_tag", plan.tag + " (harness derive_model agrees)"),
        ("target", plan.target),
        ("meta", plan.meta_path),
        ("grading_sidecar", plan.grade_path),
        ("grading_mode", plan.gmode or "none"),
        ("grade_command", grade_command(plan) if plan.gmode else "none (no [grading] rule)"),
        ("issue_title", "%s: %s (%s) one-shot result" % (plan.pid, plan.model_id, plan.effort)),
        ("branch", "feat/<N>-%s-%s-result" % (plan.prefix, dash)),
        ("commit", "feat(results): add %s %s %s one-shot result (#<N>)" % (
            plan.prefix, plan.model_id, plan.effort)),
        ("pr_title", "%s (%s, %s, one-shot): result" % (plan.prefix, plan.model_id, plan.effort)),
    ]


# --- modes ------------------------------------------------------------------


def mode_plan(repo_root, plan, environ, meta_mode):
    text = meta_text(plan, environ, meta_mode)
    for key, value in plan_fields(plan):
        print("%s: %s" % (key, value))
    if meta_mode:
        Path(repo_root, plan.meta_path).write_text(text, encoding="utf-8")
        print("written: " + plan.meta_path)
    else:
        print("meta_preview:")
        print(text, end="")


def mode_prompt(repo_root, arg):
    _, prompt = find_prompt(repo_root, arg)
    print(prompt.get("system", {}).get("text", ""))
    print("-----")
    print(prompt["user"]["text"])
    for name in prompt.get("images", {}).get("files", []):
        print("image: prompts/" + name)


def _write_work(repo_root, plan, suffix, text):
    path = Path(repo_root, plan.work_path(suffix))
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return plan.work_path(suffix)


def _paths(plan):
    paths = [plan.target, plan.meta_path]
    if plan.gmode:
        paths.append(plan.grade_path)
    return paths


def issue_body(plan):
    lines = [
        "A plain one-shot of `%s` through `/bench-run` (`prompts/%s`), with no orchestrator or agents "
        "and no repair round." % (plan.pid, plan.toml),
        "",
        "Model: `%s`. Effort: `%s`. Deliverable kind: %s." % (plan.model_id, plan.effort, plan.kind),
        "",
        "Target paths:",
        "",
    ]
    lines += ["- `%s`" % p for p in _paths(plan)]
    return "\n".join(lines) + "\n"


def pr_body(plan, number, footer, grade_text):
    if plan.gmode:
        fence = "```"
        while fence in grade_text:
            fence += "`"
        grading = "%s\n%s\n%s" % (fence, grade_text.rstrip("\n"), fence)
    else:
        grading = NO_GRADING
    lines = [
        "## Summary",
        "",
        "One-shot result of `%s` at effort `%s` on `%s` (`prompts/%s`): a plain in-session one-shot through "
        "`/bench-run`, no orchestrator, no agents, no repair round. The deliverable (%s) was "
        "written in one pass and is frozen; nothing was edited afterwards." % (
            plan.model_id, plan.effort, plan.pid, plan.toml, plan.kind),
        "",
        "## Files",
        "",
    ]
    lines += ["- `%s`" % p for p in _paths(plan)]
    lines += [
        "",
        "## Grading",
        "",
        grading,
        "",
        "## In-session caveats",
        "",
        "Generated in-session by Claude Code: the TOML's temperature and max_tokens could not be "
        "applied (session defaults applied), and finish_reason and usage are not observable.",
        "",
        "Closes #%d" % number,
    ]
    if footer:
        lines += ["", footer]
    return "\n".join(lines) + "\n"


def mode_issue_body(repo_root, plan):
    print(_write_work(repo_root, plan, "issue.md", issue_body(plan)))


def mode_pr_body(repo_root, plan, number, footer):
    grade_text = ""
    if plan.gmode:
        grade_file = Path(repo_root, plan.work_path("grade.txt"))
        grade_text = grade_file.read_text(encoding="utf-8") if grade_file.is_file() else ""
        if not grade_text.strip():
            raise Stop("no saved grade output at %s; run `%s` first" % (
                plan.work_path("grade.txt"), grade_command(plan)))
    print(_write_work(repo_root, plan, "pr.md", pr_body(plan, number, footer, grade_text)))


def mode_grade(repo_root, plan, grade_script):
    if not plan.gmode:
        raise Stop("%s has no [grading] rule; nothing to grade" % plan.pid)
    script = grade_script or Path(repo_root, "harness", "grade.py")
    proc = subprocess.run([sys.executable, str(script), "--prompt", plan.pid],
                          cwd=repo_root, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    saved = Path(repo_root, plan.work_path("grade.txt"))
    if proc.returncode:
        # Only this run's own sidecar goes; other models' sidecars stay for `git restore`.
        Path(repo_root, plan.grade_path).unlink(missing_ok=True)
        saved.unlink(missing_ok=True)
        return proc.returncode
    saved.parent.mkdir(exist_ok=True)
    saved.write_text(proc.stdout, encoding="utf-8")
    return 0


def _usage():
    return Stop("usage: <plan|meta|prompt|issue-body|grade> <prompt-id> <model-id> "
                "| pr-body <prompt-id> <model-id> <N> [--footer \"<line>\"]")


def parse_pr_body_args(rest):
    """``<N> [--footer <line>]`` to ``(number, footer)``."""
    if not rest or not rest[0].isdigit() or int(rest[0]) < 1:
        raise _usage()
    footer, extra = None, rest[1:]
    if extra:
        if len(extra) != 2 or extra[0] != "--footer":
            raise _usage()
        footer = extra[1]
    return int(rest[0]), footer


def main(argv=None, environ=None, repo_root=REPO_ROOT, run=None, grade_script=None):
    """CLI entry point; returns the process exit code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    environ = os.environ if environ is None else environ
    run = run or _run
    try:
        if len(argv) < 3 or argv[0] not in MODES:
            raise _usage()
        mode, arg, model, rest = argv[0], argv[1], argv[2], argv[3:]
        if mode == "pr-body":
            number, footer = parse_pr_body_args(rest)
        elif rest:
            raise _usage()
        if mode == "prompt":
            mode_prompt(repo_root, arg)
            return 0
        try:
            effort = session_effort(environ)
        except ValueError as exc:
            raise Stop(str(exc)) from None
        plan = resolve(repo_root, arg, model, effort)
        if mode in ("plan", "meta"):
            check_free(repo_root, plan, mode, run)
            mode_plan(repo_root, plan, environ, mode == "meta")
        elif mode == "issue-body":
            mode_issue_body(repo_root, plan)
        elif mode == "pr-body":
            mode_pr_body(repo_root, plan, number, footer)
        else:
            return mode_grade(repo_root, plan, grade_script)
        return 0
    except Stop as exc:
        print("STOP: " + str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
