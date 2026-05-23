"""Tests for context_mgr.py — section extraction, formatting, build_context_prompt."""
from unittest.mock import patch

import pytest

from pipelinex.context_mgr import _extract_context_section, _fmt, build_context_prompt


class TestExtractContextSection:
    def test_extracts_section_content(self):
        md = "# Step\n\nDo this.\n\n## Context\n\nFocus on: foo, bar\n\n## Other\n\nignore"
        result = _extract_context_section(md)
        assert "Focus on" in result
        assert "Other" not in result

    def test_returns_empty_when_section_missing(self):
        assert _extract_context_section("# Step\n\nNo context section") == ""

    def test_case_insensitive_heading(self):
        md = "# Skill\n\n## CONTEXT\n\nImportant stuff\n"
        assert "Important stuff" in _extract_context_section(md)

    def test_extracts_until_end_of_file(self):
        md = "## Context\n\nContent here\n"
        assert "Content here" in _extract_context_section(md)

    def test_extracts_until_next_heading(self):
        md = "## Context\n\nonly this\n\n## Next Section\n\nnot this"
        result = _extract_context_section(md)
        assert "only this" in result
        assert "not this" not in result


class TestFmt:
    def test_string_returned_as_is(self):
        assert _fmt("hello world") == "hello world"

    def test_dict_wrapped_in_json_fence(self):
        result = _fmt({"key": "val"})
        assert "```json" in result
        assert '"key"' in result
        assert '"val"' in result

    def test_list_wrapped_in_json_fence(self):
        result = _fmt([1, 2, 3])
        assert "```json" in result
        assert "1" in result

    def test_number_rendered(self):
        assert "42" in _fmt(42)

    def test_none_rendered(self):
        result = _fmt(None)
        assert "null" in result


class TestBuildContextPrompt:
    def test_includes_handoff_section(self):
        result = build_context_prompt({}, "", "previous done", model_cfg=None)
        assert "Handoff from previous step" in result
        assert "previous done" in result

    def test_no_handoff_section_when_none(self):
        result = build_context_prompt({}, "", None)
        assert "Handoff" not in result

    def test_skips_meta_keys(self):
        state = {
            "_meta": {"current_step": "s1"},
            "handoff": "old",
            "_input_consumed": True,
            "user_data": "keep me",
        }
        result = build_context_prompt(state, "", None)
        assert "_meta" not in result
        assert "_input_consumed" not in result
        assert "user_data" in result

    def test_includes_state_data_section(self):
        state = {"report": "Final text"}
        result = build_context_prompt(state, "", None)
        assert "Pipeline State" in result
        assert "report" in result
        assert "Final text" in result

    def test_empty_state_omits_pipeline_state(self):
        result = build_context_prompt({}, "", None)
        assert "Pipeline State" not in result

    def test_essential_tier_tagged(self):
        state = {"key_a": "value"}
        skill_md = "## Context\n\nFocus on key_a\n"
        with patch("pipelinex.context_mgr._classify_tiers", return_value={"key_a": "essential"}):
            result = build_context_prompt(
                state, skill_md, None, model_cfg={"provider": "a", "name": "b"}
            )
        assert "[ESSENTIAL]" in result

    def test_skip_tier_excludes_key(self):
        state = {"skip_me": "hidden", "keep_me": "visible"}
        skill_md = "## Context\n\nIgnore skip_me\n"
        with patch(
            "pipelinex.context_mgr._classify_tiers",
            return_value={"skip_me": "skip", "keep_me": "include"},
        ):
            result = build_context_prompt(
                state, skill_md, None, model_cfg={"provider": "a", "name": "b"}
            )
        assert "skip_me" not in result
        assert "keep_me" in result

    def test_no_model_cfg_skips_tier_classification(self):
        state = {"x": "y"}
        skill_md = "## Context\n\nFocus on x\n"
        with patch("pipelinex.context_mgr._classify_tiers") as mock_classify:
            build_context_prompt(state, skill_md, None, model_cfg=None)
            mock_classify.assert_not_called()


class TestTokenBudget:
    _model = {"provider": "openai", "name": "gpt-4o"}

    def _big_state(self) -> dict:
        return {
            "essential_key": "short value",
            "big_include": "word " * 600,  # ~150 tokens
        }

    def test_no_budget_returns_full_context(self):
        state = self._big_state()
        tiers = {"essential_key": "essential", "big_include": "include"}
        with patch("pipelinex.context_mgr._classify_tiers", return_value=tiers), \
             patch("pipelinex.context_mgr._count_tokens", return_value=999):
            result = build_context_prompt(
                state, "## Context\nsome guidance\n", None,
                model_cfg=self._model, token_budget=None,
            )
        assert "big_include" in result
        assert "[SUMMARIZED]" not in result

    def test_within_budget_returns_full_context(self):
        state = self._big_state()
        tiers = {"essential_key": "essential", "big_include": "include"}
        with patch("pipelinex.context_mgr._classify_tiers", return_value=tiers), \
             patch("pipelinex.context_mgr._count_tokens", return_value=100):
            result = build_context_prompt(
                state, "## Context\nsome guidance\n", None,
                model_cfg=self._model, token_budget=500,
            )
        assert "[SUMMARIZED]" not in result

    def test_over_budget_summarizes_include_items(self):
        state = self._big_state()
        tiers = {"essential_key": "essential", "big_include": "include"}
        # First call (full) returns over-budget; second call (summarized) returns under
        with patch("pipelinex.context_mgr._classify_tiers", return_value=tiers), \
             patch("pipelinex.context_mgr._count_tokens", side_effect=[600, 200]), \
             patch("pipelinex.context_mgr._summarize_content", return_value="short summary"):
            result = build_context_prompt(
                state, "## Context\nsome guidance\n", None,
                model_cfg=self._model, token_budget=500,
            )
        assert "[SUMMARIZED]" in result
        assert "short summary" in result

    def test_over_budget_essential_only_raises(self):
        from pipelinex.context_mgr import ContextBudgetExceeded
        state = {"essential_key": "big value " * 200}
        tiers = {"essential_key": "essential"}
        with patch("pipelinex.context_mgr._classify_tiers", return_value=tiers), \
             patch("pipelinex.context_mgr._count_tokens", return_value=800):
            with pytest.raises(ContextBudgetExceeded, match="Essential context alone"):
                build_context_prompt(
                    state, "## Context\nsome guidance\n", None,
                    model_cfg=self._model, token_budget=500,
                )

    def test_still_over_after_summarization_raises(self):
        from pipelinex.context_mgr import ContextBudgetExceeded
        state = {"essential_key": "short", "big_include": "big " * 300}
        tiers = {"essential_key": "essential", "big_include": "include"}
        # Both calls (full and summarized) return over-budget
        with patch("pipelinex.context_mgr._classify_tiers", return_value=tiers), \
             patch("pipelinex.context_mgr._count_tokens", side_effect=[800, 700]), \
             patch("pipelinex.context_mgr._summarize_content", return_value="still large summary"):
            with pytest.raises(ContextBudgetExceeded, match="after summarizing"):
                build_context_prompt(
                    state, "## Context\nsome guidance\n", None,
                    model_cfg=self._model, token_budget=500,
                )

    def test_essential_preserved_when_include_summarized(self):
        state = {"essential_key": "MUST KEEP THIS", "big_include": "filler " * 200}
        tiers = {"essential_key": "essential", "big_include": "include"}
        with patch("pipelinex.context_mgr._classify_tiers", return_value=tiers), \
             patch("pipelinex.context_mgr._count_tokens", side_effect=[600, 200]), \
             patch("pipelinex.context_mgr._summarize_content", return_value="summary"):
            result = build_context_prompt(
                state, "## Context\nsome guidance\n", None,
                model_cfg=self._model, token_budget=500,
            )
        assert "MUST KEEP THIS" in result
        assert "[ESSENTIAL]" in result
