"""Smoke tests: the package and the compiled core import correctly."""

from __future__ import annotations

import pytest

import ani2xcur
from ani2xcur import _anicore


def test_core_version_matches() -> None:
    assert _anicore.version() == ani2xcur.core_version()
    assert _anicore.__version__


def test_status_enum() -> None:
    assert _anicore.Status.OK.value == 0
    assert _anicore.strerror(_anicore.Status.ERR_FORMAT)


def test_cli_help() -> None:
    from ani2xcur.cli import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["--help"])
    assert excinfo.value.code == 0


def test_cli_convert_requires_input_output() -> None:
    from ani2xcur.cli import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["convert"])
    assert excinfo.value.code == 2
