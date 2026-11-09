# Benchmark scorecard — per-model × per-category pass rate

**Generated:** 2026-11-09T21:03:54Z · **Models:** 6 · **Categories:** 11 · **Sources:** committed verdict sidecars (`*_grading.json`) and legacy `.meta.json` grading fields

## Method

Pass rates are computed retroactively from committed evidence only — the verdict sidecars and legacy meta grading fields that already sit next to each result; this harness never generates new model output. Every prompt keeps its one-shot, no-execution-feedback policy. A cell shows passed/graded verdicts for one model and one prompt category, so its denominator counts only the results that were actually graded. A model appears as a row only when it has at least one verdict. An em dash (—) marks a model/category with no graded verdict; it is an absence, not a zero. Prompts the harness cannot grade are listed below and are excluded from every numerator and denominator.

## Results

| model | app-generation | coding | creative-writing | domain-probe | game-generation | instruction-following | math | reasoning | servicenow | summarization | vision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude_fable_5_1 | — | — | — | — | 1/1 | — | — | — | — | — | — |
| claude_haiku_5_5 | — | — | — | — | 0/1 | — | — | — | — | — | — |
| claude_haiku_5_5-v2 | — | — | — | — | 0/1 | — | — | — | — | — | — |
| glm_5_2 | — | — | — | — | 2/5 | — | — | — | — | — | — |
| glm_5_3_flash | — | 2/2 | — | 1/1 | 2/7 | — | 2/2 | — | — | — | 1/1 |
| gpt_oss_120b | 0/1 | — | — | — | 0/9 | — | — | — | — | — | — |

## Not graded by this harness

- `creative-product-description`
- `instruction-email-reply`
- `param-translate`
- `probe-callback-pyramid`
- `probe-constrained-scheduling`
- `probe-find-the-bug`
- `probe-nonexistent-api`
- `probe-push-back`
- `probe-timing-safe-token`
- `reasoning-logic-puzzle`
- `servicenow-loaner-request`
- `summarize-article`
