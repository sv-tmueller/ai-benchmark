#!/usr/bin/env python3
"""Write ``dashboard.html``: a self-contained page listing every result.

``dashboard.py`` walks ``results/`` and writes ``<repo root>/dashboard.html``
with one row per result (a deliverable with a paired ``.meta.json``): prompt,
model, effort, generation date, and the duration, output tokens and cost from
the result's ``<deliverable stem>.run.json`` where it has one. The file is
committed: ``harness/merge_results.py`` regenerates it from the results on
``origin/main`` and carries it in its docs PR. Running the command by hand on
a checkout whose dashboard is current writes the same bytes and leaves
``git status`` clean.

Usage::

    python3 harness/dashboard.py

The rows come from one pure core, :func:`collect_rows_from`, fed by one of two
readers: :func:`collect_rows` walks the working tree, :func:`collect_rows_at`
reads a git tree (``git ls-tree`` plus one ``git cat-file --batch`` for the
sidecars and run files only), so a page built from ``origin/main`` is byte for
byte what a hand run on a clean checkout of it writes. Symlinks under
``results/`` are not results in either reader.

Deliverables under ``results/`` are untrusted model output. They are never
opened, embedded or executed here, and the git reader never even requests
their blobs: the page only links to them, by a relative ``results/...`` path.
Every value that comes from a sidecar, a run file or a file name is
HTML-escaped; the page's script and style are fixed text.
"""

import argparse
import base64
import datetime
import hashlib
import html
import json
import math
import re
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parent.parent

# Running this file directly (`python harness/dashboard.py`) puts `harness/` on
# sys.path, so make the repo root importable for the `harness` package.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.grade import META_SUFFIX, is_result_file  # noqa: E402
from harness.modes._common import EFFORT_LEVELS, derive_model  # noqa: E402

RUN_SUFFIX = ".run.json"
REGULAR_FILE_MODES = (b"100644", b"100755")
_OID = re.compile(rb"[0-9a-f]{40}|[0-9a-f]{64}")
GENERATED_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
GENERATED_SHAPE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
SURROGATES = re.compile("[\ud800-\udfff]")
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


def _clean(value):
    """Replace lone surrogates with U+FFFD so ``value`` encodes as UTF-8.

    A file name that is not valid UTF-8 reaches Python with its bad bytes as
    surrogates, and a JSON ``\\udcff`` escape produces one too; neither can be
    written to the page or printed.
    """
    return SURROGATES.sub("�", value)


def _text(value):
    """Return ``value`` (cleaned) when it is a non-empty string, else ``None``."""
    return _clean(value) if isinstance(value, str) and value else None


def _is_number(value):
    """True for a finite, non-negative int or float (not a bool).

    An int too large for a float is not a valid value either.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value) and value >= 0
    except OverflowError:
        return False


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
    if not isinstance(value, str) or not GENERATED_SHAPE.fullmatch(value):
        return None
    try:
        datetime.datetime.strptime(value, GENERATED_FORMAT)
    except ValueError:
        return None
    return value


class GitReadError(Exception):
    """A git read failed, or git answered in a shape this reader does not know."""


def _load_json(data):
    """Parse ``data`` (bytes) as UTF-8 JSON.

    Decoded explicitly: ``json.loads`` on bytes would detect UTF-16/32 and
    accept files that the text-mode read of the old working-tree path rejects.
    """
    return json.loads(data.decode("utf-8"))


def _read_run_file(run_rel, files, read, warnings):
    """Return ``(duration, output_tokens, cost)`` from a run file; missing is ``None``."""
    if run_rel not in files:
        return None, None, None
    try:
        data = _load_json(read(run_rel))
    except (OSError, ValueError, RecursionError) as exc:
        warnings.append("%s: cannot read run file (%s)" % (run_rel, exc))
        return None, None, None
    if not isinstance(data, dict):
        warnings.append("%s: run file is not a JSON object" % run_rel)
        return None, None, None
    values = []
    for key in ("duration_seconds", "output_tokens", "cost_usd"):
        value = data.get(key)
        if key in data and not _is_number(value):
            warnings.append("%s: %s is not a non-negative number" % (run_rel, key))
            value = None
        elif value is not None:
            value = abs(value)  # -0.0 is zero
        values.append(value)
    return tuple(values)


def _read_meta_file(meta_rel, read):
    """Return the parsed sidecar, or ``None`` when it is unreadable or not an object."""
    try:
        meta = _load_json(read(meta_rel))
    except (OSError, ValueError, RecursionError):  # RecursionError: a deeply nested sidecar
        return None
    return meta if isinstance(meta, dict) else None


def collect_rows(repo_root):
    """Return ``(rows, warnings)`` for every result under ``repo_root/results``.

    Reads the working tree. A symlink (folder, deliverable, sidecar or run
    file) is not listed, so it is never a result and never read.
    """
    repo_root = Path(repo_root)
    results_dir = repo_root / "results"
    if not results_dir.is_dir():
        return [], []
    files = set()
    for directory in results_dir.iterdir():
        if not directory.is_dir() or directory.is_symlink():
            continue
        for path in directory.iterdir():
            if path.is_file() and not path.is_symlink():
                files.add(path.relative_to(repo_root).as_posix())
    return collect_rows_from(files, lambda rel: (repo_root / rel).read_bytes())


def _list_regular_files(listing):
    """Return ``{path: oid}`` for the ``results/<folder>/<name>`` files in ``ls-tree -r -z`` output.

    Only modes 100644 and 100755 count; a symlink (120000) or a gitlink
    (160000) is not a file, matching the working-tree reader. Paths are
    decoded as ``os.listdir`` would give them (UTF-8, bad bytes as surrogates).
    """
    found = {}
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        head, tab, raw_path = entry.partition(b"\t")
        fields = head.split(b" ")
        if not tab or len(fields) != 3 or not _OID.fullmatch(fields[2]):
            raise GitReadError("unexpected git ls-tree output")
        if fields[0] not in REGULAR_FILE_MODES:
            continue
        relpath = raw_path.decode("utf-8", "surrogateescape")
        parts = relpath.split("/")
        if len(parts) == 3 and parts[0] == "results":
            found[relpath] = fields[2].decode("ascii")
    return found


def _read_blobs(git, oids):
    """Return ``{oid: bytes}`` from one ``git cat-file --batch``; a missing blob is absent."""
    if not oids:
        return {}
    request = "".join(oid + "\n" for oid in oids).encode("ascii")
    out = git(["cat-file", "--batch"], input=request)
    blobs = {}
    pos = 0
    for oid in oids:
        end = out.find(b"\n", pos)
        if end < 0:
            raise GitReadError("git cat-file ended early")
        header = out[pos:end].split(b" ")
        pos = end + 1
        want = oid.encode("ascii")
        if header == [want, b"missing"]:
            continue
        if len(header) != 3 or header[0] != want or header[1] != b"blob" or not header[2].isdigit():
            raise GitReadError("unexpected git cat-file output")
        size = int(header[2])  # a count of bytes, not characters
        if out[pos + size:pos + size + 1] != b"\n":
            raise GitReadError("git cat-file output is truncated")
        blobs[oid] = out[pos:pos + size]
        pos += size + 1
    if pos != len(out):
        raise GitReadError("git cat-file printed more than was asked for")
    return blobs


def collect_rows_at(rev, git):
    """Return ``(rows, warnings)`` for the results in the git tree of ``rev``.

    ``git(args, input=None)`` runs ``git <args>`` and returns its stdout as
    bytes; it raises :class:`GitReadError` on a non-zero exit. Nothing is
    written to disk. Only the ``.meta.json`` and ``.run.json`` blobs are
    requested, in one call; a deliverable's blob never is. The same files give
    the same rows and warnings as :func:`collect_rows`.
    """
    oids = _list_regular_files(git(["ls-tree", "-r", "-z", rev, "--", "results"]))
    wanted = {rel for rel in oids if rel.endswith((META_SUFFIX, RUN_SUFFIX))}
    blobs = _read_blobs(git, list(dict.fromkeys(oids[rel] for rel in sorted(wanted))))

    def read(relpath):
        if relpath not in wanted or oids[relpath] not in blobs:
            raise OSError("blob of %s is not available" % relpath)
        return blobs[oids[relpath]]

    return collect_rows_from(set(oids), read)


def collect_rows_from(files, read):
    """Return ``(rows, warnings)`` for the result files in ``files``. No I/O of its own.

    ``files`` is the set of ``results/<folder>/<name>`` paths (POSIX, exactly
    two levels down) of the regular files that exist; ``read(path)`` returns a
    file's bytes or raises ``OSError``. It is only ever called for a result's
    ``.meta.json`` and ``.run.json``, never for a deliverable.

    A file is a row exactly when it passes ``is_result_file`` and has a
    paired ``.meta.json`` in ``files``. Warnings are
    ``"<path relative to the repo>: <reason>"`` strings for unreadable
    sidecars and run files, and for names that are not valid UTF-8; those
    results still appear. ``Row.relpath`` keeps the name's raw (surrogate)
    characters so the link can reproduce its bytes; every text meant for
    display or printing is cleaned.

    The files are visited in ``(folder, name)`` order, as a directory walk
    gives them, so rows that tie on every sort key keep that order whichever
    reader built ``files``: git's own tree order differs (folder ``a.b``
    sorts before ``a``).
    """
    files = set(files)
    warnings = []
    pending = []
    for relpath in sorted(files, key=lambda rel: tuple(rel.split("/"))):
        path = PurePosixPath(relpath)
        if not is_result_file(path):
            continue
        meta_rel = path.with_name(path.stem + META_SUFFIX).as_posix()
        if meta_rel not in files:
            continue
        if SURROGATES.search(relpath):
            warnings.append("%s: name is not valid UTF-8" % relpath)
        meta = _read_meta_file(meta_rel, read)
        if meta is None:
            warnings.append("%s: cannot read meta file" % meta_rel)
            meta = {}
        params = meta.get("params")
        meta_effort = _text(params.get("reasoning_effort")) if isinstance(params, dict) else None
        tag_model, tag_effort = _split_tag(
            _clean(derive_model(path, {"file_prefix": path.parent.name})))
        run_rel = path.with_name(path.stem + RUN_SUFFIX).as_posix()
        duration, output_tokens, cost = _read_run_file(run_rel, files, read, warnings)
        pending.append(dict(
            relpath=relpath,
            file=_clean(path.name),
            prompt=_text(meta.get("prompt_id")) or _clean(path.parent.name),
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
    return rows, [_clean(warning) for warning in warnings]


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


# --- the page ---------------------------------------------------------------
#
# STYLE and SCRIPT are fixed text. Nothing read from disk is ever inserted into
# them, so no sidecar value can break out of the <script> or <style> element,
# and the Content-Security-Policy below pins the page to exactly these two
# blocks (by sha256), which also blocks any network access.

STYLE = r"""
:root{color-scheme:light dark}
body{font-family:system-ui,sans-serif;margin:1.5rem}
table{border-collapse:collapse;width:100%}
th,td{padding:.35rem .6rem;text-align:left;border-bottom:1px solid #8884}
thead th{position:sticky;top:0;background:Canvas}
th button{font:inherit;font-weight:600;background:none;border:0;padding:0;color:inherit;cursor:pointer}
th[aria-sort=ascending] button::after{content:" \25B2"}
th[aria-sort=descending] button::after{content:" \25BC"}
th.num,td.num{text-align:right;font-variant-numeric:tabular-nums}
tbody tr:nth-child(even){background:#f3f3f3}
tr.group-heading th{background:#dde3ee;padding-top:.6rem}
@media (prefers-color-scheme: dark){
tbody tr:nth-child(even){background:#1f1f1f}
tr.group-heading th{background:#2b3345}
}
"""

SCRIPT = r"""
"use strict";
var MISSING_LABEL = "—";

function isMissing(value) {
  return value === null || value === undefined;
}

// Ascending comparison of two data-sort values; a missing value sorts last.
function compareValues(a, b, type) {
  var aMissing = isMissing(a);
  var bMissing = isMissing(b);
  if (aMissing || bMissing) {
    return aMissing === bMissing ? 0 : (aMissing ? 1 : -1);
  }
  if (type === "num") {
    return parseFloat(a) - parseFloat(b);
  }
  return a.localeCompare(b, "en", {numeric: true});
}

// items: [{index, values: {key: string|null}, texts: {key: string}}].
// Returns {items, groups: [{label, count}]}; items are ordered so each group's
// members are contiguous. Missing values stay last in both sort directions.
function orderRows(items, sortKey, sortDir, groupKey, types) {
  var direction = sortDir === "desc" ? -1 : 1;
  function byRow(x, y) {
    if (sortKey) {
      var a = x.values[sortKey];
      var b = y.values[sortKey];
      var c = compareValues(a, b, types[sortKey]);
      if (c !== 0) {
        return isMissing(a) || isMissing(b) ? c : c * direction;
      }
    }
    return x.index - y.index;
  }
  if (!groupKey) {
    return {items: items.slice().sort(byRow), groups: []};
  }
  var buckets = new Map();
  items.forEach(function (item) {
    var value = item.values[groupKey];
    var key = isMissing(value) ? null : value;
    if (!buckets.has(key)) {
      buckets.set(key, []);
    }
    buckets.get(key).push(item);
  });
  var keys = Array.from(buckets.keys()).sort(function (a, b) {
    return compareValues(a, b, types[groupKey]);
  });
  var ordered = [];
  var groups = [];
  keys.forEach(function (key) {
    var members = buckets.get(key).sort(byRow);
    ordered = ordered.concat(members);
    groups.push({
      label: key === null ? MISSING_LABEL : members[0].texts[groupKey],
      count: members.length
    });
  });
  return {items: ordered, groups: groups};
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", function () {
    var table = document.getElementById("results");
    var select = document.getElementById("group-by");
    if (!table || !select) {
      return;
    }
    var body = table.tBodies[0];
    var headers = Array.from(table.tHead.rows[0].cells);
    var types = {};
    headers.forEach(function (th) {
      types[th.dataset.key] = th.dataset.type;
    });
    var items = Array.from(body.rows).map(function (row) {
      var values = {};
      var texts = {};
      headers.forEach(function (th, i) {
        var cell = row.cells[i];
        values[th.dataset.key] = cell.dataset.sort === undefined ? null : cell.dataset.sort;
        texts[th.dataset.key] = cell.textContent;
      });
      return {index: Number(row.dataset.index), row: row, values: values, texts: texts};
    });
    var sortKey = null;
    var sortDir = "asc";

    function render() {
      var result = orderRows(items, sortKey, sortDir, select.value, types);
      while (body.firstChild) {
        body.removeChild(body.firstChild);
      }
      var position = 0;
      var groups = result.groups.length ? result.groups : [null];
      groups.forEach(function (group) {
        var count = group ? group.count : result.items.length;
        if (group) {
          var tr = document.createElement("tr");
          tr.className = "group-heading";
          var th = document.createElement("th");
          th.colSpan = headers.length;
          th.scope = "colgroup";
          th.textContent = group.label + " (" + group.count + ")";
          tr.appendChild(th);
          body.appendChild(tr);
        }
        for (var i = 0; i < count; i++) {
          body.appendChild(result.items[position].row);
          position += 1;
        }
      });
      headers.forEach(function (th) {
        if (th.dataset.key === sortKey) {
          th.setAttribute("aria-sort", sortDir === "asc" ? "ascending" : "descending");
        } else {
          th.removeAttribute("aria-sort");
        }
      });
    }

    headers.forEach(function (th) {
      th.querySelector("button").addEventListener("click", function () {
        if (sortKey === th.dataset.key) {
          sortDir = sortDir === "asc" ? "desc" : "asc";
        } else {
          sortKey = th.dataset.key;
          sortDir = "asc";
        }
        render();
      });
    });
    select.addEventListener("change", render);
  });
}
"""

# (data-key, header text, data-type); the page and its script both rely on
# this order.
COLUMNS = (
    ("prompt", "Prompt", "text"),
    ("model", "Model", "text"),
    ("effort", "Effort", "num"),
    ("generated", "Generated (UTC)", "text"),
    ("duration", "Duration", "num"),
    ("output_tokens", "Output tokens", "num"),
    ("cost", "Cost (USD)", "num"),
    ("file", "Result", "text"),
)
GROUP_OPTIONS = (("", "none"), ("prompt", "prompt"), ("model", "model"), ("effort", "effort"))


def _esc(value):
    """Escape a value for HTML text or a double-quoted attribute."""
    return html.escape(str(value), quote=True)


def _number(value):
    """Render a checked, finite, non-negative number for ``data-sort``."""
    return repr(value)


def _td(shown, sort=None, numeric=False, title=None, markup=False):
    """One table cell. ``shown`` is escaped unless ``markup`` (already safe HTML)."""
    attrs = ""
    if numeric:
        attrs += ' class="num"'
    if sort is not None:
        attrs += ' data-sort="%s"' % _esc(sort)
    if title is not None:
        attrs += ' title="%s"' % _esc(title)
    return "<td%s>%s</td>" % (attrs, shown if markup else _esc(shown))


def _text_cell(value, title=None):
    if value is None:
        return _td(DASH)
    return _td(value, sort=value, title=title)


def _number_cell(value, formatter):
    if value is None:
        return _td(DASH, numeric=True)
    return _td(formatter(value), sort=_number(value), numeric=True)


def _row_html(row):
    effort = row.effort
    effort_sort = str(EFFORT_LEVELS.index(effort)) if effort in EFFORT_LEVELS else None
    href = urllib.parse.quote(row.relpath, safe="/", errors="surrogateescape")
    link = ('<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>'
            % (_esc(href), _esc(row.file)))
    cells = [
        _text_cell(row.prompt, title=row.title),
        _text_cell(row.model),
        _td(effort if effort is not None else DASH, sort=effort_sort, numeric=True),
        _td(DASH) if row.generated is None
        else _td(format_generated(row.generated), sort=row.generated),
        _number_cell(row.duration, format_duration),
        _number_cell(row.output_tokens, format_tokens),
        _number_cell(row.cost, format_cost),
        _td(link, sort=row.file, markup=True),
    ]
    return '<tr data-index="%d">%s</tr>' % (row.index, "".join(cells))


def _sha256(text):
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return "'sha256-%s'" % base64.b64encode(digest).decode("ascii")


def render(rows):
    """Return the whole page for ``rows`` (as from :func:`collect_rows`)."""
    if rows:
        csp = "default-src 'none'; script-src %s; style-src %s" % (_sha256(SCRIPT), _sha256(STYLE))
    else:
        csp = "default-src 'none'; style-src %s" % _sha256(STYLE)
    head = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta http-equiv="Content-Security-Policy" content="%s">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Benchmark results</title>\n<style>%s</style>\n</head>\n<body>\n"
        "<h1>Benchmark results</h1>\n" % (csp, STYLE)
    )
    if not rows:
        return head + (
            '<p class="empty">No results found under results/ in this checkout.</p>\n'
            "</body>\n</html>\n"
        )
    count = len(rows)
    intro = (
        "<p>%d %s from results/ in this checkout. Duration, output tokens and cost come "
        "from each result's .run.json; %s means not recorded.</p>\n"
        % (count, "result" if count == 1 else "results", DASH)
    )
    options = "".join('<option value="%s">%s</option>' % (_esc(v), _esc(label))
                      for v, label in GROUP_OPTIONS)
    control = ('<p><label for="group-by">Group by</label> '
               '<select id="group-by" autocomplete="off">%s</select></p>\n' % options)
    header = "".join(
        '<th scope="col" data-key="%s" data-type="%s"%s><button type="button">%s</button></th>'
        % (key, kind, ' class="num"' if kind == "num" else "", _esc(label))
        for key, label, kind in COLUMNS
    )
    body = "\n".join(_row_html(row) for row in rows)
    return head + intro + control + (
        '<table id="results">\n<thead><tr>%s</tr></thead>\n<tbody>\n%s\n</tbody>\n</table>\n'
        "<script>%s</script>\n</body>\n</html>\n" % (header, body, SCRIPT)
    )


# --- command line -----------------------------------------------------------

def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Write dashboard.html at the repo root: one row per result under "
                    "results/, sortable and groupable, for opening straight from the "
                    "checkout. The file is committed and kept current by the merge "
                    "step; run this to regenerate it by hand."
    )
    return parser.parse_args(argv)


def main(argv=None, repo_root=REPO_ROOT, out=None, err=None):
    """CLI entry point; returns the process exit code.

    0 when the file is written (also with no results or with warnings), 1 when
    writing fails; argparse exits 2 on a usage error.
    """
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    parse_args(sys.argv[1:] if argv is None else argv)

    target = Path(repo_root).absolute() / "dashboard.html"
    try:
        rows, warnings = collect_rows(repo_root)
        for warning in warnings:
            print("warning: %s" % warning, file=err)
        target.write_text(render(rows), encoding="utf-8", newline="\n")
    except OSError as exc:
        print("error: %s" % _clean(str(exc)), file=err)
        return 1
    print(_clean(str(target)), file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
