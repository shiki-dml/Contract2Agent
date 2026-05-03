from __future__ import annotations

from contract2agent.patch_preview.models import FindingGroup
from contract2agent.patch_preview.strategies import is_read_only_tool, is_side_effect_tool


def compute_risk_and_approval(
    group: FindingGroup,
    *,
    patch_type: str,
    target_is_safe: bool,
) -> tuple[str, bool, bool, bool]:
    failure_types = set(group.failure_types)
    tool = group.tool_name

    risk = _risk_level(failure_types, tool)
    auto_apply_eligible = _auto_apply_eligible(
        failure_types,
        tool,
        patch_type=patch_type,
        target_is_safe=target_is_safe,
    )
    requires_approval = _requires_approval(risk, failure_types, auto_apply_eligible)

    # Patch Preview v0.1 is a review gate. It computes eligibility for future
    # flows but never marks a generated proposal as directly auto-applicable.
    do_not_apply_automatically = True
    if risk in {"high", "critical", "unknown"}:
        do_not_apply_automatically = True
    if failure_types & {
        "SAFETY_RISK",
        "FORBIDDEN_TOOL_CALL",
        "REGRESSION",
        "SCORER_UNCERTAIN",
        "UNKNOWN",
    }:
        do_not_apply_automatically = True
    return risk, requires_approval, auto_apply_eligible, do_not_apply_automatically


def _risk_level(failure_types: set[str], tool_name: str | None) -> str:
    if "UNKNOWN" in failure_types:
        return "unknown"
    if failure_types & {"SAFETY_RISK", "FORBIDDEN_TOOL_CALL"}:
        return "critical"
    if "REGRESSION" in failure_types:
        return "high"
    if "SCORER_UNCERTAIN" in failure_types:
        return "medium"
    if failure_types & {"TOOL_MISSING", "TOOL_ORDER_ERROR", "TOOL_ARGUMENT_ERROR"} and is_side_effect_tool(tool_name):
        lowered = (tool_name or "").casefold()
        if any(term in lowered for term in ("shell", "exec", "email", "calendar", "database")):
            return "critical"
        return "high"
    if "CONFIG_ERROR" in failure_types:
        return "medium"
    if "OUTPUT_FORMAT_ERROR" in failure_types and failure_types <= {"OUTPUT_FORMAT_ERROR"}:
        return "low"
    if failure_types & {
        "OUTPUT_SCHEMA_ERROR",
        "HALLUCINATION_RISK",
        "TOOL_ORDER_ERROR",
        "TOOL_ARGUMENT_ERROR",
        "ERROR_HANDLING_MISSING",
        "LOOP_RISK",
        "LOW_STABILITY",
        "TASK_INCOMPLETE",
    }:
        return "medium"
    if "TOOL_MISSING" in failure_types:
        return "low" if is_read_only_tool(tool_name) else "medium"
    return "medium"


def _auto_apply_eligible(
    failure_types: set[str],
    tool_name: str | None,
    *,
    patch_type: str,
    target_is_safe: bool,
) -> bool:
    if not target_is_safe or patch_type == "no_agent_patch_review_only":
        return False
    if failure_types & {
        "SAFETY_RISK",
        "FORBIDDEN_TOOL_CALL",
        "REGRESSION",
        "SCORER_UNCERTAIN",
        "UNKNOWN",
        "CONFIG_ERROR",
    }:
        return False
    if failure_types == {"OUTPUT_FORMAT_ERROR"}:
        return True
    if "OUTPUT_SCHEMA_ERROR" in failure_types:
        return True
    if "TOOL_MISSING" in failure_types:
        return is_read_only_tool(tool_name)
    if "TOOL_ORDER_ERROR" in failure_types:
        return not is_side_effect_tool(tool_name)
    if "TOOL_ARGUMENT_ERROR" in failure_types:
        return not is_side_effect_tool(tool_name)
    if "ERROR_HANDLING_MISSING" in failure_types:
        return not is_side_effect_tool(tool_name)
    if "HALLUCINATION_RISK" in failure_types:
        return patch_type == "prompt_update"
    if "LOOP_RISK" in failure_types:
        return patch_type in {"prompt_update", "agent_config_update"}
    if "LOW_STABILITY" in failure_types:
        return False
    if "TASK_INCOMPLETE" in failure_types:
        return True
    return False


def _requires_approval(
    risk: str,
    failure_types: set[str],
    auto_apply_eligible: bool,
) -> bool:
    if risk in {"high", "critical", "unknown"}:
        return True
    if failure_types & {"SAFETY_RISK", "FORBIDDEN_TOOL_CALL", "SCORER_UNCERTAIN", "UNKNOWN", "REGRESSION"}:
        return True
    if risk == "medium":
        return True
    return False
