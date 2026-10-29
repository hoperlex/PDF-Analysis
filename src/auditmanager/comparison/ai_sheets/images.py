"""The pictures of a packet: stacking the crops of A and B, frames on the overview, fitting a request into the limits
(`CMP-VC-AISHEET-01`; ``Pillow`` only, which the product already pins).

The original drew captions with OpenCV (``images.py``, ``pack.py:150-163``). A caption would need a Cyrillic font and a model reads the
prompt's own list of images ("I2 -- place O3: above A, below B") better than a stamped label, so the pictures carry no text: a frame
on the overview carries its candidate's number in the font that ships with Pillow (digits and Latin only), and nothing else is drawn.
Every PNG is encoded the same way (no metadata chunk, no timestamp, a pinned compression level), so the same crops give the same bytes
and the same request digest.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from typing import Any, Final

from PIL import Image, ImageDraw

__all__ = [
    "BYTES_PER_PIXEL_ESTIMATE",
    "FRAME_COLOUR",
    "PNG_COMPRESS_LEVEL",
    "decode",
    "draw_frames",
    "encode_png",
    "estimate_bytes",
    "fit_long_side",
    "fit_total_bytes",
    "hstack",
    "vstack",
]

PNG_COMPRESS_LEVEL: Final[int] = 6
_PNG_SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"
FRAME_COLOUR: Final[tuple[int, int, int]] = (220, 30, 30)
_GAP_COLOUR: Final[tuple[int, int, int]] = (120, 120, 120)
#: What an estimate prices a rendered picture at, per pixel. `[own design]`: a drawing crop is mostly white and compresses far below
#: this; the figure is above what the corpus measures, and the request is held to the limits by :func:`fit_total_bytes` whatever it is.
BYTES_PER_PIXEL_ESTIMATE: Final[float] = 0.6


def encode_png(image: Image.Image) -> bytes:
    """The image as PNG bytes: RGB, no metadata, a pinned compression level (the same input gives the same bytes)."""
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False)
    return buffer.getvalue()


def decode(data: bytes) -> Image.Image:
    if not data.startswith(_PNG_SIGNATURE):
        raise ValueError("not a PNG")
    image = Image.open(io.BytesIO(data))
    image.load()
    return image.convert("RGB")


def vstack(images: Sequence[Image.Image], gap: int = 8) -> Image.Image:
    """The images one under another, left aligned, with a grey gap (``pack.py`` ``img.stack``)."""
    width = max(i.width for i in images)
    height = sum(i.height for i in images) + gap * (len(images) - 1)
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    y = 0
    for index, image in enumerate(images):
        canvas.paste(image, (0, y))
        y += image.height
        if index < len(images) - 1:
            ImageDraw.Draw(canvas).rectangle([0, y, width, y + gap - 1], fill=_GAP_COLOUR)
            y += gap
    return canvas


def hstack(images: Sequence[Image.Image], gap: int = 8) -> Image.Image:
    """The images side by side, top aligned, with a grey gap (``pack.py:52-61`` ``_hstack``)."""
    height = max(i.height for i in images)
    width = sum(i.width for i in images) + gap * (len(images) - 1)
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    x = 0
    for index, image in enumerate(images):
        canvas.paste(image, (x, 0))
        x += image.width
        if index < len(images) - 1:
            ImageDraw.Draw(canvas).rectangle([x, 0, x + gap - 1, height], fill=_GAP_COLOUR)
            x += gap
    return canvas


def fit_long_side(image: Image.Image, max_px: int) -> Image.Image:
    """The image reduced (never enlarged) so its long side is at most ``max_px`` (``pack.py:165-166``)."""
    long_side = max(image.size)
    if long_side <= max_px:
        return image
    scale = max_px / long_side
    return image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.LANCZOS)


def draw_frames(image: Image.Image, frames: Sequence[tuple[str, Sequence[float]]]) -> Image.Image:
    """A copy of the overview with a frame and its label (``O3``) for each candidate (``pack.py:120-136``). ``frames`` are
    ``(label, [x0, y0, x1, y1])`` in the pixels of the image."""
    canvas = image.copy()
    draw = ImageDraw.Draw(canvas)
    for label, box in frames:
        x0, y0, x1, y1 = (float(v) for v in box)
        draw.rectangle([x0, y0, x1, y1], outline=FRAME_COLOUR, width=3)
        draw.text((x0 + 4, max(0.0, y0 - 12)), label, fill=FRAME_COLOUR)
    return canvas


def estimate_bytes(width_px: int, height_px: int) -> int:
    """What an estimate counts for one picture of this size."""
    return max(1024, int(width_px * height_px * BYTES_PER_PIXEL_ESTIMATE))


def fit_total_bytes(pngs: Sequence[bytes], *, per_image: int, total: int, extra: dict[str, Any] | None = None) -> list[bytes]:
    """The pictures held to the limits of a request: each at most ``per_image`` bytes and all together at most ``total``. A picture
    that is over is reduced by a fifth at a time until the limits hold; the order is kept. ``ValueError`` when one cannot be made to
    fit (a picture of a few hundred pixels is never over a limit of MiB, so this means a defect)."""
    images = [decode(data) for data in pngs]
    out = list(pngs)
    for _ in range(40):
        sizes = [len(d) for d in out]
        if all(s <= per_image for s in sizes) and sum(sizes) <= total:
            return out
        worst = max(range(len(out)), key=lambda i: sizes[i])
        image = images[worst]
        images[worst] = image.resize((max(1, int(image.width * 0.8)), max(1, int(image.height * 0.8))), Image.Resampling.LANCZOS)
        out[worst] = encode_png(images[worst])
    raise ValueError("the pictures of a request cannot be fitted into the limits")
