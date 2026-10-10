"""Shared pytest fixtures: the two sample theme archives from ``assets/``."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parent.parent / "assets"

MIKU_ARCHIVE = ASSETS / "MikuComplete.zip"
ZUTOMAYO_ARCHIVE = ASSETS / "Zutomayo.zip"


def _extract(target: Path, archive: Path) -> Path:
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(target)
    return target


@pytest.fixture(scope="session")
def miku_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Extracted ``MikuComplete.zip`` (animated 160x160 cursors)."""
    return _extract(tmp_path_factory.mktemp("miku"), MIKU_ARCHIVE)


@pytest.fixture(scope="session")
def zutomayo_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Extracted ``Zutomayo.zip`` (animated 32x32 cursors, plus two .cur)."""
    return _extract(tmp_path_factory.mktemp("zutomayo"), ZUTOMAYO_ARCHIVE)


@pytest.fixture(scope="session")
def find_files():
    """Return a helper that recursively finds files, sorted for stable order."""

    def _find(root: Path, pattern: str) -> list[Path]:
        return sorted(root.rglob(pattern))

    return _find
