from __future__ import annotations

from contract2agent.cost_estimate.models import BudgetGuardrails, CostEstimateOptions


def generate_budget_guardrails(
    *,
    mode: str,
    risk_level: str,
    budget_profile: str,
    estimated_rounds: int,
    options: CostEstimateOptions,
) -> BudgetGuardrails:
    profile = "custom" if options.has_budget_overrides() else budget_profile
    guardrails = _profile_defaults(profile, mode, risk_level, estimated_rounds)

    _override(guardrails, "max_rounds", options.max_rounds)
    _override(guardrails, "max_tests", options.max_tests)
    _override(guardrails, "max_runtime_minutes", options.max_runtime_minutes)
    _override(guardrails, "max_llm_calls", options.max_llm_calls)
    _override(guardrails, "max_tool_calls", options.max_tool_calls)
    _override(guardrails, "max_tool_calls_per_test", options.max_tool_calls_per_test)
    _override(guardrails, "max_repeated_runs", options.max_repeated_runs)
    _override(guardrails, "max_auto_iterations", options.max_auto_iterations)
    _override(guardrails, "max_patch_attempts", options.max_patch_attempts)
    if mode == "auto":
        guardrails.require_patch_preview = True
    if risk_level == "high":
        guardrails.require_human_review_for_high_risk = True
    return guardrails


def budget_recommendation(
    *,
    mode: str,
    risk_level: str,
    guardrails: BudgetGuardrails,
    auto_recommended: bool,
) -> str:
    if mode == "auto" and not auto_recommended:
        return (
            f"Run deep first with {guardrails.max_rounds or 3} rounds and "
            f"max {guardrails.max_tests or 24} tests; avoid auto until blockers clear."
        )
    if risk_level == "high":
        return (
            f"Use deep mode with review and max {guardrails.max_tests or 60} tests; "
            "keep safety, regression, and loop-risk stops enabled."
        )
    if mode == "quick":
        return f"Use quick mode with max {guardrails.max_tests or 8} tests."
    return (
        f"Use balanced deep mode with {guardrails.max_rounds or 3} rounds and "
        f"max {guardrails.max_tests or 24} tests."
    )


def _profile_defaults(
    profile: str,
    mode: str,
    risk_level: str,
    estimated_rounds: int,
) -> BudgetGuardrails:
    if profile == "conservative":
        rounds = 1 if mode == "quick" else min(estimated_rounds, 2)
        return BudgetGuardrails(
            max_rounds=rounds,
            max_tests=8 if mode == "quick" else 16,
            max_runtime_minutes=10,
            max_llm_calls=25,
            max_tool_calls=40,
            max_tool_calls_per_test=3,
            max_repeated_runs=1,
            max_auto_iterations=0 if mode != "auto" else 1,
            max_patch_attempts=0 if mode != "auto" else 1,
            min_confidence_improvement=0.05,
            require_patch_preview=mode == "auto",
            require_human_review_for_high_risk=True,
        )
    if profile == "thorough":
        return BudgetGuardrails(
            max_rounds=max(estimated_rounds, 5 if risk_level == "high" else 3),
            max_tests=90 if mode == "auto" else 75 if risk_level == "high" else 45,
            max_runtime_minutes=60,
            max_llm_calls=160,
            max_tool_calls=240,
            max_tool_calls_per_test=8,
            max_repeated_runs=5,
            max_auto_iterations=6 if mode == "auto" else 0,
            max_patch_attempts=3 if mode == "auto" else 1,
            min_confidence_improvement=0.02,
            require_patch_preview=mode == "auto",
            require_human_review_for_high_risk=True,
        )
    return BudgetGuardrails(
        max_rounds=estimated_rounds,
        max_tests=80 if mode == "auto" else 60 if risk_level == "high" else 24,
        max_runtime_minutes=30,
        max_llm_calls=80,
        max_tool_calls=120,
        max_tool_calls_per_test=5,
        max_repeated_runs=3,
        max_auto_iterations=4 if mode == "auto" else 0,
        max_patch_attempts=2 if mode == "auto" else 1,
        min_confidence_improvement=0.03,
        require_patch_preview=mode == "auto",
        require_human_review_for_high_risk=risk_level == "high",
    )


def _override(guardrails: BudgetGuardrails, attr: str, value: int | None) -> None:
    if value is not None:
        setattr(guardrails, attr, value)
