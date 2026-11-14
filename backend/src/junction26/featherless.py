"""LLM client for the chatbot: Featherless (OpenAI-compatible API).

Put your key in backend/.env (gitignored, never commit it):

    FEATHERLESS_API_KEY=...
    # optional
    FEATHERLESS_MODEL=deepseek-ai/DeepSeek-V4-Flash

If FEATHERLESS_API_KEY isn't set but OPENAI_API_KEY is, OpenAI is used
instead (model from OPENAI_MODEL).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from openai import OpenAI

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"  # backend/.env


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv comes with fastapi[standard]
        return
    load_dotenv(ENV_FILE, override=True)

FEATHERLESS_URL = "https://api.featherless.ai/v1"
# Featherless lists tool_use support for this model. The chat also works with
# models without tool support (see chat.py), just with less detail.
DEFAULT_FEATHERLESS_MODEL = "deepseek-ai/DeepSeek-V4-Flash"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


@dataclass(frozen=True)
class LLM:
    client: OpenAI
    model: str
    provider: str


@lru_cache(maxsize=1)
def get_llm() -> LLM:
    # Re-read backend/.env on every call until a key is found (failures aren't
    # cached), so adding the key works without restarting the backend.
    _load_env()
    if key := os.environ.get("FEATHERLESS_API_KEY"):
        return LLM(
            OpenAI(base_url=FEATHERLESS_URL, api_key=key, timeout=90),
            os.environ.get("FEATHERLESS_MODEL", DEFAULT_FEATHERLESS_MODEL),
            "featherless",
        )
    if key := os.environ.get("OPENAI_API_KEY"):
        return LLM(
            OpenAI(api_key=key, timeout=90),
            os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            "openai",
        )
    raise RuntimeError(
        "No LLM API key. Add FEATHERLESS_API_KEY=... to backend/.env (no restart needed)."
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
