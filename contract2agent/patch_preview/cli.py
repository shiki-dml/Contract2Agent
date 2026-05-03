from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from contract2agent.patch_preview.baseline import baseline_impact_for_group
from contract2agent.patch_preview.diff_builder import build_unified_diff
from contract2agent.patch_preview.grouping import grouped_failure_summary, group_findings
from contract2agent.patch_preview.loader import load_findings, normalize_failure_type
from contract2agent.patch_preview.models import (
    BaselineImpact,
    FindingGroup,
    LoadedFindings,
    PatchPreviewReport,
    PatchProposal,
    to_plain_data,
)
from contract2agent.patch_preview.report import write_patch_preview_reports
from contract2agent.patch_preview.risk import compute_risk_and_approval
from contract2agent.patch_preview.security import sanitize_text
from contract2agent.patch_preview.strategies import FixStrategy, select_strategy
from contract2agent.patch_preview.target_selection import TargetSelection, select_target_file
from contract2agent.patch_preview.validation import (
    expected_improvement_for_group,
    regression_checks_for_group,
    rollback_conditions_for_group,
    validation_command,
    validation_tags_for_group,
)


@dataclass
class PatchPreviewOptions:
    project_root: Path = Path(".")
    from_run: Path | None = None
    from_findings: Path | None = None
    failure_type: str | None = None
    output: Path | None = None
    output_format: str = "markdown"
    dry_run: bool = True
    allow_apply: bool = False
    apply_patch_id: str | None = None
    now: datetime | None = None


def run_patch_preview(options: PatchPreviewOptions | None = None) -> PatchPreviewReport:
    options = options or PatchPreviewOptions()
    project_root = Path(options.project_root).expanduser().resolve()
    now = options.now or datetime.now(timezone.utc).astimezone()
    created_at = now.replace(microsecond=0).isoformat()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    output_dir = _resolve_output_dir(project_root, options.output)

    if options.apply_patch_id:
        loaded = LoadedFindings(
            source_path=None,
            source_run_id=None,
            warnings=[
                "Apply is not implemented in Patch Preview v0.1. No files were changed.",
                "Use the generated .diff artifact for manual review or wait for an approval/apply flow.",
            ],
        )
    else:
        source = options.from_run or options.from_findings
        loaded = load_findings(source)

    skipped = list(loaded.warnings)
    proposals: list[PatchProposal] = []
    failure_filter = (
        normalize_failure_type(options.failure_type, fallback_text="")
        if options.failure_type
        else None
    )
    if failure_filter == "UNKNOWN" and options.failure_type:
        skipped.append(f"Unknown --failure-type filter: {options.failure_type}")

    groups = group_findings(loaded.findings, None if failure_filter == "UNKNOWN" else failure_filter)
    if not loaded.findings:
        skipped.append("No findings were available for patch preview.")
    elif not groups:
        skipped.append("No findings matched the requested failure type.")

    for index, group in enumerate(groups, start=1):
        patch_id = f"patch_{timestamp}_{index:03d}"
        proposals.append(
            _proposal_for_group(
                patch_id=patch_id,
                created_at=created_at,
                project_root=project_root,
                loaded=loaded,
                group=group,
            )
        )

    report = PatchPreviewReport(
        patch_preview_id=f"patch_preview_{timestamp}",
        created_at=created_at,
        source_run=loaded.source_path,
        proposals=proposals,
        skipped_items=skipped,
        review_required_count=sum(1 for proposal in proposals if proposal.requires_approval),
        auto_apply_eligible_count=sum(1 for proposal in proposals if proposal.auto_apply_eligible),
        high_risk_count=sum(1 for proposal in proposals if proposal.risk_level in {"high", "critical"}),
    )
    write_patch_preview_reports(report, output_dir)
    return report


def _proposal_for_group(
    *,
    patch_id: str,
    created_at: str,
    project_root: Path,
    loaded: LoadedFindings,
    group: FindingGroup,
) -> PatchProposal:
    strategy = select_strategy(group, previous_patch_metadata=loaded.previous_patch_metadata)
    target = select_target_file(project_root, group, strategy.patch_type)
    tags = validation_tags_for_group(group)
    target_is_safe = target.target is not None and strategy.patch_type != "no_agent_patch_review_only"
    risk_level, requires_approval, auto_apply_eligible, do_not_apply = compute_risk_and_approval(
        group,
        patch_type=strategy.patch_type,
        target_is_safe=target_is_safe,
    )
    baseline = baseline_impact_for_group(project_root, group)
    source_round_id = ",".join(group.source_round_ids) if group.source_round_ids else None
    reason = _reason(group, strategy, target)
    diff = ""
    files_changed: list[str] = []
    before_summary = _before_summary(group, target)
    after_summary = _after_summary(strategy)
    reviewer_notes = list(strategy.reviewer_notes)
    reviewer_notes.extend(target.warnings)
    reviewer_notes.append(
        "Current CLI validation does not yet support --focus or --compare-baseline; use validation_tags to choose focused cases."
    )

    if _can_generate_diff(strategy, target):
        assert target.target is not None
        diff, _ = build_unified_diff(target.target, project_root, strategy.guidance_lines)
        files_changed = [_relative(project_root, target.target)] if diff else []
        if not diff:
            reviewer_notes.append("No textual diff was generated because the proposed guidance is already present.")
    else:
        if target.review_only_reason:
            reviewer_notes.append(f"No diff generated: {target.review_only_reason}")
        elif strategy.patch_type == "rollback_patch":
            reviewer_notes.append("Rollback metadata was found, but v0.1 does not apply or synthesize reverse patches automatically.")
        elif strategy.patch_type == "no_agent_patch_review_only":
            reviewer_notes.append("This failure type is review-only for agent behavior in v0.1.")

    patch_type = strategy.patch_type
    if not diff and patch_type != "rollback_patch":
        patch_type = "no_agent_patch_review_only"

    # Recompute risk flags after review-only downgrade so auto_apply_eligible is
    # false when no diff exists.
    risk_level, requires_approval, auto_apply_eligible, do_not_apply = compute_risk_and_approval(
        group,
        patch_type=patch_type,
        target_is_safe=bool(files_changed),
    )
    return PatchProposal(
        patch_id=patch_id,
        created_at=created_at,
        source_run_id=loaded.source_run_id,
        source_round_id=source_round_id,
        related_finding_ids=group.related_finding_ids,
        failure_types=group.failure_types,
        grouped_failure_summary=grouped_failure_summary(group),
        reason=reason,
        patch_type=patch_type,
        strategy_id=strategy.strategy_id,
        target_files=target.target_files,
        files_changed=files_changed,
        diff=diff,
        before_summary=before_summary,
        after_summary=after_summary,
        expected_effect=strategy.expected_effect,
        validation_tags=tags,
        validation_command=validation_command(tags),
        regression_risks=strategy.regression_risks,
        baseline_impact=to_plain_data(baseline),
        risk_level=risk_level,
        requires_approval=requires_approval,
        auto_apply_eligible=auto_apply_eligible,
        do_not_apply_automatically=do_not_apply,
        rollback_available=_rollback_available(strategy, loaded),
        rollback_plan=_rollback_plan(strategy, files_changed),
        reviewer_notes=[sanitize_text(note) for note in reviewer_notes],
        status="previewed",
        expected_improvement=expected_improvement_for_group(group),
        regression_checks=regression_checks_for_group(group),
        rollback_condition=rollback_conditions_for_group(group),
    )


def _can_generate_diff(strategy: FixStrategy, target: TargetSelection) -> bool:
    if strategy.patch_type in {"no_agent_patch_review_only", "rollback_patch"}:
        return False
    if target.target is None:
        return False
    return bool(strategy.guidance_lines)


def _reason(group: FindingGroup, strategy: FixStrategy, target: TargetSelection) -> str:
    descriptions = [
        finding.description
        for finding in group.findings
        if finding.description
    ][:3]
    target_text = target.target_files[0] if target.target_files else "no safe target"
    if "OUTPUT_SCHEMA_ERROR" in group.failure_types:
        return (
            f"The agent produced schema/JSON-related failures in {len(group.findings)} finding(s). "
            "The selected prompt/config target does not enforce JSON-only output strongly enough. "
            f"Proposed target: {target_text}."
        )
    if "TOOL_MISSING" in group.failure_types and group.tool_name:
        return (
            f"{len(group.findings)} finding(s) indicate `{group.tool_name}` was required or missing. "
            f"The proposal adds an explicit trigger condition for that tool. Proposed target: {target_text}."
        )
    if "HALLUCINATION_RISK" in group.failure_types:
        return (
            f"{len(group.findings)} finding(s) indicate unsupported or insufficiently grounded claims. "
            "The proposal adds source-grounding and evidence requirements."
        )
    if "SCORER_UNCERTAIN" in group.failure_types:
        return "The scorer or eval expectation is uncertain, so patching agent behavior would be unsafe."
    if "UNKNOWN" in group.failure_types:
        return "The finding does not contain enough evidence to choose an agent patch safely."
    if "REGRESSION" in group.failure_types:
        return "A regression was detected; rollback or human review is preferred over stacking a new prompt patch."
    if "SAFETY_RISK" in group.failure_types or "FORBIDDEN_TOOL_CALL" in group.failure_types:
        return "The finding affects safety or permission boundaries and must be reviewed before any change."
    if descriptions:
        return sanitize_text(descriptions[0])
    return f"{strategy.title} is proposed for grouped findings."


def _before_summary(group: FindingGroup, target: TargetSelection) -> str:
    target_text = ", ".join(target.target_files) if target.target_files else "No safe target selected"
    return (
        f"Current target context: {target_text}. "
        f"Grouped findings indicate {', '.join(group.failure_types)}."
    )


def _after_summary(strategy: FixStrategy) -> str:
    if not strategy.guidance_lines:
        return "No behavior diff is proposed; reviewer action is required."
    return "Proposed guidance adds: " + " ".join(strategy.guidance_lines[:2])


def _rollback_available(strategy: FixStrategy, loaded: LoadedFindings) -> bool:
    if strategy.patch_type == "rollback_patch":
        return loaded.previous_patch_metadata is not None
    return False


def _rollback_plan(strategy: FixStrategy, files_changed: list[str]) -> str:
    if strategy.patch_type == "rollback_patch":
        return "Review previous patch metadata and apply a rollback only after human approval."
    if files_changed:
        return (
            "If this patch is later applied, revert the generated diff for "
            f"{', '.join(files_changed)} and rerun the validation command."
        )
    return "No file changes are proposed, so rollback is not needed."


def _resolve_output_dir(project_root: Path, output: Path | None) -> Path:
    if output is None:
        return project_root / ".agentdoctor" / "patches"
    path = Path(output).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path


def _relative(root: Path, path: Path | str) -> str:
    target = Path(path)
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return target.as_posix()
