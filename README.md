# AI Benchmark

A lightweight framework for benchmarking AI models against curated prompts.
Send the same prompt to multiple models, measure latency / throughput /
token usage / estimated cost, and eyeball the responses side by side.

Designed for anyone who wants to cut through marketing claims and see how
models actually behave on tasks that matter to them.

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
├── config.example.toml     # Copy to config.toml for local overrides
├── models.toml             # Model registry: endpoints, pricing, limits
├── prompts/                # One TOML file per benchmark prompt
│   ├── summarize-article.toml
│   ├── code-flatten-list.toml
│   ├── reasoning-seating-puzzle.toml
│   ├── creative-water-bottle.toml
│   ├── math-second-derivative.toml
│   ├── sql-country-analytics.toml
│   └── instruction-decline-meeting.toml
├── bench/                  # Python package (the engine)
│   ├── __init__.py
│   ├── config.py           # Loads TOML files into dataclasses
│   ├── executor.py         # Sends requests, collects metrics
│   └── reporting.py        # Generates JSON + Markdown reports
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
| `system.text` | no       | System prompt                                         |
| `user.text`   | yes      | The user message                                      |

That's it. The runner discovers all `.toml` files in `prompts/` automatically.

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
