from __future__ import annotations

from contract2agent.cost_estimate.loader import BaselineMetadata
from contract2agent.cost_estimate.models import RuntimeEstimate


def estimate_runtime_range(
    *,
    mode: str,
    complexity_level: str,
    baseline: BaselineMetadata,
) -> RuntimeEstimate:
    if baseline.historical_cost_available and baseline.avg_runtime_seconds is not None:
        average = baseline.avg_runtime_seconds
        return RuntimeEstimate(
            level=_level_from_seconds(average),
            min_seconds=max(1, int(average * 0.5)),
            max_seconds=max(1, int(average * 2.0)),
            confidence="medium",
            note=(
                "Broad runtime range is estimated from historical metadata; "
                "it is still not measured runtime for this planned run."
            ),
            source=f"baseline {baseline.path}",
        )
    if complexity_level == "unknown":
        return RuntimeEstimate(level="unknown", confidence="unknown")
    if mode == "quick" and complexity_level in {"low", "medium"}:
        return RuntimeEstimate(level="short", confidence="low")
    if mode == "auto" or complexity_level == "very_high":
        return RuntimeEstimate(level="very_long", confidence="low")
    if complexity_level == "high":
        return RuntimeEstimate(level="long", confidence="low")
    return RuntimeEstimate(level="medium", confidence="low")


def _level_from_seconds(seconds: float) -> str:
    if seconds < 60:
        return "short"
    if seconds < 300:
        return "medium"
    if seconds < 1200:
        return "long"
    return "very_long"
