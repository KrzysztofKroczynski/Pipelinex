"""Tests for tools/executor.py — custom tool execution via subprocess."""
import json
import sys
from pathlib import Path

import pytest

from pipelinex.tools.executor import execute_custom_tool


def _make_py_tool(tool_dir: Path, script: str) -> Path:
    tool_dir.mkdir(parents=True, exist_ok=True)
    runner = tool_dir / "run.py"
    runner.write_text(script, encoding="utf-8")
    return runner


class TestExecuteCustomTool:
    def test_runs_python_tool_and_returns_json(self, tmp_path):
        script = (
            "import json, sys\n"
            "args = json.load(sys.stdin)\n"
            "print(json.dumps({'result': args['x'] * 2}))\n"
        )
        _make_py_tool(tmp_path / "double", script)
        result = execute_custom_tool(tmp_path / "double", {"x": 21})
        assert result["result"] == 42

    def test_missing_runner_returns_error(self, tmp_path):
        (tmp_path / "empty_tool").mkdir()
        result = execute_custom_tool(tmp_path / "empty_tool", {})
        assert "error" in result

    def test_nonzero_exit_with_json_stdout_uses_json(self, tmp_path):
        script = (
            "import json, sys\n"
            "sys.stdin.read()\n"
            "print(json.dumps({'error': 'bad input'}))\n"
            "sys.exit(1)\n"
        )
        _make_py_tool(tmp_path / "failing_json", script)
        result = execute_custom_tool(tmp_path / "failing_json", {})
        assert result.get("error") == "bad input"

    def test_nonzero_exit_without_json_uses_stderr(self, tmp_path):
        script = (
            "import sys\n"
            "sys.stdin.read()\n"
            "sys.stderr.write('something broke')\n"
            "sys.exit(1)\n"
        )
        _make_py_tool(tmp_path / "failing_stderr", script)
        result = execute_custom_tool(tmp_path / "failing_stderr", {})
        assert "error" in result

    def test_non_json_stdout_returned_as_output_key(self, tmp_path):
        script = (
            "import sys\n"
            "sys.stdin.read()\n"
            "print('plain text output')\n"
        )
        _make_py_tool(tmp_path / "plain_output", script)
        result = execute_custom_tool(tmp_path / "plain_output", {})
        assert "output" in result
        assert "plain text output" in result["output"]

    def test_env_vars_forwarded_to_tool(self, tmp_path):
        script = (
            "import json, os, sys\n"
            "sys.stdin.read()\n"
            "print(json.dumps({'MY_VAR': os.environ.get('MY_VAR', 'missing')}))\n"
        )
        _make_py_tool(tmp_path / "env_tool", script)
        result = execute_custom_tool(tmp_path / "env_tool", {}, env={"MY_VAR": "hello"})
        assert result["MY_VAR"] == "hello"

    def test_args_passed_via_stdin(self, tmp_path):
        script = (
            "import json, sys\n"
            "args = json.load(sys.stdin)\n"
            "print(json.dumps({'received': args}))\n"
        )
        _make_py_tool(tmp_path / "echo_args", script)
        result = execute_custom_tool(tmp_path / "echo_args", {"key": "value", "num": 99})
        assert result["received"] == {"key": "value", "num": 99}

    def test_env_private_keys_excluded(self, tmp_path):
        script = (
            "import json, os, sys\n"
            "sys.stdin.read()\n"
            "print(json.dumps({'has_private': '_SECRET' in os.environ}))\n"
        )
        _make_py_tool(tmp_path / "private_env", script)
        result = execute_custom_tool(tmp_path / "private_env", {}, env={"_SECRET": "hidden"})
        assert result["has_private"] is False
