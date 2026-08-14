"""Call OpenAI-compatible chat-completions endpoints and collect metrics."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any

from .config import ModelConfig, PromptSpec


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class SingleResult:
    """Metrics for one prompt × model × repetition."""
    model_key: str
    model_name: str
    provider: str
    prompt_id: str
    prompt_title: str
    category: str
    difficulty: str
    repeat_index: int

    # Timing (seconds)
    ttfb: float = 0.0          # time to first byte / first chunk
    total_time: float = 0.0    # wall-clock for the full response

    # Token accounting
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Throughput
    tokens_per_second: float = 0.0

    # Cost estimate (USD)
    cost_usd: float = 0.0

    # Raw output
    response_text: str = ""
    finish_reason: str = ""

    # Error handling
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

def _build_messages(prompt: PromptSpec) -> list[dict[str, str]]:
    msgs: list[dict[str, str]] = []
    if prompt.system:
        msgs.append({"role": "system", "content": prompt.system})
    msgs.append({"role": "user", "content": prompt.user})
    return msgs


def _estimate_cost(model: ModelConfig, prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens / 1_000_000) * model.price_in + \
           (completion_tokens / 1_000_000) * model.price_out


def execute_once(
    model: ModelConfig,
    prompt: PromptSpec,
    timeout: float = 120.0,
) -> SingleResult:
    """Send one request to the model endpoint and return a SingleResult."""

    result = SingleResult(
        model_key=model.key,
        model_name=model.model,
        provider=model.provider,
        prompt_id=prompt.id,
        prompt_title=prompt.title,
        category=prompt.category,
        difficulty=prompt.difficulty,
        repeat_index=0,
    )

    url = f"{model.base_url.rstrip('/')}/chat/completions"
    max_tok = prompt.max_tokens if prompt.max_tokens is not None else model.max_tokens
    temp = prompt.temperature if prompt.temperature is not None else 0.0

    payload: dict[str, Any] = {
        "model": model.model,
        "messages": _build_messages(prompt),
        "max_tokens": max_tok,
        "temperature": temp,
        "stream": False,
    }

    headers = {
        "Content-Type": "application/json",
    }
    api_key = model.api_key
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    # Anthropic-style header (harmless on other servers)
    if "anthropic" in model.base_url.lower():
        headers["anthropic-version"] = "2023-06-01"

    body = json.dumps(payload).encode()

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        start = time.perf_counter()
        resp = urllib.request.urlopen(req, timeout=timeout)
        raw = resp.read()
        elapsed = time.perf_counter() - start

        data = json.loads(raw)
        result.response_text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        result.finish_reason = (
            data.get("choices", [{}])[0].get("finish_reason", "")
        )

        usage = data.get("usage", {})
        result.prompt_tokens = usage.get("prompt_tokens", 0)
        result.completion_tokens = usage.get("completion_tokens", 0)
        result.total_tokens = usage.get("total_tokens", 0)

        result.total_time = elapsed
        if result.completion_tokens > 0 and elapsed > 0:
            result.tokens_per_second = result.completion_tokens / elapsed

        result.cost_usd = _estimate_cost(
            model, result.prompt_tokens, result.completion_tokens
        )

    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode(errors="replace")[:500]
        result.error = f"HTTP {exc.code}: {err_body}"
    except Exception as exc:  # noqa: BLE001
        result.error = f"{type(exc).__name__}: {exc}"

    return result
