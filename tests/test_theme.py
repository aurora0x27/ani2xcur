"""Tests for theme directory assembly (cursors, aliases and index.theme)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ani2xcur.formats import xcursor
from ani2xcur.formats.win import load_cursor
from ani2xcur.render import resize_cursor
from ani2xcur.theme import CursorTheme


def _pointer_cursor(zutomayo_dir: Path):
    return resize_cursor(load_cursor(zutomayo_dir / "Normal.ani"), [16, 32])


def test_write_theme_layout(tmp_path: Path, zutomayo_dir: Path) -> None:
    theme = CursorTheme(
        name="ZUTOMAYO",
        cursors={"pointer": _pointer_cursor(zutomayo_dir)},
        aliases={"pointer": ("left_ptr", "default", "pointer")},
    )
    theme_dir = theme.write(tmp_path)

    assert theme_dir == tmp_path / "ZUTOMAYO"
    cursors_dir = theme_dir / "cursors"
    assert (cursors_dir / "pointer").is_file()

    assert (cursors_dir / "left_ptr").is_symlink()
    assert os.readlink(cursors_dir / "left_ptr") == "pointer"
    assert (cursors_dir / "default").is_symlink()
    # the canonical name itself is a real file, not a self-referential link
    assert not (cursors_dir / "pointer").is_symlink()

    images = xcursor.read_file(cursors_dir / "pointer")
    assert {image.nominal for image in images} == {16, 32}


def test_index_theme_content(tmp_path: Path, zutomayo_dir: Path) -> None:
    theme = CursorTheme(
        name="Moos",
        cursors={"pointer": _pointer_cursor(zutomayo_dir)},
        comment="hello",
        inherits="Adwaita",
    )
    theme_dir = theme.write(tmp_path)

    index = (theme_dir / "index.theme").read_text(encoding="utf-8")
    assert index.startswith("[Icon Theme]\n")
    assert "Name=Moos" in index
    assert "Comment=hello" in index
    assert "Inherits=Adwaita" in index
    assert (theme_dir / "cursor.theme").read_text(encoding="utf-8") == index


def test_write_theme_rejects_shadowing_alias(tmp_path: Path, zutomayo_dir: Path) -> None:
    theme = CursorTheme(
        name="X",
        cursors={"arrow": _pointer_cursor(zutomayo_dir), "link": _pointer_cursor(zutomayo_dir)},
        aliases={"link": ("pointer",), "arrow": ("link",)},
    )
    with pytest.raises(ValueError):
        theme.write(tmp_path)


def test_write_theme_is_idempotent(tmp_path: Path, zutomayo_dir: Path) -> None:
    theme = CursorTheme(
        name="ZUTOMAYO",
        cursors={"pointer": _pointer_cursor(zutomayo_dir)},
        aliases={"pointer": ("left_ptr",)},
    )
    theme.write(tmp_path)
    theme_dir = theme.write(tmp_path)  # must not fail on the existing symlink

    assert (theme_dir / "cursors" / "left_ptr").is_symlink()


def test_safe_directory_name() -> None:
    assert CursorTheme(name="a/b\\c").directory == "a_b_c"
    assert CursorTheme(name="  ").directory == "theme"
