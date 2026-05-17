import json
import os
import subprocess
import sys
from pathlib import Path


def execute_custom_tool(tool_dir: Path, args: dict, env: dict | None = None) -> dict:
    tool_dir = Path(tool_dir)

    runner = None
    for name in ("run.py", "run.sh", "run.js"):
        candidate = tool_dir / name
        if candidate.exists():
            runner = candidate
            break

    if runner is None:
        return {"error": f"No run.py/run.sh/run.js found in {tool_dir}"}

    if runner.suffix == ".py":
        cmd = [sys.executable, str(runner)]
    elif runner.suffix == ".sh":
        cmd = ["bash", str(runner)]
    else:
        cmd = ["node", str(runner)]

    run_env = os.environ.copy()
    if env:
        run_env.update({k: str(v) for k, v in env.items() if not k.startswith("_")})

    # Prepend shared dep cache to PYTHONPATH
    cache = Path.home() / ".pipelinex" / "envs" / "default"
    if cache.exists():
        existing = run_env.get("PYTHONPATH", "")
        run_env["PYTHONPATH"] = f"{cache}{os.pathsep}{existing}" if existing else str(cache)

    try:
        result = subprocess.run(
            cmd,
            input=json.dumps(args),
            capture_output=True,
            text=True,
            env=run_env,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return {"error": "Tool timed out after 300s"}
    except Exception as e:
        return {"error": str(e)}

    if result.returncode != 0:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"error": result.stderr.strip() or f"Exit code {result.returncode}"}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"output": result.stdout}
