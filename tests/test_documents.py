from __future__ import annotations

import io

import pymupdf
import pytest
from PIL import Image

from invoice_extractor.documents import DocumentKind, load_document, rotate_page, sniff_mime
from invoice_extractor.errors import (
    CorruptFile,
    EmptyDocument,
    EncryptedPdf,
    FileTooLarge,
    UnsupportedFileType,
)

from .conftest import scanned_pdf, text_pdf


def png(color: str = "white", size: tuple[int, int] = (1200, 1600)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_sniffs_real_type_not_extension() -> None:
    assert sniff_mime(text_pdf()) == "application/pdf"
    assert sniff_mime(png()) == "image/png"
    assert sniff_mime(b"hello") is None


def test_digital_pdf_keeps_text_layer() -> None:
    document = load_document(text_pdf(), "invoice.pdf")
    assert document.kind is DocumentKind.PDF
    assert document.has_text_layer and not document.is_scanned
    assert "Widget assembly kit" in document.text_layer()
    assert document.pages[0].mime_type == "image/png"


def test_scanned_pdf_has_no_text_layer() -> None:
    document = load_document(scanned_pdf(), "scan.pdf")
    assert document.is_scanned
    assert not document.pages[0].sideways


@pytest.mark.parametrize("rotation", [90, 270])
def test_detects_sideways_scans(rotation: int) -> None:
    assert load_document(scanned_pdf(rotate=rotation), "scan.pdf").pages[0].sideways


def test_slightly_skewed_scan_is_not_sideways() -> None:
    with pymupdf.open(stream=scanned_pdf()) as pdf:
        pixmap = pdf[0].get_pixmap(dpi=110)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    buffer = io.BytesIO()
    image.rotate(7, expand=True, fillcolor="white").save(buffer, format="JPEG")
    assert not load_document(buffer.getvalue(), "skewed.jpg").pages[0].sideways


def test_rotate_page_tracks_rotation() -> None:
    page = load_document(scanned_pdf(rotate=90), "scan.pdf").pages[0]
    upright = rotate_page(page, 270)
    assert upright.rotated_by == 270
    assert (upright.width, upright.height) == (page.height, page.width)


def test_page_limit_is_reported_not_silent() -> None:
    document = load_document(text_pdf(pages=3), "long.pdf", max_pages=2)
    assert len(document.pages) == 2 and document.page_count == 3
    assert any("only the first 2" in warning for warning in document.warnings)


@pytest.mark.parametrize(
    ("data", "error"),
    [
        (b"", EmptyDocument),
        (b"just some text", UnsupportedFileType),
        (b"%PDF-1.7\n this is not really a pdf", CorruptFile),
        (png()[:200], CorruptFile),
        (png("white"), EmptyDocument),
    ],
    ids=["empty", "not-a-document", "corrupt-pdf", "truncated-image", "blank-page"],
)
def test_bad_inputs_raise_typed_errors(data: bytes, error: type[Exception]) -> None:
    with pytest.raises(error):
        load_document(data, "bad")


def test_encrypted_pdf() -> None:
    pdf = pymupdf.open(stream=text_pdf())
    data = pdf.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner")
    pdf.close()
    with pytest.raises(EncryptedPdf):
        load_document(data, "locked.pdf")


def test_file_size_limit() -> None:
    with pytest.raises(FileTooLarge):
        load_document(b"%PDF-" + b"0" * 2_000_000, "big.pdf", max_file_mb=1)
