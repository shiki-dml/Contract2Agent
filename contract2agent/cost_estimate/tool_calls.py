from __future__ import annotations

from typing import Any

from contract2agent.cost_estimate.models import ToolCallEstimate


LOW_TOOL_CATEGORIES = {"formatting", "validation"}
READ_TOOL_CATEGORIES = {"document_reading", "filesystem_read", "retrieval", "memory"}
EXTERNAL_READ_CATEGORIES = {"web_search", "browser", "external_api"}
WRITE_TOOL_CATEGORIES = {"filesystem_write", "database", "communication", "calendar", "email"}
EXECUTION_TOOL_CATEGORIES = {"shell_execution", "code_execution"}


def estimate_tool_call_range(
    *,
    tools: list[dict[str, Any]],
    test_count_range: list[int],
    tags: list[str],
    rounds: int,
    max_tool_calls: int | None,
) -> ToolCallEstimate:
    if not tools:
        return ToolCallEstimate(total=[0, 0], by_tool={}, confidence="high")

    by_tool: dict[str, list[int]] = {}
    total_low = 0
    total_high = 0
    confidence = "medium"
    normalized_tags = {tag.casefold() for tag in tags}
    tool_test_low = max(1, test_count_range[0] // 3)
    tool_test_high = max(tool_test_low, test_count_range[1] // 2)
    if "tool_use" in normalized_tags or "tool_order" in normalized_tags:
        tool_test_high = max(tool_test_high, test_count_range[1])

    for tool in sorted(tools, key=lambda item: str(item.get("name") or "").casefold()):
        name = str(tool.get("name") or "unknown_tool")
        category = str(tool.get("category") or "unknown").casefold()
        side_effect = str(tool.get("side_effect_level") or "unknown").casefold()
        low_per, high_per = _per_relevant_test(category, side_effect, name)
        low = tool_test_low * low_per
        high = tool_test_high * high_per
        by_tool[name] = [low, high]
        total_low += low
        total_high += high
        if category == "unknown" or side_effect == "unknown" or not tool.get("description"):
            confidence = "low"

    if len(tools) > 1 and "tool_order" in normalized_tags:
        overhead = [len(tools) - 1, max(len(tools) - 1, (len(tools) - 1) * max(1, rounds))]
        by_tool["tool_order_overhead"] = overhead
        total_low += overhead[0]
        total_high += overhead[1]

    capped_total = _apply_cap([total_low, total_high], max_tool_calls)
    return ToolCallEstimate(total=capped_total, by_tool=by_tool, confidence=confidence)


def _per_relevant_test(category: str, side_effect: str, name: str) -> tuple[int, int]:
    lowered = name.casefold()
    if category in LOW_TOOL_CATEGORIES or lowered in {"formatter", "validator", "calculator"}:
        return 0, 1
    if category in READ_TOOL_CATEGORIES:
        return 1, 3
    if category in EXTERNAL_READ_CATEGORIES:
        return 1, 4
    if category in EXECUTION_TOOL_CATEGORIES or "shell" in lowered or "test_runner" in lowered:
        return 1, 4
    if category in WRITE_TOOL_CATEGORIES or side_effect in {"write_local", "external_write", "destructive"}:
        return 1, 3
    return 1, 3


def _apply_cap(values: list[int], cap: int | None) -> list[int]:
    low, high = values
    if cap is None:
        return [low, high]
    capped_high = min(high, cap)
    capped_low = min(low, capped_high)
    return [capped_low, capped_high]
