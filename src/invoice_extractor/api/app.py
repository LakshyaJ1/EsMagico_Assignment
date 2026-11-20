"""HTTP API and static web UI.

    uv run python serve.py            # http://127.0.0.1:8000

Read-only endpoints (documents, evaluations, validation) work without an API key so the
sample pack and the measured results can be browsed offline. Only extraction calls Gemini.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Annotated, Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from ..config import PROJECT_ROOT, PROMPT_VERSION, Settings
from ..documents import LoadedDocument, load_document, rotate_page
from ..errors import PipelineError
from ..matching import compare_document
from ..normalize import project
from ..pipeline import ExtractionOutcome, InvoicePipeline
from ..pricing import PRICES_AS_OF, PRICING_SOURCE, price_for
from ..review import decide
from ..schema import InvoiceExtraction, ModelExtraction
from ..validation import Issue, Severity, validate

log = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
EVAL_DIRS = [PROJECT_ROOT / "eval_results", PROJECT_ROOT / "eval_results" / "experiments"]
WEB_DIST = PROJECT_ROOT / "web" / "dist"
SAMPLE_SETS = ("labelled", "unlabelled")
CODE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_UPLOADS_IN_MEMORY = 24

app = FastAPI(
    title="Invoice Extractor",
    version="1.0.0",
    description="Extract validated invoice JSON from PDFs and images, with review flags and cost.",
)


@app.exception_handler(PipelineError)
async def pipeline_error_handler(_: Request, exc: PipelineError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content={"error": exc.to_dict()})


# --------------------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------------------


class _UploadStore:
    """Keeps the most recent uploads in memory so their pages can be previewed."""

    def __init__(self, capacity: int) -> None:
        self._items: OrderedDict[str, LoadedDocument] = OrderedDict()
        self._capacity = capacity
        self._lock = Lock()

    def put(self, document: LoadedDocument) -> str:
        key = uuid.uuid4().hex[:12]
        with self._lock:
            self._items[key] = document
            while len(self._items) > self._capacity:
                self._items.popitem(last=False)
        return key

    def get(self, key: str) -> LoadedDocument:
        with self._lock:
            document = self._items.get(key)
        if document is None:
            raise HTTPException(404, "Upload not found (uploads are kept in memory only).")
        return document


uploads = _UploadStore(MAX_UPLOADS_IN_MEMORY)


@lru_cache(maxsize=1)
def _pipeline() -> InvoicePipeline:
    return InvoicePipeline(Settings.from_env())


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _sample_files() -> dict[str, tuple[str, Path]]:
    files: dict[str, tuple[str, Path]] = {}
    for sample_set in SAMPLE_SETS:
        folder = DATA_DIR / sample_set
        if folder.exists():
            for path in sorted(folder.iterdir()):
                if path.suffix.lower() in (".pdf", ".jpg", ".jpeg", ".png"):
                    files[path.stem] = (sample_set, path)
    return files


def _sample(code: str) -> tuple[str, Path]:
    if not CODE.match(code):
        raise HTTPException(400, "Invalid document code.")
    found = _sample_files().get(code)
    if found is None:
        raise HTTPException(404, f"No sample document '{code}'. Run scripts/fetch_data.py.")
    return found


@lru_cache(maxsize=32)
def _sample_document(code: str) -> LoadedDocument:
    _, path = _sample(code)
    document = load_document(path.read_bytes(), path.name)
    # Show pages the way the pipeline read them (sideways scans rotated upright).
    meta = _read_json(OUTPUTS_DIR / "_meta" / f"{code}.json") or {}
    rotations = meta.get("document", {}).get("rotations_applied", [])
    for index, degrees in enumerate(rotations[: len(document.pages)]):
        if degrees:
            document.replace_page(index, rotate_page(document.pages[index], degrees))
    return document


def _pages(document: LoadedDocument, base_url: str) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "width": page.width,
            "height": page.height,
            "url": f"{base_url}/pages/{index}",
        }
        for index, page in enumerate(document.pages)
    ]


def _page_response(document: LoadedDocument, index: int) -> Response:
    if not 0 <= index < len(document.pages):
        raise HTTPException(404, "Page out of range.")
    page = document.pages[index]
    return Response(page.data, media_type=page.mime_type, headers={"Cache-Control": "max-age=3600"})


def _comparison(expected: dict | None, predicted: dict | None) -> list[dict[str, Any]] | None:
    if expected is None or predicted is None:
        return None
    results, _ = compare_document(expected, predicted)
    return [
        {
            "field": r.field,
            "correct": r.correct,
            "expected": r.expected,
            "predicted": r.predicted,
            "detail": r.detail,
        }
        for r in results
    ]


def _outcome_payload(outcome: ExtractionOutcome) -> dict[str, Any]:
    return {"result": outcome.output(), "meta": outcome.meta()}


# --------------------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, Any]:
    settings = Settings.from_env()
    price = price_for(settings.model)
    return {
        "status": "ok",
        "api_key_configured": bool(settings.api_key),
        "model": settings.model,
        "fallback_model": settings.fallback_model,
        "input_mode": settings.input_mode.value,
        "thinking_level": settings.thinking_level,
        "prompt_version": PROMPT_VERSION,
        "price_per_m_tokens": {"input": price.input_per_m, "output": price.output_per_m}
        if price
        else None,
        "prices_as_of": PRICES_AS_OF,
        "pricing_source": PRICING_SOURCE,
        "sample_pack_present": bool(_sample_files()),
    }


@app.get("/api/documents")
def list_documents() -> list[dict[str, Any]]:
    rows = []
    for code, (sample_set, path) in _sample_files().items():
        result = _read_json(OUTPUTS_DIR / f"{code}.json")
        meta = _read_json(OUTPUTS_DIR / "_meta" / f"{code}.json")
        truth = (
            _read_json(DATA_DIR / "labelled" / f"{code}.json") if sample_set == "labelled" else None
        )
        comparison = _comparison(truth, result)
        rows.append(
            {
                "code": code,
                "file_name": path.name,
                "set": sample_set,
                "kind": "photo"
                if path.suffix.lower() in (".jpg", ".jpeg", ".png")
                else ("scan" if meta and meta.get("document", {}).get("scanned") else "digital"),
                "result": result,
                "status": (meta or {}).get("status", "not_run"),
                "confidence": (meta or {}).get("review", {}).get("confidence"),
                "review_reasons": (meta or {}).get("review", {}).get("reasons", []),
                "cost_usd": (meta or {}).get("usage", {}).get("cost_usd"),
                "latency_ms": (meta or {}).get("latency_ms"),
                "fields_correct": sum(c["correct"] for c in comparison) if comparison else None,
                "fields_total": len(comparison) if comparison else None,
            }
        )
    return rows


@app.get("/api/documents/{code}")
def get_document(code: str) -> dict[str, Any]:
    sample_set, path = _sample(code)
    result = _read_json(OUTPUTS_DIR / f"{code}.json")
    truth = _read_json(DATA_DIR / "labelled" / f"{code}.json") if sample_set == "labelled" else None
    return {
        "id": code,
        "source": "sample",
        "file_name": path.name,
        "set": sample_set,
        "pages": _pages(_sample_document(code), f"/api/documents/{code}"),
        "result": result,
        "meta": _read_json(OUTPUTS_DIR / "_meta" / f"{code}.json"),
        "ground_truth": truth,
        "comparison": _comparison(truth, result),
    }


@app.get("/api/documents/{code}/pages/{index}")
def get_document_page(code: str, index: int) -> Response:
    return _page_response(_sample_document(code), index)


@app.get("/api/documents/{code}/file")
def get_document_file(code: str) -> FileResponse:
    _, path = _sample(code)
    return FileResponse(path)


@app.post("/api/documents/{code}/extract")
def reextract_document(code: str) -> dict[str, Any]:
    """Run a fresh live extraction on a sample (does not overwrite outputs/)."""
    sample_set, path = _sample(code)
    outcome = _pipeline().extract_bytes(path.read_bytes(), path.name)
    truth = _read_json(DATA_DIR / "labelled" / f"{code}.json") if sample_set == "labelled" else None
    payload = _outcome_payload(outcome)
    return {
        **get_document(code),
        **payload,
        "comparison": _comparison(truth, payload["result"]),
    }


@app.post("/api/extract")
async def extract_upload(file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    settings = _pipeline().settings
    data = await file.read(int(settings.max_file_mb * 1024 * 1024) + 1)
    name = Path(file.filename or "upload").name
    document = load_document(
        data,
        name,
        max_pages=settings.max_pages,
        dpi=settings.render_dpi,
        max_file_mb=settings.max_file_mb,
    )
    outcome = _pipeline().extract_document(document)
    key = uploads.put(outcome.document)
    return {
        "id": key,
        "source": "upload",
        "file_name": name,
        "set": None,
        "pages": _pages(outcome.document, f"/api/uploads/{key}"),
        **_outcome_payload(outcome),
        "ground_truth": None,
        "comparison": None,
    }


@app.get("/api/uploads/{key}/pages/{index}")
def get_upload_page(key: str, index: int) -> Response:
    return _page_response(uploads.get(key), index)


class ValidateRequest(BaseModel):
    result: dict[str, Any]
    evidence: dict[str, Any] | None = None
    classification: dict[str, Any] | None = None


@app.post("/api/validate")
def validate_result(request: ValidateRequest) -> dict[str, Any]:
    """Re-run every check on a (possibly hand-corrected) result. No API key needed."""
    try:
        result = InvoiceExtraction.model_validate(request.result)
    except ValidationError as exc:
        issues = [
            Issue("schema_invalid", Severity.ERROR, f"{'/'.join(map(str, e['loc']))}: {e['msg']}")
            for e in exc.errors()
        ]
        return {
            "result": None,
            "issues": [i.to_dict() for i in issues],
            "review": decide(issues, retried=False).to_dict(),
        }

    raw = _model_view(result, request.evidence or {}, request.classification or {})
    issues = validate(project(raw), raw, today=Settings.from_env().reference_date) if raw else []
    return {
        "result": project(raw).model_dump(mode="json") if raw else result.model_dump(mode="json"),
        "issues": [issue.to_dict() for issue in issues],
        "review": decide(issues, retried=False).to_dict(),
    }


def _model_view(
    result: InvoiceExtraction, evidence: dict[str, Any], classification: dict[str, Any]
) -> ModelExtraction | None:
    unit_prices = evidence.get("unit_prices") or []
    items = [
        {**item.model_dump(), "unit_price": unit_prices[i] if i < len(unit_prices) else None}
        for i, item in enumerate(result.line_items or [])
    ]
    try:
        return ModelExtraction.model_validate(
            {
                **result.model_dump(),
                "document_type": "invoice"
                if result.is_invoice
                else classification.get("document_type", "other"),
                "classification_reason": classification.get("reason", ""),
                # A human has looked at the page; the model's legibility doubt no longer applies.
                "legibility": "clear",
                "line_items": items if result.line_items is not None else None,
                "invoice_date_as_printed": evidence.get("invoice_date_as_printed"),
                "date_reasoning": evidence.get("date_reasoning"),
                "subtotal": evidence.get("subtotal"),
                "tax_lines": evidence.get("tax_lines") or None,
                "uncertain_fields": [],
            }
        )
    except ValidationError:
        return None


@app.get("/api/evaluations")
def list_evaluations() -> list[dict[str, Any]]:
    reports = []
    for folder in EVAL_DIRS:
        for path in sorted(folder.glob("*.json")) if folder.exists() else []:
            report = _read_json(path)
            if not isinstance(report, dict) or "field_accuracy" not in report:
                continue
            reports.append(
                {
                    "tag": path.stem,
                    "group": "experiments" if folder.name == "experiments" else "main",
                    "run": report["run"],
                    "all_fields": report["field_accuracy"]["all_fields"],
                    "field_accuracy": report["field_accuracy"],
                    "line_items": report["line_items"],
                    "review": report["review"],
                    "cost": report.get("cost", {}),
                    "failed": sum(1 for doc in report["documents"] if doc["error"]),
                }
            )
    return reports


@app.get("/api/evaluations/{tag}")
def get_evaluation(tag: str) -> dict[str, Any]:
    if not CODE.match(tag.replace(".", "_")):
        raise HTTPException(400, "Invalid report name.")
    for folder in EVAL_DIRS:
        path = folder / f"{tag}.json"
        if path.exists():
            return _read_json(path)
    raise HTTPException(404, f"No evaluation report '{tag}'.")


# --------------------------------------------------------------------------------------
# Web UI
# --------------------------------------------------------------------------------------

if (WEB_DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Unknown API endpoint.")
        candidate = (WEB_DIST / path).resolve()
        if path and candidate.is_file() and WEB_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")
else:

    @app.get("/", include_in_schema=False)
    def missing_ui() -> Response:
        return Response(
            "<h1>Invoice Extractor API</h1><p>The web UI is not built yet. Run "
            "<code>cd web &amp;&amp; npm install &amp;&amp; npm run build</code>, then restart. "
            "API docs: <a href='/docs'>/docs</a></p>",
            media_type="text/html",
        )
