"""Compatibility and robustness tests for the conversion pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ani2xcur.cli import main
from ani2xcur.log import Logger
from ani2xcur.pipeline import convert, find_inf


def _write_inf(path: Path, **entries: str) -> None:
    lines = ["[Strings]", 'SCHEME_NAME = "T"']
    lines += [f'{key} = "{value}"' for key, value in entries.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_case_insensitive_filename(tmp_path: Path, zutomayo_dir: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _write_inf(src / "install.inf", pointer="NORMAL.ANI")
    shutil.copy(zutomayo_dir / "Normal.ani", src / "normal.ani")

    out = tmp_path / "out"
    assert main(["convert", "-i", str(src), "-o", str(out), "--sizes", "16"]) == 0
    assert (out / "T" / "cursors" / "arrow").is_file()


def test_single_file_input(tmp_path: Path, zutomayo_dir: Path) -> None:
    source = tmp_path / "Widget.ani"
    shutil.copy(zutomayo_dir / "Normal.ani", source)

    out = tmp_path / "out"
    assert main(["convert", "-i", str(source), "-o", str(out), "--sizes", "16"]) == 0
    assert (out / "Widget" / "cursors" / "Widget").is_file()


def test_image_source(tmp_path: Path, png_bytes) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _write_inf(src / "install.inf", pointer="art.png")
    (src / "art.png").write_bytes(png_bytes(32, (1, 2, 3, 255)))

    out = tmp_path / "out"
    assert main(["convert", "-i", str(src), "-o", str(out), "--sizes", "16"]) == 0
    assert (out / "T" / "cursors" / "arrow").is_file()


def test_nested_inf(tmp_path: Path, zutomayo_dir: Path) -> None:
    nested = tmp_path / "root" / "deep" / "theme"
    nested.mkdir(parents=True)
    _write_inf(nested / "install.inf", pointer="Normal.ani")
    shutil.copy(zutomayo_dir / "Normal.ani", nested / "Normal.ani")

    out = tmp_path / "out"
    assert main(["convert", "-i", str(tmp_path / "root"), "-o", str(out), "--sizes", "16"]) == 0
    assert (out / "T" / "cursors" / "arrow").is_file()


def test_multiple_inf_picks_shallowest(tmp_path: Path, zutomayo_dir: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    _write_inf(root / "top.inf", pointer="Normal.ani")
    deep = root / "sub" / "deep"
    deep.mkdir(parents=True)
    _write_inf(deep / "other.inf", pointer="Normal.ani")
    shutil.copy(zutomayo_dir / "Normal.ani", root / "Normal.ani")

    assert find_inf(root) == root / "top.inf"


def test_multiple_inf_same_level_errors(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    _write_inf(root / "a.inf")
    _write_inf(root / "b.inf")

    with pytest.raises(ValueError):
        find_inf(root)


def test_explicit_inf(tmp_path: Path, zutomayo_dir: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    _write_inf(root / "theme.inf", pointer="Normal.ani")
    shutil.copy(zutomayo_dir / "Normal.ani", root / "Normal.ani")

    out = tmp_path / "out"
    code = main(
        [
            "convert",
            "-i",
            str(root),
            "-o",
            str(out),
            "--sizes",
            "16",
            "--inf",
            str(root / "theme.inf"),
        ]
    )
    assert code == 0
    assert (out / "T" / "cursors" / "arrow").is_file()


def test_bad_cursor_is_skipped(tmp_path: Path, zutomayo_dir: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _write_inf(src / "install.inf", pointer="Normal.ani", help="broken.ani")
    shutil.copy(zutomayo_dir / "Normal.ani", src / "Normal.ani")
    (src / "broken.ani").write_bytes(b"not a cursor")

    out = tmp_path / "out"
    result = convert(src, out, sizes=[16], logger=Logger("fatal"))

    assert result.failed == ["help"]
    assert (out / "T" / "cursors" / "arrow").is_file()
    assert not (out / "T" / "cursors" / "help").exists()
    # a failed entry surfaces as a non-zero exit code
    assert main(["convert", "-i", str(src), "-o", str(out), "--sizes", "16"]) == 1


def test_missing_file_is_skipped(tmp_path: Path, zutomayo_dir: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _write_inf(src / "install.inf", pointer="Normal.ani", help="nope.ani")
    shutil.copy(zutomayo_dir / "Normal.ani", src / "Normal.ani")

    result = convert(src, tmp_path / "out", sizes=[16], logger=Logger("fatal"))
    assert result.skipped == ["help"]
