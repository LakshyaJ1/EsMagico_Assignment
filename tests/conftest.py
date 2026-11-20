from __future__ import annotations

import copy
import io
import json
from collections.abc import Callable
from typing import Any

import pymupdf
import pytest
from PIL import Image

from invoice_extractor.config import Settings
from invoice_extractor.errors import PipelineError
from invoice_extractor.llm import Content, LLMResponse
from invoice_extractor.pricing import Usage

# A consistent invoice in the model's (internal) response format.
GOOD_ANSWER: dict[str, Any] = {
    "document_type": "invoice",
    "is_invoice": True,
    "classification_reason": "A tax invoice issued by the seller.",
    "legibility": "clear",
    "vendor": "Acme Supplies Pvt Ltd",
    "invoice_number": "INV-2041",
    "invoice_date_as_printed": "14/03/2026",
    "invoice_date": "2026-03-14",
    "date_reasoning": None,
    "currency": "INR",
    "line_items": [
        {
            "description": "A4 paper, 500 sheets",
            "quantity": 10,
            "unit_price": 320.0,
            "amount": 3200.0,
        },
        {"description": "Delivery", "quantity": None, "unit_price": None, "amount": 150.0},
    ],
    "subtotal": 3350.0,
    "tax_lines": [
        {"label": "CGST @ 9%", "rate_percent": 9, "amount": 301.5},
        {"label": "SGST @ 9%", "rate_percent": 9, "amount": 301.5},
    ],
    "tax_total": 603.0,
    "total": 3953.0,
    "uncertain_fields": [],
}

NOT_AN_INVOICE: dict[str, Any] = {
    **{key: None for key in GOOD_ANSWER},
    "document_type": "purchase_order",
    "is_invoice": False,
    "classification_reason": "Issued by the buyer.",
    "legibility": "clear",
    "uncertain_fields": [],
}


def answer(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(GOOD_ANSWER)
    data.update(changes)
    return data


class FakeClient:
    """Stands in for GeminiClient: returns queued answers and records every request."""

    def __init__(
        self, *responses: dict[str, Any] | str | PipelineError | Callable[[list[Content]], Any]
    ):
        self.responses = list(responses)
        self.requests: list[list[Content]] = []

    def generate_json(self, contents: list[Content], **_: Any) -> LLMResponse:
        self.requests.append(contents)
        item = self.responses.pop(0)
        if callable(item) and not isinstance(item, dict):
            item = item(contents)
        if isinstance(item, PipelineError):
            raise item
        text = item if isinstance(item, str) else json.dumps(item)
        usage = Usage(calls=1, input_tokens=1000, output_tokens=200, cost_usd=0.001)
        return LLMResponse(
            text=text,
            usage=usage,
            model="fake-model",
            model_version="fake",
            finish_reason="STOP",
            latency_ms=5.0,
        )


@pytest.fixture
def settings() -> Settings:
    return Settings(api_key="test", model="fake-model", cache_dir=None, second_read=False)


ITEMS = [
    "Widget assembly kit",
    "Freight to warehouse",
    "Stainless hex bolts M8 (box of 200)",
    "Annual maintenance",
    "Thermal labels",
    "Installation and commissioning, on site",
    "Cable ties",
    "Printer toner cartridge, black, high yield",
]


def text_pdf(lines: int = 30, pages: int = 1) -> bytes:
    """A digital PDF with varied, invoice-like lines (identical lines would align into
    vertical columns and look nothing like a real page)."""
    pdf = pymupdf.open()
    for page_number in range(pages):
        page = pdf.new_page()
        rows = []
        for i in range(lines):
            item = ITEMS[(i * 3) % len(ITEMS)]
            quantity = (i * 7) % 23 + 1
            rows.append(f"{i + 1}. {item}{' ' * (i % 5)}  x{quantity}  @ {quantity * 13.5:,.2f}")
        page.insert_text(
            (50, 60), f"TAX INVOICE page {page_number + 1}\n" + "\n".join(rows), fontsize=10
        )
    data = pdf.tobytes()
    pdf.close()
    return data


def scanned_pdf(rotate: int = 0, lines: int = 30) -> bytes:
    """An image-only PDF made from a rendered text page, optionally rotated clockwise."""
    with pymupdf.open(stream=text_pdf(lines)) as source:
        pixmap = source[0].get_pixmap(dpi=110)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples).rotate(
        -rotate, expand=True
    )
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    pdf = pymupdf.open()
    page = pdf.new_page(width=image.width * 72 / 110, height=image.height * 72 / 110)
    page.insert_image(page.rect, stream=buffer.getvalue())
    data = pdf.tobytes()
    pdf.close()
    return data
