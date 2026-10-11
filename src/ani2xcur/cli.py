"""Command line interface for ani2xcur.

Subcommands:
    convert   Convert a Windows cursor theme directory into a Linux XCursor theme.
    inspect   Dump metadata of ANI / ICO / CUR files.
    roles     List canonical cursor roles and their X11 aliases.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__

DEFAULT_SIZES = (16, 24, 32, 48, 64, 96, 128)


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
    p_convert.add_argument("-i", "--input", required=True, help="input theme directory")
    p_convert.add_argument("-o", "--output", required=True, help="output directory")
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
        "-n", "--dry-run", action="store_true", help="show what would be done only"
    )
    p_convert.set_defaults(func=_cmd_convert)

    p_inspect = sub.add_parser(
        "inspect",
        help="dump metadata of ANI / ICO / CUR files",
        description="Dump metadata of one or more ANI / ICO / CUR files or directories.",
    )
    p_inspect.add_argument(
        "paths", nargs="+", metavar="PATH", help="files or directories to inspect"
    )
    p_inspect.add_argument("--json", action="store_true", help="emit JSON instead of plain text")
    p_inspect.set_defaults(func=_cmd_inspect)

    p_roles = sub.add_parser(
        "roles",
        help="list canonical cursor roles and their X11 aliases",
        description="List canonical cursor roles and their X11 aliases.",
    )
    p_roles.set_defaults(func=_cmd_roles)

    return parser


def _cmd_convert(args: argparse.Namespace) -> int:
    raise SystemExit("error: 'convert' is not implemented yet (Phase 5)")


def _cmd_inspect(args: argparse.Namespace) -> int:
    raise SystemExit("error: 'inspect' is not implemented yet (Phase 5)")


def _cmd_roles(args: argparse.Namespace) -> int:
    raise SystemExit("error: 'roles' is not implemented yet (Phase 5)")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
