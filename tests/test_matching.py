from __future__ import annotations

import copy

import pytest

from invoice_extractor.matching import (
    compare_document,
    compare_line_items,
    match_money,
    match_vendor,
    normalize_invoice_number,
    parse_number,
)

TRUTH = {
    "is_invoice": True,
    "vendor": "Kaveri Office Mart Pvt Ltd",
    "invoice_number": "KOM/26-27/00418",
    "invoice_date": "2026-06-23",
    "currency": "INR",
    "line_items": [
        {"description": "A4 copier paper 75 GSM (ream)", "quantity": 40, "amount": 11560.0},
        {"description": "Whiteboard markers (box of 10)", "quantity": 12, "amount": 2580.0},
        {"description": "Returning client discount", "quantity": None, "amount": -450.0},
    ],
    "tax_total": 9788.4,
    "total": 64168.4,
}


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        (1200, 1200.0),
        ("1,200.00", 1200.0),
        ("₹ 3,00,484.80", 300484.8),
        ("1.136,25", 1136.25),
        ("-450", -450.0),
        (None, None),
    ],
)
def test_parse_number(raw: object, value: float | None) -> None:
    assert parse_number(raw) == value


def test_money_rule() -> None:
    assert match_money(1200, "1,200.00")[0]
    assert match_money(100.0, 100.009)[0]
    assert not match_money(100.0, 100.02)[0]
    assert match_money(None, None)[0] and not match_money(0, None)[0]


@pytest.mark.parametrize(
    ("expected", "predicted", "ok"),
    [
        ("Acme Pvt Ltd", "Acme", True),
        ("Pixel Harbor Studio", "PIXEL HARBOR STUDIO", True),
        ("Anand & Rao Associates", "Anand and Rao Associates", True),
        ("Meridian Print & Pack LLP", "Meridian Print and Pack", True),
        ("Northwind Logistics Ltd", "Calder & Finch Interiors", False),
        ("Acme Supplies", "Apex Supplies", False),
    ],
)
def test_vendor_rule(expected: str, predicted: str, ok: bool) -> None:
    assert match_vendor(expected, predicted)[0] is ok


def test_invoice_number_rule_keeps_separators() -> None:
    assert normalize_invoice_number(" kom/26-27/00418 ") == normalize_invoice_number(
        "KOM/26-27/00418"
    )
    assert normalize_invoice_number("KOM-26-27-00418") != normalize_invoice_number(
        "KOM/26-27/00418"
    )


def test_ground_truth_scores_perfectly_against_itself() -> None:
    results, items = compare_document(TRUTH, copy.deepcopy(TRUTH))
    assert all(result.correct for result in results)
    assert items is not None and items.exact and items.matched_rows == 3


def test_missing_row_fails_the_field_but_keeps_row_credit() -> None:
    predicted = TRUTH["line_items"][:2]
    comparison = compare_line_items(TRUTH["line_items"], predicted)
    assert not comparison.exact
    assert comparison.matched_rows == 2
    assert "2 rows vs 3 expected" in comparison.detail


def test_quantity_null_vs_one_is_wrong() -> None:
    predicted = copy.deepcopy(TRUTH["line_items"])
    predicted[2]["quantity"] = 1
    comparison = compare_line_items(TRUTH["line_items"], predicted)
    assert not comparison.exact and comparison.quantity_ok == 2


def test_cosmetic_description_differences_are_tolerated() -> None:
    predicted = copy.deepcopy(TRUTH["line_items"])
    predicted[0]["description"] = "A4 Copier Paper 75 GSM  (Ream)"
    assert compare_line_items(TRUTH["line_items"], predicted).exact


def test_non_invoice_nulls_match() -> None:
    empty = {key: None for key in TRUTH} | {"is_invoice": False}
    results, _ = compare_document(empty, copy.deepcopy(empty))
    assert all(result.correct for result in results)

    results, _ = compare_document(empty, copy.deepcopy(TRUTH))
    assert [r.field for r in results if not r.correct] == list(TRUTH)
