"""Business-rule checks on an extraction.

Each check returns ``Issue`` objects with a severity:

* ``error``   - the data is wrong or unusable as-is (totals do not reconcile, schema
                violation, unreadable). Errors marked ``retryable`` trigger one corrective
                re-read; anything still failing afterwards is flagged for review.
* ``warning`` - plausible but suspicious (low legibility, a line where qty x rate does
                not equal the amount, missing invoice number). Flags for review.
* ``info``    - recorded for the reviewer, does not flag on its own.

Nothing here mutates the extraction; the pipeline decides what to do with the issues.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum

from .normalize import normalize_date
from .schema import InvoiceExtraction, Legibility, ModelExtraction, official_schema_errors


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Issue:
    code: str
    severity: Severity
    message: str
    field: str | None = None
    retryable: bool = False

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


# Active ISO 4217 codes (subset that excludes funds/precious metals codes).
ISO_4217 = frozenset(
    [
        "AED",
        "AFN",
        "ALL",
        "AMD",
        "ANG",
        "AOA",
        "ARS",
        "AUD",
        "AWG",
        "AZN",
        "BAM",
        "BBD",
        "BDT",
        "BGN",
        "BHD",
        "BIF",
        "BMD",
        "BND",
        "BOB",
        "BRL",
        "BSD",
        "BTN",
        "BWP",
        "BYN",
        "BZD",
        "CAD",
        "CDF",
        "CHF",
        "CLP",
        "CNY",
        "COP",
        "CRC",
        "CUP",
        "CVE",
        "CZK",
        "DJF",
        "DKK",
        "DOP",
        "DZD",
        "EGP",
        "ERN",
        "ETB",
        "EUR",
        "FJD",
        "FKP",
        "GBP",
        "GEL",
        "GHS",
        "GIP",
        "GMD",
        "GNF",
        "GTQ",
        "GYD",
        "HKD",
        "HNL",
        "HTG",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "IQD",
        "IRR",
        "ISK",
        "JMD",
        "JOD",
        "JPY",
        "KES",
        "KGS",
        "KHR",
        "KMF",
        "KPW",
        "KRW",
        "KWD",
        "KYD",
        "KZT",
        "LAK",
        "LBP",
        "LKR",
        "LRD",
        "LSL",
        "LYD",
        "MAD",
        "MDL",
        "MGA",
        "MKD",
        "MMK",
        "MNT",
        "MOP",
        "MRU",
        "MUR",
        "MVR",
        "MWK",
        "MXN",
        "MYR",
        "MZN",
        "NAD",
        "NGN",
        "NIO",
        "NOK",
        "NPR",
        "NZD",
        "OMR",
        "PAB",
        "PEN",
        "PGK",
        "PHP",
        "PKR",
        "PLN",
        "PYG",
        "QAR",
        "RON",
        "RSD",
        "RUB",
        "RWF",
        "SAR",
        "SBD",
        "SCR",
        "SDG",
        "SEK",
        "SGD",
        "SHP",
        "SLE",
        "SOS",
        "SRD",
        "SSP",
        "STN",
        "SVC",
        "SYP",
        "SZL",
        "THB",
        "TJS",
        "TMT",
        "TND",
        "TOP",
        "TRY",
        "TTD",
        "TWD",
        "TZS",
        "UAH",
        "UGX",
        "USD",
        "UYU",
        "UZS",
        "VES",
        "VND",
        "VUV",
        "WST",
        "XAF",
        "XCD",
        "XOF",
        "XPF",
        "YER",
        "ZAR",
        "ZMW",
        "ZWG",
    ]
)

_NUMERIC_DATE = re.compile(r"^\s*(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\s*$")
_CORE_FIELDS = ("vendor", "invoice_number", "invoice_date", "currency", "total")


def money_tolerance(component_count: int) -> float:
    """Rounding tolerance for a sum of printed money values.

    Each printed value can be off by half a cent from the exact figure, so the
    tolerance grows with the number of values summed (minimum 5 cents). It stays an
    absolute, cent-level bound on purpose: a percentage tolerance would hide a missed
    ₹250 row on a ₹3,00,000 invoice.
    """
    return max(0.05, 0.01 * (component_count + 1))


def _close(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


def _fmt(value: float) -> str:
    return f"{value:,.2f}"


def check_schema(result: InvoiceExtraction) -> list[Issue]:
    return [
        Issue(
            "schema_invalid",
            Severity.ERROR,
            f"Output does not match the schema: {message}",
            retryable=True,
        )
        for message in official_schema_errors(result.model_dump(mode="json"))
    ]


def check_arithmetic(result: InvoiceExtraction, raw: ModelExtraction) -> list[Issue]:
    issues: list[Issue] = []
    items = result.line_items or []
    line_sum = sum(item.amount for item in items)
    tax_lines = raw.tax_lines or []

    if raw.subtotal is not None and items:
        tolerance = money_tolerance(len(items))
        if not _close(line_sum, raw.subtotal, tolerance):
            issues.append(
                Issue(
                    "subtotal_mismatch",
                    Severity.ERROR,
                    f"Line items sum to {_fmt(line_sum)} but the printed subtotal is "
                    f"{_fmt(raw.subtotal)} (difference {_fmt(line_sum - raw.subtotal)}).",
                    field="line_items",
                    retryable=True,
                )
            )

    if tax_lines and result.tax_total is not None:
        tax_sum = sum(line.amount for line in tax_lines)
        if not _close(tax_sum, result.tax_total, money_tolerance(len(tax_lines))):
            issues.append(
                Issue(
                    "tax_lines_mismatch",
                    Severity.ERROR,
                    f"Tax lines sum to {_fmt(tax_sum)} but tax_total is {_fmt(result.tax_total)}.",
                    field="tax_total",
                    retryable=True,
                )
            )

    if result.total is not None and result.tax_total is not None and items:
        expected = line_sum + result.tax_total
        tolerance = money_tolerance(len(items) + max(len(tax_lines), 1))
        if not _close(expected, result.total, tolerance):
            issues.append(
                Issue(
                    "totals_mismatch",
                    Severity.ERROR,
                    f"Line items ({_fmt(line_sum)}) + tax ({_fmt(result.tax_total)}) = "
                    f"{_fmt(expected)}, but total is {_fmt(result.total)} "
                    f"(difference {_fmt(result.total - expected)}).",
                    field="total",
                    retryable=True,
                )
            )

    for index, item in enumerate(raw.line_items or [], start=1):
        if item.quantity is None or item.unit_price is None:
            continue
        expected = item.quantity * item.unit_price
        if not _close(expected, item.amount, max(0.05, 0.005 * abs(item.amount))):
            issues.append(
                Issue(
                    "line_arithmetic",
                    Severity.WARNING,
                    f"Row {index} '{item.description[:40]}': {item.quantity:g} x "
                    f"{_fmt(item.unit_price)} = {_fmt(expected)}, but amount is {_fmt(item.amount)}.",
                    field="line_items",
                )
            )
    return issues


def check_fields(
    result: InvoiceExtraction, raw: ModelExtraction, today: date | None = None
) -> list[Issue]:
    issues: list[Issue] = []
    today = today or date.today()

    for name in _CORE_FIELDS:
        if getattr(result, name) is None:
            original = getattr(raw, name, None)
            detail = f" (model returned {original!r}, which is not valid)" if original else ""
            issues.append(
                Issue(
                    "missing_field",
                    Severity.ERROR if name == "total" else Severity.WARNING,
                    f"{name} is missing{detail}.",
                    field=name,
                    retryable=name == "total",
                )
            )

    if not result.line_items:
        issues.append(
            Issue("no_line_items", Severity.WARNING, "No line items were extracted.", "line_items")
        )

    if result.currency and result.currency not in ISO_4217:
        issues.append(
            Issue(
                "currency_unknown",
                Severity.ERROR,
                f"'{result.currency}' is not an ISO 4217 code.",
                "currency",
            )
        )

    if result.total is not None and result.total < 0:
        issues.append(Issue("negative_total", Severity.WARNING, "The total is negative.", "total"))

    if result.invoice_date:
        issues.extend(_check_invoice_age(date.fromisoformat(result.invoice_date), today))
    issues.extend(_check_printed_date(result, raw))
    issues.extend(_check_due_date(result, raw))
    return issues


# Accounts-payable control: invoices normally arrive within weeks of issue. An invoice
# dated more than a year before processing is either stale or has a misread year.
MAX_INVOICE_AGE_DAYS = 365
MAX_FUTURE_DAYS = 30


def _check_invoice_age(issued: date, today: date) -> list[Issue]:
    age = (today - issued).days
    if age > MAX_INVOICE_AGE_DAYS:
        message = (
            f"Invoice date {issued} is {age} days before the processing date {today}: "
            "a stale invoice, or a misread year."
        )
        return [Issue("date_stale", Severity.WARNING, message, "invoice_date")]
    if age < -MAX_FUTURE_DAYS:
        message = f"Invoice date {issued} is {-age} days after the processing date {today}."
        return [Issue("date_future", Severity.WARNING, message, "invoice_date")]
    return []


# Payment terms longer than this are rare enough that a gap this size means a misread date.
MAX_PAYMENT_TERM_DAYS = 180


def _check_due_date(result: InvoiceExtraction, raw: ModelExtraction) -> list[Issue]:
    """Cross-check the issue date against the printed due date.

    A misread digit in the year (2026 read as 2020) passes every format check; the due
    date printed on the same page is independent evidence that catches it.
    """
    due = normalize_date(raw.due_date)
    if not result.invoice_date or not due:
        return []
    gap = (date.fromisoformat(due) - date.fromisoformat(result.invoice_date)).days
    if gap < 0:
        message = f"Due date {due} is before the invoice date {result.invoice_date}."
    elif gap > MAX_PAYMENT_TERM_DAYS:
        message = (
            f"Due date {due} is {gap} days after the invoice date {result.invoice_date}; "
            "one of the two dates is probably misread."
        )
    else:
        return []
    return [Issue("date_order", Severity.ERROR, message, "invoice_date", retryable=True)]


def _check_printed_date(result: InvoiceExtraction, raw: ModelExtraction) -> list[Issue]:
    """Cross-check the ISO date against the date text the model says it read."""
    if not result.invoice_date or not raw.invoice_date_as_printed:
        return []
    match = _NUMERIC_DATE.match(raw.invoice_date_as_printed)
    if not match:
        return []  # e.g. "08 April 2026": unambiguous, nothing to cross-check

    first, second, year = (int(group) for group in match.groups())
    year = year + 2000 if year < 100 else year
    readings = set()
    for day, month in ((first, second), (second, first)):
        try:
            readings.add(date(year, month, day).isoformat())
        except ValueError:
            continue

    if result.invoice_date not in readings:
        return [
            Issue(
                "date_inconsistent",
                Severity.WARNING,
                f"Printed date '{raw.invoice_date_as_printed}' cannot be read as {result.invoice_date}.",
                "invoice_date",
            )
        ]
    if len(readings) == 2:
        reason = raw.date_reasoning or "no reason given"
        return [
            Issue(
                "date_ambiguous",
                Severity.INFO,
                f"'{raw.invoice_date_as_printed}' could be day-first or month-first; read as "
                f"{result.invoice_date} ({reason}).",
                "invoice_date",
            )
        ]
    return []


def check_model_signals(raw: ModelExtraction) -> list[Issue]:
    issues: list[Issue] = []
    if raw.legibility is Legibility.UNREADABLE:
        issues.append(
            Issue("unreadable", Severity.ERROR, "The model reports the document is unreadable.")
        )
    elif raw.legibility is Legibility.DEGRADED:
        issues.append(
            Issue(
                "low_legibility",
                Severity.WARNING,
                "The model reports degraded legibility (blur, skew or noise).",
            )
        )

    uncertain = sorted({name for name in raw.uncertain_fields if name})
    if uncertain and raw.is_invoice:
        issues.append(
            Issue(
                "model_uncertain",
                Severity.WARNING,
                f"The model was unsure about: {', '.join(uncertain)}.",
                field=uncertain[0] if len(uncertain) == 1 else None,
            )
        )

    claims_invoice = raw.document_type.value == "invoice"
    if claims_invoice != raw.is_invoice:
        issues.append(
            Issue(
                "classification_conflict",
                Severity.WARNING,
                f"document_type is '{raw.document_type.value}' but is_invoice is {raw.is_invoice}.",
                "is_invoice",
            )
        )
    return issues


def validate(
    result: InvoiceExtraction, raw: ModelExtraction, today: date | None = None
) -> list[Issue]:
    issues = check_schema(result) + check_model_signals(raw)
    if result.is_invoice:
        issues += check_fields(result, raw, today) + check_arithmetic(result, raw)
    return issues


def errors_of(issues: list[Issue]) -> list[Issue]:
    return [issue for issue in issues if issue.severity is Severity.ERROR]
