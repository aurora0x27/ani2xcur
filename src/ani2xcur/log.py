"""Minimal leveled logger used by the CLI and the conversion pipeline."""

from __future__ import annotations

import sys
from enum import IntEnum
from typing import TextIO


class Level(IntEnum):
    TRACE = 10
    INFO = 20
    WARN = 30
    FATAL = 40


#: Lower-cased level names accepted on the command line.
LEVELS: dict[str, Level] = {level.name.lower(): level for level in Level}


class Logger:
    """Print leveled messages to a stream (stderr by default)."""

    def __init__(self, level: Level | str = Level.INFO, stream: TextIO | None = None) -> None:
        self.level = LEVELS[level.lower()] if isinstance(level, str) else level
        self.stream = stream if stream is not None else sys.stderr

    def _emit(self, level: Level, message: str) -> None:
        if level >= self.level:
            print(f"[{level.name.lower()}]: {message}", file=self.stream)

    def trace(self, message: str) -> None:
        self._emit(Level.TRACE, message)

    def info(self, message: str) -> None:
        self._emit(Level.INFO, message)

    def warn(self, message: str) -> None:
        self._emit(Level.WARN, message)

    def fatal(self, message: str) -> None:
        """Log a fatal error and abort the program with a non-zero exit code."""
        self._emit(Level.FATAL, message)
        raise SystemExit(1)
