"""Field matching rules for the eval harness.

These rules decide what counts as "correct". They are deliberately strict where a
finance team would be hurt by a mismatch (amounts, dates, invoice numbers) and lenient
only where the difference is cosmetic (vendor legal suffixes, description whitespace).

| Field          | Rule                                                                      |
|----------------|---------------------------------------------------------------------------|
| is_invoice     | exact boolean                                                             |
| vendor         | case/punctuation-insensitive; legal suffixes (Pvt, Ltd, LLP, GmbH, ...)   |
|                | ignored; then equal, or token-set similarity >= 90                       |
| invoice_number | exact after trimming and case-folding; separators ("/", "-") DO matter    |
| invoice_date   | exact ISO date                                                            |
| currency       | exact ISO code                                                            |
| tax_total      | numeric, |a - b| <= 0.01; strings like "1,200.00" are parsed first        |
| total          | numeric, |a - b| <= 0.01                                                  |
| line_items     | same row count, and every row matches in order: description similarity   |
|                | >= 90 after normalising case/whitespace/punctuation, quantity equal       |
|                | (null == null), amount within 0.01                                        |

``null`` on both sides is a match (that is how non-invoices score their empty fields).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz

MONEY_TOLERANCE = 0.01
QUANTITY_TOLERANCE = 1e-6
VENDOR_SIMILARITY = 90
DESCRIPTION_SIMILARITY = 90

LEGAL_SUFFIXES = {
    "pvt", "private", "ltd", "limited", "llp", "llc", "inc", "incorporated", "co",
    "company", "corp", "corporation", "gmbh", "bv", "plc", "sa", "ag", "pty", "srl", "nv",
}  # fmt: skip

FIELDS = (
    "is_invoice",
    "vendor",
    "invoice_number",
    "invoice_date",
    "currency",
    "line_items",
    "tax_total",
    "total",
)


def parse_number(value: Any) -> float | None:
    """Parse 1200, "1,200.00", "₹ 1,200", "1.200,50" into a float."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("booleans are not numbers")
    if isinstance(value, int | float):
        return float(value)
    text = re.sub(r"[^\d,.\-]", "", str(value))
    if not text:
        return None
    if "," in text and "." in text:
        # The right-most separator is the decimal point.
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text:
        head, _, tail = text.rpartition(",")
        text = text.replace(",", "") if len(tail) == 3 else f"{head.replace(',', '')}.{tail}"
    return float(text)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.casefold().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text)).strip()


def normalize_vendor(name: str) -> str:
    return " ".join(token for token in _fold(name).split() if token not in LEGAL_SUFFIXES)


def normalize_description(text: str) -> str:
    return _fold(text)


def normalize_invoice_number(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldResult:
    field: str
    correct: bool
    expected: Any
    predicted: Any
    detail: str = ""


def _both_null(expected: Any, predicted: Any) -> bool | None:
    if expected is None and predicted is None:
        return True
    if expected is None or predicted is None:
        return False
    return None


def match_vendor(expected: str | None, predicted: str | None) -> tuple[bool, str]:
    if (verdict := _both_null(expected, predicted)) is not None:
        return verdict, ""
    a, b = normalize_vendor(expected), normalize_vendor(predicted)  # type: ignore[arg-type]
    if a == b:
        return True, ""
    score = fuzz.token_set_ratio(a, b)
    return score >= VENDOR_SIMILARITY, f"similarity {score:.0f}"


def match_money(expected: Any, predicted: Any) -> tuple[bool, str]:
    if (verdict := _both_null(expected, predicted)) is not None:
        return verdict, ""
    a, b = parse_number(expected), parse_number(predicted)
    if a is None or b is None:
        return False, "unparseable"
    delta = b - a
    return abs(delta) <= MONEY_TOLERANCE, "" if abs(
        delta
    ) <= MONEY_TOLERANCE else f"off by {delta:+,.2f}"


def match_quantity(expected: Any, predicted: Any) -> bool:
    if (verdict := _both_null(expected, predicted)) is not None:
        return verdict
    a, b = parse_number(expected), parse_number(predicted)
    return a is not None and b is not None and abs(a - b) <= QUANTITY_TOLERANCE


def description_similarity(expected: str, predicted: str) -> float:
    return fuzz.ratio(normalize_description(expected), normalize_description(predicted))


@dataclass(frozen=True)
class LineItemComparison:
    """Row-level detail used for item precision/recall and the failure analysis."""

    expected_count: int
    predicted_count: int
    matched_rows: int  # rows matching on description, quantity and amount
    description_ok: int
    quantity_ok: int
    amount_ok: int
    aligned: int  # rows paired up for sub-field scoring
    exact: bool
    detail: str


def compare_line_items(
    expected: list[dict] | None, predicted: list[dict] | None
) -> LineItemComparison:
    expected, predicted = expected or [], predicted or []

    def row_matches(e: dict, p: dict) -> tuple[bool, bool, bool]:
        return (
            description_similarity(e["description"], p["description"]) >= DESCRIPTION_SIMILARITY,
            match_quantity(e.get("quantity"), p.get("quantity")),
            match_money(e["amount"], p["amount"])[0],
        )

    # Pair rows greedily by best description similarity (order-independent), so a
    # single missed row does not make every later row count as wrong.
    unpaired = list(range(len(predicted)))
    pairs: list[tuple[dict, dict]] = []
    for e in expected:
        if not unpaired:
            break
        best = max(
            unpaired,
            key=lambda j: description_similarity(e["description"], predicted[j]["description"]),
        )
        if description_similarity(e["description"], predicted[best]["description"]) >= 60:
            pairs.append((e, predicted[best]))
            unpaired.remove(best)

    checks = [row_matches(e, p) for e, p in pairs]
    description_ok = sum(c[0] for c in checks)
    quantity_ok = sum(c[1] for c in checks)
    amount_ok = sum(c[2] for c in checks)
    matched = sum(all(c) for c in checks)

    in_order = len(expected) == len(predicted) and all(
        all(row_matches(e, p)) for e, p in zip(expected, predicted, strict=True)
    )
    problems = []
    if len(expected) != len(predicted):
        problems.append(f"{len(predicted)} rows vs {len(expected)} expected")
    if quantity_ok < len(pairs):
        problems.append(f"{len(pairs) - quantity_ok} quantity mismatch(es)")
    if amount_ok < len(pairs):
        problems.append(f"{len(pairs) - amount_ok} amount mismatch(es)")
    if description_ok < len(pairs):
        problems.append(f"{len(pairs) - description_ok} description mismatch(es)")
    if not problems and not in_order and expected:
        problems.append("row order differs")

    return LineItemComparison(
        expected_count=len(expected),
        predicted_count=len(predicted),
        matched_rows=matched,
        description_ok=description_ok,
        quantity_ok=quantity_ok,
        amount_ok=amount_ok,
        aligned=len(pairs),
        exact=in_order,
        detail="; ".join(problems),
    )


def compare_document(
    expected: dict[str, Any], predicted: dict[str, Any]
) -> tuple[list[FieldResult], LineItemComparison | None]:
    results: list[FieldResult] = []
    line_items: LineItemComparison | None = None
    for name in FIELDS:
        e, p = expected.get(name), predicted.get(name)
        detail = ""
        if name == "is_invoice":
            correct = e == p
        elif name == "vendor":
            correct, detail = match_vendor(e, p)
        elif name == "invoice_number":
            verdict = _both_null(e, p)
            correct = (
                verdict
                if verdict is not None
                else normalize_invoice_number(e) == normalize_invoice_number(p)
            )
        elif name in ("invoice_date", "currency"):
            correct = (
                e == p
                if e is None or p is None
                else str(e).strip().upper() == str(p).strip().upper()
            )
        elif name in ("tax_total", "total"):
            correct, detail = match_money(e, p)
        else:  # line_items
            if e is None and p is None:
                correct = True
            elif e is None or p is None:
                correct, detail = False, "null vs list"
            else:
                line_items = compare_line_items(e, p)
                correct, detail = line_items.exact, line_items.detail
        results.append(FieldResult(name, bool(correct), e, p, detail))
    return results, line_items
