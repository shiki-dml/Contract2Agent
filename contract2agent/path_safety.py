from __future__ import annotations

from pathlib import Path


class PathContainmentError(ValueError):
    """Raised when a resolved path escapes the required containing directory."""


def resolve_within(base: str | Path, path: str | Path) -> Path:
    base_path = Path(base).expanduser().resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = base_path / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base_path)
    except ValueError as exc:
        raise PathContainmentError(f"Path escapes {base_path}: {path}") from exc
    return resolved


def is_within(path: str | Path, base: str | Path) -> bool:
    base_path = Path(base).expanduser().resolve()
    try:
        Path(path).expanduser().resolve().relative_to(base_path)
    except (OSError, ValueError):
        return False
    return True
