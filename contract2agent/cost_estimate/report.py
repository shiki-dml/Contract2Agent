from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contract2agent.cost_estimate.models import EstimatedDiagnosticCost, STATIC_ESTIMATE_NOTE, to_plain_data

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is a declared dependency.
    yaml = None  # type: ignore[assignment]


def write_cost_reports(
    estimate: EstimatedDiagnosticCost,
    output_dir: str | Path,
) -> dict[str, str]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    latest_md = target / "latest.md"
    latest_json = target / "latest.json"
    timestamp_md = target / f"{estimate.cost_estimate_id}.md"
    timestamp_json = target / f"{estimate.cost_estimate_id}.json"
    paths = {
        "latest_markdown": str(latest_md),
        "latest_json": str(latest_json),
        "timestamped_markdown": str(timestamp_md),
        "timestamped_json": str(timestamp_json),
    }
    estimate.report_paths = paths

    markdown = format_markdown_report(estimate)
    json_text = format_json_report(estimate)
    latest_md.write_text(markdown, encoding="utf-8")
    timestamp_md.write_text(markdown, encoding="utf-8")
    latest_json.write_text(json_text, encoding="utf-8")
    timestamp_json.write_text(json_text, encoding="utf-8")
    return paths


def format_terminal_summary(estimate: EstimatedDiagnosticCost) -> str:
    drivers = [driver.title for driver in estimate.cost_drivers[:5]]
    guardrails = to_plain_data(estimate.budget_guardrails)
    guardrail_lines = [
        f"- {key}: {value}"
        for key, value in guardrails.items()
        if key
        in {
            "max_rounds",
            "max_tests",
            "max_tool_calls_per_test",
            "max_repeated_runs",
            "stop_on_safety_risk",
        }
        and value is not None
    ]
    lines = [
        "AgentDoctor Time Cost Estimate",
        "",
        f"Mode: {estimate.mode}",
        f"Complexity: {estimate.complexity_level}",
        f"Estimate confidence: {estimate.confidence}",
        f"Estimated rounds: {_range_text(estimate.estimated_rounds)}",
        f"Estimated tests: {_range_text(estimate.estimated_test_count_range)}",
        f"Runtime level: {estimate.estimated_runtime_range.level}",
        f"Review burden: {estimate.estimated_human_review_items.review_burden_level}",
        "",
        "Key cost drivers:",
    ]
    lines.extend(f"- {driver}" for driver in drivers or ["none detected"])
    lines.extend(["", "Recommended guardrails:"])
    lines.extend(guardrail_lines or ["- none"])
    lines.extend(
        [
            "",
            "Recommended command:",
            estimate.recommended_command,
            "",
            "Note:",
            STATIC_ESTIMATE_NOTE,
        ]
    )
    return "\n".join(lines)


def format_markdown_report(estimate: EstimatedDiagnosticCost) -> str:
    data = to_plain_data(estimate)
    lines = [
        "# AgentDoctor Time Cost Estimate",
        "",
        f"Estimate ID: `{estimate.cost_estimate_id}`",
        f"Created: `{estimate.created_at}`",
        f"Project root: `{estimate.project_root}`",
        "",
        f"> {STATIC_ESTIMATE_NOTE}",
        "",
        "## 1. Summary",
        "",
        _yaml_block(
            {
                "mode": estimate.mode,
                "complexity_level": estimate.complexity_level,
                "confidence": estimate.confidence,
                "estimated_rounds": estimate.estimated_rounds,
                "estimated_test_count_range": estimate.estimated_test_count_range,
                "estimated_llm_call_range": estimate.estimated_llm_call_range,
                "estimated_tool_call_range": data["estimated_tool_call_range"],
                "runtime_level": data["estimated_runtime_range"]["level"],
                "review_burden": data["estimated_human_review_items"]["review_burden_level"],
                "recommended_command": estimate.recommended_command,
                "note": STATIC_ESTIMATE_NOTE,
            }
        ),
        "",
        "## 2. Estimate Confidence and Assumptions",
        "",
        _yaml_block(
            {
                "confidence": estimate.confidence,
                "assumptions": estimate.assumptions,
                "warnings": estimate.warnings,
                "note": STATIC_ESTIMATE_NOTE,
            }
        ),
        "",
        "## 3. Mode Comparison",
        "",
        _yaml_block(data["mode_comparison"]),
        "",
        "## 4. Estimated Diagnostic Cost",
        "",
        _yaml_block(
            {
                "estimated_rounds": estimate.estimated_rounds,
                "estimated_test_count_range": estimate.estimated_test_count_range,
                "estimated_llm_call_range": estimate.estimated_llm_call_range,
                "estimated_tool_call_range": data["estimated_tool_call_range"],
                "estimated_runtime_range": data["estimated_runtime_range"],
                "estimated_human_review_items": data["estimated_human_review_items"],
                "estimated_patch_attempts": estimate.estimated_patch_attempts,
                "estimated_auto_iterations": estimate.estimated_auto_iterations,
                "note": STATIC_ESTIMATE_NOTE,
            }
        ),
        "",
        "## 5. Cost Drivers",
        "",
        _yaml_block(data["cost_drivers"]),
        "",
        "## 6. Failure-Type Cost Risks",
        "",
        _yaml_block(data["failure_type_cost_risks"]),
        "",
        "## 7. Budget Guardrails",
        "",
        _yaml_block(data["budget_guardrails"]),
        "",
        "## 8. Slow Path Predictions",
        "",
        _yaml_block(data["slow_path_predictions"]),
        "",
        "## 9. Human Review Burden",
        "",
        _yaml_block(data["review_burden"]),
        "",
        "## 10. Auto Mode Cost Plan",
        "",
        _yaml_block(data["auto_cost_plan"]),
        "",
        "## 11. Patch Preview Cost Context",
        "",
        _yaml_block(data["patch_preview_cost_context"]),
        "",
        "## 12. Baseline Cost Context",
        "",
        _yaml_block(data["baseline_cost_context"]),
        "",
        "## 13. Optimization Suggestions",
        "",
        _yaml_block(data["optimization_suggestions"]),
        "",
        "## 14. Recommended Command",
        "",
        "```bash",
        estimate.recommended_command,
        "```",
        "",
        "## 15. Notes and Limitations",
        "",
        "- This estimate does not run tests.",
        "- This estimate does not call the agent.",
        "- This estimate does not call tools or LLM APIs.",
        f"- {STATIC_ESTIMATE_NOTE}",
        "",
        _yaml_block(
            {
                "budget_recommendation": estimate.budget_recommendation,
                "report_paths": estimate.report_paths,
            }
        ),
    ]
    return "\n".join(lines) + "\n"


def format_json_report(estimate: EstimatedDiagnosticCost) -> str:
    return json.dumps(to_plain_data(estimate), indent=2, sort_keys=True) + "\n"


def _yaml_block(value: Any) -> str:
    if yaml is not None:
        text = yaml.safe_dump(value, sort_keys=False, allow_unicode=True).rstrip()
    else:
        text = json.dumps(value, indent=2, sort_keys=True)
    return f"```yaml\n{text}\n```"


def _range_text(value: Any) -> str:
    if isinstance(value, list) and len(value) == 2:
        return f"{value[0]}-{value[1]}"
    return str(value)
