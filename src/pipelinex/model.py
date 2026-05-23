import json
import logging
import os
import threading

os.environ.setdefault("LITELLM_LOG", "ERROR")

# Block LiteLLM startup warnings (botocore/sagemaker) before import fires them
_litellm_logger = logging.getLogger("LiteLLM")
_litellm_logger.setLevel(logging.ERROR)
_litellm_logger.propagate = False

import litellm

litellm.drop_params = True


class _UsageAccumulator:
    def __init__(self):
        self._lock = threading.Lock()
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost_usd = 0.0

    def add(self, prompt: int, completion: int, cost: float):
        with self._lock:
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.cost_usd += cost

    def reset(self):
        with self._lock:
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.cost_usd = 0.0

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.prompt_tokens + self.completion_tokens,
                "cost_usd": round(self.cost_usd, 6),
            }


_usage = _UsageAccumulator()


def get_usage() -> dict:
    return _usage.snapshot()


def reset_usage():
    _usage.reset()


def _model_str(cfg: dict) -> str:
    provider = cfg["provider"]
    name = cfg["name"]
    if provider == "anthropic":
        return f"anthropic/{name}"
    if provider in ("ollama",):
        return f"ollama/{name}"
    if provider == "groq":
        return f"groq/{name}"
    if provider == "bedrock":
        return f"bedrock/{name}"
    if provider == "openai":
        return name
    return f"{provider}/{name}"


def _litellm_kwargs(cfg: dict) -> dict:
    kw = {"model": _model_str(cfg)}
    if "api_key" in cfg:
        kw["api_key"] = cfg["api_key"]
    if "base_url" in cfg:
        kw["base_url"] = cfg["base_url"]
    return kw


def check_tool_support(cfg: dict):
    model = _model_str(cfg)
    try:
        if not litellm.supports_function_calling(model=model):
            raise SystemExit(
                f'ERROR: model "{cfg.get("name", model)}" does not support tool calling.\n'
                f"       Tool calling is required. Use a model that supports it."
            )
    except SystemExit:
        raise
    except Exception:
        pass  # can't verify — let it fail at runtime


def call_llm(cfg: dict, messages: list[dict], tools: list[dict] | None = None, max_tokens: int = 4096):
    kw = _litellm_kwargs(cfg)
    kw["messages"] = messages
    kw["max_tokens"] = max_tokens

    if tools:
        kw["tools"] = [{"type": "function", "function": t} for t in tools]
        kw["tool_choice"] = "auto"

    fallback = cfg.get("fallback")
    try:
        resp = litellm.completion(**kw)
    except Exception:
        if not fallback:
            raise
        fb_kw = _litellm_kwargs(fallback)
        fb_kw["messages"] = messages
        fb_kw["max_tokens"] = max_tokens
        if tools:
            fb_kw["tools"] = kw["tools"]
            fb_kw["tool_choice"] = "auto"
        resp = litellm.completion(**fb_kw)

    try:
        u = resp.usage
        cost = litellm.completion_cost(completion_response=resp)
        _usage.add(
            getattr(u, "prompt_tokens", 0) or 0,
            getattr(u, "completion_tokens", 0) or 0,
            cost or 0.0,
        )
    except Exception:
        pass

    return resp.choices[0].message


def extract_tool_calls(message) -> list[dict]:
    if not getattr(message, "tool_calls", None):
        return []
    calls = []
    for tc in message.tool_calls:
        try:
            args = json.loads(tc.function.arguments)
        except (json.JSONDecodeError, AttributeError):
            args = {}
        calls.append({"id": tc.id, "name": tc.function.name, "args": args})
    return calls


def extract_text(message) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content or ""
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""
