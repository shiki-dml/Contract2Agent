from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

from contract2agent.path_safety import PathContainmentError, is_within, resolve_within
from contract2agent.triage.models import InputSource, TriageWarning


MAX_TEXT_FILE_BYTES = 1024 * 1024

AGENT_CONFIG_PATTERNS = [
    "agent.yaml",
    "agent.yml",
    "agent.json",
    "agents/*.yaml",
    "agents/*.yml",
    "agents/*.json",
    ".agentdoctor/agent.yaml",
    ".agentdoctor/config.yaml",
]
PROMPT_PATTERNS = [
    "prompts/*.md",
    "prompts/*.txt",
    "prompt.md",
    "system_prompt.md",
    "instructions.md",
    "agent/prompts/*.md",
]
TOOL_CONFIG_PATTERNS = [
    "tool_descriptions.yaml",
    "tool_descriptions.yml",
    "tools.yaml",
    "tools.yml",
    "agent_tools.yaml",
    "workflow_config.yaml",
    "workflow_config.yml",
]
EVAL_PATTERNS = [
    "evals/*.yaml",
    "evals/*.yml",
    "evals/*.json",
    "tests/evals/*.yaml",
    "tests/evals/*.yml",
    "tests/evals/*.json",
    "agentdoctor_tests/*.yaml",
    "agentdoctor_tests/*.yml",
    "agentdoctor_tests/*.json",
    ".agentdoctor/evals/*.yaml",
    ".agentdoctor/evals/*.yml",
    ".agentdoctor/evals/*.json",
]
BASELINE_PATTERNS = [
    ".agentdoctor/baselines/latest.json",
    ".agentdoctor/baselines/*.json",
]
AGENTDOCTOR_CONFIG_PATTERNS = [
    ".agentdoctor/config.yaml",
    ".agentdoctor/config.yml",
    "agentdoctor.yaml",
    "agentdoctor.yml",
]

EXCLUDED_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    ".git",
    "dist",
    "build",
    "__pycache__",
}
EXCLUDED_FILE_PATTERNS = {
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "*.crt",
    "secrets.*",
    "credentials.*",
}


@dataclass
class FileRead:
    path: Path
    text: str | None
    status: str
    reason: str | None = None


@dataclass
class DiscoveryResult:
    project_root: Path
    agent_config: InputSource
    agent_config_path: Path | None = None
    prompt_sources: list[InputSource] = field(default_factory=list)
    prompt_paths: list[Path] = field(default_factory=list)
    tool_sources: list[InputSource] = field(default_factory=list)
    tool_paths: list[Path] = field(default_factory=list)
    eval_sources: list[InputSource] = field(default_factory=list)
    eval_paths: list[Path] = field(default_factory=list)
    baseline: InputSource = field(default_factory=lambda: InputSource(None, "missing"))
    baseline_path: Path | None = None
    agentdoctor_config: InputSource = field(default_factory=lambda: InputSource(None, "missing"))
    agentdoctor_config_path: Path | None = None
    all_agent_configs: list[Path] = field(default_factory=list)
    warnings: list[TriageWarning] = field(default_factory=list)

    def input_sources(self) -> dict[str, object]:
        return {
            "agent_config": self.agent_config,
            "prompts": self.prompt_sources,
            "tools": self.tool_sources,
            "evals": self.eval_sources,
            "baseline": self.baseline,
            "agentdoctor_config": self.agentdoctor_config,
        }


def discover_project(project_root: str | Path, agent_path: str | Path | None = None) -> DiscoveryResult:
    root = Path(project_root).expanduser().resolve()
    result = DiscoveryResult(
        project_root=root,
        agent_config=InputSource(None, "missing", "No agent config found."),
    )

    discovered_agents = _dedupe_paths(_glob_patterns(root, AGENT_CONFIG_PATTERNS))
    result.all_agent_configs = discovered_agents

    if agent_path is not None:
        try:
            selected = _resolve_under_root(root, agent_path)
        except PathContainmentError:
            result.agent_config = InputSource(
                Path(agent_path).as_posix(),
                "skipped",
                "Specified --agent path is outside --project-root.",
            )
            result.warnings.append(
                TriageWarning(
                    id="agent_path_outside_project_root",
                    severity="warning",
                    title="Skipped outside agent config",
                    description="The specified --agent path resolves outside --project-root and was not read.",
                    evidence=[Path(agent_path).as_posix()],
                    recommended_action="Pass an agent config path inside --project-root.",
                )
            )
        else:
            if selected.exists() and selected.is_file() and not is_excluded_path(selected, root):
                result.agent_config_path = selected
                result.agent_config = InputSource(_relative(root, selected), "found")
            else:
                result.agent_config = InputSource(
                    _relative(root, selected),
                    "missing",
                    "Specified --agent path was not found or is excluded.",
                )
        result.prompt_paths = _dedupe_paths(_glob_patterns(root, PROMPT_PATTERNS))
    else:
        if discovered_agents:
            selected = discovered_agents[0]
            result.agent_config_path = selected
            result.agent_config = InputSource(_relative(root, selected), "found")
            if len(discovered_agents) > 1:
                result.warnings.append(
                    TriageWarning(
                        id="multiple_agent_configs",
                        severity="warning",
                        title="Multiple agent configs found",
                        description=(
                            f"Multiple agent configs found. Using {_relative(root, selected)}. "
                            "Pass --agent to select another agent."
                        ),
                        evidence=[_relative(root, path) for path in discovered_agents],
                        recommended_action="Pass --agent to select the intended agent config.",
                    )
                )
        result.prompt_paths = _dedupe_paths(_glob_patterns(root, PROMPT_PATTERNS))

    result.prompt_sources = _sources_for_paths(root, result.prompt_paths)
    result.tool_paths = _dedupe_paths(_glob_patterns(root, TOOL_CONFIG_PATTERNS))
    result.tool_sources = _sources_for_paths(root, result.tool_paths)
    result.eval_paths = _dedupe_paths(_glob_patterns(root, EVAL_PATTERNS))
    result.eval_sources = _sources_for_paths(root, result.eval_paths)

    baselines = _dedupe_paths(_glob_patterns(root, BASELINE_PATTERNS))
    if baselines:
        baseline = next(
            (path for path in baselines if path.as_posix().endswith("/latest.json")),
            baselines[0],
        )
        result.baseline_path = baseline
        result.baseline = InputSource(_relative(root, baseline), "found")
    else:
        result.baseline = InputSource(".agentdoctor/baselines/latest.json", "missing")

    configs = _dedupe_paths(_glob_patterns(root, AGENTDOCTOR_CONFIG_PATTERNS))
    if configs:
        result.agentdoctor_config_path = configs[0]
        result.agentdoctor_config = InputSource(_relative(root, configs[0]), "found")
    else:
        result.agentdoctor_config = InputSource(".agentdoctor/config.yaml", "missing")

    return result


def safe_read_text(path: Path, project_root: Path) -> FileRead:
    if not is_within(path, project_root):
        return FileRead(path=path, text=None, status="skipped", reason="Path is outside project root.")
    if is_excluded_path(path, project_root):
        return FileRead(path=path, text=None, status="skipped", reason="Excluded secret or unsafe path.")
    try:
        size = path.stat().st_size
    except OSError as exc:
        return FileRead(path=path, text=None, status="error", reason=str(exc))
    if size > MAX_TEXT_FILE_BYTES:
        return FileRead(path=path, text=None, status="skipped", reason=f"Skipped large file: {_relative(project_root, path)}")
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return FileRead(
            path=path,
            text=None,
            status="skipped",
            reason=f"Skipped non-text or unreadable file: {_relative(project_root, path)} ({exc})",
        )
    return FileRead(path=path, text=text, status="found")


def warning_for_file_read(read: FileRead, project_root: Path) -> TriageWarning | None:
    if read.status == "found":
        return None
    title = "Skipped large file" if read.reason and "large file" in read.reason else "Skipped unreadable file"
    return TriageWarning(
        id=f"file_{read.status}_{_slug(_relative(project_root, read.path))}",
        severity="warning",
        title=title,
        description=read.reason or f"Could not read {_relative(project_root, read.path)}.",
        evidence=[_relative(project_root, read.path)],
        recommended_action="Review the file manually if it is needed for triage.",
    )


def is_excluded_path(path: Path, project_root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        return True
    parts = {part.casefold() for part in relative.parts[:-1]}
    if parts & EXCLUDED_DIRS:
        return True
    name = relative.name
    return any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDED_FILE_PATTERNS)


def _glob_patterns(root: Path, patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file() and not is_excluded_path(path, root):
                paths.append(path.resolve())
    return paths


def _sources_for_paths(root: Path, paths: list[Path]) -> list[InputSource]:
    return [InputSource(_relative(root, path), "found") for path in paths]


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    return sorted({path.resolve() for path in paths}, key=lambda item: item.as_posix().casefold())


def _resolve_under_root(root: Path, path: str | Path) -> Path:
    return resolve_within(root, path)


def _relative(root: Path, path: Path | str) -> str:
    target = Path(path)
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return target.as_posix()


def _slug(value: str) -> str:
    cleaned = []
    for char in value.casefold():
        if char.isalnum():
            cleaned.append(char)
        elif cleaned and cleaned[-1] != "_":
            cleaned.append("_")
    return "".join(cleaned).strip("_") or "path"
