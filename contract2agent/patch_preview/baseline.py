from __future__ import annotations

from pathlib import Path

from contract2agent.patch_preview.loader import count_failure_types_in_file
from contract2agent.patch_preview.models import BaselineImpact, FindingGroup
from contract2agent.patch_preview.validation import regression_checks_for_group


def baseline_impact_for_group(
    project_root: Path,
    group: FindingGroup,
    baseline_path: Path | None = None,
) -> BaselineImpact:
    path = baseline_path or project_root / ".agentdoctor" / "baselines" / "latest.json"
    current_counts = {
        failure_type: sum(1 for finding in group.findings if finding.failure_type == failure_type)
        for failure_type in group.failure_types
    }

    if not path.exists():
        return BaselineImpact(
            baseline_exists=False,
            baseline_path=str(path),
            current_failure_count=current_counts,
            likely_regression_risks=_likely_regression_risks(group),
            recommended_regression_checks=_checks(group),
            warning="No baseline found. Regression impact is limited.",
        )

    baseline_counts, resolved_path = count_failure_types_in_file(path)
    target_counts = {
        failure_type: baseline_counts.get(failure_type, 0)
        for failure_type in group.failure_types
    }
    return BaselineImpact(
        baseline_exists=True,
        baseline_path=resolved_path or str(path),
        target_failure_type_in_baseline=target_counts,
        current_failure_count=current_counts,
        baseline_failure_count=baseline_counts,
        likely_regression_risks=_likely_regression_risks(group),
        recommended_regression_checks=_checks(group),
    )


def _likely_regression_risks(group: FindingGroup) -> list[str]:
    risks: list[str] = []
    if "OUTPUT_SCHEMA_ERROR" in group.failure_types:
        risks.append("Stricter JSON output may reduce task completeness.")
    if "TOOL_MISSING" in group.failure_types:
        risks.append("Tool-use triggers may cause unnecessary tool calls in borderline cases.")
    if "HALLUCINATION_RISK" in group.failure_types:
        risks.append("Source-grounding rules may make answers overly conservative.")
    if "SAFETY_RISK" in group.failure_types or "FORBIDDEN_TOOL_CALL" in group.failure_types:
        risks.append("Permission-boundary changes may block legitimate workflows without explicit approval.")
    if not risks:
        risks.append("Patch may change behavior outside the triggering findings.")
    return risks


def _checks(group: FindingGroup) -> list[str]:
    checks = regression_checks_for_group(group)
    tags = []
    for check in checks:
        if "TASK_INCOMPLETE" in check:
            tags.append("task_completion")
        elif "HALLUCINATION_RISK" in check:
            tags.append("source_grounding")
        elif "SAFETY_RISK" in check:
            tags.append("safety")
        elif "FORBIDDEN_TOOL_CALL" in check:
            tags.append("forbidden_tool_call")
        else:
            tags.append("regression")
    return list(dict.fromkeys(tags))
