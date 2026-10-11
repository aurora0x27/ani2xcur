# ani2xcur

Convert Windows cursor themes (`.ani` animated cursors and `.cur` / `.ico`
static cursors) into Linux **XCursor** themes with multiple nominal sizes.

Because Windows cursors ship a single raster size, the converter rescales each
frame to the requested sizes, scales the hotspot accordingly, and writes the
XCursor binary directly — no `xcursorgen` required. Windows cursor *roles*
(“Normal Select”, “Busy”, …) are mapped to the freedesktop/X11 cursor names so
the result works in GTK, Qt, KDE and GNOME.

## How it works

- a small **C core** (`src/csrc`) parses the container formats — ANI
  (RIFF/ACON), ICO and CUR — and is exposed to Python through **pybind11**;
- a **Python package** (`src/ani2xcur`) decodes the frames with Pillow, resizes
  them, maps Windows roles to X11 names, and writes the XCursor files and theme
  directory.

See [`docs/design.md`](docs/design.md) for the architecture and
[`docs/usage.md`](docs/usage.md) for a detailed guide.

## Requirements

- Python >= 3.10
- A C/C++ toolchain and CMake (build time only)

## Install

```bash
# recommended: run the CLI without polluting a project
uv tool install .
# or
pipx install .
# or inside a checkout
uv sync
```

## Quick start

```bash
# Convert a Windows theme directory (containing an .inf and .ani / .cur files)
ani2xcur convert --input /path/to/theme --output ./out

# The result is a ready-to-use theme:
mkdir -p ~/.icons && cp -r ./out/<ThemeName> ~/.icons/
# GNOME:
gsettings set org.gnome.desktop.interface cursor-theme '<ThemeName>'
```

## Usage

```bash
# Convert a theme directory
ani2xcur convert -i ./theme -o ./out

# Choose the nominal sizes (default: 16,24,32,48,64,96,128)
ani2xcur convert -i ./theme -o ./out --sizes 24,32,48

# Override the theme name and inspect what would happen first
ani2xcur convert -i ./theme -o ./out --name MyTheme --dry-run

# Convert a single cursor/image file
ani2xcur convert -i ./Some.ani -o ./out

# Dump metadata of files or a whole directory (--json for machine output)
ani2xcur inspect ./theme
ani2xcur inspect ./out/MyTheme/cursors/left_ptr --json

# List the canonical roles and their X11 aliases
ani2xcur roles
```

`convert` writes `<output>/<ThemeName>/`:

```
<ThemeName>/
├── cursors/
│   ├── arrow            # real XCursor file for every canonical role
│   ├── left_ptr -> arrow
│   ├── default -> arrow
│   ├── ...
│   └── pointer -> link
├── index.theme
└── cursor.theme
```

`--input` may point at a theme directory or a single cursor/image file, and
`--inf` selects a specific description file when a directory contains more than
one.

## Supported input

| Kind | Details |
| --- | --- |
| `.ani` | RIFF/ACON; `seq` frame order, `rate`/`jifRate` delays |
| `.cur`, `.ico` | multi-image; DIB (1/4/8/24/32 bpp) and PNG payloads; AND mask |
| `.inf` | `[Strings]` role map; UTF-8 / ASCII / UTF-16 (BOM) |
| images | `.png`, `.bmp`, `.gif`, `.jpg`, `.jpeg`, `.webp` (loaded as a static cursor) |

Role keys are normalised, so vendor differences (`work` / `working`,
`handwrt` / `hand`, `unavailiable` / `unavailable`, …) all resolve. Unknown
keys become a standalone cursor instead of failing.

## Development

```bash
uv sync
uv run pytest                       # unit + end-to-end tests
uv run pytest --cov=ani2xcur        # with coverage
uv run ruff check && uv run ruff format

# Generate build/compile_commands.json for clangd / IDE tooling
./scripts/gen-compile-commands.sh
```

CI runs the suite on a Python 3.10–3.14 matrix (build + lint + tests).
