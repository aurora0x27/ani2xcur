"""Tests for the tolerant Windows ``.inf`` parser."""

from __future__ import annotations

import codecs
from pathlib import Path

from ani2xcur.config.inf import decode_inf, load_inf, parse_inf


def _load_sample(root: Path):
    return load_inf(next(root.rglob("*.inf")))


def test_decode_utf16_and_bom() -> None:
    text = '[Strings]\r\npointer = "Normal.ani"\r\n'
    assert decode_inf(codecs.BOM_UTF16_LE + text.encode("utf-16-le")) == text
    assert decode_inf(codecs.BOM_UTF16_BE + text.encode("utf-16-be")) == text
    assert decode_inf(codecs.BOM_UTF8 + text.encode("utf-8")) == text
    assert decode_inf(text.encode("utf-8")) == text


def test_decode_falls_back_to_cp1252() -> None:
    # 0xE9 is "é" in cp1252 but invalid UTF-8.
    assert decode_inf(b"[Strings]\r\npointer = \xe9.ani\r\n").endswith("é.ani\r\n")


def test_parse_basic_and_dirty() -> None:
    text = (
        "[Version]\r\n"
        'signature="$CHICAGO$"\r\n'
        "\r\n"
        "[Strings]\r\n"
        'pointer   = "Normal Select.ani"\r\n'
        'pin       = "Location Select.ani\r\n'  # missing closing quote
        "; a comment\r\n"
        "\t\r\n"
        'CUR_DIR   = "Windows\\Cursors\\Moos"\r\n'
        "SCHEME_NAME = Moos\r\n"
    )
    inf = parse_inf(text)

    assert inf.section("strings") == inf.section("Strings")  # case-insensitive
    assert inf.strings()["pointer"] == "Normal Select.ani"
    assert inf.strings()["pin"] == "Location Select.ani"  # tolerant of the typo
    assert inf.scheme_name() == "Moos"
    assert inf.cur_dir() == "Windows\\Cursors\\Moos"


def test_cursor_entries_drop_metadata() -> None:
    inf = parse_inf(
        '[Strings]\r\nSCHEME_NAME = "X"\r\nCUR_DIR = "dir"\r\npointer = "p.ani"\r\nempty =\r\n'
    )
    assert inf.cursor_entries() == {"pointer": "p.ani"}


def test_miku_inf(miku_dir: Path) -> None:
    inf = _load_sample(miku_dir)
    assert inf.scheme_name() == "Moos"
    entries = inf.cursor_entries()
    assert entries["pointer"] == "Normal Select.ani"
    assert entries["work"] == "Work.ani"
    assert entries["pin"] == "Location Select.ani"
    assert entries["person"] == "Person Select.ani"
    assert len(entries) == 17


def test_zutomayo_inf(zutomayo_dir: Path) -> None:
    inf = _load_sample(zutomayo_dir)
    assert inf.scheme_name() == "ZUTOMAYO"
    entries = inf.cursor_entries()
    assert entries["pointer"] == "Normal.ani"
    assert entries["working"] == "Working.ani"
    assert entries["hand"] == "Handwriting.ani"
    assert entries["person"] == "Person.cur"
    assert entries["pin"] == "Pin.cur"
    assert len(entries) == 17
