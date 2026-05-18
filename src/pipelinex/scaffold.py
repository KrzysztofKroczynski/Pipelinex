from pathlib import Path

_PIPELINE_YAML = """\
name: {name}
version: 1.0.0

model:
  provider: anthropic
  name: claude-sonnet-4-6
  api_key: ${{ANTHROPIC_API_KEY}}

steps:
  - id: step-01-ingest

  - id: step-02-process
    max_iterations: 100
    can_goto:
      - step-02-process
      - step-03-output

  - id: step-03-output
    terminal: true
"""

_GLOBAL_SKILL = """\
# {name}

Describe what this pipeline does and who it serves.

All output should be precise and well-structured.
"""

_STEP_SKILL = """\
# {step_id}

Describe what this step does and why it exists.

## Context

Describe what this step needs from previous steps.
The previous step's handoff and key state values are injected automatically.

## Task

Describe what this step should do — written as you'd explain it to a smart colleague.

## When things go wrong

Describe how to handle failures, what to retry, when to stop.

## Notes

Edge cases worth knowing about.
"""

_TOOL_JSON = """\
{{
  "name": "{name}",
  "description": "Describe when to use this tool and when NOT to.",
  "inputSchema": {{
    "type": "object",
    "properties": {{
      "input": {{
        "type": "string",
        "description": "Input value"
      }}
    }},
    "required": ["input"]
  }},
  "run": "run.py",
  "deps": []
}}
"""

_TOOL_RUN = """\
import sys
import json

args = json.load(sys.stdin)

# TODO: implement tool logic
result = {"ok": True, "output": f"Processed: {args.get('input', '')}"}

print(json.dumps(result))
"""

_ENV = """\
ANTHROPIC_API_KEY=sk-ant-your-key-here
"""

_GITIGNORE = """\
.env
output/
__pycache__/
*.pyc
"""


def scaffold_pipeline(name: str, base_dir: Path = Path(".")):
    d = Path(base_dir) / name
    d.mkdir(parents=True, exist_ok=True)

    (d / "pipeline.yaml").write_text(_PIPELINE_YAML.format(name=name), encoding="utf-8")
    (d / "SKILL.md").write_text(_GLOBAL_SKILL.format(name=name), encoding="utf-8")
    (d / ".env").write_text(_ENV, encoding="utf-8")
    (d / ".gitignore").write_text(_GITIGNORE, encoding="utf-8")

    for sub in ("input", "output", "tools"):
        (d / sub).mkdir(exist_ok=True)

    for step_id in ("step-01-ingest", "step-02-process", "step-03-output"):
        scaffold_step(step_id, d, _quiet=True)

    print(f"Created pipeline: {d}")
    print(f"Next steps:")
    print(f"  1. Edit {d}/.env — add your API key")
    print(f"  2. Edit {d}/pipeline.yaml — configure steps and model")
    print(f"  3. Edit {d}/*/SKILL.md — write step instructions")
    print(f"  4. Drop files into {d}/input/")
    print(f"  5. Run: folpipe run {d}")


def scaffold_step(step_id: str, pipeline_dir: Path, _quiet: bool = False):
    d = Path(pipeline_dir) / step_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(_STEP_SKILL.format(step_id=step_id), encoding="utf-8")
    (d / "tools").mkdir(exist_ok=True)
    if not _quiet:
        print(f"Created step: {d}")
        print(f"  Edit {d}/SKILL.md to write the step instructions")


def scaffold_tool(name: str, tools_dir: Path):
    d = Path(tools_dir) / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "tool.json").write_text(_TOOL_JSON.format(name=name), encoding="utf-8")
    (d / "run.py").write_text(_TOOL_RUN, encoding="utf-8")
    (d / "README.md").write_text(f"# {name}\n\nDescribe this tool.\n", encoding="utf-8")
    print(f"Created tool: {d}")
    print(f"  Edit {d}/tool.json — description and schema")
    print(f"  Edit {d}/run.py — tool implementation")
