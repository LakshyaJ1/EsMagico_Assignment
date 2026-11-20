"""Data contracts.

Two layers:

* ``InvoiceExtraction`` is the public output: exactly the schema in the brief
  (``resources/invoice.schema.json``). Every JSON file the pipeline emits matches it.
* ``ModelExtraction`` is what we ask the LLM for. It is a superset that carries the
  evidence our validators need (printed subtotal, each tax line, unit prices, the date
  exactly as printed, legibility). Those extra fields are what make the arithmetic and
  date checks possible; they are projected away before output.
"""

from __future__ import annotations

import json
import re
from datetime import date
from enum import StrEnum
from functools import cache
from importlib import resources
from typing import Any

import jsonschema
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_CURRENCY = re.compile(r"^[A-Z]{3}$")


def _compact_number(value: float | None) -> float | int | None:
    """Serialise 3.0 as 3 so quantities read the way they are printed."""
    if value is None:
        return None
    return int(value) if float(value).is_integer() else value


# --------------------------------------------------------------------------------------
# Public output contract
# --------------------------------------------------------------------------------------


class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    quantity: float | None
    amount: float

    @field_serializer("quantity")
    def _serialise_quantity(self, value: float | None) -> float | int | None:
        return _compact_number(value)


class InvoiceExtraction(BaseModel):
    """The output schema from the brief. Field order matches the example output."""

    model_config = ConfigDict(extra="forbid")

    is_invoice: bool
    vendor: str | None
    invoice_number: str | None
    invoice_date: str | None
    currency: str | None
    line_items: list[LineItem] | None
    tax_total: float | None
    total: float | None

    @field_validator("invoice_date")
    @classmethod
    def _iso_calendar_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not ISO_DATE.match(value):
            raise ValueError("invoice_date must be YYYY-MM-DD")
        date.fromisoformat(value)  # rejects 2026-02-30
        return value

    @field_validator("currency")
    @classmethod
    def _iso_currency(cls, value: str | None) -> str | None:
        if value is not None and not ISO_CURRENCY.match(value):
            raise ValueError("currency must be a 3-letter ISO 4217 code")
        return value

    @model_validator(mode="after")
    def _non_invoice_is_all_null(self) -> InvoiceExtraction:
        if not self.is_invoice:
            populated = [
                name
                for name in type(self).model_fields
                if name != "is_invoice" and getattr(self, name) is not None
            ]
            if populated:
                raise ValueError(f"non-invoice must have null fields, got {populated}")
        return self

    @classmethod
    def not_an_invoice(cls) -> InvoiceExtraction:
        return cls(
            is_invoice=False,
            vendor=None,
            invoice_number=None,
            invoice_date=None,
            currency=None,
            line_items=None,
            tax_total=None,
            total=None,
        )


@cache
def official_schema() -> dict[str, Any]:
    text = (
        resources.files("invoice_extractor.resources")
        .joinpath("invoice.schema.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(text)


def official_schema_errors(payload: dict[str, Any]) -> list[str]:
    """Validate against the brief's JSON Schema (independent of our Pydantic model)."""
    validator = jsonschema.Draft202012Validator(official_schema())
    return [
        f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    ]


# --------------------------------------------------------------------------------------
# What the model returns (internal)
# --------------------------------------------------------------------------------------


class DocumentType(StrEnum):
    INVOICE = "invoice"
    PURCHASE_ORDER = "purchase_order"
    QUOTATION = "quotation"
    RECEIPT = "receipt"
    CREDIT_NOTE = "credit_note"
    DELIVERY_NOTE = "delivery_note"
    BANK_STATEMENT = "bank_statement"
    LETTER = "letter"
    OTHER = "other"


class Legibility(StrEnum):
    CLEAR = "clear"
    DEGRADED = "degraded"
    UNREADABLE = "unreadable"


class ModelLineItem(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    amount: float


class TaxLine(BaseModel):
    label: str
    rate_percent: float | None = None
    amount: float


class ModelExtraction(BaseModel):
    """The model's answer, with the evidence fields the validators use."""

    document_type: DocumentType
    is_invoice: bool
    classification_reason: str = ""
    legibility: Legibility = Legibility.CLEAR
    vendor: str | None = None
    invoice_number: str | None = None
    invoice_date_as_printed: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    date_reasoning: str | None = None
    currency: str | None = None
    line_items: list[ModelLineItem] | None = None
    subtotal: float | None = None
    tax_lines: list[TaxLine] | None = None
    tax_total: float | None = None
    total: float | None = None
    uncertain_fields: list[str] = Field(default_factory=list)


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    kind = schema["type"]
    return {**schema, "type": [kind, "null"]} if isinstance(kind, str) else schema


def model_response_schema() -> dict[str, Any]:
    """Hand-written JSON Schema for ``ModelExtraction`` used for constrained decoding.

    Written by hand rather than via ``model_json_schema()`` so it stays inside the
    subset Gemini enforces (no $defs/anyOf; nullability via type arrays) and so the
    property order, which the model follows, puts classification before extraction.
    """
    number = {"type": "number"}
    string = {"type": "string"}
    line_item = {
        "type": "object",
        "properties": {
            "description": {**string, "description": "Item text exactly as printed."},
            "quantity": _nullable(
                {**number, "description": "Printed quantity; null if blank or '-'."}
            ),
            "unit_price": _nullable({**number, "description": "Printed unit price/rate, if any."}),
            "amount": {**number, "description": "Row total before tax. Discounts are negative."},
        },
        "required": ["description", "quantity", "unit_price", "amount"],
        "additionalProperties": False,
    }
    tax_line = {
        "type": "object",
        "properties": {
            "label": {**string, "description": "Tax line label as printed, e.g. 'CGST @ 9%'."},
            "rate_percent": _nullable(number),
            "amount": number,
        },
        "required": ["label", "rate_percent", "amount"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "document_type": {"type": "string", "enum": [t.value for t in DocumentType]},
            "is_invoice": {"type": "boolean"},
            "classification_reason": {**string, "description": "One short sentence."},
            "legibility": {"type": "string", "enum": [level.value for level in Legibility]},
            "vendor": _nullable(string),
            "invoice_number": _nullable(string),
            "invoice_date_as_printed": _nullable({**string, "description": "Issue date verbatim."}),
            "invoice_date": _nullable({**string, "description": "Issue date as YYYY-MM-DD."}),
            "due_date": _nullable(
                {**string, "description": "Payment due date as YYYY-MM-DD, if printed."}
            ),
            "date_reasoning": _nullable(
                {
                    **string,
                    "description": "Only if day/month order was ambiguous: how you resolved it.",
                }
            ),
            "currency": _nullable({**string, "description": "ISO 4217 code."}),
            "line_items": {"type": ["array", "null"], "items": line_item},
            "subtotal": _nullable(
                {**number, "description": "Printed subtotal before tax, if shown."}
            ),
            "tax_lines": {"type": ["array", "null"], "items": tax_line},
            "tax_total": _nullable(number),
            "total": _nullable({**number, "description": "Final amount payable."}),
            "uncertain_fields": {
                "type": "array",
                "items": string,
                "description": "Output fields you could not read with confidence.",
            },
        },
        "required": [
            "document_type",
            "is_invoice",
            "classification_reason",
            "legibility",
            "vendor",
            "invoice_number",
            "invoice_date_as_printed",
            "invoice_date",
            "due_date",
            "date_reasoning",
            "currency",
            "line_items",
            "subtotal",
            "tax_lines",
            "tax_total",
            "total",
            "uncertain_fields",
        ],
        "additionalProperties": False,
    }
