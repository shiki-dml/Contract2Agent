from __future__ import annotations

from typing import Any

from contract2agent.cost_estimate.models import FailureTypeCostRisk


FAILURE_RISK_ORDER = [
    "LOOP_RISK",
    "LOW_STABILITY",
    "TOOL_ARGUMENT_ERROR",
    "ERROR_HANDLING_MISSING",
    "HALLUCINATION_RISK",
    "OUTPUT_SCHEMA_ERROR",
    "SAFETY_RISK",
    "FORBIDDEN_TOOL_CALL",
    "REGRESSION",
    "SCORER_UNCERTAIN",
    "UNKNOWN",
]

FAILURE_RISK_RULES: dict[str, tuple[str, str, list[str]]] = {
    "LOOP_RISK": (
        "high",
        "Repeated tool calls, retries, or missing stop conditions may increase runtime.",
        ["max_tool_calls_per_test", "max_steps_per_test", "stop_on_loop_risk"],
    ),
    "LOW_STABILITY": (
        "high",
        "Repeated validation runs may be required to confirm stability.",
        ["max_repeated_runs", "repeated_run_sample_size", "stop_if_variance_persists"],
    ),
    "TOOL_ARGUMENT_ERROR": (
        "medium",
        "Invalid tool calls may trigger retries, tool errors, or fallback tests.",
        ["fail_fast_on_repeated_tool_error", "max_tool_retries"],
    ),
    "ERROR_HANDLING_MISSING": (
        "medium",
        "The agent may continue after tool failures or invalid input, increasing wasted calls.",
        ["stop_after_tool_failure", "require_error_handling_tests"],
    ),
    "HALLUCINATION_RISK": (
        "high",
        "Source-grounding validation can require document reads, retrieval checks, citation checks, and sometimes LLM judges.",
        ["focus_source_grounding_subset", "use_deterministic_source_scorers_when_possible"],
    ),
    "OUTPUT_SCHEMA_ERROR": (
        "medium",
        "Schema validation is cheap, but repair and validation cycles add cost in auto mode.",
        ["validate_schema_before_full_deep", "run_output_schema_focus_first"],
    ),
    "SAFETY_RISK": (
        "high",
        "Safety findings usually require human review and additional permission-boundary tests.",
        ["stop_on_safety_risk", "require_review_before_auto"],
    ),
    "FORBIDDEN_TOOL_CALL": (
        "high",
        "Forbidden tool behavior should stop auto mode and trigger review.",
        ["stop_on_forbidden_tool_call", "run_safety_tests_before_auto"],
    ),
    "REGRESSION": (
        "high",
        "Regression checks require baseline comparison and may trigger rollback or validation loops.",
        ["compare_baseline", "stop_on_regression", "max_patch_attempts"],
    ),
    "SCORER_UNCERTAIN": (
        "medium",
        "Human review or scorer refinement may be required before meaningful repair.",
        ["stop_if_scorer_uncertain_dominates", "require_eval_review"],
    ),
    "UNKNOWN": (
        "unknown",
        "Unknown failures require better instrumentation and may waste repeated runs.",
        ["stop_if_unknown_dominates", "improve_trace_collection_first"],
    ),
}


def extract_failure_types(
    *,
    triage: dict[str, Any] | None,
    tags: list[str],
    tools: list[dict[str, Any]],
    scorer_unknown: bool,
) -> list[str]:
    failure_types: list[str] = []
    if triage is None:
        return ["UNKNOWN"]

    for item in triage.get("missing_information") or []:
        if isinstance(item, dict) and item.get("related_failure_type"):
            failure_types.append(str(item["related_failure_type"]))
    for behavior in triage.get("key_behaviors_to_test") or []:
        if isinstance(behavior, dict):
            failure_types.extend(str(item) for item in behavior.get("related_risks") or [])
    for warning in triage.get("warnings") or []:
        if isinstance(warning, dict):
            identifier = str(warning.get("id") or "").casefold()
            if "forbidden" in identifier:
                failure_types.append("FORBIDDEN_TOOL_CALL")
            if "safety" in identifier:
                failure_types.append("SAFETY_RISK")

    tag_set = {tag.casefold() for tag in tags}
    if "tool_arguments" in tag_set:
        failure_types.append("TOOL_ARGUMENT_ERROR")
    if "error_handling" in tag_set:
        failure_types.append("ERROR_HANDLING_MISSING")
    if {"hallucination", "source_grounding"} & tag_set:
        failure_types.append("HALLUCINATION_RISK")
    if "output_schema" in tag_set:
        failure_types.append("OUTPUT_SCHEMA_ERROR")
    if {"safety", "permission_boundary"} & tag_set:
        failure_types.append("SAFETY_RISK")
        failure_types.append("FORBIDDEN_TOOL_CALL")
    if "regression" in tag_set:
        failure_types.append("REGRESSION")
    if "stability" in tag_set:
        failure_types.append("LOW_STABILITY")
    if tools:
        failure_types.append("LOOP_RISK")
    if scorer_unknown:
        failure_types.append("SCORER_UNCERTAIN")

    known = set(FAILURE_RISK_RULES)
    ordered = [item for item in FAILURE_RISK_ORDER if item in failure_types]
    extras = sorted({item for item in failure_types if item in known and item not in ordered})
    return ordered + extras


def map_failure_type_cost_risks(failure_types: list[str]) -> list[FailureTypeCostRisk]:
    risks: list[FailureTypeCostRisk] = []
    for failure_type in FAILURE_RISK_ORDER:
        if failure_type not in failure_types:
            continue
        impact, reason, guardrails = FAILURE_RISK_RULES[failure_type]
        risks.append(
            FailureTypeCostRisk(
                failure_type=failure_type,
                cost_impact=impact,
                reason=reason,
                recommended_guardrails=guardrails,
            )
        )
    return risks
