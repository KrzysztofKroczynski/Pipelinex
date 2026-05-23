"""Tests for PipelineRunner utility methods — no LLM calls required."""
import pytest
from unittest.mock import MagicMock

from pipelinex.runner import PipelineRunner


def _make_runner(global_self_reflection: bool = False) -> PipelineRunner:
    runner = PipelineRunner.__new__(PipelineRunner)
    runner.config = {"self_reflection": global_self_reflection}
    runner.model_override = None
    return runner


class TestExtractNext:
    def test_fenced_json_block(self):
        r = _make_runner()
        assert r._extract_next('```json\n{"next": "step-02", "reason": "done"}\n```') == "step-02"

    def test_fenced_block_without_language_tag(self):
        r = _make_runner()
        assert r._extract_next('```\n{"next": "step-04"}\n```') == "step-04"

    def test_inline_json_object(self):
        r = _make_runner()
        assert r._extract_next('Some text {"next": "step-03"} more text') == "step-03"

    def test_returns_none_on_no_match(self):
        r = _make_runner()
        assert r._extract_next("No routing here.") is None

    def test_returns_none_on_empty_string(self):
        r = _make_runner()
        assert r._extract_next("") is None

    def test_returns_none_on_none_input(self):
        r = _make_runner()
        assert r._extract_next(None) is None

    def test_prefers_fenced_block_over_inline(self):
        r = _make_runner()
        text = '```json\n{"next": "step-fenced"}\n```\n{"next": "step-inline"}'
        assert r._extract_next(text) == "step-fenced"


class TestBuildAssistantMsg:
    def test_no_tool_calls_omits_key(self):
        r = _make_runner()
        msg = r._build_assistant_msg("Hello", [])
        assert msg["role"] == "assistant"
        assert msg["content"] == "Hello"
        assert "tool_calls" not in msg

    def test_with_tool_calls_included(self):
        r = _make_runner()
        tcs = [{"id": "c1", "name": "read_file", "args": {"path": "foo.txt"}}]
        msg = r._build_assistant_msg("", tcs)
        assert "tool_calls" in msg
        assert msg["tool_calls"][0]["function"]["name"] == "read_file"
        assert msg["tool_calls"][0]["id"] == "c1"
        assert msg["tool_calls"][0]["type"] == "function"

    def test_tool_args_serialized_to_json_string(self):
        r = _make_runner()
        tcs = [{"id": "c2", "name": "write_state", "args": {"key": "x", "value": 1}}]
        msg = r._build_assistant_msg("", tcs)
        import json
        args = json.loads(msg["tool_calls"][0]["function"]["arguments"])
        assert args == {"key": "x", "value": 1}

    def test_none_text_becomes_empty_string(self):
        r = _make_runner()
        msg = r._build_assistant_msg(None, [])
        assert msg["content"] == ""


class TestApplyModelOverride:
    def test_name_only_updates_name(self):
        r = _make_runner()
        base = {"provider": "anthropic", "name": "claude-haiku-4-5-20251001"}
        result = r._apply_model_override("claude-sonnet-4-6", base)
        assert result["name"] == "claude-sonnet-4-6"
        assert result["provider"] == "anthropic"

    def test_provider_slash_name_updates_both(self):
        r = _make_runner()
        base = {"provider": "anthropic", "name": "old-model"}
        result = r._apply_model_override("openai/gpt-4o", base)
        assert result["provider"] == "openai"
        assert result["name"] == "gpt-4o"

    def test_does_not_mutate_base_dict(self):
        r = _make_runner()
        base = {"provider": "anthropic", "name": "claude-sonnet-4-6"}
        r._apply_model_override("new-model", base)
        assert base["name"] == "claude-sonnet-4-6"

    def test_preserves_extra_fields(self):
        r = _make_runner()
        base = {"provider": "anthropic", "name": "old", "temperature": 0.5}
        result = r._apply_model_override("new", base)
        assert result["temperature"] == 0.5


class TestSelfReflectionEnabled:
    def test_disabled_by_default(self):
        r = _make_runner(global_self_reflection=False)
        assert r._self_reflection_enabled({}) is False

    def test_global_enable(self):
        r = _make_runner(global_self_reflection=True)
        assert r._self_reflection_enabled({}) is True

    def test_step_override_disables_when_global_on(self):
        r = _make_runner(global_self_reflection=True)
        assert r._self_reflection_enabled({"self_reflection": False}) is False

    def test_step_override_enables_when_global_off(self):
        r = _make_runner(global_self_reflection=False)
        assert r._self_reflection_enabled({"self_reflection": True}) is True
