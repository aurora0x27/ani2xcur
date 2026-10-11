"""Tests for the XCursor binary writer and reader."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from PIL import Image

from ani2xcur.formats import xcursor
from ani2xcur.formats.win import load_cursor
from ani2xcur.model import Cursor, CursorFrame, CursorImage
from ani2xcur.render import resize_cursor


def _one_pixel_cursor(pixel: tuple[int, int, int, int]) -> Cursor:
    image = Image.new("RGBA", (1, 1), pixel)
    frame = CursorFrame(delay_ms=5, images={1: CursorImage(1, 1, 1, (0, 0), image)})
    return Cursor(name="one", frames=[frame])


def test_header_and_pixel_layout() -> None:
    data = xcursor.write(_one_pixel_cursor((10, 20, 30, 40)))

    magic, header_size, version, toc_entries = struct.unpack_from("<4sIII", data, 0)
    assert magic == b"Xcur"
    assert header_size == 16
    assert version == 0x0001_0000
    assert toc_entries == 1

    images = xcursor.read(data)
    assert len(images) == 1
    image = images[0]
    assert (image.nominal, image.width, image.height, image.hotspot, image.delay_ms) == (
        1,
        1,
        1,
        (0, 0),
        5,
    )
    # Premultiplied ARGB stored little-endian == B, G, R, A bytes.
    assert image.pixels == bytes([30, 20, 10, 40])
    assert image.to_pil().getpixel((0, 0)) == (10, 20, 30, 40)


def test_animation_order_and_metadata(zutomayo_dir: Path) -> None:
    cursor = resize_cursor(load_cursor(zutomayo_dir / "Normal.ani"), [16, 32])
    images = xcursor.read(xcursor.write(cursor))

    assert len(images) == 16
    # Frame-major order: every frame contributes one chunk per nominal size.
    assert [image.nominal for image in images] == [16, 32] * 8
    assert all(image.delay_ms == 100 for image in images)

    for nominal in (16, 32):
        group = [image for image in images if image.nominal == nominal]
        assert len(group) == 8
        assert all((image.width, image.height) == (nominal, nominal) for image in group)


def test_hotspot_round_trip(zutomayo_dir: Path) -> None:
    cursor = resize_cursor(load_cursor(zutomayo_dir / "Normal.ani"), [64])
    images = xcursor.read(xcursor.write(cursor))
    assert all(image.hotspot == (2, 2) for image in images)  # 1 * 64/32


def test_write_and_read_file(tmp_path: Path, zutomayo_dir: Path) -> None:
    cursor = resize_cursor(load_cursor(zutomayo_dir / "Normal.ani"), [16])
    path = tmp_path / "nested" / "pointer"
    xcursor.write_file(cursor, path)

    assert path.is_file()
    images = xcursor.read_file(path)
    assert len(images) == 8


@pytest.mark.parametrize("blob", [b"", b"nope", b"Xcur" + b"\x00" * 20])
def test_read_rejects_malformed(blob: bytes) -> None:
    with pytest.raises(ValueError):
        xcursor.read(blob)
