"""Tests for BuiltinExecutor — read_file, write_file, write_state, extract_json, template, run_script."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pipelinex.tools.builtin import BuiltinExecutor


def _make_executor(tmp_path: Path) -> BuiltinExecutor:
    state = MagicMock()
    state.set = MagicMock()
    (tmp_path / "output" / "step-01").mkdir(parents=True, exist_ok=True)
    return BuiltinExecutor(
        state=state,
        pipeline_path=tmp_path,
        step_id="step-01",
        model_config={},
        logger=MagicMock(),
    )


class TestReadFile:
    def test_reads_existing_file(self, tmp_path):
        exe = _make_executor(tmp_path)
        f = tmp_path / "doc.txt"
        f.write_text("line1\nline2\nline3", encoding="utf-8")
        result = exe._read_file({"path": str(f)})
        assert result["content"] == "line1\nline2\nline3"
        assert result["lines"] == 3

    def test_missing_file_returns_error(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._read_file({"path": str(tmp_path / "nope.txt")})
        assert "error" in result

    def test_line_range(self, tmp_path):
        exe = _make_executor(tmp_path)
        f = tmp_path / "big.txt"
        f.write_text("\n".join(str(i) for i in range(1, 11)), encoding="utf-8")
        result = exe._read_file({"path": str(f), "start_line": 3, "end_line": 5})
        assert result["content"] == "3\n4\n5"
        assert result["lines"] == 3

    def test_relative_path_resolved_to_pipeline(self, tmp_path):
        exe = _make_executor(tmp_path)
        (tmp_path / "relative.txt").write_text("hello", encoding="utf-8")
        result = exe._read_file({"path": "relative.txt"})
        assert result["content"] == "hello"

    def test_returns_path_in_result(self, tmp_path):
        exe = _make_executor(tmp_path)
        f = tmp_path / "x.txt"
        f.write_text("data", encoding="utf-8")
        result = exe._read_file({"path": str(f)})
        assert "path" in result


class TestWriteFile:
    def test_writes_new_file(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._write_file({"path": "out.txt", "content": "hello"})
        assert result["ok"] is True
        assert (tmp_path / "output" / "step-01" / "out.txt").read_text() == "hello"

    def test_appends_to_existing_file(self, tmp_path):
        exe = _make_executor(tmp_path)
        exe._write_file({"path": "out.txt", "content": "first\n"})
        exe._write_file({"path": "out.txt", "content": "second\n", "mode": "append"})
        content = (tmp_path / "output" / "step-01" / "out.txt").read_text()
        assert content == "first\nsecond\n"

    def test_path_traversal_denied(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._write_file({"path": "../../etc/passwd", "content": "bad"})
        assert "error" in result

    def test_absolute_path_within_output_allowed(self, tmp_path):
        exe = _make_executor(tmp_path)
        target = tmp_path / "output" / "step-01" / "safe.txt"
        result = exe._write_file({"path": str(target), "content": "ok"})
        assert result["ok"] is True

    def test_absolute_path_outside_output_denied(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._write_file({"path": str(tmp_path / "outside.txt"), "content": "bad"})
        assert "error" in result

    def test_creates_subdirectories(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._write_file({"path": "sub/dir/out.txt", "content": "nested"})
        assert result["ok"] is True
        assert (tmp_path / "output" / "step-01" / "sub" / "dir" / "out.txt").exists()


class TestWriteState:
    def test_calls_state_set(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._write_state({"key": "result", "value": {"data": 42}})
        assert result["ok"] is True
        exe.state.set.assert_called_once_with("result", {"data": 42})

    def test_returns_key_in_result(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._write_state({"key": "mykey", "value": "myval"})
        assert result["key"] == "mykey"


class TestExtractJson:
    def test_parses_simple_json(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._extract_json({"content": '{"a": 1}'})
        assert result["result"] == {"a": 1}

    def test_no_path_returns_full_data(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._extract_json({"content": '[1, 2, 3]'})
        assert result["result"] == [1, 2, 3]

    def test_dot_path_dict_traversal(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._extract_json({"content": '{"a": {"b": "deep"}}', "path": "a.b"})
        assert result["result"] == "deep"

    def test_dot_path_list_index(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._extract_json({"content": '{"items": ["x", "y", "z"]}', "path": "items.1"})
        assert result["result"] == "y"

    def test_missing_dict_key_returns_none(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._extract_json({"content": '{"a": 1}', "path": "b"})
        assert result["result"] is None

    def test_list_index_out_of_range_returns_error(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._extract_json({"content": '[1, 2]', "path": "5"})
        assert "error" in result

    def test_bad_json_caught_by_execute(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe.execute("extract_json", {"content": "not json"})
        assert "error" in result


class TestTemplate:
    def test_renders_variable(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._template({"template": "Hello {{ name }}!", "variables": {"name": "world"}})
        assert result["result"] == "Hello world!"

    def test_static_template(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._template({"template": "static", "variables": {}})
        assert result["result"] == "static"

    def test_loop_template(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._template({
            "template": "{% for i in items %}{{ i }}{% endfor %}",
            "variables": {"items": ["a", "b", "c"]},
        })
        assert result["result"] == "abc"


class TestExecuteDispatch:
    def test_unknown_tool_returns_error(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe.execute("nonexistent_tool", {})
        assert "error" in result

    def test_execute_wraps_exceptions(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe.execute("extract_json", {"content": "{{invalid}}"})
        assert "error" in result


class TestRunScript:
    def test_runs_echo_command(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._run_script({"command": "echo hello"})
        assert result["ok"] is True
        assert "hello" in result["stdout"]

    def test_nonzero_exit_marks_not_ok(self, tmp_path):
        exe = _make_executor(tmp_path)
        result = exe._run_script({"command": "exit 1"})
        assert result["ok"] is False
        assert result["returncode"] == 1

    def test_captures_stderr(self, tmp_path):
        import sys
        exe = _make_executor(tmp_path)
        result = exe._run_script(
            {"command": f'{sys.executable} -c "import sys; sys.stderr.write(\'err\')"'}
        )
        assert "err" in result["stderr"]
