"""Run the pipeline over many files concurrently and write the results to disk."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import PipelineError
from .pipeline import ExtractionOutcome, InvoicePipeline
from .pricing import Usage

log = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


@dataclass
class BatchItem:
    path: Path
    outcome: ExtractionOutcome | None = None
    error: PipelineError | None = None

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def status(self) -> str:
        return self.outcome.status if self.outcome else f"error:{self.error.code}"  # type: ignore[union-attr]


def collect_inputs(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files += sorted(p for p in path.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES)
        else:
            files.append(path)
    return files


def run_batch(
    pipeline: InvoicePipeline,
    files: list[Path],
    *,
    workers: int = 4,
    on_done: Callable[[BatchItem], None] | None = None,
    extract: Callable[[Path], ExtractionOutcome] | None = None,
) -> list[BatchItem]:
    """Extract every file; ``extract`` overrides how a path becomes an outcome (stress tests)."""
    extract = extract or pipeline.extract_path

    def work(path: Path) -> BatchItem:
        item = BatchItem(path)
        try:
            item.outcome = extract(path)
        except PipelineError as exc:
            item.error = exc
        except Exception as exc:  # never let one document kill the batch
            log.exception("unexpected failure on %s", path.name)
            item.error = PipelineError(f"Unexpected error: {type(exc).__name__}: {exc}")
        if on_done:
            on_done(item)
        return item

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(work, files))


def write_outputs(items: list[BatchItem], out_dir: Path) -> dict[str, Any]:
    """Write ``<name>.json`` (schema-exact) plus ``_meta/<name>.json`` for each item."""
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_dir = out_dir / "_meta"
    meta_dir.mkdir(exist_ok=True)

    total = Usage()
    documents = []
    for item in items:
        if item.outcome:
            _write_json(out_dir / f"{item.name}.json", item.outcome.output())
            _write_json(meta_dir / f"{item.name}.json", item.outcome.meta())
            total = total + item.outcome.usage
            documents.append(
                {
                    "name": item.name,
                    "file": item.path.name,
                    "status": item.outcome.status,
                    "is_invoice": item.outcome.result.is_invoice,
                    "confidence": item.outcome.review.confidence,
                    "review_reasons": item.outcome.review.reasons,
                    "cost_usd": round(item.outcome.usage.cost_usd, 6),
                    "latency_ms": round(item.outcome.latency_ms),
                }
            )
        else:
            assert item.error is not None
            _write_json(
                meta_dir / f"{item.name}.json", {"status": "error", "error": item.error.to_dict()}
            )
            documents.append(
                {
                    "name": item.name,
                    "file": item.path.name,
                    "status": "error",
                    "error": item.error.to_dict(),
                }
            )

    succeeded = [item for item in items if item.outcome]
    summary = {
        "documents": len(items),
        "succeeded": len(succeeded),
        "needs_review": sum(item.outcome.review.needs_review for item in succeeded),  # type: ignore[union-attr]
        "errors": len(items) - len(succeeded),
        "usage": total.to_dict(),
        "avg_cost_usd": round(total.cost_usd / len(succeeded), 6) if succeeded else 0.0,
        "items": documents,
    }
    _write_json(out_dir / "_summary.json", summary)
    return summary


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
