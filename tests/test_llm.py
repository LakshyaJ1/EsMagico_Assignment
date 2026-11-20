from __future__ import annotations

from typing import Any

import pytest

from invoice_extractor.config import Settings
from invoice_extractor.errors import ConfigurationError, LLMUnavailable
from invoice_extractor.llm import GeminiClient, LLMResponse
from invoice_extractor.pricing import Usage, cost_of, price_for


def test_missing_key_is_a_configuration_error() -> None:
    with pytest.raises(ConfigurationError):
        GeminiClient(Settings(api_key=None))


def _client(
    monkeypatch: pytest.MonkeyPatch, fallback: str | None, fail: set[str]
) -> tuple[GeminiClient, list[str]]:
    client = GeminiClient(
        Settings(api_key="test", model="primary", fallback_model=fallback, cache_dir=None)
    )
    calls: list[str] = []

    def fake_generate(model: str, *args: Any) -> LLMResponse:
        calls.append(model)
        if model in fail:
            raise LLMUnavailable("503 high demand")
        return LLMResponse(
            text="{}",
            usage=Usage(calls=1),
            model=model,
            model_version=None,
            finish_reason="STOP",
            latency_ms=1,
        )

    monkeypatch.setattr(client, "_generate", fake_generate)
    return client, calls


def test_falls_back_when_primary_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    client, calls = _client(monkeypatch, fallback="backup", fail={"primary"})
    response = client.generate_json(["hi"], schema={})
    assert calls == ["primary", "backup"]
    assert response.model == "backup" and "503" in (response.fallback_reason or "")


def test_no_fallback_configured_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _client(monkeypatch, fallback=None, fail={"primary"})
    with pytest.raises(LLMUnavailable):
        client.generate_json(["hi"], schema={})


def test_both_down_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    client, calls = _client(monkeypatch, fallback="backup", fail={"primary", "backup"})
    with pytest.raises(LLMUnavailable):
        client.generate_json(["hi"], schema={})
    assert calls == ["primary", "backup"]


def test_cost_counts_thinking_at_the_output_rate() -> None:
    price = price_for("gemini-3.5-flash-lite")
    assert price is not None
    cost, priced = cost_of("gemini-3.5-flash-lite", 1_000_000, 500_000, 500_000)
    assert priced and cost == pytest.approx(price.input_per_m + price.output_per_m)


def test_unknown_model_is_marked_unpriced() -> None:
    assert cost_of("mystery-model", 10, 10, 0) == (0.0, False)
    assert price_for("models/gemini-3.5-flash-lite") is not None
