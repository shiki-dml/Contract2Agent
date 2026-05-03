from __future__ import annotations

from contract2agent.cost_estimate.loader import BaselineMetadata, EvalMetadata
from contract2agent.cost_estimate.models import OptimizationSuggestion


def generate_optimization_suggestions(
    *,
    mode: str,
    recommended_mode: str,
    failure_types: list[str],
    baseline: BaselineMetadata,
    eval_metadata: EvalMetadata,
    has_high_risk_tools: bool,
) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []

    def add(title: str, reason: str, effect: str, guardrail: str) -> None:
        suggestions.append(
            OptimizationSuggestion(
                title=title,
                reason=reason,
                expected_effect=effect,
                related_guardrail_or_command=guardrail,
            )
        )

    if mode == "auto" and recommended_mode != "auto":
        add(
            "Run deep before auto",
            "Auto readiness or safety guardrails are not sufficient for bounded repair.",
            "Avoids patch and validation loops until failures are understood.",
            "agentdoctor deep --rounds 3 --review on-fail",
        )
    if not eval_metadata.exists:
        add(
            "Run quick because eval coverage is incomplete",
            "No eval metadata was available, so the test count estimate is rule-based.",
            "Keeps the first diagnosis bounded while metadata is improved.",
            "agentdoctor quick",
        )
    if "LOOP_RISK" in failure_types:
        add(
            "Add max tool-call limits",
            "Loop risk can multiply tool calls and runtime.",
            "Bounds repeated tool calls and stops unproductive retries.",
            "max_tool_calls_per_test",
        )
    if not baseline.exists:
        add(
            "Save a baseline after the first reliable deep run",
            "Regression cost cannot be refined without baseline context.",
            "Improves future regression and runtime estimates.",
            "compare_baseline",
        )
    if "OUTPUT_SCHEMA_ERROR" in failure_types:
        add(
            "Run focused output-schema tests first",
            "Schema checks are cheap and catch common repair regressions early.",
            "Reduces full deep reruns after simple formatting fixes.",
            "run_output_schema_focus_first",
        )
    if "HALLUCINATION_RISK" in failure_types:
        add(
            "Use deterministic source scorers when possible",
            "LLM judges can add calls and scorer uncertainty for grounding checks.",
            "Lowers LLM-call risk for source-grounding validation.",
            "use_deterministic_source_scorers_when_possible",
        )
    if has_high_risk_tools:
        add(
            "Mock side-effectful tools during diagnosis",
            "High-risk tools should not execute real writes or external actions in a diagnostic estimate.",
            "Reduces safety and review burden before real validation.",
            "require_human_review_for_high_risk",
        )
    if mode == "auto":
        add(
            "Use focused patch-preview validation tags",
            "Rerunning all tests after every patch can cause auto mode cost blow-up.",
            "Keeps validation tied to the changed behavior plus regression checks.",
            "max_patch_attempts",
        )
    return _dedupe(suggestions)


def _dedupe(values: list[OptimizationSuggestion]) -> list[OptimizationSuggestion]:
    seen: set[str] = set()
    result: list[OptimizationSuggestion] = []
    for item in values:
        if item.title in seen:
            continue
        seen.add(item.title)
        result.append(item)
    return result
