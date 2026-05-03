from __future__ import annotations

import fnmatch
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contract2agent import __version__
from contract2agent.diagnostic_modes import (
    DiagnosticReport,
    DiagnosticRound,
    PatchHistory,
    TestCase,
    TestResult,
)

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is a declared dependency.
    yaml = None  # type: ignore[assignment]


SCHEMA_VERSION = "baseline_snapshot_v0.1"
MAX_SNAPSHOT_COPY_BYTES = 1024 * 1024

SNAPSHOT_ALLOWLIST_PATTERNS = [
    "agent.yaml",
    "agent.yml",
    "agent.json",
    "prompts/*.md",
    "prompts/*.txt",
    "prompt.md",
    "system_prompt.md",
    "instructions.md",
    "tool_descriptions.yaml",
    "tool_descriptions.yml",
    "tools.yaml",
    "tools.yml",
    "workflow_config.yaml",
    "workflow_config.yml",
    "eval_config.yaml",
    "eval_config.yml",
    "agentdoctor.yaml",
    "agentdoctor.yml",
    ".agentdoctor/config.yaml",
    ".agentdoctor/config.yml",
]

EVAL_DISCOVERY_PATTERNS = [
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

EXCLUDED_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    ".git",
    "dist",
    "build",
    "__pycache__",
}

EXCLUDED_FILE_PATTERNS = [
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "*.crt",
    "secrets.*",
    "credentials.*",
    "token.*",
    "auth.*",
]

CRITICAL_FAILURE_TYPES = {"SAFETY_RISK", "FORBIDDEN_TOOL_CALL"}
SCORER_UNCERTAIN_TYPES = {"SCORER_UNCERTAIN", "UNKNOWN"}
SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2, "critical": 3}


@dataclass
class BaselineRecord:
    baseline_id: str
    baseline_name: str | None
    created_at: str
    baseline_quality: str
    baseline_quality_warnings: list[str]
    command: str
    mode: str
    agent_identity: dict[str, Any]
    diagnostic_summary: dict[str, Any]
    confidence_summary: dict[str, Any]
    test_result_summary: dict[str, Any]
    failure_taxonomy_summary: dict[str, Any]
    review_summary: dict[str, Any]
    time_cost_summary: dict[str, Any]
    patch_summary: dict[str, Any]
    eval_suite_summary: dict[str, Any]
    agent_state_snapshot_ref: dict[str, Any]
    report_paths: dict[str, Any]
    metadata: dict[str, Any]


@dataclass
class AgentStateSnapshot:
    snapshot_id: str
    created_at: str
    agent_identity: dict[str, Any]
    model_state: dict[str, Any]
    prompt_state: dict[str, Any]
    tool_state: dict[str, Any]
    workflow_state: dict[str, Any]
    eval_state: dict[str, Any]
    patch_state: dict[str, Any]
    repo_state: dict[str, Any]
    environment_state: dict[str, Any]
    file_hashes: dict[str, str]
    copied_config_files: dict[str, Any]
    excluded_files: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResultChange:
    test_id: str
    baseline_status: str | None
    current_status: str | None
    baseline_score: float | None
    current_score: float | None
    score_delta: float | None
    baseline_failure_types: list[str]
    current_failure_types: list[str]
    change_status: str


@dataclass
class FailureTypeChange:
    failure_type: str
    baseline_count: int
    current_count: int
    delta: int
    change_status: str
    max_baseline_severity: str | None = None
    max_current_severity: str | None = None


@dataclass
class AgentStateDiff:
    changed_prompt_files: list[dict[str, Any]]
    changed_tool_configs: list[dict[str, Any]]
    changed_workflow_configs: list[dict[str, Any]]
    changed_eval_configs: list[dict[str, Any]]
    file_hash_changes: list[dict[str, Any]]
    model_changed: bool
    tool_list_changed: bool
    tool_list_diff: dict[str, list[str]]
    approval_policy_changed: bool
    git_commit_changed: bool
    dirty_state_changed: bool
    missing_snapshot: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class EvalSuiteDiff:
    eval_suite_changed: bool
    added_tests: list[str]
    removed_tests: list[str]
    changed_eval_files: list[str]
    scorer_changed: bool
    warning: str | None = None


@dataclass
class RollbackRecommendation:
    rollback_recommended: bool
    reason: str
    candidate_files: list[str]
    candidate_patch_ids: list[str]
    requires_human_review: bool


@dataclass
class BaselineComparison:
    baseline_id: str
    current_run_id: str
    compared_at: str
    comparable: str
    comparability_warnings: list[str]
    overall_delta: dict[str, Any]
    test_result_changes: list[TestResultChange]
    failure_type_changes: list[FailureTypeChange]
    severity_changes: dict[str, dict[str, int]]
    confidence_delta: dict[str, float]
    time_cost_delta: dict[str, Any]
    agent_state_diff: AgentStateDiff
    eval_suite_diff: EvalSuiteDiff
    likely_cause_candidates: list[dict[str, Any]]
    regression_summary: dict[str, Any]
    improvement_summary: dict[str, Any]
    rollback_recommendation: RollbackRecommendation
    recommended_next_command: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BaselineSaveResult:
    baseline: BaselineRecord
    snapshot: AgentStateSnapshot
    baseline_dir: Path
    baseline_path: Path
    snapshot_path: Path
    file_hashes_path: Path
    latest_path: Path
    markdown_path: Path


@dataclass
class BaselineLoadResult:
    baseline: dict[str, Any] | None
    baseline_path: Path | None
    warnings: list[str] = field(default_factory=list)


@dataclass
class BaselineCompareResult:
    comparison: BaselineComparison | None
    markdown_path: Path | None
    json_path: Path | None
    warnings: list[str] = field(default_factory=list)


def save_baseline(
    *,
    report: DiagnosticReport,
    project_root: str | Path = ".",
    baseline_name: str | None = None,
    command: str | None = None,
    agent_config_path: str | Path | None = None,
    report_dir: str | Path | None = None,
    now: datetime | None = None,
) -> BaselineSaveResult:
    root = Path(project_root).expanduser().resolve()
    stamp_dt = _now(now)
    stamp = stamp_dt.strftime("%Y%m%d_%H%M%S")
    created_at = _iso(stamp_dt)
    baseline_id = f"baseline_{stamp}"
    snapshot_id = f"snapshot_{stamp}"
    baseline_dir = root / ".agentdoctor" / "baselines" / baseline_id
    baseline_dir.mkdir(parents=True, exist_ok=True)

    snapshot = build_agent_state_snapshot(
        project_root=root,
        snapshot_id=snapshot_id,
        created_at=created_at,
        report=report,
        agent_config_path=agent_config_path,
        baseline_dir=baseline_dir,
        copy_files=True,
    )
    baseline = build_baseline_record(
        report=report,
        snapshot=snapshot,
        baseline_id=baseline_id,
        baseline_name=baseline_name,
        created_at=created_at,
        command=command or "",
        report_dir=report_dir,
        baseline_dir=baseline_dir,
        project_root=root,
    )

    baseline_path = baseline_dir / "baseline.json"
    snapshot_path = baseline_dir / "snapshot.json"
    file_hashes_path = baseline_dir / "file_hashes.json"
    latest_path = root / ".agentdoctor" / "baselines" / "latest.json"
    markdown_path = baseline_dir / "baseline_saved.md"

    _write_json(baseline_path, baseline)
    _write_json(snapshot_path, snapshot)
    _write_json(file_hashes_path, snapshot.file_hashes)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_payload = {
        "latest_baseline_id": baseline.baseline_id,
        "path": _relative(root, baseline_path),
        "baseline_name": baseline.baseline_name,
        "created_at": baseline.created_at,
        "mode": baseline.mode,
        "baseline_quality": baseline.baseline_quality,
        "confidence": baseline.diagnostic_summary.get("diagnostic_confidence"),
        "agent_name": baseline.agent_identity.get("agent_name"),
        "schema_version": SCHEMA_VERSION,
    }
    _write_json(latest_path, latest_payload)
    markdown_path.write_text(format_baseline_saved_markdown(baseline, snapshot), encoding="utf-8")
    return BaselineSaveResult(
        baseline=baseline,
        snapshot=snapshot,
        baseline_dir=baseline_dir,
        baseline_path=baseline_path,
        snapshot_path=snapshot_path,
        file_hashes_path=file_hashes_path,
        latest_path=latest_path,
        markdown_path=markdown_path,
    )


def build_baseline_record(
    *,
    report: DiagnosticReport,
    snapshot: AgentStateSnapshot,
    baseline_id: str,
    baseline_name: str | None,
    created_at: str,
    command: str,
    report_dir: str | Path | None,
    baseline_dir: Path,
    project_root: Path,
) -> BaselineRecord:
    diagnostic_summary = build_diagnostic_summary(report)
    confidence_summary = build_confidence_summary(report)
    test_result_summary = build_test_result_summary(report)
    failure_taxonomy_summary = build_failure_taxonomy_summary(report)
    review_summary = build_review_summary(report)
    time_cost_summary = build_time_cost_summary(report)
    patch_summary = build_patch_summary(report)
    eval_suite_summary = build_eval_suite_summary(report, snapshot)
    quality, warnings = determine_baseline_quality(
        mode=report.mode,
        diagnostic_summary=diagnostic_summary,
        failure_taxonomy_summary=failure_taxonomy_summary,
        eval_suite_summary=eval_suite_summary,
        review_summary=review_summary,
        patch_summary=patch_summary,
    )
    snapshot_ref = {
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_path": _relative(project_root, baseline_dir / "snapshot.json"),
        "file_hashes_path": _relative(project_root, baseline_dir / "file_hashes.json"),
    }
    reports_root = Path(report_dir) if report_dir is not None else Path("reports")
    if reports_root.is_absolute():
        reports_root_rel = _relative(project_root, reports_root)
    else:
        reports_root_rel = reports_root.as_posix()
    report_paths = {
        "markdown_report": f"{reports_root_rel}/latest.md",
        "json_report": f"{reports_root_rel}/latest.json",
        "trace_dir": f"{reports_root_rel}/rounds",
        "baseline_markdown": _relative(project_root, baseline_dir / "baseline_saved.md"),
    }
    return BaselineRecord(
        baseline_id=baseline_id,
        baseline_name=baseline_name,
        created_at=created_at,
        baseline_quality=quality,
        baseline_quality_warnings=warnings,
        command=command,
        mode=report.mode,
        agent_identity=snapshot.agent_identity,
        diagnostic_summary=diagnostic_summary,
        confidence_summary=confidence_summary,
        test_result_summary=test_result_summary,
        failure_taxonomy_summary=failure_taxonomy_summary,
        review_summary=review_summary,
        time_cost_summary=time_cost_summary,
        patch_summary=patch_summary,
        eval_suite_summary=eval_suite_summary,
        agent_state_snapshot_ref=snapshot_ref,
        report_paths=report_paths,
        metadata={
            "schema_version": SCHEMA_VERSION,
            "agentdoctor_version": __version__,
        },
    )


def build_agent_state_snapshot(
    *,
    project_root: str | Path,
    snapshot_id: str,
    created_at: str,
    report: DiagnosticReport | None = None,
    agent_config_path: str | Path | None = None,
    baseline_dir: str | Path | None = None,
    copy_files: bool = False,
) -> AgentStateSnapshot:
    root = Path(project_root).expanduser().resolve()
    baseline_target = Path(baseline_dir) if baseline_dir is not None else None
    warnings: list[str] = []
    files = discover_snapshot_files(root, agent_config_path=agent_config_path)
    safe_files = files["safe"]
    excluded_detected = detect_excluded_files(root)

    file_hashes: dict[str, str] = {}
    copied_files: list[dict[str, str]] = []
    copied_root = baseline_target / "copied_configs" if baseline_target is not None else None

    for rel_path in sorted(safe_files, key=str.casefold):
        path = root / rel_path
        hash_value = sha256_file(path)
        if hash_value is not None:
            file_hashes[rel_path] = hash_value
        if not copy_files or copied_root is None:
            continue
        copied_to, warning = copy_snapshot_file(root, path, copied_root)
        if warning:
            warnings.append(warning)
        if copied_to is not None:
            copied_files.append(
                {
                    "source": rel_path,
                    "snapshot_path": _relative(baseline_target, copied_to),
                }
            )

    parsed = _load_project_metadata(root, safe_files)
    agent_identity = _agent_identity(parsed, report, root, agent_config_path)
    model_state = _model_state(parsed)
    prompt_state = _prompt_state(root, safe_files, file_hashes, copied_files)
    tool_state = _tool_state(parsed, file_hashes)
    workflow_state = _workflow_state(parsed)
    eval_state = _eval_state(report, parsed, file_hashes)
    patch_state = _patch_state(report)
    repo_state = capture_repo_state(root)
    if not repo_state.get("git_available"):
        warnings.append("Git metadata unavailable; repo_state.git_available=false.")
    environment_state = {
        "agentdoctor_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.system().casefold() or sys.platform,
    }
    return AgentStateSnapshot(
        snapshot_id=snapshot_id,
        created_at=created_at,
        agent_identity=agent_identity,
        model_state=model_state,
        prompt_state=prompt_state,
        tool_state=tool_state,
        workflow_state=workflow_state,
        eval_state=eval_state,
        patch_state=patch_state,
        repo_state=repo_state,
        environment_state=environment_state,
        file_hashes=file_hashes,
        copied_config_files={"copied_files": sorted(copied_files, key=lambda item: item["source"])},
        excluded_files={
            "excluded_patterns": list(EXCLUDED_FILE_PATTERNS) + [f"{item}/" for item in sorted(EXCLUDED_DIRS)],
            "excluded_files_detected": excluded_detected,
        },
        warnings=warnings + files["warnings"],
        metadata={"schema_version": SCHEMA_VERSION},
    )


def compare_against_baseline(
    *,
    report: DiagnosticReport,
    project_root: str | Path = ".",
    baseline_ref: str | None = "latest",
    command: str | None = None,
    agent_config_path: str | Path | None = None,
    now: datetime | None = None,
) -> BaselineCompareResult:
    root = Path(project_root).expanduser().resolve()
    loaded = load_baseline(root, baseline_ref or "latest")
    if loaded.baseline is None:
        return BaselineCompareResult(
            comparison=None,
            markdown_path=None,
            json_path=None,
            warnings=loaded.warnings or [f"Baseline {baseline_ref or 'latest'} was not found."],
        )
    stamp_dt = _now(now)
    current_run_id = f"run_{stamp_dt.strftime('%Y%m%d_%H%M%S')}"
    current_snapshot = build_agent_state_snapshot(
        project_root=root,
        snapshot_id=f"snapshot_current_{stamp_dt.strftime('%Y%m%d_%H%M%S')}",
        created_at=_iso(stamp_dt),
        report=report,
        agent_config_path=agent_config_path,
        copy_files=False,
    )
    comparison = build_baseline_comparison(
        baseline=loaded.baseline,
        current_report=report,
        current_snapshot=current_snapshot,
        current_run_id=current_run_id,
        compared_at=_iso(stamp_dt),
        baseline_path=loaded.baseline_path,
        project_root=root,
        load_warnings=loaded.warnings,
        command=command,
    )
    baseline_dir = loaded.baseline_path.parent if loaded.baseline_path else root / ".agentdoctor" / "baselines"
    json_path = baseline_dir / "comparison_latest.json"
    markdown_path = baseline_dir / "comparison_latest.md"
    _write_json(json_path, comparison)
    markdown_path.write_text(format_comparison_markdown(comparison), encoding="utf-8")
    return BaselineCompareResult(
        comparison=comparison,
        markdown_path=markdown_path,
        json_path=json_path,
        warnings=loaded.warnings,
    )


def build_baseline_comparison(
    *,
    baseline: dict[str, Any],
    current_report: DiagnosticReport,
    current_snapshot: AgentStateSnapshot,
    current_run_id: str,
    compared_at: str,
    baseline_path: Path | None = None,
    project_root: str | Path = ".",
    load_warnings: list[str] | None = None,
    command: str | None = None,
) -> BaselineComparison:
    baseline_id = str(baseline.get("baseline_id") or baseline.get("latest_baseline_id") or "unknown")
    baseline_summary = _mapping(baseline.get("diagnostic_summary"))
    current_summary = build_diagnostic_summary(current_report)
    baseline_confidence = _to_float(
        baseline_summary.get("diagnostic_confidence")
        or baseline.get("confidence")
        or baseline.get("overall_confidence")
    )
    current_confidence = _to_float(current_summary.get("diagnostic_confidence"))
    overall_delta = {
        "baseline_confidence": baseline_confidence,
        "current_confidence": current_confidence,
        "confidence_delta": _round_delta(current_confidence, baseline_confidence),
        "baseline_pass_count": _to_int(baseline_summary.get("pass_count")),
        "current_pass_count": _to_int(current_summary.get("pass_count")),
        "pass_count_delta": _delta_int(current_summary.get("pass_count"), baseline_summary.get("pass_count")),
        "baseline_fail_count": _to_int(baseline_summary.get("fail_count")),
        "current_fail_count": _to_int(current_summary.get("fail_count")),
        "fail_count_delta": _delta_int(current_summary.get("fail_count"), baseline_summary.get("fail_count")),
        "baseline_warning_count": _to_int(baseline_summary.get("warning_count")),
        "current_warning_count": _to_int(current_summary.get("warning_count")),
        "warning_count_delta": _delta_int(current_summary.get("warning_count"), baseline_summary.get("warning_count")),
        "baseline_review_required": baseline_summary.get("review_required"),
        "current_review_required": current_summary.get("review_required"),
    }
    current_test_summary = build_test_result_summary(current_report)
    test_changes = compare_test_results(
        _mapping(baseline.get("test_result_summary")),
        current_test_summary,
    )
    current_taxonomy = build_failure_taxonomy_summary(current_report)
    failure_changes = compare_failure_types(
        _mapping(baseline.get("failure_taxonomy_summary")),
        current_taxonomy,
    )
    severity_changes = compare_severity_counts(
        _mapping(baseline.get("failure_taxonomy_summary")).get("severity_counts"),
        current_taxonomy.get("severity_counts"),
    )
    confidence_delta = compare_confidence_fields(
        _mapping(baseline.get("confidence_summary")),
        build_confidence_summary(current_report),
    )
    time_delta = compare_time_costs(
        _mapping(baseline.get("time_cost_summary")),
        build_time_cost_summary(current_report),
    )
    baseline_snapshot, snapshot_warnings = _load_baseline_snapshot(
        baseline,
        baseline_path,
        project_root=Path(project_root).expanduser().resolve(),
    )
    agent_state_diff = compare_agent_state(baseline_snapshot, current_snapshot)
    if snapshot_warnings:
        agent_state_diff.warnings.extend(snapshot_warnings)
    eval_suite_diff = compare_eval_suite(
        _mapping(baseline.get("eval_suite_summary")),
        build_eval_suite_summary(current_report, current_snapshot),
        baseline_snapshot,
        current_snapshot,
    )
    comparable, comparability_warnings = determine_comparability(
        baseline=baseline,
        current_report=current_report,
        current_agent_identity=current_snapshot.agent_identity,
        test_changes=test_changes,
        eval_suite_diff=eval_suite_diff,
        agent_state_diff=agent_state_diff,
        load_warnings=(load_warnings or []) + snapshot_warnings,
    )
    likely_causes = build_likely_cause_candidates(agent_state_diff, eval_suite_diff, failure_changes, test_changes)
    regression_summary = build_regression_summary(
        test_changes,
        failure_changes,
        severity_changes,
        overall_delta,
        time_delta,
    )
    improvement_summary = build_improvement_summary(test_changes, failure_changes, confidence_delta)
    rollback = build_rollback_recommendation(
        comparison_comparable=comparable,
        baseline_quality=str(baseline.get("baseline_quality") or "unknown"),
        failure_type_changes=failure_changes,
        severity_changes=severity_changes,
        confidence_delta=overall_delta.get("confidence_delta"),
        agent_state_diff=agent_state_diff,
        baseline_patch_summary=_mapping(baseline.get("patch_summary")),
        current_patch_summary=build_patch_summary(current_report),
    )
    return BaselineComparison(
        baseline_id=baseline_id,
        current_run_id=current_run_id,
        compared_at=compared_at,
        comparable=comparable,
        comparability_warnings=comparability_warnings,
        overall_delta=overall_delta,
        test_result_changes=test_changes,
        failure_type_changes=failure_changes,
        severity_changes=severity_changes,
        confidence_delta=confidence_delta,
        time_cost_delta=time_delta,
        agent_state_diff=agent_state_diff,
        eval_suite_diff=eval_suite_diff,
        likely_cause_candidates=likely_causes,
        regression_summary=regression_summary,
        improvement_summary=improvement_summary,
        rollback_recommendation=rollback,
        recommended_next_command=_recommended_next_command(comparable, rollback),
        metadata={"schema_version": SCHEMA_VERSION, "command": command or ""},
    )


def build_diagnostic_summary(report: DiagnosticReport) -> dict[str, Any]:
    return {
        "status": report.status,
        "diagnostic_confidence": report.overall_confidence,
        "rounds_executed": report.total_rounds_executed,
        "tests_executed": report.pass_count + report.fail_count,
        "pass_count": report.pass_count,
        "fail_count": report.fail_count,
        "warning_count": report.warning_count,
        "review_required": report.review_required,
    }


def build_confidence_summary(report: DiagnosticReport) -> dict[str, Any]:
    latest_scores: dict[str, float] = {}
    for round_report in report.rounds:
        latest_scores.update(round_report.scores)
    if report.overall_confidence is not None:
        latest_scores["overall"] = report.overall_confidence
    return {key: latest_scores[key] for key in sorted(latest_scores)}


def build_test_result_summary(report: DiagnosticReport) -> dict[str, Any]:
    latest = _latest_test_contexts(report)
    tests: list[dict[str, Any]] = []
    for test_id in sorted(latest, key=str.casefold):
        round_report, test_case, result = latest[test_id]
        failure_types = infer_failure_types(test_case, result, round_report)
        tests.append(
            {
                "test_id": test_id,
                "name": test_case.name if test_case else test_id,
                "tags": sorted(test_case.tags if test_case else []),
                "status": "passed" if result.passed else "failed",
                "score": result.score,
                "failure_types": failure_types,
            }
        )
    return {"tests": tests}


def build_failure_taxonomy_summary(report: DiagnosticReport) -> dict[str, Any]:
    failure_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter({"info": 0, "warning": 0, "error": 0, "critical": 0})
    critical_types: set[str] = set()
    review_types: set[str] = set()
    severity_by_type: dict[str, str] = {}

    latest = _latest_test_contexts(report)
    for _test_id, (round_report, test_case, result) in latest.items():
        inferred = infer_failure_types(test_case, result, round_report)
        if not inferred and result.passed:
            continue
        severity = _result_severity(test_case, result, round_report)
        for failure_type in inferred:
            failure_counts[failure_type] += 1
            severity_by_type[failure_type] = _max_severity(severity_by_type.get(failure_type), severity)
            if severity == "critical" or failure_type in CRITICAL_FAILURE_TYPES:
                critical_types.add(failure_type)
            if not result.passed or severity in {"warning", "error", "critical"}:
                review_types.add(failure_type)

    for finding in report.findings:
        severity = _normalize_severity(finding.severity)
        severity_counts[severity] += 1
        for failure_type in _extract_failure_type_tokens(f"{finding.title} {finding.description}"):
            if severity != "info":
                failure_counts[failure_type] += 1
            severity_by_type[failure_type] = _max_severity(severity_by_type.get(failure_type), severity)
            if severity == "critical" or failure_type in CRITICAL_FAILURE_TYPES:
                critical_types.add(failure_type)
            if severity != "info":
                review_types.add(failure_type)

    if not report.findings:
        for _test_id, (round_report, test_case, result) in latest.items():
            severity_counts[_result_severity(test_case, result, round_report)] += 1

    for item in report.review_items:
        for failure_type in _extract_failure_type_tokens(f"{item.title} {item.description} {item.suggested_action}"):
            review_types.add(failure_type)

    return {
        "available": True,
        "failure_type_counts": dict(sorted(failure_counts.items())),
        "severity_counts": {key: int(severity_counts.get(key, 0)) for key in ("info", "warning", "error", "critical")},
        "critical_failure_types": sorted(critical_types),
        "review_required_failure_types": sorted(review_types),
        "max_severity_by_failure_type": dict(sorted(severity_by_type.items())),
    }


def build_review_summary(report: DiagnosticReport) -> dict[str, Any]:
    return {
        "review_required": report.review_required,
        "review_policy": "unknown",
        "review_item_count": len(report.review_items),
        "review_reasons": [
            item.description or item.title for item in report.review_items[:20]
        ],
    }


def build_time_cost_summary(report: DiagnosticReport) -> dict[str, Any]:
    elapsed_values = []
    slowest: list[dict[str, Any]] = []
    for round_report in report.rounds:
        elapsed = _elapsed_seconds(round_report.started_at, round_report.finished_at)
        if elapsed is not None:
            elapsed_values.append(elapsed)
    total_elapsed = report.budget_summary.get("elapsed_seconds")
    if total_elapsed is None and elapsed_values:
        total_elapsed = round(sum(elapsed_values), 3)
    latest = _latest_test_contexts(report)
    if total_elapsed is not None and latest:
        average = round(float(total_elapsed) / max(1, len(latest)), 3)
    else:
        average = None
    for test_id, (round_report, test_case, result) in latest.items():
        elapsed = _elapsed_seconds(round_report.started_at, round_report.finished_at)
        if elapsed is None:
            continue
        per_test = round(elapsed / max(1, len(round_report.test_results)), 3)
        slowest.append(
            {
                "test_id": test_id,
                "elapsed_seconds": per_test,
                "failure_types": infer_failure_types(test_case, result, round_report),
            }
        )
    return {
        "available": total_elapsed is not None,
        "total_elapsed_seconds": total_elapsed,
        "round_count": report.total_rounds_executed,
        "test_count": report.pass_count + report.fail_count,
        "average_test_seconds": average,
        "slowest_tests": sorted(slowest, key=lambda item: item["elapsed_seconds"], reverse=True)[:5],
    }


def build_patch_summary(report: DiagnosticReport) -> dict[str, Any]:
    targeted: set[str] = set()
    patch_ids: list[str] = []
    for index, patch in enumerate(report.patch_history, start=1):
        patch_id = f"patch_{index:03d}"
        patch_ids.append(patch_id)
        targeted.update(_extract_failure_type_tokens(f"{patch.patch_summary} {patch.reason_for_patch}"))
    return {
        "patches_applied": len(report.patch_history),
        "patches_previewed": len(report.patch_history),
        "rollback_performed": any(patch.rollback_performed for patch in report.patch_history),
        "patch_ids": patch_ids,
        "failure_types_targeted": sorted(targeted),
        "patch_history": [_patch_history_item(index, patch) for index, patch in enumerate(report.patch_history, start=1)],
    }


def build_eval_suite_summary(
    report: DiagnosticReport,
    snapshot: AgentStateSnapshot | None = None,
) -> dict[str, Any]:
    test_summary = build_test_result_summary(report)
    test_ids = [item["test_id"] for item in test_summary["tests"]]
    tags = sorted({tag for item in test_summary["tests"] for tag in item.get("tags", [])})
    scorers = sorted(_scorers_from_report(report))
    eval_files: list[str] = []
    eval_hash = None
    if snapshot is not None:
        eval_files = [
            item["path"]
            for item in snapshot.eval_state.get("eval_files", [])
            if isinstance(item, dict) and item.get("path")
        ]
        eval_hash = snapshot.eval_state.get("scorer_config_hash")
    if eval_hash is None:
        eval_hash = _stable_hash(
            {
                "test_ids": test_ids,
                "tags": tags,
                "scorers": scorers,
                "eval_files": eval_files,
            }
        )
    return {
        "eval_files": eval_files,
        "eval_case_count": len(test_ids),
        "test_tags": tags,
        "test_ids": test_ids,
        "scorers": scorers,
        "eval_hash": eval_hash,
    }


def determine_baseline_quality(
    *,
    mode: str,
    diagnostic_summary: dict[str, Any],
    failure_taxonomy_summary: dict[str, Any],
    eval_suite_summary: dict[str, Any],
    review_summary: dict[str, Any],
    patch_summary: dict[str, Any],
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    failure_counts = _mapping(failure_taxonomy_summary.get("failure_type_counts"))
    critical_types = set(failure_taxonomy_summary.get("critical_failure_types") or [])
    fail_count = _to_int(diagnostic_summary.get("fail_count")) or 0
    warning_count = _to_int(diagnostic_summary.get("warning_count")) or 0
    eval_case_count = _to_int(eval_suite_summary.get("eval_case_count")) or 0
    uncertain_total = sum(int(failure_counts.get(item, 0) or 0) for item in SCORER_UNCERTAIN_TYPES)
    failure_total = sum(int(value or 0) for value in failure_counts.values())

    if mode == "quick":
        warnings.append("This baseline was created from quick mode and is incomplete.")
    if not failure_taxonomy_summary.get("available"):
        warnings.append("Failure taxonomy data is unavailable.")
    if eval_case_count <= 0:
        warnings.append("Eval coverage is missing or weak.")
    if critical_types:
        warnings.append(f"Critical failure types exist: {', '.join(sorted(critical_types))}.")
    if fail_count:
        warnings.append("Baseline contains failed tests.")
    if warning_count:
        warnings.append("Baseline contains warning-level diagnostic results.")
    if patch_summary.get("patches_applied", 0) and review_summary.get("review_required"):
        warnings.append("Auto patches were applied but still require review.")
    if failure_total and uncertain_total / max(1, failure_total) >= 0.5:
        warnings.append("Baseline findings are dominated by SCORER_UNCERTAIN or UNKNOWN.")

    if (
        mode == "deep"
        and not critical_types
        and fail_count == 0
        and warning_count == 0
        and eval_case_count > 0
        and failure_taxonomy_summary.get("available")
        and uncertain_total / max(1, failure_total or 1) < 0.5
        and not review_summary.get("review_required")
    ):
        return "high", warnings

    low = (
        mode == "quick" and fail_count > 0
        or bool(critical_types)
        or eval_case_count <= 0
        or failure_total and uncertain_total / max(1, failure_total) >= 0.5
        or (mode == "auto" and patch_summary.get("patches_applied", 0) and review_summary.get("review_required"))
    )
    if low:
        warnings.append("This baseline has low quality and should not be used as a strong regression reference.")
        return "low", list(dict.fromkeys(warnings))
    return "medium", list(dict.fromkeys(warnings))


def compare_test_results(
    baseline_summary: dict[str, Any],
    current_summary: dict[str, Any],
) -> list[TestResultChange]:
    baseline = {str(item.get("test_id")): item for item in baseline_summary.get("tests", []) if isinstance(item, dict)}
    current = {str(item.get("test_id")): item for item in current_summary.get("tests", []) if isinstance(item, dict)}
    changes: list[TestResultChange] = []
    for test_id in sorted(set(baseline) | set(current), key=str.casefold):
        old = baseline.get(test_id)
        new = current.get(test_id)
        old_status = old.get("status") if old else None
        new_status = new.get("status") if new else None
        old_score = _to_float(old.get("score")) if old else None
        new_score = _to_float(new.get("score")) if new else None
        score_delta = _round_delta(new_score, old_score)
        change_status = _test_change_status(old_status, new_status, old_score, new_score)
        changes.append(
            TestResultChange(
                test_id=test_id,
                baseline_status=old_status,
                current_status=new_status,
                baseline_score=old_score,
                current_score=new_score,
                score_delta=score_delta,
                baseline_failure_types=sorted(old.get("failure_types", []) if old else []),
                current_failure_types=sorted(new.get("failure_types", []) if new else []),
                change_status=change_status,
            )
        )
    return changes


def compare_failure_types(
    baseline_taxonomy: dict[str, Any],
    current_taxonomy: dict[str, Any],
) -> list[FailureTypeChange]:
    baseline_counts = _mapping(baseline_taxonomy.get("failure_type_counts"))
    current_counts = _mapping(current_taxonomy.get("failure_type_counts"))
    baseline_severity = _mapping(baseline_taxonomy.get("max_severity_by_failure_type"))
    current_severity = _mapping(current_taxonomy.get("max_severity_by_failure_type"))
    changes: list[FailureTypeChange] = []
    for failure_type in sorted(set(baseline_counts) | set(current_counts), key=str.casefold):
        old = _to_int(baseline_counts.get(failure_type)) or 0
        new = _to_int(current_counts.get(failure_type)) or 0
        delta = new - old
        if old == 0 and new > 0:
            status = "new"
        elif old > 0 and new == 0:
            status = "resolved"
        elif new > old:
            status = "worsened"
        elif new < old:
            status = "improved"
        else:
            status = "unchanged"
        changes.append(
            FailureTypeChange(
                failure_type=failure_type,
                baseline_count=old,
                current_count=new,
                delta=delta,
                change_status=status,
                max_baseline_severity=baseline_severity.get(failure_type),
                max_current_severity=current_severity.get(failure_type),
            )
        )
    return changes


def compare_severity_counts(
    baseline_counts: Any,
    current_counts: Any,
) -> dict[str, dict[str, int]]:
    baseline = _mapping(baseline_counts)
    current = _mapping(current_counts)
    result: dict[str, dict[str, int]] = {}
    for severity in ("info", "warning", "error", "critical"):
        old = _to_int(baseline.get(severity)) or 0
        new = _to_int(current.get(severity)) or 0
        result[severity] = {
            "baseline_count": old,
            "current_count": new,
            "delta": new - old,
        }
    return result


def compare_confidence_fields(
    baseline_confidence: dict[str, Any],
    current_confidence: dict[str, Any],
) -> dict[str, float]:
    deltas: dict[str, float] = {}
    for key in sorted(set(baseline_confidence) & set(current_confidence), key=str.casefold):
        old = _to_float(baseline_confidence.get(key))
        new = _to_float(current_confidence.get(key))
        delta = _round_delta(new, old)
        if delta is not None:
            deltas[key] = delta
    return deltas


def compare_time_costs(
    baseline_time: dict[str, Any],
    current_time: dict[str, Any],
) -> dict[str, Any]:
    old = _to_float(baseline_time.get("total_elapsed_seconds"))
    new = _to_float(current_time.get("total_elapsed_seconds"))
    if old is None or new is None:
        return {
            "available": False,
            "baseline_total_elapsed_seconds": old,
            "current_total_elapsed_seconds": new,
            "total_elapsed_delta_seconds": None,
            "total_elapsed_delta_percent": None,
            "slowest_failure_type_changes": [],
            "efficiency_warning": "Time cost data is unavailable or partial.",
        }
    delta = round(new - old, 3)
    percent = round((delta / old) * 100, 2) if old else None
    warning = None
    if percent is not None and percent >= 50:
        warning = "Runtime increased significantly."
    return {
        "available": True,
        "baseline_total_elapsed_seconds": old,
        "current_total_elapsed_seconds": new,
        "total_elapsed_delta_seconds": delta,
        "total_elapsed_delta_percent": percent,
        "slowest_failure_type_changes": _slow_failure_type_changes(baseline_time, current_time),
        "efficiency_warning": warning,
    }


def compare_agent_state(
    baseline_snapshot: dict[str, Any] | None,
    current_snapshot: AgentStateSnapshot,
) -> AgentStateDiff:
    if baseline_snapshot is None:
        return AgentStateDiff(
            changed_prompt_files=[],
            changed_tool_configs=[],
            changed_workflow_configs=[],
            changed_eval_configs=[],
            file_hash_changes=[],
            model_changed=False,
            tool_list_changed=False,
            tool_list_diff={"added_tools": [], "removed_tools": [], "changed_tools": []},
            approval_policy_changed=False,
            git_commit_changed=False,
            dirty_state_changed=False,
            missing_snapshot=True,
            warnings=["Baseline snapshot is unavailable; agent state comparison is partial."],
        )
    baseline_hashes = _mapping(baseline_snapshot.get("file_hashes"))
    current_hashes = current_snapshot.file_hashes
    file_changes: list[dict[str, Any]] = []
    for path in sorted(set(baseline_hashes) | set(current_hashes), key=str.casefold):
        old = baseline_hashes.get(path)
        new = current_hashes.get(path)
        if old == new:
            continue
        file_changes.append(
            {
                "path": path,
                "baseline_hash": old,
                "current_hash": new,
                "changed": True,
            }
        )
    baseline_model = _mapping(baseline_snapshot.get("model_state"))
    baseline_tools = _tool_names(_mapping(baseline_snapshot.get("tool_state")).get("tools", []))
    current_tools = _tool_names(current_snapshot.tool_state.get("tools", []))
    added_tools = sorted(current_tools - baseline_tools)
    removed_tools = sorted(baseline_tools - current_tools)
    changed_tools = _changed_tool_descriptions(baseline_snapshot, current_snapshot)
    baseline_workflow = _mapping(baseline_snapshot.get("workflow_state"))
    baseline_repo = _mapping(baseline_snapshot.get("repo_state"))
    current_repo = current_snapshot.repo_state
    diff = AgentStateDiff(
        changed_prompt_files=[item for item in file_changes if _path_category(item["path"]) == "prompt"],
        changed_tool_configs=[item for item in file_changes if _path_category(item["path"]) == "tool"],
        changed_workflow_configs=[item for item in file_changes if _path_category(item["path"]) == "workflow"],
        changed_eval_configs=[item for item in file_changes if _path_category(item["path"]) == "eval"],
        file_hash_changes=file_changes,
        model_changed=_stable_hash(baseline_model) != _stable_hash(current_snapshot.model_state),
        tool_list_changed=bool(added_tools or removed_tools or changed_tools),
        tool_list_diff={
            "added_tools": added_tools,
            "removed_tools": removed_tools,
            "changed_tools": changed_tools,
        },
        approval_policy_changed=_approval_policy_hash(baseline_workflow) != _approval_policy_hash(current_snapshot.workflow_state),
        git_commit_changed=baseline_repo.get("commit_hash") != current_repo.get("commit_hash"),
        dirty_state_changed=baseline_repo.get("dirty") != current_repo.get("dirty"),
    )
    return diff


def compare_eval_suite(
    baseline_eval: dict[str, Any],
    current_eval: dict[str, Any],
    baseline_snapshot: dict[str, Any] | None,
    current_snapshot: AgentStateSnapshot,
) -> EvalSuiteDiff:
    baseline_tests = set(str(item) for item in baseline_eval.get("test_ids", []) or [])
    current_tests = set(str(item) for item in current_eval.get("test_ids", []) or [])
    added_tests = sorted(current_tests - baseline_tests)
    removed_tests = sorted(baseline_tests - current_tests)
    changed_files = [
        item["path"]
        for item in compare_agent_state(baseline_snapshot, current_snapshot).changed_eval_configs
    ] if baseline_snapshot is not None else []
    scorer_changed = baseline_eval.get("scorers") != current_eval.get("scorers")
    hash_changed = baseline_eval.get("eval_hash") != current_eval.get("eval_hash")
    changed = bool(added_tests or removed_tests or changed_files or scorer_changed or hash_changed)
    warning = "Eval suite changed since baseline. Comparison may be partial." if changed else None
    return EvalSuiteDiff(
        eval_suite_changed=changed,
        added_tests=added_tests,
        removed_tests=removed_tests,
        changed_eval_files=changed_files,
        scorer_changed=scorer_changed,
        warning=warning,
    )


def determine_comparability(
    *,
    baseline: dict[str, Any],
    current_report: DiagnosticReport,
    current_agent_identity: dict[str, Any] | None = None,
    test_changes: list[TestResultChange],
    eval_suite_diff: EvalSuiteDiff,
    agent_state_diff: AgentStateDiff,
    load_warnings: list[str] | None = None,
) -> tuple[str, list[str]]:
    warnings = list(load_warnings or [])
    baseline_agent = _mapping(baseline.get("agent_identity"))
    current_agent = current_agent_identity or _agent_identity_from_report(current_report)
    baseline_name = baseline_agent.get("agent_name")
    current_name = current_agent.get("agent_name")
    if baseline_name and current_name and baseline_name not in {"unknown", None} and current_name not in {"unknown", None} and baseline_name != current_name:
        warnings.append("Baseline agent name differs from current agent.")
        return "not_comparable", list(dict.fromkeys(warnings))
    overlapping = [
        change for change in test_changes
        if change.baseline_status is not None and change.current_status is not None
    ]
    if not overlapping:
        warnings.append("No overlapping tests were found between baseline and current run.")
        return "not_comparable", list(dict.fromkeys(warnings))
    baseline_mode = str(baseline.get("mode") or "")
    current_mode = current_report.mode
    baseline_quality = str(baseline.get("baseline_quality") or "unknown")
    baseline_taxonomy = _mapping(baseline.get("failure_taxonomy_summary"))
    if baseline_mode == "quick" and current_mode != "quick":
        warnings.append("Baseline was created from quick mode; current run uses a broader mode.")
        return "weak", list(dict.fromkeys(warnings))
    if baseline_quality == "low":
        warnings.append("Baseline quality is low, so comparison evidence is weak.")
        return "weak", list(dict.fromkeys(warnings))
    if not baseline_taxonomy.get("available"):
        warnings.append("Failure taxonomy data is missing from baseline.")
        return "weak", list(dict.fromkeys(warnings))
    if agent_state_diff.missing_snapshot:
        warnings.append("Baseline snapshot is missing.")
        return "partial", list(dict.fromkeys(warnings))
    if eval_suite_diff.eval_suite_changed:
        warnings.append(eval_suite_diff.warning or "Eval suite changed since baseline.")
        return "partial", list(dict.fromkeys(warnings))
    if baseline_mode and baseline_mode != current_mode:
        warnings.append("Baseline mode differs from current mode.")
        return "partial", list(dict.fromkeys(warnings))
    return "full", list(dict.fromkeys(warnings))


def build_likely_cause_candidates(
    agent_state_diff: AgentStateDiff,
    eval_suite_diff: EvalSuiteDiff,
    failure_changes: list[FailureTypeChange],
    test_changes: list[TestResultChange],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    regressed_types = [
        item.failure_type for item in failure_changes
        if item.change_status in {"new", "worsened"}
    ]
    regressed_tests = [
        item.test_id for item in test_changes
        if item.change_status in {"regressed", "changed_score"} and (item.score_delta or 0) < 0
    ]
    if agent_state_diff.changed_prompt_files and regressed_types:
        candidates.append(
            {
                "reason": f"{agent_state_diff.changed_prompt_files[0]['path']} changed since baseline",
                "related_regressions": regressed_types[:5] or regressed_tests[:5],
                "confidence": "medium",
            }
        )
    if agent_state_diff.changed_tool_configs and any("TOOL" in item for item in regressed_types):
        candidates.append(
            {
                "reason": "Tool configuration changed since baseline",
                "related_regressions": [item for item in regressed_types if "TOOL" in item],
                "confidence": "medium",
            }
        )
    if agent_state_diff.changed_workflow_configs and any(item in CRITICAL_FAILURE_TYPES for item in regressed_types):
        candidates.append(
            {
                "reason": "Workflow or approval configuration changed since baseline",
                "related_regressions": [item for item in regressed_types if item in CRITICAL_FAILURE_TYPES],
                "confidence": "medium",
            }
        )
    if eval_suite_diff.eval_suite_changed:
        candidates.append(
            {
                "reason": "Eval suite changed since baseline",
                "related_regressions": regressed_tests[:5],
                "confidence": "low",
            }
        )
    return candidates


def build_regression_summary(
    test_changes: list[TestResultChange],
    failure_changes: list[FailureTypeChange],
    severity_changes: dict[str, dict[str, int]],
    overall_delta: dict[str, Any],
    time_delta: dict[str, Any],
) -> dict[str, Any]:
    return {
        "regressed_tests": [item.test_id for item in test_changes if item.change_status == "regressed"],
        "new_failure_types": [item.failure_type for item in failure_changes if item.change_status == "new"],
        "worsened_failure_types": [item.failure_type for item in failure_changes if item.change_status == "worsened"],
        "new_critical_failures": severity_changes.get("critical", {}).get("delta", 0) > 0,
        "confidence_regressed": (overall_delta.get("confidence_delta") or 0) < 0,
        "time_cost_regressed": bool(time_delta.get("efficiency_warning") and time_delta.get("available")),
    }


def build_improvement_summary(
    test_changes: list[TestResultChange],
    failure_changes: list[FailureTypeChange],
    confidence_delta: dict[str, float],
) -> dict[str, Any]:
    return {
        "improved_tests": [item.test_id for item in test_changes if item.change_status == "improved"],
        "resolved_failure_types": [item.failure_type for item in failure_changes if item.change_status == "resolved"],
        "improved_failure_types": [item.failure_type for item in failure_changes if item.change_status == "improved"],
        "confidence_improved": any(value > 0 for value in confidence_delta.values()),
    }


def build_rollback_recommendation(
    *,
    comparison_comparable: str,
    baseline_quality: str,
    failure_type_changes: list[FailureTypeChange],
    severity_changes: dict[str, dict[str, int]],
    confidence_delta: float | None,
    agent_state_diff: AgentStateDiff,
    baseline_patch_summary: dict[str, Any] | None = None,
    current_patch_summary: dict[str, Any] | None = None,
) -> RollbackRecommendation:
    new_or_worse = [
        item for item in failure_type_changes
        if item.change_status in {"new", "worsened"}
    ]
    if _scorer_uncertain_dominates(new_or_worse):
        return RollbackRecommendation(
            rollback_recommended=False,
            reason="SCORER_UNCERTAIN or UNKNOWN dominates the change; review evals/scorers before rollback.",
            candidate_files=[],
            candidate_patch_ids=[],
            requires_human_review=True,
        )
    if comparison_comparable == "weak" or baseline_quality == "low":
        return RollbackRecommendation(
            rollback_recommended=False,
            reason="Evidence is weak because the baseline quality or comparability is low; human review is recommended.",
            candidate_files=_candidate_changed_files(agent_state_diff),
            candidate_patch_ids=[],
            requires_human_review=True,
        )
    critical_new = [
        item.failure_type for item in new_or_worse
        if item.failure_type in CRITICAL_FAILURE_TYPES
        or item.max_current_severity == "critical"
    ]
    if critical_new or (severity_changes.get("critical", {}).get("delta", 0) > 0):
        return RollbackRecommendation(
            rollback_recommended=True,
            reason=f"New critical failure evidence appeared: {', '.join(critical_new) or 'critical severity increase'}.",
            candidate_files=_candidate_changed_files(agent_state_diff),
            candidate_patch_ids=_candidate_patch_ids(current_patch_summary),
            requires_human_review=True,
        )
    if confidence_delta is not None and confidence_delta <= -0.05:
        return RollbackRecommendation(
            rollback_recommended=True,
            reason=f"Overall confidence dropped by {confidence_delta:.2f} since baseline.",
            candidate_files=_candidate_changed_files(agent_state_diff),
            candidate_patch_ids=_candidate_patch_ids(current_patch_summary),
            requires_human_review=True,
        )
    if detect_overfitting_from_failure_type_changes(failure_type_changes):
        return RollbackRecommendation(
            rollback_recommended=True,
            reason="A targeted failure type improved while multiple non-target failure types worsened.",
            candidate_files=_candidate_changed_files(agent_state_diff),
            candidate_patch_ids=_candidate_patch_ids(current_patch_summary),
            requires_human_review=True,
        )
    return RollbackRecommendation(
        rollback_recommended=False,
        reason="No rollback trigger was detected from baseline comparison.",
        candidate_files=[],
        candidate_patch_ids=[],
        requires_human_review=bool(new_or_worse),
    )


def detect_overfitting_from_failure_type_changes(
    failure_type_changes: list[FailureTypeChange],
) -> bool:
    improved = [item for item in failure_type_changes if item.change_status in {"resolved", "improved"}]
    worsened = [item for item in failure_type_changes if item.change_status in {"new", "worsened"}]
    return bool(improved and len([item for item in worsened if item.failure_type not in SCORER_UNCERTAIN_TYPES]) >= 2)


def build_patch_preview_baseline_context(
    comparison: BaselineComparison,
    *,
    target_failure_type: str,
) -> dict[str, Any]:
    by_type = {item.failure_type: item for item in comparison.failure_type_changes}
    target = by_type.get(target_failure_type)
    changed_files = _candidate_changed_files(comparison.agent_state_diff)
    worsened = [
        item.failure_type
        for item in comparison.failure_type_changes
        if item.change_status in {"new", "worsened"} and item.failure_type != target_failure_type
    ]
    risks = []
    if comparison.eval_suite_diff.eval_suite_changed:
        risks.append("Eval suite changed since baseline; validate with overlapping and new tests.")
    if changed_files:
        risks.append("Prompt/config/tool/eval files changed since baseline.")
    if worsened:
        risks.append(f"Non-target failure types worsened: {', '.join(worsened)}.")
    return {
        "target_failure_type": target_failure_type,
        "baseline_failure_type_count": target.baseline_count if target else 0,
        "current_failure_type_count": target.current_count if target else 0,
        "changed_files_since_baseline": changed_files,
        "regression_risks": risks,
        "recommended_validation_tags": _validation_tags_for_failure_types([target_failure_type, *worsened]),
    }


def detect_baseline_status(project_root: str | Path) -> Any:
    from contract2agent.triage.models import BaselineStatus

    root = Path(project_root).expanduser().resolve()
    loaded = load_baseline(root, "latest")
    if loaded.baseline is None:
        return BaselineStatus(exists=False, warning="No baseline found.")
    baseline = loaded.baseline
    diagnostic = _mapping(baseline.get("diagnostic_summary"))
    identity = _mapping(baseline.get("agent_identity"))
    try:
        return BaselineStatus(
            exists=True,
            path=_relative(root, loaded.baseline_path) if loaded.baseline_path else None,
            created_at=baseline.get("created_at"),
            mode=baseline.get("mode"),
            confidence=_to_float(diagnostic.get("diagnostic_confidence") or baseline.get("confidence")),
            agent_name=identity.get("agent_name") or baseline.get("agent_name"),
            baseline_id=baseline.get("baseline_id"),
            baseline_quality=baseline.get("baseline_quality"),
            warning="; ".join(loaded.warnings) if loaded.warnings else None,
        )
    except TypeError:
        return BaselineStatus(
            exists=True,
            path=_relative(root, loaded.baseline_path) if loaded.baseline_path else None,
            created_at=baseline.get("created_at"),
            mode=baseline.get("mode"),
            confidence=_to_float(diagnostic.get("diagnostic_confidence") or baseline.get("confidence")),
            agent_name=identity.get("agent_name") or baseline.get("agent_name"),
            warning="; ".join(loaded.warnings) if loaded.warnings else None,
        )


def load_baseline(project_root: str | Path, baseline_ref: str | None = "latest") -> BaselineLoadResult:
    root = Path(project_root).expanduser().resolve()
    ref = baseline_ref or "latest"
    baselines_dir = root / ".agentdoctor" / "baselines"
    if ref == "latest":
        latest_path = baselines_dir / "latest.json"
        if not latest_path.exists():
            return BaselineLoadResult(None, None, ["No latest baseline exists."])
        payload, warning = _read_json_file(latest_path)
        if payload is None:
            return BaselineLoadResult(None, latest_path, [warning or "Latest baseline JSON is unreadable."])
        if "path" in payload and "latest_baseline_id" in payload:
            target = _resolve_under_root(root, str(payload["path"]))
            record, record_warning = _read_json_file(target)
            if record is None:
                return BaselineLoadResult(
                    None,
                    target,
                    [record_warning or "Latest baseline pointer target is unreadable."],
                )
            return BaselineLoadResult(record, target)
        return BaselineLoadResult(payload, latest_path)

    direct_dir = baselines_dir / ref / "baseline.json"
    if direct_dir.exists():
        payload, warning = _read_json_file(direct_dir)
        return BaselineLoadResult(payload, direct_dir, [warning] if warning else [])
    direct_file = baselines_dir / f"{ref}.json"
    if direct_file.exists():
        payload, warning = _read_json_file(direct_file)
        return BaselineLoadResult(payload, direct_file, [warning] if warning else [])

    for candidate in sorted(baselines_dir.glob("baseline_*/baseline.json")):
        payload, warning = _read_json_file(candidate)
        if payload is None:
            continue
        if payload.get("baseline_name") == ref or payload.get("baseline_id") == ref:
            return BaselineLoadResult(payload, candidate, [warning] if warning else [])
    return BaselineLoadResult(None, None, [f"Baseline {ref!r} was not found."])


def discover_snapshot_files(
    project_root: Path,
    *,
    agent_config_path: str | Path | None = None,
) -> dict[str, Any]:
    safe: set[str] = set()
    warnings: list[str] = []
    for pattern in SNAPSHOT_ALLOWLIST_PATTERNS + EVAL_DISCOVERY_PATTERNS:
        for path in sorted(project_root.glob(pattern), key=lambda item: item.as_posix().casefold()):
            if not path.is_file():
                continue
            rel = _relative(project_root, path)
            if is_excluded_path(path, project_root):
                continue
            safe.add(rel)
    if agent_config_path is not None:
        path = _resolve_under_root(project_root, agent_config_path)
        if path.exists() and path.is_file() and not is_excluded_path(path, project_root):
            safe.add(_relative(project_root, path))
        else:
            warnings.append(f"Agent config path is unavailable or excluded: {agent_config_path}")
    return {"safe": sorted(safe, key=str.casefold), "warnings": warnings}


def is_excluded_path(path: str | Path, project_root: str | Path) -> bool:
    root = Path(project_root).expanduser().resolve()
    target = Path(path).expanduser()
    try:
        relative = target.resolve().relative_to(root)
    except (ValueError, OSError):
        relative = target
    parts = [part.casefold() for part in relative.parts]
    if any(part in EXCLUDED_DIRS for part in parts[:-1]):
        return True
    name = relative.name
    return any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDED_FILE_PATTERNS)


def detect_excluded_files(project_root: str | Path) -> list[str]:
    root = Path(project_root).expanduser().resolve()
    detected: list[str] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda item: item.name.casefold())
        except OSError:
            continue
        for entry in entries:
            rel = _relative(root, entry)
            if entry.is_dir():
                if entry.name.casefold() in EXCLUDED_DIRS:
                    detected.append(rel + "/")
                    continue
                if rel.startswith(".agentdoctor/baselines/"):
                    continue
                stack.append(entry)
                continue
            if is_excluded_path(entry, root):
                detected.append(rel)
    return sorted(set(detected), key=str.casefold)[:200]


def sha256_file(path: str | Path) -> str | None:
    target = Path(path)
    try:
        digest = hashlib.sha256()
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return f"sha256:{digest.hexdigest()}"
    except OSError:
        return None


def copy_snapshot_file(root: Path, source: Path, copied_root: Path) -> tuple[Path | None, str | None]:
    rel = _relative(root, source)
    if is_excluded_path(source, root):
        return None, f"Excluded unsafe file from snapshot: {rel}"
    try:
        size = source.stat().st_size
    except OSError as exc:
        return None, f"Could not stat snapshot file {rel}: {exc}"
    if size > MAX_SNAPSHOT_COPY_BYTES:
        return None, f"Skipped large snapshot file over 1 MB: {rel}"
    try:
        source.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return None, f"Skipped non-text or unreadable snapshot file {rel}: {exc}"
    target = copied_root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target, None


def capture_repo_state(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()

    def run_git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root), *args],
            text=True,
            capture_output=True,
            timeout=5,
        )

    try:
        inside = run_git("rev-parse", "--is-inside-work-tree")
    except (OSError, subprocess.SubprocessError):
        return {"git_available": False}
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return {"git_available": False}
    top_level = run_git("rev-parse", "--show-toplevel")
    if top_level.returncode != 0:
        return {"git_available": False}
    try:
        if Path(top_level.stdout.strip()).resolve() != root:
            return {"git_available": False}
    except OSError:
        return {"git_available": False}
    commit = run_git("rev-parse", "HEAD")
    branch = run_git("branch", "--show-current")
    porcelain = run_git("status", "--porcelain")
    changed: list[str] = []
    untracked: list[str] = []
    if porcelain.returncode == 0:
        for line in porcelain.stdout.splitlines():
            if not line:
                continue
            status = line[:2]
            path = line[3:].strip()
            if status == "??":
                untracked.append(path)
            else:
                changed.append(path)
    return {
        "git_available": True,
        "commit_hash": commit.stdout.strip() if commit.returncode == 0 else None,
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "dirty": bool(changed or untracked),
        "changed_files": sorted(changed, key=str.casefold),
        "untracked_files": sorted(untracked, key=str.casefold),
    }


def format_baseline_saved_summary(result: BaselineSaveResult) -> str:
    baseline = result.baseline
    snapshot = result.snapshot
    lines = [
        "Baseline Saved",
        "",
        f"Baseline ID: {baseline.baseline_id}",
        f"Name: {baseline.baseline_name or '-'}",
        f"Mode: {baseline.mode}",
        f"Quality: {baseline.baseline_quality}",
        f"Confidence: {_format_optional_float(baseline.diagnostic_summary.get('diagnostic_confidence'))}",
        f"Tests: {baseline.diagnostic_summary.get('tests_executed')}",
        f"Failures: {baseline.diagnostic_summary.get('fail_count')}",
        f"Snapshot: {baseline.agent_state_snapshot_ref.get('snapshot_path')}",
        "",
        "Files snapshotted:",
    ]
    copied = snapshot.copied_config_files.get("copied_files", [])
    if copied:
        lines.extend(f"- {item['source']}" for item in copied)
    else:
        lines.append("- none")
    if baseline.baseline_quality_warnings:
        lines.extend(["", "Warning:"])
        lines.extend(baseline.baseline_quality_warnings)
    next_ref = baseline.baseline_name or baseline.baseline_id
    lines.extend(["", "Next:", f"Use --compare-baseline {next_ref} in future runs."])
    return "\n".join(lines)


def format_comparison_summary(comparison: BaselineComparison) -> str:
    lines = [
        "Baseline Comparison",
        "",
        f"Baseline: {comparison.baseline_id}",
        f"Comparable: {comparison.comparable}",
        "",
        "Overall:",
        (
            "- Confidence: "
            f"{_format_optional_float(comparison.overall_delta.get('baseline_confidence'))} -> "
            f"{_format_optional_float(comparison.overall_delta.get('current_confidence'))} "
            f"({_format_signed(comparison.overall_delta.get('confidence_delta'))})"
        ),
        f"- Pass count: {comparison.overall_delta.get('baseline_pass_count')} -> {comparison.overall_delta.get('current_pass_count')}",
        f"- Fail count: {comparison.overall_delta.get('baseline_fail_count')} -> {comparison.overall_delta.get('current_fail_count')}",
        "",
        "Regressions:",
    ]
    regressions = [item for item in comparison.test_result_changes if item.change_status == "regressed"]
    lines.extend(
        f"- {item.test_id}: {item.baseline_status} -> {item.current_status}"
        for item in regressions[:10]
    )
    if not regressions:
        lines.append("- none")
    lines.extend(["", "Failure Type Changes:"])
    changed_failures = [item for item in comparison.failure_type_changes if item.change_status != "unchanged"]
    lines.extend(
        f"- {item.failure_type}: {item.baseline_count} -> {item.current_count}"
        for item in changed_failures[:10]
    )
    if not changed_failures:
        lines.append("- none")
    lines.extend(["", "Agent State Changes:"])
    changed_paths = [item["path"] for item in comparison.agent_state_diff.file_hash_changes]
    lines.extend(f"- {path} changed" for path in changed_paths[:10])
    if not changed_paths:
        lines.append("- none")
    lines.extend(["", "Recommendation:", comparison.rollback_recommendation.reason])
    return "\n".join(lines)


def format_baseline_saved_markdown(baseline: BaselineRecord, snapshot: AgentStateSnapshot) -> str:
    data = to_plain_data(baseline)
    snapshot_data = to_plain_data(snapshot)
    return "\n".join(
        [
            "# Baseline Saved",
            "",
            "## Baseline Summary",
            "",
            _json_block(
                {
                    "baseline_id": baseline.baseline_id,
                    "baseline_name": baseline.baseline_name,
                    "created_at": baseline.created_at,
                    "mode": baseline.mode,
                    "baseline_quality": baseline.baseline_quality,
                    "baseline_quality_warnings": baseline.baseline_quality_warnings,
                }
            ),
            "",
            "## Diagnostic Summary",
            "",
            _json_block(data["diagnostic_summary"]),
            "",
            "## Failure Taxonomy Summary",
            "",
            _json_block(data["failure_taxonomy_summary"]),
            "",
            "## Agent State Snapshot",
            "",
            _json_block(
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "model_state": snapshot_data["model_state"],
                    "repo_state": snapshot_data["repo_state"],
                    "environment_state": snapshot_data["environment_state"],
                }
            ),
            "",
            "## Files Snapshotted",
            "",
            _json_block(snapshot_data["copied_config_files"]),
            "",
            "## Warnings",
            "",
            _json_block({"warnings": baseline.baseline_quality_warnings + snapshot.warnings}),
            "",
            "## Next Steps",
            "",
            f"Use `agentdoctor deep --rounds 3 --compare-baseline {baseline.baseline_name or baseline.baseline_id}` in future runs.",
            "",
        ]
    )


def format_comparison_markdown(comparison: BaselineComparison) -> str:
    data = to_plain_data(comparison)
    return "\n".join(
        [
            "# Baseline Comparison",
            "",
            "## 1. Baseline and Current Run",
            "",
            _json_block(
                {
                    "baseline_id": comparison.baseline_id,
                    "current_run_id": comparison.current_run_id,
                    "compared_at": comparison.compared_at,
                }
            ),
            "",
            "## 2. Comparability",
            "",
            _json_block({"comparable": comparison.comparable, "warnings": comparison.comparability_warnings}),
            "",
            "## 3. Overall Delta",
            "",
            _json_block(data["overall_delta"]),
            "",
            "## 4. Test Result Changes",
            "",
            _json_block(data["test_result_changes"]),
            "",
            "## 5. Failure Type Changes",
            "",
            _json_block(data["failure_type_changes"]),
            "",
            "## 6. Severity Changes",
            "",
            _json_block(data["severity_changes"]),
            "",
            "## 7. Agent State Changes",
            "",
            _json_block(data["agent_state_diff"]),
            "",
            "## 8. Eval Suite Changes",
            "",
            _json_block(data["eval_suite_diff"]),
            "",
            "## 9. Time Cost Changes",
            "",
            _json_block(data["time_cost_delta"]),
            "",
            "## 10. Possible Causes",
            "",
            _json_block(data["likely_cause_candidates"]),
            "",
            "## 11. Regression Summary",
            "",
            _json_block(data["regression_summary"]),
            "",
            "## 12. Improvement Summary",
            "",
            _json_block(data["improvement_summary"]),
            "",
            "## 13. Rollback Recommendation",
            "",
            _json_block(data["rollback_recommendation"]),
            "",
            "## 14. Recommended Next Step",
            "",
            f"`{comparison.recommended_next_command}`",
            "",
        ]
    )


def to_plain_data(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if is_dataclass(value):
        return {key: to_plain_data(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    return value


def infer_failure_types(
    test_case: TestCase | None,
    result: TestResult,
    round_report: DiagnosticRound | None = None,
) -> list[str]:
    if result.passed and result.warning_count == 0:
        return []
    text = " ".join(
        [
            result.check_rule or "",
            result.check_message or "",
            " ".join(score.kind for score in result.rule_scores if not score.passed),
            test_case.name if test_case else "",
            " ".join(test_case.tags if test_case else []),
        ]
    )
    tokens = set(_extract_failure_type_tokens(text))
    failed_kinds = {score.kind for score in result.rule_scores if not score.passed}
    tags = set(test_case.tags if test_case else [])
    if "tool_called" in failed_kinds:
        tokens.add("TOOL_MISSING")
    if "tool_not_called" in failed_kinds:
        tokens.add("FORBIDDEN_TOOL_CALL")
    if "tool_sequence" in failed_kinds:
        tokens.add("TOOL_ORDER_ERROR")
    if "json_schema" in failed_kinds:
        tokens.add("OUTPUT_SCHEMA_ERROR")
    if failed_kinds & {"contains", "regex", "not_contains"}:
        tokens.add("OUTPUT_FORMAT_ERROR" if "output_format" in tags else "TASK_INCOMPLETE")
    if "max_steps" in failed_kinds:
        tokens.add("LOOP_RISK")
    if "error_handling" in tags and not result.passed:
        tokens.add("ERROR_HANDLING_MISSING")
    if "safety" in tags and "FORBIDDEN_TOOL_CALL" in tokens:
        tokens.add("SAFETY_RISK")
    if not result.passed and not tokens:
        tokens.add("UNKNOWN")
    return sorted(tokens)


def _latest_test_contexts(report: DiagnosticReport) -> dict[str, tuple[DiagnosticRound, TestCase | None, TestResult]]:
    latest: dict[str, tuple[DiagnosticRound, TestCase | None, TestResult]] = {}
    for round_report in report.rounds:
        cases_by_id = {case.id: case for case in round_report.test_cases}
        for result in round_report.test_results:
            latest[result.test_case_id] = (
                round_report,
                cases_by_id.get(result.test_case_id),
                result,
            )
    return latest


def _load_project_metadata(root: Path, safe_files: list[str]) -> dict[str, Any]:
    loaded: dict[str, Any] = {"files": {}, "warnings": []}
    for rel in safe_files:
        path = root / rel
        text: str | None = None
        try:
            if path.stat().st_size <= MAX_SNAPSHOT_COPY_BYTES:
                text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = None
        loaded["files"][rel] = {
            "path": path,
            "text": text,
            "data": _parse_structured(path, text) if text is not None else None,
        }
    return loaded


def _agent_identity(
    parsed: dict[str, Any],
    report: DiagnosticReport | None,
    root: Path,
    agent_config_path: str | Path | None,
) -> dict[str, Any]:
    config_rel = _find_agent_config(parsed, root, agent_config_path)
    config_data = _mapping(_mapping(parsed.get("files")).get(config_rel, {}).get("data"))
    nested = _mapping(config_data.get("agent"))
    name = _first_string(config_data.get("name"), nested.get("name"), config_data.get("agent_name"), config_data.get("id"))
    description = _first_string(config_data.get("description"), nested.get("description"))
    goal = _first_string(config_data.get("goal"), nested.get("goal"))
    if not goal and report is not None:
        goal = f"{report.mode} diagnostic reference"
    return {
        "agent_name": name or "unknown",
        "agent_type": _first_string(config_data.get("agent_type"), config_data.get("type"), nested.get("type")) or "unknown",
        "description": description or "unknown",
        "goal": goal or "unknown",
        "agent_config_path": config_rel,
        "config_path": config_rel,
    }


def _agent_identity_from_report(report: DiagnosticReport) -> dict[str, Any]:
    return {
        "agent_name": "unknown",
        "agent_type": "unknown",
        "goal": f"{report.mode} diagnostic reference",
        "agent_config_path": None,
    }


def _model_state(parsed: dict[str, Any]) -> dict[str, Any]:
    config_rel = _find_agent_config(parsed, Path("."), None)
    config = _mapping(_mapping(parsed.get("files")).get(config_rel, {}).get("data"))
    model_spec = _mapping(config.get("model")) or _mapping(config.get("llm"))
    provider_spec = _mapping(config.get("provider"))
    state = {
        "provider": _first_string(config.get("provider"), provider_spec.get("name"), model_spec.get("provider")) or "unknown",
        "model": _first_string(config.get("model"), config.get("model_name"), model_spec.get("name"), model_spec.get("id")) or "unknown",
    }
    for key in ("temperature", "max_tokens", "top_p", "tool_choice"):
        if key in config:
            state[key] = config[key]
        elif key in model_spec:
            state[key] = model_spec[key]
    return state


def _prompt_state(
    root: Path,
    safe_files: list[str],
    file_hashes: dict[str, str],
    copied_files: list[dict[str, str]],
) -> dict[str, Any]:
    copied_by_source = {item["source"]: item["snapshot_path"] for item in copied_files}
    prompts = []
    for rel in safe_files:
        if _path_category(rel) != "prompt":
            continue
        path = root / rel
        prompts.append(
            {
                "path": rel,
                "sha256": file_hashes.get(rel),
                "copied_to": copied_by_source.get(rel),
                "size_bytes": path.stat().st_size if path.exists() else None,
            }
        )
    return {"prompt_files": prompts, "prompt_count": len(prompts)}


def _tool_state(parsed: dict[str, Any], file_hashes: dict[str, str]) -> dict[str, Any]:
    tools = []
    tool_config_files = []
    for rel, item in sorted(_mapping(parsed.get("files")).items()):
        data = item.get("data")
        if _path_category(rel) == "tool":
            tool_config_files.append(rel)
        for spec in _extract_tools(data):
            description = str(spec.get("description") or "")
            tools.append(
                {
                    "name": str(spec.get("name") or "unknown"),
                    "category": str(spec.get("category") or spec.get("type") or "unknown"),
                    "side_effect_level": str(spec.get("side_effect_level") or "unknown"),
                    "risk_level": str(spec.get("risk_level") or "unknown"),
                    "description_hash": _stable_hash(description),
                }
            )
    deduped = {tool["name"]: tool for tool in tools}
    return {
        "tools": [deduped[key] for key in sorted(deduped, key=str.casefold)],
        "tool_count": len(deduped),
        "tool_config_files": sorted(set(tool_config_files), key=str.casefold),
    }


def _workflow_state(parsed: dict[str, Any]) -> dict[str, Any]:
    config = {}
    workflow_files = [
        item.get("data")
        for rel, item in _mapping(parsed.get("files")).items()
        if _path_category(rel) == "workflow" or _path_category(rel) == "agent_config"
    ]
    for item in workflow_files:
        if isinstance(item, dict):
            config.update(item)
    workflow = _mapping(config.get("workflow"))
    limits = _mapping(config.get("limits"))
    review = _mapping(config.get("review"))
    permissions = _mapping(config.get("permissions"))
    return {
        "max_steps": config.get("max_steps") or limits.get("max_steps"),
        "max_tool_calls": config.get("max_tool_calls") or limits.get("max_tool_calls"),
        "review_policy": config.get("review_policy") or review.get("policy") or "unknown",
        "approval_required_for": _list_value(config.get("approval_required_for") or permissions.get("approval_required_for")),
        "forbidden_tools": _list_value(config.get("forbidden_tools") or workflow.get("forbidden_tools")),
        "allowed_patch_targets": _list_value(config.get("allowed_patch_targets") or workflow.get("allowed_patch_targets")),
    }


def _eval_state(
    report: DiagnosticReport | None,
    parsed: dict[str, Any],
    file_hashes: dict[str, str],
) -> dict[str, Any]:
    eval_files = [
        {"path": rel, "sha256": file_hashes.get(rel)}
        for rel in sorted(file_hashes, key=str.casefold)
        if _path_category(rel) == "eval"
    ]
    test_ids: list[str] = []
    scorers: set[str] = set()
    if report is not None:
        test_summary = build_test_result_summary(report)
        test_ids = [item["test_id"] for item in test_summary["tests"]]
        scorers = _scorers_from_report(report)
    for rel, item in _mapping(parsed.get("files")).items():
        if _path_category(rel) != "eval":
            continue
        for case in _extract_eval_cases(item.get("data")):
            test_id = _first_string(case.get("id"), case.get("test_id"), case.get("name"))
            if test_id and test_id not in test_ids:
                test_ids.append(test_id)
            scorers.update(str(scorer) for scorer in _list_value(case.get("scorers") or case.get("assertions")))
    return {
        "eval_files": eval_files,
        "eval_case_count": len(test_ids),
        "test_ids": sorted(test_ids, key=str.casefold),
        "scorers": sorted(scorers, key=str.casefold),
        "scorer_config_hash": _stable_hash(
            {
                "eval_files": eval_files,
                "test_ids": sorted(test_ids, key=str.casefold),
                "scorers": sorted(scorers, key=str.casefold),
            }
        ),
    }


def _patch_state(report: DiagnosticReport | None) -> dict[str, Any]:
    if report is None or not report.patch_history:
        return {"has_agentdoctor_patches": False, "patch_history": []}
    return {
        "has_agentdoctor_patches": True,
        "patch_history": [_patch_history_item(index, patch) for index, patch in enumerate(report.patch_history, start=1)],
    }


def _patch_history_item(index: int, patch: PatchHistory) -> dict[str, Any]:
    return {
        "patch_id": f"patch_{index:03d}",
        "created_at": None,
        "target_failure_types": _extract_failure_type_tokens(f"{patch.patch_summary} {patch.reason_for_patch}"),
        "files_changed": list(patch.files_changed),
        "rollback_performed": patch.rollback_performed,
        "regression_detected": patch.regression_detected,
    }


def _load_baseline_snapshot(
    baseline: dict[str, Any],
    baseline_path: Path | None,
    *,
    project_root: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    ref = _mapping(baseline.get("agent_state_snapshot_ref"))
    snapshot_path = ref.get("snapshot_path")
    if snapshot_path:
        target = _resolve_under_root(project_root, str(snapshot_path))
    elif baseline_path is not None:
        target = baseline_path.parent / "snapshot.json"
    else:
        return None, ["Baseline snapshot path is missing."]
    payload, warning = _read_json_file(target)
    if payload is None:
        return None, [warning or "Baseline snapshot is missing or unreadable."]
    return payload, []


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_plain_data(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json_file(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except json.JSONDecodeError as exc:
        return None, f"Corrupt baseline JSON at {path}: {exc.msg}"
    except OSError as exc:
        return None, f"Could not read {path}: {exc}"
    if not isinstance(data, dict):
        return None, f"Baseline JSON is not an object: {path}"
    return data, None


def _parse_structured(path: Path, text: str | None) -> Any:
    if text is None:
        return None
    try:
        if path.suffix.casefold() == ".json":
            return json.loads(text)
        if path.suffix.casefold() in {".yaml", ".yml"} and yaml is not None:
            return yaml.safe_load(text) or {}
    except Exception:
        return None
    return text


def _extract_tools(value: Any) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            specs.extend(_extract_tools(item))
        return specs
    if not isinstance(value, dict):
        return specs
    for key in ("tools", "tool_descriptions", "agent_tools", "available_tools"):
        if key in value:
            specs.extend(_tool_items(value[key]))
    nested = value.get("agent")
    if isinstance(nested, dict):
        for key in ("tools", "tool_descriptions", "available_tools"):
            if key in nested:
                specs.extend(_tool_items(nested[key]))
    if not specs and any(key in value for key in ("name", "description", "category", "type")):
        specs.append(dict(value))
    return specs


def _tool_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) if isinstance(item, dict) else {"name": str(item)} for item in value]
    if isinstance(value, dict):
        items = []
        for key, item in sorted(value.items()):
            if isinstance(item, dict):
                spec = dict(item)
                spec.setdefault("name", key)
                items.append(spec)
            else:
                items.append({"name": key, "description": str(item)})
        return items
    if isinstance(value, str):
        return [{"name": value}]
    return []


def _extract_eval_cases(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item if isinstance(item, dict) else {"name": str(item)} for item in value]
    if not isinstance(value, dict):
        return []
    for key in ("cases", "tests", "evals", "examples"):
        items = value.get(key)
        if isinstance(items, list):
            return [item if isinstance(item, dict) else {"name": str(item)} for item in items]
    if any(key in value for key in ("name", "id", "test_id", "tags", "scorers", "assertions")):
        return [value]
    return []


def _scorers_from_report(report: DiagnosticReport) -> set[str]:
    scorers: set[str] = set()
    for round_report in report.rounds:
        for test_case in round_report.test_cases:
            scorers.update(rule.kind for rule in test_case.scoring_rules)
    return scorers


def _result_severity(
    test_case: TestCase | None,
    result: TestResult,
    round_report: DiagnosticRound | None,
) -> str:
    if result.passed and result.warning_count == 0:
        return "info"
    if any(not score.passed and score.severity == "critical" for score in result.rule_scores):
        return "critical"
    if "SAFETY_RISK" in infer_failure_types(test_case, result, round_report) or "FORBIDDEN_TOOL_CALL" in infer_failure_types(test_case, result, round_report):
        return "critical"
    if not result.passed:
        return "error"
    if result.warning_count:
        return "warning"
    return "info"


def _normalize_severity(value: str | None) -> str:
    normalized = (value or "info").casefold()
    return normalized if normalized in SEVERITY_ORDER else "info"


def _max_severity(left: str | None, right: str | None) -> str:
    left_norm = _normalize_severity(left)
    right_norm = _normalize_severity(right)
    return left_norm if SEVERITY_ORDER[left_norm] >= SEVERITY_ORDER[right_norm] else right_norm


def _extract_failure_type_tokens(text: str) -> list[str]:
    known = {
        "TASK_INCOMPLETE",
        "TOOL_MISSING",
        "TOOL_ORDER_ERROR",
        "FORBIDDEN_TOOL_CALL",
        "OUTPUT_FORMAT_ERROR",
        "OUTPUT_SCHEMA_ERROR",
        "ERROR_HANDLING_MISSING",
        "HALLUCINATION_RISK",
        "LOOP_RISK",
        "REGRESSION",
        "LOW_STABILITY",
        "SAFETY_RISK",
        "CONFIG_ERROR",
        "SCORER_UNCERTAIN",
        "UNKNOWN",
    }
    upper = text.upper()
    return sorted({item for item in known if item in upper}, key=str.casefold)


def _test_change_status(
    old_status: str | None,
    new_status: str | None,
    old_score: float | None,
    new_score: float | None,
) -> str:
    if old_status is None:
        return "new_test"
    if new_status is None:
        return "removed_test"
    if old_status == "failed" and new_status == "passed":
        return "improved"
    if old_status == "passed" and new_status == "failed":
        return "regressed"
    if old_status == "passed" and new_status == "passed":
        if old_score is not None and new_score is not None and abs(new_score - old_score) >= 0.05:
            return "changed_score"
        return "unchanged_pass"
    if old_status == "failed" and new_status == "failed":
        if old_score is not None and new_score is not None:
            if new_score > old_score:
                return "improved"
            if new_score < old_score:
                return "regressed"
        return "unchanged_fail"
    return "unknown"


def _slow_failure_type_changes(
    baseline_time: dict[str, Any],
    current_time: dict[str, Any],
) -> list[dict[str, Any]]:
    baseline_by_type = _seconds_by_failure_type(baseline_time.get("slowest_tests", []))
    current_by_type = _seconds_by_failure_type(current_time.get("slowest_tests", []))
    changes = []
    for failure_type in sorted(set(baseline_by_type) | set(current_by_type), key=str.casefold):
        delta = round(current_by_type.get(failure_type, 0.0) - baseline_by_type.get(failure_type, 0.0), 3)
        if delta:
            changes.append({"failure_type": failure_type, "delta_seconds": delta})
    return changes


def _seconds_by_failure_type(items: Any) -> dict[str, float]:
    result: dict[str, float] = {}
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        seconds = _to_float(item.get("elapsed_seconds")) or 0.0
        for failure_type in item.get("failure_types", []) or []:
            result[str(failure_type)] = result.get(str(failure_type), 0.0) + seconds
    return result


def _candidate_changed_files(agent_state_diff: AgentStateDiff) -> list[str]:
    return [item["path"] for item in agent_state_diff.file_hash_changes]


def _candidate_patch_ids(patch_summary: dict[str, Any] | None) -> list[str]:
    if not patch_summary:
        return []
    return list(patch_summary.get("patch_ids", []) or [])


def _scorer_uncertain_dominates(changes: list[FailureTypeChange]) -> bool:
    worsened = [item for item in changes if item.delta > 0]
    if not worsened:
        return False
    uncertain = sum(item.delta for item in worsened if item.failure_type in SCORER_UNCERTAIN_TYPES)
    total = sum(item.delta for item in worsened)
    return total > 0 and uncertain / total >= 0.5


def _recommended_next_command(comparable: str, rollback: RollbackRecommendation) -> str:
    if rollback.rollback_recommended:
        return "Review rollback candidates before running auto mode."
    if comparable in {"weak", "not_comparable"}:
        return "agentdoctor deep --rounds 3 --save-baseline"
    return "agentdoctor deep --rounds 3 --compare-baseline latest"


def _validation_tags_for_failure_types(failure_types: list[str]) -> list[str]:
    mapping = {
        "OUTPUT_SCHEMA_ERROR": ["output_schema", "output_format", "regression"],
        "OUTPUT_FORMAT_ERROR": ["output_format", "task_completion", "regression"],
        "TASK_INCOMPLETE": ["task_completion", "regression"],
        "TOOL_MISSING": ["tool_use", "task_completion", "regression"],
        "TOOL_ORDER_ERROR": ["tool_order", "tool_use", "regression"],
        "FORBIDDEN_TOOL_CALL": ["safety", "tool_use", "regression"],
        "SAFETY_RISK": ["safety", "regression"],
        "HALLUCINATION_RISK": ["source_grounding", "task_completion", "regression"],
        "ERROR_HANDLING_MISSING": ["error_handling", "safety", "regression"],
        "LOOP_RISK": ["stability", "tool_use", "regression"],
    }
    tags: list[str] = []
    for failure_type in failure_types:
        for tag in mapping.get(failure_type, ["regression"]):
            if tag not in tags:
                tags.append(tag)
    return tags


def _path_category(path: str) -> str:
    normalized = path.replace("\\", "/").casefold()
    name = Path(normalized).name
    if normalized.startswith("prompts/") or name in {"prompt.md", "system_prompt.md", "instructions.md"} or "prompt" in name:
        return "prompt"
    if name in {"tool_descriptions.yaml", "tool_descriptions.yml", "tools.yaml", "tools.yml"}:
        return "tool"
    if name in {"workflow_config.yaml", "workflow_config.yml", "agentdoctor.yaml", "agentdoctor.yml", "config.yaml", "config.yml"}:
        return "workflow"
    if normalized.startswith("evals/") or "/evals/" in normalized or name.startswith("eval_") or "eval" in name:
        return "eval"
    if name in {"agent.yaml", "agent.yml", "agent.json"} or normalized.startswith("agents/"):
        return "agent_config"
    return "other"


def _find_agent_config(
    parsed: dict[str, Any],
    root: Path,
    agent_config_path: str | Path | None,
) -> str:
    files = _mapping(parsed.get("files"))
    if agent_config_path is not None:
        try:
            rel = _relative(root, _resolve_under_root(root, agent_config_path))
            if rel in files:
                return rel
        except OSError:
            pass
    for rel in sorted(files, key=str.casefold):
        if _path_category(rel) == "agent_config":
            return rel
    return ""


def _tool_names(items: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and item.get("name"):
                names.add(str(item["name"]))
    return names


def _changed_tool_descriptions(
    baseline_snapshot: dict[str, Any],
    current_snapshot: AgentStateSnapshot,
) -> list[str]:
    baseline_tools = {
        str(item.get("name")): item
        for item in _mapping(baseline_snapshot.get("tool_state")).get("tools", [])
        if isinstance(item, dict) and item.get("name")
    }
    current_tools = {
        str(item.get("name")): item
        for item in current_snapshot.tool_state.get("tools", [])
        if isinstance(item, dict) and item.get("name")
    }
    changed = []
    for name in sorted(set(baseline_tools) & set(current_tools), key=str.casefold):
        if baseline_tools[name].get("description_hash") != current_tools[name].get("description_hash"):
            changed.append(name)
    return changed


def _approval_policy_hash(workflow: dict[str, Any]) -> str:
    return _stable_hash(
        {
            "review_policy": workflow.get("review_policy"),
            "approval_required_for": workflow.get("approval_required_for"),
            "forbidden_tools": workflow.get("forbidden_tools"),
        }
    )


def _stable_hash(value: Any) -> str:
    text = json.dumps(to_plain_data(value), sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _elapsed_seconds(started_at: str | None, finished_at: str | None) -> float | None:
    if not started_at or not finished_at:
        return None
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return round(max(0.0, (finished - started).total_seconds()), 3)


def _resolve_under_root(root: Path, path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def _relative(root: Path, path: str | Path | None) -> str:
    if path is None:
        return ""
    target = Path(path)
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return target.as_posix().replace("\\", "/")


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None:
        return []
    return [value]


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _round_delta(new: float | None, old: float | None) -> float | None:
    if new is None or old is None:
        return None
    return round(new - old, 4)


def _delta_int(new: Any, old: Any) -> int | None:
    new_int = _to_int(new)
    old_int = _to_int(old)
    if new_int is None or old_int is None:
        return None
    return new_int - old_int


def _format_optional_float(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "unknown"
    return f"{number:.2f}"


def _format_signed(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "unknown"
    return f"{number:+.2f}"


def _json_block(value: Any) -> str:
    return "```json\n" + json.dumps(to_plain_data(value), indent=2, sort_keys=True) + "\n```"


def _now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc).astimezone()
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now


def _iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()
