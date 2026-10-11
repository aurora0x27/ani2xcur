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

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def decode_image(blob: bytes) -> Image.Image:
    """Decode a single-image ICO/CUR blob into straight RGBA pixels.

    Pillow's CUR plugin only understands DIB payloads, so PNG entries (allowed
    by the ICO/CUR spec and seen in the wild) are decoded straight from the
    embedded PNG stream.
    """
    try:
        with Image.open(io.BytesIO(blob)) as image:
            return image.convert("RGBA")
    except OSError:
        offset = blob.find(PNG_SIGNATURE)
        if offset == -1:
            raise
        with Image.open(io.BytesIO(blob[offset:])) as image:
            return image.convert("RGBA")


def _kind(data: bytes) -> str:
    if data[:4] == b"RIFF":
        return "ani"
    if len(data) >= 4 and data[2:4] in (b"\x01\x00", b"\x02\x00"):
        return "ico" if data[2] == 1 else "cur"
    return "unknown"


def describe(path: str | Path) -> dict[str, object]:
    """Return container metadata for an ANI / ICO / CUR file (no pixel decoding)."""
    path = Path(path)
    data = path.read_bytes()
    parsed = _anicore.parse(data)
    return {
        "path": str(path),
        "kind": _kind(data),
        "width": parsed.width,
        "height": parsed.height,
        "hotspot": [parsed.hotspot_x, parsed.hotspot_y],
        "frames": len(parsed.frames),
        "sizes": sorted({image.nominal for frame in parsed.frames for image in frame.images}),
        "delays_ms": sorted({frame.delay_ms for frame in parsed.frames}),
        "layers": [len(frame.images) for frame in parsed.frames],
    }


def load_cursor(path: str | Path, name: str | None = None) -> Cursor:
    """Parse an ANI / ICO / CUR file into a :class:`Cursor`."""
    path = Path(path)
    parsed = _anicore.parse(path.read_bytes())

    frames: list[CursorFrame] = []
    for raw_frame in parsed.frames:
        images: dict[int, CursorImage] = {}
        for raw_image in raw_frame.images:
            existing = images.get(raw_image.nominal)
            if existing is not None and existing.width * existing.height >= (
                raw_image.width * raw_image.height
            ):
                continue  # keep the larger raster when a size is duplicated
            images[raw_image.nominal] = CursorImage(
                nominal=raw_image.nominal,
                width=raw_image.width,
                height=raw_image.height,
                hotspot=(raw_image.hotspot_x, raw_image.hotspot_y),
                image=decode_image(raw_image.blob),
            )
        frames.append(CursorFrame(delay_ms=raw_frame.delay_ms, images=images))

    return Cursor(name=name or path.name, frames=frames, source=path)
