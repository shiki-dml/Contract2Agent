from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from contract2agent.patch_preview.models import FAILURE_TYPES, LoadedFindings, PatchFinding
from contract2agent.patch_preview.security import sanitize_data, sanitize_text

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is a declared dependency.
    yaml = None  # type: ignore[assignment]


TOOL_NAME_RE = re.compile(
    r"\b([a-z][a-z0-9_]*(?:reader|writer|sender|creator|search|tool|shell|database|exec))\b",
    re.IGNORECASE,
)


def load_findings(path: str | Path | None) -> LoadedFindings:
    if path is None:
        return LoadedFindings(
            source_path=None,
            source_run_id=None,
            warnings=["No run or findings file was provided."],
        )

    source = Path(path)
    if not source.exists():
        return LoadedFindings(
            source_path=str(source),
            source_run_id=None,
            warnings=[
                f"Run/findings file not found: {source}",
                "Run `agentdoctor quick` or `agentdoctor deep --rounds 3` first.",
            ],
        )

    try:
        raw = _load_structured_file(source)
    except ValueError as exc:
        return LoadedFindings(
            source_path=str(source),
            source_run_id=None,
            warnings=[str(exc)],
        )

    data = raw if isinstance(raw, dict) else {"findings": raw if isinstance(raw, list) else []}
    data = sanitize_data(data)
    source_run_id = _first_string(
        data.get("run_id"),
        data.get("diagnostic_run_id"),
        data.get("report_id"),
        data.get("id"),
        data.get("triage_id"),
        data.get("patch_preview_id"),
    ) or source.stem
    findings: list[PatchFinding] = []

    top_findings = data.get("findings", [])
    findings.extend(_findings_from_items(top_findings, default_round_id=None))

    for round_item in _as_list(data.get("rounds")):
        if not isinstance(round_item, dict):
            continue
        round_id = _round_id(round_item)
        findings.extend(_findings_from_items(round_item.get("findings", []), round_id))

    for issue in _as_list(data.get("issues")):
        if isinstance(issue, dict):
            findings.extend(_findings_from_items([_issue_to_finding(issue)], None))

    previous_patch_metadata = _previous_patch_metadata(data)
    return LoadedFindings(
        source_path=str(source),
        source_run_id=source_run_id,
        findings=findings,
        raw_report=data,
        warnings=[],
        previous_patch_metadata=previous_patch_metadata,
    )


def count_failure_types_in_file(path: str | Path | None) -> tuple[dict[str, int], str | None]:
    loaded = load_findings(path) if path is not None and Path(path).exists() else None
    if loaded is None:
        return {}, None
    counts: dict[str, int] = {}
    for finding in loaded.findings:
        counts[finding.failure_type] = counts.get(finding.failure_type, 0) + 1
    return counts, loaded.source_path


def normalize_failure_type(value: Any, *, fallback_text: str = "") -> str:
    if isinstance(value, str) and value.strip():
        normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
        aliases = {
            "SCHEMA_ERROR": "OUTPUT_SCHEMA_ERROR",
            "FORMAT_ERROR": "OUTPUT_FORMAT_ERROR",
            "FORBIDDEN_TOOL": "FORBIDDEN_TOOL_CALL",
            "SAFETY": "SAFETY_RISK",
            "HALLUCINATION": "HALLUCINATION_RISK",
            "STABILITY": "LOW_STABILITY",
            "TOOL_ARGS_ERROR": "TOOL_ARGUMENT_ERROR",
            "TOOL_ARG_ERROR": "TOOL_ARGUMENT_ERROR",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized in FAILURE_TYPES:
            return normalized
    return infer_failure_type(fallback_text)


def infer_failure_type(text: str) -> str:
    lowered = text.casefold()
    if any(term in lowered for term in ("scorer uncertain", "judge uncertain", "ambiguous scorer")):
        return "SCORER_UNCERTAIN"
    if any(term in lowered for term in ("forbidden tool", "forbidden_tool", "called forbidden")):
        return "FORBIDDEN_TOOL_CALL"
    if any(term in lowered for term in ("safety", "unsafe", "permission", "approval gate")):
        return "SAFETY_RISK"
    if any(term in lowered for term in ("invalid json", "json", "schema", "extra field", "markdown fence")):
        return "OUTPUT_SCHEMA_ERROR"
    if any(term in lowered for term in ("format", "markdown", "heading", "section", "template", "table")):
        return "OUTPUT_FORMAT_ERROR"
    if any(term in lowered for term in ("not called", "missing tool", "tool missing", "must call", "expected tool")):
        return "TOOL_MISSING"
    if any(term in lowered for term in ("wrong order", "before", "after", "sequence", "order")):
        return "TOOL_ORDER_ERROR"
    if any(term in lowered for term in ("argument", "parameter", "invalid path", "required field", "bad args")):
        return "TOOL_ARGUMENT_ERROR"
    if any(term in lowered for term in ("file_not_found", "not found", "tool error", "fallback", "clarification")):
        return "ERROR_HANDLING_MISSING"
    if any(term in lowered for term in ("hallucinat", "source", "evidence", "ground", "guessed")):
        return "HALLUCINATION_RISK"
    if any(term in lowered for term in ("loop", "repeated", "max steps", "too many steps", "same tool")):
        return "LOOP_RISK"
    if "regression" in lowered:
        return "REGRESSION"
    if any(term in lowered for term in ("unstable", "stability", "non-deterministic", "flaky")):
        return "LOW_STABILITY"
    if "config" in lowered:
        return "CONFIG_ERROR"
    if any(term in lowered for term in ("incomplete", "missing required", "task")):
        return "TASK_INCOMPLETE"
    return "UNKNOWN"


def _load_structured_file(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Could not read run/findings file {path}: {exc}") from exc

    suffix = path.suffix.casefold()
    try:
        if suffix in {".yaml", ".yml"}:
            if yaml is None:
                raise ValueError("PyYAML is required to read YAML files.")
            return yaml.safe_load(text) or {}
        return json.loads(text)
    except (json.JSONDecodeError, yaml.YAMLError if yaml is not None else ValueError) as exc:
        raise ValueError(f"Could not parse run/findings file {path}: {exc}") from exc


def _findings_from_items(items: Any, default_round_id: str | None) -> list[PatchFinding]:
    findings: list[PatchFinding] = []
    for index, item in enumerate(_as_list(items), start=1):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or item.get("result") or "FAIL").upper()
        if status == "PASS":
            continue
        text = " ".join(
            sanitize_text(item.get(key))
            for key in ("title", "description", "message", "reason", "check_message")
            if item.get(key) is not None
        )
        failure_types = _explicit_failure_types(item, text)
        finding_id = _first_string(item.get("id"), item.get("finding_id")) or f"finding_{index:03d}"
        for failure_type in failure_types:
            finding = PatchFinding(
                id=finding_id,
                failure_type=failure_type,
                title=sanitize_text(_first_string(item.get("title"), item.get("name")) or ""),
                description=sanitize_text(
                    _first_string(
                        item.get("description"),
                        item.get("message"),
                        item.get("reason"),
                        item.get("check_message"),
                    )
                    or text
                ),
                severity=sanitize_text(str(item.get("severity") or "error")),
                status=status,
                related_test_id=_first_string(item.get("related_test_id"), item.get("test_case_id"), item.get("test_id")),
                related_trace_id=_first_string(item.get("related_trace_id"), item.get("trace_id")),
                source_round_id=_first_string(item.get("source_round_id"), item.get("round_id")) or default_round_id,
                likely_cause=_first_string(item.get("likely_cause"), item.get("cause"), item.get("natural_language_cause")),
                target_file=_extract_target_file(item),
                tool_name=_extract_tool_name(item, text),
                evidence=_extract_evidence(item),
            )
            findings.append(finding)
    return findings


def _explicit_failure_types(item: dict[str, Any], fallback_text: str) -> list[str]:
    values: list[Any] = []
    for key in ("failure_type", "failureType", "type"):
        if item.get(key):
            values.append(item[key])
    if isinstance(item.get("failure_types"), list):
        values.extend(item["failure_types"])
    if isinstance(item.get("tags"), list):
        values.extend(tag for tag in item["tags"] if str(tag).upper() in FAILURE_TYPES)
    normalized = [normalize_failure_type(value, fallback_text=fallback_text) for value in values]
    if not normalized:
        normalized = [infer_failure_type(fallback_text)]
    return sorted(set(normalized))


def _issue_to_finding(issue: dict[str, Any]) -> dict[str, Any]:
    category = str(issue.get("category") or "")
    text = " ".join(
        str(issue.get(key) or "")
        for key in ("natural_language_cause", "suggested_fix", "suggested_agent_prompt")
    )
    failure_type = {
        "agent_prompt_too_weak": "TASK_INCOMPLETE",
        "eval_expectation_too_strict": "SCORER_UNCERTAIN",
        "eval_expectation_ambiguous": "SCORER_UNCERTAIN",
        "checker_too_loose": "CONFIG_ERROR",
        "checker_too_strict": "SCORER_UNCERTAIN",
        "contract_too_loose": "CONFIG_ERROR",
        "contract_too_strict": "SCORER_UNCERTAIN",
    }.get(category, infer_failure_type(text))
    return {
        "id": issue.get("id") or category or "diagnosis_issue",
        "failure_type": failure_type,
        "title": category or "Diagnosis issue",
        "description": issue.get("natural_language_cause") or issue.get("suggested_fix") or text,
        "likely_cause": issue.get("natural_language_cause"),
        "target_file": issue.get("likely_location"),
    }


def _extract_evidence(item: dict[str, Any]) -> dict[str, Any]:
    evidence = item.get("evidence")
    if isinstance(evidence, dict):
        return sanitize_data(evidence)
    return {}


def _extract_target_file(item: dict[str, Any]) -> str | None:
    for key in ("target_file", "target", "file", "path"):
        value = _first_string(item.get(key))
        if value:
            return _first_path(value)
    patch = item.get("suggested_patch")
    if isinstance(patch, dict):
        target = _first_string(patch.get("target"), patch.get("file"), patch.get("path"))
        if target:
            return _first_path(target)
    location = _first_string(item.get("likely_location"))
    return _first_path(location) if location else None


def _first_path(value: str) -> str | None:
    if not value:
        return None
    for token in re.split(r"\s+or\s+|[,;]\s*", value):
        token = token.strip(" `\"'")
        if "/" in token or "\\" in token or "." in Path(token).name:
            return token.replace("\\", "/")
    return value.strip(" `\"'") or None


def _extract_tool_name(item: dict[str, Any], text: str) -> str | None:
    for key in ("tool", "tool_name", "missing_tool", "expected_tool"):
        value = _first_string(item.get(key))
        if value:
            return value
    evidence = item.get("evidence")
    if isinstance(evidence, dict):
        for key in ("tool", "missing_tool", "expected_tool", "called_tool"):
            value = _first_string(evidence.get(key))
            if value:
                return value
    match = TOOL_NAME_RE.search(text)
    return match.group(1) if match else None


def _previous_patch_metadata(data: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("previous_patch", "latest_patch", "rollback_metadata"):
        value = data.get(key)
        if isinstance(value, dict):
            return sanitize_data(value)
    history = data.get("patch_history")
    if isinstance(history, list) and history:
        latest = history[-1]
        if isinstance(latest, dict):
            return sanitize_data(latest)
    return None


def _round_id(item: dict[str, Any]) -> str:
    value = item.get("round_index") or item.get("round") or item.get("id")
    if isinstance(value, int):
        return f"round_{value:03d}"
    if isinstance(value, str) and value:
        return value
    return "round_unknown"


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return sanitize_text(value.strip())
        if isinstance(value, (int, float)):
            return str(value)
    return None
