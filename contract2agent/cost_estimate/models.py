from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


STATIC_ESTIMATE_NOTE = "This is a rough static estimate, not measured runtime."

MODES = {"quick", "deep", "auto", "unknown"}
BUDGET_PROFILES = {"conservative", "balanced", "thorough", "custom"}
CONFIDENCE_LEVELS = {"low", "medium", "high", "unknown"}
COMPLEXITY_LEVELS = {"low", "medium", "high", "very_high", "unknown"}


@dataclass
class CostEstimateOptions:
    from_triage: Path | None = None
    mode: str | None = None
    budget_profile: str = "balanced"
    max_rounds: int | None = None
    max_tests: int | None = None
    max_runtime_minutes: int | None = None
    max_llm_calls: int | None = None
    max_tool_calls: int | None = None
    max_tool_calls_per_test: int | None = None
    max_repeated_runs: int | None = None
    max_auto_iterations: int | None = None
    max_patch_attempts: int | None = None
    output: Path | None = None
    output_format: str = "markdown"
    project_root: Path | None = None
    now: Any | None = None

    def has_budget_overrides(self) -> bool:
        return any(
            value is not None
            for value in (
                self.max_rounds,
                self.max_tests,
                self.max_runtime_minutes,
                self.max_llm_calls,
                self.max_tool_calls,
                self.max_tool_calls_per_test,
                self.max_repeated_runs,
                self.max_auto_iterations,
                self.max_patch_attempts,
            )
        )


@dataclass
class ToolCallEstimate:
    total: list[int]
    by_tool: dict[str, list[int]] = field(default_factory=dict)
    confidence: str = "low"
    note: str = "Tool calls are statically estimated from tool metadata and test tags."


@dataclass
class RuntimeEstimate:
    level: str
    min_seconds: int | None = None
    max_seconds: int | None = None
    confidence: str = "low"
    note: str = (
        "Runtime depends on model latency, local environment, tool mocks, and network "
        "conditions."
    )
    source: str | None = None


@dataclass
class HumanReviewEstimate:
    count_range: list[int]
    review_burden_level: str
    triggers: list[str] = field(default_factory=list)
    review_policy: str = "on-fail"
    explanation: str = ""


@dataclass
class CostDriver:
    id: str
    title: str
    impact: str
    reason: str
    evidence: list[str] = field(default_factory=list)
    suggested_guardrail: str | None = None


@dataclass
class FailureTypeCostRisk:
    failure_type: str
    cost_impact: str
    reason: str
    recommended_guardrails: list[str] = field(default_factory=list)


@dataclass
class BudgetGuardrails:
    max_rounds: int | None = None
    max_tests: int | None = None
    max_runtime_minutes: int | None = None
    max_llm_calls: int | None = None
    max_tool_calls: int | None = None
    max_tool_calls_per_test: int | None = None
    max_repeated_runs: int | None = None
    max_auto_iterations: int | None = None
    max_patch_attempts: int | None = None
    min_confidence_improvement: float | None = None
    stop_on_safety_risk: bool = True
    stop_on_forbidden_tool_call: bool = True
    stop_on_regression: bool = True
    stop_on_loop_risk: bool = True
    stop_on_low_improvement: bool = True
    stop_if_scorer_uncertain_dominates: bool = True
    stop_if_unknown_dominates: bool = True
    require_patch_preview: bool = False
    require_human_review_for_high_risk: bool = False


@dataclass
class ModeCostComparison:
    mode: str
    estimated_rounds: int | list[int]
    estimated_test_count_range: list[int]
    estimated_llm_call_range: list[int]
    estimated_tool_call_range: dict[str, Any]
    runtime_level: str
    review_burden_level: str
    risk_level: str
    best_for: str
    limitations: str
    recommended: bool
    command: str


@dataclass
class SlowPathPrediction:
    id: str
    title: str
    reason: str
    likely_impact: str
    related_tools: list[str] = field(default_factory=list)
    related_failure_types: list[str] = field(default_factory=list)
    suggested_guardrail: str | None = None


@dataclass
class AutoCostPlan:
    auto_considered: bool
    auto_recommended: bool
    reason: str
    target_confidence: float | None
    max_iterations: int | None
    estimated_iterations: list[int]
    estimated_patch_attempts: list[int]
    estimated_validation_runs: list[int]
    estimated_regression_checks: list[int]
    overfitting_risk: str
    stop_conditions: list[str] = field(default_factory=list)
    required_guardrails: list[str] = field(default_factory=list)
    recommended_auto_command: str | None = None


@dataclass
class BaselineCostContext:
    baseline_exists: bool
    baseline_path: str | None = None
    historical_cost_available: bool = False
    historical_cost_used: bool = False
    previous_avg_runtime: float | None = None
    previous_slowest_tests: list[str] = field(default_factory=list)
    previous_slowest_failure_types: list[str] = field(default_factory=list)
    baseline_warning: str | None = None
    regression_check_cost: str = "limited without a reliable baseline"


@dataclass
class PatchPreviewCostContext:
    patch_preview_enabled: bool
    estimated_patch_proposals: list[int]
    estimated_validation_tests_per_patch: list[int]
    estimated_extra_validation_runs: list[int]
    recommended_validation_tags: list[str] = field(default_factory=list)
    regression_checks_required: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class OptimizationSuggestion:
    title: str
    reason: str
    expected_effect: str
    related_guardrail_or_command: str


@dataclass
class EstimatedDiagnosticCost:
    cost_estimate_id: str
    created_at: str
    source_triage_id: str | None
    source_triage_path: str | None
    project_root: str
    mode: str
    budget_profile: str
    confidence: str
    complexity_level: str
    estimated_rounds: int | list[int] | str
    estimated_test_count_range: list[int]
    estimated_llm_call_range: list[int]
    estimated_tool_call_range: ToolCallEstimate
    estimated_runtime_range: RuntimeEstimate
    estimated_human_review_items: HumanReviewEstimate
    estimated_patch_attempts: list[int]
    estimated_auto_iterations: list[int]
    cost_drivers: list[CostDriver] = field(default_factory=list)
    cost_risks: list[dict[str, Any]] = field(default_factory=list)
    failure_type_cost_risks: list[FailureTypeCostRisk] = field(default_factory=list)
    budget_recommendation: str = ""
    budget_guardrails: BudgetGuardrails = field(default_factory=BudgetGuardrails)
    mode_comparison: list[ModeCostComparison] = field(default_factory=list)
    slow_path_predictions: list[SlowPathPrediction] = field(default_factory=list)
    review_burden: dict[str, Any] = field(default_factory=dict)
    auto_cost_plan: AutoCostPlan | None = None
    baseline_cost_context: BaselineCostContext | None = None
    patch_preview_cost_context: PatchPreviewCostContext | None = None
    optimization_suggestions: list[OptimizationSuggestion] = field(default_factory=list)
    recommended_command: str = ""
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    note: str = STATIC_ESTIMATE_NOTE
    report_paths: dict[str, str] = field(default_factory=dict)


def to_plain_data(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {str(key): to_plain_data(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    return value
