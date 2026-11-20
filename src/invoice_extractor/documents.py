"""Turn an uploaded file into something we can show a model.

Responsibilities:
* identify the real file type from its bytes (never trust the extension),
* reject corrupt, encrypted, empty, blank or oversized inputs with a typed error,
* render PDF pages to images and keep the embedded text layer when there is one,
* undo phone-camera EXIF rotation and detect pages that are lying on their side.
"""

from __future__ import annotations

import hashlib
import io
import itertools
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import CorruptFile, EmptyDocument, EncryptedPdf, FileTooLarge, UnsupportedFileType

# Pages with fewer characters than this in their text layer are treated as scans.
MIN_TEXT_LAYER_CHARS = 40
# A page is sideways when its text lines are sharper near 90° than near 0° (ratio < 1).
# Measured on all 20 sample pages plus 90/270/7-degree-skewed copies of each (80 images):
# upright and skewed pages score >= 1.12, sideways pages <= 0.91.
SIDEWAYS_RATIO = 1.0
# Fraction of "ink" pixels below which a page is considered blank.
BLANK_INK_FRACTION = 0.0015
MIN_IMAGE_SIDE_PX = 500

Image.MAX_IMAGE_PIXELS = 80_000_000  # refuse decompression bombs


class DocumentKind(StrEnum):
    PDF = "pdf"
    IMAGE = "image"


_MAGIC: list[tuple[bytes, str]] = [
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
]


def sniff_mime(data: bytes) -> str | None:
    # PDFs may have junk before the header; the spec allows it within the first 1 KB.
    if b"%PDF-" in data[:1024]:
        return "application/pdf"
    for magic, mime in _MAGIC:
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@dataclass(frozen=True)
class PageImage:
    data: bytes
    mime_type: str
    width: int
    height: int
    text: str = ""
    rotated_by: int = 0  # degrees clockwise we applied before sending to the model
    sideways: bool = False

    @property
    def has_text(self) -> bool:
        return len(self.text.strip()) >= MIN_TEXT_LAYER_CHARS


@dataclass
class LoadedDocument:
    name: str
    kind: DocumentKind
    source_mime: str
    raw: bytes = field(repr=False)
    pages: list[PageImage]
    page_count: int
    sha256: str
    warnings: list[str] = field(default_factory=list)

    @property
    def has_text_layer(self) -> bool:
        return bool(self.pages) and all(page.has_text for page in self.pages)

    @property
    def is_scanned(self) -> bool:
        return not any(page.has_text for page in self.pages)

    def text_layer(self) -> str:
        return "\n\n".join(
            f"--- page {index} ---\n{page.text.strip()}"
            for index, page in enumerate(self.pages, start=1)
            if page.has_text
        )

    def replace_page(self, index: int, page: PageImage) -> None:
        self.pages[index] = page


# --------------------------------------------------------------------------------------
# Image analysis helpers (Pillow only, no numpy)
# --------------------------------------------------------------------------------------


def _pixels(image: Image.Image) -> list[int]:
    # Pillow >= 12 renamed getdata(); keep working on both.
    getter = getattr(image, "get_flattened_data", None) or image.getdata
    return list(getter())


def _ink_mask(image: Image.Image, longest_side: int = 1000) -> Image.Image:
    gray = ImageOps.grayscale(image)
    gray.thumbnail((longest_side, longest_side))
    gray = ImageOps.autocontrast(gray, cutoff=1)
    return gray.point(lambda value: 255 if value < 128 else 0)


def _profile(mask: Image.Image, rows: bool) -> list[float]:
    width, height = mask.size
    size = (1, height) if rows else (width, 1)
    squeezed = mask.resize(size, Image.Resampling.BOX)
    return [value / 255 for value in _pixels(squeezed)]


def _roughness(profile: list[float]) -> float:
    mean = sum(profile) / len(profile)
    if mean == 0 or len(profile) < 2:
        return 0.0
    steps = sum(abs(a - b) for a, b in itertools.pairwise(profile))
    return steps / (len(profile) - 1) / mean


_SWEEP_DEGREES = range(-24, 25, 3)


def text_line_ratio(image: Image.Image) -> float:
    """>1 when text lines run roughly horizontally, <1 when they run roughly vertically.

    When text lines are aligned with the pixel rows, the row-wise ink profile alternates
    sharply between lines and gaps ("rough"); at any other angle it smears out. We sweep
    angles around 0° and around 90° and compare the sharpest profile in each family.
    Sweeping (rather than testing exactly 0° vs 90°) keeps a page that is merely skewed
    by a few degrees from being mistaken for a sideways one.
    """
    mask = _ink_mask(image, longest_side=700)

    def sharpest(base: int) -> float:
        return max(
            _roughness(
                _profile(
                    mask.rotate(base + offset, expand=True, resample=Image.Resampling.NEAREST),
                    rows=True,
                )
            )
            for offset in _SWEEP_DEGREES
        )

    sideways = sharpest(90)
    return sharpest(0) / sideways if sideways else 1.0


def ink_fraction(image: Image.Image) -> float:
    mask = _ink_mask(image, longest_side=400)
    return _pixels(mask.resize((1, 1), Image.Resampling.BOX))[0] / 255


def encode_image(image: Image.Image, prefer_png: bool) -> tuple[bytes, str]:
    buffer = io.BytesIO()
    if prefer_png:
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue(), "image/png"
    image.convert("RGB").save(buffer, format="JPEG", quality=90)
    return buffer.getvalue(), "image/jpeg"


def rotate_page(page: PageImage, degrees_clockwise: int) -> PageImage:
    image = Image.open(io.BytesIO(page.data))
    rotated = image.rotate(-degrees_clockwise, expand=True)
    data, mime = encode_image(rotated, prefer_png=page.mime_type == "image/png")
    return replace(
        page,
        data=data,
        mime_type=mime,
        width=rotated.width,
        height=rotated.height,
        rotated_by=(page.rotated_by + degrees_clockwise) % 360,
        sideways=False,
    )


def thumbnail(page: PageImage, longest_side: int = 768) -> Image.Image:
    image = Image.open(io.BytesIO(page.data))
    image.thumbnail((longest_side, longest_side))
    return image.convert("RGB")


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------


def _page_from_image(image: Image.Image, text: str, prefer_png: bool) -> PageImage:
    data, mime = encode_image(image, prefer_png=prefer_png)
    sideways = len(text.strip()) < MIN_TEXT_LAYER_CHARS and text_line_ratio(image) < SIDEWAYS_RATIO
    return PageImage(
        data=data,
        mime_type=mime,
        width=image.width,
        height=image.height,
        text=text,
        sideways=sideways,
    )


def _load_pdf(data: bytes, max_pages: int, dpi: int) -> tuple[list[PageImage], int, list[str]]:
    try:
        pdf = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises several unrelated types for broken files
        raise CorruptFile(f"The PDF could not be opened: {exc}") from exc

    with pdf:
        if pdf.needs_pass:
            raise EncryptedPdf("The PDF is password-protected; remove the password and retry.")
        if pdf.page_count == 0:
            raise EmptyDocument("The PDF has no pages.")

        warnings: list[str] = []
        if pdf.page_count > max_pages:
            warnings.append(
                f"Document has {pdf.page_count} pages; only the first {max_pages} were processed."
            )

        pages: list[PageImage] = []
        for page in list(pdf)[:max_pages]:
            try:
                text = page.get_text("text", sort=True)
                pixmap = page.get_pixmap(dpi=dpi)
            except Exception as exc:
                raise CorruptFile(f"Page {page.number + 1} could not be rendered: {exc}") from exc
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            # Digital pages render crisply as PNG; scans are photos, JPEG is smaller.
            pages.append(
                _page_from_image(image, text, prefer_png=len(text.strip()) >= MIN_TEXT_LAYER_CHARS)
            )
        return pages, pdf.page_count, warnings


def _load_image(data: bytes) -> tuple[list[PageImage], list[str]]:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise CorruptFile(f"The image could not be decoded: {exc}") from exc

    warnings: list[str] = []
    exif_orientation = image.getexif().get(0x0112, 1)  # phone photos store rotation in EXIF
    upright = ImageOps.exif_transpose(image) if exif_orientation != 1 else image
    if exif_orientation != 1:
        warnings.append(f"Applied the camera's EXIF orientation (tag {exif_orientation}).")
    if max(upright.size) < MIN_IMAGE_SIDE_PX:
        warnings.append(f"Low-resolution image ({upright.width}x{upright.height}px).")
    page = _page_from_image(upright.convert("RGB"), text="", prefer_png=False)
    return [page], warnings


def load_document(
    data: bytes, name: str, *, max_pages: int = 8, dpi: int = 170, max_file_mb: float = 20.0
) -> LoadedDocument:
    if not data:
        raise EmptyDocument("The file is empty (0 bytes).")
    if len(data) > max_file_mb * 1024 * 1024:
        raise FileTooLarge(
            f"The file is {len(data) / 1e6:.1f} MB; the limit is {max_file_mb:.0f} MB."
        )

    mime = sniff_mime(data)
    if mime is None:
        raise UnsupportedFileType(
            f"'{name}' is not a PDF or a supported image (JPEG, PNG, WebP, TIFF)."
        )

    if mime == "application/pdf":
        pages, page_count, warnings = _load_pdf(data, max_pages=max_pages, dpi=dpi)
        kind = DocumentKind.PDF
    else:
        pages, warnings = _load_image(data)
        page_count, kind = 1, DocumentKind.IMAGE

    for index, page in enumerate(pages, start=1):
        if (
            not page.has_text
            and ink_fraction(Image.open(io.BytesIO(page.data))) < BLANK_INK_FRACTION
        ):
            if len(pages) == 1:
                raise EmptyDocument("The page is blank; there is nothing to read.")
            warnings.append(f"Page {index} appears to be blank.")

    return LoadedDocument(
        name=name,
        kind=kind,
        source_mime=mime,
        raw=data,
        pages=pages,
        page_count=page_count,
        sha256=hashlib.sha256(data).hexdigest(),
        warnings=warnings,
    )


def load_path(path: Path, **kwargs: object) -> LoadedDocument:
    return load_document(path.read_bytes(), path.name, **kwargs)  # type: ignore[arg-type]
