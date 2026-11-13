#!/usr/bin/env python3
"""Gated merge of ``/bench-run`` result PRs, then a ledger update.

Usage::

    python3 harness/merge_results.py --model <model-id> [--dry-run]

Open PRs titled ``<prefix> (<model-id>, one-shot): result`` are checked
against a gate (right prompt, right folder, exactly the result files, only new
files, green checks). PRs that pass are squash-merged one at a time. GitHub
has the last word: if it refuses a merge, the PR stays open and the refusal is
reported. The command never uses ``--admin`` or ``--auto`` and never posts
commit statuses.

Afterwards the README ledger rows for the model whose files are on ``main``
are moved from ``not run`` to ``generated, browser check pending`` through a
docs PR, opened with the GitHub API so the working tree is untouched. That PR
is never merged here.

Exit codes: 0 all merged (or nothing to do); 1 a PR was left open or the docs
PR step failed; 2 bad model id or failed preflight.
"""

import argparse
import base64
import json
import re
import subprocess
import sys
import time
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"

# Running this file directly puts `harness/` on sys.path, so make the repo
# root importable for the `harness.modes` package (same as grade.py).
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.modes._common import derive_model  # noqa: E402

META_SUFFIX = ".meta.json"
GRADING_SUFFIX = "_grading.json"
OK_BUCKETS = {"pass", "skipping"}

_TITLE_RE = re.compile(
    r"^(?P<prefix>[^\s()]+) \((?P<model>[^,()]+), one-shot\): result$"
)
_TAG_RE = re.compile(r"[a-z][a-z0-9_]*[a-z0-9]")


def normalize_model_id(raw):
    """Strip whitespace and a trailing ``[...]`` context suffix."""
    return re.sub(r"\[[^\]]*\]$", "", raw.strip()).strip()


def model_tag(model_id):
    """Return the filename tag for ``model_id`` (mirrors the bench-run skill)."""
    tag = re.sub(r"[^a-z0-9]+", "_", re.sub(r"-\d{8}$", "", model_id).lower())
    if not _TAG_RE.fullmatch(tag):
        raise ValueError("model tag %r from %r is not usable" % (tag, model_id))
    return tag


def parse_title(title):
    """Return ``(prefix, model)`` for a result PR title, else ``None``."""
    match = _TITLE_RE.match(title)
    return (match.group("prefix"), match.group("model")) if match else None


def gate(pr, checks, main_paths, prompts, model_id, tag):
    """Return every reason ``pr`` may not merge; an empty list means pass.

    ``pr`` is the ``gh pr view`` payload, ``checks`` the ``gh pr checks``
    list, ``main_paths`` the result paths on ``origin/main`` and ``prompts``
    the entries from :func:`load_prompt_files`. No I/O happens here.
    """
    reasons = []
    parsed = parse_title(pr.get("title", ""))
    if parsed is None or parsed[1] != model_id:
        reasons.append("title is not a result title for %s" % model_id)
    if pr.get("isDraft"):
        reasons.append("PR is a draft")
    if pr.get("isCrossRepository"):
        reasons.append("PR comes from a fork")
    reasons.extend(_checks_reasons(checks))
    if parsed is None:
        return reasons
    prefix = parsed[0]

    prompt = _find_prompt(prompts, prefix, reasons)
    branch_re = r"feat/\d+-%s-%s-result" % (
        re.escape(prefix), re.escape(tag.replace("_", "-")))
    if not re.fullmatch(branch_re, pr.get("headRefName", "")):
        reasons.append("branch %r does not match feat/<n>-%s-%s-result" % (
            pr.get("headRefName"), prefix, tag.replace("_", "-")))

    files = pr.get("files") or []
    family = _family_reasons(files, main_paths, prefix, reasons)
    for entry in files:
        if entry["path"] in main_paths:
            reasons.append("already on main: " + entry["path"])
        if entry.get("deletions", 0):
            reasons.append("deletes lines: " + entry["path"])
    if family and prompt is not None:
        _file_set_reasons(files, family, prefix, tag, prompt, reasons)
    return reasons


def _checks_reasons(checks):
    if not checks:
        return ["no checks reported"]
    red = [c["name"] for c in checks if c["bucket"] not in OK_BUCKETS | {"pending"}]
    pending = [c["name"] for c in checks if c["bucket"] == "pending"]
    reasons = []
    if red:
        reasons.append("checks red: " + ", ".join(red))
    if pending:
        reasons.append("checks pending: " + ", ".join(pending))
    return reasons


def _find_prompt(prompts, prefix, reasons):
    hits = [p for p in prompts if (p["data"].get("file_prefix") or p["stem"]) == prefix]
    if len(hits) != 1:
        reasons.append("prompt: %d prompts match prefix %r; need exactly one" % (
            len(hits), prefix))
        return None
    if hits[0]["fixtures"]:
        reasons.append("prompt %s is parametrized (has a fixtures file)" % hits[0]["stem"])
        return None
    return hits[0]["data"]


def _family_reasons(files, main_paths, prefix, reasons):
    """Return the single results family of ``files``, or ``None`` after a reason."""
    families = set()
    for entry in files:
        parts = entry["path"].split("/")
        if len(parts) != 3 or parts[0] != "results":
            reasons.append("wrong folder: %s is not results/<family>/<name>" % entry["path"])
            return None
        families.add(parts[1])
    if len(families) != 1:
        reasons.append("wrong folder: files span %s" % sorted(families))
        return None
    family = families.pop()
    on_main = {
        p.split("/")[1] for p in main_paths
        if p.count("/") == 2 and p.startswith("results/")
        and p.split("/")[2].startswith(prefix + "_") and p.endswith(META_SUFFIX)
    }
    if on_main != {family}:
        reasons.append("wrong folder: %s results live in %s, PR uses %s" % (
            prefix, sorted(on_main) or "no folder", family))
        return None
    return family


def _file_set_reasons(files, family, prefix, tag, prompt, reasons):
    base = "results/%s/%s_%s" % (family, prefix, tag)
    ext = prompt.get("save_as")
    if not ext:
        reasons.append("prompt has no save_as")
        return
    deliverable = "%s.%s" % (base, ext)
    wanted = {deliverable, base + META_SUFFIX}
    allowed = set(wanted)
    if "grading" in prompt:
        allowed.add(base + GRADING_SUFFIX)
    paths = {entry["path"] for entry in files}
    for path in sorted(paths - allowed):
        reasons.append("extra file: " + path)
    for path in sorted(wanted - paths):
        reasons.append("missing: " + path)
    if derive_model(Path(deliverable), prompt) != tag:
        reasons.append("derive_model disagrees with tag %s for %s" % (tag, deliverable))


def load_prompt_files(prompts_dir):
    """Return ``[{"stem", "data", "fixtures"}]`` for every non-fixtures TOML."""
    entries = []
    for path in sorted(Path(prompts_dir).glob("*.toml")):
        if path.name.endswith(".fixtures.toml"):
            continue
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        fixtures = path.with_name(path.stem + ".fixtures.toml").exists()
        entries.append({"stem": path.stem, "data": data, "fixtures": fixtures})
    return entries


def prompts_by_id(prompts):
    """Return ``{prompt_id: parsed TOML}`` for :func:`load_prompt_files` entries."""
    return {p["data"]["id"]: p["data"] for p in prompts if "id" in p["data"]}


# --- ledger -----------------------------------------------------------------

LEDGER_ROW_RE = re.compile(
    r"^\| `(?P<pid>[^`]+)` \| (?P<kind>[^|]+?) \| `(?P<path>results/[^`]+)` "
    r"\| (?P<status>[^|]+?) \|$",
    re.MULTILINE,
)
NOT_RUN = "not run"
GENERATED = "generated, browser check pending"


def ledger_rows(text, tag, prompts):
    """Return the ledger rows of ``text`` that belong to model ``tag``.

    A row belongs to the tag only when ``derive_model`` on its path, using the
    row's prompt, gives exactly ``tag``; a plain suffix match would confuse
    ``fable_5_2`` with ``claude_fable_5_2``.
    """
    rows = []
    for match in LEDGER_ROW_RE.finditer(text):
        prompt = prompts.get(match.group("pid"))
        if prompt is None:
            continue
        path = match.group("path")
        if derive_model(Path(path), prompt) == tag:
            rows.append({"pid": match.group("pid"), "path": path,
                         "status": match.group("status"), "span": match.span("status")})
    return rows


def rewrite_ledger(text, tag, prompts, main_paths):
    """Return ``(new_text, updated_rows, skipped_messages)`` for model ``tag``.

    Only ``not run`` cells whose deliverable and ``.meta.json`` sidecar are both
    in ``main_paths`` change, to :data:`GENERATED`. Everything else, including
    any later verdict label, is left alone, so a second pass is a no-op.
    """
    updated, skipped, edits = [], [], []
    for row in ledger_rows(text, tag, prompts):
        if row["status"] != NOT_RUN or row["path"] not in main_paths:
            continue
        meta = str(Path(row["path"]).with_suffix("")) + META_SUFFIX
        if meta not in main_paths:
            skipped.append("%s: left as not run: sidecar missing (%s)" % (row["pid"], meta))
            continue
        updated.append({"pid": row["pid"], "path": row["path"]})
        edits.append(row["span"])
    for start, end in reversed(edits):
        text = text[:start] + GENERATED + text[end:]
    return text, updated, skipped


# --- gh / git access --------------------------------------------------------

LIST_ARGV = ("gh", "pr", "list", "--state", "open", "--base", "main", "--limit", "200",
             "--json", "number,title,headRefName,isDraft,isCrossRepository")
VIEW_FIELDS = ("number,title,headRefName,headRefOid,isDraft,isCrossRepository,"
               "files,mergeStateStatus")
FETCH_ARGV = ("git", "fetch", "origin", "main")
LS_TREE_ARGV = ("git", "ls-tree", "-r", "--name-only", "origin/main", "--", "results")
POLL_SECONDS = 10
POLL_LIMIT = 60  # 10 minutes
UNKNOWN_RETRIES = 3
UNKNOWN_SECONDS = 2


def default_run(argv, input=None):
    """Run ``argv`` in the repo root; the one place that touches the system."""
    try:
        return subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True, input=input)
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(argv, 127, "", str(exc))


def first_line(text):
    """Return the first non-blank line of ``text`` (stripped), or ``""``."""
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


class Merger:
    """One command run: reads, gate, merges, ledger. All I/O goes through ``run``."""

    def __init__(self, model_id, tag, prompts, run, sleep, out, dry_run):
        self.model_id, self.tag = model_id, tag
        self.prompts = prompts
        self.by_id = prompts_by_id(prompts)
        self.run, self.sleep, self.out, self.dry_run = run, sleep, out, dry_run
        self.main_paths = set()
        self.failed = False
        self.merged = []
        self.planned = []
        self.planned_files = set()

    def say(self, message):
        print(message, file=self.out)

    def json_call(self, argv, want):
        """Run ``argv`` and return its parsed stdout if it is a ``want``, else ``None``."""
        proc = self.run(argv)
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            return None
        return data if isinstance(data, want) else None

    # -- orchestration -------------------------------------------------------

    def execute(self):
        for argv, label in ((("gh", "auth", "status"), "gh auth status"),
                            (FETCH_ARGV, "git fetch origin main")):
            proc = self.run(argv)
            if proc.returncode:
                self.say("preflight failed: %s: %s" % (label, first_line(proc.stderr)))
                return 2
        open_prs = self.json_call(LIST_ARGV, list)
        if open_prs is None:
            self.say("could not list open PRs")
            return 2
        if not self.read_main_paths():
            self.say("could not list results on origin/main")
            return 2

        candidates = sorted(
            (pr for pr in open_prs
             if (parsed := parse_title(pr.get("title", ""))) and parsed[1] == self.model_id),
            key=lambda pr: pr["number"])
        for pr in candidates:
            self.handle(pr["number"])
        if self.merged and not self.refresh_main():
            return 1
        return self.ledger(open_prs, had_candidates=bool(candidates))

    def read_main_paths(self):
        proc = self.run(LS_TREE_ARGV)
        if proc.returncode:
            return False
        self.main_paths = {line for line in proc.stdout.splitlines() if line}
        return True

    def refresh_main(self):
        proc = self.run(FETCH_ARGV)
        if proc.returncode:
            self.say("git fetch origin main failed after merging: %s" % first_line(proc.stderr))
            self.failed = True
            return False
        if not self.read_main_paths():
            self.say("could not list results on origin/main after merging")
            self.failed = True
            return False
        return True

    # -- one PR --------------------------------------------------------------

    def read_view(self, number):
        return self.json_call(("gh", "pr", "view", str(number), "--json", VIEW_FIELDS), dict)

    def read_checks(self, number):
        return self.json_call(("gh", "pr", "checks", str(number), "--json", "name,bucket"),
                              list) or []

    def settle_state(self, number, view):
        """Re-read a PR whose mergeStateStatus GitHub has not computed yet."""
        for _ in range(UNKNOWN_RETRIES):
            if view.get("mergeStateStatus") != "UNKNOWN":
                break
            self.sleep(UNKNOWN_SECONDS)
            view = self.read_view(number) or view
        return view

    def left_open(self, number, reason):
        self.failed = True
        self.say("#%d left open: %s" % (number, reason))

    def handle(self, number):
        view = self.read_view(number)
        if view is None:
            return self.left_open(number, "could not read the PR")
        view = self.settle_state(number, view)
        checks = self.read_checks(number)
        reasons = gate(view, checks, self.main_paths, self.prompts, self.model_id, self.tag)
        status = view.get("mergeStateStatus")
        if self.dry_run:
            return self.dry_report(number, view, reasons, status)
        if reasons:
            return self.left_open(number, "fails gate: " + "; ".join(reasons))
        if status == "BEHIND":
            updated = self.update_branch(number, view)
            if updated is None:
                return
            view = updated
            status = view.get("mergeStateStatus")
        self.merge(number, view, status)

    def dry_report(self, number, view, reasons, status):
        if reasons:
            self.failed = True
            return self.say("#%d fails gate: %s" % (number, "; ".join(reasons)))
        self.planned.append(number)
        self.planned_files.update(entry["path"] for entry in view["files"])
        if status == "BEHIND":
            self.say("#%d would update branch, then merge (mergeStateStatus=BEHIND)" % number)
        elif status == "BLOCKED":
            self.say("#%d would merge (mergeStateStatus=BLOCKED: merge would likely be "
                     "refused)" % number)
        else:
            self.say("#%d would merge (mergeStateStatus=%s)" % (number, status))

    def update_branch(self, number, view):
        """Merge main into the PR branch and return its re-gated view, or ``None``."""
        proc = self.run(("gh", "pr", "update-branch", str(number)))
        if proc.returncode:
            self.left_open(number, "update-branch failed: " + first_line(proc.stderr))
            return None
        old_oid = view["headRefOid"]
        for _ in range(POLL_LIMIT):
            self.sleep(POLL_SECONDS)
            fresh = self.read_view(number)
            if not fresh or fresh.get("headRefOid") == old_oid:
                continue
            checks = self.read_checks(number)
            if checks and not any(c["bucket"] == "pending" for c in checks):
                break
        else:
            self.left_open(number, "timed out waiting for update-branch to finish its checks")
            return None
        reasons = gate(fresh, checks, self.main_paths, self.prompts, self.model_id, self.tag)
        if reasons:
            self.left_open(number, "fails gate: " + "; ".join(reasons))
            return None
        return fresh

    def merge(self, number, view, status):
        prefix = parse_title(view["title"])[0]
        sha = view["headRefOid"]
        proc = self.run((
            "gh", "pr", "merge", str(number), "--squash", "--match-head-commit", sha,
            "--subject", "feat(results): add %s %s one-shot result (#%d)" % (
                prefix, self.model_id, number)))
        if proc.returncode:
            return self.left_open(number, "refused by GitHub: %s (mergeStateStatus=%s)" % (
                first_line(proc.stderr), status))
        self.merged.append(number)
        self.say("#%d merged (%s)" % (number, sha[:7]))

    # -- ledger --------------------------------------------------------------

    def ledger(self, open_prs, had_candidates):
        readme = self.run(("git", "show", "origin/main:README.md"))
        if readme.returncode:
            self.say("could not read README.md from origin/main: " + first_line(readme.stderr))
            return 1
        text = readme.stdout
        new_text, rows, skipped = rewrite_ledger(text, self.tag, self.by_id, self.main_paths)
        for message in skipped:
            self.say(message)
        if self.dry_run:
            self.say("ledger rows eligible now: " + describe_rows(rows))
            _, rows, _ = rewrite_ledger(
                text, self.tag, self.by_id, self.main_paths | self.planned_files)
            self.say("ledger rows eligible after planned merges: " + describe_rows(rows))
            new_text = None
        if not rows:
            self.say("ledger up to date" if had_candidates
                     else "nothing to merge; ledger up to date")
            return 1 if self.failed else 0
        prefix = "docs/ledger-%s-" % self.tag.replace("_", "-")
        for pr in open_prs:
            if pr.get("headRefName", "").startswith(prefix):
                self.say("ledger PR #%d already open; merge it, then re-run" % pr["number"])
                return 1 if self.failed else 0
        if self.dry_run:
            self.say("would open a docs PR marking %d row(s) generated" % len(rows))
            return 1 if self.failed else 0
        return 0 if self.docs_pr(prefix, new_text, rows) and not self.failed else 1

    def docs_pr(self, prefix, new_text, rows):
        """Open the ledger docs PR through the API; report the failing step."""
        steps = {}
        for key, argv in (("main sha", ("git", "rev-parse", "origin/main")),
                          ("README blob", ("git", "rev-parse", "origin/main:README.md"))):
            proc = self.run(argv)
            if proc.returncode or not proc.stdout.strip():
                return self.docs_failed(key, proc, None)
            steps[key] = proc.stdout.strip()
        branch = prefix + steps["main sha"][:7]
        proc = self.run(
            ("gh", "api", "--method", "POST", "repos/{owner}/{repo}/git/refs", "--input", "-"),
            input=json.dumps({"ref": "refs/heads/" + branch, "sha": steps["main sha"]}))
        if proc.returncode:
            return self.docs_failed("create branch", proc, None)
        title = "docs(readme): mark %d %s ledger rows generated" % (len(rows), self.model_id)
        proc = self.run(
            ("gh", "api", "--method", "PUT", "repos/{owner}/{repo}/contents/README.md",
             "--input", "-"),
            input=json.dumps({
                "message": title,
                "content": base64.b64encode(new_text.encode("utf-8")).decode("ascii"),
                "sha": steps["README blob"],
                "branch": branch,
            }))
        if proc.returncode:
            return self.docs_failed("update README", proc, branch)
        body = ["Marks the %s ledger rows generated now that their result PRs are merged."
                % self.model_id, "", "Rows:"]
        body += ["- `%s`: `%s`" % (row["pid"], row["path"]) for row in rows]
        if self.merged:
            body += ["", "Merged result PRs: " + ", ".join("#%d" % n for n in self.merged)]
        proc = self.run(("gh", "pr", "create", "--base", "main", "--head", branch,
                         "--title", title, "--body", "\n".join(body)))
        if proc.returncode:
            return self.docs_failed("open PR", proc, branch)
        self.say("docs PR opened: " + first_line(proc.stdout))
        return True

    def docs_failed(self, step, proc, leftover):
        self.failed = True
        self.say("docs PR step failed: %s: %s" % (step, first_line(proc.stderr)))
        if leftover:
            self.say("leftover branch: " + leftover)
        return False


def describe_rows(rows):
    return ", ".join("%s (%s)" % (row["pid"], row["path"]) for row in rows) or "none"


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="merge_results.py",
        description="Merge gated result PRs for one model, then update the README ledger.",
    )
    parser.add_argument("--model", required=True, metavar="ID",
                        help="session model id, e.g. claude-fable-5-2")
    parser.add_argument("--dry-run", action="store_true",
                        help="read-only: report what would be merged and updated")
    return parser.parse_args(argv)


def main(argv=None, run=None, sleep=None, prompts_dir=None, out=None):
    """CLI entry point; returns the process exit code."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    out = sys.stdout if out is None else out
    try:
        model_id = normalize_model_id(args.model)
        tag = model_tag(model_id)
    except ValueError as exc:
        print("bad model id: %s" % exc, file=out)
        return 2
    prompts = load_prompt_files(PROMPTS_DIR if prompts_dir is None else prompts_dir)
    merger = Merger(model_id, tag, prompts, run or default_run, sleep or time.sleep,
                    out, args.dry_run)
    return merger.execute()


if __name__ == "__main__":
    sys.exit(main())
