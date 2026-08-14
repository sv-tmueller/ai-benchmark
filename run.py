#!/usr/bin/env python3
"""
AI Benchmark Runner
====================
Send curated prompts to any OpenAI-compatible model endpoint and collect
latency, throughput, token-count, cost, grade, and scoring metrics.

Features:
  - Proposal 1: Automated response grading (exact/regex/contains/judge)
  - Proposal 2: SSE streaming with TTFB measurement (--stream)
  - Proposal 3: Side-by-side comparison reports (--compare)
  - Proposal 5: Vision/image prompts (save_as + [images] block)
  - Proposal 6: Prompt parameterization via .fixtures.toml
  - Proposal 7: Weighted composite scoring leaderboard

Usage examples
--------------
  python run.py --model glm_5_2
  python run.py --model glm_5_2 --model chatgpt_5_6 --category coding
  python run.py --model glm_5_2 --stream
  python run.py --model glm_5_2 --model chatgpt_5_6 --compare
  python run.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from bench.config import (
    load_models,
    load_prompts,
    load_runner_config,
)
from bench.executor import execute_once
from bench.reporting import (
    print_console_summary,
    write_json,
    write_markdown,
)


REPO_ROOT = Path(__file__).resolve().parent


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ.

    Existing environment variables always win (we never override them), and a
    missing file is a no-op. Keys are taken verbatim; values have surrounding
    quotes stripped. This keeps API keys out of the shell and out of git —
    .env is gitignored.
    """
    env_path = path or (REPO_ROOT / ".env")
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Benchmark prompts against AI models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--model", "-m", action="append", dest="models", metavar="KEY",
        help="Model registry key from models.toml (repeatable).")
    ap.add_argument("--prompt-id", action="append", dest="prompt_ids", metavar="ID",
        help="Only run prompts with these IDs (repeatable).")
    ap.add_argument("--category", action="append", dest="categories", metavar="CAT",
        help="Only run prompts in these categories (repeatable).")
    ap.add_argument("--difficulty", help="Filter by difficulty: easy|medium|hard.")
    ap.add_argument("--repeats", type=int, help="Override config repeats.")
    ap.add_argument("--cooldown", type=float, help="Override config cooldown (seconds).")
    ap.add_argument("--dry-run", action="store_true", help="Plan only; do not call any API.")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose logging.")
    # Proposal 2: streaming
    ap.add_argument("--stream", action="store_true", default=None,
        help="Force SSE streaming mode for TTFB measurement.")
    ap.add_argument("--no-stream", action="store_false", dest="stream",
        help="Disable streaming mode (use buffered requests).")
    # Proposal 3: comparison
    ap.add_argument("--compare", action="store_true",
        help="Generate side-by-side comparison report.")
    ap.add_argument("--compare-game-html", action="store_true",
        help="Generate HTML tab viewer for game artifacts comparison.")
    # Proposal 7: scoring weights
    ap.add_argument("--weights", type=str, metavar="speed=X,cost=Y,quality=Z",
        help="Override scoring weights (e.g. speed=0.2,cost=0.1,quality=0.7).")
    return ap.parse_args()


def _parse_weights(s: str | None) -> dict[str, float] | None:
    if not s:
        return None
    w: dict[str, float] = {}
    for pair in s.split(","):
        k, _, v = pair.partition("=")
        k = k.strip()
        if k in ("speed", "cost", "quality"):
            w[f"w_{k}"] = float(v.strip())
    return w or None


def main() -> int:
    args = parse_args()

    # Load API keys from a gitignored .env file (if present) before anything
    # reads them. Real env vars take precedence.
    load_dotenv()

    # ---- Load configs --------------------------------------------------------
    models_path = REPO_ROOT / "models.toml"
    prompts_dir = REPO_ROOT / "prompts"
    config_path = REPO_ROOT / "config.toml"

    if not models_path.exists():
        print("Error: models.toml not found.", file=sys.stderr)
        return 1

    all_models = load_models(models_path)
    all_prompts = load_prompts(prompts_dir)
    rcfg = load_runner_config(config_path)

    # ---- Filter models ------------------------------------------------------
    if args.models:
        unknown = [k for k in args.models if k not in all_models]
        if unknown:
            print(f"Unknown model key(s): {', '.join(unknown)}", file=sys.stderr)
            print(f"Available: {', '.join(all_models.keys())}", file=sys.stderr)
            return 1
        selected_models = [all_models[k] for k in args.models]
    else:
        selected_models = list(all_models.values())

    # ---- Filter prompts -----------------------------------------------------
    selected_prompts = list(all_prompts)

    if args.prompt_ids:
        wanted = set(args.prompt_ids)
        selected_prompts = [p for p in selected_prompts if p.id in wanted]

    if args.categories:
        cats = set(args.categories)
        selected_prompts = [p for p in selected_prompts if p.category in cats]

    if args.difficulty:
        selected_prompts = [p for p in selected_prompts if p.difficulty == args.difficulty]

    if not selected_prompts:
        print("No prompts match the given filters.", file=sys.stderr)
        return 1

    # ---- Override config ----------------------------------------------------
    repeats = args.repeats if args.repeats is not None else rcfg.repeats
    cooldown = args.cooldown if args.cooldown is not None else rcfg.cooldown_seconds
    use_stream = args.stream if args.stream is not None else rcfg.stream

    # Scoring weights
    weights_override = _parse_weights(args.weights)
    w_speed = weights_override.get("w_speed", rcfg.w_speed) if weights_override else rcfg.w_speed
    w_cost = weights_override.get("w_cost", rcfg.w_cost) if weights_override else rcfg.w_cost
    w_quality = weights_override.get("w_quality", rcfg.w_quality) if weights_override else rcfg.w_quality

    # ---- Plan ---------------------------------------------------------------
    total_calls = len(selected_models) * len(selected_prompts) * repeats
    print(f"\nModels ({len(selected_models)}): {[m.key for m in selected_models]}")
    print(f"Prompts ({len(selected_prompts)}): {[p.id for p in selected_prompts]}")
    print(f"Repeats: {repeats}  Cooldown: {cooldown}s  Stream: {use_stream}  Total API calls: {total_calls}")

    if args.dry_run:
        print("\n[dry-run] No API calls made.\n")
        return 0

    # ---- Prepare vision images (Proposal 5) ----------------------------------
    vision_cache: dict[str, list[str] | None] = {}
    for prompt in selected_prompts:
        if prompt.images:
            try:
                from bench.vision import load_images_from_prompt
                uris = load_images_from_prompt(prompt.images, prompts_dir)
                vision_cache[prompt.id] = uris if uris else None
            except Exception as exc:
                if args.verbose:
                    print(f"[vision] Failed to load images for {prompt.id}: {exc}")
                vision_cache[prompt.id] = None
        else:
            vision_cache[prompt.id] = None

    # ---- Execute -------------------------------------------------------------
    results = []
    for mi, model in enumerate(selected_models):
        if not model.api_key and model.api_key_env != "":
            if args.verbose:
                print(f"[warn] {model.api_key_env} not set for {model.key}; continuing anyway.")

        for pi, prompt in enumerate(selected_prompts):
            # Proposal 5: skip vision prompts for non-vision models
            img_uris = vision_cache.get(prompt.id)
            if img_uris and not model.supports_vision:
                print(f"  SKIP: {prompt.id} requires vision, {model.key} does not support it")
                continue

            for rep in range(repeats):
                idx = mi * len(selected_prompts) * repeats + pi * repeats + rep + 1
                print(f"[{idx}/{total_calls}] {model.key} :: {prompt.id} (rep {rep + 1})", flush=True)

                if use_stream:
                    from bench.streaming_executor import execute_streaming
                    result = execute_streaming(model, prompt, timeout=rcfg.request_timeout)
                else:
                    result = execute_once(model, prompt, timeout=rcfg.request_timeout,
                                         image_data_uris=img_uris)
                result.repeat_index = rep

                # Proposal 1: grade the result
                if prompt.grading and result.error is None:
                    from bench.grader import grade_result
                    judge_fn = None
                    if prompt.grading.get("mode") == "judge":
                        judge_model_key = prompt.grading.get("judge_model", "")
                        judge_model = all_models.get(judge_model_key)
                        if judge_model:
                            def _make_judge_fn(jm):
                                def judge_fn(_mk, _msgs):
                                    jr = execute_once(jm, prompt, timeout=rcfg.request_timeout)
                                    return jr.response_text
                                return judge_fn
                            judge_fn = _make_judge_fn(judge_model)
                    grade_val, grade_det = grade_result(result.response_text, prompt.grading, judge_fn)
                    # Use setattr to support both SingleResult and StreamedResult
                    setattr(result, "grade", grade_val)
                    setattr(result, "grade_details", grade_det)

                results.append(result)

                if result.error:
                    print(f"  ERROR: {result.error[:120]}")
                elif args.verbose:
                    extras = []
                    if getattr(result, "ttft", 0) > 0:
                        extras.append(f"ttft={result.ttft*1000:.0f}ms")
                    grade_val = getattr(result, "grade", None)
                    if grade_val is not None:
                        extras.append(f"grade={grade_val:.2f}")
                    extra_str = f"  {' '.join(extras)}" if extras else ""
                    print(f"  {result.total_time:.2f}s  "
                          f"in={result.prompt_tokens} out={result.completion_tokens}  "
                          f"{result.tokens_per_second:.1f} tok/s{extra_str}")

                if cooldown > 0 and not (mi == len(selected_models) - 1
                                          and pi == len(selected_prompts) - 1
                                          and rep == repeats - 1):
                    time.sleep(cooldown)

    # ---- Save artifacts (HTML, txt, etc.) -----------------------------------
    results_dir = REPO_ROOT / rcfg.results_dir
    artifacts_dir = results_dir / "artifacts"
    saved_paths: list[Path] = []

    for r in results:
        prompt_spec = next((p for p in selected_prompts if p.id == r.prompt_id), None)
        if not prompt_spec or not prompt_spec.save_as or r.error:
            continue

        ext = prompt_spec.save_as.lstrip(".")
        prefix = prompt_spec.file_prefix or r.prompt_id
        safe_model = r.model_key.replace("/", "_")
        fname = f"{prefix}_{safe_model}"
        if repeats > 1:
            fname += f"_r{r.repeat_index + 1}"
        fname += f".{ext}"

        artifact_path = artifacts_dir / fname
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(r.response_text)
        saved_paths.append(artifact_path)

    if saved_paths:
        print(f"\nSaved {len(saved_paths)} artifact(s) to {artifacts_dir}/:")
        for p in saved_paths:
            print(f"  {p.name}")

    # ---- Compute leaderboard (Proposal 7) ----------------------------------
    leaderboard_entries = None
    try:
        from bench.scoring import compute_scores, leaderboard_to_dict
        weights = {"w_speed": w_speed, "w_cost": w_cost, "w_quality": w_quality}
        scored = compute_scores(results, weights)
        leaderboard_entries = scored
        leaderboard_dicts = leaderboard_to_dict(scored)
    except Exception as exc:
        if args.verbose:
            print(f"[scoring] {exc}")
        leaderboard_dicts = None

    # ---- Reports -------------------------------------------------------------
    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = results_dir / f"benchmark_{ts}.json"
    md_path = results_dir / f"benchmark_{ts}.md"

    write_json(results, json_path, leaderboard=leaderboard_dicts)
    print(f"\nJSON  -> {json_path}")

    if rcfg.generate_markdown:
        write_markdown(results, md_path, leaderboard_entries=leaderboard_entries)
        print(f"Markdown -> {md_path}")

    # Proposal 3: comparison reports
    if args.compare:
        from bench.comparison import write_comparison_markdown
        cmp_path = results_dir / f"comparison_{ts}.md"
        write_comparison_markdown(results, cmp_path)
        print(f"Comparison -> {cmp_path}")

    if args.compare_game_html:
        from bench.comparison import write_game_comparison_html
        game_cmp_path = results_dir / f"game_comparison_{ts}.html"
        write_game_comparison_html(results, artifacts_dir, game_cmp_path)
        print(f"Game comparison -> {game_cmp_path}")

    if rcfg.print_summary:
        print_console_summary(results, leaderboard_entries=leaderboard_entries)

    return 0


if __name__ == "__main__":
    sys.exit(main())
