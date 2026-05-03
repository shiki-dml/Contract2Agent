from __future__ import annotations

from typing import Any


HIGH_RISK_TOOL_CATEGORIES = {
    "shell_execution",
    "code_execution",
    "browser",
    "filesystem_write",
    "database",
    "external_api",
}
HIGH_RISK_SIDE_EFFECTS = {"write_local", "external_write", "destructive"}


def classify_complexity(
    *,
    mode: str,
    risk_level: str,
    tools: list[dict[str, Any]],
    suggested_rounds: int | None,
    failure_types: list[str],
    patch_preview_eligible: bool,
    auto_readiness_eligible: bool | None,
    has_eval_metadata: bool,
) -> str:
    if risk_level == "unknown" and not tools and not has_eval_metadata:
        return "unknown"

    if mode == "auto":
        return "very_high"

    high_risk_tools = [tool for tool in tools if _is_high_risk_tool(tool)]
    failure_set = set(failure_types)
    if (
        high_risk_tools
        and ({"LOW_STABILITY", "LOOP_RISK"} & failure_set)
        and not auto_readiness_eligible
    ):
        return "very_high"

    if risk_level == "high":
        return "high"

    if (
        high_risk_tools
        or suggested_rounds and suggested_rounds >= 5
        or "REGRESSION" in failure_set
        or patch_preview_eligible and len(tools) > 1
    ):
        return "high"

    if risk_level == "medium" or 1 <= len(tools) <= 3:
        return "medium"

    if risk_level == "low" and mode == "quick" and not tools:
        return "low"

    if risk_level == "low":
        return "medium" if tools else "low"

    return "unknown"


def _is_high_risk_tool(tool: dict[str, Any]) -> bool:
    name = str(tool.get("name") or "").casefold()
    category = str(tool.get("category") or "").casefold()
    side_effect = str(tool.get("side_effect_level") or "").casefold()
    risk = str(tool.get("risk_level") or "").casefold()
    return (
        risk == "high"
        or category in HIGH_RISK_TOOL_CATEGORIES
        or side_effect in HIGH_RISK_SIDE_EFFECTS
        or any(token in name for token in ("shell", "code_runner", "test_runner", "browser", "writer"))
    )
