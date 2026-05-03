from __future__ import annotations

import re

from contract2agent.patch_preview.models import FindingGroup, PatchFinding


COMPATIBLE_MERGE_GROUPS = [
    {"TOOL_MISSING", "HALLUCINATION_RISK"},
    {"OUTPUT_FORMAT_ERROR", "OUTPUT_SCHEMA_ERROR"},
    {"TOOL_ARGUMENT_ERROR", "ERROR_HANDLING_MISSING"},
]

SEPARATE_FAILURE_TYPES = {
    "SCORER_UNCERTAIN",
    "UNKNOWN",
    "SAFETY_RISK",
    "FORBIDDEN_TOOL_CALL",
    "REGRESSION",
}


def group_findings(
    findings: list[PatchFinding],
    failure_type_filter: str | None = None,
) -> list[FindingGroup]:
    filtered = [
        finding
        for finding in findings
        if failure_type_filter is None or finding.failure_type == failure_type_filter
    ]
    buckets: dict[tuple[str, str, str | None], list[PatchFinding]] = {}
    for finding in sorted(filtered, key=lambda item: (item.failure_type, item.id)):
        merge_class = _merge_class(finding.failure_type)
        cause = _cause_key(finding)
        target = finding.target_file
        buckets.setdefault((merge_class, cause, target), []).append(finding)

    groups: list[FindingGroup] = []
    for index, ((_, cause, target), items) in enumerate(
        sorted(buckets.items(), key=lambda item: item[0]),
        start=1,
    ):
        failure_types = sorted({item.failure_type for item in items})
        tool_name = _first_tool(items)
        groups.append(
            FindingGroup(
                group_id=f"group_{index:03d}",
                failure_types=failure_types,
                findings=items,
                likely_cause=cause,
                target_file=target,
                tool_name=tool_name,
            )
        )
    return groups


def grouped_failure_summary(group: FindingGroup) -> str:
    count = len(group.findings)
    failure_types = ", ".join(group.failure_types)
    tests = sorted(
        {finding.related_test_id for finding in group.findings if finding.related_test_id}
    )
    target = f" Target hint: {group.target_file}." if group.target_file else ""
    tool = f" Tool: {group.tool_name}." if group.tool_name else ""
    test_text = f" Related tests: {', '.join(tests)}." if tests else ""
    return (
        f"{count} finding{'s' if count != 1 else ''} share failure type(s) "
        f"{failure_types} and likely cause `{group.likely_cause}`.{tool}{target}{test_text}"
    )


def _merge_class(failure_type: str) -> str:
    if failure_type in SEPARATE_FAILURE_TYPES:
        return failure_type
    for group in COMPATIBLE_MERGE_GROUPS:
        if failure_type in group:
            return "+".join(sorted(group))
    return failure_type


def _cause_key(finding: PatchFinding) -> str:
    if finding.tool_name:
        return f"tool:{finding.tool_name.casefold()}"
    if finding.likely_cause:
        return _slug(finding.likely_cause)
    if finding.failure_type in {"OUTPUT_SCHEMA_ERROR", "OUTPUT_FORMAT_ERROR"}:
        return "output_contract"
    if finding.failure_type in {"HALLUCINATION_RISK"}:
        return "source_grounding"
    if finding.failure_type in {"SAFETY_RISK", "FORBIDDEN_TOOL_CALL"}:
        return "permission_boundary"
    if finding.failure_type in {"SCORER_UNCERTAIN"}:
        return "scorer_review"
    if finding.failure_type in {"UNKNOWN"}:
        return "unknown_evidence"
    return _slug(finding.description)[:80] or finding.failure_type.casefold()


def _first_tool(findings: list[PatchFinding]) -> str | None:
    for finding in findings:
        if finding.tool_name:
            return finding.tool_name
    return None


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.casefold()).strip("_")
    return cleaned or "shared_cause"
