"""LLM client for the chatbot: Featherless (OpenAI-compatible API).

Put your key in the repo-root .env (gitignored, never commit it):

    FEATHERLESS_API_KEY=...
    # optional
    FEATHERLESS_MODEL=deepseek-ai/DeepSeek-V4-Flash

If FEATHERLESS_API_KEY isn't set but OPENAI_API_KEY is, OpenAI is used
instead (model from OPENAI_MODEL).

JUNCTION_CHAT_MODEL overrides the model for whichever provider is picked,
which is what you want when OPENAI_BASE_URL points at a non-OpenAI host.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import httpx
from openai import OpenAI

# The .env lives at the repo root; backend/.env is also accepted.
_ROOT = Path(__file__).resolve().parents[3]
ENV_FILES = (_ROOT / ".env", _ROOT / "backend" / ".env")


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv comes with fastapi[standard]
        return
    for env_file in ENV_FILES:
        if env_file.is_file():
            load_dotenv(env_file, override=True)

FEATHERLESS_URL = "https://api.featherless.ai/v1"
# Featherless lists tool_use support for this model. The chat also works with
# models without tool support (see chat.py), just with less detail.
DEFAULT_FEATHERLESS_MODEL = "deepseek-ai/DeepSeek-V4-Flash"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


def _model(default: str, *env_names: str) -> str:
    """First non-empty env var wins, else `default`."""
    for name in env_names:
        if value := os.environ.get(name, "").strip():
            return value
    return default


def _http_client() -> httpx.Client:
    """HTTP client that only uses IPv4.

    api.featherless.ai resolves to IPv6 first. On networks that advertise an
    IPv6 default route but silently drop the traffic, every request stalls for
    tens of seconds before falling back to IPv4 — which looks like a hung chat.
    Binding the local address to 0.0.0.0 forces AF_INET. Set
    JUNCTION_FORCE_IPV4=0 to turn this off.
    """
    if os.environ.get("JUNCTION_FORCE_IPV4", "1").strip().lower() in {"0", "false", "no"}:
        return httpx.Client(timeout=90)
    return httpx.Client(transport=httpx.HTTPTransport(local_address="0.0.0.0"), timeout=90)


@dataclass(frozen=True)
class LLM:
    client: OpenAI
    model: str
    provider: str


@lru_cache(maxsize=1)
def get_llm() -> LLM:
    # Re-read .env on every call until a key is found (failures aren't
    # cached), so adding the key works without restarting the backend.
    _load_env()
    if key := os.environ.get("FEATHERLESS_API_KEY"):
        return LLM(
            OpenAI(base_url=FEATHERLESS_URL, api_key=key, timeout=90, http_client=_http_client()),
            _model(DEFAULT_FEATHERLESS_MODEL, "JUNCTION_CHAT_MODEL", "FEATHERLESS_MODEL"),
            "featherless",
        )
    if key := os.environ.get("OPENAI_API_KEY"):
        return LLM(
            OpenAI(api_key=key, timeout=90, http_client=_http_client()),
            _model(DEFAULT_OPENAI_MODEL, "JUNCTION_CHAT_MODEL", "OPENAI_MODEL"),
            "openai",
        )
    raise RuntimeError(
        "No LLM API key. Add FEATHERLESS_API_KEY=... to .env (no restart needed)."
    )


if __name__ == "__main__":
    # Quick check that the key and model work:
    #   uv run python -m junction26.featherless
    llm = get_llm()
    response = llm.client.chat.completions.create(
        model=llm.model,
        max_tokens=200,
        messages=[{"role": "user", "content": "Say hello in one short sentence."}],
    )
    print(f"{llm.provider} / {llm.model}: {response.choices[0].message.content}")
