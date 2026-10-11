# ani2xcur

Convert Windows cursor themes (`.ani` animated cursors and `.cur` static cursors)
into Linux **XCursor** themes with multiple nominal sizes.

The project ships:

- a small **C core** that parses the Windows cursor container formats
  (`ANI`/RIFF-ACON, `ICO`, `CUR`) and is exposed to Python through **pybind11**;
- a Python package that decodes pixels with Pillow, resizes them, maps Windows
  cursor roles to X11 names, and writes the XCursor binary files directly.

## Status

Early development. See `task.md` for the plan and current progress.

## Requirements

- Python >= 3.10
- A C/C++ toolchain and CMake (used at build time only)

## Build and run

```bash
uv sync
uv run ani2xcur --help
```

## Usage

```bash
# Convert a theme directory (containing an .inf and .ani / .cur files)
uv run ani2xcur convert --input ./theme --output ./out

# Choose the nominal sizes (default: 16,24,32,48,64,96,128)
uv run ani2xcur convert -i ./theme -o ./out --sizes 24,32,48

# Inspect cursor files or a whole directory (add --json for machine output)
uv run ani2xcur inspect ./out/MyTheme/cursors/left_ptr

# List the canonical roles and their X11 aliases
uv run ani2xcur roles
```

`convert` writes `<output>/<ThemeName>/` with a `cursors/` directory (real
XCursor files plus one symlink per X11 alias) and an `index.theme`.

`--input` may also point at a single `.ani` / `.cur` / `.ico` (or image) file
for a one-off conversion, and `--inf` selects a specific description file when a
theme directory contains more than one.

## Development

```bash
uv run pytest
uv run ruff check
uv run ruff format

# Generate build/compile_commands.json for clangd / IDE tooling
./scripts/gen-compile-commands.sh
```
