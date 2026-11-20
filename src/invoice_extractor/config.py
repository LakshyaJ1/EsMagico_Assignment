"""Runtime settings, read from environment variables (and ``.env`` if present)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from datetime import date
from enum import StrEnum
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_VERSION = "v3"

load_dotenv(PROJECT_ROOT / ".env")


class InputMode(StrEnum):
    """How a document is shown to the model."""

    IMAGES = "images"  # rendered page images only
    HYBRID = "hybrid"  # page images + the PDF's embedded text layer (when present)
    PDF = "pdf"  # the raw PDF bytes, letting Gemini do its own PDF processing


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def _optional(value: str) -> str | None:
    return None if value.lower() in ("", "none", "off", "false") else value


@dataclass(frozen=True)
class Settings:
    api_key: str | None = field(default=None, repr=False)
    model: str = "gemini-3.5-flash-lite"
    # Served instead when the primary model is still unavailable (503/504/429) after
    # retries. Set INVOICE_FALLBACK_MODEL=none to disable.
    fallback_model: str | None = "gemini-3.1-flash-lite"
    thinking_level: str = "low"
    input_mode: InputMode = InputMode.HYBRID
    # One corrective retry when a validation check fails, then flag for review.
    max_validation_retries: int = 1
    # Transport-level retries for 408/429/5xx, with exponential backoff.
    api_attempts: int = 5
    request_timeout_s: float = 60.0
    # Re-read doubtful documents once and compare the two reads field by field.
    second_read: bool = True
    # A different model: two reads by the same model tend to share the same misreads.
    second_read_model: str | None = "gemini-3.1-flash-lite"
    # Detect sideways scans and rotate them upright before extraction.
    fix_orientation: bool = True
    # Date the stale-invoice check measures against (None: today). Pin it to reproduce a report.
    reference_date: date | None = None
    render_dpi: int = 170
    max_pages: int = 8
    max_file_mb: float = 20.0
    cache_dir: Path | None = PROJECT_ROOT / ".cache" / "llm"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            model=_env("INVOICE_MODEL", cls.model),
            fallback_model=_optional(_env("INVOICE_FALLBACK_MODEL", cls.fallback_model or "none")),
            second_read=_env("INVOICE_SECOND_READ", "on").lower()
            not in ("off", "false", "0", "none"),
            second_read_model=_optional(
                _env("INVOICE_SECOND_READ_MODEL", cls.second_read_model or "none")
            ),
            thinking_level=_env("INVOICE_THINKING_LEVEL", cls.thinking_level),
            input_mode=InputMode(_env("INVOICE_INPUT_MODE", cls.input_mode.value)),
            max_validation_retries=int(
                _env("INVOICE_MAX_RETRIES", str(cls.max_validation_retries))
            ),
            reference_date=date.fromisoformat(os.environ["INVOICE_REFERENCE_DATE"])
            if os.getenv("INVOICE_REFERENCE_DATE")
            else None,
            request_timeout_s=float(_env("INVOICE_REQUEST_TIMEOUT_S", str(cls.request_timeout_s))),
        )

    def with_overrides(self, **changes: object) -> Settings:
        return replace(self, **{k: v for k, v in changes.items() if v is not None})
