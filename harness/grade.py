#!/usr/bin/env python3
"""Grade benchmark results and write verdict sidecars.

``grade.py`` walks ``results/`` and, for every result file whose prompt has a
grading rule, writes ``<result>_grading.json`` next to it with the schema::

    {"prompt_id": str, "model": str, "mode": str, "pass": bool, "detail": str}

A grading rule is either a ``[grading]`` table in the prompt TOML (whose
``mode`` names a module under ``harness/modes/``) or, for game/app results, a
playability verdict in the paired ``.meta.json``. Results with neither are
skipped — never failed. Prompt association goes through the meta sidecar's
``prompt_id`` field, not the filename prefix, because prefixes and directory
names diverge from prompt ids across the corpus.

Usage::

    python harness/grade.py --all
    python harness/grade.py --prompt game-melon-jelly
"""

import argparse
import importlib
import json
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
RESULTS_DIR = REPO_ROOT / "results"
MODES_PACKAGE = "harness.modes"

# Running this file directly (`python harness/grade.py`) puts `harness/` on
# sys.path, so make the repo root importable for the `harness.modes` package.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

META_SUFFIX = ".meta.json"
SIDECAR_SUFFIX = "_grading.json"
PLAYABILITY_MODE = "playability"

_SKIP_SUFFIXES = (
    META_SUFFIX,
    SIDECAR_SUFFIX,
    "_review.html",
    ".png",
    ".jpg",
    ".jpeg",
)
_SKIP_NAMES = ("rebuild_verdict.md",)
_SKIP_NAME_PREFIXES = ("rebuild_verdict_",)


def discover_modes(package=MODES_PACKAGE):
    """Return ``{mode_name: grade_callable}`` for every mode module."""
    pkg = importlib.import_module(package)
    modes = {}
    for module_info in pkg.__path__:
        for path in sorted(Path(module_info).glob("*.py")):
            name = path.stem
            if name.startswith("_"):
                continue
            module = importlib.import_module("{}.{}".format(package, name))
            grade_fn = getattr(module, "grade", None)
            if callable(grade_fn):
                modes[name] = grade_fn
    return modes


def module_name_for_mode(mode_name):
    """Map a ``[grading].mode`` string to its module name (D1a).

    TOML mode strings may be hyphenated (``some-mode``) while module files are
    underscored (``some_mode.py``); the sidecar ``mode`` field keeps the
    literal TOML string. Non-string values are returned unchanged.
    """
    if isinstance(mode_name, str):
        return mode_name.replace("-", "_")
    return mode_name


def load_prompts(prompts_dir):
    """Return ``{prompt_id: parsed TOML}`` for every prompt file."""
    prompts = {}
    for path in sorted(Path(prompts_dir).glob("*.toml")):
        if path.name.endswith(".fixtures.toml"):
            continue
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        prompts[data["id"]] = data
    return prompts


def is_result_file(path):
    """True when ``path`` is a gradable result artifact (not harness output)."""
    name = path.name
    if name in _SKIP_NAMES or name.startswith(_SKIP_NAME_PREFIXES):
        return False
    return not name.endswith(_SKIP_SUFFIXES)


def read_meta(result_path):
    """Return the parsed paired meta sidecar, or ``None`` when absent/invalid."""
    meta_path = result_path.with_name(result_path.stem + META_SUFFIX)
    if not meta_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return meta if isinstance(meta, dict) else None


def resolve_prompt(result_path, meta, prompts):
    """Resolve the prompt TOML that produced ``result_path``.

    Prefers the meta's ``prompt_id`` (and ``toml`` filename); falls back to a
    prompt-id-suffix match on the directory name only when no meta exists.
    """
    if meta:
        prompt_id = meta.get("prompt_id")
        if prompt_id in prompts:
            return prompts[prompt_id]
        toml_name = meta.get("toml")
        if toml_name:
            for prompt in prompts.values():
                if "{}.toml".format(prompt["id"]) == toml_name:
                    return prompt
        return None

    dir_name = result_path.parent.name
    for prompt_id, prompt in prompts.items():
        if prompt_id == dir_name or prompt_id.endswith("-" + dir_name):
            return prompt
    return None


def resolve_mode(prompt, meta):
    """Return the mode that should grade this result, or ``None`` to skip."""
    grading = prompt.get("grading") if prompt else None
    if isinstance(grading, dict) and grading.get("mode"):
        return grading["mode"], grading

    playability = meta.get("playability_verification") if meta else None
    if isinstance(playability, dict) and playability.get("playability_verdict"):
        return PLAYABILITY_MODE, {}

    playability = meta.get("playability") if meta else None
    if isinstance(playability, dict) and playability.get("label"):
        return PLAYABILITY_MODE, {}

    return None, None


def iter_results(results_dir):
    """Yield result files under ``results/*/`` (root files are not results)."""
    for directory in sorted(Path(results_dir).iterdir()):
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if path.is_file() and is_result_file(path):
                yield path


def grade_all(modes, prompts, results_dir, prompt_filter=None, out=None):
    """Grade every eligible result; return ``(graded, skipped, errors)``."""
    if out is None:
        out = sys.stdout
    graded = skipped = errors = 0
    for result_path in iter_results(results_dir):
        meta = read_meta(result_path)
        prompt = resolve_prompt(result_path, meta, prompts)

        # A meta verdict whose prompt_id resolves to no prompt TOML (and whose
        # directory matches none either) cannot be graded — skip it, never
        # fail, under both --all and --prompt.
        if prompt is None:
            skipped += 1
            continue

        mode_name, grading = resolve_mode(prompt, meta)

        if mode_name is None:
            skipped += 1
            continue

        if prompt_filter is not None and prompt["id"] != prompt_filter:
            continue

        grade_fn = modes.get(module_name_for_mode(mode_name))
        if grade_fn is None:
            errors += 1
            print(
                "  ERR {}: no module for mode '{}'".format(result_path, mode_name),
                file=out,
            )
            continue

        try:
            verdict = grade_fn(result_path, grading, prompt)
        except Exception as exc:  # noqa: BLE001 - one bad result must not stop the run
            errors += 1
            print("  ERR {}: {}".format(result_path, exc), file=out)
            continue

        sidecar = result_path.with_name(result_path.stem + SIDECAR_SUFFIX)
        sidecar.write_text(
            json.dumps(verdict, indent=2) + "\n", encoding="utf-8"
        )
        graded += 1
        print(
            "  {}  {}  {}".format(
                "PASS" if verdict["pass"] else "FAIL", verdict["mode"], sidecar
            ),
            file=out,
        )

    return graded, skipped, errors


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="grade.py",
        description="Grade benchmark results and write verdict sidecars.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--prompt", metavar="ID", help="grade only results for this prompt id"
    )
    group.add_argument(
        "--all", action="store_true", help="grade every result with a grading rule"
    )
    return parser.parse_args(argv)


def main(argv=None, results_dir=None, prompts_dir=None, out=None, modes=None):
    """CLI entry point; returns the process exit code."""
    if results_dir is None:
        results_dir = RESULTS_DIR
    if prompts_dir is None:
        prompts_dir = PROMPTS_DIR
    if out is None:
        out = sys.stdout

    args = parse_args(sys.argv[1:] if argv is None else argv)

    prompts = load_prompts(prompts_dir)
    if args.prompt is not None and args.prompt not in prompts:
        print("unknown prompt id: {}".format(args.prompt), file=out)
        return 1

    if modes is None:
        modes = discover_modes()

    prompt_filter = None if args.all else args.prompt
    graded, skipped, errors = grade_all(
        modes, prompts, results_dir, prompt_filter=prompt_filter, out=out
    )
    print(
        "graded {} result(s); skipped {}; errors {}".format(graded, skipped, errors),
        file=out,
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
