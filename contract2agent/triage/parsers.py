from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from contract2agent.triage.discovery import FileRead, safe_read_text, warning_for_file_read
from contract2agent.triage.models import AgentSummary, TriageWarning

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is a declared dependency.
    yaml = None  # type: ignore[assignment]


@dataclass
class RawProjectData:
    agent_config: dict[str, Any] | None = None
    agent_config_text: str = ""
    prompt_texts: dict[str, str] = field(default_factory=dict)
    tool_configs: dict[str, Any] = field(default_factory=dict)
    eval_configs: dict[str, Any] = field(default_factory=dict)
    agentdoctor_config: dict[str, Any] | None = None
    baseline_data: dict[str, Any] | None = None
    warnings: list[TriageWarning] = field(default_factory=list)


@dataclass
class PromptSignals:
    has_output_format: bool = False
    has_tool_usage: bool = False
    has_error_handling: bool = False
    has_safety: bool = False
    has_source_grounding: bool = False
    has_tool_call_order: bool = False
    has_max_tool_calls: bool = False
    has_human_approval: bool = False
    prompt_char_count: int = 0
    evidence: dict[str, list[str]] = field(default_factory=dict)


def load_project_data(
    *,
    project_root: Path,
    agent_config_path: Path | None,
    prompt_paths: list[Path],
    tool_paths: list[Path],
    eval_paths: list[Path],
    baseline_path: Path | None,
    agentdoctor_config_path: Path | None,
) -> RawProjectData:
    data = RawProjectData()

    if agent_config_path is not None:
        read = safe_read_text(agent_config_path, project_root)
        _append_read_warning(data, read, project_root)
        if read.text is not None:
            data.agent_config_text = read.text
            loaded = _parse_structured_file(agent_config_path, read.text, data, project_root)
            if isinstance(loaded, dict):
                data.agent_config = loaded
            else:
                data.warnings.append(
                    TriageWarning(
                        id="agent_config_not_mapping",
                        severity="warning",
                        title="Agent config is not a mapping",
                        description="The selected agent config was readable but did not contain an object/mapping.",
                        evidence=[_relative(project_root, agent_config_path)],
                        recommended_action="Use a YAML or JSON mapping for agent metadata.",
                    )
                )

    for path in prompt_paths:
        read = safe_read_text(path, project_root)
        _append_read_warning(data, read, project_root)
        if read.text is not None:
            data.prompt_texts[_relative(project_root, path)] = read.text

    for path in tool_paths:
        read = safe_read_text(path, project_root)
        _append_read_warning(data, read, project_root)
        if read.text is not None:
            loaded = _parse_structured_file(path, read.text, data, project_root)
            data.tool_configs[_relative(project_root, path)] = loaded

    for path in eval_paths:
        read = safe_read_text(path, project_root)
        _append_read_warning(data, read, project_root)
        if read.text is not None:
            loaded = _parse_structured_file(path, read.text, data, project_root)
            data.eval_configs[_relative(project_root, path)] = loaded

    if baseline_path is not None:
        read = safe_read_text(baseline_path, project_root)
        _append_read_warning(data, read, project_root)
        if read.text is not None:
            loaded = _parse_structured_file(baseline_path, read.text, data, project_root)
            data.baseline_data = loaded if isinstance(loaded, dict) else None

    if agentdoctor_config_path is not None:
        read = safe_read_text(agentdoctor_config_path, project_root)
        _append_read_warning(data, read, project_root)
        if read.text is not None:
            loaded = _parse_structured_file(agentdoctor_config_path, read.text, data, project_root)
            data.agentdoctor_config = loaded if isinstance(loaded, dict) else None

    return data


def extract_agent_summary(
    *,
    project_root: Path,
    agent_config_path: Path | None,
    prompt_paths: list[Path],
    tool_count: int,
    eval_case_count: int,
    data: RawProjectData,
) -> AgentSummary:
    config = data.agent_config or {}
    nested_agent = _mapping(config.get("agent"))
    model_spec = _mapping(config.get("model")) or _mapping(config.get("llm"))
    provider_spec = _mapping(config.get("provider"))

    name = _first_string(
        config.get("name"),
        nested_agent.get("name"),
        config.get("agent_name"),
        config.get("id"),
    )
    description = _first_string(
        config.get("description"),
        nested_agent.get("description"),
        config.get("goal"),
        config.get("instructions"),
    )
    model = _first_string(
        config.get("model"),
        config.get("model_name"),
        model_spec.get("name"),
        model_spec.get("id"),
    )
    provider = _first_string(
        config.get("provider"),
        provider_spec.get("name"),
        model_spec.get("provider"),
    )
    config_files = [_relative(project_root, agent_config_path)] if agent_config_path else []
    return AgentSummary(
        name=name or "unknown",
        description=description or "unknown",
        model=model or "unknown",
        provider=provider or "unknown",
        prompt_files=[_relative(project_root, path) for path in prompt_paths],
        config_files=config_files,
        tool_count=tool_count,
        eval_case_count=eval_case_count,
    )


def extract_tool_specs(data: RawProjectData) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    if data.agent_config:
        specs.extend(_extract_tools_from_object(data.agent_config, "agent_config"))
    for source, loaded in sorted(data.tool_configs.items()):
        specs.extend(_extract_tools_from_object(loaded, source))
    return _dedupe_tools(specs)


def extract_outputs(data: RawProjectData, prompt_signals: PromptSignals) -> list[str]:
    outputs: list[str] = []
    config = data.agent_config or {}
    output = config.get("output")
    if isinstance(output, dict):
        output_format = output.get("format") or output.get("type")
        if output_format:
            outputs.append(str(output_format))
    elif isinstance(output, str):
        outputs.append(output)
    if prompt_signals.has_output_format:
        outputs.append("structured_text")
    return _sorted_unique(outputs)


def scan_prompt_signals(prompt_texts: dict[str, str], agent_config_text: str = "") -> PromptSignals:
    combined_parts = list(prompt_texts.values())
    if agent_config_text:
        combined_parts.append(agent_config_text)
    combined = "\n".join(combined_parts)
    lowered = combined.casefold()
    signals = PromptSignals(prompt_char_count=sum(len(text) for text in prompt_texts.values()))

    specs = {
        "has_output_format": [
            "json",
            "schema",
            "markdown",
            "table",
            "yaml",
            "bullet",
            "heading",
            "format",
            "return exactly",
            "must output",
        ],
        "has_tool_usage": [
            "use tool",
            "call ",
            "before answering",
            "first read",
            "retrieve",
            "search",
            "inspect",
            "do not answer without",
        ],
        "has_error_handling": [
            "if missing",
            "if not found",
            "if invalid",
            "if tool fails",
            "handle errors",
            "tool failure",
            "fallback",
            "ask for clarification",
            "file_not_found",
            "not found",
            "invalid",
            "fails",
        ],
        "has_safety": [
            "do not",
            "never",
            "forbidden",
            "must ask confirmation",
            "require approval",
            "before sending",
            "before writing",
            "avoid",
        ],
        "has_source_grounding": [
            "cite",
            "source",
            "evidence",
            "based on the document",
            "do not hallucinate",
            "do not use prior knowledge",
            "quote",
            "reference",
        ],
        "has_tool_call_order": [
            "first ",
            " then ",
            "before ",
            "after ",
            "before answering",
            "first read",
            "then summarize",
        ],
        "has_max_tool_calls": [
            "max tool",
            "maximum tool",
            "max steps",
            "maximum steps",
            "step limit",
            "at most",
            "do not exceed",
        ],
        "has_human_approval": [
            "confirm",
            "confirmation",
            "approval",
            "ask before",
            "require approval",
            "must ask",
            "before sending",
            "before writing",
            "before deleting",
        ],
    }

    for attr, keywords in specs.items():
        hits = [keyword for keyword in keywords if keyword in lowered]
        setattr(signals, attr, bool(hits))
        if hits:
            signals.evidence[attr] = hits
    return signals


def extract_eval_cases(eval_configs: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for source, loaded in sorted(eval_configs.items()):
        for index, case in enumerate(_cases_from_loaded_eval(loaded), start=1):
            if isinstance(case, dict):
                item = dict(case)
            else:
                item = {"name": str(case)}
            item.setdefault("_source", source)
            item.setdefault("_index", index)
            cases.append(item)
    return cases


def _extract_tools_from_object(value: Any, source: str) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            specs.extend(_extract_tool_items(item, source))
        return specs
    if not isinstance(value, dict):
        return specs

    for key in ("tools", "tool_descriptions", "agent_tools", "available_tools"):
        if key in value:
            specs.extend(_extract_tool_items(value[key], source))

    nested = value.get("agent")
    if isinstance(nested, dict):
        for key in ("tools", "tool_descriptions", "available_tools"):
            if key in nested:
                specs.extend(_extract_tool_items(nested[key], source))

    if not specs and source != "agent_config":
        for key, item in sorted(value.items()):
            if isinstance(item, dict):
                spec = dict(item)
                spec.setdefault("name", key)
                spec["_source"] = source
                specs.append(spec)
            elif isinstance(item, str):
                specs.append({"name": key, "description": item, "_source": source})
    return specs


def _extract_tool_items(value: Any, source: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                spec = dict(item)
                spec["_source"] = source
                items.append(spec)
            elif isinstance(item, str):
                items.append({"name": item, "_source": source})
        return items
    if isinstance(value, dict):
        for key, item in sorted(value.items()):
            if isinstance(item, dict):
                spec = dict(item)
                spec.setdefault("name", key)
                spec["_source"] = source
                items.append(spec)
            elif isinstance(item, str):
                items.append({"name": key, "description": item, "_source": source})
    elif isinstance(value, str):
        items.append({"name": value, "_source": source})
    return items


def _dedupe_tools(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for spec in specs:
        name = str(spec.get("name") or spec.get("id") or "").strip()
        if not name:
            continue
        key = name.casefold()
        existing = seen.get(key)
        if existing is None:
            item = dict(spec)
            item["name"] = name
            seen[key] = item
            continue
        if not existing.get("description") and spec.get("description"):
            existing["description"] = spec["description"]
        sources = set(str(existing.get("_source", "")).split(", "))
        sources.add(str(spec.get("_source", "")))
        existing["_source"] = ", ".join(sorted(source for source in sources if source))
    return [seen[key] for key in sorted(seen)]


def _cases_from_loaded_eval(loaded: Any) -> list[Any]:
    if isinstance(loaded, list):
        return loaded
    if not isinstance(loaded, dict):
        return []
    for key in ("cases", "tests", "evals", "examples"):
        value = loaded.get(key)
        if isinstance(value, list):
            return value
    if any(key in loaded for key in ("name", "description", "tags", "assertions", "scorers")):
        return [loaded]
    return [dict({"name": key}, **item) if isinstance(item, dict) else {"name": key, "expected": item} for key, item in loaded.items()]


def _parse_structured_file(path: Path, text: str, data: RawProjectData, project_root: Path) -> Any:
    suffix = path.suffix.casefold()
    try:
        if suffix == ".json":
            return json.loads(text)
        if suffix in {".yaml", ".yml"}:
            if yaml is None:
                raise RuntimeError("PyYAML is required to read YAML files.")
            return yaml.safe_load(text) or {}
    except (json.JSONDecodeError, RuntimeError, yaml.YAMLError if yaml is not None else ValueError) as exc:
        data.warnings.append(
            TriageWarning(
                id=f"parse_error_{_slug(_relative(project_root, path))}",
                severity="warning",
                title="Could not parse structured file",
                description=f"Could not parse {_relative(project_root, path)}: {exc}",
                evidence=[_relative(project_root, path)],
                recommended_action="Fix YAML/JSON syntax if this file should participate in triage.",
            )
        )
        return {}
    return text


def _append_read_warning(data: RawProjectData, read: FileRead, project_root: Path) -> None:
    warning = warning_for_file_read(read, project_root)
    if warning is not None:
        data.warnings.append(warning)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def _relative(root: Path, path: Path | str | None) -> str:
    if path is None:
        return ""
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
