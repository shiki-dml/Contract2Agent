from __future__ import annotations

from typing import Any

from contract2agent.cost_estimate.loader import BaselineMetadata, EvalMetadata
from contract2agent.cost_estimate.models import (
    AutoCostPlan,
    BudgetGuardrails,
    PatchPreviewCostContext,
)


STOP_CONDITIONS = [
    "safety risk appears",
    "forbidden tool call appears",
    "regression introduced",
    "same failure type persists for 2 rounds",
    "confidence improvement below min threshold",
    "scorer uncertain dominates",
    "unknown failures dominate",
    "loop risk exceeds guardrail",
    "max patch attempts reached",
    "max runtime reached",
]


def generate_auto_cost_plan(
    *,
    mode: str,
    triage: dict[str, Any] | None,
    risk_level: str,
    failure_types: list[str],
    baseline: BaselineMetadata,
    eval_metadata: EvalMetadata,
    guardrails: BudgetGuardrails,
) -> AutoCostPlan:
    auto_readiness = _mapping(triage.get("auto_readiness")) if triage else {}
    patch_readiness = _mapping(triage.get("patch_preview_readiness")) if triage else {}
    blockers = list(str(item) for item in auto_readiness.get("blockers") or [])
    if not patch_readiness.get("eligible"):
        blockers.append("missing patch allowlist")
    if risk_level == "high":
        blockers.append("run deep first for high-risk agents")
    if {"SAFETY_RISK", "FORBIDDEN_TOOL_CALL"} & set(failure_types):
        blockers.append("safety or forbidden-tool risk requires review before auto")
    if triage is None:
        blockers.append("auto readiness is unknown")

    requested_auto = mode == "auto"
    eligible = bool(auto_readiness.get("eligible")) and not blockers
    auto_recommended = requested_auto and eligible
    max_iterations = guardrails.max_auto_iterations or (4 if requested_auto else 0)
    max_patch_attempts = guardrails.max_patch_attempts or (2 if requested_auto else 0)
    estimated_iterations = [1, max(1, max_iterations)] if requested_auto else [0, 0]
    estimated_patch_attempts = [1, max(1, max_patch_attempts)] if requested_auto else [0, 0]
    validation_runs = [estimated_patch_attempts[0], max(estimated_patch_attempts[1], estimated_iterations[1])]
    regression_checks = [1, 3] if requested_auto and baseline.exists else [0, 1 if requested_auto else 0]

    reason = (
        "Auto is within static readiness guardrails."
        if auto_recommended
        else "Auto is not recommended before a bounded deep run: " + "; ".join(_dedupe(blockers))
    )
    if not blockers and not requested_auto:
        reason = "Auto was evaluated but is not the default recommendation for pre-run cost control."

    return AutoCostPlan(
        auto_considered=True,
        auto_recommended=auto_recommended,
        reason=reason,
        target_confidence=0.85 if requested_auto else None,
        max_iterations=max_iterations,
        estimated_iterations=estimated_iterations,
        estimated_patch_attempts=estimated_patch_attempts,
        estimated_validation_runs=validation_runs,
        estimated_regression_checks=regression_checks,
        overfitting_risk=_overfitting_risk(requested_auto, baseline, eval_metadata, failure_types),
        stop_conditions=STOP_CONDITIONS,
        required_guardrails=[
            "require_patch_preview",
            "max_auto_iterations",
            "max_patch_attempts",
            "stop_on_safety_risk",
            "stop_on_forbidden_tool_call",
            "stop_on_regression",
            "stop_on_loop_risk",
        ],
        recommended_auto_command=(
            "agentdoctor auto --target-confidence 0.85 "
            f"--max-rounds {max_iterations} --max-patches {max_patch_attempts} --review on-fail"
            if auto_recommended
            else "Run agentdoctor deep first; do not enable auto until readiness blockers clear."
        ),
    )


def generate_patch_preview_cost_context(
    *,
    mode: str,
    triage: dict[str, Any] | None,
    failure_types: list[str],
    guardrails: BudgetGuardrails,
    baseline_exists: bool,
) -> PatchPreviewCostContext:
    patch_readiness = _mapping(triage.get("patch_preview_readiness")) if triage else {}
    enabled = bool(patch_readiness.get("eligible")) and (guardrails.require_patch_preview or mode == "auto")
    max_patch_attempts = guardrails.max_patch_attempts or (2 if mode == "auto" else 1)
    patch_proposals = [1, max_patch_attempts] if enabled else [0, 0]
    validation_tests = _validation_tests_for_patch(failure_types)
    notes: list[str] = [ "Every patch proposal should trigger focused validation tests." ]
    if not patch_readiness.get("eligible"):
        notes.append("No patch allowlist was detected; patch preview should stay disabled.")
    if baseline_exists:
        notes.append("Baseline exists, so regression checks can be planned statically.")
    else:
        notes.append("No baseline found; regression validation cost is uncertain.")

    return PatchPreviewCostContext(
        patch_preview_enabled=enabled,
        estimated_patch_proposals=patch_proposals,
        estimated_validation_tests_per_patch=validation_tests,
        estimated_extra_validation_runs=[patch_proposals[0], max(patch_proposals[1], 1 if enabled else 0)],
        recommended_validation_tags=_validation_tags(failure_types),
        regression_checks_required=baseline_exists or "REGRESSION" in failure_types,
        notes=notes,
    )


def _validation_tests_for_patch(failure_types: list[str]) -> list[int]:
    if {"SAFETY_RISK", "FORBIDDEN_TOOL_CALL", "REGRESSION"} & set(failure_types):
        return [5, 12]
    if {"HALLUCINATION_RISK", "LOW_STABILITY"} & set(failure_types):
        return [4, 10]
    return [2, 6]


def _validation_tags(failure_types: list[str]) -> list[str]:
    tags = ["task_completion"]
    if "OUTPUT_SCHEMA_ERROR" in failure_types:
        tags.extend(["output_schema", "task_completion", "regression"])
    if "HALLUCINATION_RISK" in failure_types:
        tags.extend(["source_grounding", "hallucination", "regression"])
    if "SAFETY_RISK" in failure_types or "FORBIDDEN_TOOL_CALL" in failure_types:
        tags.extend(["safety", "permission_boundary", "tool_use"])
    if "REGRESSION" in failure_types:
        tags.append("regression")
    return _dedupe(tags)


def _overfitting_risk(
    requested_auto: bool,
    baseline: BaselineMetadata,
    eval_metadata: EvalMetadata,
    failure_types: list[str],
) -> str:
    if not requested_auto:
        return "low"
    score = 0
    if not baseline.exists:
        score += 1
    if not eval_metadata.case_count or eval_metadata.case_count < 5:
        score += 1
    if "LOW_STABILITY" in failure_types:
        score += 1
    if "OUTPUT_SCHEMA_ERROR" in failure_types:
        score += 1
    if "REGRESSION" not in failure_types:
        score += 1
    if score >= 3:
        return "high"
    if score:
        return "medium"
    return "low"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
