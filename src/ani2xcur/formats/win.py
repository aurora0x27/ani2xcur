"""Thin wrapper around the compiled ``_anicore`` core.

The C core returns each raster as a self-contained single-image ICO/CUR blob.
This module decodes those blobs with Pillow into straight RGBA
:class:`~ani2xcur.model.Cursor` objects.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from .. import _anicore
from ..model import Cursor, CursorFrame, CursorImage


def decode_image(blob: bytes) -> Image.Image:
    """Decode a single-image ICO/CUR blob into straight RGBA pixels."""
    with Image.open(io.BytesIO(blob)) as image:
        return image.convert("RGBA")


def load_cursor(path: str | Path, name: str | None = None) -> Cursor:
    """Parse an ANI / ICO / CUR file into a :class:`Cursor`."""
    path = Path(path)
    parsed = _anicore.parse(path.read_bytes())

    frames: list[CursorFrame] = []
    for raw_frame in parsed.frames:
        images: dict[int, CursorImage] = {}
        for raw_image in raw_frame.images:
            images[raw_image.nominal] = CursorImage(
                nominal=raw_image.nominal,
                width=raw_image.width,
                height=raw_image.height,
                hotspot=(raw_image.hotspot_x, raw_image.hotspot_y),
                image=decode_image(raw_image.blob),
            )
        frames.append(CursorFrame(delay_ms=raw_frame.delay_ms, images=images))

    return Cursor(name=name or path.name, frames=frames, source=path)
