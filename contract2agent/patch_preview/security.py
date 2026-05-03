from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any


DENIED_FILE_PATTERNS = {
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "*.crt",
    "secrets.*",
    "credentials.*",
}

DENIED_DIRS = {
    "node_modules",
    ".git",
    "venv",
    ".venv",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "coverage",
}

SECRET_KEY_RE = re.compile(
    r"(?i)\b(secret|password|passwd|token|api[_-]?key|credential|private[_-]?key)\b"
)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(secret|password|passwd|token|api[_-]?key|credential|private[_-]?key)"
    r"\s*[:=]\s*[^,\s\]}]+"
)


def is_denied_path(path: str | Path, project_root: str | Path) -> bool:
    root = Path(project_root).resolve()
    target = Path(path)
    if not target.is_absolute():
        target = root / target
    try:
        relative = target.resolve().relative_to(root)
    except ValueError:
        return True

    parts = [part.casefold() for part in relative.parts]
    if any(part in DENIED_DIRS for part in parts[:-1]):
        return True
    name = relative.name
    return any(fnmatch.fnmatch(name, pattern) for pattern in DENIED_FILE_PATTERNS)


def sanitize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    sanitized_lines: list[str] = []
    for line in text.splitlines():
        if SECRET_KEY_RE.search(line):
            sanitized_lines.append(SECRET_ASSIGNMENT_RE.sub(r"\1=[REDACTED]", line))
        else:
            sanitized_lines.append(line)
    return "\n".join(sanitized_lines)


def sanitize_data(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_data(item) for item in value]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if SECRET_KEY_RE.search(key_text):
                result[key_text] = "[REDACTED]"
            else:
                result[key_text] = sanitize_data(item)
        return result
    return value
