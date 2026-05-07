#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
cd "$ROOT"

echo "Contract2Agent harness doctor"
echo "project_root: $ROOT"
echo

echo "git_status_short:"
status_file="$(mktemp "${TMPDIR:-/tmp}/c2a_harness_git_status.XXXXXX")"
trap 'rm -f "$status_file"' EXIT
if git status --short >"$status_file" 2>/dev/null; then
  if [ -s "$status_file" ]; then
    cat "$status_file"
  else
    echo "  clean"
  fi
else
  echo "  git status unavailable"
fi
echo

echo "detected_commands:"
echo "  tests: python -m pytest"
echo "  compile: python -m compileall -q contract2agent tests scripts"
echo "  docs_links: python scripts/check_docs_links.py"
echo "  mkdocs: python -m mkdocs build --strict"
echo "  harness_validate: python scripts/harness/validate_docs.py"
echo

echo "package_entry_points:"
PYTHON_CMD=""
for candidate in python python3 python.exe py; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_CMD="$candidate"
    break
  fi
done

if [ -z "$PYTHON_CMD" ]; then
  echo "  python unavailable on PATH; skipping pyproject.toml parse"
else
  "$PYTHON_CMD" - <<'PY'
from pathlib import Path
import sys

try:
    import tomllib
except ModuleNotFoundError:
    print("  tomllib unavailable; cannot parse pyproject.toml")
    raise SystemExit(0)

path = Path("pyproject.toml")
if not path.exists():
    print("  pyproject.toml missing")
    raise SystemExit(0)

data = tomllib.loads(path.read_text(encoding="utf-8"))
scripts = data.get("project", {}).get("scripts", {})
if not scripts:
    print("  none detected")
else:
    for name, target in sorted(scripts.items()):
        print(f"  {name}: {target}")
PY
fi
echo

echo "docs_harness_status:"
for path in \
  AGENTS.md \
  docs/README.md \
  docs/AGENT_HANDOFF.md \
  docs/harness/README.md \
  docs/harness/feature_registry.json \
  docs/harness/QUALITY_GATES.md \
  scripts/harness/validate_docs.py
do
  if [ -e "$path" ]; then
    echo "  present: $path"
  else
    echo "  missing: $path"
  fi
done
