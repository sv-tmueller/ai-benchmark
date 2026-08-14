#!/usr/bin/env python3
"""
AI Benchmark Runner
====================
Send curated prompts to any OpenAI-compatible model endpoint and collect
latency, throughput, token-count, and cost metrics.

Usage examples
--------------
  # Run all prompts against a single model
  python run.py --model groq_llama70b

  # Run all prompts against multiple models
  python run.py --model groq_llama70b --model openai_gpt4o_mini

  # Run only prompts tagged "coding"
  python run.py --model vllm_local --category coding

  # Dry run: print which combinations would execute, call nothing
  python run.py --dry-run

  # Repeat each combination 3 times with 2 s cooldown
  python run.py --model openai_gpt4o --repeats 3 --cooldown 2
"""

from __future__ import annotations

import argparse
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


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Benchmark prompts against AI models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--model", "-m",
        action="append",
        dest="models",
        metavar="KEY",
        help=(
            "Model registry key from models.toml (repeatable). "
            "If omitted, all registered models are used."
        ),
    )
    ap.add_argument(
        "--prompt-id",
        action="append",
        dest="prompt_ids",
        metavar="ID",
        help="Only run prompts with these IDs (repeatable).",
    )
    ap.add_argument(
        "--category",
        action="append",
        dest="categories",
        metavar="CAT",
        help="Only run prompts in these categories (repeatable).",
    )
    ap.add_argument("--difficulty", help="Filter by difficulty: easy|medium|hard.")
    ap.add_argument("--repeats", type=int, help="Override config repeats.")
    ap.add_argument("--cooldown", type=float, help="Override config cooldown (seconds).")
    ap.add_argument("--dry-run", action="store_true", help="Plan only; do not call any API.")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose logging.")
    return ap.parse_args()


def main() -> int:
    args = parse_args()

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

    # ---- Plan ---------------------------------------------------------------
    total_calls = len(selected_models) * len(selected_prompts) * repeats
    print(f"\nModels ({len(selected_models)}): {[m.key for m in selected_models]}")
    print(f"Prompts ({len(selected_prompts)}): {[p.id for p in selected_prompts]}")
    print(f"Repeats: {repeats}  Cooldown: {cooldown}s  Total API calls: {total_calls}")

    if args.dry_run:
        print("\n[dry-run] No API calls made.\n")
        return 0

    # ---- Execute ------------------------------------------------------------
    results = []
    for mi, model in enumerate(selected_models):
        if not model.api_key and model.api_key_env != "":
            # Many local servers (vLLM, Ollama) accept any dummy key;
            # warn but proceed.
            if args.verbose:
                print(f"[warn] {model.api_key_env} not set for {model.key}; continuing anyway.")

        for pi, prompt in enumerate(selected_prompts):
            for rep in range(repeats):
                idx = mi * len(selected_prompts) * repeats + pi * repeats + rep + 1
                print(f"[{idx}/{total_calls}] {model.key} :: {prompt.id} (rep {rep + 1})", flush=True)

                result = execute_once(model, prompt, timeout=rcfg.request_timeout)
                result.repeat_index = rep
                results.append(result)

                if result.error:
                    print(f"  ERROR: {result.error[:120]}")
                elif args.verbose:
                    print(f"  {result.total_time:.2f}s  "
                          f"in={result.prompt_tokens} out={result.completion_tokens}  "
                          f"{result.tokens_per_second:.1f} tok/s")

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

    # ---- Reports ------------------------------------------------------------
    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = results_dir / f"benchmark_{ts}.json"
    md_path = results_dir / f"benchmark_{ts}.md"

    write_json(results, json_path)
    print(f"\nJSON  -> {json_path}")

    if rcfg.generate_markdown:
        write_markdown(results, md_path)
        print(f"Markdown -> {md_path}")

    if rcfg.print_summary:
        print_console_summary(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
