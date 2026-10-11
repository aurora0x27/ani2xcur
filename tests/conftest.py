"""Shared pytest fixtures: the two sample theme archives from ``assets/``."""

from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path

import pytest
from PIL import Image

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


# --- synthetic fixture builders --------------------------------------------


def _png_bytes(size: int, color: tuple[int, int, int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (size, size), color).save(buffer, "PNG")
    return buffer.getvalue()


def _cur_bytes(entries: list[tuple[int, tuple[int, int], bytes]]) -> bytes:
    """Build a CUR file from ``(size, (hotspot_x, hotspot_y), payload)`` entries."""
    header = struct.pack("<HHH", 0, 2, len(entries))
    offset = 6 + 16 * len(entries)
    directory = b""
    payloads = b""
    for size, (hotspot_x, hotspot_y), payload in entries:
        directory += struct.pack(
            "<BBBBHHII", size % 256, size % 256, 0, 0, hotspot_x, hotspot_y, len(payload), offset
        )
        payloads += payload
        offset += len(payload)
    return header + directory + payloads


def _ani_bytes(
    icons: list[bytes],
    seq: list[int] | None = None,
    rate: list[int] | None = None,
    *,
    cx: int = 0,
    cy: int = 0,
    jif_rate: int = 6,
) -> bytes:
    """Build a minimal ANI file around a list of icon/CUR blobs."""

    def chunk(chunk_id: bytes, payload: bytes) -> bytes:
        out = chunk_id + struct.pack("<I", len(payload)) + payload
        return out + (b"\x00" if len(payload) & 1 else b"")

    steps = len(seq) if seq else len(icons)
    anih = struct.pack("<9I", 36, len(icons), steps, cx, cy, 32, 0, jif_rate, 1)
    body = b"anih" + struct.pack("<I", 36) + anih
    if seq:
        body += chunk(b"seq ", b"".join(struct.pack("<I", index) for index in seq))
    if rate:
        body += chunk(b"rate", b"".join(struct.pack("<I", value) for value in rate))
    body += chunk(b"LIST", b"fram" + b"".join(chunk(b"icon", icon) for icon in icons))
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"ACON" + body


@pytest.fixture(scope="session")
def png_bytes():
    return _png_bytes


@pytest.fixture(scope="session")
def build_cur():
    return _cur_bytes


@pytest.fixture(scope="session")
def build_ani():
    return _ani_bytes
