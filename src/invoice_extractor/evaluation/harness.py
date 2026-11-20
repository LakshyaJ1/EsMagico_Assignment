"""Score extractions against ground truth.

Predictions come either from a live run of the pipeline or from a directory of saved
outputs (``outputs/`` holds ``<name>.json`` plus ``_meta/<name>.json``), so a run can be
re-scored offline without spending anything.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..batch import BatchItem
from ..matching import FIELDS, FieldResult, LineItemComparison, compare_document


@dataclass
class DocEval:
    name: str
    source: str  # "digital", "scan" or "photo"
    expected: dict[str, Any]
    predicted: dict[str, Any] | None
    meta: dict[str, Any] | None
    fields: list[FieldResult] = field(default_factory=list)
    line_items: LineItemComparison | None = None
    error: str | None = None

    @property
    def wrong_fields(self) -> list[str]:
        if self.predicted is None:
            return list(FIELDS)
        return [result.field for result in self.fields if not result.correct]

    @property
    def flagged(self) -> bool:
        # A pipeline error is never silent: it counts as flagged.
        return self.predicted is None or bool(self.meta and self.meta["review"]["needs_review"])

    @property
    def is_invoice(self) -> bool:
        return bool(self.expected.get("is_invoice"))


def _source_kind(meta: dict[str, Any] | None, path: Path) -> str:
    if path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        return "photo"
    if meta and meta.get("document", {}).get("scanned"):
        return "scan"
    return "digital"


def evaluate_document(
    name: str,
    path: Path,
    expected: dict,
    predicted: dict | None,
    meta: dict | None,
    error: str | None = None,
) -> DocEval:
    doc = DocEval(
        name=name,
        source=_source_kind(meta, path),
        expected=expected,
        predicted=predicted,
        meta=meta,
        error=error,
    )
    if predicted is not None:
        doc.fields, doc.line_items = compare_document(expected, predicted)
    return doc


def from_batch(items: list[BatchItem], truth_dir: Path) -> list[DocEval]:
    docs = []
    for item in items:
        expected = json.loads((truth_dir / f"{item.name}.json").read_text(encoding="utf-8"))
        if item.outcome:
            docs.append(
                evaluate_document(
                    item.name, item.path, expected, item.outcome.output(), item.outcome.meta()
                )
            )
        else:
            assert item.error is not None
            docs.append(
                evaluate_document(
                    item.name,
                    item.path,
                    expected,
                    None,
                    None,
                    f"{item.error.code}: {item.error.message}",
                )
            )
    return docs


def from_predictions(
    predictions_dir: Path, truth_dir: Path, documents: list[Path]
) -> list[DocEval]:
    docs = []
    for path in documents:
        expected = json.loads((truth_dir / f"{path.stem}.json").read_text(encoding="utf-8"))
        prediction_file = predictions_dir / f"{path.stem}.json"
        meta_file = predictions_dir / "_meta" / f"{path.stem}.json"
        meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else None
        if prediction_file.exists():
            predicted = json.loads(prediction_file.read_text(encoding="utf-8"))
            docs.append(evaluate_document(path.stem, path, expected, predicted, meta))
        else:
            reason = (meta or {}).get("error", {}).get("message", "no prediction file")
            docs.append(evaluate_document(path.stem, path, expected, None, meta, reason))
    return docs


# --------------------------------------------------------------------------------------
# Aggregates
# --------------------------------------------------------------------------------------


def field_accuracy(docs: list[DocEval]) -> dict[str, dict[str, Any]]:
    table: dict[str, dict[str, Any]] = {}
    invoices = [doc for doc in docs if doc.is_invoice]
    for name in FIELDS:

        def correct(subset: list[DocEval], name: str = name) -> int:
            return sum(
                1 for doc in subset if doc.predicted is not None and name not in doc.wrong_fields
            )

        table[name] = {
            "correct": correct(docs),
            "total": len(docs),
            "accuracy": correct(docs) / len(docs) if docs else 0.0,
            "invoices_correct": correct(invoices),
            "invoices_total": len(invoices),
        }
    perfect = sum(1 for doc in docs if doc.predicted is not None and not doc.wrong_fields)
    table["all_fields"] = {
        "correct": perfect,
        "total": len(docs),
        "accuracy": perfect / len(docs) if docs else 0.0,
        "invoices_correct": sum(
            1 for doc in invoices if doc.predicted is not None and not doc.wrong_fields
        ),
        "invoices_total": len(invoices),
    }
    return table


def line_item_metrics(docs: list[DocEval]) -> dict[str, Any]:
    comparisons = [doc.line_items for doc in docs if doc.line_items is not None]
    expected = sum(len(doc.expected.get("line_items") or []) for doc in docs)
    predicted = sum(len(doc.predicted.get("line_items") or []) for doc in docs if doc.predicted)
    matched = sum(c.matched_rows for c in comparisons)
    aligned = sum(c.aligned for c in comparisons)
    precision = matched / predicted if predicted else 0.0
    recall = matched / expected if expected else 0.0
    return {
        "expected_rows": expected,
        "predicted_rows": predicted,
        "matched_rows": matched,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "description_accuracy": sum(c.description_ok for c in comparisons) / aligned
        if aligned
        else 0.0,
        "quantity_accuracy": sum(c.quantity_ok for c in comparisons) / aligned if aligned else 0.0,
        "amount_accuracy": sum(c.amount_ok for c in comparisons) / aligned if aligned else 0.0,
    }


def review_analysis(docs: list[DocEval]) -> dict[str, Any]:
    """Does ``needs_review`` point at the documents that actually contain errors?"""
    flagged = [doc for doc in docs if doc.flagged]
    with_errors = [doc for doc in docs if doc.wrong_fields]
    field_errors = sum(len(doc.wrong_fields) for doc in docs)
    field_errors_in_flagged = sum(len(doc.wrong_fields) for doc in flagged)
    caught = [doc for doc in with_errors if doc.flagged]
    return {
        "documents": len(docs),
        "flagged": len(flagged),
        "documents_with_errors": len(with_errors),
        "errors_caught": len(caught),
        "false_alarms": len([doc for doc in flagged if not doc.wrong_fields]),
        "missed": [doc.name for doc in with_errors if not doc.flagged],
        "recall": len(caught) / len(with_errors) if with_errors else None,
        "precision": len(caught) / len(flagged) if flagged else None,
        "field_errors": field_errors,
        "field_errors_in_flagged": field_errors_in_flagged,
        "share_of_errors_in_flagged": field_errors_in_flagged / field_errors
        if field_errors
        else None,
        "confidence_with_errors": _mean(
            [
                doc.meta["review"]["confidence"]
                for doc in with_errors
                if doc.meta and "review" in doc.meta
            ]
        ),
        "confidence_without_errors": _mean(
            [
                doc.meta["review"]["confidence"]
                for doc in docs
                if not doc.wrong_fields and doc.meta and "review" in doc.meta
            ]
        ),
    }


def cost_summary(docs: list[DocEval]) -> dict[str, Any]:
    usages = [doc.meta["usage"] for doc in docs if doc.meta and "usage" in doc.meta]
    latencies = [doc.meta["latency_ms"] for doc in docs if doc.meta and "latency_ms" in doc.meta]
    if not usages:
        return {}
    n = len(usages)

    def avg(key: str) -> float:
        return sum(u[key] for u in usages) / n

    by_source: dict[str, list[float]] = {}
    for doc in docs:
        if doc.meta and "usage" in doc.meta:
            by_source.setdefault(doc.source, []).append(doc.meta["usage"]["cost_usd"])
    return {
        "documents": n,
        "avg_input_tokens": avg("input_tokens"),
        "avg_image_tokens": avg("image_tokens"),
        "avg_output_tokens": avg("output_tokens"),
        "avg_thinking_tokens": avg("thinking_tokens"),
        "avg_calls": avg("calls"),
        "avg_cost_usd": avg("cost_usd"),
        "total_cost_usd": sum(u["cost_usd"] for u in usages),
        "cost_per_1000_docs_usd": avg("cost_usd") * 1000,
        "avg_cost_by_source": {k: sum(v) / len(v) for k, v in sorted(by_source.items())},
        "avg_latency_ms": statistics.mean(latencies) if latencies else None,
        "max_latency_ms": max(latencies) if latencies else None,
        "all_priced": all(u.get("priced", True) for u in usages),
    }


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def build_report(docs: list[DocEval], run: dict[str, Any]) -> dict[str, Any]:
    return {
        "run": {**run, "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds")},
        "field_accuracy": field_accuracy(docs),
        "line_items": line_item_metrics(docs),
        "review": review_analysis(docs),
        "cost": cost_summary(docs),
        "documents": [
            {
                "name": doc.name,
                "source": doc.source,
                "is_invoice": doc.is_invoice,
                "error": doc.error,
                "flagged": doc.flagged,
                "confidence": doc.meta["review"]["confidence"]
                if doc.meta and "review" in doc.meta
                else None,
                "review_reasons": doc.meta["review"]["reasons"]
                if doc.meta and "review" in doc.meta
                else [],
                "wrong_fields": doc.wrong_fields,
                "fields": [
                    {
                        "field": r.field,
                        "correct": r.correct,
                        "expected": r.expected,
                        "predicted": r.predicted,
                        "detail": r.detail,
                    }
                    for r in doc.fields
                ],
                "cost_usd": doc.meta["usage"]["cost_usd"]
                if doc.meta and "usage" in doc.meta
                else None,
                "attempts": len(doc.meta.get("attempts", [])) if doc.meta else 0,
            }
            for doc in docs
        ],
    }
