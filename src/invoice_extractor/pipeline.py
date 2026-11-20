"""The extraction pipeline.

file bytes
  -> load_document        (type sniffing, corrupt/empty/blank checks, render, text layer)
  -> fix_orientation      (sideways scans: deterministic detection + a tiny LLM tie-break)
  -> extract              (Gemini, JSON-schema constrained)
  -> project + validate   (exact output schema, arithmetic and field checks)
  -> corrective retry     (once, only for checks a careful re-read can fix)
  -> review decision      (needs_review flag + confidence score)
"""

from __future__ import annotations

import io
import json
import logging
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from . import prompts
from .config import InputMode, Settings
from .documents import (
    DocumentKind,
    LoadedDocument,
    PageImage,
    load_document,
    rotate_page,
    thumbnail,
)
from .errors import LLMOutputInvalid, PipelineError
from .llm import Blob, Content, GeminiClient
from .matching import compare_document
from .normalize import project
from .pricing import Usage
from .review import ReviewDecision, decide
from .schema import InvoiceExtraction, Legibility, ModelExtraction, model_response_schema
from .validation import Issue, Severity, errors_of, validate

log = logging.getLogger(__name__)

ORIENTATION_SCHEMA = {
    "type": "object",
    "properties": {"upright": {"type": "string", "enum": ["A", "B"]}},
    "required": ["upright"],
    "additionalProperties": False,
}


@dataclass
class Attempt:
    number: int
    issues: list[Issue]
    usage: Usage
    latency_ms: float
    served_by: str
    raw: ModelExtraction | None = None
    result: InvoiceExtraction | None = None
    response_text: str = ""
    cached: bool = False
    fallback_reason: str | None = None
    purpose: str = "extraction"  # extraction | correction | verification
    wait_ms: float = 0.0  # time actually spent waiting (near zero on a cache hit)

    @property
    def error_count(self) -> int:
        return len(errors_of(self.issues))

    @property
    def warning_count(self) -> int:
        return sum(issue.severity is Severity.WARNING for issue in self.issues)

    def summary(self) -> dict[str, Any]:
        return {
            "attempt": self.number,
            "purpose": self.purpose,
            "served_by": self.served_by,
            "errors": [issue.code for issue in errors_of(self.issues)],
            "latency_ms": round(self.latency_ms),
            "cached": self.cached,
            **self.usage.to_dict(),
        }


@dataclass
class ExtractionOutcome:
    document: LoadedDocument
    result: InvoiceExtraction
    raw: ModelExtraction
    issues: list[Issue]
    review: ReviewDecision
    attempts: list[Attempt]
    usage: Usage
    model: str
    input_mode: InputMode
    latency_ms: float
    notes: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "needs_review" if self.review.needs_review else "ok"

    @property
    def served_by(self) -> list[str]:
        return sorted({attempt.served_by for attempt in self.attempts})

    def output(self) -> dict[str, Any]:
        """The schema-exact JSON object."""
        return self.result.model_dump(mode="json")

    def meta(self) -> dict[str, Any]:
        """Everything else a reviewer or an auditor needs, kept out of the output file."""
        document = self.document
        return {
            "document": {
                "name": document.name,
                "sha256": document.sha256,
                "kind": document.kind.value,
                "pages": document.page_count,
                "has_text_layer": document.has_text_layer,
                "scanned": document.is_scanned,
                "rotations_applied": [page.rotated_by for page in document.pages],
                "warnings": document.warnings,
            },
            "status": self.status,
            "review": self.review.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
            "model": self.model,
            "served_by": self.served_by,
            "input_mode": self.input_mode.value,
            "classification": {
                "document_type": self.raw.document_type.value,
                "reason": self.raw.classification_reason,
                "legibility": self.raw.legibility.value,
            },
            "evidence": {
                "invoice_date_as_printed": self.raw.invoice_date_as_printed,
                "date_reasoning": self.raw.date_reasoning,
                "subtotal": self.raw.subtotal,
                "tax_lines": [line.model_dump() for line in self.raw.tax_lines or []],
                "unit_prices": [item.unit_price for item in self.raw.line_items or []],
                "uncertain_fields": self.raw.uncertain_fields,
            },
            "attempts": [attempt.summary() for attempt in self.attempts],
            "usage": self.usage.to_dict(),
            "latency_ms": round(self.latency_ms),
            "notes": self.notes,
        }


class InvoicePipeline:
    def __init__(
        self, settings: Settings | None = None, client: GeminiClient | None = None
    ) -> None:
        self.settings = settings or Settings.from_env()
        self._client = client

    @property
    def client(self) -> GeminiClient:
        # Created lazily so input validation works without an API key.
        if self._client is None:
            self._client = GeminiClient(self.settings)
        return self._client

    # --- public API ---------------------------------------------------------------------

    def extract_path(self, path: Path) -> ExtractionOutcome:
        return self.extract_bytes(path.read_bytes(), path.name)

    def extract_bytes(self, data: bytes, name: str) -> ExtractionOutcome:
        started = time.perf_counter()
        document = load_document(
            data,
            name,
            max_pages=self.settings.max_pages,
            dpi=self.settings.render_dpi,
            max_file_mb=self.settings.max_file_mb,
        )
        return self.extract_document(document, started=started)

    def extract_document(
        self, document: LoadedDocument, *, started: float | None = None
    ) -> ExtractionOutcome:
        started = started if started is not None else time.perf_counter()
        notes: list[str] = []
        usage, orient_wait, orient_model = (
            self._fix_orientation(document, notes)
            if self.settings.fix_orientation
            else (Usage(), 0.0, 0.0)
        )

        contents = self._contents(document)
        attempts: list[Attempt] = []
        for number in range(1, self.settings.max_validation_retries + 2):
            request = contents if number == 1 else self._correction_request(contents, attempts[-1])
            attempt = self._attempt(number, request)
            attempts.append(attempt)
            usage = usage + attempt.usage
            if not any(issue.retryable for issue in errors_of(attempt.issues)):
                break
            log.info(
                "%s: attempt %d failed checks %s",
                document.name,
                number,
                [issue.code for issue in errors_of(attempt.issues)],
            )

        best = self._best(attempts)
        if best.raw is None or best.result is None:
            raise LLMOutputInvalid(
                f"The model returned unparseable output on all {len(attempts)} attempts."
            )
        corrected = len(attempts) > 1
        if corrected:
            notes.append(
                f"Corrective re-read after: {', '.join(i.code for i in errors_of(attempts[0].issues))}; "
                f"kept attempt {best.number}."
            )

        verdict: list[Issue] = []
        if self.settings.second_read and self._doubtful(best):
            second = self._attempt(
                len(attempts) + 1,
                [*contents, prompts.SECOND_READ],
                model=self.settings.second_read_model,
                purpose="verification",
            )
            attempts.append(second)
            usage = usage + second.usage
            best, verdict = self._reconcile(best, second, notes)

        issues = list(best.issues) + verdict + self._document_issues(document)
        if best.fallback_reason:
            issues.append(
                Issue(
                    "fallback_model",
                    Severity.INFO,
                    f"Served by fallback model {best.served_by} ({best.fallback_reason}).",
                )
            )
        return ExtractionOutcome(
            document=document,
            result=best.result,
            raw=best.raw,
            issues=issues,
            review=decide(issues, retried=corrected),
            attempts=attempts,
            usage=usage,
            model=self.settings.model,
            input_mode=self.settings.input_mode,
            latency_ms=self._latency(started, attempts, orient_wait, orient_model),
            notes=notes,
        )

    # --- steps -------------------------------------------------------------------------

    def _contents(self, document: LoadedDocument) -> list[Content]:
        mode = self.settings.input_mode
        rotated = any(page.rotated_by for page in document.pages)
        if mode is InputMode.PDF and document.kind is DocumentKind.PDF and not rotated:
            media: list[Content] = [Blob(document.raw, "application/pdf")]
        else:
            media = [Blob(page.data, page.mime_type) for page in document.pages]
        include_text = mode is InputMode.HYBRID
        return [*media, prompts.user_prompt(document, include_text_layer=include_text)]

    def _correction_request(self, contents: list[Content], previous: Attempt) -> list[Content]:
        problems = [
            issue.message for issue in previous.issues if issue.severity is not Severity.INFO
        ]
        return [
            *contents,
            f"Your previous answer:\n{previous.response_text}",
            prompts.correction_prompt(problems),
        ]

    def _attempt(
        self,
        number: int,
        contents: list[Content],
        *,
        model: str | None = None,
        purpose: str = "extraction",
    ) -> Attempt:
        waited = time.perf_counter()
        response = self.client.generate_json(
            contents,
            schema=model_response_schema(),
            system_instruction=prompts.SYSTEM_INSTRUCTION,
            model=model,
        )
        wait_ms = (time.perf_counter() - waited) * 1000
        attempt = Attempt(
            number=number,
            issues=[],
            usage=response.usage,
            latency_ms=response.latency_ms,
            served_by=response.model,
            response_text=response.text,
            cached=response.cached,
            fallback_reason=response.fallback_reason,
            purpose=purpose if number == 1 or purpose != "extraction" else "correction",
            wait_ms=wait_ms,
        )
        try:
            raw = ModelExtraction.model_validate(json.loads(response.text))
            result = project(raw)
        except (json.JSONDecodeError, ValidationError) as exc:
            attempt.issues = [
                Issue(
                    "unparseable",
                    Severity.ERROR,
                    f"The model output did not match the schema: {str(exc)[:300]}",
                    retryable=True,
                )
            ]
            return attempt

        attempt.raw, attempt.result = raw, result
        attempt.issues = validate(result, raw, today=self.settings.reference_date)
        return attempt

    @staticmethod
    def _best(attempts: list[Attempt]) -> Attempt:
        # Fewest errors, then fewest warnings; prefer the later attempt on a tie.
        parsed = [attempt for attempt in attempts if attempt.raw is not None] or attempts
        return min(reversed(parsed), key=lambda a: (a.error_count, a.warning_count))

    @staticmethod
    def _doubtful(attempt: Attempt) -> bool:
        """Should this read be verified by an independent second read?

        Triggered by the model's own doubt (degraded legibility, uncertain fields) or by
        errors the corrective retry did not fix. Clean, confident, consistent reads (the
        common case) never pay for a second call.
        """
        raw = attempt.raw
        assert raw is not None
        return (
            raw.legibility is not Legibility.CLEAR
            or bool(raw.uncertain_fields)
            or attempt.error_count > 0
        )

    @staticmethod
    def _reconcile(
        first: Attempt, second: Attempt, notes: list[str]
    ) -> tuple[Attempt, list[Issue]]:
        """Compare two independent reads and decide what the reviewer should see.

        Agreement corroborates the read: the model's self-reported doubt no longer flags
        the document on its own. Disagreement flags the exact fields that differ, which
        is the only signal that catches a misread the arithmetic still balances around.
        """
        if second.raw is None or second.result is None:
            notes.append("Second read failed to parse; kept the first read.")
            return first, []
        assert first.result is not None

        fields, _ = compare_document(
            first.result.model_dump(mode="json"), second.result.model_dump(mode="json")
        )
        disagree = [result.field for result in fields if not result.correct]
        if not disagree:
            notes.append("An independent second read agreed on every field.")
            softened = [
                replace(
                    issue,
                    severity=Severity.INFO,
                    message=f"{issue.message} Corroborated by an independent second read.",
                )
                if issue.code in ("low_legibility", "model_uncertain")
                else issue
                for issue in first.issues
            ]
            first.issues = softened
            return first, [
                Issue(
                    "second_read_agrees",
                    Severity.INFO,
                    "An independent second read agreed on every field.",
                )
            ]

        chosen = second if second.error_count < first.error_count else first
        notes.append(f"Second read disagreed on {', '.join(disagree)}; kept read {chosen.number}.")
        return chosen, [
            Issue(
                "reads_disagree",
                Severity.WARNING,
                f"Two independent reads disagree on: {', '.join(disagree)}.",
                field=disagree[0] if len(disagree) == 1 else None,
            )
        ]

    @staticmethod
    def _document_issues(document: LoadedDocument) -> list[Issue]:
        issues = []
        for warning in document.warnings:
            severity = (
                Severity.WARNING
                if "only the first" in warning or "Low-resolution" in warning
                else Severity.INFO
            )
            issues.append(Issue("input_warning", severity, warning))
        for index, page in enumerate(document.pages, start=1):
            if page.rotated_by:
                issues.append(
                    Issue(
                        "orientation_corrected",
                        Severity.INFO,
                        f"Page {index} was lying sideways; rotated {page.rotated_by}° clockwise before reading.",
                    )
                )
            elif page.sideways:
                issues.append(
                    Issue(
                        "orientation_unresolved",
                        Severity.WARNING,
                        f"Page {index} looks sideways but its orientation could not be resolved.",
                    )
                )
        return issues

    def _fix_orientation(
        self, document: LoadedDocument, notes: list[str]
    ) -> tuple[Usage, float, float]:
        """Rotate pages that are lying on their side.

        Detection is deterministic (text-line projection profile, see documents.py) and
        free. Telling 90° from 270° from pixels alone proved unreliable, so for the rare
        sideways page we show the model both candidates as small thumbnails and let it
        pick the upright one: a ~600-token call instead of guessing.
        """
        usage, wait_ms, model_ms = Usage(), 0.0, 0.0
        for index, page in enumerate(document.pages):
            if not page.sideways:
                continue
            candidates = {"A": rotate_page(page, 90), "B": rotate_page(page, 270)}
            labelled: list[Content] = []
            for label, candidate in candidates.items():
                labelled += [
                    f"Image {label}:",
                    Blob(self._thumbnail_bytes(candidate), "image/jpeg"),
                ]
            try:
                waited = time.perf_counter()
                response = self.client.generate_json(
                    [*labelled, prompts.ORIENTATION_PROMPT],
                    schema=ORIENTATION_SCHEMA,
                    thinking_level="low",
                )
                wait_ms += (time.perf_counter() - waited) * 1000
                model_ms += response.latency_ms
                choice = json.loads(response.text)["upright"]
                usage = usage + response.usage
            except (PipelineError, json.JSONDecodeError, KeyError) as exc:
                notes.append(f"Orientation check failed for page {index + 1}: {exc}")
                continue
            document.replace_page(index, candidates[choice])
            notes.append(f"Page {index + 1} rotated {candidates[choice].rotated_by}° clockwise.")
        return usage, wait_ms, model_ms

    @staticmethod
    def _latency(
        started: float, attempts: list[Attempt], orient_wait: float, orient_model: float
    ) -> float:
        """Local processing time plus the latency each model call reported.

        Equal to wall-clock time for live calls; for a response replayed from the cache it
        reports what the call originally took, so cached eval re-runs keep honest timings.
        """
        wall = (time.perf_counter() - started) * 1000
        waited = orient_wait + sum(attempt.wait_ms for attempt in attempts)
        model = orient_model + sum(attempt.latency_ms for attempt in attempts)
        return max(0.0, wall - waited) + model

    @staticmethod
    def _thumbnail_bytes(page: PageImage) -> bytes:
        buffer = io.BytesIO()
        thumbnail(page).save(buffer, format="JPEG", quality=80)
        return buffer.getvalue()
