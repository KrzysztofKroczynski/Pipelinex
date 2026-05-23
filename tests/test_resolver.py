"""Tests for tools/resolver.py — tool discovery and priority ordering."""
import json
from pathlib import Path

import pytest

from pipelinex.tools.resolver import _load_dir, resolve_tools


def _write_tool(parent: Path, name: str, description: str = "") -> Path:
    tool_dir = parent / name
    tool_dir.mkdir(parents=True, exist_ok=True)
    schema = {
        "name": name,
        "description": description or f"Tool {name}",
        "parameters": {"type": "object", "properties": {}},
    }
    (tool_dir / "tool.json").write_text(json.dumps(schema), encoding="utf-8")
    return tool_dir


class TestLoadDir:
    def test_loads_valid_tool(self, tmp_path):
        _write_tool(tmp_path, "my_tool")
        found: dict = {}
        _load_dir(tmp_path, found)
        assert "my_tool" in found
        assert found["my_tool"]["_path"] == str(tmp_path / "my_tool")

    def test_skips_underscore_prefix(self, tmp_path):
        _write_tool(tmp_path, "_private")
        found: dict = {}
        _load_dir(tmp_path, found)
        assert "_private" not in found

    def test_skips_missing_tool_json(self, tmp_path):
        (tmp_path / "no_schema").mkdir()
        found: dict = {}
        _load_dir(tmp_path, found)
        assert "no_schema" not in found

    def test_normalizes_input_schema_to_parameters(self, tmp_path):
        tool_dir = tmp_path / "mcp_tool"
        tool_dir.mkdir()
        schema = {"name": "mcp_tool", "description": "x", "inputSchema": {"type": "object"}}
        (tool_dir / "tool.json").write_text(json.dumps(schema), encoding="utf-8")
        found: dict = {}
        _load_dir(tmp_path, found)
        assert "parameters" in found["mcp_tool"]

    def test_handles_nonexistent_dir_gracefully(self, tmp_path):
        found: dict = {}
        _load_dir(tmp_path / "nonexistent", found)
        assert found == {}

    def test_handles_invalid_json_gracefully(self, tmp_path):
        tool_dir = tmp_path / "bad_tool"
        tool_dir.mkdir()
        (tool_dir / "tool.json").write_text("not json {{", encoding="utf-8")
        found: dict = {}
        _load_dir(tmp_path, found)
        assert "bad_tool" not in found

    def test_later_call_overwrites_earlier(self, tmp_path):
        _write_tool(tmp_path, "tool_a", "first")
        found: dict = {}
        _load_dir(tmp_path, found)
        assert found["tool_a"]["description"] == "first"
        # Overwrite with same name
        (tmp_path / "tool_a" / "tool.json").write_text(
            json.dumps({"name": "tool_a", "description": "second", "parameters": {}}),
            encoding="utf-8",
        )
        found2: dict = {}
        _load_dir(tmp_path, found2)
        assert found2["tool_a"]["description"] == "second"


class TestResolveTools:
    def test_step_tool_overrides_pipeline_tool(self, tmp_path):
        _write_tool(tmp_path / "tools", "shared_tool", "pipeline version")
        _write_tool(tmp_path / "step-01" / "tools", "shared_tool", "step version")
        tools = resolve_tools(tmp_path, step_id="step-01")
        tool = next(t for t in tools if t["name"] == "shared_tool")
        assert tool["description"] == "step version"

    def test_builtin_tools_included(self, tmp_path):
        builtins = [{"name": "read_file", "description": "read", "parameters": {}}]
        tools = resolve_tools(tmp_path, builtin_tools=builtins)
        assert any(t["name"] == "read_file" for t in tools)

    def test_custom_tool_overrides_builtin(self, tmp_path):
        _write_tool(tmp_path / "tools", "read_file", "custom override")
        builtins = [{"name": "read_file", "description": "builtin", "parameters": {}}]
        tools = resolve_tools(tmp_path, builtin_tools=builtins)
        tool = next(t for t in tools if t["name"] == "read_file")
        assert tool["description"] == "custom override"

    def test_substep_tool_overrides_step_tool(self, tmp_path):
        _write_tool(tmp_path / "step-01" / "tools", "shared", "step level")
        _write_tool(tmp_path / "step-01" / "sub-01" / "tools", "shared", "substep level")
        tools = resolve_tools(tmp_path, step_id="step-01", substep_id="sub-01")
        tool = next(t for t in tools if t["name"] == "shared")
        assert tool["description"] == "substep level"

    def test_no_tools_returns_builtins_only(self, tmp_path):
        builtins = [{"name": "write_file", "description": "w", "parameters": {}}]
        tools = resolve_tools(tmp_path, builtin_tools=builtins)
        names = {t["name"] for t in tools}
        assert names == {"write_file"}

    def test_tools_without_step_id(self, tmp_path):
        _write_tool(tmp_path / "tools", "pipeline_tool")
        tools = resolve_tools(tmp_path)
        assert any(t["name"] == "pipeline_tool" for t in tools)
