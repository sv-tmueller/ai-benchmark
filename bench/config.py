"""Load and parse TOML configuration and prompt files."""

from __future__ import annotations

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # pip install tomli (older Python)
    except ModuleNotFoundError:
        raise ImportError(
            "This project requires Python 3.11+ (built-in tomllib) "
            "or the 'tomli' package: pip install tomli"
        )
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ModelConfig:
    """One entry from models.toml."""
    key: str               # registry key, e.g. "openai_gpt4o"
    provider: str
    base_url: str
    api_key_env: str
    model: str
    price_in: float = 0.0   # USD per 1M input tokens
    price_out: float = 0.0  # USD per 1M output tokens
    max_tokens: int = 1024

    @property
    def api_key(self) -> str | None:
        """Resolve the API key from the environment."""
        import os
        return os.environ.get(self.api_key_env)


@dataclass
class PromptSpec:
    """One parsed prompt TOML file."""
    id: str
    title: str
    category: str
    difficulty: str
    system: str | None
    user: str
    max_tokens: int | None = None
    temperature: float | None = None
    file_path: Path = field(default_factory=lambda: Path(""))


@dataclass
class RunnerConfig:
    """Parsed config.toml [runner] + [reporting] sections."""
    repeats: int = 1
    cooldown_seconds: float = 0.0
    request_timeout: float = 120.0
    results_dir: str = "results"
    generate_markdown: bool = True
    print_summary: bool = True


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_models(path: Path) -> dict[str, ModelConfig]:
    """Parse models.toml and return a {key: ModelConfig} dict."""
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    models_section = data.get("models", {})
    result: dict[str, ModelConfig] = {}
    for key, val in models_section.items():
        result[key] = ModelConfig(
            key=key,
            provider=val["provider"],
            base_url=val["base_url"],
            api_key_env=val["api_key_env"],
            model=val["model"],
            price_in=float(val.get("price_in", 0)),
            price_out=float(val.get("price_out", 0)),
            max_tokens=int(val.get("max_tokens", 1024)),
        )
    return result


def load_prompt(path: Path) -> PromptSpec:
    """Parse a single prompt TOML file."""
    with open(path, "rb") as fh:
        data: dict[str, Any] = tomllib.load(fh)

    sys_block = data.get("system")
    system_text = sys_block["text"] if isinstance(sys_block, dict) else None

    user_block = data["user"]
    user_text = user_block["text"] if isinstance(user_block, dict) else user_block

    return PromptSpec(
        id=data["id"],
        title=data.get("title", data["id"]),
        category=data.get("category", "uncategorized"),
        difficulty=data.get("difficulty", "unknown"),
        system=system_text,
        user=user_text.strip(),
        max_tokens=data.get("max_tokens"),
        temperature=data.get("temperature"),
        file_path=path,
    )


def load_prompts(directory: Path) -> list[PromptSpec]:
    """Load every *.toml file from the prompts/ directory."""
    prompts: list[PromptSpec] = []
    for path in sorted(directory.glob("*.toml")):
        prompts.append(load_prompt(path))
    return prompts


def load_runner_config(path: Path) -> RunnerConfig:
    """Parse config.toml (falls back to defaults if file is absent)."""
    cfg = RunnerConfig()
    if not path.exists():
        return cfg
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    runner = data.get("runner", {})
    reporting = data.get("reporting", {})
    cfg.repeats = int(runner.get("repeats", cfg.repeats))
    cfg.cooldown_seconds = float(runner.get("cooldown_seconds", cfg.cooldown_seconds))
    cfg.request_timeout = float(runner.get("request_timeout", cfg.request_timeout))
    cfg.results_dir = str(runner.get("results_dir", cfg.results_dir))
    cfg.generate_markdown = bool(reporting.get("generate_markdown", cfg.generate_markdown))
    cfg.print_summary = bool(reporting.get("print_summary", cfg.print_summary))
    return cfg
