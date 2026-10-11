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


def _as_icon(blob: bytes) -> bytes:
    """Re-view a single-image ICO/CUR blob as an ICO.

    Pillow's CUR plugin only applies the 1-bit AND mask for ``1``/``L`` modes,
    so palettized (``P``) cursors -- common in the wild, e.g. Zutomayo -- come
    back fully opaque (a black background). Pillow's ICO plugin applies the mask
    for every bit depth, so we rewrite the container type and directory fields
    (planes / bit depth taken from the DIB header) before decoding. The hotspot
    is reported separately by the C core, so nothing is lost.
    """
    if len(blob) < 22 or blob[2:4] not in (b"\x01\x00", b"\x02\x00"):
        return blob  # not one of our single-image containers

    payload_offset = int.from_bytes(blob[18:22], "little")
    if payload_offset + 16 > len(blob):
        return blob
    payload = blob[payload_offset:]

    if payload[:8] == PNG_SIGNATURE:
        planes, bit_count = 1, 32
    else:
        if int.from_bytes(payload[0:4], "little") < 40:  # not a BITMAPINFOHEADER
            return blob
        planes = int.from_bytes(payload[12:14], "little") or 1
        bit_count = int.from_bytes(payload[14:16], "little")
        if bit_count == 0:
            return blob

    data = bytearray(blob)
    data[2:4] = b"\x01\x00"  # ICO
    data[10:12] = planes.to_bytes(2, "little")
    data[12:14] = bit_count.to_bytes(2, "little")
    return bytes(data)


def decode_image(blob: bytes) -> Image.Image:
    """Decode a single-image ICO/CUR blob into straight RGBA pixels.

    DIB payloads are decoded through the ICO path so the AND mask is applied
    (see :func:`_as_icon`); PNG payloads are a fallback for anything Pillow's
    icon plugin cannot read.
    """
    try:
        with Image.open(io.BytesIO(_as_icon(blob))) as image:
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
