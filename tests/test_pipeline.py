from __future__ import annotations

import pytest

from invoice_extractor.config import Settings
from invoice_extractor.errors import CorruptFile, LLMOutputInvalid, LLMUnavailable
from invoice_extractor.llm import Blob
from invoice_extractor.pipeline import InvoicePipeline

from .conftest import NOT_AN_INVOICE, FakeClient, answer, scanned_pdf, text_pdf


def pipeline(settings: Settings, client: FakeClient) -> InvoicePipeline:
    return InvoicePipeline(settings, client=client)  # type: ignore[arg-type]


def test_clean_extraction_takes_one_call(settings: Settings) -> None:
    client = FakeClient(answer())
    outcome = pipeline(settings, client).extract_bytes(text_pdf(), "a.pdf")

    assert outcome.status == "ok" and outcome.review.confidence == 1.0
    assert outcome.output()["total"] == 3953.0
    assert len(client.requests) == 1
    # Hybrid mode: page image(s) first, then the prompt carrying the text layer.
    request = client.requests[0]
    assert isinstance(request[0], Blob) and "<text_layer>" in request[-1]


def test_failed_check_triggers_one_corrective_retry(settings: Settings) -> None:
    client = FakeClient(answer(total=9999.0), answer())
    outcome = pipeline(settings, client).extract_bytes(text_pdf(), "a.pdf")

    assert [attempt.number for attempt in outcome.attempts] == [1, 2]
    assert outcome.status == "ok"
    assert outcome.review.confidence == pytest.approx(0.95)  # recovered, small retry penalty
    assert outcome.usage.calls == 2
    feedback = client.requests[1][-1]
    assert "totals" in feedback.lower() or "total is" in feedback


def test_persistent_failure_is_flagged_not_passed_silently(settings: Settings) -> None:
    client = FakeClient(answer(total=9999.0), answer(total=8888.0))
    outcome = pipeline(settings, client).extract_bytes(text_pdf(), "a.pdf")

    assert outcome.status == "needs_review"
    assert any("total is" in reason for reason in outcome.review.reasons)
    assert outcome.output()["total"] == 8888.0  # later attempt wins the tie


def test_retry_keeps_the_better_attempt(settings: Settings) -> None:
    worse = answer(total=9999.0, legibility="degraded", uncertain_fields=["total"])
    client = FakeClient(answer(total=1.0), worse)
    outcome = pipeline(settings, client).extract_bytes(text_pdf(), "a.pdf")
    assert outcome.output()["total"] == 1.0  # same error count, fewer warnings


def test_validation_retries_can_be_disabled(settings: Settings) -> None:
    client = FakeClient(answer(total=9999.0))
    from dataclasses import replace

    no_retry = replace(settings, max_validation_retries=0)
    outcome = pipeline(no_retry, client).extract_bytes(text_pdf(), "a.pdf")
    assert len(outcome.attempts) == 1 and outcome.status == "needs_review"


def test_unparseable_output_twice_raises(settings: Settings) -> None:
    client = FakeClient("not json", '{"is_invoice": "maybe"}')
    with pytest.raises(LLMOutputInvalid):
        pipeline(settings, client).extract_bytes(text_pdf(), "a.pdf")


def test_non_invoice_returns_nulls(settings: Settings) -> None:
    outcome = pipeline(settings, FakeClient(NOT_AN_INVOICE)).extract_bytes(text_pdf(), "po.pdf")
    output = outcome.output()
    assert output["is_invoice"] is False
    assert all(value is None for key, value in output.items() if key != "is_invoice")
    assert outcome.status == "ok"


def test_api_failure_propagates_as_typed_error(settings: Settings) -> None:
    client = FakeClient(LLMUnavailable("timed out"))
    with pytest.raises(LLMUnavailable):
        pipeline(settings, client).extract_bytes(text_pdf(), "a.pdf")


def test_bad_input_fails_before_any_api_call(settings: Settings) -> None:
    client = FakeClient()
    with pytest.raises(CorruptFile):
        pipeline(settings, client).extract_bytes(b"%PDF-1.4 broken", "a.pdf")
    assert client.requests == []


def test_sideways_scan_is_rotated_before_extraction(settings: Settings) -> None:
    client = FakeClient({"upright": "B"}, answer())
    outcome = pipeline(settings, client).extract_bytes(scanned_pdf(rotate=90), "scan.pdf")

    assert outcome.document.pages[0].rotated_by == 270
    assert any(issue.code == "orientation_corrected" for issue in outcome.issues)
    assert outcome.usage.calls == 2  # orientation tie-break + extraction
    orientation_request = client.requests[0]
    assert orientation_request[0] == "Image A:" and orientation_request[2] == "Image B:"


def test_orientation_failure_degrades_gracefully(settings: Settings) -> None:
    client = FakeClient(LLMUnavailable("down"), answer())
    outcome = pipeline(settings, client).extract_bytes(scanned_pdf(rotate=90), "scan.pdf")
    assert any(issue.code == "orientation_unresolved" for issue in outcome.issues)
    assert outcome.status == "needs_review"


def test_meta_is_serialisable(settings: Settings) -> None:
    import json

    outcome = pipeline(settings, FakeClient(answer())).extract_bytes(text_pdf(), "a.pdf")
    meta = json.loads(json.dumps(outcome.meta()))
    assert meta["usage"]["calls"] == 1 and meta["served_by"] == ["fake-model"]


# --- second-read verification ----------------------------------------------------------


def verifying(settings: Settings) -> Settings:
    from dataclasses import replace

    return replace(settings, second_read=True)


def test_confident_clean_read_is_not_verified(settings: Settings) -> None:
    client = FakeClient(answer())
    outcome = pipeline(verifying(settings), client).extract_bytes(text_pdf(), "a.pdf")
    assert len(client.requests) == 1 and outcome.status == "ok"


def test_agreeing_second_read_clears_a_legibility_doubt(settings: Settings) -> None:
    doubtful = answer(legibility="degraded")
    client = FakeClient(doubtful, answer())
    outcome = pipeline(verifying(settings), client).extract_bytes(text_pdf(), "a.pdf")

    assert [a.purpose for a in outcome.attempts] == ["extraction", "verification"]
    assert outcome.status == "ok"  # corroborated, so the doubt alone no longer flags it
    codes = {issue.code: issue.severity.value for issue in outcome.issues}
    assert codes["low_legibility"] == "info" and codes["second_read_agrees"] == "info"
    assert "Independent verification read" in client.requests[1][-1]


def test_disagreeing_second_read_flags_the_fields(settings: Settings) -> None:
    # A self-consistent misread: the arithmetic still balances, so no check fails.
    misread = answer(
        legibility="degraded",
        line_items=[
            {
                "description": "A4 paper, 500 sheets",
                "quantity": 10,
                "unit_price": 330.0,
                "amount": 3300.0,
            },
            {"description": "Delivery", "quantity": None, "unit_price": None, "amount": 50.0},
        ],
    )
    client = FakeClient(misread, answer())
    outcome = pipeline(verifying(settings), client).extract_bytes(text_pdf(), "a.pdf")

    assert outcome.status == "needs_review"
    disagreement = next(i for i in outcome.issues if i.code == "reads_disagree")
    assert "line_items" in disagreement.message


def test_second_read_prefers_the_read_with_fewer_errors(settings: Settings) -> None:
    client = FakeClient(answer(total=1.0), answer(total=2.0), answer())
    outcome = pipeline(verifying(settings), client).extract_bytes(text_pdf(), "a.pdf")
    assert outcome.output()["total"] == 3953.0
    assert [a.purpose for a in outcome.attempts] == ["extraction", "correction", "verification"]
    assert outcome.status == "needs_review"  # the reads disagreed on the total


def test_due_date_catches_a_misread_year(settings: Settings) -> None:
    wrong_year = answer(
        invoice_date="2020-03-14", invoice_date_as_printed="14 Mar 2020", due_date="2026-04-13"
    )
    client = FakeClient(wrong_year, answer(due_date="2026-04-13"))
    outcome = pipeline(settings, client).extract_bytes(text_pdf(), "a.pdf")
    assert outcome.output()["invoice_date"] == "2026-03-14"
    assert "date_order" in [
        code for a in outcome.attempts[:1] for code in (i.code for i in a.issues)
    ]
