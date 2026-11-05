"""The call to Claude Haiku 5.5, its time and its cost (the AI layer's spec,
`docs/PICWISE_AI_LAYER_SPEC.md`, 4.3, 4.6 and 4.7).

The Anthropic SDK is imported only by `make_client`, so the site and the tests never
need it: the measure and the service that calls the API install it in an environment of
their own, pinned with every package's hash. The key is read from `ANTHROPIC_API_KEY` by
the SDK and never written anywhere.

A failure of any kind (a refusal, an answer cut short, no answer within the time, an
error of the API or the network) is an answer with nothing to show: the page stays as it
is (the spec, 4.3).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

# Anthropic's prices per million tokens for Claude Haiku 5.5, prompts up to 100,000
# tokens (the pricing page, read on 2026-11-05): read, written, a 5-minute cache write,
# a cache read. A prompt over 100,000 tokens costs more; this layer never sends one.
PRICES_PER_MILLION = {
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_write": 0.125, "cache_read": 0.01},
}
# No answer within this many seconds: nothing is shown (the spec, 4.3).
TIMEOUT_SECONDS = 8.0
# One retry, for a passing error of the network or an overloaded API.
MAX_RETRIES = 1


@dataclass(frozen=True)
class Asked:
    """One call: the structured answer (None when there is none), why the model stopped,
    the tokens and their cost, the time, and the error ("" when there was none)."""

    answer: dict[str, Any] | None
    stop_reason: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    cost_usd: float
    seconds: float
    error: str


def make_client(*, timeout: float = TIMEOUT_SECONDS, max_retries: int = MAX_RETRIES) -> Any:
    """The SDK's client, the key taken from `ANTHROPIC_API_KEY` by the SDK itself."""
    import anthropic  # only here: the site never needs it

    return anthropic.Anthropic(timeout=timeout, max_retries=max_retries)


def cost_usd(model: str, usage: dict[str, Any]) -> float:
    """What one call cost, from the tokens the API counted."""
    prices = PRICES_PER_MILLION.get(model) or PRICES_PER_MILLION["claude-haiku-5-5"]
    tokens = {
        "input": int(usage.get("input_tokens") or 0),
        "output": int(usage.get("output_tokens") or 0),
        "cache_write": int(usage.get("cache_creation_input_tokens") or 0),
        "cache_read": int(usage.get("cache_read_input_tokens") or 0),
    }
    return sum(tokens[name] * prices[name] for name in tokens) / 1_000_000


def _as_dict(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    for method in ("to_dict", "model_dump"):
        convert = getattr(response, method, None)
        if callable(convert):
            return convert()
    raise TypeError(f"an answer of an unknown kind: {type(response).__name__}")


def _error_name(error: BaseException) -> str:
    status = getattr(error, "status_code", None)
    return f"{type(error).__name__}" + (f" (HTTP {status})" if status else "")


def ask(request: dict[str, Any], *, client: Any) -> Asked:
    """Send one request (`request.request_kwargs`) and read its answer."""
    model = str(request.get("model") or "")
    began = time.monotonic()
    try:
        response = _as_dict(client.messages.create(**request))
    except Exception as error:  # nothing is shown; the caller records why
        return Asked(None, "", "", 0, 0, 0, 0, 0.0, time.monotonic() - began, _error_name(error))
    seconds = time.monotonic() - began
    usage = dict(response.get("usage") or {})
    answered_model = str(response.get("model") or model)
    text = "".join(
        str(block.get("text") or "")
        for block in response.get("content") or ()
        if isinstance(block, dict) and block.get("type") == "text"
    )
    stop_reason = str(response.get("stop_reason") or "")
    answer: dict[str, Any] | None = None
    error = ""
    if text.strip():
        try:
            parsed = json.loads(text)
        except ValueError:
            error = "an answer that is not JSON"
        else:
            if isinstance(parsed, dict):
                answer = parsed
            else:
                error = "an answer that is not a JSON object"
    elif stop_reason != "refusal":
        error = "an answer with no text"
    return Asked(
        answer=answer,
        stop_reason=stop_reason,
        model=answered_model,
        input_tokens=int(usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
        cache_write_tokens=int(usage.get("cache_creation_input_tokens") or 0),
        cache_read_tokens=int(usage.get("cache_read_input_tokens") or 0),
        cost_usd=cost_usd(answered_model, usage),
        seconds=seconds,
        error=error,
    )
