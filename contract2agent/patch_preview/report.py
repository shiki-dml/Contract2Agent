from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contract2agent.patch_preview.models import PatchPreviewReport, PatchProposal, to_plain_data


def write_patch_preview_reports(
    report: PatchPreviewReport,
    output_dir: str | Path,
) -> dict[str, str]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    latest_md = target / "latest.md"
    latest_json = target / "latest.json"
    report.output_paths = {
        "latest_markdown": str(latest_md),
        "latest_json": str(latest_json),
    }

    for proposal in report.proposals:
        patch_base = target / proposal.patch_id
        md_path = patch_base.with_suffix(".md")
        json_path = patch_base.with_suffix(".json")
        report.output_paths[f"{proposal.patch_id}_markdown"] = str(md_path)
        report.output_paths[f"{proposal.patch_id}_json"] = str(json_path)
        md_path.write_text(format_single_patch_markdown(proposal), encoding="utf-8")
        json_path.write_text(
            json.dumps(to_plain_data(proposal), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if proposal.diff:
            diff_path = patch_base.with_suffix(".diff")
            diff_path.write_text(proposal.diff, encoding="utf-8")
            report.output_paths[f"{proposal.patch_id}_diff"] = str(diff_path)

    latest_md.write_text(format_markdown_report(report), encoding="utf-8")
    latest_json.write_text(
        json.dumps(to_plain_data(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report.output_paths


def format_terminal_summary(report: PatchPreviewReport) -> str:
    review_only = sum(1 for proposal in report.proposals if not proposal.diff)
    lines = [
        "AgentDoctor Patch Preview",
        "",
        f"Proposals: {len(report.proposals)}",
        f"Review-only items: {review_only}",
        f"High/Critical risk: {report.high_risk_count}",
    ]
    if not report.proposals:
        lines.extend(
            [
                "",
                "No patch proposals generated.",
                "Run `agentdoctor quick` or `agentdoctor deep --rounds 3` to collect findings.",
            ]
        )
    else:
        lines.extend(["", "Patch proposals:"])
        for proposal in report.proposals:
            target = ",".join(proposal.files_changed or proposal.target_files or ["review-only"])
            approval = "approval required" if proposal.requires_approval else "no approval required"
            lines.append(
                f"- {proposal.patch_id}: {','.join(proposal.failure_types)} -> "
                f"{target} [{proposal.risk_level}, {approval}]"
            )
    if report.skipped_items:
        lines.extend(["", "Skipped items:"])
        lines.extend(f"- {item}" for item in report.skipped_items[:5])
    lines.extend(
        [
            "",
            "Reports:",
            report.output_paths.get("latest_markdown", ".agentdoctor/patches/latest.md"),
            report.output_paths.get("latest_json", ".agentdoctor/patches/latest.json"),
        ]
    )
    return "\n".join(lines)


def format_markdown_report(report: PatchPreviewReport) -> str:
    lines = [
        "# AgentDoctor Patch Preview",
        "",
        "## Summary",
        "",
        f"- Preview ID: `{report.patch_preview_id}`",
        f"- Created: `{report.created_at}`",
        f"- Source run: `{report.source_run or '-'}`",
        f"- Proposals: `{len(report.proposals)}`",
        f"- Review required: `{report.review_required_count}`",
        f"- Auto-apply eligible for future flow: `{report.auto_apply_eligible_count}`",
        f"- High/Critical risk: `{report.high_risk_count}`",
        "",
        "Patch Preview v0.1 is preview-only. No files were modified.",
        "",
        "## Patch Proposals",
        "",
    ]
    if report.proposals:
        for proposal in report.proposals:
            lines.extend(_proposal_lines(proposal))
    else:
        lines.append("No patch proposals generated.")

    lines.extend(["", "## Review-Only Items", ""])
    review_only = [proposal for proposal in report.proposals if not proposal.diff]
    if review_only:
        for proposal in review_only:
            lines.append(f"- `{proposal.patch_id}`: {proposal.reason}")
    else:
        lines.append("No review-only items.")

    lines.extend(["", "## Skipped Items", ""])
    if report.skipped_items:
        lines.extend(f"- {item}" for item in report.skipped_items)
    else:
        lines.append("No skipped items.")

    lines.extend(
        [
            "",
            "## Raw Metadata",
            "",
            "```json",
            json.dumps(
                {
                    "patch_preview_id": report.patch_preview_id,
                    "created_at": report.created_at,
                    "source_run": report.source_run,
                    "output_paths": report.output_paths,
                },
                indent=2,
                sort_keys=True,
            ),
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def format_single_patch_markdown(proposal: PatchProposal) -> str:
    return "\n".join(
        [
            "# AgentDoctor Patch Proposal",
            "",
            *_proposal_lines(proposal),
        ]
    ) + "\n"


def format_json_report(report: PatchPreviewReport) -> str:
    return json.dumps(to_plain_data(report), indent=2, sort_keys=True) + "\n"


def _proposal_lines(proposal: PatchProposal) -> list[str]:
    lines = [
        f"### Patch: {proposal.patch_id}",
        "",
        "#### Target Failure Types",
        "",
        ", ".join(f"`{item}`" for item in proposal.failure_types) or "-",
        "",
        "#### Related Findings",
        "",
        ", ".join(f"`{item}`" for item in proposal.related_finding_ids) or "-",
        "",
        "#### Reason",
        "",
        proposal.reason,
        "",
        "#### Proposed Files",
        "",
    ]
    lines.extend(f"- `{path}`" for path in (proposal.files_changed or proposal.target_files or ["review-only"]))
    lines.extend(["", "#### Diff", ""])
    if proposal.diff:
        lines.extend(["```diff", proposal.diff.rstrip(), "```"])
    else:
        lines.append("No diff was generated. This item requires review only.")

    lines.extend(
        [
            "",
            "#### Expected Effect",
            "",
            *_bullet_lines(proposal.expected_effect),
            "",
            "#### Validation Plan",
            "",
            f"- Tags: {', '.join(f'`{tag}`' for tag in proposal.validation_tags)}",
            f"- Command: `{proposal.validation_command}`",
        ]
    )
    lines.extend(_bullet_section("Expected improvement", proposal.expected_improvement))
    lines.extend(_bullet_section("Regression checks", proposal.regression_checks))
    lines.extend(
        [
            "",
            "#### Baseline Impact",
            "",
            "```json",
            json.dumps(proposal.baseline_impact, indent=2, sort_keys=True),
            "```",
            "",
            "#### Regression Risks",
            "",
            *_bullet_lines(proposal.regression_risks),
            "",
            "#### Risk and Approval",
            "",
            f"- Risk: `{proposal.risk_level}`",
            f"- Requires approval: `{str(proposal.requires_approval).lower()}`",
            f"- Auto-apply eligible for future flow: `{str(proposal.auto_apply_eligible).lower()}`",
            f"- Do not apply automatically: `{str(proposal.do_not_apply_automatically).lower()}`",
            "",
            "#### Rollback Plan",
            "",
            proposal.rollback_plan,
        ]
    )
    lines.extend(_bullet_section("Rollback conditions", proposal.rollback_condition))
    lines.extend(["", "#### Reviewer Notes", ""])
    lines.extend(_bullet_lines(proposal.reviewer_notes))
    lines.append("")
    return lines


def _bullet_section(title: str, values: list[str]) -> list[str]:
    lines = ["", f"- {title}:"]
    if values:
        lines.extend(f"  - {value}" for value in values)
    else:
        lines.append("  - None.")
    return lines


def _bullet_lines(values: list[str]) -> list[str]:
    if not values:
        return ["- None."]
    return [f"- {value}" for value in values]
