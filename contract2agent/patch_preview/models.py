from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


FAILURE_TYPES = {
    "CONFIG_ERROR",
    "TASK_INCOMPLETE",
    "TOOL_MISSING",
    "TOOL_ORDER_ERROR",
    "TOOL_ARGUMENT_ERROR",
    "FORBIDDEN_TOOL_CALL",
    "OUTPUT_FORMAT_ERROR",
    "OUTPUT_SCHEMA_ERROR",
    "ERROR_HANDLING_MISSING",
    "HALLUCINATION_RISK",
    "LOOP_RISK",
    "LOW_STABILITY",
    "REGRESSION",
    "SAFETY_RISK",
    "SCORER_UNCERTAIN",
    "UNKNOWN",
}

PATCH_TYPES = {
    "prompt_update",
    "tool_description_update",
    "workflow_config_update",
    "agent_config_update",
    "eval_update",
    "scorer_update",
    "rollback_patch",
    "documentation_update",
    "no_agent_patch_review_only",
}

PATCH_RISK_LEVELS = {"low", "medium", "high", "critical", "unknown"}

PATCH_STATUSES = {
    "draft",
    "previewed",
    "approved",
    "rejected",
    "edited",
    "applied",
    "rolled_back",
    "expired",
}


@dataclass
class PatchFinding:
    id: str
    failure_type: str
    title: str = ""
    description: str = ""
    severity: str = "error"
    status: str = "FAIL"
    related_test_id: str | None = None
    related_trace_id: str | None = None
    source_round_id: str | None = None
    likely_cause: str | None = None
    target_file: str | None = None
    tool_name: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class FindingGroup:
    group_id: str
    failure_types: list[str]
    findings: list[PatchFinding]
    likely_cause: str
    target_file: str | None = None
    tool_name: str | None = None

    @property
    def related_finding_ids(self) -> list[str]:
        return sorted({finding.id for finding in self.findings})

    @property
    def source_round_ids(self) -> list[str]:
        return sorted(
            {finding.source_round_id for finding in self.findings if finding.source_round_id}
        )


@dataclass
class LoadedFindings:
    source_path: str | None
    source_run_id: str | None
    findings: list[PatchFinding] = field(default_factory=list)
    raw_report: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    previous_patch_metadata: dict[str, Any] | None = None


@dataclass
class BaselineImpact:
    baseline_exists: bool
    baseline_path: str | None = None
    target_failure_type_in_baseline: dict[str, int] = field(default_factory=dict)
    current_failure_count: dict[str, int] = field(default_factory=dict)
    baseline_failure_count: dict[str, int] = field(default_factory=dict)
    likely_regression_risks: list[str] = field(default_factory=list)
    recommended_regression_checks: list[str] = field(default_factory=list)
    warning: str | None = None


@dataclass
class PatchProposal:
    patch_id: str
    created_at: str
    source_run_id: str | None
    source_round_id: str | None
    related_finding_ids: list[str]
    failure_types: list[str]
    grouped_failure_summary: str
    reason: str
    patch_type: str
    strategy_id: str
    target_files: list[str]
    files_changed: list[str]
    diff: str
    before_summary: str
    after_summary: str
    expected_effect: list[str]
    validation_tags: list[str]
    validation_command: str
    regression_risks: list[str]
    baseline_impact: dict[str, Any]
    risk_level: str
    requires_approval: bool
    auto_apply_eligible: bool
    do_not_apply_automatically: bool
    rollback_available: bool
    rollback_plan: str
    reviewer_notes: list[str]
    status: str = "previewed"
    expected_improvement: list[str] = field(default_factory=list)
    regression_checks: list[str] = field(default_factory=list)
    rollback_condition: list[str] = field(default_factory=list)


@dataclass
class PatchPreviewReport:
    patch_preview_id: str
    created_at: str
    source_run: str | None
    proposals: list[PatchProposal]
    skipped_items: list[str] = field(default_factory=list)
    review_required_count: int = 0
    auto_apply_eligible_count: int = 0
    high_risk_count: int = 0
    output_paths: dict[str, str] = field(default_factory=dict)


def to_plain_data(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {key: to_plain_data(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    return value
