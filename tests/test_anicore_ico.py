"""ICO / CUR (static cursor) parsing tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from ani2xcur import _anicore


def parse(path: Path) -> _anicore.Cursor:
    return _anicore.parse(path.read_bytes())


def _assert_static(zutomayo_dir: Path, name: str, size: int, hotspot: tuple[int, int]) -> None:
    cursor = parse(zutomayo_dir / name)

    assert len(cursor.frames) == 1
    frame = cursor.frames[0]
    assert frame.delay_ms == 0
    assert len(frame.images) == 1

    image = frame.images[0]
    assert (image.width, image.height) == (size, size)
    assert image.nominal == size
    assert (image.hotspot_x, image.hotspot_y) == hotspot
    assert image.blob[:4] == b"\x00\x00\x02\x00"  # CUR header
    # A single synthesized directory entry: header (6) + entry (16) + payload.
    assert len(image.blob) > 22

    # The synthesized blob points at the payload at offset 22.
    assert int.from_bytes(image.blob[18:22], "little") == 22


def test_person_cur(zutomayo_dir: Path) -> None:
    _assert_static(zutomayo_dir, "Person.cur", 42, (10, 9))


def test_pin_cur(zutomayo_dir: Path) -> None:
    _assert_static(zutomayo_dir, "Pin.cur", 36, (10, 6))


def test_icon_type_has_no_hotspot() -> None:
    # Minimal 1x1 ICO (type 1): a 22 byte header/entry with an empty payload.
    blob = (
        b"\x00\x00"  # reserved
        b"\x01\x00"  # type: icon
        b"\x01\x00"  # count
        b"\x01\x01\x00\x00"  # width, height, colors, reserved
        b"\x01\x00\x20\x00"  # planes, bit count
        b"\x00\x00\x00\x00"  # payload size
        b"\x16\x00\x00\x00"  # payload offset (22)
    )
    cursor = _anicore.parse(blob)
    image = cursor.frames[0].images[0]
    assert (image.hotspot_x, image.hotspot_y) == (0, 0)


@pytest.mark.parametrize(
    "blob",
    [
        b"",
        b"not a cursor file at all",
        b"\x00\x00\x02\x00\x00\x00",  # cursor header claiming zero entries
        b"\x01\x00\x01\x00\x01\x00",  # non-zero reserved field
        b"\x00\x00\x09\x00\x01\x00",  # unknown type (9)
    ],
)
def test_malformed_input_raises(blob: bytes) -> None:
    with pytest.raises(ValueError):
        _anicore.parse(blob)


def test_multi_image_cur(build_cur, png_bytes) -> None:
    blob = build_cur(
        [
            (16, (1, 1), png_bytes(16, (255, 0, 0, 255))),
            (32, (2, 2), png_bytes(32, (0, 255, 0, 255))),
        ]
    )
    cursor = _anicore.parse(blob)

    assert len(cursor.frames) == 1
    images = cursor.frames[0].images
    assert [(image.nominal, image.hotspot_x, image.hotspot_y) for image in images] == [
        (16, 1, 1),
        (32, 2, 2),
    ]
