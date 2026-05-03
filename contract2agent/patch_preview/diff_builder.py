from __future__ import annotations

import difflib
from pathlib import Path

from contract2agent.patch_preview.security import sanitize_text


def build_unified_diff(
    path: Path,
    project_root: Path,
    addition_lines: list[str],
    *,
    heading: str = "AgentDoctor Patch Preview Guidance",
) -> tuple[str, str]:
    previous = path.read_text(encoding="utf-8")
    new_text = append_guidance(previous, addition_lines, heading=heading)
    relative = _relative(project_root, path)
    diff = "".join(
        difflib.unified_diff(
            previous.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=relative,
            tofile=relative,
        )
    )
    return sanitize_text(diff), new_text


def append_guidance(
    current_text: str,
    addition_lines: list[str],
    *,
    heading: str = "AgentDoctor Patch Preview Guidance",
) -> str:
    current = current_text.rstrip()
    if _looks_like_markdown_prompt(current_text):
        block = ["", "", f"## {heading}", ""]
        block.extend(f"- {line}" for line in addition_lines)
        return current + "\n".join(block) + "\n"

    block = ["", "", "# AgentDoctor Patch Preview Guidance"]
    block.extend(f"# - {line}" for line in addition_lines)
    return current + "\n".join(block) + "\n"


def _looks_like_markdown_prompt(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("#") or "## " in text or len(text.splitlines()) <= 40


def _relative(root: Path, path: Path | str) -> str:
    target = Path(path)
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return target.as_posix()
