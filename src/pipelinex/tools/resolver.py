import json
import sys
import subprocess
from pathlib import Path

GLOBAL_TOOLS_PATH = Path.home() / ".pipelinex" / "tools"


def resolve_tools(
    pipeline_path: Path,
    step_id: str | None = None,
    substep_id: str | None = None,
    builtin_tools: list[dict] | None = None,
) -> list[dict]:
    """
    Resolve tools in priority order (most specific wins):
    substep-local → step-local → pipeline-level → global cache → builtin
    """
    found: dict[str, dict] = {}

    if builtin_tools:
        for t in builtin_tools:
            found[t["name"]] = t

    _load_dir(GLOBAL_TOOLS_PATH, found)
    _load_dir(pipeline_path / "tools", found)

    if step_id:
        _load_dir(pipeline_path / step_id / "tools", found)
        if substep_id:
            _load_dir(pipeline_path / step_id / substep_id / "tools", found)

    return list(found.values())


def _load_dir(tools_dir: Path, found: dict):
    if not tools_dir.exists():
        return
    for tool_dir in tools_dir.iterdir():
        if not tool_dir.is_dir() or tool_dir.name.startswith("_"):
            continue
        tool_json = tool_dir / "tool.json"
        if not tool_json.exists():
            continue
        try:
            schema = json.loads(tool_json.read_text(encoding="utf-8"))
            schema["_path"] = str(tool_dir)
            # normalize inputSchema -> parameters
            if "inputSchema" in schema and "parameters" not in schema:
                schema["parameters"] = schema["inputSchema"]
            found[schema["name"]] = schema
        except Exception:
            pass


def install_tool_deps(tool_dir: Path, env_base: Path):
    tool_json = tool_dir / "tool.json"
    if not tool_json.exists():
        return
    schema = json.loads(tool_json.read_text(encoding="utf-8"))
    deps = schema.get("deps", [])
    if not deps:
        return

    env_dir = env_base / "envs" / "default"
    env_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--target", str(env_dir)] + deps,
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
