"""Helpers shared by the grading modes.

This module deliberately does not define a mode: its name starts with an
underscore, and :func:`harness.grade.discover_modes` skips such modules, so
adding it does not change the mode registry.
"""

import re
from pathlib import Path

META_SUFFIX = ".meta.json"
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


def pair_meta(result_path):
    """Return the ``<stem>.meta.json`` sibling of ``result_path``, or ``None``.

    Prompt association goes through this sidecar's ``prompt_id`` field;
    filename prefixes diverge from prompt ids across the corpus.
    """
    result_path = Path(result_path)
    meta = result_path.with_name(result_path.stem + META_SUFFIX)
    return meta if meta.is_file() else None


def derive_model(result_path, prompt=None):
    """Extract the model tag from a result filename (D1a).

    The model is the filename-stem remainder after ``<file_prefix>_``, where
    ``file_prefix`` comes from the prompt TOML. Prefixes and results-directory
    names diverge from prompt ids across the corpus, so the directory name is
    only a last resort:

    1. ``prompt["file_prefix"]`` — e.g. ``melon-jelly`` in
       ``results/melon-jelly/melon-jelly_claude_fable_5_2.html``.
    2. ``prompt["id"]`` — for prompts that declare no ``file_prefix``.
    3. The stem after its first underscore — for results whose prompt is
       unknown.

    The remainder keeps embedded underscores and name suffixes intact
    (``melon-jelly_claude_haiku_5_5-v2.html`` -> ``claude_haiku_5_5-v2``), so
    for a ``/bench-run`` result it is the run tag, model and effort together
    (``melon-jelly_claude_fable_5_2_high.html`` -> ``claude_fable_5_2_high``).
    Returns an empty string when no rule matches.
    """
    result_path = Path(result_path)
    stem = result_path.stem
    for candidate in _model_prefix_candidates(prompt):
        if stem.startswith(candidate + "_"):
            return stem[len(candidate) + 1:]
    if "_" in stem:
        return stem.split("_", 1)[1]
    return ""


def _model_prefix_candidates(prompt):
    """Return the filename prefixes to try, in order, for ``prompt``."""
    if not isinstance(prompt, dict):
        return []
    candidates = []
    for key in ("file_prefix", "id"):
        value = prompt.get(key)
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def model_tag(model_id):
    """Return the results-file model tag for a session model id.

    ``claude-fable-5-2`` -> ``claude_fable_5_2``. A trailing ``[...]`` suffix
    (such as ``[1m]``) and a trailing ``-YYYYMMDD`` stamp are dropped, the rest
    is lowercased and every run of non-alphanumerics becomes ``_``. Raises
    ``ValueError`` when the result is not a usable tag. The ``/bench-run``
    resolver and ``harness/bench_run_all.py`` both call this, so the two
    cannot disagree.
    """
    model_id = re.sub(r"\[[^\]]*\]$", "", model_id.strip()).strip()
    tag = re.sub(r"[^a-z0-9]+", "_", re.sub(r"-\d{8}$", "", model_id.lower()))
    if not re.fullmatch(r"[a-z][a-z0-9_]*[a-z0-9]", tag):
        raise ValueError("model tag %r from %r is not usable" % (tag, model_id))
    return tag


def session_effort(environ):
    """Return the session's effort level, read from ``CLAUDE_EFFORT``.

    The level is part of every result file name, so it is never typed in and
    never defaulted. Raises ``ValueError`` when the variable is unset, empty
    or not one of :data:`EFFORT_LEVELS`.
    """
    effort = environ.get("CLAUDE_EFFORT", "")
    if not effort:
        raise ValueError("CLAUDE_EFFORT is unset or empty; the effort level is part of the "
                         "result file name and cannot be guessed")
    if effort not in EFFORT_LEVELS:
        raise ValueError("CLAUDE_EFFORT=%r is not one of %s" % (effort, ", ".join(EFFORT_LEVELS)))
    return effort


def run_tag(model_id, effort):
    """Return the results-file tag of one run: model tag, ``_``, effort level.

    ``("claude-fable-5-2", "high")`` -> ``claude_fable_5_2_high``. Raises
    ``ValueError`` for an unusable model id or an unknown effort level.
    """
    if effort not in EFFORT_LEVELS:
        raise ValueError("effort %r is not one of %s" % (effort, ", ".join(EFFORT_LEVELS)))
    return "%s_%s" % (model_tag(model_id), effort)
