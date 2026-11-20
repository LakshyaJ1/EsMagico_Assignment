"""Thin wrapper around the Gemini API (official ``google-genai`` SDK).

What it adds on top of the SDK:
* JSON-schema constrained output, parsed and returned as text,
* transport retries with exponential backoff for 408/429/5xx and a hard timeout,
* one typed error per failure mode (see ``errors.py``),
* token accounting and cost for every call,
* an optional on-disk response cache so re-running the eval does not re-spend money.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from .config import PROMPT_VERSION, Settings
from .errors import ConfigurationError, LLMRejected, LLMUnavailable
from .pricing import Usage, cost_of

log = logging.getLogger(__name__)

RETRYABLE_STATUS = [408, 429, 500, 502, 503, 504]
MAX_OUTPUT_TOKENS = 16_384


def _transport_errors() -> tuple[type[BaseException], ...]:
    # The SDK can run on either httpx or httpx2; catch transport failures from both.
    found: list[type[BaseException]] = []
    for module_name in ("httpx2", "httpx"):
        try:
            found.append(importlib.import_module(module_name).TransportError)
        except (ImportError, AttributeError):
            continue
    return tuple(found) or (OSError,)


TRANSPORT_ERRORS = _transport_errors()


@dataclass(frozen=True)
class Blob:
    """Binary input (an image or a PDF)."""

    data: bytes
    mime_type: str


Content = str | Blob


@dataclass
class LLMResponse:
    text: str
    usage: Usage
    model: str  # the model that actually answered (differs from the request on fallback)
    model_version: str | None
    finish_reason: str | None
    latency_ms: float
    cached: bool = False
    fallback_reason: str | None = None


class GeminiClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        self.settings = settings
        self._client = genai.Client(
            api_key=settings.api_key,
            http_options=types.HttpOptions(
                timeout=int(settings.request_timeout_s * 1000),
                retry_options=types.HttpRetryOptions(
                    attempts=settings.api_attempts,
                    initial_delay=2.0,
                    max_delay=60.0,
                    http_status_codes=RETRYABLE_STATUS,
                ),
            ),
        )
        self._cache_dir = settings.cache_dir

    # ----------------------------------------------------------------------------------

    def generate_json(
        self,
        contents: list[Content],
        *,
        schema: dict[str, Any],
        system_instruction: str | None = None,
        thinking_level: str | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        model = model or self.settings.model
        try:
            return self._generate(model, contents, schema, system_instruction, thinking_level)
        except LLMUnavailable as exc:
            fallback = self.settings.fallback_model
            if not fallback or fallback == model:
                raise
            log.warning("%s unavailable (%s); falling back to %s", model, exc.message, fallback)
            response = self._generate(
                fallback, contents, schema, system_instruction, thinking_level
            )
            response.fallback_reason = f"{model} unavailable: {exc.message}"
            return response

    def _generate(
        self,
        model: str,
        contents: list[Content],
        schema: dict[str, Any],
        system_instruction: str | None,
        thinking_level: str | None,
    ) -> LLMResponse:
        thinking_level = thinking_level or self.settings.thinking_level
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_json_schema=schema,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            media_resolution=types.MediaResolution.MEDIA_RESOLUTION_HIGH,
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level.upper()),
        )

        cache_key = self._cache_key(model, contents, system_instruction, schema, thinking_level)
        if (cached := self._read_cache(cache_key)) is not None:
            return cached

        parts = [self._to_part(item) for item in contents]
        started = time.perf_counter()
        response = self._call(model, parts, config)
        latency_ms = (time.perf_counter() - started) * 1000

        result = self._parse(model, response, latency_ms)
        self._write_cache(cache_key, result)
        return result

    # ----------------------------------------------------------------------------------

    def _call(
        self, model: str, parts: list[types.Part], config: types.GenerateContentConfig
    ) -> types.GenerateContentResponse:
        try:
            return self._client.models.generate_content(model=model, contents=parts, config=config)
        except genai_errors.ClientError as exc:
            if exc.code in (401, 403):
                raise ConfigurationError(f"The Gemini API rejected the key ({exc.code}).") from exc
            if exc.code == 429:
                raise LLMUnavailable("Rate limited by the Gemini API after retries.") from exc
            if exc.code == 404:
                raise LLMRejected(
                    f"Model '{model}' was not found or is not available to this key."
                ) from exc
            raise LLMRejected(
                f"The Gemini API rejected the request ({exc.code}): {exc.message}"
            ) from exc
        except genai_errors.ServerError as exc:
            raise LLMUnavailable(
                f"Gemini API error {exc.code} after retries: {exc.message}"
            ) from exc
        except TRANSPORT_ERRORS as exc:
            raise LLMUnavailable(
                f"Could not reach the Gemini API within {self.settings.request_timeout_s:.0f}s "
                f"({type(exc).__name__})."
            ) from exc

    @staticmethod
    def _to_part(item: Content) -> types.Part:
        if isinstance(item, Blob):
            return types.Part.from_bytes(data=item.data, mime_type=item.mime_type)
        return types.Part.from_text(text=item)

    @staticmethod
    def _parse(
        model: str, response: types.GenerateContentResponse, latency_ms: float
    ) -> LLMResponse:
        feedback = response.prompt_feedback
        if feedback is not None and feedback.block_reason:
            raise LLMRejected(f"The prompt was blocked by the API ({feedback.block_reason}).")
        if not response.candidates:
            raise LLMRejected("The API returned no candidates.")

        candidate = response.candidates[0]
        finish = candidate.finish_reason.name if candidate.finish_reason else None
        if finish not in (None, "STOP", "MAX_TOKENS"):
            raise LLMRejected(f"Generation stopped early ({finish}).")

        meta = response.usage_metadata
        input_tokens = (meta.prompt_token_count or 0) if meta else 0
        output_tokens = (meta.candidates_token_count or 0) if meta else 0
        thinking_tokens = (meta.thoughts_token_count or 0) if meta else 0
        image_tokens = sum(
            detail.token_count or 0
            for detail in ((meta.prompt_tokens_details or []) if meta else [])
            if detail.modality and detail.modality.name in ("IMAGE", "DOCUMENT")
        )
        cost, priced = cost_of(model, input_tokens, output_tokens, thinking_tokens)
        usage = Usage(
            calls=1,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            thinking_tokens=thinking_tokens,
            image_tokens=image_tokens,
            cost_usd=cost,
            priced=priced,
        )
        return LLMResponse(
            text=response.text or "",
            usage=usage,
            model=model,
            model_version=response.model_version,
            finish_reason=finish,
            latency_ms=latency_ms,
        )

    # --- cache ------------------------------------------------------------------------

    @staticmethod
    def _cache_key(
        model: str,
        contents: list[Content],
        system_instruction: str | None,
        schema: dict[str, Any],
        thinking_level: str,
    ) -> str:
        digest = hashlib.sha256()
        for chunk in (
            PROMPT_VERSION,
            model,
            thinking_level,
            system_instruction or "",
            json.dumps(schema, sort_keys=True),
        ):
            digest.update(chunk.encode())
        for item in contents:
            digest.update(item.data if isinstance(item, Blob) else item.encode())
        return digest.hexdigest()

    def _read_cache(self, key: str) -> LLMResponse | None:
        if self._cache_dir is None:
            return None
        path = self._cache_dir / f"{key}.json"
        if not path.exists():
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        log.debug("cache hit %s", key[:12])
        return LLMResponse(
            text=record["text"],
            usage=Usage(**record["usage"]),
            model=record["model"],
            model_version=record.get("model_version"),
            finish_reason=record.get("finish_reason"),
            latency_ms=record["latency_ms"],
            cached=True,
        )

    def _write_cache(self, key: str, result: LLMResponse) -> None:
        if self._cache_dir is None:
            return
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "text": result.text,
            "usage": {**result.usage.to_dict()},
            "model": result.model,
            "model_version": result.model_version,
            "finish_reason": result.finish_reason,
            "latency_ms": result.latency_ms,
        }
        Path(self._cache_dir / f"{key}.json").write_text(json.dumps(record), encoding="utf-8")
