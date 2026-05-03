from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from contract2agent.triage.classifiers import classify_agent_type, classify_tools
from contract2agent.triage.coverage import analyze_eval_coverage
from contract2agent.triage.discovery import discover_project
from contract2agent.triage.models import TriagePlan
from contract2agent.triage.parsers import (
    extract_agent_summary,
    extract_eval_cases,
    extract_outputs,
    extract_tool_specs,
    load_project_data,
    scan_prompt_signals,
)
from contract2agent.triage.planner import (
    estimate_diagnostic_cost,
    generate_key_behaviors,
    suggest_round_plan,
    suggest_test_tags,
)
from contract2agent.triage.recommendations import (
    evaluate_auto_readiness,
    evaluate_baseline_status,
    evaluate_patch_preview_readiness,
    generate_recommendation,
)
from contract2agent.triage.report import write_triage_reports
from contract2agent.triage.risk import assess_risk, detect_missing_information, generate_warnings


@dataclass
class TriageOptions:
    project_root: Path = Path(".")
    agent: Path | None = None
    goal: str | None = None
    output: Path | None = None
    allow_auto: bool = False
    now: datetime | None = None


def run_triage(options: TriageOptions | None = None) -> TriagePlan:
    options = options or TriageOptions()
    now = options.now or datetime.now(timezone.utc).astimezone()
    project_root = Path(options.project_root).expanduser().resolve()
    output_dir = (
        Path(options.output).expanduser()
        if options.output is not None
        else project_root / ".agentdoctor" / "triage"
    )
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir

    discovery = discover_project(project_root, options.agent)
    data = load_project_data(
        project_root=project_root,
        agent_config_path=discovery.agent_config_path,
        prompt_paths=discovery.prompt_paths,
        tool_paths=discovery.tool_paths,
        eval_paths=discovery.eval_paths,
        baseline_path=discovery.baseline_path,
        agentdoctor_config_path=discovery.agentdoctor_config_path,
    )
    prompt_signals = scan_prompt_signals(data.prompt_texts, data.agent_config_text)
    tool_specs = extract_tool_specs(data)
    capabilities = classify_tools(tool_specs)
    eval_cases = extract_eval_cases(data.eval_configs)
    eval_coverage = analyze_eval_coverage(eval_cases)
    capabilities.outputs = extract_outputs(data, prompt_signals)

    prompt_text = "\n".join(data.prompt_texts.values())
    classification = classify_agent_type(
        goal=options.goal,
        data=data,
        prompt_text=prompt_text,
        capabilities=capabilities,
        eval_cases=eval_cases,
    )
    agent_summary = extract_agent_summary(
        project_root=project_root,
        agent_config_path=discovery.agent_config_path,
        prompt_paths=discovery.prompt_paths,
        tool_count=len(capabilities.tools),
        eval_case_count=len(eval_cases),
        data=data,
    )
    baseline_status, baseline_warnings = evaluate_baseline_status(
        discovery=discovery,
        data=data,
        agent_summary=agent_summary,
        now=now,
    )
    patch_readiness = evaluate_patch_preview_readiness(project_root)
    risk = assess_risk(
        discovery=discovery,
        data=data,
        capabilities=capabilities,
        prompt_signals=prompt_signals,
        eval_case_count=len(eval_cases),
        baseline_exists=baseline_status.exists,
    )
    auto_readiness = evaluate_auto_readiness(
        discovery=discovery,
        data=data,
        capabilities=capabilities,
        classification=classification,
        risk=risk,
        prompt_signals=prompt_signals,
        eval_case_count=len(eval_cases),
        patch_readiness=patch_readiness,
    )
    missing_information = detect_missing_information(
        discovery=discovery,
        data=data,
        capabilities=capabilities,
        classification=classification,
        prompt_signals=prompt_signals,
        eval_case_count=len(eval_cases),
        baseline_exists=baseline_status.exists,
        patch_targets_available=patch_readiness.eligible,
        allow_auto=options.allow_auto,
    )
    warnings = generate_warnings(
        discovery=discovery,
        capabilities=capabilities,
        classification=classification,
        prompt_signals=prompt_signals,
        eval_covered_areas=eval_coverage.covered_areas,
        allow_auto=options.allow_auto,
        auto_eligible=auto_readiness.eligible,
        auto_blockers=auto_readiness.blockers,
    )
    warnings.extend(data.warnings)
    warnings.extend(baseline_warnings)
    warnings = _dedupe_warnings(warnings)

    suggested_tags = suggest_test_tags(
        classification=classification,
        capabilities=capabilities,
        risk=risk,
        prompt_signals=prompt_signals,
    )
    recommendation, next_command = generate_recommendation(
        risk=risk,
        classification=classification,
        auto_readiness=auto_readiness,
        allow_auto=options.allow_auto,
        agent_arg=_agent_arg_for_command(options.agent),
        goal=options.goal,
    )
    round_plan = suggest_round_plan(
        risk=risk,
        suggested_tags=suggested_tags,
        auto_mode=recommendation.recommended_mode == "auto",
    )
    key_behaviors = generate_key_behaviors(
        classification=classification,
        capabilities=capabilities,
        risk=risk,
        prompt_signals=prompt_signals,
    )
    cost = estimate_diagnostic_cost(
        risk=risk,
        capabilities=capabilities,
        coverage=eval_coverage,
        suggested_round_plan=round_plan,
        prompt_signals=prompt_signals,
    )

    plan = TriagePlan(
        triage_id=now.strftime("triage_%Y%m%d_%H%M%S"),
        created_at=now.replace(microsecond=0).isoformat(),
        project_root=str(project_root),
        input_sources=discovery.input_sources(),
        agent_summary=agent_summary,
        detected_capabilities=capabilities,
        agent_classification=classification,
        risk_assessment=risk,
        eval_coverage=eval_coverage,
        key_behaviors_to_test=key_behaviors,
        missing_information=missing_information,
        warnings=warnings,
        suggested_test_tags=suggested_tags,
        suggested_round_plan=round_plan,
        baseline_status=baseline_status,
        patch_preview_readiness=patch_readiness,
        auto_readiness=auto_readiness,
        estimated_diagnostic_cost=cost,
        recommendation=recommendation,
        recommended_next_command=next_command,
        report_paths={},
    )
    write_triage_reports(plan, output_dir)
    return plan


def _agent_arg_for_command(agent: Path | None) -> str | None:
    if agent is None:
        return None
    return agent.as_posix()


def _dedupe_warnings(items):
    seen = set()
    result = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        result.append(item)
    return result
