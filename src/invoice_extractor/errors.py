"""Typed failures with stable machine-readable codes.

Every failure the pipeline can hit maps to one of these, so the CLI, the batch runner
and the HTTP API can all report it the same way instead of leaking stack traces.
"""

from __future__ import annotations


class PipelineError(Exception):
    """Base class. ``code`` is stable and safe to show to API clients."""

    code = "pipeline_error"
    http_status = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


# --- Bad inputs (the caller sent something we cannot process) -------------------------


class InputError(PipelineError):
    code = "invalid_input"
    http_status = 422


class UnsupportedFileType(InputError):
    code = "unsupported_file_type"
    http_status = 415


class CorruptFile(InputError):
    code = "corrupt_file"


class EncryptedPdf(InputError):
    code = "encrypted_pdf"


class EmptyDocument(InputError):
    code = "empty_document"


class FileTooLarge(InputError):
    code = "file_too_large"
    http_status = 413


# --- Upstream / model failures --------------------------------------------------------


class ConfigurationError(PipelineError):
    code = "not_configured"
    http_status = 503


class LLMUnavailable(PipelineError):
    """Timeouts, rate limits or 5xx that survived every retry."""

    code = "llm_unavailable"
    http_status = 503


class LLMRejected(PipelineError):
    """The provider refused the request (bad request, safety block, auth)."""

    code = "llm_rejected"
    http_status = 502


class LLMOutputInvalid(PipelineError):
    """The model kept returning output we could not parse into the schema."""

    code = "llm_output_invalid"
    http_status = 502
