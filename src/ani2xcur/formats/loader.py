"""Load a cursor from any supported source file.

Windows cursor schemes normally reference ``.ani`` / ``.ico`` / ``.cur`` files,
but a few ship plain images (``.png`` / ``.bmp`` / ...). Those are loaded as a
single static frame; the hotspot is unknown and defaults to the top-left corner.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from ..model import Cursor, CursorFrame, CursorImage
from .win import load_cursor

IMAGE_SUFFIXES = frozenset({".png", ".bmp", ".gif", ".jpeg", ".jpg", ".webp"})


def load_image(path: str | Path, name: str | None = None) -> Cursor:
    """Load a plain image file as a single static cursor frame."""
    path = Path(path)
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
    width, height = rgba.size
    nominal = max(width, height)
    frame = CursorFrame(
        delay_ms=0,
        images={nominal: CursorImage(nominal, width, height, (0, 0), rgba)},
    )
    return Cursor(name=name or path.name, frames=[frame], source=path)


def load_source(path: str | Path, name: str | None = None) -> Cursor:
    """Load a cursor from a container (ANI/ICO/CUR) or a plain image file."""
    path = Path(path)
    if path.suffix.lower() in IMAGE_SUFFIXES:
        return load_image(path, name)
    return load_cursor(path, name)
