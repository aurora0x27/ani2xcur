"""Assemble a Linux cursor theme directory from converted cursors.

The output layout is::

    <output>/<Name>/
        cursors/<role>            # the XCursor file
        cursors/<alias> -> <role> # symlinks for every X11 alias
        index.theme
        cursor.theme

``index.theme`` is what modern desktops (GNOME, KDE, ...) read to list and
activate the theme; ``cursor.theme`` is a legacy fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .formats import xcursor
from .model import Cursor

DEFAULT_COMMENT = "Converted from a Windows cursor scheme by ani2xcur"


def _safe_dirname(name: str) -> str:
    cleaned = name.replace("/", "_").replace("\\", "_").strip().strip(".")
    return cleaned or "theme"


def _theme_file(name: str, comment: str, inherits: str = "") -> str:
    lines = ["[Icon Theme]", f"Name={name}", f"Comment={comment}"]
    if inherits:
        lines.append(f"Inherits={inherits}")
    return "\n".join(lines) + "\n"


@dataclass
class CursorTheme:
    """A named theme: canonical cursors plus their X11 aliases."""

    name: str
    cursors: dict[str, Cursor] = field(default_factory=dict)
    aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    comment: str = DEFAULT_COMMENT
    inherits: str = ""

    @property
    def directory(self) -> str:
        return _safe_dirname(self.name)

    def write(self, output_dir: str | Path) -> Path:
        """Write the theme below ``output_dir`` and return the theme directory."""
        theme_dir = Path(output_dir) / self.directory
        cursors_dir = theme_dir / "cursors"
        cursors_dir.mkdir(parents=True, exist_ok=True)

        for role, cursor in self.cursors.items():
            xcursor.write_file(cursor, cursors_dir / role)

        real_names = set(self.cursors)
        for role, names in self.aliases.items():
            for name in names:
                if name == role:
                    continue
                if name in real_names:
                    raise ValueError(f"alias {name!r} of {role!r} would shadow another cursor")
                link = cursors_dir / name
                if link.is_symlink() or link.exists():
                    link.unlink()
                link.symlink_to(role)

        content = _theme_file(self.name, self.comment, self.inherits)
        (theme_dir / "index.theme").write_text(content, encoding="utf-8")
        (theme_dir / "cursor.theme").write_text(content, encoding="utf-8")
        return theme_dir
