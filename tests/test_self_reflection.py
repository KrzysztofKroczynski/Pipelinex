"""Tests for step self-reflection feature."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipelinex.runner import PipelineRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm_response(text: str = "", tool_calls: list = None):
    """Build a minimal mock response object that extract_text/extract_tool_calls understand."""
    msg = MagicMock()
    msg.content = text

    if tool_calls:
        tc_objects = []
        for tc in tool_calls:
            obj = MagicMock()
            obj.id = tc["id"]
            obj.function.name = tc["name"]
            obj.function.arguments = json.dumps(tc["args"])
            tc_objects.append(obj)
        msg.tool_calls = tc_objects
    else:
        msg.tool_calls = None

    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_pipeline(tmp_path: Path, self_reflection_global=None, step_override=None) -> PipelineRunner:
    """Scaffold a minimal single-step pipeline in tmp_path."""
    step_id = "step-01"
    pipeline_yaml = {"name": "test", "version": "1", "model": {"provider": "anthropic", "name": "claude-sonnet-4-6"}, "steps": [{"id": step_id, "terminal": True}]}
    if self_reflection_global is not None:
        pipeline_yaml["self_reflection"] = self_reflection_global
    if step_override is not None:
        pipeline_yaml["steps"][0]["self_reflection"] = step_override

    import yaml
    (tmp_path / "pipeline.yaml").write_text(yaml.dump(pipeline_yaml), encoding="utf-8")

    skill_path = tmp_path / step_id / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text(
        "# Step\n\nDo the thing.\n\n"
        "## Self-Reflection\n\n"
        "If any tool errors occurred, append a note under '## Lessons Learned' "
        "explaining what went wrong.\n",
        encoding="utf-8",
    )

    (tmp_path / "output").mkdir()

    with patch("pipelinex.runner.load_pipeline") as mock_load, \
         patch("pipelinex.runner.State") as mock_state_cls, \
         patch("pipelinex.runner.PipelineLogger"):

        import yaml as _yaml
        config = _yaml.safe_load((tmp_path / "pipeline.yaml").read_text())
        config["_path"] = tmp_path
        config["_env"] = {}
        mock_load.return_value = config

        state = MagicMock()
        state.snapshot.return_value = {}
        state.get_handoff.return_value = None
        state.get.return_value = None
        mock_state_cls.return_value = state

        runner = PipelineRunner.__new__(PipelineRunner)
        runner.pipeline_path = tmp_path
        runner.config = config
        runner.state = state
        runner.global_model = config["model"]
        runner.model_override = None
        runner.input_data = None
        runner.watch = False
        runner.from_step = None
        runner.max_parallel = 10
        runner.max_depth = 5
        runner.dispatch_timeout = 300
        runner.logger = MagicMock()

    return runner, step_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSelfReflectionEnabled:
    def test_disabled_by_default(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path)
        step_cfg = runner.config["steps"][0]
        assert runner._self_reflection_enabled(step_cfg) is False

    def test_global_enable(self, tmp_path):
        runner, _ = _make_pipeline(tmp_path, self_reflection_global=True)
        step_cfg = runner.config["steps"][0]
        assert runner._self_reflection_enabled(step_cfg) is True

    def test_step_overrides_global(self, tmp_path):
        runner, _ = _make_pipeline(tmp_path, self_reflection_global=True, step_override=False)
        step_cfg = runner.config["steps"][0]
        assert runner._self_reflection_enabled(step_cfg) is False

    def test_step_enables_when_global_off(self, tmp_path):
        runner, _ = _make_pipeline(tmp_path, self_reflection_global=False, step_override=True)
        step_cfg = runner.config["steps"][0]
        assert runner._self_reflection_enabled(step_cfg) is True


class TestSelfReflect:
    def test_appends_to_skill_md_when_model_returns_text(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path, self_reflection_global=True)
        skill_path = tmp_path / step_id / "SKILL.md"
        original = skill_path.read_text(encoding="utf-8")

        reflection_text = "## Lessons Learned\n\n- The file path was wrong."
        messages = [
            {"role": "system", "content": original},
            {"role": "user", "content": "Begin this step."},
        ]

        with patch("pipelinex.runner.call_llm", return_value=_make_llm_response(reflection_text)), \
             patch("pipelinex.runner.extract_text", return_value=reflection_text):
            runner._self_reflect(step_id, messages, runner.global_model)

        updated = skill_path.read_text(encoding="utf-8")
        assert reflection_text in updated
        assert original.rstrip() in updated

    def test_writes_reflection_md_to_output(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path, self_reflection_global=True)
        reflection_text = "## Lessons Learned\n\n- Timeout needs increasing."
        messages = [{"role": "system", "content": "skill"}, {"role": "user", "content": "go"}]

        with patch("pipelinex.runner.call_llm", return_value=_make_llm_response(reflection_text)), \
             patch("pipelinex.runner.extract_text", return_value=reflection_text):
            runner._self_reflect(step_id, messages, runner.global_model)

        reflection_file = tmp_path / "output" / step_id / "reflection.md"
        assert reflection_file.exists()
        assert reflection_text in reflection_file.read_text(encoding="utf-8")

    def test_no_write_when_model_returns_empty(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path, self_reflection_global=True)
        skill_path = tmp_path / step_id / "SKILL.md"
        original = skill_path.read_text(encoding="utf-8")
        messages = [{"role": "system", "content": original}, {"role": "user", "content": "go"}]

        with patch("pipelinex.runner.call_llm", return_value=_make_llm_response("")), \
             patch("pipelinex.runner.extract_text", return_value=""):
            runner._self_reflect(step_id, messages, runner.global_model)

        assert skill_path.read_text(encoding="utf-8") == original
        assert not (tmp_path / "output" / step_id / "reflection.md").exists()

    def test_no_op_when_skill_md_missing(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path, self_reflection_global=True)
        (tmp_path / step_id / "SKILL.md").unlink()
        messages = [{"role": "system", "content": ""}, {"role": "user", "content": "go"}]

        with patch("pipelinex.runner.call_llm") as mock_llm:
            runner._self_reflect(step_id, messages, runner.global_model)
            mock_llm.assert_not_called()


class TestSelfReflectGetRunUsage:
    def _tool_call_response(self, tool_id="u1"):
        """Response that calls get_run_usage."""
        msg = MagicMock()
        msg.content = ""
        tc = MagicMock()
        tc.id = tool_id
        tc.function.name = "get_run_usage"
        tc.function.arguments = "{}"
        msg.tool_calls = [tc]
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    def test_get_run_usage_tool_returns_usage_data(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path, self_reflection_global=True)
        messages = [{"role": "system", "content": "skill"}, {"role": "user", "content": "go"}]

        from pipelinex.model import reset_usage, _usage
        reset_usage()
        _usage.add(1000, 250, 0.02, "USD")

        call_sequence = [self._tool_call_response(), _make_llm_response("## Lessons\n\n- Used 1250 tokens.")]
        captured_tool_results = []

        original_append = list.append

        with patch("pipelinex.runner.call_llm", side_effect=call_sequence), \
             patch("pipelinex.runner.extract_text", side_effect=["", "## Lessons\n\n- Used 1250 tokens."]), \
             patch("pipelinex.runner.extract_tool_calls", side_effect=[
                 [{"id": "u1", "name": "get_run_usage", "args": {}}],
                 [],
             ]):
            runner._self_reflect(step_id, messages, runner.global_model)

        # Reflection file should exist with the final text
        reflection = tmp_path / "output" / step_id / "reflection.md"
        assert reflection.exists()
        assert "Lessons" in reflection.read_text(encoding="utf-8")

    def test_get_run_usage_result_injected_as_tool_response(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path, self_reflection_global=True)
        messages = [{"role": "system", "content": "skill"}, {"role": "user", "content": "go"}]

        from pipelinex.model import reset_usage, _usage
        reset_usage()
        _usage.add(500, 100, 0.005, "EUR")

        calls_made = []

        def fake_call_llm(cfg, msgs, tools=None):
            calls_made.append(msgs[:])
            if len(calls_made) == 1:
                return self._tool_call_response()
            return _make_llm_response("done")

        with patch("pipelinex.runner.call_llm", side_effect=fake_call_llm), \
             patch("pipelinex.runner.extract_text", side_effect=["", "done"]), \
             patch("pipelinex.runner.extract_tool_calls", side_effect=[
                 [{"id": "u1", "name": "get_run_usage", "args": {}}],
                 [],
             ]):
            runner._self_reflect(step_id, messages, runner.global_model)

        # Second call's messages should include a tool result with usage data
        second_call_msgs = calls_made[1]
        tool_msg = next(m for m in second_call_msgs if m["role"] == "tool")
        import json as _json
        result = _json.loads(tool_msg["content"])
        assert result["prompt_tokens"] == 500
        assert result["completion_tokens"] == 100
        assert result["currency"] == "EUR"

    def test_unknown_tool_during_reflection_returns_error(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path, self_reflection_global=True)
        messages = [{"role": "system", "content": "skill"}, {"role": "user", "content": "go"}]

        calls_made = []

        def fake_call_llm(cfg, msgs, tools=None):
            calls_made.append(msgs)
            if len(calls_made) == 1:
                return self._tool_call_response()
            return _make_llm_response("")

        with patch("pipelinex.runner.call_llm", side_effect=fake_call_llm), \
             patch("pipelinex.runner.extract_text", side_effect=["", ""]), \
             patch("pipelinex.runner.extract_tool_calls", side_effect=[
                 [{"id": "x1", "name": "write_file", "args": {}}],
                 [],
             ]):
            runner._self_reflect(step_id, messages, runner.global_model)

        second_msgs = calls_made[1]
        tool_msg = next(m for m in second_msgs if m["role"] == "tool")
        import json as _json
        result = _json.loads(tool_msg["content"])
        assert "error" in result

    def test_get_run_usage_schema_passed_to_call_llm(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path, self_reflection_global=True)
        messages = [{"role": "system", "content": "skill"}, {"role": "user", "content": "go"}]
        captured_tools = []

        def fake_call_llm(cfg, msgs, tools=None):
            captured_tools.append(tools)
            return _make_llm_response("")

        with patch("pipelinex.runner.call_llm", side_effect=fake_call_llm), \
             patch("pipelinex.runner.extract_text", return_value=""), \
             patch("pipelinex.runner.extract_tool_calls", return_value=[]):
            runner._self_reflect(step_id, messages, runner.global_model)

        from pipelinex.model import GET_RUN_USAGE_SCHEMA, READ_DOCS_SCHEMA
        assert captured_tools[0] == [GET_RUN_USAGE_SCHEMA, READ_DOCS_SCHEMA]


class TestRunStepTriggersReflection:
    def test_reflection_called_after_step_completes(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path, self_reflection_global=True)
        step_cfg = runner.config["steps"][0]

        with patch.object(runner, "_self_reflect") as mock_reflect, \
             patch("pipelinex.runner.call_llm", return_value=_make_llm_response("Done.")), \
             patch("pipelinex.runner.extract_text", return_value="Done."), \
             patch("pipelinex.runner.extract_tool_calls", return_value=[]), \
             patch("pipelinex.runner.resolve_tools", return_value=[]), \
             patch("pipelinex.runner.build_context_prompt", return_value=""), \
             patch("pipelinex.runner.load_skill_md", return_value="skill"):

            from pipelinex.tools.builtin import BuiltinExecutor
            with patch.object(BuiltinExecutor, "__init__", return_value=None):
                runner._run_step(step_cfg)
                mock_reflect.assert_called_once()

    def test_reflection_not_called_when_disabled(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path, self_reflection_global=False)
        step_cfg = runner.config["steps"][0]

        with patch.object(runner, "_self_reflect") as mock_reflect, \
             patch("pipelinex.runner.call_llm", return_value=_make_llm_response("Done.")), \
             patch("pipelinex.runner.extract_text", return_value="Done."), \
             patch("pipelinex.runner.extract_tool_calls", return_value=[]), \
             patch("pipelinex.runner.resolve_tools", return_value=[]), \
             patch("pipelinex.runner.build_context_prompt", return_value=""), \
             patch("pipelinex.runner.load_skill_md", return_value="skill"):

            from pipelinex.tools.builtin import BuiltinExecutor
            with patch.object(BuiltinExecutor, "__init__", return_value=None):
                runner._run_step(step_cfg)
                mock_reflect.assert_not_called()


class TestReadDocs:
    def _write_spec(self, tmp_path: Path, content: str) -> Path:
        spec = tmp_path / "PIPELINE_SPEC.md"
        spec.write_text(content, encoding="utf-8")
        return spec

    def test_returns_toc_when_no_section(self, tmp_path):
        spec_content = "# Title\n\n## Model\n\nstuff\n\n## Tools\n\nmore\n"
        self._write_spec(tmp_path, spec_content)
        with patch("pipelinex.runner._find_pipeline_spec", return_value=tmp_path / "PIPELINE_SPEC.md"):
            from pipelinex.runner import _read_docs_section
            result = _read_docs_section("")
        assert "table_of_contents" in result
        assert "## Model" in result["table_of_contents"]
        assert "## Tools" in result["table_of_contents"]

    def test_returns_section_content(self, tmp_path):
        spec_content = "# Title\n\n## Model\n\nmodel config here\n\n## Tools\n\ntool stuff\n"
        self._write_spec(tmp_path, spec_content)
        with patch("pipelinex.runner._find_pipeline_spec", return_value=tmp_path / "PIPELINE_SPEC.md"):
            from pipelinex.runner import _read_docs_section
            result = _read_docs_section("model")
        assert "content" in result
        assert "model config here" in result["content"]
        assert "tool stuff" not in result["content"]

    def test_section_match_is_case_insensitive(self, tmp_path):
        spec_content = "## Context Budget\n\nbudget info\n"
        self._write_spec(tmp_path, spec_content)
        with patch("pipelinex.runner._find_pipeline_spec", return_value=tmp_path / "PIPELINE_SPEC.md"):
            from pipelinex.runner import _read_docs_section
            result = _read_docs_section("context budget")
        assert "content" in result
        assert "budget info" in result["content"]

    def test_multi_word_query_matches_heading_with_underscores(self, tmp_path):
        spec_content = "## context_budget_tokens\n\nSet this to cap injected state.\n"
        self._write_spec(tmp_path, spec_content)
        with patch("pipelinex.runner._find_pipeline_spec", return_value=tmp_path / "PIPELINE_SPEC.md"):
            from pipelinex.runner import _read_docs_section
            result = _read_docs_section("context budget")
        assert "content" in result
        assert "cap injected state" in result["content"]

    def test_missing_section_returns_error(self, tmp_path):
        spec_content = "## Model\n\nstuff\n"
        self._write_spec(tmp_path, spec_content)
        with patch("pipelinex.runner._find_pipeline_spec", return_value=tmp_path / "PIPELINE_SPEC.md"):
            from pipelinex.runner import _read_docs_section
            result = _read_docs_section("nonexistent")
        assert "error" in result

    def test_missing_spec_returns_error(self):
        with patch("pipelinex.runner._find_pipeline_spec", return_value=None):
            from pipelinex.runner import _read_docs_section
            result = _read_docs_section("model")
        assert "error" in result

    def test_read_docs_tool_called_during_reflection(self, tmp_path):
        runner, step_id = _make_pipeline(tmp_path, self_reflection_global=True)
        messages = [{"role": "system", "content": "skill"}, {"role": "user", "content": "go"}]

        doc_tool_response = MagicMock()
        doc_tool_response.content = ""
        tc = MagicMock()
        tc.id = "d1"
        tc.function.name = "read_docs"
        tc.function.arguments = '{"section": "model"}'
        doc_tool_response.tool_calls = [tc]
        choice = MagicMock()
        choice.message = doc_tool_response
        resp = MagicMock()
        resp.choices = [choice]

        calls_made = []

        def fake_call_llm(cfg, msgs, tools=None):
            calls_made.append(msgs[:])
            if len(calls_made) == 1:
                return resp
            return _make_llm_response("done")

        with patch("pipelinex.runner.call_llm", side_effect=fake_call_llm), \
             patch("pipelinex.runner.extract_text", side_effect=["", "done"]), \
             patch("pipelinex.runner.extract_tool_calls", side_effect=[
                 [{"id": "d1", "name": "read_docs", "args": {"section": "model"}}],
                 [],
             ]), \
             patch("pipelinex.runner._read_docs_section", return_value={"content": "model docs"}) as mock_read:
            runner._self_reflect(step_id, messages, runner.global_model)

        mock_read.assert_called_once_with("model")
        second_msgs = calls_made[1]
        tool_msg = next(m for m in second_msgs if m["role"] == "tool")
        import json as _json
        assert _json.loads(tool_msg["content"]) == {"content": "model docs"}
