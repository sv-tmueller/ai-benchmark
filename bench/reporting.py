"""Aggregate results into JSON and Markdown reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .executor import SingleResult


def write_json(results: list[SingleResult], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "num_results": len(results),
        "results": [r.to_dict() for r in results],
    }
    with open(out_path, "w") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return out_path


def _fmt_ms(seconds: float) -> str:
    return f"{seconds * 1000:.0f} ms"


def _fmt_tps(tps: float) -> str:
    return f"{tps:.1f}" if tps > 0 else "-"


def write_markdown(results: list[SingleResult], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Benchmark Report\n")
    lines.append(f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n")

    # --- Summary table -------------------------------------------------------
    lines.append("\n## Summary Table\n")
    lines.append("| Model | Prompt | Category | Tokens (in/out) | Total Time | Tok/s | Cost ($) | Status |")
    lines.append("|-------|--------|----------|-----------------|-------------|-------|----------|--------|")

    for r in results:
        status = "OK" if r.error is None else f"ERR: {r.error[:40]}"
        tok_io = f"{r.prompt_tokens}/{r.completion_tokens}"
        cost_str = f"{r.cost_usd:.4f}" if r.cost_usd > 0 else "-"
        lines.append(
            f"| {r.model_key} | {r.prompt_id} | {r.category} "
            f"| {tok_io} | {_fmt_ms(r.total_time)} | {_fmt_tps(r.tokens_per_second)} "
            f"| {cost_str} | {status} |"
        )

    # --- Per-model aggregate -------------------------------------------------
    lines.append("\n## Per-Model Aggregate\n")
    agg: dict[str, dict[str, Any]] = {}
    for r in results:
        if r.error is not None:
            continue
        bucket = agg.setdefault(r.model_key, {
            "calls": 0, "total_time": 0.0, "tokens_out": 0,
            "tokens_in": 0, "cost": 0.0,
        })
        bucket["calls"] += 1
        bucket["total_time"] += r.total_time
        bucket["tokens_out"] += r.completion_tokens
        bucket["tokens_in"] += r.prompt_tokens
        bucket["cost"] += r.cost_usd

    lines.append("| Model | Calls | Avg Latency | Total Out Tokens | Avg Tok/s | Total Cost ($) |")
    lines.append("|-------|-------|-------------|------------------|-----------|-----------------|")
    for key, b in sorted(agg.items()):
        avg_lat = b["total_time"] / b["calls"] if b["calls"] else 0
        avg_tps = b["tokens_out"] / b["total_time"] if b["total_time"] > 0 else 0
        cost_s = f"{b['cost']:.4f}" if b["cost"] > 0 else "-"
        lines.append(
            f"| {key} | {b['calls']} | {_fmt_ms(avg_lat)} "
            f"| {b['tokens_out']} | {avg_tps:.1f} | {cost_s} |"
        )

    # --- Full responses ------------------------------------------------------
    lines.append("\n## Individual Responses\n")
    for r in results:
        emoji = "PASS" if r.error is None else "FAIL"
        lines.append(f"\n### [{emoji}] {r.model_key} :: {r.prompt_id}")
        meta_parts = [
            f"latency={_fmt_ms(r.total_time)}",
            f"tokens={r.prompt_tokens}+{r.completion_tokens}",
            f"tps={_fmt_tps(r.tokens_per_second)}",
        ]
        if r.cost_usd > 0:
            meta_parts.append(f"cost=${r.cost_usd:.4f}")
        lines.append(f"> {' · '.join(meta_parts)}")
        if r.error:
            lines.append(f"\n**Error:** `{r.error}`\n")
        else:
            lines.append(f"\n```\n{r.response_text}\n```\n")

    out_path.write_text("\n".join(lines))
    return out_path


def print_console_summary(results: list[SingleResult]) -> None:
    ok = sum(1 for r in results if r.error is None)
    fail = len(results) - ok
    total_time = sum(r.total_time for r in results)
    total_out = sum(r.completion_tokens for r in results if r.error is None)
    print()
    print("=" * 60)
    print(f"  Benchmarks complete: {ok} OK, {fail} failed")
    print(f"  Wall time: {total_time:.2f}s   Output tokens: {total_out}")
    print("=" * 60)
    for r in results:
        tag = "OK " if r.error is None else "ERR"
        tps = _fmt_tps(r.tokens_per_second)
        lat = _fmt_ms(r.total_time)
        print(f"  [{tag}] {r.model_key:24s} {r.prompt_id:28s} {lat:>8s}  {tps:>6s} tok/s")
    print()
