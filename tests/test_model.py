"""Tests for model.py — _UsageAccumulator, get_usage, reset_usage, call_llm cost tracking."""
import threading
from unittest.mock import MagicMock, patch

import pytest

from pipelinex.model import _UsageAccumulator, get_usage, reset_usage


# ---------------------------------------------------------------------------
# _UsageAccumulator
# ---------------------------------------------------------------------------

class TestUsageAccumulator:
    def setup_method(self):
        self.acc = _UsageAccumulator()

    def test_initial_state(self):
        s = self.acc.snapshot()
        assert s["prompt_tokens"] == 0
        assert s["completion_tokens"] == 0
        assert s["total_tokens"] == 0
        assert s["cost"] == 0.0
        assert s["currency"] == "USD"

    def test_add_accumulates(self):
        self.acc.add(100, 50, 0.01)
        self.acc.add(200, 80, 0.02)
        s = self.acc.snapshot()
        assert s["prompt_tokens"] == 300
        assert s["completion_tokens"] == 130
        assert s["total_tokens"] == 430
        assert round(s["cost"], 6) == round(0.03, 6)

    def test_add_sets_currency(self):
        self.acc.add(10, 5, 0.001, "EUR")
        assert self.acc.snapshot()["currency"] == "EUR"

    def test_currency_defaults_to_usd(self):
        self.acc.add(10, 5, 0.001)
        assert self.acc.snapshot()["currency"] == "USD"

    def test_currency_updated_on_each_add(self):
        self.acc.add(10, 5, 0.001, "USD")
        self.acc.add(10, 5, 0.001, "EUR")
        assert self.acc.snapshot()["currency"] == "EUR"

    def test_reset_clears_all(self):
        self.acc.add(500, 200, 0.05, "EUR")
        self.acc.reset()
        s = self.acc.snapshot()
        assert s["prompt_tokens"] == 0
        assert s["completion_tokens"] == 0
        assert s["cost"] == 0.0
        assert s["currency"] == "USD"

    def test_cost_rounded_in_snapshot(self):
        self.acc.add(0, 0, 1.0 / 3)
        s = self.acc.snapshot()
        assert s["cost"] == round(1.0 / 3, 6)

    def test_thread_safe_concurrent_adds(self):
        errors = []

        def add_many():
            try:
                for _ in range(100):
                    self.acc.add(1, 1, 0.000001)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_many) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        s = self.acc.snapshot()
        assert s["prompt_tokens"] == 1000
        assert s["completion_tokens"] == 1000


# ---------------------------------------------------------------------------
# Module-level get_usage / reset_usage
# ---------------------------------------------------------------------------

class TestModuleUsage:
    def setup_method(self):
        reset_usage()

    def test_reset_usage_zeroes_counters(self):
        s = get_usage()
        assert s["total_tokens"] == 0
        assert s["cost"] == 0.0

    def test_get_usage_returns_snapshot(self):
        s = get_usage()
        assert "prompt_tokens" in s
        assert "completion_tokens" in s
        assert "total_tokens" in s
        assert "cost" in s
        assert "currency" in s


# ---------------------------------------------------------------------------
# call_llm cost accumulation
# ---------------------------------------------------------------------------

def _make_resp(prompt=100, completion=50):
    """Build a minimal mock LiteLLM response."""
    resp = MagicMock()
    resp.choices[0].message = MagicMock()
    resp.usage.prompt_tokens = prompt
    resp.usage.completion_tokens = completion
    return resp


class TestGetRunUsageSchema:
    def test_schema_has_required_fields(self):
        from pipelinex.model import GET_RUN_USAGE_SCHEMA
        assert GET_RUN_USAGE_SCHEMA["name"] == "get_run_usage"
        assert "description" in GET_RUN_USAGE_SCHEMA
        assert GET_RUN_USAGE_SCHEMA["parameters"]["type"] == "object"
        assert GET_RUN_USAGE_SCHEMA["parameters"]["required"] == []


class TestCallLlmCostAccumulation:
    _cfg = {"provider": "openai", "name": "gpt-4o"}

    def setup_method(self):
        reset_usage()

    def test_litellm_cost_accumulated_when_nonzero(self):
        resp = _make_resp(100, 50)
        with patch("pipelinex.model.litellm.completion", return_value=resp), \
             patch("pipelinex.model.litellm.completion_cost", return_value=0.05):
            from pipelinex.model import call_llm
            call_llm(self._cfg, [{"role": "user", "content": "hi"}])
        s = get_usage()
        assert s["prompt_tokens"] == 100
        assert s["completion_tokens"] == 50
        assert s["cost"] == 0.05
        assert s["currency"] == "USD"

    def test_manual_pricing_used_when_litellm_returns_zero(self):
        resp = _make_resp(1_000_000, 500_000)
        cfg = {
            **self._cfg,
            "pricing": {"input_per_million": 1.0, "output_per_million": 2.0, "currency": "USD"},
        }
        with patch("pipelinex.model.litellm.completion", return_value=resp), \
             patch("pipelinex.model.litellm.completion_cost", return_value=0.0):
            from pipelinex.model import call_llm
            call_llm(cfg, [{"role": "user", "content": "hi"}])
        s = get_usage()
        # 1M input @ $1/M + 500K output @ $2/M = $1 + $1 = $2
        assert s["cost"] == pytest.approx(2.0, rel=1e-5)

    def test_manual_pricing_currency_stored(self):
        resp = _make_resp(1_000_000, 0)
        cfg = {
            **self._cfg,
            "pricing": {"input_per_million": 0.5, "output_per_million": 0.0, "currency": "EUR"},
        }
        with patch("pipelinex.model.litellm.completion", return_value=resp), \
             patch("pipelinex.model.litellm.completion_cost", return_value=0.0):
            from pipelinex.model import call_llm
            call_llm(cfg, [{"role": "user", "content": "hi"}])
        assert get_usage()["currency"] == "EUR"

    def test_litellm_cost_wins_over_manual_pricing_when_nonzero(self):
        resp = _make_resp(1_000_000, 0)
        cfg = {
            **self._cfg,
            "pricing": {"input_per_million": 999.0, "output_per_million": 0.0},
        }
        with patch("pipelinex.model.litellm.completion", return_value=resp), \
             patch("pipelinex.model.litellm.completion_cost", return_value=0.01):
            from pipelinex.model import call_llm
            call_llm(cfg, [{"role": "user", "content": "hi"}])
        # LiteLLM returned 0.01, manual would give 999 — LiteLLM must win
        assert get_usage()["cost"] == pytest.approx(0.01)

    def test_currency_is_usd_when_litellm_cost_used(self):
        resp = _make_resp(100, 50)
        cfg = {
            **self._cfg,
            "pricing": {"input_per_million": 1.0, "output_per_million": 2.0, "currency": "EUR"},
        }
        with patch("pipelinex.model.litellm.completion", return_value=resp), \
             patch("pipelinex.model.litellm.completion_cost", return_value=0.01):
            from pipelinex.model import call_llm
            call_llm(cfg, [{"role": "user", "content": "hi"}])
        # LiteLLM cost was used → currency must be USD, not EUR from pricing config
        assert get_usage()["currency"] == "USD"

    def test_no_pricing_config_cost_zero_when_litellm_returns_zero(self):
        resp = _make_resp(500, 200)
        with patch("pipelinex.model.litellm.completion", return_value=resp), \
             patch("pipelinex.model.litellm.completion_cost", return_value=0.0):
            from pipelinex.model import call_llm
            call_llm(self._cfg, [{"role": "user", "content": "hi"}])
        s = get_usage()
        assert s["cost"] == 0.0
        assert s["prompt_tokens"] == 500  # tokens still tracked

    def test_fallback_model_pricing_used(self):
        resp = _make_resp(1_000_000, 0)
        fallback_cfg = {
            "provider": "deepseek",
            "name": "deepseek-chat",
            "api_key": "x",
            "pricing": {"input_per_million": 0.27, "output_per_million": 1.10, "currency": "USD"},
        }
        cfg = {**self._cfg, "fallback": fallback_cfg}

        primary_err = Exception("primary failed")

        with patch("pipelinex.model.litellm.completion", side_effect=[primary_err, resp]), \
             patch("pipelinex.model.litellm.completion_cost", return_value=0.0):
            from pipelinex.model import call_llm
            call_llm(cfg, [{"role": "user", "content": "hi"}])

        s = get_usage()
        # 1M input @ $0.27/M = $0.27
        assert s["cost"] == pytest.approx(0.27, rel=1e-5)

    def test_cost_accumulates_across_multiple_calls(self):
        resp = _make_resp(100, 50)
        with patch("pipelinex.model.litellm.completion", return_value=resp), \
             patch("pipelinex.model.litellm.completion_cost", return_value=0.01):
            from pipelinex.model import call_llm
            call_llm(self._cfg, [{"role": "user", "content": "a"}])
            call_llm(self._cfg, [{"role": "user", "content": "b"}])
            call_llm(self._cfg, [{"role": "user", "content": "c"}])
        s = get_usage()
        assert s["prompt_tokens"] == 300
        assert s["cost"] == pytest.approx(0.03)
