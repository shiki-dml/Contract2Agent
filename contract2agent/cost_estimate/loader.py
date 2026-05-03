from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from contract2agent.triage.discovery import safe_read_text
from contract2agent.triage.parsers import extract_eval_cases

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is a declared dependency.
    yaml = None  # type: ignore[assignment]


@dataclass
class EvalMetadata:
    exists: bool = False
    case_count: int | None = None
    tags: list[str] = field(default_factory=list)
    scorer_types: list[str] = field(default_factory=list)
    expected_tools: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    llm_judge_detected: bool = False
    deterministic_scorers_only: bool | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class BaselineMetadata:
    exists: bool = False
    path: str | None = None
    historical_cost_available: bool = False
    avg_runtime_seconds: float | None = None
    slowest_tests: list[str] = field(default_factory=list)
    slowest_failure_types: list[str] = field(default_factory=list)
    raw_keys: list[str] = field(default_factory=list)
    warning: str | None = None


@dataclass
class CostEstimateInputs:
    triage: dict[str, Any] | None
    triage_path: Path | None
    triage_missing: bool
    project_root: Path
    eval_metadata: EvalMetadata
    baseline_metadata: BaselineMetadata
    warnings: list[str] = field(default_factory=list)

    @property
    def source_triage_id(self) -> str | None:
        if not self.triage:
            return None
        value = self.triage.get("triage_id")
        return str(value) if value else None


def load_cost_estimate_inputs(
    from_triage: Path | None,
    *,
    cwd: Path,
    project_root_override: Path | None = None,
) -> CostEstimateInputs:
    warnings: list[str] = []
    triage_path = _resolve(cwd, from_triage) if from_triage is not None else None
    triage: dict[str, Any] | None = None
    triage_missing = False

    if triage_path is None:
        candidate = cwd / ".agentdoctor" / "triage" / "latest.json"
        triage_path = candidate
    if triage_path.exists():
        try:
            loaded = json.loads(triage_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                triage = loaded
            else:
                warnings.append("Triage report JSON is not an object; using limited estimate.")
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"Could not read triage report: {exc}")
    else:
        triage_missing = True
        warnings.append("No triage report found. Run agentdoctor triage first for a better estimate.")

    project_root = _project_root(cwd, triage, project_root_override)
    eval_metadata = _load_eval_metadata(triage, project_root, warnings)
    baseline_metadata = _load_baseline_metadata(triage, project_root, warnings)
    return CostEstimateInputs(
        triage=triage,
        triage_path=triage_path,
        triage_missing=triage_missing,
        project_root=project_root,
        eval_metadata=eval_metadata,
        baseline_metadata=baseline_metadata,
        warnings=warnings,
    )


def _load_eval_metadata(
    triage: dict[str, Any] | None,
    project_root: Path,
    warnings: list[str],
) -> EvalMetadata:
    metadata = EvalMetadata()
    eval_configs: dict[str, Any] = {}

    if triage:
        coverage = _mapping(triage.get("eval_coverage"))
        count = coverage.get("eval_case_count")
        if isinstance(count, int):
            metadata.case_count = count
        metadata.tags.extend(_string_list(coverage.get("detected_tags")))
        metadata.tags.extend(_string_list(coverage.get("covered_areas")))

        for source in _input_source_list(triage, "evals"):
            path_value = source.get("path")
            if source.get("status") != "found" or not path_value:
                continue
            path = _resolve(project_root, Path(str(path_value)))
            read = safe_read_text(path, project_root)
            if read.text is None:
                message = read.reason or f"Could not read eval metadata: {path_value}"
                metadata.warnings.append(message)
                warnings.append(message)
                continue
            loaded = _parse_structured(path, read.text, metadata.warnings)
            eval_configs[str(path_value)] = loaded
            metadata.paths.append(str(path_value))

    if eval_configs:
        cases = extract_eval_cases(eval_configs)
        metadata.exists = True
        metadata.case_count = len(cases)
        metadata.tags = _sorted_unique(metadata.tags + _tags_from_cases(cases))
        metadata.scorer_types = _sorted_unique(_scorers_from_cases(cases))
        metadata.expected_tools = _sorted_unique(_expected_tools_from_cases(cases))
    elif metadata.case_count:
        metadata.exists = metadata.case_count > 0
        metadata.tags = _sorted_unique(metadata.tags)

    if not metadata.exists:
        message = "No eval metadata found. Test count estimate is rule-based."
        metadata.warnings.append(message)
        warnings.append(message)

    metadata.llm_judge_detected = any(
        token in scorer.casefold()
        for scorer in metadata.scorer_types
        for token in ("llm", "judge", "model", "gpt", "claude")
    )
    deterministic_tokens = ("exact", "regex", "schema", "json", "contains", "unit", "deterministic")
    if metadata.scorer_types:
        metadata.deterministic_scorers_only = all(
            any(token in scorer.casefold() for token in deterministic_tokens)
            for scorer in metadata.scorer_types
        )
    else:
        metadata.deterministic_scorers_only = None
    return metadata


def _load_baseline_metadata(
    triage: dict[str, Any] | None,
    project_root: Path,
    warnings: list[str],
) -> BaselineMetadata:
    status = _mapping(triage.get("baseline_status")) if triage else {}
    candidate_path = status.get("path") or ".agentdoctor/baselines/latest.json"
    baseline = BaselineMetadata(
        exists=bool(status.get("exists")),
        path=str(candidate_path) if candidate_path else None,
        warning=_string_or_none(status.get("warning")),
    )
    if not baseline.exists and not (project_root / str(candidate_path)).exists():
        baseline.warning = baseline.warning or "No baseline found. Regression cost estimate is limited."
        warnings.append(baseline.warning)
        return baseline

    path = _resolve(project_root, Path(str(candidate_path)))
    read = safe_read_text(path, project_root)
    if read.text is None:
        baseline.warning = read.reason or "Baseline metadata could not be read."
        warnings.append(baseline.warning)
        return baseline
    loaded = _parse_structured(path, read.text, warnings)
    if not isinstance(loaded, dict):
        baseline.warning = "Baseline metadata is not an object; historical cost was not used."
        warnings.append(baseline.warning)
        return baseline

    baseline.exists = True
    baseline.raw_keys = sorted(str(key) for key in loaded.keys())
    runtime = _extract_runtime_seconds(loaded)
    if runtime is not None:
        baseline.historical_cost_available = True
        baseline.avg_runtime_seconds = runtime
    baseline.slowest_tests = _string_list(
        loaded.get("previous_slowest_tests") or loaded.get("slowest_tests")
    )
    baseline.slowest_failure_types = _string_list(
        loaded.get("previous_slowest_failure_types") or loaded.get("slowest_failure_types")
    )
    if not baseline.historical_cost_available:
        baseline.warning = baseline.warning or "Baseline found without historical runtime metadata."
    return baseline


def _parse_structured(path: Path, text: str, warnings: list[str]) -> Any:
    try:
        if path.suffix.casefold() == ".json":
            return json.loads(text)
        if path.suffix.casefold() in {".yaml", ".yml"}:
            if yaml is None:
                raise RuntimeError("PyYAML is required to read YAML files.")
            return yaml.safe_load(text) or {}
    except (json.JSONDecodeError, RuntimeError, ValueError) as exc:
        warnings.append(f"Could not parse metadata file {path.name}: {exc}")
        return {}
    if yaml is not None:
        try:
            return yaml.safe_load(text) or {}
        except yaml.YAMLError:
            return text
    return text


def _extract_runtime_seconds(value: dict[str, Any]) -> float | None:
    direct_keys = (
        "avg_runtime_seconds",
        "average_runtime_seconds",
        "previous_avg_runtime",
        "runtime_seconds",
        "elapsed_seconds",
        "duration_seconds",
    )
    for key in direct_keys:
        number = _to_float(value.get(key))
        if number is not None:
            return number
    metrics = _mapping(value.get("metrics")) or _mapping(value.get("historical_cost"))
    for key in direct_keys:
        number = _to_float(metrics.get(key))
        if number is not None:
            return number
    runs = value.get("runs")
    if isinstance(runs, list):
        durations = [
            number
            for item in runs
            if isinstance(item, dict)
            for number in [_to_float(item.get("runtime_seconds") or item.get("duration_seconds"))]
            if number is not None
        ]
        if durations:
            return round(sum(durations) / len(durations), 2)
    return None


def _input_source_list(triage: dict[str, Any], key: str) -> list[dict[str, Any]]:
    input_sources = _mapping(triage.get("input_sources"))
    value = input_sources.get(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _tags_from_cases(cases: list[dict[str, Any]]) -> list[str]:
    tags: list[str] = []
    for case in cases:
        tags.extend(_string_list(case.get("tags")))
        tags.extend(_string_list(case.get("tag")))
        tags.extend(_string_list(case.get("areas")))
    return tags


def _scorers_from_cases(cases: list[dict[str, Any]]) -> list[str]:
    scorers: list[str] = []
    for case in cases:
        raw = case.get("scorers") or case.get("scorer") or case.get("assertions")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    name = item.get("type") or item.get("name") or item.get("scorer")
                    if name:
                        scorers.append(str(name))
                else:
                    scorers.append(str(item))
        elif isinstance(raw, dict):
            scorers.extend(str(key) for key in raw.keys())
        elif raw:
            scorers.append(str(raw))
    return scorers


def _expected_tools_from_cases(cases: list[dict[str, Any]]) -> list[str]:
    tools: list[str] = []
    for case in cases:
        for key in ("expected_tools", "tools", "expected_tool_calls"):
            raw = case.get(key)
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict) and item.get("name"):
                        tools.append(str(item["name"]))
                    elif isinstance(item, str):
                        tools.append(item)
            elif isinstance(raw, str):
                tools.append(raw)
    return tools


def _project_root(
    cwd: Path,
    triage: dict[str, Any] | None,
    project_root_override: Path | None,
) -> Path:
    if project_root_override is not None:
        return project_root_override.expanduser().resolve()
    if triage and triage.get("project_root"):
        return Path(str(triage["project_root"])).expanduser().resolve()
    return cwd.resolve()


def _resolve(root: Path, path: Path | None) -> Path:
    if path is None:
        return root.resolve()
    path = path.expanduser()
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if value}, key=str.casefold)


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
