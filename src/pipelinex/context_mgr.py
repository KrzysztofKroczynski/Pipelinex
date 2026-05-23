import json
import re
from typing import Any


class ContextBudgetExceeded(Exception):
    pass


def _extract_context_section(skill_md: str) -> str:
    m = re.search(r'##\s+Context\s*\n(.*?)(?=\n##|\Z)', skill_md, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _classify_tiers(context_section: str, keys: list[str], model_cfg: dict) -> dict[str, str]:
    from .model import call_llm, extract_text

    prompt = (
        f"A pipeline step has this context guidance:\n\n{context_section}\n\n"
        f"Available state keys: {keys}\n\n"
        "Classify each key as:\n"
        "- 'essential': explicitly needed in full\n"
        "- 'skip': explicitly not needed\n"
        "- 'include': everything else\n\n"
        "Reply with JSON only: {\"key\": \"essential|include|skip\", ...}"
    )

    try:
        resp = call_llm(model_cfg, [{"role": "user", "content": prompt}], max_tokens=256)
        text = extract_text(resp)
        m = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if m:
            result = json.loads(m.group())
            valid = {"essential", "include", "skip"}
            return {k: (v if v in valid else "include") for k, v in result.items()}
    except Exception:
        pass

    return {k: "include" for k in keys}


def _count_tokens(text: str, model_cfg: dict | None = None) -> int:
    if model_cfg:
        try:
            import litellm
            provider = model_cfg.get("provider", "")
            name = model_cfg.get("name", "")
            if provider == "anthropic":
                model = f"anthropic/{name}"
            elif provider == "openai":
                model = name
            elif provider in ("ollama", "groq", "bedrock"):
                model = f"{provider}/{name}"
            else:
                model = f"{provider}/{name}"
            return litellm.token_counter(model=model, text=text)
        except Exception:
            pass
    # Fallback: rough estimate (4 chars ≈ 1 token)
    return max(1, len(text) // 4)


def _summarize_content(key: str, value: Any, model_cfg: dict) -> str:
    from .model import call_llm, extract_text

    raw = _fmt(value) if not isinstance(value, str) else value
    prompt = (
        f"Summarize the following pipeline state value (key: '{key}') concisely. "
        "Preserve all important facts, numbers, decisions, and structure. "
        "Target: under 120 words.\n\n"
        f"{raw}"
    )
    try:
        resp = call_llm(model_cfg, [{"role": "user", "content": prompt}], max_tokens=200)
        return extract_text(resp).strip()
    except Exception:
        return raw[:500] + "\n... [truncated — summarization failed]"


def _fmt(value: Any) -> str:
    if isinstance(value, str):
        return value
    return f"```json\n{json.dumps(value, indent=2, default=str)}\n```"


def build_context_prompt(
    state: dict,
    skill_md: str,
    handoff: str | None,
    model_cfg: dict | None = None,
    token_budget: int | None = None,
) -> str:
    context_section = _extract_context_section(skill_md)

    handoff_part = f"## Handoff from previous step\n\n{handoff}" if handoff else None

    meta_keys = {"_meta", "handoff", "_input_consumed"}
    state_data = {k: v for k, v in state.items() if k not in meta_keys}

    essential_rendered: list[str] = []
    include_items: list[tuple[str, Any]] = []

    if state_data:
        keys = list(state_data.keys())

        if context_section and model_cfg and keys:
            tiers = _classify_tiers(context_section, keys, model_cfg)
        else:
            tiers = {k: "include" for k in keys}

        for key, value in state_data.items():
            tier = tiers.get(key, "include")
            if tier == "skip":
                continue
            if tier == "essential":
                essential_rendered.append(f"### {key} [ESSENTIAL]\n{_fmt(value)}")
            else:
                include_items.append((key, value))

    def _assemble(inc_rendered: list[str]) -> str:
        parts = []
        if handoff_part:
            parts.append(handoff_part)
        state_parts = essential_rendered + inc_rendered
        if state_parts:
            parts.append("## Pipeline State\n\n" + "\n\n".join(state_parts))
        return "\n\n".join(parts)

    result = _assemble([f"### {k}\n{_fmt(v)}" for k, v in include_items])

    if token_budget is None or model_cfg is None:
        return result

    used = _count_tokens(result, model_cfg)
    if used <= token_budget:
        return result

    # Over budget — summarize include items
    if not include_items:
        raise ContextBudgetExceeded(
            f"Essential context alone exceeds token budget "
            f"({used} > {token_budget} tokens). "
            "Mark more state keys as skip, or increase context_budget_tokens."
        )

    summarized_inc = [
        f"### {key} [SUMMARIZED]\n{_summarize_content(key, value, model_cfg)}"
        for key, value in include_items
    ]
    result = _assemble(summarized_inc)

    used = _count_tokens(result, model_cfg)
    if used > token_budget:
        raise ContextBudgetExceeded(
            f"Context still exceeds token budget after summarizing include items "
            f"({used} > {token_budget} tokens). "
            "Increase context_budget_tokens or mark more keys as skip."
        )

    return result
