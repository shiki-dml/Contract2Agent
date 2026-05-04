from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any


class DiagnosisCategory(str, Enum):
    CONTRACT_TOO_LOOSE = "contract_too_loose"
    CONTRACT_TOO_STRICT = "contract_too_strict"
    CHECKER_TOO_LOOSE = "checker_too_loose"
    CHECKER_TOO_STRICT = "checker_too_strict"
    MONITOR_TOO_LOOSE = "monitor_too_loose"
    MONITOR_TOO_STRICT = "monitor_too_strict"
    AGENT_PROMPT_TOO_WEAK = "agent_prompt_too_weak"
    PARSER_MISSED_CONSTRAINT = "parser_missed_constraint"
    EVAL_EXPECTATION_TOO_STRICT = "eval_expectation_too_strict"
    EVAL_EXPECTATION_AMBIGUOUS = "eval_expectation_ambiguous"
    CONTRACT_CONFLICT = "contract_conflict"
    RULE_UNCOVERED = "rule_uncovered"
    AGENT_BEHAVIOR_FAILURE = "agent_behavior_failure"


class Strictness(str, Enum):
    TOO_LOOSE = "too_loose"
    TOO_STRICT = "too_strict"
    AMBIGUOUS = "ambiguous"
    NOT_APPLICABLE = "not_applicable"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AffectedAgentPart(str, Enum):
    TOOL_ORDERING = "tool_ordering"
    ERROR_HANDLING = "error_handling"
    FORBIDDEN_TOOL_CONTROL = "forbidden_tool_control"
    FORBIDDEN_INTENT_REFUSAL = "forbidden_intent_refusal"
    OUTPUT_FORMATTING = "output_formatting"
    RUNTIME_MONITOR = "runtime_monitor"
    TRACE_CHECKER = "trace_checker"
    CONTRACT_PARSER = "contract_parser"
    EVAL_EXPECTATION = "eval_expectation"
    CAPABILITY_SCOPE = "capability_scope"
    CONTRACT_CONSISTENCY = "contract_consistency"
    RULE_COVERAGE = "rule_coverage"


RULE_COVERAGE_STATUSES = {"ok", "weak", "uncovered", "unknown"}


@dataclass
class RuleCoverageItem:
    rule_name: str
    rule_kind: str | None = None
    has_positive_trace: bool = False
    has_negative_trace: bool = False
    covered_by: list[str] = field(default_factory=list)
    status: str = "unknown"
    uncovered_reason: str | None = None
    suggested_test: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in RULE_COVERAGE_STATUSES:
            raise ValueError(f"Unsupported rule coverage status: {self.status}")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RuleCoverageItem":
        return cls(
            rule_name=str(value.get("rule_name") or "unknown_rule"),
            rule_kind=value.get("rule_kind"),
            has_positive_trace=bool(value.get("has_positive_trace")),
            has_negative_trace=bool(value.get("has_negative_trace")),
            covered_by=[str(item) for item in value.get("covered_by", [])],
            status=str(value.get("status") or "unknown"),
            uncovered_reason=value.get("uncovered_reason"),
            suggested_test=value.get("suggested_test"),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass
class DiagnosisIssue:
    id: str
    severity: str
    category: str
    strictness: str
    affected_agent_part: str
    summary: str
    natural_language_cause: str
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.75
    confidence_reason: list[str] = field(default_factory=list)
    likely_location: str | None = None
    responsibility: dict[str, Any] = field(default_factory=dict)
    suggested_fix: str | None = None
    suggested_patch: dict[str, Any] | None = None
    suggested_requirement_prompt: str | None = None
    suggested_agent_prompt: str | None = None
    suggested_regression_trace: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        self.severity = _coerce_enum_value(Severity, self.severity, "severity")
        self.category = _coerce_enum_value(DiagnosisCategory, self.category, "category")
        self.strictness = _coerce_enum_value(Strictness, self.strictness, "strictness")
        self.affected_agent_part = _coerce_enum_value(
            AffectedAgentPart,
            self.affected_agent_part,
            "affected_agent_part",
        )
        if not self.summary or not self.summary.strip():
            raise ValueError("DiagnosisIssue.summary must not be empty")
        if not self.natural_language_cause or not self.natural_language_cause.strip():
            self.natural_language_cause = self.summary
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("DiagnosisIssue.confidence must be between 0.0 and 1.0")
        self.confidence = float(self.confidence)
        self.evidence = dict(self.evidence or {})
        self.confidence_reason = list(self.confidence_reason or [])
        self.responsibility = dict(self.responsibility or {})
        if not self.responsibility:
            self.responsibility = {
                "primary": self.likely_location or "unknown",
                "secondary": [],
                "not_responsible": [],
            }

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass
class DiagnosisReport:
    contract_name: str | None
    total_issues: int
    issue_counts_by_category: dict[str, int] = field(default_factory=dict)
    issue_counts_by_affected_part: dict[str, int] = field(default_factory=dict)
    issues: list[DiagnosisIssue] = field(default_factory=list)
    rule_coverage: list[RuleCoverageItem] = field(default_factory=list)
    rule_coverage_summary: dict[str, int] = field(default_factory=dict)
    issue_counts_by_severity: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.issues = list(self.issues or [])
        self.rule_coverage = [
            item if isinstance(item, RuleCoverageItem) else RuleCoverageItem.from_dict(item)
            for item in self.rule_coverage or []
        ]
        self.total_issues = len(self.issues)
        self.issue_counts_by_category = dict(
            Counter(issue.category for issue in self.issues)
        )
        self.issue_counts_by_affected_part = dict(
            Counter(issue.affected_agent_part for issue in self.issues)
        )
        self.issue_counts_by_severity = dict(
            Counter(issue.severity for issue in self.issues)
        )
        self.rule_coverage_summary = dict(
            Counter(item.status for item in self.rule_coverage)
        )

    @classmethod
    def from_issues(
        cls,
        *,
        contract_name: str | None,
        issues: list[DiagnosisIssue],
        rule_coverage: list[RuleCoverageItem] | None = None,
    ) -> "DiagnosisReport":
        return cls(
            contract_name=contract_name,
            total_issues=len(issues),
            issues=issues,
            rule_coverage=rule_coverage or [],
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


def make_issue(
    *,
    id: str = "pending",
    severity: Severity | str,
    category: DiagnosisCategory | str,
    strictness: Strictness | str = Strictness.NOT_APPLICABLE,
    affected_agent_part: AffectedAgentPart | str = AffectedAgentPart.CAPABILITY_SCOPE,
    summary: str,
    natural_language_cause: str | None = None,
    evidence: dict[str, Any] | None = None,
    confidence: float = 0.75,
    confidence_reason: list[str] | None = None,
    likely_location: str | None = None,
    responsibility: dict[str, Any] | None = None,
    suggested_fix: str | None = None,
    suggested_patch: dict[str, Any] | None = None,
    suggested_requirement_prompt: str | None = None,
    suggested_agent_prompt: str | None = None,
    suggested_regression_trace: list[dict[str, Any]] | None = None,
) -> DiagnosisIssue:
    return DiagnosisIssue(
        id=id,
        severity=_coerce_enum_value(Severity, severity, "severity"),
        category=_coerce_enum_value(DiagnosisCategory, category, "category"),
        strictness=_coerce_enum_value(Strictness, strictness, "strictness"),
        affected_agent_part=_coerce_enum_value(
            AffectedAgentPart,
            affected_agent_part,
            "affected_agent_part",
        ),
        summary=summary,
        natural_language_cause=natural_language_cause or summary,
        evidence=evidence or {},
        confidence=confidence,
        confidence_reason=confidence_reason or [],
        likely_location=likely_location,
        responsibility=responsibility or {},
        suggested_fix=suggested_fix,
        suggested_patch=suggested_patch,
        suggested_requirement_prompt=suggested_requirement_prompt,
        suggested_agent_prompt=suggested_agent_prompt,
        suggested_regression_trace=suggested_regression_trace,
    )


LEGACY_FAILURE_MAPPINGS: dict[str, dict[str, str]] = {
    "missing_error_handling": {
        "category": DiagnosisCategory.CONTRACT_TOO_LOOSE.value,
        "strictness": Strictness.TOO_LOOSE.value,
        "affected_agent_part": AffectedAgentPart.ERROR_HANDLING.value,
        "likely_location": "agent_contract.yaml",
        "suggested_fix": "Add an explicit missing-input or tool-error handling rule.",
    },
    "no_write_on_missing_file": {
        "category": DiagnosisCategory.AGENT_BEHAVIOR_FAILURE.value,
        "strictness": Strictness.NOT_APPLICABLE.value,
        "affected_agent_part": AffectedAgentPart.ERROR_HANDLING.value,
        "likely_location": "generated_project/agent/prompts/system.md",
        "suggested_fix": "Stop after pdf_reader returns file_not_found; do not call markdown_writer.",
    },
    "forbid_tool_after_tool_error": {
        "category": DiagnosisCategory.AGENT_BEHAVIOR_FAILURE.value,
        "strictness": Strictness.NOT_APPLICABLE.value,
        "affected_agent_part": AffectedAgentPart.ERROR_HANDLING.value,
        "likely_location": "generated_project/agent/prompts/system.md",
        "suggested_fix": "Handle tool errors before continuing with dependent write actions.",
    },
    "forbidden_tool_not_caught": {
        "category": DiagnosisCategory.CHECKER_TOO_LOOSE.value,
        "strictness": Strictness.TOO_LOOSE.value,
        "affected_agent_part": AffectedAgentPart.FORBIDDEN_TOOL_CONTROL.value,
        "likely_location": "contract2agent/checker.py",
        "suggested_fix": "Enforce forbidden tool calls in the trace checker.",
    },
    "forbidden_tool": {
        "category": DiagnosisCategory.AGENT_BEHAVIOR_FAILURE.value,
        "strictness": Strictness.NOT_APPLICABLE.value,
        "affected_agent_part": AffectedAgentPart.FORBIDDEN_TOOL_CONTROL.value,
        "likely_location": "generated_project/agent/prompts/system.md",
        "suggested_fix": "Update the agent prompt to refuse or avoid forbidden tools.",
    },
    "valid_trace_rejected": {
        "category": DiagnosisCategory.CHECKER_TOO_STRICT.value,
        "strictness": Strictness.TOO_STRICT.value,
        "affected_agent_part": AffectedAgentPart.TOOL_ORDERING.value,
        "likely_location": "contract2agent/checker.py",
        "suggested_fix": "Relax the checker so valid tool sequences are accepted.",
    },
    "tool_order_violation": {
        "category": DiagnosisCategory.AGENT_BEHAVIOR_FAILURE.value,
        "strictness": Strictness.NOT_APPLICABLE.value,
        "affected_agent_part": AffectedAgentPart.TOOL_ORDERING.value,
        "likely_location": "generated_project/agent/prompts/system.md",
        "suggested_fix": "Require the agent to follow the declared tool sequence.",
    },
    "must_read_before_write": {
        "category": DiagnosisCategory.AGENT_BEHAVIOR_FAILURE.value,
        "strictness": Strictness.NOT_APPLICABLE.value,
        "affected_agent_part": AffectedAgentPart.TOOL_ORDERING.value,
        "likely_location": "generated_project/agent/prompts/system.md",
        "suggested_fix": "Call pdf_reader successfully before calling markdown_writer.",
    },
    "require_tool_before_tool": {
        "category": DiagnosisCategory.AGENT_BEHAVIOR_FAILURE.value,
        "strictness": Strictness.NOT_APPLICABLE.value,
        "affected_agent_part": AffectedAgentPart.TOOL_ORDERING.value,
        "likely_location": "generated_project/agent/prompts/system.md",
        "suggested_fix": "Call the prerequisite tool before the dependent tool.",
    },
    "eval_output_mismatch": {
        "category": DiagnosisCategory.EVAL_EXPECTATION_TOO_STRICT.value,
        "strictness": Strictness.TOO_STRICT.value,
        "affected_agent_part": AffectedAgentPart.EVAL_EXPECTATION.value,
        "likely_location": "evals/user_dataset.yaml",
        "suggested_fix": "Review the eval expectation and accept equivalent output variants where appropriate.",
    },
    "final_output_contains": {
        "category": DiagnosisCategory.EVAL_EXPECTATION_TOO_STRICT.value,
        "strictness": Strictness.TOO_STRICT.value,
        "affected_agent_part": AffectedAgentPart.EVAL_EXPECTATION.value,
        "likely_location": "evals/user_dataset.yaml",
        "suggested_fix": "Check whether the required output text is too strict or should be moved into the agent prompt.",
    },
    "malformed_trace": {
        "category": DiagnosisCategory.AGENT_BEHAVIOR_FAILURE.value,
        "strictness": Strictness.NOT_APPLICABLE.value,
        "affected_agent_part": AffectedAgentPart.TRACE_CHECKER.value,
        "likely_location": "trace fixture",
        "suggested_fix": "Fix the trace fixture so tool calls and results are well formed.",
    },
    "max_steps": {
        "category": DiagnosisCategory.AGENT_BEHAVIOR_FAILURE.value,
        "strictness": Strictness.NOT_APPLICABLE.value,
        "affected_agent_part": AffectedAgentPart.CAPABILITY_SCOPE.value,
        "likely_location": "generated_project/agent/prompts/system.md",
        "suggested_fix": "Add a step budget and stop condition to the agent behavior.",
    },
    "unexpected_pass": {
        "category": DiagnosisCategory.CHECKER_TOO_LOOSE.value,
        "strictness": Strictness.TOO_LOOSE.value,
        "affected_agent_part": AffectedAgentPart.TRACE_CHECKER.value,
        "likely_location": "contract2agent/checker.py",
        "suggested_fix": "Enforce the expected failing rule or add the missing contract rule.",
    },
    "unexpected_fail": {
        "category": DiagnosisCategory.CHECKER_TOO_STRICT.value,
        "strictness": Strictness.TOO_STRICT.value,
        "affected_agent_part": AffectedAgentPart.TRACE_CHECKER.value,
        "likely_location": "contract2agent/checker.py",
        "suggested_fix": "Relax the checker or contract rule that rejected the expected passing trace.",
    },
}


def issue_from_legacy_failure(
    failure_label: str,
    *,
    summary: str | None = None,
    evidence: dict[str, Any] | None = None,
    natural_language_cause: str | None = None,
    severity: Severity | str = Severity.ERROR,
    confidence: float = 0.6,
    likely_location: str | None = None,
    suggested_fix: str | None = None,
) -> DiagnosisIssue:
    normalized = str(failure_label).split(":", 1)[0]
    mapping = LEGACY_FAILURE_MAPPINGS.get(
        str(failure_label),
        LEGACY_FAILURE_MAPPINGS.get(normalized),
    )
    if mapping is None:
        mapping = {
            "category": DiagnosisCategory.AGENT_BEHAVIOR_FAILURE.value,
            "strictness": Strictness.NOT_APPLICABLE.value,
            "affected_agent_part": AffectedAgentPart.TRACE_CHECKER.value,
        }
    issue_summary = summary or _legacy_summary(str(failure_label))
    issue_cause = natural_language_cause or _legacy_cause(str(failure_label), issue_summary)
    return make_issue(
        severity=severity,
        category=mapping["category"],
        strictness=mapping["strictness"],
        affected_agent_part=mapping["affected_agent_part"],
        summary=issue_summary,
        natural_language_cause=issue_cause,
        evidence={"legacy_failure_label": failure_label, **(evidence or {})},
        confidence=confidence,
        confidence_reason=["Converted from deterministic legacy failure label."],
        likely_location=likely_location or mapping.get("likely_location"),
        suggested_fix=suggested_fix or mapping.get("suggested_fix"),
    )


normalize_failure_type_to_issue = issue_from_legacy_failure


def to_plain_data(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: to_plain_data(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    return value


def _coerce_enum_value(enum_type: type[Enum], value: Enum | str, field_name: str) -> str:
    if isinstance(value, enum_type):
        return str(value.value)
    try:
        return str(enum_type(str(value)).value)
    except ValueError as exc:
        raise ValueError(f"Unsupported {field_name}: {value}") from exc


def _legacy_summary(failure_label: str) -> str:
    label = str(failure_label)
    if label in {"no_write_on_missing_file", "forbid_tool_after_tool_error"}:
        return "Agent wrote after a missing-file tool error."
    if label in {"must_read_before_write", "require_tool_before_tool", "tool_order_violation"}:
        return "Agent used tools in the wrong order."
    if label in {"forbidden_tool", "forbidden_tool_not_caught"}:
        return "Forbidden tool behavior was observed."
    if label in {"valid_trace_rejected", "unexpected_fail"}:
        return "Expected passing trace was rejected."
    if label == "unexpected_pass":
        return "Expected failing trace was accepted."
    if label in {"eval_output_mismatch", "final_output_contains"}:
        return "Eval output expectation did not match the trace output."
    return f"Legacy failure {failure_label} was reported."


def _legacy_cause(failure_label: str, summary: str) -> str:
    label = str(failure_label)
    if label in {"no_write_on_missing_file", "forbid_tool_after_tool_error"}:
        return (
            "The agent's missing-file handling failed. The checker reported that "
            "pdf_reader returned file_not_found, but markdown_writer was still "
            "called. The agent should stop or ask for a valid file instead of "
            "writing notes after a failed read."
        )
    if label in {"must_read_before_write", "require_tool_before_tool", "tool_order_violation"}:
        return (
            "The agent's tool ordering failed. The trace called a dependent tool "
            "before the required prerequisite tool had completed successfully. "
            "The agent prompt should require the prerequisite tool result before "
            "continuing."
        )
    if label == "forbidden_tool_not_caught":
        return (
            "Forbidden-tool checking is too loose. A trace containing a forbidden "
            "tool was accepted, so the checker should enforce the forbidden tool "
            "policy."
        )
    if label == "forbidden_tool":
        return (
            "The agent called a tool that the contract forbids. The checker caught "
            "the violation, so the likely repair belongs in the agent prompt or "
            "tool-use policy."
        )
    if label in {"valid_trace_rejected", "unexpected_fail"}:
        return (
            "The system is too strict for this trace. A trace expected to pass was "
            "rejected, so the checker or contract rule should be narrowed to allow "
            "the intended valid behavior."
        )
    if label == "unexpected_pass":
        return (
            "The system is too loose for this trace. A trace expected to fail was "
            "accepted, so the missing contract rule or checker enforcement should "
            "be added."
        )
    if label in {"eval_output_mismatch", "final_output_contains"}:
        return (
            "The eval expectation rejected the output. Review whether the expected "
            "text is stricter than the task requires or whether the agent prompt "
            "needs a clearer output template."
        )
    return (
        f"{summary} The legacy failure label was normalized into the structured "
        "diagnosis schema with deterministic category, strictness, affected part, "
        "evidence, and suggested fix fields."
    )
