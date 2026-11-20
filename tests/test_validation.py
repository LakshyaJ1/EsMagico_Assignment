from __future__ import annotations

from datetime import date

import pytest

from invoice_extractor.normalize import project
from invoice_extractor.review import decide
from invoice_extractor.schema import InvoiceExtraction, ModelExtraction, official_schema_errors
from invoice_extractor.validation import Severity, money_tolerance, validate

from .conftest import NOT_AN_INVOICE, answer


def run(**changes: object) -> list[str]:
    raw = ModelExtraction.model_validate(answer(**changes))
    return [issue.code for issue in validate(project(raw), raw)]


def test_consistent_invoice_passes_every_check() -> None:
    assert run() == []


def test_projection_matches_the_official_schema() -> None:
    result = project(ModelExtraction.model_validate(answer()))
    payload = result.model_dump(mode="json")
    assert official_schema_errors(payload) == []
    assert list(payload) == list(InvoiceExtraction.model_fields)
    assert payload["line_items"][0]["quantity"] == 10  # integral quantities stay integers


def test_non_invoice_projects_to_all_null() -> None:
    raw = ModelExtraction.model_validate({**NOT_AN_INVOICE, "vendor": "Should be dropped"})
    payload = project(raw).model_dump(mode="json")
    assert payload["is_invoice"] is False
    assert all(value is None for key, value in payload.items() if key != "is_invoice")
    assert official_schema_errors(payload) == []


def test_totals_mismatch_is_a_retryable_error() -> None:
    raw = ModelExtraction.model_validate(answer(total=4953.0))
    issues = validate(project(raw), raw)
    mismatch = next(issue for issue in issues if issue.code == "totals_mismatch")
    assert mismatch.severity is Severity.ERROR and mismatch.retryable
    assert "difference 1,000.00" in mismatch.message


def test_missed_line_item_breaks_subtotal() -> None:
    items = answer()["line_items"][:1]
    assert "subtotal_mismatch" in run(line_items=items)


def test_tax_lines_must_sum_to_tax_total() -> None:
    assert "tax_lines_mismatch" in run(tax_total=301.5, total=3651.5)


def test_row_arithmetic_is_a_warning() -> None:
    items = answer()["line_items"]
    items[0]["unit_price"] = 32.0
    assert "line_arithmetic" in run(line_items=items)


def test_rounding_within_tolerance_is_accepted() -> None:
    assert run(total=3953.02) == []


def test_money_tolerance_grows_with_components_but_stays_small() -> None:
    assert money_tolerance(1) == pytest.approx(0.05)
    assert money_tolerance(30) == pytest.approx(0.31)


def test_ambiguous_numeric_date_is_recorded() -> None:
    assert run(invoice_date_as_printed="04/03/2026", invoice_date="2026-03-04") == [
        "date_ambiguous"
    ]


def test_date_that_contradicts_the_printed_text_is_flagged() -> None:
    assert "date_inconsistent" in run(
        invoice_date_as_printed="14/03/2026", invoice_date="2026-04-13"
    )


def test_invalid_date_and_currency_are_dropped_and_reported() -> None:
    codes = run(invoice_date="2026-02-30", currency="RUPEES")
    assert codes.count("missing_field") == 2


def test_unknown_currency_code() -> None:
    assert "currency_unknown" in run(currency="XYZ")


def test_implausible_date() -> None:
    raw = ModelExtraction.model_validate(
        answer(invoice_date="1999-01-01", invoice_date_as_printed=None)
    )
    from invoice_extractor.validation import check_fields

    codes = [issue.code for issue in check_fields(project(raw), raw, today=date(2026, 11, 21))]
    assert "date_stale" in codes


def test_model_self_reports_feed_review() -> None:
    assert "low_legibility" in run(legibility="degraded")
    assert "unreadable" in run(legibility="unreadable")
    assert "model_uncertain" in run(uncertain_fields=["total"])


def test_review_decision() -> None:
    raw = ModelExtraction.model_validate(answer(total=4953.0, legibility="degraded"))
    decision = decide(validate(project(raw), raw), retried=True)
    assert decision.needs_review
    assert decision.confidence == pytest.approx(1 - 0.40 - 0.15 - 0.05)
    assert len(decision.reasons) == 2

    clean = decide([], retried=False)
    assert not clean.needs_review and clean.confidence == 1.0


def test_due_date_must_follow_the_invoice_date() -> None:
    assert "date_order" in run(due_date="2026-03-01")  # before the 14 March issue date
    assert "date_order" in run(
        invoice_date="2020-03-14", invoice_date_as_printed=None, due_date="2026-04-13"
    )
    assert run(due_date="2026-04-13") == []


def test_stale_and_future_invoice_dates() -> None:
    from invoice_extractor.validation import check_fields

    def codes(iso: str) -> list[str]:
        raw = ModelExtraction.model_validate(answer(invoice_date=iso, invoice_date_as_printed=None))
        return [issue.code for issue in check_fields(project(raw), raw, today=date(2026, 11, 21))]

    assert "date_stale" in codes("2020-09-03")  # the lowres "2026 read as 2020" failure
    assert "date_future" in codes("2027-06-01")
    assert not {"date_stale", "date_future"} & set(codes("2026-03-14"))
