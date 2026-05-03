from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from contract2agent.patch_preview.models import FindingGroup
from contract2agent.patch_preview.security import is_denied_path


ALLOWED_TARGET_PATTERNS = [
    "prompts/*.md",
    "prompts/*.txt",
    "prompt.md",
    "system_prompt.md",
    "instructions.md",
    "agent.yaml",
    "agent.yml",
    "agent.json",
    ".agentdoctor/agent.yaml",
    "tool_descriptions.yaml",
    "tool_descriptions.yml",
    "tools.yaml",
    "tools.yml",
    "agent_tools.yaml",
    "workflow_config.yaml",
    "workflow_config.yml",
    "eval_config.yaml",
    "eval_config.yml",
    "evals/*.yaml",
    "evals/*.yml",
    "evals/*.json",
    ".agentdoctor/evals/*.yaml",
    ".agentdoctor/evals/*.yml",
    ".agentdoctor/evals/*.json",
]

PROMPT_PATTERNS = [
    "prompts/system.md",
    "prompt.md",
    "system_prompt.md",
    "instructions.md",
    "prompts/*.md",
    "prompts/*.txt",
]

TOOL_PATTERNS = [
    "tool_descriptions.yaml",
    "tool_descriptions.yml",
    "tools.yaml",
    "tools.yml",
    "agent_tools.yaml",
]

WORKFLOW_PATTERNS = [
    "workflow_config.yaml",
    "workflow_config.yml",
    "agent.yaml",
    "agent.yml",
    ".agentdoctor/agent.yaml",
]

AGENT_CONFIG_PATTERNS = [
    "agent.yaml",
    "agent.yml",
    "agent.json",
    ".agentdoctor/agent.yaml",
]

EVAL_PATTERNS = [
    "eval_config.yaml",
    "eval_config.yml",
    "evals/*.yaml",
    "evals/*.yml",
    "evals/*.json",
    ".agentdoctor/evals/*.yaml",
    ".agentdoctor/evals/*.yml",
    ".agentdoctor/evals/*.json",
]


@dataclass
class TargetSelection:
    target: Path | None
    target_files: list[str]
    warnings: list[str]
    review_only_reason: str | None = None


def select_target_file(
    project_root: Path,
    group: FindingGroup,
    patch_type: str,
) -> TargetSelection:
    root = project_root.resolve()
    if group.target_file:
        candidate = _resolve_under_root(root, group.target_file)
        relative = _relative(root, candidate)
        if is_denied_path(candidate, root):
            return TargetSelection(
                target=None,
                target_files=[relative],
                warnings=[f"Denied patch target was skipped: {relative}"],
                review_only_reason="The suggested target is denied by the secret/unsafe path policy.",
            )
        if not is_allowed_target(candidate, root):
            return TargetSelection(
                target=None,
                target_files=[relative],
                warnings=[f"Target is outside the patch allowlist: {relative}"],
                review_only_reason="The suggested target is outside the patch allowlist.",
            )
        if not candidate.exists() or not candidate.is_file():
            return TargetSelection(
                target=None,
                target_files=[relative],
                warnings=[f"Target file is missing: {relative}"],
                review_only_reason="The suggested target file does not exist.",
            )
        return TargetSelection(target=candidate, target_files=[relative], warnings=[])

    patterns = _patterns_for_patch_type(patch_type)
    candidates = _existing_allowed_targets(root, patterns)
    if candidates:
        target = candidates[0]
        return TargetSelection(target=target, target_files=[_relative(root, target)], warnings=[])

    return TargetSelection(
        target=None,
        target_files=[],
        warnings=["No existing safe patch target matched the patch strategy."],
        review_only_reason="No safe patch target exists for this proposal.",
    )


def is_allowed_target(path: str | Path, project_root: str | Path) -> bool:
    root = Path(project_root).resolve()
    target = Path(path)
    if not target.is_absolute():
        target = root / target
    try:
        relative = target.resolve().relative_to(root)
    except ValueError:
        return False
    rel = relative.as_posix()
    if is_denied_path(target, root):
        return False
    return any(fnmatch.fnmatch(rel, pattern) for pattern in ALLOWED_TARGET_PATTERNS)


def _patterns_for_patch_type(patch_type: str) -> list[str]:
    if patch_type == "tool_description_update":
        return TOOL_PATTERNS + PROMPT_PATTERNS
    if patch_type == "workflow_config_update":
        return WORKFLOW_PATTERNS + PROMPT_PATTERNS
    if patch_type == "agent_config_update":
        return AGENT_CONFIG_PATTERNS + PROMPT_PATTERNS
    if patch_type in {"eval_update", "scorer_update"}:
        return EVAL_PATTERNS
    if patch_type == "rollback_patch":
        return []
    return PROMPT_PATTERNS


def _existing_allowed_targets(root: Path, patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        for candidate in root.glob(pattern):
            if candidate.is_file() and is_allowed_target(candidate, root):
                paths.append(candidate.resolve())
    return sorted(set(paths), key=lambda item: _relative(root, item).casefold())


def _resolve_under_root(root: Path, path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def _relative(root: Path, path: Path | str) -> str:
    target = Path(path)
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return target.as_posix()
