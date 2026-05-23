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
