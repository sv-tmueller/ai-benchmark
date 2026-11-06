"""Helpers shared by the grading modes.

This module deliberately does not define a mode: its name starts with an
underscore, and :func:`harness.grade.discover_modes` skips such modules, so
adding it does not change the mode registry.
"""

from pathlib import Path

META_SUFFIX = ".meta.json"


def pair_meta(result_path):
    """Return the ``<stem>.meta.json`` sibling of ``result_path``, or ``None``.

    Prompt association goes through this sidecar's ``prompt_id`` field;
    filename prefixes diverge from prompt ids across the corpus.
    """
    result_path = Path(result_path)
    meta = result_path.with_name(result_path.stem + META_SUFFIX)
    return meta if meta.is_file() else None


def derive_model(result_path):
    """Extract the model tag from a ``<dirname>_<model>.<ext>`` result name.

    The remainder keeps embedded underscores and name suffixes intact
    (``melon-jelly_claude_haiku_5_5-v2.html`` -> ``claude_haiku_5_5-v2``).
    Returns an empty string when the name does not carry the directory prefix.
    """
    result_path = Path(result_path)
    prefix = result_path.parent.name + "_"
    stem = result_path.stem
    if stem.startswith(prefix):
        return stem[len(prefix):]
    return ""
