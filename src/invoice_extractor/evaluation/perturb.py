"""Synthetic degradations of the labelled documents, for stress-testing.

The clean labelled set is small and mostly easy, so it says little about where the
pipeline breaks. Each perturbation re-renders a labelled document as an image-only
("scanned") PDF with one controlled defect. The ground truth is unchanged, so the
degraded copies can be scored exactly like the originals.
"""

from __future__ import annotations

import io
import random
from collections.abc import Callable
from pathlib import Path

import pymupdf
from PIL import Image, ImageChops, ImageFilter, ImageOps

RENDER_DPI = 150


def _rotate(degrees_clockwise: int) -> Callable[[Image.Image], Image.Image]:
    return lambda image: image.rotate(-degrees_clockwise, expand=True, fillcolor="white")


def _blur(image: Image.Image) -> Image.Image:
    return image.filter(ImageFilter.GaussianBlur(radius=2.4))


def _low_resolution(image: Image.Image) -> Image.Image:
    # Roughly a 55 DPI fax: small, then JPEG-crushed, then scaled back up.
    small = image.resize((image.width * 3 // 8, image.height * 3 // 8), Image.Resampling.BILINEAR)
    buffer = io.BytesIO()
    small.convert("RGB").save(buffer, format="JPEG", quality=25)
    return Image.open(buffer).resize(image.size, Image.Resampling.BILINEAR)


def _skew(image: Image.Image) -> Image.Image:
    return image.rotate(7, expand=True, fillcolor="white", resample=Image.Resampling.BICUBIC)


def _fax(image: Image.Image) -> Image.Image:
    """A fax: ~100 DPI, hard 1-bit threshold, speckle noise."""
    gray = ImageOps.grayscale(image)
    small = gray.resize((gray.width * 2 // 3, gray.height * 2 // 3), Image.Resampling.BILINEAR)
    bits = small.point(lambda value: 255 if value > 150 else 0)
    rng = random.Random(7)
    pixels = bits.load()
    for _ in range(int(bits.width * bits.height * 0.002)):
        pixels[rng.randrange(bits.width), rng.randrange(bits.height)] = 0
    return bits.resize(image.size, Image.Resampling.NEAREST).convert("RGB")


def _phone_photo(image: Image.Image) -> Image.Image:
    """A hand-held photo of the page on a desk: keystone, uneven light, soft focus."""
    width, height = image.size
    margin_x, margin_y = width * 0.09, height * 0.06
    source_quad = (
        -margin_x, -margin_y * 0.4,
        -margin_x * 0.3, height + margin_y,
        width + margin_x * 0.6, height + margin_y * 0.5,
        width + margin_x, -margin_y,
    )  # fmt: skip
    warped = image.transform(
        image.size, Image.Transform.QUAD, data=source_quad,
        resample=Image.Resampling.BICUBIC, fillcolor=(112, 96, 82),
    )  # fmt: skip
    # Light falls off toward one corner: blend a horizontal and a vertical ramp.
    ramp = Image.linear_gradient("L")
    falloff = ImageChops.add(ramp.rotate(90).resize(image.size), ramp.resize(image.size), scale=2.0)
    light = falloff.point(lambda value: 150 + value * 105 // 255).convert("RGB")
    lit = ImageChops.multiply(warped, light).filter(ImageFilter.GaussianBlur(radius=1.1))
    buffer = io.BytesIO()
    lit.save(buffer, format="JPEG", quality=55)
    return Image.open(buffer).convert("RGB")


# Designed and inspected while building v3 of the pipeline.
PERTURBATIONS: dict[str, Callable[[Image.Image], Image.Image]] = {
    "rotate90": _rotate(90),
    "rotate270": _rotate(270),
    "rotate180": _rotate(180),
    "skew7": _skew,
    "blur": _blur,
    "lowres": _low_resolution,
    # Held out: added after v3 was designed, never used to tune it.
    "fax": _fax,
    "photo": _phone_photo,
}
HELD_OUT = frozenset({"fax", "photo"})


def _pages(path: Path) -> list[Image.Image]:
    if path.suffix.lower() == ".pdf":
        with pymupdf.open(path) as pdf:
            images = []
            for page in pdf:
                pixmap = page.get_pixmap(dpi=RENDER_DPI)
                images.append(Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples))
            return images
    return [ImageOps.exif_transpose(Image.open(path)).convert("RGB")]


def perturbed_pdf(path: Path, kind: str) -> bytes:
    """Return an image-only PDF of ``path`` with the ``kind`` defect applied to every page."""
    transform = PERTURBATIONS[kind]
    output = pymupdf.open()
    for image in _pages(path):
        degraded = transform(image).convert("RGB")
        buffer = io.BytesIO()
        degraded.save(buffer, format="JPEG", quality=85)
        page = output.new_page(
            width=degraded.width * 72 / RENDER_DPI, height=degraded.height * 72 / RENDER_DPI
        )
        page.insert_image(page.rect, stream=buffer.getvalue())
    data = output.tobytes(garbage=3, deflate=True)
    output.close()
    return data
