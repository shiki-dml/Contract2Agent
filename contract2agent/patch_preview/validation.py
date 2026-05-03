from __future__ import annotations

from contract2agent.patch_preview.models import FindingGroup


VALIDATION_TAGS_BY_FAILURE_TYPE = {
    "CONFIG_ERROR": ["config", "smoke", "task_completion"],
    "TASK_INCOMPLETE": ["task_completion", "instruction_following", "regression"],
    "TOOL_MISSING": ["tool_use", "tool_order", "regression"],
    "TOOL_ORDER_ERROR": ["tool_order", "tool_sequence", "tool_use", "regression"],
    "TOOL_ARGUMENT_ERROR": ["tool_arguments", "input_validation", "error_handling", "regression"],
    "FORBIDDEN_TOOL_CALL": ["safety", "forbidden_tool_call", "permission_boundary", "regression"],
    "OUTPUT_FORMAT_ERROR": ["output_format", "task_completion", "regression"],
    "OUTPUT_SCHEMA_ERROR": ["output_schema", "json_schema", "output_format", "regression"],
    "ERROR_HANDLING_MISSING": ["error_handling", "missing_file", "tool_error", "clarification", "regression"],
    "HALLUCINATION_RISK": ["hallucination", "source_grounding", "citation", "evidence", "regression"],
    "LOOP_RISK": ["loop_risk", "max_steps", "repeated_tool_calls", "time_cost", "regression"],
    "LOW_STABILITY": ["stability", "repeated_runs", "output_schema", "tool_order", "regression"],
    "REGRESSION": ["regression", "baseline_comparison", "changed_behavior"],
    "SAFETY_RISK": ["safety", "permission_boundary", "human_review", "forbidden_tool_call", "regression"],
    "SCORER_UNCERTAIN": ["scorer_validation", "eval_review", "human_review"],
    "UNKNOWN": ["trace_collection", "instrumentation", "human_review"],
}


def validation_tags_for_group(group: FindingGroup) -> list[str]:
    tags: list[str] = []
    for failure_type in group.failure_types:
        tags.extend(VALIDATION_TAGS_BY_FAILURE_TYPE.get(failure_type, ["regression"]))
    return _dedupe(tags)


def validation_command(tags: list[str]) -> str:
    # The current CLI does not expose --focus or --compare-baseline yet. Keep
    # the command runnable and put the requested focus in validation_tags.
    return "agentdoctor deep --rounds 2 --review on-fail"


def expected_improvement_for_group(group: FindingGroup) -> list[str]:
    improvements: list[str] = []
    for failure_type in group.failure_types:
        if failure_type == "OUTPUT_SCHEMA_ERROR":
            improvements.append("OUTPUT_SCHEMA_ERROR count should decrease.")
            improvements.append("JSON schema tests should pass.")
        elif failure_type == "OUTPUT_FORMAT_ERROR":
            improvements.append("Required output format violations should decrease.")
        elif failure_type == "TOOL_MISSING":
            improvements.append("Required tool-use findings should decrease.")
        elif failure_type == "HALLUCINATION_RISK":
            improvements.append("Unsupported source-grounding findings should decrease.")
        elif failure_type == "SAFETY_RISK":
            improvements.append("Safety-risk findings should move to approval or refusal paths.")
        elif failure_type == "FORBIDDEN_TOOL_CALL":
            improvements.append("Forbidden tool calls should stop appearing in traces.")
        elif failure_type == "REGRESSION":
            improvements.append("Behavior should return to the last accepted baseline or pre-patch state.")
        elif failure_type == "SCORER_UNCERTAIN":
            improvements.append("Scorer uncertainty should be resolved by eval or rubric review.")
        elif failure_type == "UNKNOWN":
            improvements.append("Additional instrumentation should make the failure classifiable.")
        else:
            improvements.append(f"{failure_type} count should decrease.")
    return _dedupe(improvements)


def regression_checks_for_group(group: FindingGroup) -> list[str]:
    checks = [
        "No new SAFETY_RISK findings.",
        "No new FORBIDDEN_TOOL_CALL findings.",
        "No unrelated failure type worsens compared with baseline.",
    ]
    if "OUTPUT_SCHEMA_ERROR" in group.failure_types:
        checks.append("No new TASK_INCOMPLETE findings from stricter schema output.")
        checks.append("No new HALLUCINATION_RISK findings from omitted evidence.")
    if "TOOL_MISSING" in group.failure_types or "TOOL_ORDER_ERROR" in group.failure_types:
        checks.append("No new tool-order or repeated-call failures.")
    if "HALLUCINATION_RISK" in group.failure_types:
        checks.append("No new TASK_INCOMPLETE findings from overly conservative grounding.")
    return _dedupe(checks)


def rollback_conditions_for_group(group: FindingGroup) -> list[str]:
    return [
        "A new SAFETY_RISK or FORBIDDEN_TOOL_CALL appears.",
        "Target failure type improves but unrelated failure types worsen.",
        "Diagnostic confidence drops below the accepted baseline.",
    ]


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
