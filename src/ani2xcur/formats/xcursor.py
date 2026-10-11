"""XCursor (``Xcur``) binary reader and writer.

Reference: the file format understood by ``libXcursor``. A file is a 16 byte
header, a table of contents (one 12 byte entry per chunk) and a list of image
chunks. Every image chunk carries a nominal size, hotspot, delay and
``width * height`` 32-bit ARGB pixels.

Pixels are stored premultiplied and, on little-endian hosts, laid out as
``B, G, R, A`` bytes -- which is exactly Pillow's ``BGRA`` raw mode. The writer
therefore expects **premultiplied** RGBA images (as produced by
:func:`ani2xcur.render.resize_cursor`).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from ..model import Cursor

MAGIC = b"Xcur"
VERSION = 0x0001_0000
FILE_HEADER = struct.Struct("<4sIII")
TOC_ENTRY = struct.Struct("<III")
IMAGE_TYPE = 0xFFFD_0002
IMAGE_HEADER = struct.Struct("<9I")
IMAGE_HEADER_SIZE = IMAGE_HEADER.size  # 36


@dataclass(frozen=True)
class XcursorImage:
    """One image chunk read back from an XCursor file."""

    nominal: int
    width: int
    height: int
    hotspot: tuple[int, int]
    delay_ms: int
    pixels: bytes  # premultiplied, ``width * height * 4`` bytes in BGRA order

    def to_pil(self) -> Image.Image:
        """Decode the chunk into a premultiplied RGBA image."""
        return Image.frombytes("RGBA", (self.width, self.height), self.pixels, "raw", "BGRA")


def _image_pixels(image: Image.Image) -> bytes:
    return image.convert("RGBA").tobytes("raw", "BGRA")


def write(cursor: Cursor) -> bytes:
    """Serialise a rendered cursor into XCursor bytes."""
    chunks: list[tuple[int, bytes]] = []
    for frame in cursor.frames:
        for nominal in sorted(frame.images):
            image = frame.images[nominal]
            header = IMAGE_HEADER.pack(
                IMAGE_HEADER_SIZE,
                IMAGE_TYPE,
                nominal,
                1,
                image.width,
                image.height,
                image.hotspot[0],
                image.hotspot[1],
                frame.delay_ms,
            )
            chunks.append((nominal, header + _image_pixels(image.image)))

    file_header = FILE_HEADER.pack(MAGIC, FILE_HEADER.size, VERSION, len(chunks))

    offset = FILE_HEADER.size + TOC_ENTRY.size * len(chunks)
    toc = bytearray()
    for nominal, chunk in chunks:
        toc += TOC_ENTRY.pack(IMAGE_TYPE, nominal, offset)
        offset += len(chunk)

    return bytes(file_header) + bytes(toc) + b"".join(chunk for _, chunk in chunks)


def write_file(cursor: Cursor, path: str | Path) -> None:
    """Write a rendered cursor to ``path`` (parent directories are created)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(write(cursor))


def read(data: bytes) -> list[XcursorImage]:
    """Parse XCursor bytes into a list of image chunks, in file order."""
    if len(data) < FILE_HEADER.size:
        raise ValueError("not an XCursor file: too short")

    magic, header_size, version, toc_entries = FILE_HEADER.unpack_from(data, 0)
    if magic != MAGIC:
        raise ValueError("not an XCursor file: bad magic")
    if header_size != FILE_HEADER.size:
        raise ValueError(f"unsupported XCursor header size: {header_size}")
    if version != VERSION:
        raise ValueError(f"unsupported XCursor version: 0x{version:08x}")

    images: list[XcursorImage] = []
    for index in range(toc_entries):
        type_, subtype, position = TOC_ENTRY.unpack_from(
            data, FILE_HEADER.size + TOC_ENTRY.size * index
        )
        if type_ != IMAGE_TYPE:
            continue

        (
            size,
            image_type,
            nominal,
            image_version,
            width,
            height,
            xhot,
            yhot,
            delay_ms,
        ) = IMAGE_HEADER.unpack_from(data, position)
        if size != IMAGE_HEADER_SIZE or image_type != type_ or image_version != 1:
            raise ValueError(f"malformed XCursor image chunk at {position}")
        if nominal != subtype:
            raise ValueError(f"mismatched nominal size at {position}")

        start = position + size
        length = width * height * 4
        pixels = data[start : start + length]
        if len(pixels) != length:
            raise ValueError(f"truncated XCursor image chunk at {position}")

        images.append(
            XcursorImage(
                nominal=subtype,
                width=width,
                height=height,
                hotspot=(xhot, yhot),
                delay_ms=delay_ms,
                pixels=pixels,
            )
        )

    return images


def read_file(path: str | Path) -> list[XcursorImage]:
    """Read and parse an XCursor file from disk."""
    return read(Path(path).read_bytes())
