#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
cd "$ROOT"

if [ ! -f pyproject.toml ]; then
  echo "pyproject.toml not found; cannot detect repository pytest command" >&2
  exit 2
fi

PYTHON_CMD=""
for candidate in python python3 python.exe py; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_CMD="$candidate"
    break
  fi
done

if [ -z "$PYTHON_CMD" ]; then
  echo "No Python executable found on PATH. Tried python, python3, python.exe, py." >&2
  exit 127
fi

echo "Running existing test command: PYTHONDONTWRITEBYTECODE=1 $PYTHON_CMD -m pytest -p no:cacheprovider $*"
PYTHONDONTWRITEBYTECODE=1 exec "$PYTHON_CMD" -m pytest -p no:cacheprovider "$@"
