#!/usr/bin/env python3
"""Gated merge of ``/bench-run`` result PRs, then a ledger update.

Usage::

    python3 harness/merge_results.py --model <model-id> [--post-statuses] [--dry-run]

Open PRs titled ``<prefix> (<model-id>, one-shot): result`` are checked
against a gate (right prompt, right folder, exactly the result files, only new
files, green checks). PRs that pass are squash-merged one at a time. GitHub
has the last word: if it refuses a merge, the PR stays open and the refusal is
reported. The command never uses ``--admin`` or ``--auto``.

Without ``--post-statuses`` it posts no commit status. ``main`` requires the
contexts ``orchestrai/test`` and ``orchestrai/review``, which one-shot result PRs
never receive, so with ``--post-statuses`` (owner-approved exception, #253) a PR
that passed the full gate gets both as ``success`` on its gated head commit,
each described as a one-shot result exception, and is then merged on that same
commit. Statuses go only on a commit that passed the gate: after a BEHIND update
the gate runs again and only the new head is vouched for, and a last read of the
PR must still show the gated head before anything is posted. A failed post
leaves the PR open; nothing is retried.

Afterwards the README ledger rows for the model whose files are on ``main``
are moved from ``not run`` to ``generated, review pending`` through a
docs PR, opened with the GitHub API so the working tree is untouched. Without
``--post-statuses`` that PR is never merged here. With it, the docs PR (the one
just opened, or exactly one left by an earlier run) is merged only after proof
that its diff is the rewrite this run computed: one commit on top of
``origin/main`` that changes only ``README.md`` to exactly the new text, whose
base text is main's README byte for byte (compared as git blob ids), with a
``docs/ledger-<tag>-<sha7>`` branch and green checks. It then gets the same two
statuses and a squash merge pinned to that commit. A docs PR is never brought up
to date, closed or deleted; one that fails the proof, or a second open docs PR,
stays open and is reported.

Exit codes: 0 all merged (or nothing to do); 1 a PR was left open or the docs
PR step failed (with ``--post-statuses`` a docs PR left open counts); 2 bad
model id or failed preflight.
"""

import argparse
import base64
import hashlib
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
        if entry.get("changeType") != "ADDED":
            reasons.append("not a new file (%s): %s" % (
                entry.get("changeType"), entry["path"]))
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
    # No result of this prompt on main yet: the folder is the file prefix,
    # the same fallback harness/bench_run.py uses.
    expected = on_main or {prefix}
    if expected != {family}:
        reasons.append("wrong folder: %s results live in %s, PR uses %s" % (
            prefix, sorted(expected), family))
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
GENERATED = "generated, review pending"


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


def git_blob_sha(data):
    """Return the git blob id of ``data`` (bytes), as ``git hash-object`` prints it."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def docs_gate(pr, commit, main_sha, main_blob, text, new_text, tag):
    """Return every reason the ledger docs PR may not be vouched for; empty means pass.

    ``pr`` is the ``gh pr view`` payload, ``commit`` the commits API payload of
    its head, ``main_sha`` and ``main_blob`` the ids of ``origin/main`` and of
    its ``README.md``, ``text`` the README the rewrite read and ``new_text`` its
    result. A head with the single parent ``main_sha`` that changes only
    ``README.md`` to exactly ``new_text``, where ``text`` is main's README byte
    for byte, has the diff ``text -> new_text`` and nothing else. No I/O here.
    """
    reasons = []
    if git_blob_sha(text.encode("utf-8")) != main_blob:
        reasons.append("base README is not the README on origin/main")
    parents = [p.get("sha") for p in commit.get("parents") or []]
    if parents != [main_sha]:
        reasons.append("commit parents %s are not exactly [origin/main %s]" % (
            [str(p)[:7] for p in parents], main_sha[:7]))
    files = commit.get("files") or []
    if len(files) != 1:
        reasons.append("commit must change exactly one file (README.md), found %d" % len(files))
    else:
        entry = files[0]
        if entry.get("filename") != "README.md":
            reasons.append("changed file is %r, not README.md" % entry.get("filename"))
        elif entry.get("status") != "modified":
            reasons.append("README.md status is %r, not modified" % entry.get("status"))
        if entry.get("sha") != git_blob_sha(new_text.encode("utf-8")):
            reasons.append("README.md blob is not this rewrite")
    branch_re = r"docs/ledger-%s-[0-9a-f]{7}" % re.escape(tag.replace("_", "-"))
    if not re.fullmatch(branch_re, pr.get("headRefName", "")):
        reasons.append("branch %r does not match docs/ledger-%s-<7 hex>" % (
            pr.get("headRefName"), tag.replace("_", "-")))
    if pr.get("isDraft"):
        reasons.append("PR is a draft")
    if pr.get("isCrossRepository"):
        reasons.append("PR comes from a fork")
    return reasons


# --- gh / git access --------------------------------------------------------

LIST_ARGV = ("gh", "pr", "list", "--state", "open", "--base", "main", "--limit", "200",
             "--json", "number,title,headRefName,isDraft,isCrossRepository")
VIEW_FIELDS = ("number,title,headRefName,headRefOid,isDraft,isCrossRepository,"
               "files,mergeStateStatus")
FETCH_ARGV = ("git", "fetch", "origin", "main")
LS_TREE_ARGV = ("git", "ls-tree", "-r", "--name-only", "origin/main", "--", "results")
STATUS_CONTEXTS = ("orchestrai/test", "orchestrai/review")
STATUS_MARKER = "one-shot result exception: "
RESULT_STATUS_DESC = STATUS_MARKER + "merge_results.py gate passed on this commit"
DOCS_STATUS_DESC = STATUS_MARKER + "merge_results.py ledger rewrite verified on this commit"
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

    def __init__(self, model_id, tag, prompts, run, sleep, out, dry_run,
                 post_statuses=False):
        self.model_id, self.tag = model_id, tag
        self.post_statuses = post_statuses
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
        if self.post_statuses:
            reason = self.vouch(number, view["headRefOid"], RESULT_STATUS_DESC)
            if reason:
                return self.left_open(number, reason)
        self.merge(number, view, status)

    def vouch(self, number, sha, desc):
        """Post both statuses on ``sha`` once it is confirmed; return a failure reason or ``None``.

        Opt-in only. ``gh pr checks`` names no commit, so a last read of the PR
        must still show ``sha`` as its head before anything is posted. Nothing is
        retried or undone: statuses cannot be deleted, and the merge that follows
        is pinned to ``sha``.
        """
        fresh = self.read_view(number)
        if fresh is None:
            return "could not read the PR to confirm its head; no status posted"
        if fresh.get("headRefOid") != sha:
            return "head moved after the gate read (%s -> %s); no status posted" % (
                sha[:7], str(fresh.get("headRefOid"))[:7])
        for done, context in enumerate(STATUS_CONTEXTS):
            proc = self.run((
                "gh", "api", "--method", "POST", "repos/{owner}/{repo}/statuses/" + sha,
                "-f", "state=success", "-f", "context=" + context,
                "-f", "description=" + desc))
            if proc.returncode:
                note = " (%s already posted)" % STATUS_CONTEXTS[0] if done else ""
                return "status post failed: %s on %s: %s%s" % (
                    context, sha[:7], first_line(proc.stderr), note)
        return None

    def dry_report(self, number, view, reasons, status):
        if reasons:
            self.failed = True
            return self.say("#%d fails gate: %s%s" % (
                number, "; ".join(reasons),
                "; no statuses would be posted" if self.post_statuses else ""))
        self.planned.append(number)
        self.planned_files.update(entry["path"] for entry in view["files"])
        if self.post_statuses:
            both = "post orchestrai/test and orchestrai/review"
            if status == "BEHIND":
                self.say("#%d would update branch, re-gate the new head, %s on it, then "
                         "merge (mergeStateStatus=BEHIND)" % (number, both))
            else:
                self.say("#%d would %s on %s, then merge (mergeStateStatus=%s)" % (
                    number, both, view["headRefOid"][:7], status))
        elif status == "BEHIND":
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
        open_docs = [pr for pr in open_prs if pr.get("headRefName", "").startswith(prefix)]
        if open_docs and not self.post_statuses:
            self.say("ledger PR #%d already open; merge it, then re-run" % open_docs[0]["number"])
            return 1 if self.failed else 0
        if len(open_docs) > 1:
            self.failed = True
            self.say("ledger PRs %s are open; no statuses %s; close all but one and re-run" % (
                ", ".join("#%d" % pr["number"] for pr in open_docs),
                "would be posted" if self.dry_run else "posted"))
            return 1
        if open_docs:
            return self.vouch_open_docs(open_docs[0]["number"], text, new_text, rows)
        if self.dry_run:
            self.say("would open a docs PR marking %d row(s) generated%s" % (
                len(rows), ", then post orchestrai/test and orchestrai/review on it and "
                "merge it once its diff is verified and its checks are green"
                if self.post_statuses else ""))
            return 1 if self.failed else 0
        return 0 if self.docs_pr(prefix, text, new_text, rows) and not self.failed else 1

    def vouch_open_docs(self, number, text, new_text, rows):
        """Opt-in: an earlier run's docs PR is merged only if it is exactly this rewrite."""
        if self.dry_run:
            self.say("ledger PR #%d already open; would post orchestrai/test and "
                     "orchestrai/review on it and merge it only if it is exactly this "
                     "rewrite on origin/main and its checks are green" % number)
            return 1 if self.failed else 0
        refs = self.main_refs()
        if refs is not None:
            self.docs_sequence(number, refs, text, new_text, rows)
        return 1 if self.failed else 0

    def main_refs(self):
        """Return ``{"main sha", "README blob"}`` of ``origin/main``, or ``None`` after a report."""
        refs = {}
        for key, argv in (("main sha", ("git", "rev-parse", "origin/main")),
                          ("README blob", ("git", "rev-parse", "origin/main:README.md"))):
            proc = self.run(argv)
            if proc.returncode or not proc.stdout.strip():
                self.docs_failed(key, proc, None)
                return None
            refs[key] = proc.stdout.strip()
        return refs

    def ledger_open(self, number, reason):
        self.failed = True
        self.say("ledger PR #%d left open: %s" % (number, reason))

    def wait_checks(self, number):
        """Poll until the PR's checks have finished; return the reasons they are not green."""
        for attempt in range(POLL_LIMIT):
            checks = self.read_checks(number)
            if checks and not any(c["bucket"] == "pending" for c in checks):
                return _checks_reasons(checks)
            if attempt < POLL_LIMIT - 1:
                self.sleep(POLL_SECONDS)
        return ["timed out waiting for checks"]

    def docs_sequence(self, number, refs, text, new_text, rows):
        """Opt-in: prove the docs PR is exactly the rewrite, wait for checks, vouch, merge.

        Never ``update-branch``: a merge commit would break the single-parent proof,
        so a docs PR that falls behind ``main`` stays open (``strict`` refuses it).
        """
        view = self.read_view(number)
        if view is None:
            return self.ledger_open(number, "could not read the PR")
        sha = view["headRefOid"]
        commit = self.json_call(("gh", "api", "repos/{owner}/{repo}/commits/" + sha), dict)
        if commit is None:
            return self.ledger_open(number, "could not read its head commit")
        reasons = docs_gate(view, commit, refs["main sha"], refs["README blob"], text,
                            new_text, self.tag)
        if reasons:
            return self.ledger_open(
                number, "fails docs gate: %s; close it and re-run" % "; ".join(reasons))
        reasons = self.wait_checks(number)
        if reasons:
            return self.ledger_open(number, "; ".join(reasons))
        reason = self.vouch(number, sha, DOCS_STATUS_DESC)
        if reason:
            return self.ledger_open(number, reason)
        proc = self.run((
            "gh", "pr", "merge", str(number), "--squash", "--match-head-commit", sha,
            "--subject", "docs(readme): mark %d %s ledger rows generated (#%d)" % (
                len(rows), self.model_id, number)))
        if proc.returncode:
            return self.ledger_open(number, "refused by GitHub: " + first_line(proc.stderr))
        self.say("docs PR #%d merged (%s)" % (number, sha[:7]))

    def docs_pr(self, prefix, text, new_text, rows):
        """Open the ledger docs PR through the API; report the failing step."""
        steps = self.main_refs()
        if steps is None:
            return False
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
        url = first_line(proc.stdout)
        self.say("docs PR opened: " + url)
        if self.post_statuses:
            match = re.search(r"/pull/(\d+)$", url)
            if match is None:
                self.failed = True
                self.say("ledger PR left open: could not read its number from: " + url)
            else:
                self.docs_sequence(int(match.group(1)), steps, text, new_text, rows)
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
    parser.add_argument("--post-statuses", action="store_true",
                        help="one-shot result exception: post orchestrai/test and "
                             "orchestrai/review on a PR that passed the gate, then merge it")
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
                    out, args.dry_run, args.post_statuses)
    return merger.execute()


if __name__ == "__main__":
    sys.exit(main())
