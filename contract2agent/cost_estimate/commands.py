from __future__ import annotations

from contract2agent.cost_estimate.models import BudgetGuardrails


def recommended_command_for_mode(
    *,
    mode: str,
    risk_level: str,
    guardrails: BudgetGuardrails,
    auto_allowed: bool,
) -> str:
    if mode == "quick":
        return "agentdoctor quick"
    if mode == "auto" and auto_allowed:
        max_rounds = guardrails.max_auto_iterations or guardrails.max_rounds or 4
        max_patches = guardrails.max_patch_attempts or 2
        max_time = guardrails.max_runtime_minutes or 30
        return (
            "agentdoctor auto --target-confidence 0.85 "
            f"--max-rounds {max_rounds} --max-time-minutes {max_time} "
            f"--max-patches {max_patches} --review on-fail"
        )
    rounds = guardrails.max_rounds or (5 if risk_level == "high" else 3)
    review = "each-round" if risk_level == "high" else "on-fail"
    return f"agentdoctor deep --rounds {rounds} --review {review}"


def missing_triage_command() -> str:
    return "agentdoctor triage --include-cost"
