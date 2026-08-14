# AI Benchmark

![CI](https://github.com/sv-tmueller/ai-benchmark/actions/workflows/ci.yml/badge.svg)

A lightweight framework for benchmarking AI models against curated prompts.
Send the same prompt to multiple models, measure latency / throughput /
token usage / estimated cost, grade responses, and rank models with a
weighted composite score.

Designed for anyone who wants to cut through marketing claims and see how
models actually behave on tasks that matter to them.

## Features

- **6 models** preconfigured: Kimi K3, GLM 5.2, ChatGPT 5.6, Claude Opus 5, Claude Fable, Claude Sonnet 5
- **16 prompts** across 8 categories: coding, reasoning, math, summarization, creative-writing, instruction-following, game-generation, vision
- **Automated grading** (Proposal 1): exact, regex, contains, or judge-model modes
- **SSE streaming** (Proposal 2): true time-to-first-token (TTFB) measurement
- **Side-by-side comparison** (Proposal 3): Markdown diff view + HTML game artifact tab viewer
- **Historical trend tracking** (Proposal 4): `analyze.py` generates SVG dashboards from accumulated results
- **Vision prompts** (Proposal 5): image inputs for multi-modal models, with `supports_vision` flag
- **Prompt parameterization** (Proposal 6): `{{variable}}` placeholders filled from `.fixtures.toml` files
- **Weighted scoring leaderboard** (Proposal 7): composite score blending speed, cost, and quality
- Zero external dependencies (Python 3.11+ stdlib only)

---

## Quick start

```bash
# 1. Install Python 3.11+
python3 --version   # needs >= 3.11 (uses tomllib)

# 2. Set at least one API key
export OPENAI_API_KEY="sk-..."
# export GROQ_API_KEY="..."
# export ANTHROPIC_API_KEY="..."

# 3. Create your local config (optional — sensible defaults exist)
cp config.example.toml config.toml

# 4. Dry run to see what would happen
python run.py --model openai_gpt4o_mini --dry-run

# 5. Run the benchmark
python run.py --model openai_gpt4o_mini

# 6. Compare multiple models
python run.py --model openai_gpt4o_mini --model groq_llama70b --model deepseek_chat
```

Results appear in `results/` as both JSON (machine-parseable) and Markdown
(human-readable).

---

## Repository structure

```
ai-benchmark/
├── run.py                  # CLI entry point — run this
├── analyze.py              # Historical trend tracking dashboard (Proposal 4)
├── config.example.toml     # Copy to config.toml for local overrides
├── models.toml             # Model registry: endpoints, pricing, vision flags
├── prompts/                # One TOML file per benchmark prompt
│   ├── summarize-article.toml
│   ├── code-flatten-list.toml
│   ├── reasoning-seating-puzzle.toml
│   ├── creative-water-bottle.toml
│   ├── math-second-derivative.toml
│   ├── math-addition.toml           # graded prompt (Proposal 1)
│   ├── sql-country-analytics.toml
│   ├── instruction-decline-meeting.toml
│   ├── game-snake.toml
│   ├── game-breakout.toml
│   ├── game-angry-birds.toml
│   ├── vision-shape-count.toml      # vision prompt (Proposal 5)
│   ├── param-translate.toml         # parameterized (Proposal 6)
│   ├── param-translate.fixtures.toml
│   └── assets/                      # image assets for vision prompts
│       └── shapes.png
├── bench/                  # Python package (the engine)
│   ├── __init__.py
│   ├── config.py           # Loads TOML files into dataclasses
│   ├── executor.py         # Sends requests, collects metrics (+ vision support)
│   ├── streaming_executor.py  # SSE streaming with TTFB (Proposal 2)
│   ├── reporting.py        # Generates JSON + Markdown reports (+ grades + leaderboard)
│   ├── grader.py            # Automated response grading (Proposal 1)
│   ├── comparison.py        # Side-by-side diff + HTML game viewer (Proposal 3)
│   ├── vision.py            # Image encoding for multi-modal prompts (Proposal 5)
│   ├── parameterize.py      # Fixture-based prompt expansion (Proposal 6)
│   └── scoring.py           # Weighted composite scoring leaderboard (Proposal 7)
├── results/                # Generated output (gitignored)
└── README.md               # You are here
```

---

## Adding a new model

Edit `models.toml` and add a new block:

```toml
[models.my_custom_model]
provider    = "custom-endpoint"
base_url    = "https://my-server.com/v1"
api_key_env = "MY_API_KEY"
model       = "my-model-v2"
price_in    = 0.50   # USD per 1M input tokens (optional)
price_out   = 2.00   # USD per 1M output tokens (optional)
max_tokens  = 2048
```

Set the environment variable and you're ready:

```bash
export MY_API_KEY="..."
python run.py --model my_custom_model
```

Any OpenAI-compatible `/chat/completions` endpoint works: OpenAI, Azure
OpenAI, vLLM, Ollama (with `OLLAMA_API_KEY=dummy`), Groq, Together,
DeepSeek, Mistral, AI noris DE, local LM Studio, etc.

---

## Adding a new prompt

Create a `.toml` file in `prompts/`:

```toml
id          = "my-new-prompt"
title       = "Short description"
category    = "coding"
difficulty  = "medium"
temperature = 0.0

[system]
text = "System persona or instructions."

[user]
text = '''
Your actual prompt goes here.
Multiple lines are fine.
'''
```

Fields:

| Field         | Required | Description                                           |
|---------------|----------|-------------------------------------------------------|
| `id`          | yes      | Unique slug, used in result files                     |
| `title`       | no       | Human-readable name                                    |
| `category`    | no       | Grouping label (coding, reasoning, math, etc.)        |
| `difficulty`  | no       | `easy`, `medium`, or `hard`                           |
| `temperature` | no       | Sampling temp (default 0.0 for deterministic output) |
| `max_tokens`  | no       | Override the model's default max completion tokens    |
| `save_as`     | no       | File extension to save response as (e.g. `"html"`)   |
| `file_prefix` | no       | Filename prefix for saved artifacts (defaults to id) |
| `system.text` | no       | System prompt                                         |
| `user.text`   | yes      | The user message                                      |

That's it. The runner discovers all `.toml` files in `prompts/` automatically.

---

## Game and browser-testable prompts

Prompts with `save_as = "html"` are special: the runner saves each model's
response as a standalone `.html` file in `results/artifacts/`. You can open
these directly in a browser to play, test, and visually compare the output
of different models.

Two game prompts ship with the repo:

| Prompt file | Game | Difficulty |
|-------------|------|------------|
| `game-snake.toml` | Classic Snake with wrap-around walls | medium |
| `game-breakout.toml` | Brick breaker with levels, lives, particles | hard |
| `game-angry-birds.toml` | Physics-based slingshot with destructible structures | hard |

Running them:

```bash
python run.py --model openai_gpt4o_mini --category game-generation

# Or specifically:
python run.py --model openai_gpt4o_mini --prompt-id game-snake
python run.py --model groq_llama70b --prompt-id game-breakout
```

Artifacts land in `results/artifacts/`:

```
results/artifacts/snake_openai_gpt4o_mini.html
results/artifacts/snake_groq_llama70b.html
results/artifacts/breakout_openai_gpt4o_mini.html
...
```

Open any of them in a browser to play the game the model generated. This is
a powerful qualitative benchmark: you instantly see whether the model produced
working, polished code or something that barely runs.

Tips for game prompts:
- Set `max_tokens` high enough (4096+) so the model doesn't truncate mid-file.
- Use `temperature = 0.2` for consistent-but-varied results.
- The system prompt instructs the model to output raw HTML only (no markdown
  fences). Some models may still wrap output in ```html fences; the saved
  file would need manual cleanup in that case.

---

## Metrics collected

For every prompt × model × repeat, the runner records:

| Metric              | Description                                            |
|---------------------|--------------------------------------------------------|
| `total_time`        | Wall-clock latency for the full response (seconds)     |
| `prompt_tokens`     | Input token count (from API usage object)              |
| `completion_tokens` | Output token count                                     |
| `total_tokens`      | Sum of the above                                       |
| `tokens_per_second` | Completion tokens divided by total time                |
| `cost_usd`          | Estimated cost based on `price_in` / `price_out`       |
| `response_text`     | The full model response (for manual inspection)       |
| `finish_reason`     | Why generation stopped (`stop`, `length`, etc.)       |
| `error`             | Error message if the request failed                    |

---

## CLI reference

```bash
# Flags
--model KEY          Select a model from models.toml (repeatable)
--prompt-id ID       Run only this prompt by id (repeatable)
--category CAT       Filter prompts by category (repeatable)
--difficulty LEVEL   Filter by easy/medium/hard
--repeats N          Override config repeats
--cooldown SECS      Override config cooldown between calls
--dry-run            Show the plan without calling any API
--verbose, -v        Print per-call metrics to console
```

Examples:

```bash
# Only coding prompts, 5 repetitions each
python run.py --model openai_gpt4o --category coding --repeats 5

# Everything against all registered models
python run.py

# Just one specific prompt
python run.py --model groq_llama70b --prompt-id reasoning-logic-puzzle
```

---

## Reading results

After a run, check `results/`:

- **`benchmark_YYYYMMDD_HHMMSS.json`** — structured data for programmatic analysis
- **`benchmark_YYYYMMDD_HHMMSS.md`** — formatted report with:
  - Summary table (all calls at a glance)
  - Per-model aggregates (average latency, average throughput, total cost)
  - Full response text for each call (so you can judge quality manually)

The Markdown report is designed for quick scanning: skim the summary table
for outliers, then jump to individual responses to assess answer quality.

---

## Advanced Features

### Automated Response Grading (Proposal 1)

Add a `[grading]` block to any prompt TOML to auto-score responses:

    [grading]
    mode     = "contains"       # exact | regex | contains | judge
    expected = "42"             # for exact/contains modes
    pattern  = "\\d+"           # for regex mode
    judge_model = "glm_5_2"     # for judge mode
    judge_criteria = "Accuracy, clarity (1-10)"

Grades appear in JSON, Markdown, and console output. Judge mode calls the
specified model to evaluate the response.

### SSE Streaming with TTFB (Proposal 2)

Pass `--stream` to use SSE streaming mode. This measures true time-to-first-token
(TTFB) -- how long before the model starts generating -- alongside total time
and generation-only throughput:

    python run.py --model glm_5_2 --stream

Or enable permanently in `config.toml`:

    [runner]
    stream = true

### Side-by-Side Comparison (Proposal 3)

Generate comparison reports placing model responses adjacent to each other:

    python run.py --model glm_5_2 --model chatgpt_5_6 --compare

For game artifacts, generate an HTML tab viewer:

    python run.py --model glm_5_2 --model chatgpt_5_6 --compare-game-html

### Historical Trend Tracking (Proposal 4)

Analyze accumulated results over time:

    python analyze.py                          # full dashboard
    python analyze.py --metric latency         # one metric
    python analyze.py --model glm_5_2          # one model
    python analyze.py --since 2026-01-01       # date filter
    python analyze.py --output custom.html     # custom output path

Generates a self-contained HTML dashboard with SVG charts (no external deps).
If matplotlib is installed, also exports PNG charts.

### Vision Prompts (Proposal 5)

Prompts with an `[images]` block send image inputs to vision-capable models:

    [images]
    files = ["assets/photo.png"]
    urls  = ["https://example.com/img.jpg"]

Models without `supports_vision = true` in `models.toml` are automatically
skipped for vision prompts.

### Prompt Parameterization (Proposal 6)

Use `{{variable}}` placeholders in prompts, filled from a `.fixtures.toml`
sibling file:

    # prompts/translate.toml
    [user]
    text = "Translate to {{TARGET_LANG}}: {{TEXT}}"

    # prompts/translate.fixtures.toml
    [[cases]]
    description = "English to German"
    vars.TARGET_LANG = "German"
    vars.TEXT = "Hello world"

Each fixture case expands into a separate prompt instance with a unique ID
(`translate__english-to-german`). One template, many test cases.

### Weighted Scoring Leaderboard (Proposal 7)

After each run, a composite score ranks models by speed, cost, and quality:

    score = w_speed * norm(throughput) + w_cost * norm(inverse_cost) + w_quality * norm(grade)

Configure weights in `config.toml`:

    [scoring]
    w_speed   = 0.3
    w_cost    = 0.3
    w_quality = 0.4

Or override per-run:

    python run.py --weights speed=0.2,cost=0.1,quality=0.7

The leaderboard appears in console output, Markdown report, and JSON.

---

## Tips for good benchmarks

1. **Use `temperature=0`** for coding, math, and factual tasks. Use higher
   temps only for creative tasks where variance matters.

2. **Repeat measurements** (`--repeats 3` or more) to smooth out jitter in
   latency and detect inconsistent outputs.

3. **Mix difficulties.** Easy prompts reveal baseline speed; hard prompts
   expose reasoning quality and whether a model gives up early.

4. **Check `finish_reason`.** If it says `length`, the model hit your
   `max_tokens` ceiling — increase it or the comparison is unfair.

5. **Compare apples to apples.** Same `max_tokens`, same `temperature`,
   same prompt wording. Different settings invalidate comparisons.

6. **Eyeball the responses.** Speed and cheapness mean nothing if the
   answer is wrong. The Markdown report puts the full output right there
   for you to read.
