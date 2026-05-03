from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


STATUSES = {"found", "missing", "skipped", "error"}
AGENT_TYPES = {
    "research_agent",
    "coding_agent",
    "workflow_agent",
    "data_analysis_agent",
    "file_operation_agent",
    "general_tool_agent",
    "chat_agent",
    "unknown",
}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
RISK_LEVELS = {"low", "medium", "high", "unknown"}
TOOL_CATEGORIES = {
    "document_reading",
    "web_search",
    "browser",
    "filesystem_read",
    "filesystem_write",
    "code_execution",
    "shell_execution",
    "database",
    "external_api",
    "communication",
    "calendar",
    "email",
    "memory",
    "retrieval",
    "formatting",
    "validation",
    "unknown",
}
SIDE_EFFECT_LEVELS = {
    "none",
    "read_only",
    "write_local",
    "external_read",
    "external_write",
    "destructive",
    "unknown",
}
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


@dataclass
class InputSource:
    path: str | None
    status: str
    reason: str | None = None


@dataclass
class DetectedTool:
    name: str
    description: str
    category: str
    risk_level: str
    side_effect_level: str
    requires_confirmation: bool
    evidence: list[str] = field(default_factory=list)


@dataclass
class DetectedCapabilities:
    tools: list[DetectedTool] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    external_dependencies: list[str] = field(default_factory=list)


@dataclass
class AgentSummary:
    name: str | None = None
    description: str | None = None
    model: str | None = None
    provider: str | None = None
    prompt_files: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    tool_count: int = 0
    eval_case_count: int = 0


@dataclass
class AgentClassification:
    agent_type: str
    classification_confidence: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    risk_level: str
    risk_score: int
    reasons: list[str] = field(default_factory=list)
    high_risk_tools: list[str] = field(default_factory=list)
    missing_safety_controls: list[str] = field(default_factory=list)
    recommended_review_policy: str = "on-fail"


@dataclass
class EvalCoverage:
    eval_case_count: int
    detected_tags: list[str] = field(default_factory=list)
    covered_areas: list[str] = field(default_factory=list)
    missing_areas: list[str] = field(default_factory=list)
    weak_areas: list[str] = field(default_factory=list)
    recommended_new_areas: list[str] = field(default_factory=list)


@dataclass
class KeyBehavior:
    id: str
    title: str
    description: str
    priority: str
    reason: str
    suggested_tags: list[str] = field(default_factory=list)
    related_tools: list[str] = field(default_factory=list)
    related_risks: list[str] = field(default_factory=list)


@dataclass
class MissingInformation:
    id: str
    severity: str
    title: str
    description: str
    why_it_matters: str
    suggested_action: str
    related_failure_type: str


@dataclass
class TriageWarning:
    id: str
    severity: str
    title: str
    description: str
    evidence: list[str] = field(default_factory=list)
    recommended_action: str = ""


@dataclass
class RoundFocus:
    round_index: int
    focus: str
    suggested_tags: list[str] = field(default_factory=list)


@dataclass
class SuggestedRoundPlan:
    mode: str
    rounds: int
    review_policy: str
    round_focuses: list[RoundFocus] = field(default_factory=list)
    target_confidence: float | None = None
    preview_patches: bool = False


@dataclass
class BaselineStatus:
    exists: bool
    path: str | None = None
    created_at: str | None = None
    mode: str | None = None
    confidence: float | None = None
    agent_name: str | None = None
    baseline_id: str | None = None
    baseline_quality: str | None = None
    warning: str | None = None


@dataclass
class PatchPreviewReadiness:
    eligible: bool
    allowed_files_detected: list[str] = field(default_factory=list)
    missing_patch_targets: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)


@dataclass
class AutoReadiness:
    eligible: bool
    reasons: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    required_safety_controls: list[str] = field(default_factory=list)


@dataclass
class EstimatedDiagnosticCost:
    complexity_level: str
    estimated_rounds: int
    estimated_test_count_range: str
    cost_drivers: list[str] = field(default_factory=list)
    note: str = "This is a rough static estimate, not measured runtime."


@dataclass
class Recommendation:
    recommended_mode: str
    recommended_rounds: int
    suggested_review_policy: str
    target_confidence: float | None
    reasoning: list[str] = field(default_factory=list)
    alternative_commands: list[str] = field(default_factory=list)


@dataclass
class TriagePlan:
    triage_id: str
    created_at: str
    project_root: str
    input_sources: dict[str, Any]
    agent_summary: AgentSummary
    detected_capabilities: DetectedCapabilities
    agent_classification: AgentClassification
    risk_assessment: RiskAssessment
    eval_coverage: EvalCoverage
    key_behaviors_to_test: list[KeyBehavior]
    missing_information: list[MissingInformation]
    warnings: list[TriageWarning]
    suggested_test_tags: list[str]
    suggested_round_plan: SuggestedRoundPlan
    baseline_status: BaselineStatus
    patch_preview_readiness: PatchPreviewReadiness
    auto_readiness: AutoReadiness
    estimated_diagnostic_cost: EstimatedDiagnosticCost
    recommendation: Recommendation
    recommended_next_command: str
    report_paths: dict[str, str] = field(default_factory=dict)


def to_plain_data(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {
            key: to_plain_data(item)
            for key, item in asdict(value).items()
            if item is not None
        }
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    return value
