#!/usr/bin/env python3
"""Write ``dashboard.html``: a local, self-contained page listing every result.

``dashboard.py`` walks ``results/`` and writes ``<repo root>/dashboard.html``
with one row per result (a deliverable with a paired ``.meta.json``): prompt,
model, effort, generation date, and the duration, output tokens and cost from
the result's ``<deliverable stem>.run.json`` where it has one. The file is
git-ignored; run the command again after pulling new results.

Usage::

    python3 harness/dashboard.py

Deliverables under ``results/`` are untrusted model output. They are never
opened, embedded or executed here: the page only links to them, by a relative
``results/...`` path. Every value that comes from a sidecar, a run file or a
file name is HTML-escaped; the page's script and style are fixed text.
"""

import argparse
import datetime
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Running this file directly (`python harness/dashboard.py`) puts `harness/` on
# sys.path, so make the repo root importable for the `harness` package.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.grade import iter_results, read_meta  # noqa: E402
from harness.modes._common import EFFORT_LEVELS, derive_model, pair_meta  # noqa: E402

RUN_SUFFIX = ".run.json"
GENERATED_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DASH = "—"


@dataclass(frozen=True)
class Row:
    """One result. ``None`` means the value is missing (shown as a dash)."""

    index: int
    relpath: str
    file: str
    prompt: str
    title: str | None
    model: str | None
    effort: str | None
    generated: str | None
    duration: float | None
    output_tokens: float | None
    cost: float | None


def _text(value):
    """Return ``value`` when it is a non-empty string, else ``None``."""
    return value if isinstance(value, str) and value else None


def _is_number(value):
    """True for a finite, non-negative int or float (not a bool)."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


def _effort_rank(effort):
    """Index of ``effort`` in ``EFFORT_LEVELS``; unknown or missing sorts last."""
    return EFFORT_LEVELS.index(effort) if effort in EFFORT_LEVELS else len(EFFORT_LEVELS)


def _split_tag(tag):
    """Split a run tag into ``(model, effort)``; either may be ``None``."""
    head, _, last = tag.rpartition("_")
    if head and last in EFFORT_LEVELS:
        return head, last
    return (tag or None), None


def _parse_generated(value):
    """Return ``value`` when it is a ``generated_utc`` timestamp, else ``None``."""
    if not isinstance(value, str):
        return None
    try:
        datetime.datetime.strptime(value, GENERATED_FORMAT)
    except ValueError:
        return None
    return value


def _read_run_file(run_path, relpath, warnings):
    """Return ``(duration, output_tokens, cost)`` from a run file; missing is ``None``."""
    if not run_path.is_file():
        return None, None, None
    try:
        data = json.loads(run_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        warnings.append("%s: cannot read run file (%s)" % (relpath, exc))
        return None, None, None
    if not isinstance(data, dict):
        warnings.append("%s: run file is not a JSON object" % relpath)
        return None, None, None
    values = []
    for key in ("duration_seconds", "output_tokens", "cost_usd"):
        value = data.get(key)
        if key in data and not _is_number(value):
            warnings.append("%s: %s is not a non-negative number" % (relpath, key))
            value = None
        values.append(value)
    return tuple(values)


def collect_rows(repo_root):
    """Return ``(rows, warnings)`` for every result under ``repo_root/results``.

    A file is a row exactly when it has a paired ``.meta.json``. Warnings are
    ``"<path relative to the repo>: <reason>"`` strings for unreadable
    sidecars and run files; those results still appear.
    """
    repo_root = Path(repo_root)
    results_dir = repo_root / "results"
    warnings = []
    pending = []
    if not results_dir.is_dir():
        return [], warnings
    for path in iter_results(results_dir):
        if path.name.endswith(RUN_SUFFIX):
            continue
        meta_path = pair_meta(path)
        if meta_path is None:
            continue
        relpath = path.relative_to(repo_root).as_posix()
        meta = read_meta(path)
        if meta is None:
            warnings.append("%s: cannot read meta file" % meta_path.relative_to(repo_root).as_posix())
            meta = {}
        params = meta.get("params")
        meta_effort = _text(params.get("reasoning_effort")) if isinstance(params, dict) else None
        tag_model, tag_effort = _split_tag(derive_model(path, {"file_prefix": path.parent.name}))
        run_path = path.with_name(path.stem + RUN_SUFFIX)
        duration, output_tokens, cost = _read_run_file(
            run_path, run_path.relative_to(repo_root).as_posix(), warnings)
        pending.append(dict(
            relpath=relpath,
            file=path.name,
            prompt=_text(meta.get("prompt_id")) or path.parent.name,
            title=_text(meta.get("title")),
            model=_text(meta.get("model")) or tag_model,
            effort=meta_effort or tag_effort,
            generated=_parse_generated(meta.get("generated_utc")),
            duration=duration,
            output_tokens=output_tokens,
            cost=cost,
        ))
    pending.sort(key=lambda r: (
        r["prompt"].casefold(),
        r["model"] is None, (r["model"] or "").casefold(),
        _effort_rank(r["effort"]),
        r["file"],
    ))
    rows = [Row(index=i, **fields) for i, fields in enumerate(pending)]
    return rows, warnings


def format_duration(seconds):
    """``45s``, ``12m 34s`` or ``1h 02m 03s``, rounded to whole seconds."""
    total = int(round(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "%dh %02dm %02ds" % (hours, minutes, secs)
    if minutes:
        return "%dm %02ds" % (minutes, secs)
    return "%ds" % secs


def format_tokens(count):
    """``12,345``."""
    return "{:,}".format(int(round(count)))


def format_cost(usd):
    """``$1.23``, or ``<$0.01`` for a positive amount below one cent."""
    if 0 < usd < 0.01:
        return "<$0.01"
    return "${:,.2f}".format(usd)


def format_generated(value):
    """``2026-11-14T18:00:00Z`` -> ``2026-11-14 18:00``."""
    return datetime.datetime.strptime(value, GENERATED_FORMAT).strftime("%Y-%m-%d %H:%M")
