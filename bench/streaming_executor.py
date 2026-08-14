"""Streaming (SSE) variant of the chat-completions executor.

Connects to an OpenAI-compatible ``/chat/completions`` endpoint with
``stream=true`` and measures time-to-first-token while accumulating the
response incrementally from Server-Sent Events.

Stdlib only — uses :mod:`http.client` for low-level line-oriented reads
and :mod:`urllib.parse` for URL decomposition.
"""

from __future__ import annotations

import json
import time
import http.client
import socket
import ssl
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urlparse

from .config import ModelConfig, PromptSpec


# ---------------------------------------------------------------------------
# Helpers (mirrors executor.py but kept local to avoid coupling)
# ---------------------------------------------------------------------------

def _build_messages(prompt: PromptSpec) -> list[dict[str, str]]:
    """Build the OpenAI-style messages array from a PromptSpec."""
    msgs: list[dict[str, str]] = []
    if prompt.system:
        msgs.append({"role": "system", "content": prompt.system})
    msgs.append({"role": "user", "content": prompt.user})
    return msgs


def _estimate_cost(
    model: ModelConfig, prompt_tokens: int, completion_tokens: int
) -> float:
    return (prompt_tokens / 1_000_000) * model.price_in + \
           (completion_tokens / 1_000_000) * model.price_out


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class StreamedResult:
    """Metrics for one streamed prompt × model × repetition.

    Contains every field from :class:`bench.executor.SingleResult` **plus**
    streaming-specific timing: ``ttft``, ``generation_time``, and a
    ``tokens_per_second`` derived from ``generation_time`` rather than
    ``total_time``.
    """
    # --- identity (same as SingleResult) ---
    model_key: str
    model_name: str
    provider: str
    prompt_id: str
    prompt_title: str
    category: str
    difficulty: str
    repeat_index: int

    # --- timing (seconds) ---
    ttfb: float = 0.0              # time to first byte / first chunk arrival
    total_time: float = 0.0        # wall-clock for the full response

    # --- streaming-specific timing ---
    ttft: float = 0.0              # time to first *token* (first content chunk)
    generation_time: float = 0.0   # total_time − ttft

    # --- token accounting ---
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # --- throughput (computed from generation_time, not total_time) ---
    tokens_per_second: float = 0.0

    # --- cost estimate (USD) ---
    cost_usd: float = 0.0

    # --- raw output ---
    response_text: str = ""
    finish_reason: str = ""

    # --- error handling ---
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Streaming executor
# ---------------------------------------------------------------------------

def execute_streaming(
    model: ModelConfig,
    prompt: PromptSpec,
    timeout: float = 120.0,
) -> StreamedResult:
    """Send one streaming request and return a :class:`StreamedResult`.

    Uses ``http.client`` to establish the connection, sends a POST with
    ``stream=true``, then reads SSE ``data:`` lines incrementally. Measures
    TTFB (connection + headers), TTFT (first content-bearing chunk),
    accumulates content deltas, and extracts usage from the final chunk when
    the server provides it.
    """

    result = StreamedResult(
        model_key=model.key,
        model_name=model.model,
        provider=model.provider,
        prompt_id=prompt.id,
        prompt_title=prompt.title,
        category=prompt.category,
        difficulty=prompt.difficulty,
        repeat_index=0,
    )

    # ---- Build request ---------------------------------------------------

    url = f"{model.base_url.rstrip('/')}/chat/completions"
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    port = parsed.port or (443 if scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    max_tok = (
        prompt.max_tokens
        if prompt.max_tokens is not None
        else model.max_tokens
    )
    temp = prompt.temperature if prompt.temperature is not None else 0.0

    payload: dict[str, Any] = {
        "model": model.model,
        "messages": _build_messages(prompt),
        "max_tokens": max_tok,
        "temperature": temp,
        "stream": True,
    }

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "Connection": "keep-alive",
    }
    api_key = model.api_key
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    # Anthropic-style header (harmless on other servers)
    if "anthropic" in model.base_url.lower():
        headers["anthropic-version"] = "2023-06-01"

    body = json.dumps(payload).encode()

    # ---- Establish connection --------------------------------------------

    if host is None:
        result.error = f"No hostname in URL: {url!r}"
        return result

    conn: http.client.HTTPConnection | None = None
    start = time.perf_counter()
    try:
        if scheme == "https":
            ctx = ssl.create_default_context()
            conn = http.client.HTTPSConnection(
                host, port, timeout=timeout, context=ctx
            )
        elif scheme == "http":
            conn = http.client.HTTPConnection(host, port, timeout=timeout)
        else:
            result.error = f"Unsupported scheme: {scheme!r}"
            return result

        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()

        # TTFB: moment we receive response headers/status line
        ttfb_elapsed = time.perf_counter() - start
        result.ttfb = ttfb_elapsed

        # ---- Validate content-type --------------------------------------
        ctype = resp.headers.get("Content-Type", "")
        if resp.status != 200:
            err_body = resp.read().decode(errors="replace")[:500]
            result.error = f"HTTP {resp.status}: {err_body}"
            result.total_time = time.perf_counter() - start
            return result

        if "event-stream" not in ctype.lower():
            # Non-SSE response — read fully and attempt JSON decode
            raw = resp.read()
            result.total_time = time.perf_counter() - start
            try:
                data = json.loads(raw)
                msg_obj = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                )
                result.response_text = msg_obj.get("content", "") or ""
                result.finish_reason = (
                    data.get("choices", [{}])[0]
                    .get("finish_reason", "")
                    or ""
                )
                usage = data.get("usage", {}) or {}
                result.prompt_tokens = usage.get("prompt_tokens", 0) or 0
                result.completion_tokens = (
                    usage.get("completion_tokens", 0) or 0
                )
                result.total_tokens = usage.get("total_tokens", 0) or 0
            except (json.JSONDecodeError, KeyError, IndexError):
                result.error = (
                    f"Non-SSE response with unexpected Content-Type "
                    f"{ctype!r}; could not parse body"
                )
            finally:
                _finalize_metrics(result, start)
            return result

        # ---- Read SSE stream line by line -------------------------------

        accumulated_parts: list[str] = []
        ttft_recorded = False
        finish_reason = ""
        usage_data: dict[str, Any] = {}

        # http.client.HTTPResponse supports line iteration via fp.readline;
        # iterate manually so we can react to each event promptly.
        while True:
            line_bytes = resp.readline()
            if not line_bytes:
                # Connection closed by server
                break

            line = line_bytes.decode("utf-8", errors="replace").rstrip("\r\n")

            # SSE events are separated by blank lines; skip keep-alives/comments
            if not line:
                continue
            if line.startswith(":"):  # SSE comment / heartbeat
                continue

            # We only care about ``data:`` lines
            if not line.startswith("data:"):
                # Ignore event/id/retry lines for our purposes
                continue

            # Strip the ``data:`` prefix (with optional space)
            data_str = line[len("data:"):].strip()

            # Done sentinel
            if data_str == "[DONE]" or data_str.upper() == "[DONE]":
                break

            # Parse the JSON chunk
            try:
                chunk: dict[str, Any] = json.loads(data_str)
            except json.JSONDecodeError:
                # Malformed chunk — skip but don't abort the stream
                continue

            # Capture usage if the server embeds it in a chunk
            u = chunk.get("usage")
            if isinstance(u, dict) and u:
                usage_data.update(u)

            # Navigate choices[0] defensively
            choices = chunk.get("choices")
            if not choices or not isinstance(choices, list):
                continue
            choice0 = choices[0]
            if not isinstance(choice0, dict):
                continue

            delta = choice0.get("delta")
            if isinstance(delta, dict):
                content_delta = delta.get("content")
                if content_delta:
                    # First content-bearing chunk → record TTFT
                    if not ttft_recorded:
                        result.ttft = time.perf_counter() - start
                        ttft_recorded = True
                    accumulated_parts.append(content_delta)

            fr = choice0.get("finish_reason")
            if fr:
                finish_reason = fr
                # Many servers close the stream right after finish_reason;
                # we can break early but keep reading for trailing usage/DONE.
                # Continue loop to catch any subsequent usage chunk or [DONE].
                # However, some servers send nothing after, so we rely on
                # the eventual empty readline / [DONE] to terminate.

        # ---- Assemble results -------------------------------------------
        result.total_time = time.perf_counter() - start
        result.response_text = "".join(accumulated_parts)
        result.finish_reason = finish_reason or ""

        if usage_data:
            result.prompt_tokens = usage_data.get("prompt_tokens", 0) or 0
            result.completion_tokens = (
                usage_data.get("completion_tokens", 0) or 0
            )
            result.total_tokens = usage_data.get("total_tokens", 0) or 0
        else:
            # Estimate tokens from content length (~4 chars/token heuristic)
            est_completion = len(result.response_text) // 4
            result.completion_tokens = est_completion
            result.total_tokens = result.prompt_tokens + est_completion

        _finalize_metrics(result, start)

    except socket.timeout as exc:
        result.total_time = time.perf_counter() - start
        result.error = f"Timeout: {exc}"
    except http.client.HTTPException as exc:
        result.total_time = time.perf_counter() - start
        result.error = f"HTTPException: {exc}"
    except OSError as exc:
        result.total_time = time.perf_counter() - start
        result.error = f"{type(exc).__name__}: {exc}"
    except Exception as exc:  # noqa: BLE001
        result.total_time = time.perf_counter() - start
        result.error = f"{type(exc).__name__}: {exc}"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass

    return result


# ---------------------------------------------------------------------------
# Post-processing helper
# ---------------------------------------------------------------------------

def _finalize_metrics(result: StreamedResult, start: float) -> None:
    """Compute derived timing/throughput/cost fields on *result*.

    Called once the response is fully consumed (or errored). Ensures
    ``total_time``, ``generation_time``, ``tokens_per_second``, and
    ``cost_usd`` are populated consistently regardless of code path.
    """
    # Ensure total_time reflects the full elapsed wall clock
    # (caller may have already set it; respect that value)
    if result.total_time <= 0.0:
        result.total_time = time.perf_counter() - start

    # generation_time = total_time − ttft (guard against negatives)
    if result.ttft > 0.0 and result.total_time > result.ttft:
        result.generation_time = result.total_time - result.ttft
    else:
        # Either no TTFT recorded or pathological timing; fall back to
        # total_time so division is safe and meaningful.
        result.generation_time = result.total_time

    # tokens_per_second from generation_time (NOT total_time)
    if (
        result.completion_tokens > 0
        and result.generation_time > 0
    ):
        result.tokens_per_second = (
            result.completion_tokens / result.generation_time
        )
    else:
        result.tokens_per_second = 0.0
