from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contract2agent.cost_estimate.auto_plan import (
    generate_auto_cost_plan,
    generate_patch_preview_cost_context,
)
from contract2agent.cost_estimate.commands import (
    missing_triage_command,
    recommended_command_for_mode,
)
from contract2agent.cost_estimate.complexity import classify_complexity
from contract2agent.cost_estimate.cost_drivers import (
    generate_cost_drivers,
    generate_cost_risks,
)
from contract2agent.cost_estimate.failure_cost import (
    extract_failure_types,
    map_failure_type_cost_risks,
)
from contract2agent.cost_estimate.guardrails import (
    budget_recommendation,
    generate_budget_guardrails,
)
from contract2agent.cost_estimate.llm_calls import estimate_llm_call_range
from contract2agent.cost_estimate.loader import CostEstimateInputs, load_cost_estimate_inputs
from contract2agent.cost_estimate.mode_comparison import generate_mode_comparison
from contract2agent.cost_estimate.models import (
    BUDGET_PROFILES,
    CostEstimateOptions,
    EstimatedDiagnosticCost,
    BaselineCostContext,
    STATIC_ESTIMATE_NOTE,
    to_plain_data,
)
from contract2agent.cost_estimate.review import estimate_review_burden
from contract2agent.cost_estimate.runtime import estimate_runtime_range
from contract2agent.cost_estimate.slow_paths import generate_slow_path_predictions
from contract2agent.cost_estimate.suggestions import generate_optimization_suggestions
from contract2agent.cost_estimate.test_count import estimate_test_count_range
from contract2agent.cost_estimate.tool_calls import estimate_tool_call_range


def build_cost_estimate(
    options: CostEstimateOptions | None = None,
    *,
    cwd: Path | None = None,
) -> EstimatedDiagnosticCost:
    options = options or CostEstimateOptions()
    cwd = (cwd or Path.cwd()).resolve()
    now = options.now or datetime.now(timezone.utc).astimezone()
    inputs = load_cost_estimate_inputs(
        options.from_triage,
        cwd=cwd,
        project_root_override=options.project_root,
    )
    warnings = list(inputs.warnings)

    budget_profile = _normalize_budget_profile(options.budget_profile, warnings)
    effective_budget = "custom" if options.has_budget_overrides() else budget_profile
    mode = _select_mode(options, inputs)
    risk_level = _risk_level(inputs.triage)
    tools = _tools(inputs.triage)
    tags = _tags(inputs)
    scorer_unknown = inputs.eval_metadata.deterministic_scorers_only is None
    failure_types = extract_failure_types(
        triage=inputs.triage,
        tags=tags,
        tools=tools,
        scorer_unknown=scorer_unknown,
    )
    estimated_rounds_int = _estimated_rounds_int(mode, risk_level, inputs.triage, options)

    guardrails = generate_budget_guardrails(
        mode=mode,
        risk_level=risk_level,
        budget_profile=budget_profile,
        estimated_rounds=estimated_rounds_int,
        options=options,
    )
    repeated_runs = guardrails.max_repeated_runs or 1
    auto_iterations = [1, guardrails.max_auto_iterations or estimated_rounds_int] if mode == "auto" else [0, 0]
    patch_attempts = [1, guardrails.max_patch_attempts or 2] if mode == "auto" else [0, 0]

    test_range = estimate_test_count_range(
        mode=mode,
        risk_level=risk_level,
        rounds=estimated_rounds_int,
        tags=tags,
        eval_case_count=inputs.eval_metadata.case_count,
        repeated_runs=repeated_runs,
        budget_profile=budget_profile,
        max_tests=guardrails.max_tests,
    )
    llm_range, llm_warnings = estimate_llm_call_range(
        mode=mode,
        test_count_range=test_range,
        eval_metadata=inputs.eval_metadata,
        tags=tags,
        auto_iterations=auto_iterations,
        patch_attempts=patch_attempts,
        repeated_runs=repeated_runs,
        max_llm_calls=guardrails.max_llm_calls,
    )
    warnings.extend(llm_warnings)
    tool_range = estimate_tool_call_range(
        tools=tools,
        test_count_range=test_range,
        tags=tags,
        rounds=estimated_rounds_int,
        max_tool_calls=guardrails.max_tool_calls,
    )
    complexity = classify_complexity(
        mode=mode,
        risk_level=risk_level,
        tools=tools,
        suggested_rounds=estimated_rounds_int,
        failure_types=failure_types,
        patch_preview_eligible=_patch_preview_eligible(inputs.triage),
        auto_readiness_eligible=_auto_readiness_eligible(inputs.triage),
        has_eval_metadata=inputs.eval_metadata.exists,
    )
    runtime = estimate_runtime_range(
        mode=mode,
        complexity_level=complexity,
        baseline=inputs.baseline_metadata,
    )
    review = estimate_review_burden(
        mode=mode,
        risk_level=risk_level,
        tools=tools,
        failure_types=failure_types,
        patch_preview_required=guardrails.require_patch_preview,
    )
    auto_plan = generate_auto_cost_plan(
        mode=mode,
        triage=inputs.triage,
        risk_level=risk_level,
        failure_types=failure_types,
        baseline=inputs.baseline_metadata,
        eval_metadata=inputs.eval_metadata,
        guardrails=guardrails,
    )
    recommended_mode = _recommended_mode(
        mode=mode,
        risk_level=risk_level,
        inputs=inputs,
        auto_recommended=auto_plan.auto_recommended,
    )
    drivers = generate_cost_drivers(
        mode=mode,
        tools=tools,
        tags=tags,
        failure_types=failure_types,
        baseline=inputs.baseline_metadata,
        eval_metadata=inputs.eval_metadata,
    )
    failure_risks = map_failure_type_cost_risks(failure_types)
    patch_context = generate_patch_preview_cost_context(
        mode=mode,
        triage=inputs.triage,
        failure_types=failure_types,
        guardrails=guardrails,
        baseline_exists=inputs.baseline_metadata.exists,
    )
    baseline_context = _baseline_context(inputs)
    mode_comparison = generate_mode_comparison(
        recommended_mode=recommended_mode,
        risk_level=risk_level,
        tools=tools,
        tags=tags,
        eval_metadata=inputs.eval_metadata,
        failure_types=failure_types,
        guardrails=guardrails,
        budget_profile=budget_profile,
    )
    has_high_risk_tools = any(_is_high_risk_tool(tool) for tool in tools)
    suggestions = generate_optimization_suggestions(
        mode=mode,
        recommended_mode=recommended_mode,
        failure_types=failure_types,
        baseline=inputs.baseline_metadata,
        eval_metadata=inputs.eval_metadata,
        has_high_risk_tools=has_high_risk_tools,
    )
    command = (
        missing_triage_command()
        if inputs.triage_missing or recommended_mode == "unknown"
        else recommended_command_for_mode(
            mode=recommended_mode,
            risk_level=risk_level,
            guardrails=guardrails,
            auto_allowed=auto_plan.auto_recommended,
        )
    )
    if inputs.triage_missing:
        test_range = [0, 0] if mode == "unknown" else test_range
        llm_range = [0, 0] if mode == "unknown" else llm_range
        tool_range.total = [0, 0] if mode == "unknown" else tool_range.total
    if inputs.baseline_metadata.warning:
        warnings.append(inputs.baseline_metadata.warning)
    if mode == "auto" and not auto_plan.auto_recommended:
        warnings.append(auto_plan.reason)
    warnings.append(
        "Some diagnostic budget guardrails are static recommendations; existing run commands may not enforce every reported limit."
    )

    estimate = EstimatedDiagnosticCost(
        cost_estimate_id=now.strftime("cost_%Y%m%d_%H%M%S"),
        created_at=now.replace(microsecond=0).isoformat(),
        source_triage_id=inputs.source_triage_id,
        source_triage_path=str(inputs.triage_path) if inputs.triage_path else None,
        project_root=str(inputs.project_root),
        mode=mode,
        budget_profile=effective_budget,
        confidence=_estimate_confidence(inputs, tools, mode),
        complexity_level=complexity,
        estimated_rounds=[1, estimated_rounds_int] if mode == "auto" else estimated_rounds_int if mode != "unknown" else "unknown",
        estimated_test_count_range=test_range,
        estimated_llm_call_range=llm_range,
        estimated_tool_call_range=tool_range,
        estimated_runtime_range=runtime,
        estimated_human_review_items=review,
        estimated_patch_attempts=patch_attempts,
        estimated_auto_iterations=auto_iterations,
        cost_drivers=drivers,
        cost_risks=generate_cost_risks(drivers, failure_types),
        failure_type_cost_risks=failure_risks,
        budget_recommendation=budget_recommendation(
            mode=mode,
            risk_level=risk_level,
            guardrails=guardrails,
            auto_recommended=auto_plan.auto_recommended,
        ),
        budget_guardrails=guardrails,
        mode_comparison=mode_comparison,
        slow_path_predictions=generate_slow_path_predictions(
            mode=mode,
            tools=tools,
            tags=tags,
            failure_types=failure_types,
            baseline_exists=inputs.baseline_metadata.exists,
        ),
        review_burden=to_plain_data(review),
        auto_cost_plan=auto_plan,
        baseline_cost_context=baseline_context,
        patch_preview_cost_context=patch_context,
        optimization_suggestions=suggestions,
        recommended_command=command,
        assumptions=_assumptions(inputs, tags),
        warnings=_dedupe(warnings),
        note=STATIC_ESTIMATE_NOTE,
    )
    return estimate


def _normalize_budget_profile(value: str, warnings: list[str]) -> str:
    normalized = value.casefold()
    if normalized in BUDGET_PROFILES - {"custom"}:
        return normalized
    warnings.append(f"Unknown budget profile {value!r}; using balanced.")
    return "balanced"


def _select_mode(options: CostEstimateOptions, inputs: CostEstimateInputs) -> str:
    if options.mode:
        normalized = options.mode.casefold()
        return normalized if normalized in {"quick", "deep", "auto"} else "unknown"
    triage = inputs.triage or {}
    recommendation = _mapping(triage.get("recommendation"))
    if recommendation.get("recommended_mode"):
        return str(recommendation["recommended_mode"])
    round_plan = _mapping(triage.get("suggested_round_plan"))
    if round_plan.get("mode"):
        return str(round_plan["mode"])
    return "unknown"


def _recommended_mode(
    *,
    mode: str,
    risk_level: str,
    inputs: CostEstimateInputs,
    auto_recommended: bool,
) -> str:
    if inputs.triage_missing:
        return "unknown"
    if mode == "auto" and not auto_recommended:
        return "deep"
    if mode == "unknown":
        return "deep" if risk_level != "unknown" else "unknown"
    return mode


def _risk_level(triage: dict[str, Any] | None) -> str:
    risk = _mapping((triage or {}).get("risk_assessment"))
    value = str(risk.get("risk_level") or "unknown")
    return value if value in {"low", "medium", "high", "unknown"} else "unknown"


def _tools(triage: dict[str, Any] | None) -> list[dict[str, Any]]:
    capabilities = _mapping((triage or {}).get("detected_capabilities"))
    tools = capabilities.get("tools")
    return [dict(tool) for tool in tools if isinstance(tool, dict)] if isinstance(tools, list) else []


def _tags(inputs: CostEstimateInputs) -> list[str]:
    triage = inputs.triage or {}
    tags: list[str] = [str(tag) for tag in triage.get("suggested_test_tags") or []]
    coverage = _mapping(triage.get("eval_coverage"))
    tags.extend(str(tag) for tag in coverage.get("detected_tags") or [])
    tags.extend(str(tag) for tag in coverage.get("covered_areas") or [])
    round_plan = _mapping(triage.get("suggested_round_plan"))
    for focus in round_plan.get("round_focuses") or []:
        if isinstance(focus, dict):
            tags.extend(str(tag) for tag in focus.get("suggested_tags") or [])
    tags.extend(inputs.eval_metadata.tags)
    return _dedupe(tags)


def _estimated_rounds_int(
    mode: str,
    risk_level: str,
    triage: dict[str, Any] | None,
    options: CostEstimateOptions,
) -> int:
    if mode == "quick":
        default = 1
    elif mode == "auto":
        default = options.max_auto_iterations or options.max_rounds or 6
    else:
        round_plan = _mapping((triage or {}).get("suggested_round_plan"))
        default = int(round_plan.get("rounds") or (5 if risk_level == "high" else 3))
    if options.max_rounds is not None and mode != "auto":
        default = min(default, options.max_rounds)
    return max(1, int(default))


def _estimate_confidence(
    inputs: CostEstimateInputs,
    tools: list[dict[str, Any]],
    mode: str,
) -> str:
    if inputs.triage_missing:
        return "unknown"
    score = 3
    if not inputs.eval_metadata.exists:
        score -= 1
    if not inputs.baseline_metadata.exists:
        score -= 1
    if any(_tool_metadata_missing(tool) for tool in tools):
        score -= 1
    if mode == "auto" and not inputs.baseline_metadata.historical_cost_available:
        score -= 1
    if inputs.baseline_metadata.historical_cost_available:
        score += 1
    if score >= 3:
        return "high"
    if score == 2:
        return "medium"
    return "low"


def _baseline_context(inputs: CostEstimateInputs) -> BaselineCostContext:
    baseline = inputs.baseline_metadata
    if baseline.exists:
        return BaselineCostContext(
            baseline_exists=True,
            baseline_path=baseline.path,
            historical_cost_available=baseline.historical_cost_available,
            historical_cost_used=baseline.historical_cost_available,
            previous_avg_runtime=baseline.avg_runtime_seconds,
            previous_slowest_tests=baseline.slowest_tests,
            previous_slowest_failure_types=baseline.slowest_failure_types,
            baseline_warning=baseline.warning,
            regression_check_cost=(
                "historical runtime metadata can refine broad regression estimates"
                if baseline.historical_cost_available
                else "baseline can guide regression selection but not runtime"
            ),
        )
    return BaselineCostContext(
        baseline_exists=False,
        baseline_path=baseline.path,
        historical_cost_available=False,
        historical_cost_used=False,
        baseline_warning=baseline.warning or "No baseline found. Regression cost estimate is limited.",
        regression_check_cost="limited until a reliable deep-run baseline is saved",
    )


def _assumptions(inputs: CostEstimateInputs, tags: list[str]) -> list[str]:
    assumptions = [
        "No agents, tests, tools, shell tools, browser tools, or LLM APIs were executed.",
        "Ranges are deterministic static estimates derived from triage, eval metadata, tool metadata, baseline metadata, and budget options.",
        STATIC_ESTIMATE_NOTE,
    ]
    if tags:
        assumptions.append("Suggested test tags are used as coverage and cost signals.")
    if not inputs.eval_metadata.exists:
        assumptions.append("Eval metadata is missing, so test count ranges use mode defaults and triage tags.")
    if not inputs.baseline_metadata.exists:
        assumptions.append("Baseline history is missing, so regression and runtime estimates have lower confidence.")
    return assumptions


def _patch_preview_eligible(triage: dict[str, Any] | None) -> bool:
    return bool(_mapping((triage or {}).get("patch_preview_readiness")).get("eligible"))


def _auto_readiness_eligible(triage: dict[str, Any] | None) -> bool | None:
    if triage is None:
        return None
    return bool(_mapping(triage.get("auto_readiness")).get("eligible"))


def _is_high_risk_tool(tool: dict[str, Any]) -> bool:
    return (
        str(tool.get("risk_level") or "").casefold() == "high"
        or str(tool.get("side_effect_level") or "").casefold()
        in {"write_local", "external_write", "destructive"}
        or str(tool.get("category") or "").casefold()
        in {"shell_execution", "code_execution", "browser", "filesystem_write"}
    )


def _tool_metadata_missing(tool: dict[str, Any]) -> bool:
    return (
        not tool.get("description")
        or str(tool.get("category") or "unknown") == "unknown"
        or str(tool.get("side_effect_level") or "unknown") == "unknown"
    )


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
