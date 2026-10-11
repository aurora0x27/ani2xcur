"""Conversion pipeline: a Windows cursor theme directory -> an XCursor theme."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from . import roles
from .config.inf import load_inf
from .formats.loader import load_source
from .log import Logger
from .render import DEFAULT_SIZES, resize_cursor
from .theme import CursorTheme


@dataclass
class ConvertResult:
    """Outcome of a :func:`convert` run."""

    theme: CursorTheme
    theme_dir: Path | None
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def find_inf(
    input_dir: str | Path, explicit: str | Path | None = None, logger: Logger | None = None
) -> Path:
    """Locate the ``.inf`` describing the theme.

    ``explicit`` wins when given. Otherwise the ``.inf`` is searched for
    recursively; when several exist the shallowest one is used and, if that is
    still ambiguous, an error is raised.
    """
    if explicit is not None:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"inf file not found: {path}")
        return path

    root = Path(input_dir)
    infs = sorted(path for path in root.rglob("*") if path.suffix.lower() == ".inf")
    if not infs:
        raise FileNotFoundError(f"no .inf file found under {root}")
    if len(infs) == 1:
        return infs[0]

    shallow = min(len(path.relative_to(root).parts) for path in infs)
    top = [path for path in infs if len(path.relative_to(root).parts) == shallow]
    if len(top) > 1:
        names = ", ".join(str(path) for path in top)
        raise ValueError(f"several .inf files found ({names}); pick one with --inf")
    if logger is not None:
        logger.warn(f"several .inf files found; using {top[0]}")
    return top[0]


def _resolve_file(root: Path, input_dir: Path, filename: str) -> Path | None:
    """Find ``filename`` under ``root``/``input_dir``, falling back to a
    case-insensitive match (Windows file names are case-insensitive)."""
    for base in (root, input_dir):
        candidate = base / filename
        if candidate.exists():
            return candidate
        lowered = filename.lower()
        try:
            for entry in base.iterdir():
                if entry.is_file() and entry.name.lower() == lowered:
                    return entry
        except OSError:
            continue
    return None


def _render(source: Path, cursor_name: str, sizes: Iterable[int], allow_upscale: bool):
    return resize_cursor(load_source(source, name=cursor_name), sizes, allow_upscale=allow_upscale)


def convert(
    input_dir: str | Path,
    output_dir: str | Path,
    sizes: Iterable[int] = DEFAULT_SIZES,
    name: str | None = None,
    inf: str | Path | None = None,
    *,
    allow_upscale: bool = True,
    dry_run: bool = False,
    logger: Logger | None = None,
) -> ConvertResult:
    """Convert a Windows cursor theme into an XCursor theme.

    ``input_dir`` may be a theme directory (with an ``.inf`` and cursor files)
    or a single cursor/image file. The theme is written to
    ``output_dir/<ThemeName>/`` where ``ThemeName`` is ``name``, else the
    ``.inf``'s ``SCHEME_NAME`` (directory input) or the file stem (single file),
    else the input directory name.
    """
    logger = logger or Logger()
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    skipped: list[str] = []
    failed: list[str] = []

    if input_dir.is_file():
        theme, theme_name = _convert_single(input_dir, sizes, name, allow_upscale, dry_run, logger)
    else:
        theme, theme_name = _convert_directory(
            input_dir, sizes, name, inf, allow_upscale, dry_run, logger, skipped, failed
        )

    if dry_run:
        logger.info(f"[dry-run] would write theme {theme_name!r} to {output_dir / theme.directory}")
        return ConvertResult(theme=theme, theme_dir=None, skipped=skipped, failed=failed)

    theme_dir = theme.write(output_dir)
    logger.info(f"wrote theme {theme_name!r} ({len(theme.cursors)} cursors) to {theme_dir}")
    if skipped:
        logger.warn(f"skipped {len(skipped)} entries: {', '.join(skipped)}")
    if failed:
        logger.warn(f"failed {len(failed)} entries: {', '.join(failed)}")
    return ConvertResult(theme=theme, theme_dir=theme_dir, skipped=skipped, failed=failed)


def _cursors_for_key(key: str) -> tuple[str, tuple[str, ...]]:
    role = roles.resolve(key)
    if role is None:
        return roles.sanitize_name(key), ()
    return role.canonical, role.x11


def _convert_single(
    source: Path,
    sizes: Iterable[int],
    name: str | None,
    allow_upscale: bool,
    dry_run: bool,
    logger: Logger,
) -> tuple[CursorTheme, str]:
    theme_name = name or source.stem
    theme = CursorTheme(name=theme_name)
    cursor_name, aliases = _cursors_for_key(source.stem)

    if dry_run:
        logger.info(f"[dry-run] {cursor_name} <- {source}")
        return theme, theme_name

    theme.cursors[cursor_name] = _render(source, cursor_name, sizes, allow_upscale)
    if aliases:
        theme.aliases[cursor_name] = aliases
    return theme, theme_name


def _convert_directory(
    input_dir: Path,
    sizes: Iterable[int],
    name: str | None,
    inf: str | Path | None,
    allow_upscale: bool,
    dry_run: bool,
    logger: Logger,
    skipped: list[str],
    failed: list[str],
) -> tuple[CursorTheme, str]:
    inf_path = find_inf(input_dir, inf, logger)
    parsed = load_inf(inf_path)
    inf_root = inf_path.parent

    theme_name = name or parsed.scheme_name() or input_dir.name
    theme = CursorTheme(name=theme_name)
    claimed: dict[str, str] = {}

    for key, filename in parsed.cursor_entries().items():
        cursor_name, aliases = _cursors_for_key(key)

        if cursor_name in claimed:
            logger.warn(
                f"role {cursor_name!r} already provided by "
                f"{claimed[cursor_name]!r}; ignoring {key!r}"
            )
            continue

        source = _resolve_file(inf_root, input_dir, filename)
        if source is None:
            logger.warn(f"file {filename!r} for {key!r} not found; skipping")
            skipped.append(key)
            continue

        if not aliases:
            logger.warn(f"unknown cursor key {key!r}; adding standalone cursor {cursor_name!r}")

        claimed[cursor_name] = key

        if dry_run:
            logger.info(f"[dry-run] {cursor_name} <- {source}")
            continue

        try:
            theme.cursors[cursor_name] = _render(source, cursor_name, sizes, allow_upscale)
        except (OSError, ValueError) as exc:
            logger.warn(f"failed to convert {source}: {exc}")
            failed.append(key)
            continue
        if aliases:
            theme.aliases[cursor_name] = aliases
        logger.trace(f"converted {cursor_name} from {filename}")

    return theme, theme_name
