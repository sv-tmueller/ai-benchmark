"""Expand prompt specs with fixture data for parameterized prompting."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # pip install tomli (older Python)
    except ModuleNotFoundError:
        raise ImportError(
            "This project requires Python 3.11+ (built-in tomllib) "
            "or the 'tomli' package: pip install tomli"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def slugify(text: str) -> str:
    """Lowercase *text*, replace spaces/non-alphanumeric with hyphens,
    and collapse consecutive hyphens."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def find_placeholders(text: str) -> list[str]:
    """Return a list of unique ``{{var_name}}`` placeholder names found in
    *text*, preserving first-appearance order."""
    seen: set[str] = set()
    names: list[str] = []
    for m in _PLACEHOLDER_RE.finditer(text):
        name = m.group(1)
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _substitute(text: str | None, variables: dict[str, Any]) -> str | None:
    """Replace ``{{var_name}}`` placeholders in *text* using *variables*.

    Raises :class:`ValueError` if a placeholder has no matching variable.
    """
    if text is None:
        return None

    def _repl(m: re.Match[str]) -> str:
        name = m.group(1)
        if name not in variables:
            raise ValueError(f"No fixture variable provided for placeholder '{name}'")
        return str(variables[name])

    return _PLACEHOLDER_RE.sub(_repl, text)


# ---------------------------------------------------------------------------
# Fixtures loading
# ---------------------------------------------------------------------------

def load_fixtures(prompt_path: Path) -> list[dict] | None:
    """Look for a sibling ``<stem>.fixtures.toml`` file next to *prompt_path*
    and return its ``cases`` list.  Returns ``None`` if the file does not
    exist.
    """
    fixtures_path = prompt_path.with_suffix(".fixtures.toml")
    if not fixtures_path.exists():
        return None
    with open(fixtures_path, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("cases", [])  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Expansion
# ---------------------------------------------------------------------------

_SPEC_KEYS = (
    "id",
    "title",
    "category",
    "difficulty",
    "system",
    "user",
    "max_tokens",
    "temperature",
    "save_as",
    "file_prefix",
)


def _spec_to_dict(spec: Any) -> dict[str, Any]:
    """Normalise a :class:`~bench.config.PromptSpec` (or plain dict) into a
    plain dict containing the canonical keys."""
    if isinstance(spec, dict):
        return {k: spec.get(k) for k in _SPEC_KEYS}
    # Assume dataclass-like object with attributes
    return {k: getattr(spec, k, None) for k in _SPEC_KEYS}


def expand_prompt(spec: Any, fixtures_data: list[dict]) -> list[dict]:
    """Expand *spec* into one dict per fixture case in *fixtures_data*.

    Parameters
    ----------
    spec:
        A :class:`PromptSpec` instance or a plain dict with keys ``id``,
        ``title``, ``category``, ``difficulty``, ``system``, ``user``,
        ``max_tokens``, ``temperature``, ``save_as``, ``file_prefix``.
    fixtures_data:
        A list of fixture-case dicts.  Each case must have a ``description``
        (str) and a ``vars`` sub-dict mapping placeholder names to values.

    Returns
    -------
    list[dict]
        One plain dict per fixture case, with the same keys as *spec*.
        Text fields (``system``, ``user``) have ``{{var_name}}`` placeholders
        replaced.  The ``id`` is suffixed with ``__`` followed by the
        slugified case description.

    Raises
    ------
    ValueError
        If a placeholder in ``system`` or ``user`` has no matching variable
        in a fixture case's ``vars``.
    """
    base = _spec_to_dict(spec)
    expanded: list[dict] = []

    for case in fixtures_data:
        description: str = case.get("description", "")
        variables: dict[str, Any] = case.get("vars", {})

        row = dict(base)
        row["system"] = _substitute(base.get("system"), variables)
        row["user"] = _substitute(base.get("user"), variables)

        suffix = slugify(description)
        if suffix:
            row["id"] = f"{base['id']}__{suffix}"

        expanded.append(row)

    return expanded
