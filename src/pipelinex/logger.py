import json
from datetime import datetime
from pathlib import Path
from typing import Any


class PipelineLogger:
    def __init__(self, output_path: Path, watch: bool = False):
        self.output_path = Path(output_path)
        self.watch = watch
        self.log_file = self.output_path / "run.log"
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.log_file.write_text("", encoding="utf-8")

    def _write(self, entry: dict):
        entry["ts"] = datetime.now().isoformat()
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def step_start(self, step_id: str):
        self._write({"type": "step_start", "step": step_id})
        if self.watch:
            print(f"[{_now()}] > {step_id}")

    def step_end(self, step_id: str, next_step: str | None = None):
        self._write({"type": "step_end", "step": step_id, "next": next_step})
        if self.watch:
            suffix = f" → {next_step}" if next_step else " (done)"
            print(f"[{_now()}] v {step_id}{suffix}")

    def tool_call(self, step_id: str, tool_name: str, args: dict):
        self._write({"type": "tool_call", "step": step_id, "tool": tool_name, "args": args})
        if self.watch:
            print(f"[{_now()}]   | {tool_name}({_trim(args)})")

    def tool_result(self, step_id: str, tool_name: str, result: Any):
        self._write({"type": "tool_result", "step": step_id, "tool": tool_name, "result": result})

    def model_response(self, step_id: str, text: str):
        self._write({"type": "model_response", "step": step_id, "text": text})

    def context_snapshot(self, step_id: str, context: str):
        self._write({"type": "context_snapshot", "step": step_id, "context": context})

    def error(self, step_id: str, error: str, state: dict | None = None, last_response: str | None = None):
        self._write({"type": "error", "step": step_id, "error": error})

        errors_dir = self.output_path / "errors"
        errors_dir.mkdir(parents=True, exist_ok=True)

        report = (
            f"# Pipeline Error Report\n\n"
            f"**Failed at step:** {step_id}\n\n"
            f"**Time:** {datetime.now().isoformat()}\n\n"
            f"**Error:**\n\n```\n{error}\n```\n"
        )
        (errors_dir / "report.md").write_text(report, encoding="utf-8")

        if state:
            (errors_dir / "state.json").write_text(
                json.dumps(state, indent=2, default=str), encoding="utf-8"
            )
        if last_response:
            (errors_dir / "last-response.md").write_text(last_response, encoding="utf-8")


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _trim(args: dict) -> str:
    s = json.dumps(args, default=str)
    return s[:80] + "..." if len(s) > 80 else s
