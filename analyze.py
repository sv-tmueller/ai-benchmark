#!/usr/bin/env python3
"""Historical trend tracking and dashboard generator for benchmark results.

Scans ``results/benchmark_*.json`` files, builds time-series data keyed by
(model_key, metric), and emits a self-contained HTML dashboard with embedded
SVG line charts.  Optionally generates PNG charts if matplotlib is available.

Usage::

    python analyze.py                      # full dashboard, default filters
    python analyze.py --metric latency     # single chart
    python analyze.py --model gpt-4o       # single model
    python analyze.py --since 2025-01-01   # only runs since this date
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import html
import json
import os
import statistics
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants & metric definitions
# ---------------------------------------------------------------------------

RESULTS_GLOB = "benchmark_*.json"
CHARTS_DIR = os.path.join("results", "charts")

# Metric -> (field name, aggregator, chart title, y-axis label, decimal places)
METRIC_DEFS: Dict[str, Tuple[str, str, str, str, int]] = {
    "latency": ("total_time",        "avg", "Average Latency Over Time",  "Time (s)",      2),
    "throughput": ("tokens_per_second", "avg", "Throughput (tok/s) Over Time", "Tokens/sec", 2),
    "grade": ("grade",              "avg", "Quality Grade Over Time",    "Grade (0-10)",  2),
    "cost": ("cost_usd",            "avg", "Cost Per Run Over Time",      "USD ($)",       4),
}

PALETTE = [
    "#2563eb", "#dc2626", "#059669", "#d97706",
    "#7c3aed", "#db2777", "#0891b2", "#65a30d",
    "#ea580c", "#4f46e5", "#0d9488", "#ca8a04",
]


# ---------------------------------------------------------------------------
# Data loading & filtering
# ---------------------------------------------------------------------------

def _parse_iso(ts: str) -> _dt.datetime:
    """Parse an ISO-8601 timestamp string tolerantly."""
    ts = ts.strip()
    # Handle trailing Z
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        dt = _dt.datetime.fromisoformat(ts)
    except ValueError:
        # Fall back to stripping fractional seconds beyond microseconds
        try:
            dt = _dt.datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            dt = _dt.datetime.strptime(ts[:10], "%Y-%m-%d")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt


def load_result_files(results_dir: str) -> List[dict]:
    """Return a list of parsed benchmark dicts sorted by generated_at ascending."""
    pattern = os.path.join(results_dir, RESULTS_GLOB)
    paths = sorted(glob.glob(pattern))
    entries: List[Tuple[_dt.datetime, dict]] = []
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: skipping unreadable file {p}: {exc}", file=sys.stderr)
            continue
        ga = data.get("generated_at")
        if not ga:
            print(f"Warning: skipping {p} (missing generated_at)", file=sys.stderr)
            continue
        entries.append((_parse_iso(ga), data))
    entries.sort(key=lambda t: t[0])
    return [d for _, d in entries]


def filter_results(
    entries: List[dict],
    *,
    model: str | None,
    prompt_id: str | None,
    since: _dt.datetime | None,
) -> List[Tuple[_dt.datetime, List[dict]]]:
    """Apply model/prompt/date filters, returning [(timestamp, [result_objs]), ...]."""
    out: List[Tuple[_dt.datetime, List[dict]]] = []
    for data in entries:
        ts = _parse_iso(data["generated_at"])
        if since is not None and ts < since:
            continue
        rows: List[dict] = []
        for r in data.get("results", []):
            if model is not None and r.get("model_key") != model:
                continue
            if prompt_id is not None and r.get("prompt_id") != prompt_id:
                continue
            rows.append(r)
        if rows:
            out.append((ts, rows))
    return out


# ---------------------------------------------------------------------------
# Time series building
# ---------------------------------------------------------------------------

def aggregate_metric(rows: List[dict], field: str, agg: str) -> float | None:
    vals = [float(r[field]) for r in rows if r.get(field) is not None]
    if not vals:
        return None
    if agg == "avg":
        return statistics.mean(vals)
    if agg == "sum":
        return sum(vals)
    if agg == "median":
        return statistics.median(vals)
    if agg == "min":
        return min(vals)
    if agg == "max":
        return max(vals)
    return statistics.mean(vals)


def build_series(
    filtered: List[Tuple[_dt.datetime, List[dict]]],
) -> Dict[str, Dict[str, List[Tuple[_dt.datetime, float]]]]:
    """Build nested mapping: metric -> model_key -> [(timestamp, value), ...]."""
    series: Dict[str, Dict[str, List[Tuple[_dt.datetime, float]]]] = {}
    for metric, (field, agg, *_rest) in METRIC_DEFS.items():
        series[metric] = defaultdict(list)
        for ts, rows in filtered:
            # Group by model_key within this run
            per_model: Dict[str, List[dict]] = defaultdict(list)
            for r in rows:
                mk = r.get("model_key", "?")
                per_model[mk].append(r)
            for mk, mrows in per_model.items():
                val = aggregate_metric(mrows, field, agg)
                if val is not None:
                    series[metric][mk].append((ts, val))
    return series


def collect_models(series: Dict[str, Dict[str, list]]) -> List[str]:
    models: set[str] = set()
    for metric_data in series.values():
        models.update(metric_data.keys())
    return sorted(models)


# ---------------------------------------------------------------------------
# SVG chart rendering
# ---------------------------------------------------------------------------

W_PX = 800
H_PX = 360
PAD_L = 70
PAD_R = 30
PAD_T = 50
PAD_B = 60

PLOT_W = W_PX - PAD_L - PAD_R
PLOT_H = H_PX - PAD_T - PAD_B


def _fmt_ts_axis(dt: _dt.datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def _esc(s: str) -> str:
    return html.escape(str(s))


def svg_chart(
    title: str,
    ylabel: str,
    models: List[str],
    series_by_model: Dict[str, List[Tuple[_dt.datetime, float]]],
    decimals: int,
) -> str:
    """Render a single SVG chart as a string."""

    color_map = {m: PALETTE[i % len(PALETTE)] for i, m in enumerate(models)}

    # Collect all points across models to determine axis ranges
    all_points: List[Tuple[float, float]] = []  # (x_epoch, y_val)
    epoch_min: float | None = None
    epoch_max: float | None = None
    y_vals: List[float] = []

    pts_by_model: Dict[str, List[Tuple[float, float, _dt.datetime]]] = {}

    for m in models:
        pts = series_by_model.get(m, [])
        xs = []
        for ts, val in pts:
            ep = ts.timestamp()
            xs.append(ep)
            y_vals.append(val)
            all_points.append((ep, val))
            if epoch_min is None or ep < epoch_min:
                epoch_min = ep
            if epoch_max is None or ep > epoch_max:
                epoch_max = ep
        pts_by_model[m] = [(ts.timestamp(), val, ts) for ts, val in pts]

    parts: List[str] = []
    parts.append(f'<svg width="{W_PX}" height="{H_PX}" viewBox="0 0 {W_PX} {H_PX}" '
                 f'class="chart" xmlns="http://www.w3.org/2000/svg">')
    parts.append('<style>')
    parts.append('.chart-bg{fill:#fafafa;}')
    parts.append('.axis-text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;'
                 'font-size:12px;fill:#333;}')
    parts.append('.title-text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;'
                 'font-size:16px;font-weight:700;fill:#111;}')
    parts.append('.gridline{stroke:#ddd;stroke-width:1;}')
    parts.append('</style>')

    # Background
    parts.append(f'<rect x="0" y="0" width="{W_PX}" height="{H_PX}" rx="8" ry="8" class="chart-bg"/>')

    # Title
    parts.append(f'<text x="{W_PX // 2}" y="28" text-anchor="middle" class="title-text">{_esc(title)}</text>')

    # Empty plot area
    parts.append(f'<rect x="{PAD_L}" y="{PAD_T}" width="{PLOT_W}" height="{PLOT_H}" '
                 f'fill="#fff" stroke="#ccc" stroke-width="1"/>')

    if not all_points or epoch_min is None or epoch_max is None or not y_vals:
        parts.append(f'<text x="{W_PX // 2}" y="{H_PX // 2}" text-anchor="middle" '
                     f'class="axis-text" fill="#999">No data</text>')
        parts.append("</svg>")
        return "\n".join(parts)

    # Axis ranges
    y_min_raw = min(y_vals)
    y_max_raw = max(y_vals)
    if y_min_raw == y_max_raw:
        pad = abs(y_min_raw) * 0.1 + 0.001
    else:
        pad = (y_max_raw - y_min_raw) * 0.1
    y_min = y_min_raw - pad
    y_max = y_max_raw + pad

    def sx(ep: float) -> float:
        if epoch_max == epoch_min:
            return PAD_L + PLOT_W / 2
        return PAD_L + ((ep - epoch_min) / (epoch_max - epoch_min)) * PLOT_W

    def sy(v: float) -> float:
        if y_max == y_min:
            return PAD_T + PLOT_H / 2
        return PAD_T + PLOT_H - ((v - y_min) / (y_max - y_min)) * PLOT_H

    # Gridlines + Y labels (5 ticks)
    for i in range(5):
        frac = i / 4
        gy = PAD_T + PLOT_H - frac * PLOT_H
        gv = y_min + frac * (y_max - y_min)
        parts.append(f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{PAD_L + PLOT_W}" y2="{gy:.1f}" '
                     f'class="gridline"/>')
        parts.append(f'<text x="{PAD_L - 8}" y="{gy + 4:.1f}" text-anchor="end" '
                     f'class="axis-text">{gv:.{decimals}f}</text>')

    # X axis tick labels (5 evenly spaced timestamps)
    for i in range(5):
        frac = i / 4
        gx = PAD_L + frac * PLOT_W
        gep = epoch_min + frac * (epoch_max - epoch_min)
        gd = _dt.datetime.fromtimestamp(gep, tz=_dt.timezone.utc)
        parts.append(f'<line x1="{gx:.1f}" y1="{PAD_T + PLOT_H}" x2="{gx:.1f}" '
                     f'y2="{PAD_T + PLOT_H + 5}" stroke="#aaa"/>')
        label = gd.strftime("%m/%d")
        parts.append(f'<text x="{gx:.1f}" y="{PAD_T + PLOT_H + 22}" text-anchor="middle" '
                     f'class="axis-text">{label}</text>')

    # Axis titles
    parts.append(f'<text x="{PAD_L + PLOT_W / 2}" y="{H_PX - 10}" text-anchor="middle" '
                 f'class="axis-text">Date</text>')
    # Rotated Y label
    parts.append(f'<text transform="translate({18},{PAD_T + PLOT_H / 2}) rotate(-90)" '
                 f'text-anchor="middle" class="axis-text">{_esc(ylabel)}</text>')

    # One polyline per model + point circles with tooltip titles
    for m in models:
        pts = pts_by_model.get(m, [])
        if not pts:
            continue
        col = color_map[m]
        coords = [(sx(ep), sy(v)) for ep, v, _ in pts]
        poly_str = " ".join(f"{cx:.1f},{cy:.1f}" for cx, cy in coords)
        parts.append(f'<polyline points="{poly_str}" fill="none" stroke="{col}" '
                     f'stroke-width="2" />')
        for (ep, v, ts), (cx, cy) in zip(pts, coords):
            tip = (f'{_esc(m)} | {_fmt_ts_axis(ts)} | {ylabel}: {v:.{decimals}f}')
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="{col}" '
                f'stroke="#fff" stroke-width="1">'
                f'<title>{tip}</title></circle>'
            )

    # Legend
    legend_items = [m for m in models if pts_by_model.get(m)]
    ly = PAD_T + 14
    lx = PAD_L + PLOT_W - 140
    if legend_items:
        parts.append(f'<rect x="{lx - 8}" y="{ly - 14}" width="135" '
                     f'height="{len(legend_items) * 18 + 8}" rx="4" ry="4" '
                     f'fill="#ffffffee" stroke="#ddd"/>')
        for i, m in enumerate(legend_items):
            yy = ly + i * 18
            col = color_map[m]
            parts.append(f'<line x1="{lx}" y1="{yy}" x2="{lx + 20}" y2="{yy}" '
                         f'stroke="{col}" stroke-width="2"/>')
            parts.append(f'<text x="{lx + 26}" y="{yy + 4}" class="axis-text">{_esc(m)[:14]}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# HTML assembly
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Benchmark Trend Dashboard</title>
<style>
  :root {{ --bg:#0f172a; --card:#1e293b; --fg:#e2e8f0; --accent:#38bdf8; }}
  body {{ margin:0; padding:24px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
         background:var(--bg); color:var(--fg); }}
  header {{ margin-bottom:24px; }}
  h1 {{ margin:0 0 4px; font-size:28px; }}
  .subtitle {{ color:#94a3b8; font-size:14px; }}
  .summary {{ display:flex; gap:16px; flex-wrap:wrap; margin-top:16px; }}
  .stat {{ background:var(--card); border-radius:10px; padding:14px 18px; min-width:120px; }}
  .stat .num {{ font-size:24px; font-weight:700; color:var(--accent); }}
  .stat .lbl {{ font-size:12px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:20px; }}
  .panel {{ background:var(--card); border-radius:12px; padding:16px; overflow:auto; }}
  footer {{ margin-top:32px; color:#64748b; font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>Benchmark Trend Dashboard</h1>
  <div class="subtitle">{filters_summary}</div>
  <div class="subtitle" style="margin-top:4px;">Generated {gen_time}</div>
  <div class="summary">{stats_html}</div>
</header>
<div class="grid">
{charts}
</div>
<footer>Saved to {out_path}. Self-contained HTML · no external dependencies.</footer>
</body>
</html>
"""


def build_stats(filtered: List[Tuple[_dt.datetime, List[dict]]]) -> str:
    if not filtered:
        return ""
    total_runs = len(filtered)
    total_rows = sum(len(rs) for _, rs in filtered)
    all_costs = [float(r["cost_usd"]) for _, rs in filtered for r in rs if r.get("cost_usd") is not None]
    avg_cost = statistics.mean(all_costs) if all_costs else 0.0
    timespan = filtered[-1][0] - filtered[0][0]
    days = timespan.total_seconds() / 86400
    stat_cards = [
        ("Runs", str(total_runs)),
        ("Results", str(total_rows)),
        ("Avg Cost", f"${avg_cost:.4f}"),
        ("Timespan", f"{days:.1f}d"),
    ]
    cards = "".join(
        f'<div class="stat"><div class="num">{v}</div><div class="lbl">{lbl}</div></div>'
        for lbl, v in stat_cards
    )
    return cards


def build_dashboard(
    series: Dict[str, Dict[str, List[Tuple[_dt.datetime, float]]]],
    metrics: List[str],
    models: List[str],
    out_path: str,
    filters_desc: str,
) -> None:
    panels: List[str] = []
    for metric in metrics:
        field, agg, title, ylabel, dec = METRIC_DEFS[metric]
        panel_svg = svg_chart(title, ylabel, models, series.get(metric, {}), dec)
        panels.append(f'<div class="panel">\n{panel_svg}\n</div>')

    stats_html = ""  # computed outside; placeholder filled below
    # We compute stats from the flattened filtered data if available; here we approximate
    # using series sums.
    gen_time = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html_doc = HTML_TEMPLATE.format(
        filters_summary=filters_desc,
        gen_time=gen_time,
        stats_html=stats_html,
        charts="\n".join(panels),
        out_path=_esc(out_path),
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html_doc)
    print(f"Wrote HTML dashboard -> {out_path}")


def build_dashboard_with_stats(
    series: Dict[str, Dict[str, List[Tuple[_dt.datetime, float]]]],
    filtered: List[Tuple[_dt.datetime, List[dict]]],
    metrics: List[str],
    models: List[str],
    out_path: str,
    filters_desc: str,
) -> None:
    panels: List[str] = []
    for metric in metrics:
        field, agg, title, ylabel, dec = METRIC_DEFS[metric]
        panel_svg = svg_chart(title, ylabel, models, series.get(metric, {}), dec)
        panels.append(f'<div class="panel">\n{panel_svg}\n</div>')

    stats_html = build_stats(filtered)
    gen_time = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html_doc = HTML_TEMPLATE.format(
        filters_summary=filters_desc,
        gen_time=gen_time,
        stats_html=stats_html,
        charts="\n".join(panels),
        out_path=_esc(out_path),
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html_doc)
    print(f"Wrote HTML dashboard -> {out_path}")


# ---------------------------------------------------------------------------
# Optional matplotlib PNG charts
# ---------------------------------------------------------------------------

def maybe_generate_png_charts(
    series: Dict[str, Dict[str, List[Tuple[_dt.datetime, float]]]],
    metrics: List[str],
    models: List[str],
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        print("matplotlib not installed — skipping PNG chart generation.")
        return

    os.makedirs(CHARTS_DIR, exist_ok=True)
    palette = PALETTE
    for metric in metrics:
        field, agg, title, ylabel, dec = METRIC_DEFS[metric]
        fig, ax = plt.subplots(figsize=(8, 4))
        plotted_any = False
        for i, m in enumerate(models):
            pts = series.get(metric, {}).get(m, [])
            if not pts:
                continue
            dts = [t for t, _ in pts]
            vals = [v for _, v in pts]
            ax.plot(dts, vals, marker="o", linestyle="-", linewidth=1.5,
                    markersize=4, label=m, color=palette[i % len(palette)])
            plotted_any = True
        if not plotted_any:
            plt.close(fig)
            continue
        ax.set_title(title)
        ax.set_xlabel("Date")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc="best")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        fig.autofmt_xdate(rotation=30)
        fig.tight_layout()
        fname = os.path.join(CHARTS_DIR, f"{metric}_over_time.png")
        fig.savefig(fname, dpi=130)
        plt.close(fig)
        print(f"Wrote PNG chart -> {fname}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="analyze.py",
        description="Analyze benchmark results and generate a trend dashboard.",
    )
    p.add_argument("--metric", choices=list(METRIC_DEFS.keys()),
                   help="Generate only this metric's chart.")
    p.add_argument("--model", help="Filter results to a single model_key.")
    p.add_argument("--prompt-id", dest="prompt_id", help="Filter results to a single prompt_id.")
    p.add_argument("--since", metavar="DATE", help="Only include runs from this ISO date onward "
                                                   "(e.g. 2025-01-01T00:00:00Z).")
    p.add_argument("--all-models", action="store_true", dest="all_models",
                   help="Include all models (disable implicit limiting). Currently informational.")
    p.add_argument("--output", default=os.path.join("results", "dashboard.html"), metavar="PATH",
                   help="Output HTML path (default: %(default)s).")
    return p.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)

    results_dir = os.path.join(".", "results")
    if not os.path.isdir(results_dir):
        print(f"No results directory found at {results_dir}/", file=sys.stderr)
        return 1

    entries = load_result_files(results_dir)
    if not entries:
        print("No benchmark_*.json files found in results/", file=sys.stderr)
        return 1

    since_dt: _dt.datetime | None = None
    if args.since:
        try:
            since_dt = _parse_iso(args.since)
        except Exception as exc:
            print(f"Invalid --since value '{args.since}': {exc}", file=sys.stderr)
            return 2

    filtered = filter_results(entries, model=args.model, prompt_id=args.prompt_id, since=since_dt)
    if not filtered:
        print("No results remain after applying filters.", file=sys.stderr)
        return 1

    series = build_series(filtered)
    models = collect_models(series)
    if not models:
        print("No models found in filtered results.", file=sys.stderr)
        return 1

    metrics = [args.metric] if args.metric else list(METRIC_DEFS.keys())

    # Filters summary line
    bits = []
    if args.model:
        bits.append(f"model={args.model}")
    if args.prompt_id:
        bits.append(f"prompt_id={args.prompt_id}")
    if since_dt:
        bits.append(f"since={since_dt.isoformat()}")
    if args.all_models:
        bits.append("all_models")
    filters_desc = ", ".join(bits) if bits else "All runs"

    build_dashboard_with_stats(series, filtered, metrics, models, args.output, filters_desc)
    maybe_generate_png_charts(series, metrics, models)
    return 0


if __name__ == "__main__":
    sys.exit(main())
