"""Deterministic clean-up between the model's answer and the public schema."""

from __future__ import annotations

import re
from datetime import date

from .schema import InvoiceExtraction, LineItem, ModelExtraction

_WHITESPACE = re.compile(r"\s+")
_CURRENCY_SYMBOLS = {
    "₹": "INR",
    "RS": "INR",
    "RS.": "INR",
    "£": "GBP",
    "€": "EUR",
    "$": "USD",
    "US$": "USD",
    "¥": "JPY",
}


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _WHITESPACE.sub(" ", value).strip()
    return cleaned or None


def normalize_currency(value: str | None) -> str | None:
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    upper = cleaned.upper()
    return _CURRENCY_SYMBOLS.get(upper, upper)


def normalize_date(value: str | None) -> str | None:
    """Return the value if it is a real ISO calendar date, else None."""
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    try:
        return date.fromisoformat(cleaned[:10]).isoformat()
    except ValueError:
        return None


def round_money(value: float | None) -> float | None:
    # Removes binary float noise (e.g. 0.1 + 0.2) without changing printed values.
    return None if value is None else round(float(value), 4)


def project(extraction: ModelExtraction) -> InvoiceExtraction:
    """Map the model's rich answer onto the exact output schema."""
    if not extraction.is_invoice:
        return InvoiceExtraction.not_an_invoice()

    line_items = None
    if extraction.line_items is not None:
        line_items = [
            LineItem(
                description=clean_text(item.description) or "",
                quantity=round_money(item.quantity),
                amount=round_money(item.amount) or 0.0,
            )
            for item in extraction.line_items
        ]

    tax_total = extraction.tax_total
    if tax_total is None:
        # Labelling convention: no tax printed means tax_total is 0.
        tax_total = sum(line.amount for line in extraction.tax_lines or [])

    currency = normalize_currency(extraction.currency)
    return InvoiceExtraction(
        is_invoice=True,
        vendor=clean_text(extraction.vendor),
        invoice_number=clean_text(extraction.invoice_number),
        invoice_date=normalize_date(extraction.invoice_date),
        currency=currency if currency and re.fullmatch(r"[A-Z]{3}", currency) else None,
        line_items=line_items,
        tax_total=round_money(tax_total),
        total=round_money(extraction.total),
    )
