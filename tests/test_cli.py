"""Tests for the command line interface and the conversion pipeline."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ani2xcur import roles
from ani2xcur.cli import main
from ani2xcur.log import Logger


def test_roles_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["roles", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == len(roles.load_roles())
    canonicals = {entry["canonical"] for entry in payload}
    assert {"arrow", "link", "work"} <= canonicals


def test_roles_plain(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["roles"]) == 0
    out = capsys.readouterr().out
    assert "arrow:" in out
    assert "left_ptr" in out


def test_inspect_file_json(zutomayo_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["inspect", str(zutomayo_dir / "Normal.ani"), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 1
    assert rows[0]["kind"] == "ani"
    assert rows[0]["frames"] == 8
    assert rows[0]["sizes"] == [32]
    assert rows[0]["hotspot"] == [1, 1]


def test_inspect_directory(zutomayo_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["inspect", str(zutomayo_dir)]) == 0
    out = capsys.readouterr().out
    assert "Normal.ani" in out
    assert "Person.cur" in out


def test_inspect_missing_path(tmp_path: Path) -> None:
    assert main(["inspect", str(tmp_path / "nope.ani")]) == 1


def test_convert_end_to_end(tmp_path: Path, zutomayo_dir: Path) -> None:
    out = tmp_path / "out"
    assert main(["convert", "-i", str(zutomayo_dir), "-o", str(out), "--sizes", "16,32"]) == 0

    theme_dir = out / "ZUTOMAYO"  # from SCHEME_NAME
    assert (theme_dir / "index.theme").is_file()
    cursors = theme_dir / "cursors"
    assert (cursors / "arrow").is_file()
    assert (cursors / "left_ptr").is_symlink()
    assert (cursors / "pointer").is_symlink()


def test_convert_name_override(tmp_path: Path, zutomayo_dir: Path) -> None:
    out = tmp_path / "out"
    assert main(["convert", "-i", str(zutomayo_dir), "-o", str(out), "--name", "Custom"]) == 0
    assert (out / "Custom" / "index.theme").is_file()


def test_convert_dry_run_writes_nothing(tmp_path: Path, zutomayo_dir: Path) -> None:
    out = tmp_path / "out"
    assert main(["convert", "-i", str(zutomayo_dir), "-o", str(out), "--dry-run"]) == 0
    assert not out.exists()


def test_convert_missing_inf(tmp_path: Path) -> None:
    assert main(["convert", "-i", str(tmp_path / "nope"), "-o", str(tmp_path / "out")]) == 1


def test_convert_unknown_key_falls_back(tmp_path: Path, zutomayo_dir: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "install.inf").write_text(
        '[Strings]\nSCHEME_NAME = "Test"\nmystery = "Person.cur"\n', encoding="utf-8"
    )
    shutil.copy(zutomayo_dir / "Person.cur", src / "Person.cur")

    out = tmp_path / "out"
    assert main(["convert", "-i", str(src), "-o", str(out), "--sizes", "16"]) == 0

    cursors = out / "Test" / "cursors"
    assert (cursors / "mystery").is_file()
    # unknown keys get no standard aliases
    assert [p.name for p in cursors.iterdir()] == ["mystery"]


def test_convert_duplicate_role_keeps_first(tmp_path: Path, zutomayo_dir: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "install.inf").write_text(
        '[Strings]\nSCHEME_NAME = "Dup"\npointer = "Normal.ani"\narrow = "Normal.ani"\n',
        encoding="utf-8",
    )
    shutil.copy(zutomayo_dir / "Normal.ani", src / "Normal.ani")

    out = tmp_path / "out"
    assert main(["convert", "-i", str(src), "-o", str(out), "--sizes", "16"]) == 0

    # Both keys map to the "arrow" role; only one cursor is produced.
    cursor_files = [p for p in (out / "Dup" / "cursors").iterdir() if not p.is_symlink()]
    assert [p.name for p in cursor_files] == ["arrow"]


def test_logger_levels(capsys: pytest.CaptureFixture[str]) -> None:
    logger = Logger("warn")
    logger.info("hidden")
    logger.warn("shown")
    captured = capsys.readouterr()
    assert "hidden" not in captured.err
    assert "[warn]: shown" in captured.err
