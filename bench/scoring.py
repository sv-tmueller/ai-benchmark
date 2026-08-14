"""Weighted composite scoring and leaderboard formatting."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Sequence

_EPSILON = 1e-9


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class ScoreEntry:
    """One row in the ranked leaderboard."""

    model_key: str
    rank: int
    score: float            # overall composite, 0..1
    speed_component: float   # normalized speed contribution, 0..1
    cost_component: float    # normalized cost contribution, 0..1
    quality_component: float # normalized quality contribution, 0..1


# ---------------------------------------------------------------------------
# Normalisation helper
# ---------------------------------------------------------------------------

def normalize(values: list[float], higher_is_better: bool = True) -> list[float]:
    """Min-max normalise *values* to the ``[0, 1]`` range.

    Edge cases handled:
    * Empty input  -> empty output.
    * All values equal -> every slot becomes ``0.5`` (neutral midpoint),
      regardless of *higher_is_better*.
    """
    n = len(values)
    if n == 0:
        return []

    lo = min(values)
    hi = max(values)

    span = hi - lo
    if abs(span) < _EPSILON:
        # Degenerate case: everything identical -> neutral 0.5
        return [0.5] * n

    out: list[float] = []
    for v in values:
        frac = (v - lo) / span           # 0..1, higher-is-better
        if not higher_is_better:
            frac = 1.0 - frac              # invert for lower-is-better
        out.append(frac)
    return out


# ---------------------------------------------------------------------------
# Core scoring
# ---------------------------------------------------------------------------

_DEFAULT_WEIGHTS: dict[str, float] = {
    "speed": 0.3,
    "cost": 0.3,
    "quality": 0.4,
}


def _safe_grade(result: Any) -> float | None:
    """Return ``result.grade`` if it exists and is a usable float, else None."""
    val = getattr(result, "grade", None)
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    return None


def compute_scores(
    results: Sequence[Any],
    weights: dict[str, float] | None = None,
) -> list[ScoreEntry]:
    """Compute weighted composite scores for every successful result.

    Parameters
    ----------
    results
        Iterable of objects exposing ``model_key``, ``tokens_per_second``,
        ``cost_usd``, ``grade`` (may be absent or None), and ``error``.
    weights
        Override the default weight mapping.  Keys recognised: ``"speed"``,
        ``"cost"``, ``"quality"``.  Weights for excluded components are simply
        discarded and the remainder renormalised to sum to 1.

    Returns
    -------
    list[ScoreEntry]
        Ranked entries (rank 1 = best).  Results with ``error is not None``
        are skipped entirely.
    """
    # --- filter to error-free results ---------------------------------------
    clean = [r for r in results if getattr(r, "error", None) is None]
    if not clean:
        return []

    # --- base weights --------------------------------------------------------
    w = dict(_DEFAULT_WEIGHTS)
    if weights is not None:
        w.update(weights)

    # --- gather raw metric arrays -------------------------------------------
    speeds_raw = [float(getattr(r, "tokens_per_second", 0.0)) for r in clean]

    costs_raw = [float(getattr(r, "cost_usd", 0.0)) for r in clean]
    all_zero_cost = all(c <= _EPSILON for c in costs_raw)

    grades_raw = [_safe_grade(r) for r in clean]
    any_grades = any(g is not None for g in grades_raw)

    # --- determine which components participate ------------------------------
    use_speed = True                       # speed always participates
    use_cost = not all_zero_cost
    use_quality = any_grades

    # Renormalise weights among participating components
    active_keys: list[str] = []
    if use_speed:
        active_keys.append("speed")
    if use_cost:
        active_keys.append("cost")
    if use_quality:
        active_keys.append("quality")

    raw_sum = sum(w.get(k, 0.0) for k in active_keys)
    if raw_sum <= 0:
        # Fall back to uniform distribution among active components
        norm_w = {k: 1.0 / len(active_keys) for k in active_keys}
    else:
        norm_w = {k: w.get(k, 0.0) / raw_sum for k in active_keys}

    # --- normalise each metric -----------------------------------------------
    speed_norm = normalize(speeds_raw, higher_is_better=True)

    if use_cost:
        # Cheaper is better -> transform to "benefit" via 1/(cost+eps)
        cost_benefit = [1.0 / (c + _EPSILON) for c in costs_raw]
        cost_norm = normalize(cost_benefit, higher_is_better=True)
    else:
        cost_norm = [0.0] * len(clean)

    if use_quality:
        # Fill missing grades with the mean of available grades so they neither
        # benefit nor penalise unfairly.
        present = [g for g in grades_raw if g is not None]
        avg_grade = sum(present) / len(present) if present else 0.0
        filled = [(g if g is not None else avg_grade) for g in grades_raw]
        quality_norm = normalize(filled, higher_is_better=True)
    else:
        quality_norm = [0.0] * len(clean)

    # --- composite score -----------------------------------------------------
    entries: list[ScoreEntry] = []
    for idx, r in enumerate(clean):
        score = (
            norm_w.get("speed", 0.0) * speed_norm[idx]
            + norm_w.get("cost", 0.0) * cost_norm[idx]
            + norm_w.get("quality", 0.0) * quality_norm[idx]
        )
        entries.append(
            ScoreEntry(
                model_key=getattr(r, "model_key", ""),
                rank=0,                 # assigned after sorting
                score=score,
                speed_component=speed_norm[idx],
                cost_component=cost_norm[idx],
                quality_component=quality_norm[idx],
            )
        )

    # Sort descending by score, tie-break alphabetically for determinism
    entries.sort(key=lambda e: (-e.score, e.model_key))
    for pos, entry in enumerate(entries, start=1):
        entry.rank = pos

    return entries


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------

def _fmt_cell(value: float | None, fmt: str = "{:.3f}") -> str:
    if value is None:
        return "-"
    return fmt.format(value)


def format_leaderboard(entries: list[ScoreEntry]) -> str:
    """Render *entries* as a fixed-width ASCII table suitable for consoles.

    Columns: Rank · Model · Score · Speed · Cost · Quality
    """
    headers = ("Rank", "Model", "Score", "Speed", "Cost", "Quality")
    rows: list[tuple[str, str, str, str, str, str]] = [
        (
            str(e.rank),
            e.model_key,
            f"{e.score:.3f}",
            f"{e.speed_component:.3f}",
            f"{e.cost_component:.3f}",
            f"{e.quality_component:.3f}",
        )
        for e in entries
    ]

    # Column widths derived from header + widest cell
    col_widths: list[int] = []
    for ci, hdr in enumerate(headers):
        w = len(hdr)
        for row in rows:
            w = max(w, len(row[ci]))
        col_widths.append(w)

    sep = "+" + "+".join("-" * (cw + 2) for cw in col_widths) + "+"

    def fmt_row(cells: tuple[str, ...]) -> str:
        parts = []
        for ci, cell in enumerate(cells):
            align_left = ci == 1  # Model column left-aligned
            if align_left:
                parts.append(" " + cell.ljust(col_widths[ci]) + " ")
            else:
                parts.append(" " + cell.rjust(col_widths[ci]) + " ")
        return "|" + "|".join(parts) + "|"

    lines: list[str] = [sep, fmt_row(headers), sep]
    for row in rows:
        lines.append(fmt_row(row))
    lines.append(sep)
    return "\n".join(lines)


def leaderboard_to_dict(entries: list[ScoreEntry]) -> list[dict[str, Any]]:
    """Serialise *entries* to a list of dicts for JSON output."""
    return [asdict(e) for e in entries]
