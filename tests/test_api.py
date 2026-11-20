from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from invoice_extractor.api import app as api_module
from invoice_extractor.config import Settings
from invoice_extractor.pipeline import InvoicePipeline

from .conftest import FakeClient, answer, text_pdf


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> TestClient:
    fake = FakeClient(answer())
    pipeline = InvoicePipeline(settings, client=fake)  # type: ignore[arg-type]
    monkeypatch.setattr(api_module, "_pipeline", lambda: pipeline)
    return TestClient(api_module.app)


def test_health(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and "model" in body and "prompt_version" in body


def test_upload_returns_result_meta_and_previews(client: TestClient) -> None:
    response = client.post(
        "/api/extract", files={"file": ("invoice.pdf", text_pdf(), "application/pdf")}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["total"] == 3953.0
    assert body["meta"]["status"] == "ok"
    page = client.get(body["pages"][0]["url"])
    assert page.status_code == 200 and page.headers["content-type"] == "image/png"


@pytest.mark.parametrize(
    ("payload", "status", "code"),
    [
        (b"%PDF-1.4 broken", 422, "corrupt_file"),
        (b"plain text", 415, "unsupported_file_type"),
        (b"", 422, "empty_document"),
    ],
)
def test_bad_uploads_return_typed_errors(
    client: TestClient, payload: bytes, status: int, code: str
) -> None:
    response = client.post("/api/extract", files={"file": ("bad.pdf", payload, "application/pdf")})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_validate_reruns_checks_on_a_corrected_result(client: TestClient) -> None:
    result = {
        "is_invoice": True,
        "vendor": "Acme",
        "invoice_number": "INV-1",
        "invoice_date": "2026-03-14",
        "currency": "INR",
        "line_items": [{"description": "Paper", "quantity": 10, "amount": 3200.0}],
        "tax_total": 576.0,
        "total": 3776.0,
    }
    ok = client.post("/api/validate", json={"result": result}).json()
    assert ok["review"]["needs_review"] is False

    broken = client.post("/api/validate", json={"result": {**result, "total": 4000.0}}).json()
    assert broken["review"]["needs_review"] is True
    assert any(issue["code"] == "totals_mismatch" for issue in broken["issues"])


def test_validate_reports_schema_violations(client: TestClient) -> None:
    body = client.post("/api/validate", json={"result": {"is_invoice": True}}).json()
    assert body["result"] is None and body["review"]["needs_review"] is True


def test_unknown_sample_is_404(client: TestClient) -> None:
    assert client.get("/api/documents/NOPE").status_code == 404
    assert client.get("/api/documents/..%2Fsecrets").status_code in (400, 404)
    assert client.get("/api/no-such-endpoint").status_code == 404
