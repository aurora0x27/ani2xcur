"""Tests for the cursor model and the multi-size renderer."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from ani2xcur.formats.win import load_cursor
from ani2xcur.model import Cursor, CursorFrame, CursorImage
from ani2xcur.render import DEFAULT_SIZES, premultiply, resize_cursor


def _solid(size: int, color: tuple[int, int, int, int]) -> Image.Image:
    return Image.new("RGBA", (size, size), color)


# --- parsing into the model -------------------------------------------------


def test_load_static_cur(zutomayo_dir: Path) -> None:
    cursor = load_cursor(zutomayo_dir / "Person.cur")
    assert cursor.name == "Person.cur"
    assert cursor.frame_count == 1
    assert not cursor.is_animated
    assert cursor.nominal_sizes == [42]
    frame = cursor.frames[0]
    assert frame.delay_ms == 0
    image = frame.images[42]
    assert image.hotspot == (10, 9)
    assert image.image.mode == "RGBA"


def test_load_animated_ani(zutomayo_dir: Path) -> None:
    cursor = load_cursor(zutomayo_dir / "Normal.ani")
    assert cursor.frame_count == 8
    assert cursor.is_animated
    assert cursor.nominal_sizes == [32]
    assert all(frame.delay_ms == 100 for frame in cursor.frames)


# --- rendering --------------------------------------------------------------


def test_resize_produces_every_size(zutomayo_dir: Path) -> None:
    cursor = load_cursor(zutomayo_dir / "Normal.ani")
    rendered = resize_cursor(cursor)

    assert rendered.nominal_sizes == list(DEFAULT_SIZES)
    assert rendered.frame_count == cursor.frame_count

    for frame in rendered.frames:
        assert frame.delay_ms == 100
        assert set(frame.images) == set(DEFAULT_SIZES)
        for nominal, image in frame.images.items():
            assert image.nominal == nominal
            assert (image.width, image.height) == (nominal, nominal)
            assert image.image.size == (nominal, nominal)
            assert image.image.mode == "RGBA"


def test_resize_scales_hotspot(zutomayo_dir: Path) -> None:
    cursor = load_cursor(zutomayo_dir / "Normal.ani")  # hotspot (1, 1), 32px
    rendered = resize_cursor(cursor, [16, 32, 64])
    frame = rendered.frames[0]
    assert frame.images[16].hotspot == (1, 1)  # 1 * 16/32 = 0.5 -> 1
    assert frame.images[32].hotspot == (1, 1)
    assert frame.images[64].hotspot == (2, 2)  # 1 * 64/32 = 2


def test_resize_scales_hotspot_non_square_ratio(miku_dir: Path) -> None:
    cursor = load_cursor(next(p for p in miku_dir.rglob("Work.ani")))  # hotspot (8, 9), 160px
    rendered = resize_cursor(cursor, [48, 96])
    assert rendered.frames[0].images[48].hotspot == (2, 3)  # 8*48/160=2.4, 9*48/160=2.7
    assert rendered.frames[0].images[96].hotspot == (5, 5)  # 8*96/160=4.8, 9*96/160=5.4


def test_no_upscale_skips_large_sizes(zutomayo_dir: Path) -> None:
    cursor = load_cursor(zutomayo_dir / "Normal.ani")  # only a 32px source
    rendered = resize_cursor(cursor, [16, 32, 64, 128], allow_upscale=False)
    assert rendered.nominal_sizes == [16, 32]


def test_picks_best_source_size() -> None:
    frame = CursorFrame(
        delay_ms=0,
        images={
            16: CursorImage(16, 16, 16, (1, 1), _solid(16, (255, 0, 0, 255))),
            32: CursorImage(32, 32, 32, (2, 2), _solid(32, (0, 255, 0, 255))),
        },
    )
    rendered = resize_cursor(Cursor(name="multi", frames=[frame]), [24])
    image = rendered.frames[0].images[24]

    # The 32px source wins (smallest source >= 24) and its colour is preserved.
    assert (image.width, image.height) == (24, 24)
    assert image.hotspot == (2, 2)  # 2 * 24/32 = 1.5 -> 2
    assert image.image.getpixel((12, 12))[:3] == (0, 255, 0)


def test_premultiply() -> None:
    premultiplied = premultiply(Image.new("RGBA", (1, 1), (200, 100, 50, 128)))
    red, green, blue, alpha = premultiplied.getpixel((0, 0))
    assert alpha == 128
    assert abs(red - round(200 * 128 / 255)) <= 1
    assert abs(green - round(100 * 128 / 255)) <= 1
    assert abs(blue - round(50 * 128 / 255)) <= 1


def test_opaque_and_transparent_survive_resize() -> None:
    opaque = CursorFrame(images={2: CursorImage(2, 2, 2, (0, 0), _solid(2, (255, 0, 0, 255)))})
    transparent = CursorFrame(images={4: CursorImage(4, 4, 4, (0, 0), _solid(4, (0, 0, 0, 0)))})
    rendered = resize_cursor(Cursor(name="c", frames=[opaque, transparent]), [8])

    assert rendered.frames[0].images[8].image.getpixel((4, 4)) == (255, 0, 0, 255)
    assert rendered.frames[1].images[8].image.getpixel((4, 4)) == (0, 0, 0, 0)
