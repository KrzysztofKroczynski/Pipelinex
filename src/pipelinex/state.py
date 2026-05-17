import json
import threading
from datetime import datetime
from pathlib import Path


class State:
    def __init__(self, pipeline_path: Path, resume: bool = False, pipeline_version: str | None = None):
        self.pipeline_path = Path(pipeline_path)
        self.output_path = self.pipeline_path / "output"
        self.state_file = self.output_path / "state.json"
        self._lock = threading.Lock()

        if resume and self.state_file.exists():
            self._data = json.loads(self.state_file.read_text(encoding="utf-8"))
            saved_version = self._data.get("_meta", {}).get("pipeline_version")
            if pipeline_version and saved_version and saved_version != pipeline_version:
                print(
                    f"WARNING: Pipeline version mismatch — saved state is v{saved_version}, "
                    f"current pipeline is v{pipeline_version}. State structure may have changed."
                )
        else:
            self._data = {
                "_meta": {
                    "started": datetime.now().isoformat(),
                    "pipeline_version": pipeline_version,
                    "current_step": None,
                    "completed_steps": [],
                },
                "handoff": None,
            }
            self._persist()

    def get(self, key: str, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value):
        with self._lock:
            self._data[key] = value
            self._persist()

    def get_handoff(self) -> str | None:
        return self._data.get("handoff")

    def set_current_step(self, step_id: str):
        with self._lock:
            self._data["_meta"]["current_step"] = step_id
            self._persist()

    def mark_step_complete(self, step_id: str):
        with self._lock:
            if step_id not in self._data["_meta"]["completed_steps"]:
                self._data["_meta"]["completed_steps"].append(step_id)
            self._persist()

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._data)

    def _persist(self):
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(self._data, indent=2, default=str), encoding="utf-8"
        )
