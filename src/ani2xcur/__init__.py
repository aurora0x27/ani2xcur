"""ani2xcur - convert Windows cursor themes into Linux XCursor themes."""

from __future__ import annotations

from . import _anicore

__all__ = ["__version__", "core_version"]

__version__ = "0.1.0"
core_version = _anicore.version
