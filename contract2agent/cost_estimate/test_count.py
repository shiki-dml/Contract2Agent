from __future__ import annotations


TAG_TEST_ADJUSTMENTS: dict[str, tuple[int, int]] = {
    "output_schema": (2, 5),
    "output_format": (1, 3),
    "tool_use": (2, 5),
    "tool_order": (2, 5),
    "tool_arguments": (2, 5),
    "error_handling": (2, 6),
    "hallucination": (3, 8),
    "source_grounding": (3, 8),
    "safety": (3, 8),
    "permission_boundary": (2, 6),
    "regression": (3, 10),
    "stability": (2, 8),
    "loop_risk": (1, 4),
}


def estimate_test_count_range(
    *,
    mode: str,
    risk_level: str,
    rounds: int,
    tags: list[str],
    eval_case_count: int | None,
    repeated_runs: int,
    budget_profile: str,
    max_tests: int | None,
) -> list[int]:
    normalized_tags = {tag.casefold() for tag in tags}
    if mode == "quick":
        low, high = 3, 8
    elif mode == "auto":
        per_round = _deep_per_round(risk_level)
        base_low = per_round[0] * max(rounds, 1)
        base_high = per_round[1] * max(rounds, 1)
        validation_low, validation_high = 4, 12
        regression_low, regression_high = (3, 10) if "regression" in normalized_tags else (1, 4)
        low = base_low + validation_low + regression_low
        high = base_high + validation_high + regression_high
    else:
        per_round = _deep_per_round(risk_level)
        low = per_round[0] * max(rounds, 1)
        high = per_round[1] * max(rounds, 1)

    for tag, adjustment in TAG_TEST_ADJUSTMENTS.items():
        if tag in normalized_tags:
            low += adjustment[0]
            high += adjustment[1]

    if "stability" in normalized_tags and repeated_runs > 1:
        selected_low = max(1, low // 4)
        selected_high = max(selected_low, high // 3)
        low += selected_low * (repeated_runs - 1)
        high += selected_high * (repeated_runs - 1)

    if eval_case_count:
        if mode == "quick":
            high = max(high, min(eval_case_count, 8))
        elif mode == "auto":
            low = max(low, min(eval_case_count, low))
            high = max(high, eval_case_count * max(1, min(rounds, 3)))
        else:
            low = max(low, min(eval_case_count, low))
            high = max(high, eval_case_count)

    low, high = _apply_profile(low, high, budget_profile)
    return _apply_cap([low, high], max_tests)


def _deep_per_round(risk_level: str) -> tuple[int, int]:
    if risk_level == "low":
        return 4, 7
    if risk_level == "high":
        return 5, 12
    return 4, 10


def _apply_profile(low: int, high: int, profile: str) -> tuple[int, int]:
    if profile == "conservative":
        high = max(low, int(round(high * 0.75)))
    elif profile == "thorough":
        low = int(round(low * 1.1))
        high = int(round(high * 1.25))
    return max(0, low), max(low, high)


def _apply_cap(values: list[int], cap: int | None) -> list[int]:
    low, high = values
    if cap is None:
        return [max(0, low), max(0, high)]
    capped_high = min(high, cap)
    capped_low = min(low, capped_high)
    return [max(0, capped_low), max(0, capped_high)]
