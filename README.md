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

# Inspect a cursor file
uv run ani2xcur inspect ./theme/Normal.ani
```

## Development

```bash
uv run pytest
uv run ruff check
uv run ruff format

# Generate build/compile_commands.json for clangd / IDE tooling
./scripts/gen-compile-commands.sh
```
