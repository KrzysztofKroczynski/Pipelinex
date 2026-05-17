import json
import re
from typing import Any


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


def _fmt(value: Any) -> str:
    if isinstance(value, str):
        return value
    return f"```json\n{json.dumps(value, indent=2, default=str)}\n```"


def build_context_prompt(
    state: dict,
    skill_md: str,
    handoff: str | None,
    model_cfg: dict | None = None,
) -> str:
    context_section = _extract_context_section(skill_md)
    parts = []

    if handoff:
        parts.append(f"## Handoff from previous step\n\n{handoff}")

    meta_keys = {"_meta", "handoff", "_input_consumed"}
    state_data = {k: v for k, v in state.items() if k not in meta_keys}

    if state_data:
        keys = list(state_data.keys())

        if context_section and model_cfg and keys:
            tiers = _classify_tiers(context_section, keys, model_cfg)
        else:
            tiers = {k: "include" for k in keys}

        state_parts = []
        for key, value in state_data.items():
            tier = tiers.get(key, "include")
            if tier == "skip":
                continue
            tag = " [ESSENTIAL]" if tier == "essential" else ""
            state_parts.append(f"### {key}{tag}\n{_fmt(value)}")

        if state_parts:
            parts.append("## Pipeline State\n\n" + "\n\n".join(state_parts))

    return "\n\n".join(parts)
