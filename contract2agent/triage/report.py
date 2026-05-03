from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contract2agent.triage.models import TriagePlan, to_plain_data

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is a declared dependency.
    yaml = None  # type: ignore[assignment]


def write_triage_reports(plan: TriagePlan, output_dir: str | Path) -> dict[str, str]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    latest_md = target / "latest.md"
    latest_json = target / "latest.json"
    timestamp_md = target / f"{plan.triage_id}.md"
    timestamp_json = target / f"{plan.triage_id}.json"

    paths = {
        "latest_markdown": str(latest_md),
        "latest_json": str(latest_json),
        "timestamped_markdown": str(timestamp_md),
        "timestamped_json": str(timestamp_json),
    }
    plan.report_paths = paths

    data = to_plain_data(plan)
    markdown = format_markdown_report(plan)
    json_text = json.dumps(data, indent=2, sort_keys=True) + "\n"

    latest_md.write_text(markdown, encoding="utf-8")
    timestamp_md.write_text(markdown, encoding="utf-8")
    latest_json.write_text(json_text, encoding="utf-8")
    timestamp_json.write_text(json_text, encoding="utf-8")
    return paths


def format_terminal_summary(plan: TriagePlan) -> str:
    behaviors = [behavior.title for behavior in plan.key_behaviors_to_test[:5]]
    warnings = [warning.title for warning in plan.warnings[:5]]
    lines = [
        "AgentDoctor Triage Plan",
        "",
        f"Agent: {plan.agent_summary.name or 'unknown'}",
        f"Type: {plan.agent_classification.agent_type}",
        f"Risk: {plan.risk_assessment.risk_level}",
        f"Recommended mode: {plan.recommendation.recommended_mode}",
        f"Recommended rounds: {plan.recommendation.recommended_rounds}",
        f"Review policy: {plan.recommendation.suggested_review_policy}",
        "",
        "Key behaviors:",
    ]
    lines.extend(f"- {item}" for item in behaviors)
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {item}" for item in warnings)
    lines.extend(
        [
            "",
            "Recommended next command:",
            plan.recommended_next_command,
            "",
            "Full report:",
            plan.report_paths.get("latest_markdown", ".agentdoctor/triage/latest.md"),
            plan.report_paths.get("latest_json", ".agentdoctor/triage/latest.json"),
        ]
    )
    return "\n".join(lines)


def format_markdown_report(plan: TriagePlan) -> str:
    data = to_plain_data(plan)
    lines = [
        "# AgentDoctor Triage Plan",
        "",
        f"Triage ID: `{plan.triage_id}`",
        f"Created: `{plan.created_at}`",
        f"Project root: `{plan.project_root}`",
        "",
        "## 1. Agent Summary",
        "",
        _yaml_block(data["agent_summary"]),
        "",
        "## 2. Input Sources",
        "",
        _yaml_block(data["input_sources"]),
        "",
        "## 3. Detected Capabilities",
        "",
        _yaml_block(data["detected_capabilities"]),
        "",
        "## 4. Agent Classification",
        "",
        _yaml_block(data["agent_classification"]),
        "",
        "## 5. Risk Assessment",
        "",
        _yaml_block(data["risk_assessment"]),
        "",
        "## 6. Eval Coverage",
        "",
        _yaml_block(data["eval_coverage"]),
        "",
        "## 7. Key Behaviors to Test",
        "",
    ]
    if plan.key_behaviors_to_test:
        for behavior in plan.key_behaviors_to_test:
            lines.append(f"- **{behavior.priority}** `{behavior.id}`: {behavior.title} - {behavior.description}")
    else:
        lines.append("No key behaviors were generated.")

    lines.extend(["", "## 8. Missing Information", ""])
    if plan.missing_information:
        for item in plan.missing_information:
            lines.append(f"- **{item.severity}** `{item.id}`: {item.title} - {item.suggested_action}")
    else:
        lines.append("No missing information items were generated.")

    lines.extend(["", "## 9. Warnings", ""])
    if plan.warnings:
        for warning in plan.warnings:
            lines.append(f"- **{warning.severity}** `{warning.id}`: {warning.title} - {warning.recommended_action}")
    else:
        lines.append("No warnings were generated.")

    lines.extend(
        [
            "",
            "## 10. Suggested Round Plan",
            "",
            _yaml_block(data["suggested_round_plan"]),
            "",
            "## 11. Baseline Status",
            "",
            _yaml_block(data["baseline_status"]),
            "",
            "## 12. Patch Preview Readiness",
            "",
            _yaml_block(data["patch_preview_readiness"]),
            "",
            "## 13. Auto Readiness",
            "",
            _yaml_block(data["auto_readiness"]),
            "",
            "## 14. Estimated Diagnostic Cost",
            "",
            _yaml_block(data["estimated_diagnostic_cost"]),
            "",
            "## 15. Recommended Next Step",
            "",
            "Recommended next command:",
            "",
            "```bash",
            plan.recommended_next_command,
            "```",
            "",
            _yaml_block(data["recommendation"]),
            "",
            "## 16. Raw Metadata",
            "",
            _yaml_block(
                {
                    "triage_id": plan.triage_id,
                    "created_at": plan.created_at,
                    "suggested_test_tags": plan.suggested_test_tags,
                    "report_paths": plan.report_paths,
                }
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def format_json_report(plan: TriagePlan) -> str:
    return json.dumps(to_plain_data(plan), indent=2, sort_keys=True) + "\n"


def _yaml_block(value: Any) -> str:
    if yaml is not None:
        text = yaml.safe_dump(value, sort_keys=False, allow_unicode=True).rstrip()
    else:
        text = json.dumps(value, indent=2, sort_keys=True)
    return f"```yaml\n{text}\n```"
