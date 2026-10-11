"""Data model for Windows cursors and their rendered counterparts.

A :class:`Cursor` is a list of :class:`CursorFrame` animation steps; every frame
holds one or more rasters (:class:`CursorImage`) keyed by their *nominal* size.
A static ``.cur`` is simply a cursor with a single frame and a single size.

Alpha convention:
    * cursors produced by parsing (``formats.win.load_cursor``) hold straight
      (non-premultiplied) RGBA pixels, just like the source icons;
    * cursors produced by :func:`ani2xcur.render.resize_cursor` hold
      **premultiplied** RGBA pixels, ready for the XCursor writer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class CursorImage:
    """A single raster of a cursor."""

    nominal: int
    width: int
    height: int
    hotspot: tuple[int, int]
    image: Image.Image  # RGBA


@dataclass
class CursorFrame:
    """One animation step: the rasters for each nominal size plus its delay."""

    delay_ms: int = 0
    images: dict[int, CursorImage] = field(default_factory=dict)


@dataclass
class Cursor:
    """A parsed or rendered cursor."""

    name: str
    frames: list[CursorFrame] = field(default_factory=list)
    source: Path | None = None

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def is_animated(self) -> bool:
        return len(self.frames) > 1

    @property
    def nominal_sizes(self) -> list[int]:
        """All nominal sizes present across every frame, sorted."""
        sizes: set[int] = set()
        for frame in self.frames:
            sizes.update(frame.images)
        return sorted(sizes)
