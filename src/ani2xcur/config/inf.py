"""Tolerant parser for Windows cursor scheme ``.inf`` files.

These files are INI-like: ``[Section]`` headers followed by ``key = value``
lines (and occasionally bare tokens, e.g. in ``[Scheme.Cur]``). They may be
encoded as ASCII/UTF-8 or UTF-16 with a byte order mark, use CRLF line endings,
and are frequently hand-edited (unbalanced quotes, stray whitespace).

The only section the converter needs is ``[Strings]``, which maps a cursor role
key (``pointer``, ``work``, ...) to a file name.
"""

from __future__ import annotations

import codecs
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

# ``[Strings]`` entries that are metadata rather than cursor roles.
RESERVED_KEYS = frozenset({"cur_dir", "scheme_name"})


def decode_inf(data: bytes) -> str:
    """Decode ``.inf`` bytes, honouring BOMs and falling back to Windows ANSI."""
    if data.startswith(codecs.BOM_UTF8):
        return data.decode("utf-8-sig")
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _unquote(value: str) -> str:
    """Strip one layer of surrounding quotes, tolerating a missing closer."""
    value = value.strip()
    if value and value[0] in "\"'":
        value = value[1:]
    if value and value[-1] in "\"'":
        value = value[:-1]
    return value.strip()


@dataclass
class InfFile:
    """A parsed ``.inf`` file: ordered sections, each with ordered key/values."""

    sections: dict[str, OrderedDict[str, str]] = field(default_factory=OrderedDict)

    def section(self, name: str) -> dict[str, str]:
        """Return a section by case-insensitive name (empty if missing)."""
        wanted = name.strip().lower()
        for section_name, values in self.sections.items():
            if section_name.strip().lower() == wanted:
                return values
        return {}

    def strings(self) -> dict[str, str]:
        """Return the ``[Strings]`` section."""
        return self.section("Strings")

    def _string(self, key: str) -> str | None:
        wanted = key.strip().lower()
        for entry, value in self.strings().items():
            if entry.strip().lower() == wanted:
                return value
        return None

    def scheme_name(self) -> str | None:
        """Return ``SCHEME_NAME`` from ``[Strings]``, if present and non-empty."""
        value = self._string("SCHEME_NAME")
        return value or None

    def cur_dir(self) -> str | None:
        """Return ``CUR_DIR`` from ``[Strings]``, if present and non-empty."""
        value = self._string("CUR_DIR")
        return value or None

    def cursor_entries(self) -> dict[str, str]:
        """Return ``[Strings]`` entries that map role keys to file names.

        Metadata keys such as ``CUR_DIR`` and ``SCHEME_NAME`` and empty values
        are dropped.
        """
        result: dict[str, str] = {}
        for key, value in self.strings().items():
            if key.strip().lower() in RESERVED_KEYS:
                continue
            if not value:
                continue
            result[key] = value
        return result


def parse_inf(text: str) -> InfFile:
    """Parse ``.inf`` text into an :class:`InfFile`."""
    inf = InfFile()
    current: str | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in ";#":
            continue

        if line.startswith("["):
            end = line.find("]")
            current = (line[1:end] if end != -1 else line[1:]).strip()
            inf.sections.setdefault(current, OrderedDict())
            continue

        if current is None:
            continue

        if "=" in line:
            key, _, value = line.partition("=")
            inf.sections[current][key.strip()] = _unquote(value)
        else:
            # Bare token, e.g. a file name listed under [Scheme.Cur].
            inf.sections[current][_unquote(line)] = ""

    return inf


def load_inf(path: str | Path) -> InfFile:
    """Read and parse an ``.inf`` file from disk."""
    data = Path(path).read_bytes()
    return parse_inf(decode_inf(data))
