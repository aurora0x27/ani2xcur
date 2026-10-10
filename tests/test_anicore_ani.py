"""ANI (RIFF/ACON) parsing tests against the bundled sample themes."""

from __future__ import annotations

from pathlib import Path

import pytest

from ani2xcur import _anicore


def parse(path: Path) -> _anicore.Cursor:
    return _anicore.parse(path.read_bytes())


def test_zutomayo_normal_ani(zutomayo_dir: Path) -> None:
    cursor = parse(zutomayo_dir / "Normal.ani")

    # The header leaves the logical size unset; the real size comes from the icons.
    assert (cursor.width, cursor.height) == (32, 32)
    assert len(cursor.frames) == 8

    for frame in cursor.frames:
        assert len(frame.images) == 1
        assert frame.delay_ms == 100  # jifRate 6 jiffies -> 100 ms

    image = cursor.frames[0].images[0]
    assert (image.nominal, image.width, image.height) == (32, 32, 32)
    assert (image.hotspot_x, image.hotspot_y) == (1, 1)
    assert image.blob[:4] == b"\x00\x00\x02\x00"  # CUR header
    assert (cursor.hotspot_x, cursor.hotspot_y) == (image.hotspot_x, image.hotspot_y)


def test_miku_work_ani(miku_dir: Path) -> None:
    cursor = parse(next(p for p in miku_dir.rglob("Work.ani")))

    assert (cursor.width, cursor.height) == (160, 160)
    assert len(cursor.frames) == 23

    for frame in cursor.frames:
        assert len(frame.images) == 1
        assert frame.delay_ms == 117  # 7 jiffies -> 116.7 ms, rounded

    image = cursor.frames[0].images[0]
    assert (image.width, image.height) == (160, 160)
    assert image.nominal == 160
    assert (image.hotspot_x, image.hotspot_y) == (8, 9)


def test_miku_seq_and_rate_are_honoured(miku_dir: Path) -> None:
    # "Diagonal Resize 1.ani" has seq == identity and rate == 9 jiffies.
    cursor = parse(next(p for p in miku_dir.rglob("Diagonal Resize 1.ani")))
    assert len(cursor.frames) == 4
    assert all(frame.delay_ms == 150 for frame in cursor.frames)
    image = cursor.frames[0].images[0]
    assert (image.hotspot_x, image.hotspot_y) == (77, 79)


@pytest.mark.parametrize("fixture_name", ["miku_dir", "zutomayo_dir"])
def test_every_ani_parses(request, fixture_name: str, find_files) -> None:
    root = request.getfixturevalue(fixture_name)
    paths = find_files(root, "*.ani")
    assert paths, "expected at least one .ani sample"
    for path in paths:
        cursor = parse(path)
        assert cursor.frames, f"{path} produced no frames"
        for frame in cursor.frames:
            assert frame.images, f"{path} has a frame without images"
            for image in frame.images:
                assert image.width > 0 and image.height > 0
                assert image.blob, f"{path} produced an empty image blob"
