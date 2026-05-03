from __future__ import annotations

from contract2agent.cost_estimate.loader import EvalMetadata


def estimate_llm_call_range(
    *,
    mode: str,
    test_count_range: list[int],
    eval_metadata: EvalMetadata,
    tags: list[str],
    auto_iterations: list[int],
    patch_attempts: list[int],
    repeated_runs: int,
    max_llm_calls: int | None,
) -> tuple[list[int], list[str]]:
    warnings: list[str] = []
    low, high = test_count_range
    llm_low = low
    llm_high = high

    normalized_tags = {tag.casefold() for tag in tags}
    if eval_metadata.llm_judge_detected:
        llm_low += low
        llm_high += high
    elif eval_metadata.deterministic_scorers_only is None:
        if {"hallucination", "source_grounding", "safety"} & normalized_tags:
            llm_high += high
        warnings.append("Scorer type is unknown. LLM call estimate may be low.")

    if repeated_runs > 1 and "stability" in normalized_tags:
        repeated_low = max(0, low // 4) * (repeated_runs - 1)
        repeated_high = max(1, high // 3) * (repeated_runs - 1)
        llm_low += repeated_low
        llm_high += repeated_high

    if mode == "auto":
        llm_low += auto_iterations[0] * 1
        llm_high += auto_iterations[1] * 3
        llm_low += patch_attempts[0] * 1
        llm_high += patch_attempts[1] * 3

    return _apply_cap([llm_low, llm_high], max_llm_calls), warnings


def _apply_cap(values: list[int], cap: int | None) -> list[int]:
    low, high = values
    if cap is None:
        return [low, high]
    capped_high = min(high, cap)
    capped_low = min(low, capped_high)
    return [capped_low, capped_high]
