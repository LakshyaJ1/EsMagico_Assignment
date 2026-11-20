"""Render an eval report as terminal tables (rich) and as Markdown."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

from ..matching import FIELDS

SHORT = {
    "is_invoice": "is_inv",
    "vendor": "vendor",
    "invoice_number": "inv_no",
    "invoice_date": "date",
    "currency": "cur",
    "line_items": "lines",
    "tax_total": "tax",
    "total": "total",
}


def _pct(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator} ({numerator / denominator:.0%})" if denominator else "-"


def _ratio(value: float | None) -> str:
    return "-" if value is None else f"{value:.0%}"


def _money(value: float | None, digits: int = 4) -> str:
    return "-" if value is None else f"${value:.{digits}f}"


def _truncate(value: Any, width: int = 48) -> str:
    text = "null" if value is None else str(value)
    return text if len(text) <= width else text[: width - 1] + "…"


def print_report(report: dict[str, Any], console: Console | None = None) -> None:
    console = console or Console(stderr=False)
    run = report["run"]
    console.print(
        f"\n[bold]Eval[/bold] · model [cyan]{run['model']}[/cyan] · input {run['input_mode']} · "
        f"thinking {run['thinking_level']} · prompt {run['prompt_version']} · {run['documents']} documents"
        + (
            f" · [magenta]perturbation {run['perturbation']}[/magenta]"
            if run.get("perturbation")
            else ""
        )
        + ("" if run.get("orientation_fix", True) else " · orientation fix OFF")
    )

    grid = Table(title="Per-document results (✓ correct, ✗ wrong)", title_justify="left")
    grid.add_column("doc")
    grid.add_column("source")
    for name in FIELDS:
        grid.add_column(SHORT[name], justify="center")
    grid.add_column("flagged", justify="center")
    grid.add_column("conf", justify="right")
    grid.add_column("cost", justify="right")
    for doc in report["documents"]:
        if doc["error"]:
            marks = ["[red]ERR[/red]"] * len(FIELDS)
        else:
            marks = ["[green]✓[/green]" if f["correct"] else "[red]✗[/red]" for f in doc["fields"]]
        grid.add_row(
            doc["name"],
            doc["source"],
            *marks,
            "[yellow]yes[/yellow]" if doc["flagged"] else "no",
            "-" if doc["confidence"] is None else f"{doc['confidence']:.2f}",
            _money(doc["cost_usd"]),
        )
    console.print(grid)

    accuracy = Table(title="Field-level accuracy", title_justify="left")
    accuracy.add_column("field")
    accuracy.add_column("all labelled docs", justify="right")
    accuracy.add_column("invoices only", justify="right")
    for name, row in report["field_accuracy"].items():
        accuracy.add_row(
            name if name != "all_fields" else "[bold]all 8 fields correct[/bold]",
            _pct(row["correct"], row["total"]),
            _pct(row["invoices_correct"], row["invoices_total"]),
        )
    console.print(accuracy)

    items = report["line_items"]
    console.print(
        f"Line items: {items['matched_rows']}/{items['expected_rows']} rows fully correct · "
        f"precision {_ratio(items['precision'])} · recall {_ratio(items['recall'])} · F1 {_ratio(items['f1'])} · "
        f"description {_ratio(items['description_accuracy'])} · quantity {_ratio(items['quantity_accuracy'])} · "
        f"amount {_ratio(items['amount_accuracy'])}"
    )

    errors = [
        (doc["name"], f) for doc in report["documents"] for f in doc["fields"] if not f["correct"]
    ]
    if errors:
        table = Table(title="Errors", title_justify="left")
        for column in ("doc", "field", "expected", "predicted", "detail"):
            table.add_column(column)
        for name, f in errors:
            table.add_row(
                name, f["field"], _truncate(f["expected"]), _truncate(f["predicted"]), f["detail"]
            )
        console.print(table)
    for doc in report["documents"]:
        if doc["error"]:
            console.print(f"[red]{doc['name']} failed:[/red] {doc['error']}")

    review = report["review"]
    console.print(
        f"\n[bold]Review flag[/bold]: {review['flagged']}/{review['documents']} flagged · "
        f"caught {review['errors_caught']}/{review['documents_with_errors']} documents with errors · "
        f"{review['false_alarms']} false alarm(s) · flagged docs hold "
        f"{review['field_errors_in_flagged']}/{review['field_errors']} field errors"
        + (f" · missed: {', '.join(review['missed'])}" if review["missed"] else "")
    )

    cost = report["cost"]
    if cost:
        console.print(
            f"[bold]Cost[/bold]: avg {_money(cost['avg_cost_usd'], 5)}/doc · "
            f"{cost['avg_input_tokens']:.0f} in ({cost['avg_image_tokens']:.0f} image) / "
            f"{cost['avg_output_tokens']:.0f} out / {cost['avg_thinking_tokens']:.0f} thinking tokens · "
            f"{cost['avg_calls']:.2f} calls/doc · total {_money(cost['total_cost_usd'])} · "
            f"≈ ${cost['cost_per_1000_docs_usd']:.2f} per 1,000 docs · "
            f"avg latency {cost['avg_latency_ms'] / 1000:.1f}s\n"
        )


def to_markdown(report: dict[str, Any]) -> str:
    run = report["run"]
    lines = [
        f"# Eval results: {run['model']}",
        "",
        f"- Evaluated: {run['evaluated_at']}",
        f"- Model: `{run['model']}` · input mode `{run['input_mode']}` · thinking `{run['thinking_level']}` "
        f"· prompt `{run['prompt_version']}`",
        f"- Documents: {run['documents']} labelled",
        "",
        "## Field-level accuracy",
        "",
        "| Field | All labelled docs | Invoices only |",
        "|---|---|---|",
    ]
    for name, row in report["field_accuracy"].items():
        label = "**All 8 fields correct**" if name == "all_fields" else f"`{name}`"
        lines.append(
            f"| {label} | {_pct(row['correct'], row['total'])} | "
            f"{_pct(row['invoices_correct'], row['invoices_total'])} |"
        )

    items = report["line_items"]
    lines += [
        "",
        "## Line items (row level)",
        "",
        "| Rows expected | Rows predicted | Fully correct | Precision | Recall | F1 | Description | Quantity | Amount |",
        "|---|---|---|---|---|---|---|---|---|",
        f"| {items['expected_rows']} | {items['predicted_rows']} | {items['matched_rows']} | "
        f"{_ratio(items['precision'])} | {_ratio(items['recall'])} | {_ratio(items['f1'])} | "
        f"{_ratio(items['description_accuracy'])} | {_ratio(items['quantity_accuracy'])} | "
        f"{_ratio(items['amount_accuracy'])} |",
        "",
        "## Per document",
        "",
        "| Doc | Source | "
        + " | ".join(SHORT[f] for f in FIELDS)
        + " | Flagged | Confidence | Cost |",
        "|---|---|" + "---|" * len(FIELDS) + "---|---|---|",
    ]
    for doc in report["documents"]:
        marks = (
            ["ERR"] * len(FIELDS)
            if doc["error"]
            else ["✓" if f["correct"] else "✗" for f in doc["fields"]]
        )
        confidence = "-" if doc["confidence"] is None else f"{doc['confidence']:.2f}"
        lines.append(
            f"| {doc['name']} | {doc['source']} | "
            + " | ".join(marks)
            + f" | {'yes' if doc['flagged'] else 'no'} | {confidence} | {_money(doc['cost_usd'])} |"
        )

    errors = [
        (doc["name"], f) for doc in report["documents"] for f in doc["fields"] if not f["correct"]
    ]
    lines += ["", "## Errors", ""]
    if errors:
        lines += ["| Doc | Field | Expected | Predicted | Detail |", "|---|---|---|---|---|"]
        for name, f in errors:
            lines.append(
                f"| {name} | `{f['field']}` | {_truncate(f['expected'], 60)} | "
                f"{_truncate(f['predicted'], 60)} | {f['detail']} |"
            )
    else:
        lines.append("No field errors.")

    review = report["review"]
    cost = report["cost"]
    lines += [
        "",
        "## Review flag vs. actual errors",
        "",
        f"- Flagged: {review['flagged']}/{review['documents']}",
        f"- Documents with at least one wrong field: {review['documents_with_errors']}; "
        f"flagged: {review['errors_caught']} (recall {_ratio(review['recall'])})",
        f"- Flagged documents with no errors (false alarms): {review['false_alarms']} "
        f"(precision {_ratio(review['precision'])})",
        f"- Share of all field errors that sit in flagged documents: "
        f"{review['field_errors_in_flagged']}/{review['field_errors']} ({_ratio(review['share_of_errors_in_flagged'])})",
        f"- Missed (wrong but not flagged): {', '.join(review['missed']) or 'none'}",
    ]
    if cost:
        lines += [
            "",
            "## Cost",
            "",
            "| Avg input tokens | of which image | Avg output tokens | Avg thinking tokens | Calls/doc | Avg cost/doc | Total | Per 1,000 docs | Avg latency |",
            "|---|---|---|---|---|---|---|---|---|",
            f"| {cost['avg_input_tokens']:.0f} | {cost['avg_image_tokens']:.0f} | {cost['avg_output_tokens']:.0f} | "
            f"{cost['avg_thinking_tokens']:.0f} | {cost['avg_calls']:.2f} | {_money(cost['avg_cost_usd'], 5)} | "
            f"{_money(cost['total_cost_usd'])} | ${cost['cost_per_1000_docs_usd']:.2f} | "
            f"{cost['avg_latency_ms'] / 1000:.1f}s |",
        ]
    return "\n".join(lines) + "\n"
