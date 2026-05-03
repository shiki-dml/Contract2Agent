from __future__ import annotations

from typing import Any

from contract2agent.cost_estimate.commands import recommended_command_for_mode
from contract2agent.cost_estimate.loader import EvalMetadata
from contract2agent.cost_estimate.llm_calls import estimate_llm_call_range
from contract2agent.cost_estimate.models import BudgetGuardrails, ModeCostComparison, to_plain_data
from contract2agent.cost_estimate.review import estimate_review_burden
from contract2agent.cost_estimate.test_count import estimate_test_count_range
from contract2agent.cost_estimate.tool_calls import estimate_tool_call_range


def generate_mode_comparison(
    *,
    recommended_mode: str,
    risk_level: str,
    tools: list[dict[str, Any]],
    tags: list[str],
    eval_metadata: EvalMetadata,
    failure_types: list[str],
    guardrails: BudgetGuardrails,
    budget_profile: str,
) -> list[ModeCostComparison]:
    comparisons: list[ModeCostComparison] = []
    for mode in ("quick", "deep", "auto"):
        rounds = _rounds_for_mode(mode, risk_level, guardrails)
        auto_iterations = [1, guardrails.max_auto_iterations or 4] if mode == "auto" else [0, 0]
        patch_attempts = [1, guardrails.max_patch_attempts or 2] if mode == "auto" else [0, 0]
        test_range = estimate_test_count_range(
            mode=mode,
            risk_level=risk_level,
            rounds=rounds,
            tags=tags,
            eval_case_count=eval_metadata.case_count,
            repeated_runs=guardrails.max_repeated_runs or 1,
            budget_profile=budget_profile,
            max_tests=guardrails.max_tests,
        )
        llm_range, _ = estimate_llm_call_range(
            mode=mode,
            test_count_range=test_range,
            eval_metadata=eval_metadata,
            tags=tags,
            auto_iterations=auto_iterations,
            patch_attempts=patch_attempts,
            repeated_runs=guardrails.max_repeated_runs or 1,
            max_llm_calls=guardrails.max_llm_calls,
        )
        tool_range = estimate_tool_call_range(
            tools=tools,
            test_count_range=test_range,
            tags=tags,
            rounds=rounds,
            max_tool_calls=guardrails.max_tool_calls,
        )
        review = estimate_review_burden(
            mode=mode,
            risk_level=risk_level,
            tools=tools,
            failure_types=failure_types,
            patch_preview_required=mode == "auto",
        )
        comparisons.append(
            ModeCostComparison(
                mode=mode,
                estimated_rounds=[1, rounds] if mode == "auto" else rounds,
                estimated_test_count_range=test_range,
                estimated_llm_call_range=llm_range,
                estimated_tool_call_range=to_plain_data(tool_range),
                runtime_level=_runtime_level(mode, risk_level),
                review_burden_level=review.review_burden_level,
                risk_level=_mode_risk(mode, risk_level),
                best_for=_best_for(mode),
                limitations=_limitations(mode),
                recommended=mode == recommended_mode,
                command=recommended_command_for_mode(
                    mode=mode,
                    risk_level=risk_level,
                    guardrails=guardrails,
                    auto_allowed=mode == recommended_mode == "auto",
                ),
            )
        )
    return comparisons


def _rounds_for_mode(mode: str, risk_level: str, guardrails: BudgetGuardrails) -> int:
    if mode == "quick":
        return 1
    if mode == "auto":
        return guardrails.max_auto_iterations or 6
    return guardrails.max_rounds or (5 if risk_level == "high" else 3)


def _runtime_level(mode: str, risk_level: str) -> str:
    if mode == "quick":
        return "short"
    if mode == "auto":
        return "very_long"
    return "long" if risk_level == "high" else "medium"


def _mode_risk(mode: str, risk_level: str) -> str:
    if mode == "auto":
        return "high"
    if mode == "quick" and risk_level == "high":
        return "coverage_risk"
    return risk_level


def _best_for(mode: str) -> str:
    if mode == "quick":
        return "fast smoke diagnosis"
    if mode == "deep":
        return "reliable diagnosis with broader coverage"
    return "iterative repair only after readiness checks pass"


def _limitations(mode: str) -> str:
    if mode == "quick":
        return "low coverage and limited regression signal"
    if mode == "deep":
        return "slower than quick and still not an auto repair loop"
    return "high overfitting, runtime, patch, and validation risk"
