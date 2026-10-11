"""Cursor role mapping.

Windows cursor schemes name their cursors with loose keys (``work`` vs
``working``, ``handwrt`` vs ``hand``, ...). This module normalises those keys to
a small set of *canonical* roles and, for each role, lists the X11 cursor names
that should point at the generated cursor.

The canonical role set and the X11 aliases live in ``config/roles.json``.

Note: the key ``hand`` is mapped to the *handwriting* role because vendor
schemes (e.g. Zutomayo) use ``hand`` for NWPen; ``link`` is resolved through
``link`` / ``pointing_hand`` instead.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

_DATA_PACKAGE = "ani2xcur.config"
_DATA_FILE = "roles.json"

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class Role:
    """A canonical cursor role and its X11 alias names."""

    canonical: str
    keys: tuple[str, ...]
    x11: tuple[str, ...]
    description: str = ""


@lru_cache(maxsize=1)
def load_roles() -> tuple[Role, ...]:
    """Load the canonical role table (cached)."""
    with resources.files(_DATA_PACKAGE).joinpath(_DATA_FILE).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return tuple(
        Role(
            canonical=entry["canonical"],
            keys=tuple(entry["keys"]),
            x11=tuple(entry["x11"]),
            description=entry.get("description", ""),
        )
        for entry in data["roles"]
    )


@lru_cache(maxsize=1)
def _key_index() -> dict[str, Role]:
    index: dict[str, Role] = {}
    for role in load_roles():
        for key in (role.canonical, *role.keys):
            index.setdefault(key.strip().lower(), role)
    return index


def resolve(key: str) -> Role | None:
    """Map a Windows ``.inf`` key to a canonical role, or ``None`` if unknown."""
    return _key_index().get(key.strip().lower())


def find(canonical: str) -> Role | None:
    """Look up a role by its canonical name."""
    return _key_index().get(canonical.strip().lower())


def sanitize_name(name: str) -> str:
    """Turn an arbitrary key into a safe file name for a standalone cursor."""
    cleaned = _UNSAFE.sub("-", name.strip()).strip("-")
    return cleaned or "unnamed"
