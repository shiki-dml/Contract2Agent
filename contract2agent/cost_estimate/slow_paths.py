from __future__ import annotations

from typing import Any

from contract2agent.cost_estimate.models import SlowPathPrediction


def generate_slow_path_predictions(
    *,
    mode: str,
    tools: list[dict[str, Any]],
    tags: list[str],
    failure_types: list[str],
    baseline_exists: bool,
) -> list[SlowPathPrediction]:
    predictions: list[SlowPathPrediction] = []
    tag_set = {tag.casefold() for tag in tags}
    tool_names = [str(tool.get("name") or "unknown_tool") for tool in tools]

    def add(
        prediction_id: str,
        title: str,
        reason: str,
        impact: str,
        related_tools: list[str] | None = None,
        related_failure_types: list[str] | None = None,
        guardrail: str | None = None,
    ) -> None:
        predictions.append(
            SlowPathPrediction(
                id=prediction_id,
                title=title,
                reason=reason,
                likely_impact=impact,
                related_tools=related_tools or [],
                related_failure_types=related_failure_types or [],
                suggested_guardrail=guardrail,
            )
        )

    if {"source_grounding", "hallucination"} & tag_set:
        add(
            "source_grounding",
            "Source-grounding validation",
            "Source-grounding tests may require document reads plus citation or evidence checks.",
            "medium",
            _tools_by_category(tools, {"document_reading", "retrieval", "filesystem_read"}),
            ["HALLUCINATION_RISK"],
            "focus_source_grounding_subset",
        )
    if any(str(tool.get("category") or "") in {"shell_execution", "code_execution"} for tool in tools):
        add(
            "coding_execution",
            "Coding or execution tests",
            "Coding tests may require shell, code runner, or test runner validation.",
            "high",
            tool_names,
            ["REGRESSION", "SAFETY_RISK"],
            "max_runtime_minutes",
        )
    if any(str(tool.get("category") or "") in {"browser", "web_search"} for tool in tools):
        add(
            "browser_or_search",
            "Browser or search latency",
            "Browser and web-search tools can add external latency and brittle environment behavior.",
            "high",
            _tools_by_category(tools, {"browser", "web_search"}),
            ["HALLUCINATION_RISK"],
            "max_runtime_minutes",
        )
    if "LOW_STABILITY" in failure_types:
        add(
            "stability_repeats",
            "Repeated stability validation",
            "Stability tests require repeated runs, which multiplies agent and scorer calls.",
            "high",
            tool_names,
            ["LOW_STABILITY"],
            "max_repeated_runs",
        )
    if baseline_exists or "REGRESSION" in failure_types:
        add(
            "regression_replay",
            "Regression comparison",
            "Regression comparison requires baseline replay or selected baseline checks.",
            "medium",
            tool_names,
            ["REGRESSION"],
            "stop_on_regression",
        )
    if mode == "auto":
        add(
            "auto_repair_loop",
            "Auto repair loop",
            "Auto repair requires patch proposals plus validation and regression loops.",
            "high",
            tool_names,
            failure_types,
            "max_auto_iterations",
        )
    if "TOOL_ARGUMENT_ERROR" in failure_types:
        add(
            "tool_argument_retries",
            "Tool argument retry path",
            "Tool argument failures may trigger retries, tool errors, or fallback checks.",
            "medium",
            tool_names,
            ["TOOL_ARGUMENT_ERROR"],
            "max_tool_retries",
        )
    if "LOOP_RISK" in failure_types:
        add(
            "loop_risk",
            "Loop-risk tool calls",
            "Loop risk may cause repeated tool calls unless max-step and stop conditions are active.",
            "high",
            tool_names,
            ["LOOP_RISK"],
            "max_tool_calls_per_test",
        )
    return _dedupe(predictions)


def _tools_by_category(tools: list[dict[str, Any]], categories: set[str]) -> list[str]:
    return [
        str(tool.get("name") or "unknown_tool")
        for tool in tools
        if str(tool.get("category") or "") in categories
    ]


def _dedupe(predictions: list[SlowPathPrediction]) -> list[SlowPathPrediction]:
    seen: set[str] = set()
    result: list[SlowPathPrediction] = []
    for prediction in predictions:
        if prediction.id in seen:
            continue
        seen.add(prediction.id)
        result.append(prediction)
    return result
