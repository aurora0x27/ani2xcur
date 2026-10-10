#!/usr/bin/env bash
#
# Generate build/compile_commands.json for clangd and other C/C++ tooling.
#
# The project is normally built by scikit-build-core into build/<wheel_tag>/,
# which is awkward for editors. This script runs a plain CMake configure in
# build/ (using the pybind11 provided by the uv environment) so the compilation
# database lands exactly where tooling expects it.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

build_dir="$root/build"
pybind11_dir="$(uv run python -m pybind11 --cmakedir)"

uv run cmake -S "$root" -B "$build_dir" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -Dpybind11_DIR="$pybind11_dir"

echo "Wrote $build_dir/compile_commands.json"
