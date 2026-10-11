"""End-to-end regression tests over the two bundled sample themes.

Each sample is converted with the default sizes and the produced theme is
checked for structure (real cursors + alias symlinks + index.theme), sizes,
animation frames, delays and XCursor readability.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ani2xcur import roles
from ani2xcur.cli import main
from ani2xcur.formats import xcursor
from ani2xcur.log import Logger
from ani2xcur.pipeline import convert
from ani2xcur.render import DEFAULT_SIZES


def _expected_alias_count() -> int:
    return sum(
        len([name for name in role.x11 if name != role.canonical]) for role in roles.load_roles()
    )


def _frames(images: list[xcursor.XcursorImage], nominal: int) -> list[xcursor.XcursorImage]:
    return [image for image in images if image.nominal == nominal]


def _assert_theme(theme_dir: Path, expected_cursors: int) -> Path:
    assert theme_dir.is_dir()
    index = (theme_dir / "index.theme").read_text(encoding="utf-8")
    assert index.startswith("[Icon Theme]")
    assert f"Name={theme_dir.name}" in index
    assert (theme_dir / "cursor.theme").is_file()

    cursors = theme_dir / "cursors"
    real = [path for path in cursors.iterdir() if not path.is_symlink()]
    links = [path for path in cursors.iterdir() if path.is_symlink()]
    assert len(real) == expected_cursors
    assert len(links) == _expected_alias_count()
    for link in links:
        assert link.resolve().is_file()

    assert os.readlink(cursors / "left_ptr") == "arrow"
    assert os.readlink(cursors / "pointer") == "link"

    for cursor_file in real:
        images = xcursor.read_file(cursor_file)
        assert images, f"{cursor_file} has no images"
        assert {image.nominal for image in images} == set(DEFAULT_SIZES)
    return cursors


def test_zutomayo_end_to_end(tmp_path: Path, zutomayo_dir: Path) -> None:
    result = convert(zutomayo_dir, tmp_path / "out", logger=Logger("fatal"))
    cursors = _assert_theme(result.theme_dir, expected_cursors=17)

    # Animated: Normal.ani -> arrow (8 frames, 100 ms each).
    images = xcursor.read_file(cursors / "arrow")
    assert len(_frames(images, 32)) == 8
    assert all(image.delay_ms == 100 for image in images)
    # Palettized source: the AND mask must survive as real transparency.
    assert 0 in images[0].pixels[3::4]

    # Static: Person.cur -> person (single frame, no delay).
    person = xcursor.read_file(cursors / "person")
    assert len(person) == len(DEFAULT_SIZES)
    assert all(image.delay_ms == 0 for image in person)
    assert all((image.width, image.height) == (image.nominal, image.nominal) for image in person)


def test_miku_end_to_end(tmp_path: Path, miku_dir: Path) -> None:
    result = convert(miku_dir, tmp_path / "out", logger=Logger("fatal"))
    cursors = _assert_theme(result.theme_dir, expected_cursors=17)

    # Animated: Normal Select.ani -> arrow (12 frames, 7 jiffies -> 117 ms).
    images = xcursor.read_file(cursors / "arrow")
    assert len(_frames(images, 32)) == 12
    assert all(image.delay_ms == 117 for image in images)
    assert 0 in images[0].pixels[3::4]

    # Work.ani -> work (23 frames) and a hotspot scaled from the 160px source.
    work = _frames(xcursor.read_file(cursors / "work"), 32)
    assert len(work) == 23
    assert work[0].hotspot == (2, 2)  # 8*32/160, 9*32/160

    # Static: Person Select.ani -> person (1 frame, 6 jiffies -> 100 ms).
    person = xcursor.read_file(cursors / "person")
    assert len(person) == len(DEFAULT_SIZES)
    assert all(image.delay_ms == 100 for image in person)


@pytest.mark.parametrize("fixture_name", ["zutomayo_dir", "miku_dir"])
def test_cli_convert_exit_code(request, tmp_path: Path, fixture_name: str) -> None:
    root = request.getfixturevalue(fixture_name)
    assert main(["convert", "-i", str(root), "-o", str(tmp_path / "out")]) == 0
