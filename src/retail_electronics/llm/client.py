"""OpenAI wrapper with per-step model selection."""

from __future__ import annotations

import json
import logging
import re

from openai import OpenAI

from retail_electronics.config import OPENAI_API_KEY, OPENAI_BASE_URL

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "OPEN_API_KEY is not set — cannot call OpenAI."
            )
        _client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    return _client


# ── Chat completions ─────────────────────────────────────────────────

def chat(
    prompt: str,
    *,
    model: str,
    system: str | None = None,
    temperature: float = 0,
    response_format: dict | None = None,
) -> str:
    """Send a chat completion request and return the assistant message."""
    client = _get_client()
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict = {
        "model": model,
        "messages": messages,
    }

    # o4-mini and other reasoning models don't support temperature or
    # response_format with json_object — handle gracefully
    is_reasoning = model.startswith("o")
    if not is_reasoning:
        kwargs["temperature"] = temperature
        if response_format:
            kwargs["response_format"] = response_format

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


def chat_json(
    prompt: str,
    *,
    model: str,
    system: str | None = None,
    temperature: float = 0.2,
) -> dict:
    """Chat completion that parses the response as JSON."""
    is_reasoning = model.startswith("o")
    fmt = None if is_reasoning else {"type": "json_object"}
    raw = chat(
        prompt,
        model=model,
        system=system,
        temperature=temperature,
        response_format=fmt,
    )
    # Strip markdown fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)
