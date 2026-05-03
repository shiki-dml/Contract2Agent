from __future__ import annotations

from typing import Any

from contract2agent.cost_estimate.models import HumanReviewEstimate


def estimate_review_burden(
    *,
    mode: str,
    risk_level: str,
    tools: list[dict[str, Any]],
    failure_types: list[str],
    patch_preview_required: bool,
) -> HumanReviewEstimate:
    triggers: list[str] = []
    if any(_is_high_risk_tool(tool) for tool in tools):
        triggers.append("high risk tools")
    if any(str(tool.get("side_effect_level") or "") == "external_write" for tool in tools):
        triggers.append("external write tools")
    if any(str(tool.get("category") or "") in {"shell_execution", "code_execution"} for tool in tools):
        triggers.append("shell/code execution")
    if "SAFETY_RISK" in failure_types:
        triggers.append("safety tests")
    if "FORBIDDEN_TOOL_CALL" in failure_types:
        triggers.append("forbidden tool tests")
    if "REGRESSION" in failure_types:
        triggers.append("regression checks")
    if patch_preview_required:
        triggers.append("patch preview required")
    if mode == "auto":
        triggers.append("auto mode")
    if "SCORER_UNCERTAIN" in failure_types:
        triggers.append("SCORER_UNCERTAIN risk")
    if "UNKNOWN" in failure_types:
        triggers.append("UNKNOWN risk")

    if mode == "quick" and risk_level == "low" and not triggers:
        return HumanReviewEstimate(
            count_range=[0, 1],
            review_burden_level="low",
            triggers=[],
            review_policy="on-fail",
            explanation="Quick low-risk diagnosis should need little manual review unless a failure appears.",
        )

    if mode == "auto" or risk_level == "high" or {"SAFETY_RISK", "FORBIDDEN_TOOL_CALL"} & set(failure_types):
        return HumanReviewEstimate(
            count_range=[2, 12 if mode == "auto" else 8],
            review_burden_level="high",
            triggers=_dedupe(triggers),
            review_policy="each-round" if risk_level == "high" else "on-fail",
            explanation="High-risk tools, safety checks, or auto loops require review before trusting repair or diagnosis results.",
        )

    return HumanReviewEstimate(
        count_range=[0, 3],
        review_burden_level="medium",
        triggers=_dedupe(triggers),
        review_policy="on-fail",
        explanation="Deep diagnosis may produce findings that need human triage before repair.",
    )


def _is_high_risk_tool(tool: dict[str, Any]) -> bool:
    return (
        str(tool.get("risk_level") or "").casefold() == "high"
        or str(tool.get("side_effect_level") or "").casefold()
        in {"write_local", "external_write", "destructive"}
    )


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
