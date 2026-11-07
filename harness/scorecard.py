#!/usr/bin/env python3
"""Aggregate committed verdict sidecars into a per-model × per-category matrix.

``scorecard.py`` walks ``results/`` and reads the evidence ``grade.py``
already produced: every ``<result>_grading.json`` verdict sidecar plus the
legacy ``grading`` field of ``<result>.meta.json``. It emits

- ``results/scorecard.json`` — machine-readable counts, and
- ``results/scorecard.md`` — the rendered matrix, in the style of
  ``results/frontier_summary.md``.

The matrix is honest by construction: a model appears as a row only when it
has at least one verdict, a cell is ``null``/``—`` (never ``0``) when a model
has no graded verdict in a category, and prompts the harness cannot grade are
listed explicitly instead of being counted as failures. There is deliberately
no single composite index number.

Grading is retroactive — this script never generates model output. Where both
a verdict sidecar and a legacy ``.meta.json`` grading field exist for the same
result, the sidecar wins; the row key is the winning source's ``model`` string
verbatim. Prompt association and categories go through ``prompt_id`` and the
prompt TOML ``category``, never through directory or filename prefixes.

Usage::

    python harness/scorecard.py
    python harness/scorecard.py --results-dir results --prompts-dir prompts \
        --out-json results/scorecard.json --out-md results/scorecard.md
"""

import argparse
import json
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS_DIR = REPO_ROOT / "results"
DEFAULT_PROMPTS_DIR = REPO_ROOT / "prompts"
DEFAULT_OUT_JSON = DEFAULT_RESULTS_DIR / "scorecard.json"
DEFAULT_OUT_MD = DEFAULT_RESULTS_DIR / "scorecard.md"

META_SUFFIX = ".meta.json"
SIDECAR_SUFFIX = "_grading.json"
FIXTURES_SUFFIX = ".fixtures.toml"
EMPTY_CELL = "—"
SIDECAR_SOURCE = "sidecar"
LEGACY_SOURCE = "legacy-meta"


def load_prompts(prompts_dir):
    """Return ``{prompt_id: parsed TOML}`` for every non-fixture prompt file."""
    prompts = {}
    for path in sorted(Path(prompts_dir).glob("*.toml")):
        if path.name.endswith(FIXTURES_SUFFIX):
            continue
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            continue
        prompt_id = data.get("id")
        if prompt_id:
            prompts[prompt_id] = data
    return prompts


def _read_json(path):
    """Return the parsed JSON object at ``path``, or ``None`` when unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _as_vendor_key(value):
    """Return ``value`` when it is a non-empty string id, else ``None``.

    ``prompt_id``/``model`` are used as dict keys and sorted downstream, so a
    list or dict would abort the whole run with ``TypeError: unhashable type``
    and mixed key types would break the sort. Anything that is not a string
    means the verdict is malformed — skip it, never crash.
    """
    return value if isinstance(value, str) and value else None


def _as_bool(value):
    """Return ``value`` only when it is a genuine ``bool``, else ``None``.

    Coercing with ``bool()`` would silently turn ``"false"`` into a PASS and
    ``None``/``[]`` into a recorded failure. A wrong-typed verdict is rejected
    outright, so a bad sidecar can neither fabricate a pass nor mask a fail.
    """
    return value if isinstance(value, bool) else None


def _has_playability(meta):
    """True when ``meta`` carries a playability verdict/label (gradable)."""
    verification = meta.get("playability_verification")
    if isinstance(verification, dict) and verification.get("playability_verdict"):
        return True
    playability = meta.get("playability")
    return bool(isinstance(playability, dict) and playability.get("label"))


def _iter_result_dirs(results_dir):
    """Yield the ``results/<family>/`` directories, mirroring ``grade.py``."""
    root = Path(results_dir)
    if not root.is_dir():
        return
    for directory in sorted(root.iterdir()):
        if directory.is_dir():
            yield directory


def collect_verdicts(results_dir):
    """Return per-result verdicts plus the set of playability-gradable prompts.

    Each verdict dict carries ``prompt_id``, ``model`` (verbatim), ``pass`` and
    ``source``. Results are keyed by ``(family, stem)`` so that a verdict
    sidecar overrides that stem's legacy ``.meta.json`` grading field instead of
    double-counting one result.
    """
    verdicts = {}
    playability_prompts = set()

    # Pass 1: verdict sidecars (the authoritative evidence).
    for directory in _iter_result_dirs(results_dir):
        for path in sorted(directory.iterdir()):
            if not path.is_file() or not path.name.endswith(SIDECAR_SUFFIX):
                continue
            stem = path.name[: -len(SIDECAR_SUFFIX)]
            data = _read_json(path)
            if data is None:
                continue
            prompt_id = _as_vendor_key(data.get("prompt_id"))
            model = _as_vendor_key(data.get("model"))
            passed = _as_bool(data.get("pass"))
            if not prompt_id or not model or passed is None:
                continue
            verdicts[(directory.name, stem)] = {
                "prompt_id": prompt_id,
                "model": model,
                "pass": passed,
                "source": SIDECAR_SOURCE,
            }

    # Pass 2: legacy meta grading fields — only where no sidecar won.
    for directory in _iter_result_dirs(results_dir):
        for path in sorted(directory.iterdir()):
            if not path.is_file() or not path.name.endswith(META_SUFFIX):
                continue
            stem = path.name[: -len(META_SUFFIX)]
            data = _read_json(path)
            if data is None:
                continue
            meta_prompt_id = _as_vendor_key(data.get("prompt_id"))
            if _has_playability(data) and meta_prompt_id:
                playability_prompts.add(meta_prompt_id)
            key = (directory.name, stem)
            if key in verdicts:
                continue  # a sidecar already owns this result
            grading = data.get("grading")
            if not isinstance(grading, dict) or "pass" not in grading:
                continue  # "grading": null is *no verdict*, never a failure
            passed = _as_bool(grading.get("pass"))
            if passed is None:
                continue  # non-bool pass is malformed, not a coerced verdict
            model = _as_vendor_key(data.get("model"))
            if not meta_prompt_id or not model:
                continue
            verdicts[key] = {
                "prompt_id": meta_prompt_id,
                "model": model,
                "pass": passed,
                "source": LEGACY_SOURCE,
            }

    return verdicts, playability_prompts


def gradable_prompts(prompts, playability_prompts):
    """Return the prompt ids the harness can grade, per ``grade.py``'s rule.

    A prompt is gradable when its TOML carries a ``[grading]`` block with a
    ``mode``, or when its result metas carry playability fields. Prompt ids are
    compared verbatim; anything else is ungraded and never counted as a fail.
    """
    gradable = set()
    for prompt_id, prompt in prompts.items():
        grading = prompt.get("grading")
        if isinstance(grading, dict) and grading.get("mode"):
            gradable.add(prompt_id)
    gradable |= set(playability_prompts)
    return gradable


def build_scorecard(results_dir=None, prompts_dir=None, now=None):
    """Return the scorecard payload for the corpus rooted at the given dirs."""
    if results_dir is None:
        results_dir = DEFAULT_RESULTS_DIR
    if prompts_dir is None:
        prompts_dir = DEFAULT_PROMPTS_DIR
    if now is None:
        now = datetime.now(timezone.utc)

    prompts = load_prompts(prompts_dir)
    categories = sorted(
        {
            prompt["category"]
            for prompt in prompts.values()
            if prompt.get("category")
        }
    )
    verdicts, playability_prompts = collect_verdicts(results_dir)
    gradable = gradable_prompts(prompts, playability_prompts)
    ungraded = sorted(
        prompt_id for prompt_id in prompts if prompt_id not in gradable
    )

    graded = {}
    for verdict in verdicts.values():
        prompt_id = verdict["prompt_id"]
        if prompt_id not in gradable:
            continue  # ungraded results never enter numerators or denominators
        prompt = prompts.get(prompt_id)
        category = prompt.get("category") if prompt else None
        if not category:
            continue
        row = graded.setdefault(verdict["model"], {c: None for c in categories})
        counts = row.get(category)
        if counts is None:
            counts = {"passed": 0, "graded": 0}
            row[category] = counts
        counts["graded"] += 1
        if verdict["pass"]:
            counts["passed"] += 1

    return {
        "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "graded": {model: graded[model] for model in sorted(graded)},
        "ungraded_prompts": ungraded,
    }


def _scorecard_categories(scorecard):
    """Return the category columns, in stable order."""
    categories = set()
    for row in scorecard.get("graded", {}).values():
        categories.update(row)
    return sorted(categories)


def _render_cell(counts):
    if counts is None:
        return EMPTY_CELL
    return "{}/{}".format(counts["passed"], counts["graded"])


def render_markdown(scorecard):
    """Render the scorecard payload as markdown mirroring ``frontier_summary``."""
    graded = scorecard.get("graded", {})
    ungraded = scorecard.get("ungraded_prompts", [])
    categories = _scorecard_categories(scorecard)
    models = sorted(graded)

    lines = [
        "# Benchmark scorecard — per-model × per-category pass rate",
        "",
        "**Generated:** {} · **Models:** {} · **Categories:** {} · "
        "**Sources:** committed verdict sidecars (`*_grading.json`) and legacy "
        "`.meta.json` grading fields".format(
            scorecard.get("generated_utc", ""), len(models), len(categories)
        ),
        "",
        "## Method",
        "",
        "Pass rates are computed retroactively from committed evidence only — the "
        "verdict sidecars and legacy meta grading fields that already sit next to "
        "each result; this harness never generates new model output. Every prompt "
        "keeps its one-shot, no-execution-feedback policy. A cell shows "
        "passed/graded verdicts for one model and one prompt category, so its "
        "denominator counts only the results that were actually graded. A model "
        "appears as a row only when it has at least one verdict. An em dash "
        "({}) marks a model/category with no graded verdict; it is an absence, "
        "not a zero. Prompts the harness cannot grade are listed below and are "
        "excluded from every numerator and denominator.".format(EMPTY_CELL),
        "",
        "## Results",
        "",
    ]

    header = "| model | " + " | ".join(categories) + " |"
    separator = "|---|" + "|".join("---" for _ in categories) + "|"
    lines.append(header)
    lines.append(separator)
    for model in models:
        row = graded[model]
        cells = [_render_cell(row.get(category)) for category in categories]
        lines.append("| {} | {} |".format(model, " | ".join(cells)))

    lines.append("")
    lines.append("## Not graded by this harness")
    lines.append("")
    if ungraded:
        for prompt_id in ungraded:
            lines.append("- `{}`".format(prompt_id))
    else:
        lines.append("- (none)")
    lines.append("")

    return "\n".join(lines)


def write_outputs(scorecard, out_json, out_md):
    """Write the JSON and markdown renderings, creating parent dirs as needed."""
    out_json = Path(out_json)
    out_md = Path(out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(scorecard, indent=2) + "\n", encoding="utf-8"
    )
    out_md.write_text(render_markdown(scorecard), encoding="utf-8")


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="scorecard.py",
        description="Aggregate verdict sidecars into a per-model matrix.",
    )
    parser.add_argument(
        "--results-dir", default=None, help="results tree to scan"
    )
    parser.add_argument(
        "--prompts-dir", default=None, help="prompt TOML directory"
    )
    parser.add_argument(
        "--out-json", default=None, help="where to write the JSON scorecard"
    )
    parser.add_argument(
        "--out-md", default=None, help="where to write the markdown scorecard"
    )
    return parser.parse_args(argv)


def main(
    argv=None,
    results_dir=None,
    prompts_dir=None,
    out_json=None,
    out_md=None,
    out=None,
):
    """CLI entry point; returns the process exit code."""
    if argv is None:
        argv = sys.argv[1:]
    if out is None:
        out = sys.stdout

    args = parse_args(argv)
    results_dir = args.results_dir or results_dir or DEFAULT_RESULTS_DIR
    prompts_dir = args.prompts_dir or prompts_dir or DEFAULT_PROMPTS_DIR
    out_json = args.out_json or out_json or DEFAULT_OUT_JSON
    out_md = args.out_md or out_md or DEFAULT_OUT_MD

    scorecard = build_scorecard(results_dir, prompts_dir)
    write_outputs(scorecard, out_json, out_md)

    graded = scorecard["graded"]
    verdicts = sum(
        counts["graded"]
        for row in graded.values()
        for counts in row.values()
        if counts is not None
    )
    print(
        "scorecard: {} model row(s), {} graded verdict(s), {} ungraded prompt(s)"
        " -> {} + {}".format(
            len(graded), verdicts, len(scorecard["ungraded_prompts"]),
            out_json, out_md,
        ),
        file=out,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
