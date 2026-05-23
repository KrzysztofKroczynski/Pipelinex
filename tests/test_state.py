"""Tests for state.py — init, persistence, resume, thread safety."""
import json
import threading

import pytest

from pipelinex.state import State


class TestStateInit:
    def test_creates_state_file(self, tmp_path):
        State(tmp_path)
        assert (tmp_path / "output" / "state.json").exists()

    def test_initial_meta_structure(self, tmp_path):
        State(tmp_path)
        data = json.loads((tmp_path / "output" / "state.json").read_text())
        assert data["_meta"]["completed_steps"] == []
        assert data["_meta"]["current_step"] is None

    def test_stores_pipeline_version(self, tmp_path):
        State(tmp_path, pipeline_version="2")
        data = json.loads((tmp_path / "output" / "state.json").read_text())
        assert data["_meta"]["pipeline_version"] == "2"

    def test_resume_loads_existing_data(self, tmp_path):
        s1 = State(tmp_path)
        s1.set("foo", "bar")
        s2 = State(tmp_path, resume=True)
        assert s2.get("foo") == "bar"

    def test_no_resume_fresh_state(self, tmp_path):
        s1 = State(tmp_path)
        s1.set("foo", "bar")
        s2 = State(tmp_path, resume=False)
        assert s2.get("foo") is None

    def test_version_mismatch_prints_warning(self, tmp_path, capsys):
        State(tmp_path, pipeline_version="1").set("x", 1)
        State(tmp_path, resume=True, pipeline_version="2")
        out = capsys.readouterr().out
        assert "WARNING" in out or "version mismatch" in out.lower()

    def test_no_warning_on_version_match(self, tmp_path, capsys):
        State(tmp_path, pipeline_version="1").set("x", 1)
        State(tmp_path, resume=True, pipeline_version="1")
        assert capsys.readouterr().out == ""


class TestStateOperations:
    def test_get_returns_default_for_missing_key(self, tmp_path):
        s = State(tmp_path)
        assert s.get("missing") is None
        assert s.get("missing", "fallback") == "fallback"

    def test_set_persists_to_disk(self, tmp_path):
        s = State(tmp_path)
        s.set("report", {"lines": 42})
        data = json.loads((tmp_path / "output" / "state.json").read_text())
        assert data["report"] == {"lines": 42}

    def test_get_handoff_none_initially(self, tmp_path):
        assert State(tmp_path).get_handoff() is None

    def test_set_current_step(self, tmp_path):
        s = State(tmp_path)
        s.set_current_step("step-02")
        assert s._data["_meta"]["current_step"] == "step-02"

    def test_mark_step_complete(self, tmp_path):
        s = State(tmp_path)
        s.mark_step_complete("step-01")
        assert "step-01" in s._data["_meta"]["completed_steps"]

    def test_mark_step_complete_no_duplicates(self, tmp_path):
        s = State(tmp_path)
        s.mark_step_complete("step-01")
        s.mark_step_complete("step-01")
        assert s._data["_meta"]["completed_steps"].count("step-01") == 1

    def test_snapshot_returns_shallow_copy(self, tmp_path):
        s = State(tmp_path)
        snap = s.snapshot()
        snap["injected"] = True
        assert "injected" not in s._data

    def test_thread_safe_concurrent_writes(self, tmp_path):
        s = State(tmp_path)
        errors = []

        def writer(i):
            try:
                s.set(f"key_{i}", i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        for i in range(20):
            assert s.get(f"key_{i}") == i
