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
