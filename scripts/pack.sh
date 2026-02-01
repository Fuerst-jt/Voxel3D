#!/usr/bin/env bash
# Cross-platform packaging helper (Linux/macOS)
# Usage: ./scripts/pack.sh linux|macos|windows
set -euo pipefail
# Determine repository root (script can be called from any cwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."
PLATFORM=${1:-linux}
APP_NAME=voxel3d

# absolute path to main.py
MAIN_PY="${REPO_ROOT}/main.py"
if [ ! -f "${MAIN_PY}" ]; then
  echo "ERROR: Script file '${MAIN_PY}' does not exist." >&2
  exit 2
fi

DISTDIR=${REPO_ROOT}/dist

# Common pyinstaller args
PYI_ARGS=(--onefile --noconfirm --clean --name ${APP_NAME})
# Hidden imports to help PyInstaller find vtk/qt modules
PYI_ARGS+=(--hidden-import=vtkmodules)
PYI_ARGS+=(--hidden-import=vtkmodules.qt.QVTKRenderWindowInteractor)
PYI_ARGS+=(--hidden-import=vtkmodules.util.numpy_support)
PYI_ARGS+=(--hidden-import=vtkmodules.all)

case "${PLATFORM}" in
  linux|macos)
    python -m PyInstaller "${PYI_ARGS[@]}" "${MAIN_PY}"
    ;;
  windows)
    # To build Windows executable, run this on Windows or use cross-build toolchain
    python -m PyInstaller "${PYI_ARGS[@]}" "${MAIN_PY}"
    ;;
  *)
    echo "Unknown platform: ${PLATFORM}" >&2; exit 2
    ;;
esac

echo "Build complete. Output in ${DISTDIR}/" 
