from __future__ import annotations

from typing import Any

from contract2agent.cost_estimate.loader import BaselineMetadata, EvalMetadata
from contract2agent.cost_estimate.models import CostDriver


def generate_cost_drivers(
    *,
    mode: str,
    tools: list[dict[str, Any]],
    tags: list[str],
    failure_types: list[str],
    baseline: BaselineMetadata,
    eval_metadata: EvalMetadata,
) -> list[CostDriver]:
    drivers: list[CostDriver] = []
    tag_set = {tag.casefold() for tag in tags}
    tool_names = [str(tool.get("name") or "unknown_tool") for tool in tools]

    def add(
        driver_id: str,
        title: str,
        impact: str,
        reason: str,
        evidence: list[str] | None = None,
        guardrail: str | None = None,
    ) -> None:
        drivers.append(
            CostDriver(
                id=driver_id,
                title=title,
                impact=impact,
                reason=reason,
                evidence=evidence or [],
                suggested_guardrail=guardrail,
            )
        )

    if len(tools) > 1:
        add(
            "multiple_tools",
            "Multiple tools",
            "medium",
            "Multiple tools increase tool-use, tool-order, and tool-argument coverage.",
            [f"detected tools: {', '.join(tool_names)}"],
            "max_tool_calls_per_test",
        )
    high_tools = [name for name, tool in zip(tool_names, tools) if _is_high_risk_tool(tool)]
    if high_tools:
        add(
            "high_risk_tools",
            "High-risk tools",
            "high",
            "Write, execution, browser, or external tools increase validation and review burden.",
            high_tools,
            "require_human_review_for_high_risk",
        )
    unknown_tools = [
        name
        for name, tool in zip(tool_names, tools)
        if str(tool.get("category") or "unknown") == "unknown"
        or str(tool.get("side_effect_level") or "unknown") == "unknown"
        or not tool.get("description")
    ]
    if unknown_tools:
        add(
            "unknown_tool_side_effects",
            "Unknown tool side effects",
            "unknown",
            "Missing tool descriptions lower confidence and may hide latency or side effects.",
            unknown_tools,
            "require_tool_metadata",
        )
    if any(str(tool.get("category") or "") in {"web_search", "browser", "external_api"} for tool in tools):
        add(
            "external_read_tools",
            "External read tools",
            "medium",
            "Browser, search, and API reads can add external latency and source-grounding checks.",
            tool_names,
            "max_runtime_minutes",
        )
    if any(str(tool.get("side_effect_level") or "") == "external_write" for tool in tools):
        add(
            "external_write_review",
            "External write tools requiring review",
            "high",
            "External side effects should be mocked and reviewed during diagnosis.",
            tool_names,
            "require_human_review_for_high_risk",
        )
    if any(str(tool.get("category") or "") in {"shell_execution", "code_execution"} for tool in tools):
        add(
            "shell_or_code_execution",
            "Shell or code execution",
            "high",
            "Execution tools are slow-path and safety risks even when diagnosis uses static estimates.",
            tool_names,
            "stop_on_safety_risk",
        )
    if eval_metadata.llm_judge_detected:
        add(
            "llm_judge_scorers",
            "LLM judge scorers",
            "high",
            "LLM judge scorers can add an extra model call per judged test.",
            eval_metadata.scorer_types,
            "max_llm_calls",
        )
    if "LOW_STABILITY" in failure_types:
        add(
            "repeated_stability_runs",
            "Repeated stability runs",
            "high",
            "Stability risks often require repeated validation runs to confirm variance.",
            ["LOW_STABILITY"],
            "max_repeated_runs",
        )
    if "REGRESSION" in failure_types:
        add(
            "regression_comparison",
            "Regression comparison",
            "high",
            "Regression checks require baseline comparison and can expand validation coverage.",
            ["regression tag or failure risk"],
            "stop_on_regression",
        )
    if mode == "auto":
        add(
            "auto_repair_iterations",
            "Auto repair iterations",
            "high",
            "Auto mode can add repair planning, patch proposal, validation, and regression loops.",
            [mode],
            "max_auto_iterations",
        )
    if {"source_grounding", "hallucination"} & tag_set:
        add(
            "source_grounding_validation",
            "Source-grounding validation",
            "medium",
            "Grounding checks may need document reads, citation checks, and scorer review.",
            sorted({"source_grounding", "hallucination"} & tag_set),
            "focus_source_grounding_subset",
        )
    if not baseline.exists:
        add(
            "no_baseline_found",
            "No baseline found",
            "medium",
            "Regression cost cannot be refined without a baseline or historical run context.",
            ["baseline missing"],
            "compare_baseline",
        )
    if "output_schema" in tag_set:
        add(
            "output_schema_validation",
            "Output schema validation",
            "low",
            "Schema validation is cheap, but auto repair can rerun schema checks repeatedly.",
            ["output_schema"],
            "run_output_schema_focus_first",
        )
    if {"safety", "permission_boundary"} & tag_set:
        add(
            "safety_permission_tests",
            "Safety and permission-boundary tests",
            "high",
            "Safety checks add review burden and should stop unsafe auto behavior.",
            sorted({"safety", "permission_boundary"} & tag_set),
            "stop_on_safety_risk",
        )
    return _dedupe_drivers(drivers)


def generate_cost_risks(drivers: list[CostDriver], failure_types: list[str]) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []
    for driver in drivers:
        if driver.impact in {"high", "unknown"}:
            risks.append(
                {
                    "id": driver.id,
                    "impact": driver.impact,
                    "reason": driver.reason,
                }
            )
    if "SCORER_UNCERTAIN" in failure_types:
        risks.append(
            {
                "id": "scorer_uncertain",
                "impact": "medium",
                "reason": "Scorer uncertainty may require human review before repair.",
            }
        )
    return risks


def _is_high_risk_tool(tool: dict[str, Any]) -> bool:
    return (
        str(tool.get("risk_level") or "").casefold() == "high"
        or str(tool.get("side_effect_level") or "").casefold()
        in {"write_local", "external_write", "destructive"}
        or str(tool.get("category") or "").casefold()
        in {"shell_execution", "code_execution", "browser", "filesystem_write"}
    )


def _dedupe_drivers(drivers: list[CostDriver]) -> list[CostDriver]:
    seen: set[str] = set()
    result: list[CostDriver] = []
    for driver in drivers:
        if driver.id in seen:
            continue
        seen.add(driver.id)
        result.append(driver)
    return result
