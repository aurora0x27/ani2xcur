"""Command line interface for ani2xcur.

Subcommands:
    convert   Convert a Windows cursor theme directory into a Linux XCursor theme.
    inspect   Dump metadata of ANI / ICO / CUR files.
    roles     List canonical cursor roles and their X11 aliases.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__, roles
from .formats.win import describe
from .log import LEVELS, Logger
from .pipeline import convert
from .render import DEFAULT_SIZES

CURSOR_SUFFIXES = frozenset({".ani", ".cur", ".ico"})


def _parse_sizes(raw: str) -> list[int]:
    sizes: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid size: {part!r}") from None
        if value <= 0:
            raise argparse.ArgumentTypeError(f"size must be positive: {value}")
        if value not in sizes:
            sizes.append(value)
    if not sizes:
        raise argparse.ArgumentTypeError("no sizes given")
    return sizes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ani2xcur",
        description="Convert Windows cursor themes (.ani / .cur) into Linux XCursor themes.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p_convert = sub.add_parser(
        "convert",
        help="convert a Windows cursor theme directory into a Linux XCursor theme",
        description="Convert a directory containing a Windows .inf and .ani / .cur files "
        "into a Linux XCursor theme.",
    )
    p_convert.add_argument("-i", "--input", required=True, type=Path, help="input theme directory")
    p_convert.add_argument("-o", "--output", required=True, type=Path, help="output directory")
    p_convert.add_argument(
        "--sizes",
        type=_parse_sizes,
        default=list(DEFAULT_SIZES),
        metavar="LIST",
        help="comma separated nominal sizes (default: %(default)s)",
    )
    p_convert.add_argument(
        "--name", default=None, help="theme name (default: SCHEME_NAME from the .inf)"
    )
    p_convert.add_argument(
        "--inf", default=None, type=Path, help="explicit .inf file (when several are present)"
    )
    p_convert.add_argument(
        "--no-upscale",
        action="store_true",
        help="do not enlarge sources smaller than a requested size",
    )
    p_convert.add_argument(
        "-n", "--dry-run", action="store_true", help="show what would be done only"
    )
    p_convert.add_argument(
        "--log-level",
        choices=sorted(LEVELS),
        default="info",
        help="log level (default: %(default)s)",
    )
    p_convert.set_defaults(func=_cmd_convert)

    p_inspect = sub.add_parser(
        "inspect",
        help="dump metadata of ANI / ICO / CUR files",
        description="Dump metadata of one or more ANI / ICO / CUR files or directories.",
    )
    p_inspect.add_argument(
        "paths", nargs="+", type=Path, metavar="PATH", help="files or directories"
    )
    p_inspect.add_argument("--json", action="store_true", help="emit JSON instead of plain text")
    p_inspect.add_argument(
        "--log-level",
        choices=sorted(LEVELS),
        default="info",
        help="log level (default: %(default)s)",
    )
    p_inspect.set_defaults(func=_cmd_inspect)

    p_roles = sub.add_parser(
        "roles",
        help="list canonical cursor roles and their X11 aliases",
        description="List canonical cursor roles and their X11 aliases.",
    )
    p_roles.add_argument("--json", action="store_true", help="emit JSON instead of plain text")
    p_roles.set_defaults(func=_cmd_roles)

    return parser


def _collect_cursors(paths: Sequence[Path], logger: Logger) -> tuple[list[Path], int]:
    files: list[Path] = []
    missing = 0
    for path in paths:
        if path.is_dir():
            files.extend(
                sorted(
                    child for child in path.rglob("*") if child.suffix.lower() in CURSOR_SUFFIXES
                )
            )
        elif path.exists():
            files.append(path)
        else:
            logger.warn(f"path not found: {path}")
            missing += 1
    return files, missing


def _cmd_convert(args: argparse.Namespace) -> int:
    logger = Logger(args.log_level)
    result = convert(
        args.input,
        args.output,
        sizes=args.sizes,
        name=args.name,
        inf=args.inf,
        allow_upscale=not args.no_upscale,
        dry_run=args.dry_run,
        logger=logger,
    )
    return 1 if result.failed else 0


def _print_metadata(row: dict[str, object]) -> None:
    print(row["path"])
    print(f"  kind:    {row['kind']}")
    print(f"  size:    {row['width']}x{row['height']}")
    print(f"  hotspot: {tuple(row['hotspot'])}")  # type: ignore[arg-type]
    print(f"  frames:  {row['frames']}")
    print(f"  sizes:   {row['sizes']}")
    print(f"  delays:  {row['delays_ms']} ms")


def _cmd_inspect(args: argparse.Namespace) -> int:
    logger = Logger(args.log_level)
    files, missing = _collect_cursors(args.paths, logger)

    rows: list[dict[str, object]] = []
    failed = missing
    for path in files:
        try:
            rows.append(describe(path))
        except (OSError, ValueError) as exc:
            logger.warn(f"{path}: {exc}")
            failed += 1

    if args.json:
        json.dump(rows, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        for row in rows:
            _print_metadata(row)

    if not files and not missing:
        logger.warn("no cursor files found")
    return 1 if failed else 0


def _cmd_roles(args: argparse.Namespace) -> int:
    all_roles = roles.load_roles()
    if args.json:
        json.dump(
            [
                {
                    "canonical": role.canonical,
                    "description": role.description,
                    "keys": list(role.keys),
                    "x11": list(role.x11),
                }
                for role in all_roles
            ],
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        sys.stdout.write("\n")
    else:
        for role in all_roles:
            print(f"{role.canonical}: {role.description}")
            print(f"  keys: {', '.join(role.keys)}")
            print(f"  x11:  {', '.join(role.x11)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("ani2xcur: interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - keep tracebacks away from users
        if os.environ.get("ANI2XCUR_DEBUG"):
            raise
        print(f"ani2xcur: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
