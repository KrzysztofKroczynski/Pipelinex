"""Tests for loader.py — env loading, substitution, pipeline loading, SKILL.md cascading, validation."""
import yaml
import pytest

from pipelinex.loader import _substitute, load_pipeline, load_skill_md, validate_pipeline


class TestSubstitute:
    def test_replaces_env_var(self):
        assert _substitute("Hello ${NAME}", {"NAME": "world"}) == "Hello world"

    def test_replaces_multiple_vars(self):
        assert _substitute("${A}-${B}", {"A": "foo", "B": "bar"}) == "foo-bar"

    def test_raises_on_missing_var(self):
        with pytest.raises(EnvironmentError, match="Missing environment variable: MISSING"):
            _substitute("${MISSING}", {})

    def test_traverses_dict(self):
        assert _substitute({"key": "${X}"}, {"X": "val"}) == {"key": "val"}

    def test_traverses_list(self):
        assert _substitute(["${A}", "${B}"], {"A": "1", "B": "2"}) == ["1", "2"]

    def test_non_string_passthrough(self):
        assert _substitute(42, {}) == 42
        assert _substitute(None, {}) is None
        assert _substitute(True, {}) is True

    def test_nested_dict_and_list(self):
        obj = {"model": {"name": "${MODEL}"}, "tags": ["${TAG}"]}
        result = _substitute(obj, {"MODEL": "claude", "TAG": "prod"})
        assert result == {"model": {"name": "claude"}, "tags": ["prod"]}


class TestLoadPipeline:
    def _write_pipeline(self, tmp_path, cfg):
        (tmp_path / "pipeline.yaml").write_text(yaml.dump(cfg), encoding="utf-8")

    def _base_cfg(self):
        return {
            "name": "test",
            "version": "1",
            "model": {"provider": "anthropic", "name": "claude-sonnet-4-6"},
            "steps": [{"id": "s1"}],
        }

    def test_loads_basic_pipeline(self, tmp_path):
        self._write_pipeline(tmp_path, self._base_cfg())
        config = load_pipeline(tmp_path)
        assert config["name"] == "test"
        assert config["_path"] == tmp_path

    def test_adds_env_key(self, tmp_path):
        self._write_pipeline(tmp_path, self._base_cfg())
        config = load_pipeline(tmp_path)
        assert "_env" in config

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_pipeline(tmp_path)

    def test_substitutes_env_from_dotenv(self, tmp_path):
        (tmp_path / ".env").write_text("MY_KEY=secret\n", encoding="utf-8")
        cfg = self._base_cfg()
        cfg["model"]["provider"] = "${MY_KEY}"
        self._write_pipeline(tmp_path, cfg)
        config = load_pipeline(tmp_path)
        assert config["model"]["provider"] == "secret"

    def test_exits_on_missing_env_var(self, tmp_path):
        cfg = self._base_cfg()
        cfg["model"]["provider"] = "${FOLPIPE_UNDEFINED_VAR_XYZ_12345}"
        self._write_pipeline(tmp_path, cfg)
        with pytest.raises(SystemExit):
            load_pipeline(tmp_path)


class TestLoadSkillMd:
    def test_returns_empty_when_nothing_exists(self, tmp_path):
        assert load_skill_md(tmp_path) == ""

    def test_loads_global_skill_only(self, tmp_path):
        (tmp_path / "SKILL.md").write_text("global skill", encoding="utf-8")
        assert load_skill_md(tmp_path) == "global skill"

    def test_loads_step_skill_without_global(self, tmp_path):
        step = tmp_path / "step-01"
        step.mkdir()
        (step / "SKILL.md").write_text("step skill", encoding="utf-8")
        assert load_skill_md(tmp_path, "step-01") == "step skill"

    def test_cascades_global_and_step(self, tmp_path):
        (tmp_path / "SKILL.md").write_text("global", encoding="utf-8")
        step = tmp_path / "step-01"
        step.mkdir()
        (step / "SKILL.md").write_text("step", encoding="utf-8")
        result = load_skill_md(tmp_path, "step-01")
        assert "global" in result
        assert "step" in result
        assert "---" in result

    def test_cascades_substep(self, tmp_path):
        step = tmp_path / "step-01"
        sub = step / "sub-01"
        sub.mkdir(parents=True)
        (step / "SKILL.md").write_text("step", encoding="utf-8")
        (sub / "SKILL.md").write_text("substep", encoding="utf-8")
        result = load_skill_md(tmp_path, "step-01", "sub-01")
        assert "step" in result
        assert "substep" in result

    def test_missing_step_skill_ignored(self, tmp_path):
        (tmp_path / "SKILL.md").write_text("global", encoding="utf-8")
        result = load_skill_md(tmp_path, "nonexistent-step")
        assert result == "global"


class TestValidatePipeline:
    def _base(self):
        return {
            "model": {"provider": "anthropic", "name": "claude-sonnet-4-6"},
            "steps": [{"id": "s1"}],
        }

    def test_valid_pipeline_no_errors(self):
        assert validate_pipeline(self._base()) == []

    def test_missing_model_section(self):
        cfg = self._base()
        del cfg["model"]
        errors = validate_pipeline(cfg)
        assert any("model" in e for e in errors)

    def test_missing_provider(self):
        cfg = self._base()
        del cfg["model"]["provider"]
        errors = validate_pipeline(cfg)
        assert any("provider" in e for e in errors)

    def test_missing_model_name(self):
        cfg = self._base()
        del cfg["model"]["name"]
        errors = validate_pipeline(cfg)
        assert any("name" in e for e in errors)

    def test_empty_steps(self):
        cfg = self._base()
        cfg["steps"] = []
        errors = validate_pipeline(cfg)
        assert any("step" in e.lower() for e in errors)

    def test_step_missing_id(self):
        cfg = {"model": {"provider": "a", "name": "b"}, "steps": [{}]}
        errors = validate_pipeline(cfg)
        assert any("id" in e for e in errors)

    def test_invalid_can_goto_target(self):
        cfg = self._base()
        cfg["steps"][0]["can_goto"] = ["nonexistent"]
        errors = validate_pipeline(cfg)
        assert any("nonexistent" in e for e in errors)

    def test_valid_can_goto(self):
        cfg = {
            "model": {"provider": "a", "name": "b"},
            "steps": [{"id": "s1", "can_goto": ["s2"]}, {"id": "s2"}],
        }
        assert validate_pipeline(cfg) == []
