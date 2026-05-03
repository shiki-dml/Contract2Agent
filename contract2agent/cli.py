from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from contract2agent.baseline import (
    compare_against_baseline,
    format_baseline_saved_summary,
    format_comparison_summary,
    save_baseline,
)
from contract2agent.checker import CheckResult, check_trace, check_trace_file
from contract2agent.compiler import (
    compile_contract,
    create_demo_project,
    create_project_from_requirement,
)
from contract2agent.counterexamples import generate_counterexamples
from contract2agent.diagnosis import (
    diagnose_evaluation,
    explain_trace_result,
    write_regression_traces,
    write_diagnosis_report_markdown,
    write_diagnosis_report_yaml,
)
from contract2agent.diagnostic_modes import (
    ReviewPolicy,
    auto_mode_warnings,
    default_contract,
    format_console_report,
    run_auto_diagnosis,
    run_deep_diagnosis,
    run_quick_diagnosis,
)
from contract2agent.capabilities import (
    format_capability_report,
    generate_capability_report,
    write_capability_eval_cases,
    write_capability_report,
)
from contract2agent.cost_estimate import CostEstimateOptions, run_cost_estimate
from contract2agent.schema import load_contract, model_to_dict
from contract2agent.triage import TriageOptions, run_triage
from contract2agent.triage.report import (
    format_json_report as format_triage_json_report,
    format_terminal_summary as format_triage_terminal_summary,
)
from contract2agent.patch_preview import PatchPreviewOptions, run_patch_preview
from contract2agent.patch_preview.report import (
    format_json_report as format_patch_preview_json_report,
    format_terminal_summary as format_patch_preview_terminal_summary,
)

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is a declared dependency.
    yaml = None  # type: ignore[assignment]

try:
    import typer

    _HAS_TYPER = True
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs.
    typer = None  # type: ignore[assignment]
    _HAS_TYPER = False

try:
    from rich.console import Console

    console = Console(markup=False)
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs.

    class _PlainConsole:
        def print(self, message: str) -> None:
            print(message)

    console = _PlainConsole()


def _cmd_new(requirement: str, out: Path) -> None:
    target = create_project_from_requirement(requirement, out)
    console.print(f"Created AgentTraceDoctor project at {target}")


def _cmd_compile(contract: Path, out: Path) -> None:
    target = compile_contract(contract, out)
    console.print(f"Compiled contract into project at {target}")


def _cmd_check(contract: Path, trace: Path) -> int:
    loaded_contract = load_contract(contract)
    result = check_trace_file(loaded_contract, trace)
    if result.passed:
        console.print("PASS: trace satisfies the contract")
        return 0

    console.print("FAIL: trace violates the contract")
    for failure in result.failures:
        console.print(f"- {failure}")
    return 1


def _cmd_demo(out: Path) -> None:
    target = create_demo_project(out)
    console.print(f"Demo project created at {target}")


def _cmd_counterexamples(contract: Path, out: Path) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required to write the counterexample manifest.")
    loaded_contract = load_contract(contract)
    cases = generate_counterexamples(loaded_contract)
    out.mkdir(parents=True, exist_ok=True)

    for case in cases:
        (out / f"{case.name}.json").write_text(
            json.dumps(case.trace, indent=2) + "\n",
            encoding="utf-8",
        )

    manifest = {
        "cases": [
            {
                "name": case.name,
                "description": case.description,
                "expected_to_fail": case.expected_to_fail,
                "expected_rule": case.expected_rule,
            }
            for case in cases
        ]
    }
    (out / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )
    console.print(f"Wrote {len(cases)} counterexample traces to {out}")


def _cmd_restrictions(contract: Path) -> None:
    loaded_contract = load_contract(contract)
    data = model_to_dict(loaded_contract)
    summary = {
        "forbidden_tools": data.get("forbidden_tools", []),
        "forbidden_capabilities": [
            {
                "name": capability.get("name"),
                "kind": capability.get("kind"),
                "description": capability.get("description"),
                "keywords": capability.get("keywords", []),
                "forbidden_tools": capability.get("forbidden_tools", []),
            }
            for capability in data.get("forbidden_capabilities", [])
        ],
    }
    if yaml is not None:
        console.print(yaml.safe_dump(summary, sort_keys=False))
    else:
        console.print(json.dumps(summary, indent=2, ensure_ascii=False))


def _cmd_capabilities(
    contract: Path,
    eval_report: Path | None = None,
    out: Path | None = None,
    generate_tests: Path | None = None,
) -> None:
    loaded_contract = load_contract(contract)
    report = generate_capability_report(
        loaded_contract,
        str(eval_report) if eval_report is not None else None,
    )
    console.print(format_capability_report(report).rstrip())

    if out is not None:
        write_capability_report(report, out)
        console.print(f"Wrote capability report to {out}")

    if generate_tests is not None:
        write_capability_eval_cases(report, generate_tests)
        console.print(f"Wrote suggested capability eval cases to {generate_tests}")


def _cmd_triage(
    agent: Path | None = None,
    goal: str | None = None,
    project_root: Path = Path("."),
    output_format: str = "markdown",
    output: Path | None = None,
    allow_auto: bool = False,
    include_cost: bool = False,
) -> int:
    plan = run_triage(
        TriageOptions(
            project_root=project_root,
            agent=agent,
            goal=goal,
            output=output,
            allow_auto=allow_auto,
        )
    )
    normalized = output_format.casefold()
    if normalized == "json":
        console.print(format_triage_json_report(plan).rstrip())
    elif normalized == "markdown":
        console.print(format_triage_terminal_summary(plan))
    else:
        raise ValueError("--format must be markdown or json")
    if include_cost:
        latest_triage_json = Path(
            plan.report_paths.get("latest_json", ".agentdoctor/triage/latest.json")
        )
        estimate, summary = run_cost_estimate(
            CostEstimateOptions(
                from_triage=latest_triage_json,
                output_format="markdown",
            ),
            cwd=Path(plan.project_root),
        )
        console.print("")
        console.print(summary.rstrip())
        console.print(
            f"Wrote cost estimate to {estimate.report_paths.get('latest_markdown', '.agentdoctor/cost/latest.md')}"
        )
    return 0


def _cmd_patch_preview(
    from_run: Path | None = None,
    from_findings: Path | None = None,
    failure_type: str | None = None,
    output: Path | None = None,
    output_format: str = "markdown",
    dry_run: bool = True,
    allow_apply: bool = False,
    apply_patch_id: str | None = None,
    project_root: Path = Path("."),
) -> int:
    report = run_patch_preview(
        PatchPreviewOptions(
            project_root=project_root,
            from_run=from_run,
            from_findings=from_findings,
            failure_type=failure_type,
            output=output,
            output_format=output_format,
            dry_run=dry_run,
            allow_apply=allow_apply,
            apply_patch_id=apply_patch_id,
        )
    )
    normalized = output_format.casefold()
    if normalized == "json":
        console.print(format_patch_preview_json_report(report).rstrip())
    elif normalized == "markdown":
        console.print(format_patch_preview_terminal_summary(report))
    else:
        raise ValueError("--format must be markdown or json")
    return 0


def _cmd_cost_estimate(
    from_triage: Path | None = None,
    mode: str | None = None,
    budget: str = "balanced",
    max_rounds: int | None = None,
    max_tests: int | None = None,
    max_runtime_minutes: int | None = None,
    max_llm_calls: int | None = None,
    max_tool_calls: int | None = None,
    max_tool_calls_per_test: int | None = None,
    max_repeated_runs: int | None = None,
    max_auto_iterations: int | None = None,
    max_patch_attempts: int | None = None,
    output: Path | None = None,
    output_format: str = "markdown",
) -> int:
    _, rendered = run_cost_estimate(
        CostEstimateOptions(
            from_triage=from_triage,
            mode=mode,
            budget_profile=budget,
            max_rounds=max_rounds,
            max_tests=max_tests,
            max_runtime_minutes=max_runtime_minutes,
            max_llm_calls=max_llm_calls,
            max_tool_calls=max_tool_calls,
            max_tool_calls_per_test=max_tool_calls_per_test,
            max_repeated_runs=max_repeated_runs,
            max_auto_iterations=max_auto_iterations,
            max_patch_attempts=max_patch_attempts,
            output=output,
            output_format=output_format,
        )
    )
    console.print(rendered.rstrip())
    return 0


def _mode_contract(contract: Path | None = None) -> Any:
    if contract is not None:
        return load_contract(contract)
    local_contract = Path("agent_contract.yaml")
    if local_contract.exists():
        return load_contract(local_contract)
    return default_contract()


def _command_string() -> str:
    command = Path(sys.argv[0]).name
    if command in {"cli.py", "__main__.py"}:
        command = "agentdoctor"
    return " ".join([command, *sys.argv[1:]])


def _normalize_optional_compare_baseline_args(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    for index, item in enumerate(argv):
        normalized.append(item)
        if item != "--compare-baseline":
            continue
        next_item = argv[index + 1] if index + 1 < len(argv) else None
        if next_item is None or next_item.startswith("-"):
            normalized.append("latest")
    return normalized


def main() -> None:
    sys.argv[:] = _normalize_optional_compare_baseline_args(sys.argv)
    app()


def _parse_focus_tags(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _handle_baseline_actions(
    *,
    report: Any,
    out: Path,
    project_root: Path = Path("."),
    agent: Path | None = None,
    save_baseline_flag: bool = False,
    baseline_name: str | None = None,
    compare_baseline_ref: str | None = None,
) -> int:
    if save_baseline_flag:
        saved = save_baseline(
            report=report,
            project_root=project_root,
            baseline_name=baseline_name,
            command=_command_string(),
            agent_config_path=agent,
            report_dir=out,
        )
        console.print("")
        console.print(format_baseline_saved_summary(saved))

    if compare_baseline_ref is not None:
        compared = compare_against_baseline(
            report=report,
            project_root=project_root,
            baseline_ref=compare_baseline_ref or "latest",
            command=_command_string(),
            agent_config_path=agent,
        )
        console.print("")
        if compared.comparison is None:
            console.print("Baseline Comparison")
            for warning in compared.warnings:
                console.print(f"Warning: {warning}")
            return 1
        console.print(format_comparison_summary(compared.comparison))
        if compared.markdown_path is not None:
            console.print(f"Wrote baseline comparison to {compared.markdown_path}")
    return 0


def _cmd_quick(
    contract: Path | None = None,
    out: Path = Path("reports"),
    agent: Path | None = None,
    save_baseline_flag: bool = False,
    baseline_name: str | None = None,
    compare_baseline_ref: str | None = None,
) -> int:
    report = run_quick_diagnosis(contract=_mode_contract(contract), out_dir=out)
    console.print(format_console_report(report))
    console.print(f"Wrote diagnostic report to {out / 'latest.md'}")
    return _handle_baseline_actions(
        report=report,
        out=out,
        agent=agent,
        save_baseline_flag=save_baseline_flag,
        baseline_name=baseline_name,
        compare_baseline_ref=compare_baseline_ref,
    )


def _cmd_deep(
    rounds: int,
    review: str = ReviewPolicy.ON_FAIL.value,
    contract: Path | None = None,
    out: Path = Path("reports"),
    agent: Path | None = None,
    save_baseline_flag: bool = False,
    baseline_name: str | None = None,
    compare_baseline_ref: str | None = None,
    focus: str | None = None,
) -> int:
    report = run_deep_diagnosis(
        rounds=rounds,
        review_policy=review,
        contract=_mode_contract(contract),
        out_dir=out,
        focus_tags=_parse_focus_tags(focus),
    )
    console.print(format_console_report(report))
    console.print(f"Wrote diagnostic report to {out / 'latest.md'}")
    return _handle_baseline_actions(
        report=report,
        out=out,
        agent=agent,
        save_baseline_flag=save_baseline_flag,
        baseline_name=baseline_name,
        compare_baseline_ref=compare_baseline_ref,
    )


def _cmd_auto(
    target_confidence: float = 0.85,
    max_rounds: int = 6,
    max_time_minutes: int = 30,
    max_patches: int = 8,
    min_improvement: float = 0.03,
    review: str = ReviewPolicy.ON_FAIL.value,
    contract: Path | None = None,
    out: Path = Path("reports"),
    repo_root: Path = Path("."),
    agent: Path | None = None,
    save_baseline_flag: bool = False,
    baseline_name: str | None = None,
    compare_baseline_ref: str | None = None,
) -> int:
    for warning in auto_mode_warnings(target_confidence):
        console.print(warning)
    report = run_auto_diagnosis(
        target_confidence=target_confidence,
        max_rounds=max_rounds,
        max_time_minutes=max_time_minutes,
        max_patches=max_patches,
        min_improvement=min_improvement,
        review_policy=review,
        contract=_mode_contract(contract),
        out_dir=out,
        repo_root=repo_root,
    )
    console.print(format_console_report(report))
    console.print(f"Wrote diagnostic report to {out / 'latest.md'}")
    return _handle_baseline_actions(
        report=report,
        out=out,
        project_root=repo_root,
        agent=agent,
        save_baseline_flag=save_baseline_flag,
        baseline_name=baseline_name,
        compare_baseline_ref=compare_baseline_ref,
    )


def _cmd_check_all(
    contract: Path,
    traces: Path,
    diagnose: bool = False,
    profile: str = "balanced",
    write_regression_traces_dir: Path | None = None,
) -> int:
    loaded_contract = load_contract(contract)
    manifest = _load_manifest(traces / "manifest.yaml")
    report_rows: list[dict[str, Any]] = []
    unexpected = False

    for trace_path in sorted(traces.glob("*.json")):
        case_name = trace_path.stem
        expected = manifest.get(case_name, {})
        expected_to_fail = expected.get("expected_to_fail")
        result = _check_trace_path(loaded_contract, trace_path, expected_to_fail)
        status = _comparison_status(result, expected_to_fail)
        if status in {"PASS unexpectedly", "FAIL unexpectedly"}:
            unexpected = True
        note = _status_note(status)
        console.print(
            f"[{status}] {case_name}: {result.rule or '-'} - "
            f"{result.message or '-'}"
        )
        if note:
            console.print(f"  {note}")
        report_rows.append(
            {
                "case": case_name,
                "description": expected.get("description", ""),
                "expected_to_fail": expected_to_fail,
                "expected_rule": expected.get("expected_rule"),
                "actual_failed": not result.passed,
                "status": status,
                "rule": result.rule,
                "message": result.message,
                "evidence": _brief_evidence(result),
                "note": note,
            }
        )

    report_path = contract.parent / "reports" / "counterexample_report.md"
    _write_counterexample_report(report_path, report_rows)
    console.print(f"Wrote counterexample report to {report_path}")

    if diagnose:
        diagnosis_path = contract.parent / "reports" / "diagnosis_report.md"
        _write_diagnosis_for_traces(
            loaded_contract=loaded_contract,
            traces_dir=traces,
            manifest=manifest,
            out=diagnosis_path,
            output_format="markdown",
            profile=profile,
            write_regression_traces_dir=write_regression_traces_dir,
        )
        console.print(f"Wrote diagnosis report to {diagnosis_path}")
    return 1 if unexpected else 0


def _cmd_diagnose(
    contract: Path,
    traces: Path,
    manifest_path: Path | None,
    out: Path,
    requirement: Path | None = None,
    eval_dataset: Path | None = None,
    output_format: str = "markdown",
    profile: str = "balanced",
    write_regression_traces_dir: Path | None = None,
) -> int:
    loaded_contract = load_contract(contract)
    manifest = _load_manifest(manifest_path or traces / "manifest.yaml")
    requirement_text = (
        requirement.read_text(encoding="utf-8") if requirement is not None else None
    )
    eval_data = _load_yaml_mapping(eval_dataset) if eval_dataset is not None else None
    _write_diagnosis_for_traces(
        loaded_contract=loaded_contract,
        traces_dir=traces,
        manifest=manifest,
        out=out,
        output_format=output_format,
        requirement_text=requirement_text,
        eval_dataset=eval_data,
        profile=profile,
        write_regression_traces_dir=write_regression_traces_dir,
    )
    console.print(f"Wrote diagnosis report to {out}")
    return 0


def _cmd_why(
    contract: Path,
    trace: Path,
    manifest_path: Path | None = None,
    requirement: Path | None = None,
    out: Path | None = None,
    profile: str = "balanced",
) -> int:
    loaded_contract = load_contract(contract)
    loaded_trace = load_trace_file_or_empty(trace)
    manifest = _load_manifest(manifest_path) if manifest_path is not None else {}
    manifest_case = manifest.get(trace.stem, {})
    result = check_trace(
        loaded_contract,
        loaded_trace,
        expected_failure=manifest_case.get("expected_to_fail"),
    )
    requirement_text = (
        requirement.read_text(encoding="utf-8") if requirement is not None else None
    )
    explanation = explain_trace_result(
        loaded_contract,
        loaded_trace,
        result,
        manifest_case=manifest_case,
        requirement_text=requirement_text,
        profile=profile,
    )
    lines = _why_report_lines(explanation)
    console.print("\n".join(lines))
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(["# Why Report", "", *lines]) + "\n", encoding="utf-8")
        console.print(f"Wrote why report to {out}")
    return 0


def _write_diagnosis_for_traces(
    *,
    loaded_contract: Any,
    traces_dir: Path,
    manifest: dict[str, dict[str, Any]],
    out: Path,
    output_format: str,
    requirement_text: str | None = None,
    eval_dataset: dict[str, Any] | None = None,
    profile: str = "balanced",
    write_regression_traces_dir: Path | None = None,
) -> None:
    traces_by_case = _load_trace_directory(traces_dir)
    check_rows: list[dict[str, Any]] = []
    for case_name in sorted(traces_by_case):
        expected = manifest.get(case_name, {})
        result = check_trace(
            loaded_contract,
            traces_by_case[case_name],
            expected_failure=expected.get("expected_to_fail"),
        )
        check_rows.append(_check_result_row(case_name, result, expected))

    report = diagnose_evaluation(
        loaded_contract,
        check_rows,
        traces_by_case,
        manifest=manifest,
        requirement_text=requirement_text,
        eval_dataset=eval_dataset,
        profile=profile,
    )
    normalized_format = output_format.casefold()
    if normalized_format == "markdown":
        write_diagnosis_report_markdown(report, out)
        if write_regression_traces_dir is not None:
            count = write_regression_traces(report, write_regression_traces_dir)
            console.print(
                f"Wrote {count} regression trace(s) to {write_regression_traces_dir}"
            )
        return
    if normalized_format == "yaml":
        write_diagnosis_report_yaml(report, out)
        if write_regression_traces_dir is not None:
            count = write_regression_traces(report, write_regression_traces_dir)
            console.print(
                f"Wrote {count} regression trace(s) to {write_regression_traces_dir}"
            )
        return
    raise ValueError("--format must be markdown or yaml")


def _load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    if yaml is None or not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = data.get("cases", []) if isinstance(data, dict) else []
    manifest: dict[str, dict[str, Any]] = {}
    for case in cases:
        if isinstance(case, dict) and "name" in case:
            manifest[str(case["name"])] = case
    return manifest


def _check_trace_path(
    contract: Any,
    trace_path: Path,
    expected_to_fail: bool | None,
) -> CheckResult:
    try:
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result = CheckResult(passed=True, expected_failure=expected_to_fail)
        result.add_failure(
            f"Trace JSON could not be parsed: {exc.msg}. "
            "This violates rule: malformed_trace.",
            rule="malformed_trace",
            evidence={"path": str(trace_path), "line": exc.lineno, "column": exc.colno},
        )
        return result
    return check_trace(contract, trace, expected_failure=expected_to_fail)


def _load_trace_directory(traces: Path) -> dict[str, list[dict[str, Any]]]:
    loaded: dict[str, list[dict[str, Any]]] = {}
    for trace_path in sorted(traces.glob("*.json")):
        try:
            data = json.loads(trace_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded[trace_path.stem] = []
            continue
        loaded[trace_path.stem] = data if isinstance(data, list) else []
    return loaded


def load_trace_file_or_empty(trace: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(trace.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _load_yaml_mapping(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    if yaml is None:
        raise RuntimeError("PyYAML is required to read YAML files.")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def _check_result_row(
    case_name: str,
    result: CheckResult,
    expected: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case": case_name,
        "passed": result.passed,
        "expected_to_fail": expected.get("expected_to_fail"),
        "expected_rule": expected.get("expected_rule"),
        "rule": result.rule,
        "message": result.message,
        "failures": result.failures,
        "evidence": result.evidence,
    }


def _why_report_lines(explanation: dict[str, Any]) -> list[str]:
    lines = [
        f"Result: {explanation['result']}",
        "",
        "Natural-language explanation:",
        str(explanation["natural_language_cause"]),
        "",
        f"Relevant rule: {explanation.get('rule') or '-'}",
        f"Strictness: {explanation.get('strictness') or '-'}",
        f"Affected agent part: {explanation.get('affected_agent_part') or '-'}",
        f"Likely location: {explanation.get('likely_location') or '-'}",
        "",
        f"Suggested fix: {explanation.get('suggested_fix') or '-'}",
    ]
    evidence = explanation.get("evidence")
    if evidence:
        lines.extend(["", "Evidence:", json.dumps(evidence, indent=2, sort_keys=True)])
    return lines


def _comparison_status(result: CheckResult, expected_to_fail: Any) -> str:
    if expected_to_fail is True and not result.passed:
        return "FAIL as expected"
    if expected_to_fail is False and result.passed:
        return "PASS as expected"
    if expected_to_fail is True and result.passed:
        return "PASS unexpectedly"
    if expected_to_fail is False and not result.passed:
        return "FAIL unexpectedly"
    return "PASS" if result.passed else "FAIL"


def _status_note(status: str) -> str:
    if status == "PASS unexpectedly":
        return "This may indicate a missing rule or checker bug."
    if status == "FAIL unexpectedly":
        return "This may indicate an overly strict checker."
    return ""


def _brief_evidence(result: CheckResult) -> str:
    if not result.evidence:
        return "-"
    parts = []
    for key in ("step", "tool", "error_step", "after_tool", "missing", "event_count"):
        if key in result.evidence:
            parts.append(f"{key}={result.evidence[key]}")
    if parts:
        return ", ".join(parts)
    return json.dumps(result.evidence, sort_keys=True)


def _write_counterexample_report(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Counterexample Report",
        "",
        "| Case | Expected | Actual | Status | Rule | Message | Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        expected = _expected_label(row["expected_to_fail"])
        actual = "FAIL" if row["actual_failed"] else "PASS"
        rule = row["rule"] or "-"
        message = _escape_table_text(row["message"] or "-")
        evidence = _escape_table_text(row["evidence"])
        lines.append(
            f"| {row['case']} | {expected} | {actual} | {row['status']} | "
            f"{rule} | {message} | {evidence} |"
        )
        if row["note"]:
            lines.append(
                f"| {row['case']} note | - | - | - | - | "
                f"{_escape_table_text(row['note'])} | - |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _expected_label(expected_to_fail: Any) -> str:
    if expected_to_fail is True:
        return "FAIL"
    if expected_to_fail is False:
        return "PASS"
    return "unknown"


def _escape_table_text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


if _HAS_TYPER:
    app = typer.Typer(help="Offline trace diagnosis for LLM agent behavior.")

    @app.command()
    def new(
        requirement: str,
        out: Path = typer.Option(..., "--out", "-o", help="Output directory."),
    ) -> None:
        _cmd_new(requirement, out)

    @app.command(name="compile")
    def compile_command(
        contract: Path = typer.Argument(..., help="Path to agent_contract.yaml."),
        out: Path = typer.Option(..., "--out", "-o", help="Output directory."),
    ) -> None:
        _cmd_compile(contract, out)

    @app.command()
    def check(
        contract: Path = typer.Option(..., "--contract", help="Path to contract YAML."),
        trace: Path = typer.Option(..., "--trace", help="Path to trace JSON."),
    ) -> None:
        raise typer.Exit(_cmd_check(contract, trace))

    @app.command()
    def demo(
        out: Path = typer.Option("demo_project", "--out", "-o", help="Output directory."),
    ) -> None:
        _cmd_demo(out)

    @app.command()
    def quick(
        contract: Path | None = typer.Option(
            None,
            "--contract",
            help="Optional path to agent_contract.yaml. Defaults to ./agent_contract.yaml or a built-in sample contract.",
        ),
        out: Path = typer.Option(
            Path("reports"),
            "--out",
            "-o",
            help="Report output directory.",
        ),
        agent: Path | None = typer.Option(
            None,
            "--agent",
            help="Optional agent config path used for baseline snapshots.",
        ),
        save_baseline_flag: bool = typer.Option(
            False,
            "--save-baseline",
            help="Save this diagnostic run as an AgentDoctor baseline.",
        ),
        baseline_name: str | None = typer.Option(
            None,
            "--baseline-name",
            help="Optional human-readable name for a saved baseline.",
        ),
        compare_baseline_ref: str | None = typer.Option(
            None,
            "--compare-baseline",
            help="Compare this run with a saved baseline. Use latest or a baseline name.",
        ),
    ) -> None:
        raise typer.Exit(
            _cmd_quick(
                contract,
                out,
                agent,
                save_baseline_flag,
                baseline_name,
                compare_baseline_ref,
            )
        )

    @app.command()
    def deep(
        rounds: int = typer.Option(..., "--rounds", help="Number of diagnosis rounds."),
        review: str = typer.Option(
            ReviewPolicy.ON_FAIL.value,
            "--review",
            help="Review policy: never, on-fail, or each-round.",
        ),
        contract: Path | None = typer.Option(
            None,
            "--contract",
            help="Optional path to agent_contract.yaml. Defaults to ./agent_contract.yaml or a built-in sample contract.",
        ),
        out: Path = typer.Option(
            Path("reports"),
            "--out",
            "-o",
            help="Report output directory.",
        ),
        agent: Path | None = typer.Option(
            None,
            "--agent",
            help="Optional agent config path used for baseline snapshots.",
        ),
        save_baseline_flag: bool = typer.Option(
            False,
            "--save-baseline",
            help="Save this diagnostic run as an AgentDoctor baseline.",
        ),
        baseline_name: str | None = typer.Option(
            None,
            "--baseline-name",
            help="Optional human-readable name for a saved baseline.",
        ),
        compare_baseline_ref: str | None = typer.Option(
            None,
            "--compare-baseline",
            help="Compare this run with a saved baseline. Use latest or a baseline name.",
        ),
        focus: str | None = typer.Option(
            None,
            "--focus",
            help="Optional comma-separated failure-type focus tags.",
        ),
    ) -> None:
        raise typer.Exit(
            _cmd_deep(
                rounds,
                review,
                contract,
                out,
                agent,
                save_baseline_flag,
                baseline_name,
                compare_baseline_ref,
                focus,
            )
        )

    @app.command()
    def auto(
        target_confidence: float = typer.Option(
            0.85,
            "--target-confidence",
            help="Heuristic diagnostic confidence target.",
        ),
        max_rounds: int = typer.Option(
            6,
            "--max-rounds",
            help="Maximum auto diagnosis/repair rounds.",
        ),
        max_time_minutes: int = typer.Option(
            30,
            "--max-time-minutes",
            help="Maximum auto mode runtime budget in minutes.",
        ),
        max_patches: int = typer.Option(
            8,
            "--max-patches",
            help="Maximum allowlisted prompt/config patches.",
        ),
        min_improvement: float = typer.Option(
            0.03,
            "--min-improvement",
            help="Minimum useful confidence improvement between rounds.",
        ),
        review: str = typer.Option(
            ReviewPolicy.ON_FAIL.value,
            "--review",
            help="Review policy: never, on-fail, or each-round.",
        ),
        contract: Path | None = typer.Option(
            None,
            "--contract",
            help="Optional path to agent_contract.yaml. Defaults to ./agent_contract.yaml or a built-in sample contract.",
        ),
        out: Path = typer.Option(
            Path("reports"),
            "--out",
            "-o",
            help="Report output directory.",
        ),
        repo_root: Path = typer.Option(
            Path("."),
            "--repo-root",
            help="Repository root used for allowlisted auto patch targets.",
        ),
        agent: Path | None = typer.Option(
            None,
            "--agent",
            help="Optional agent config path used for baseline snapshots.",
        ),
        save_baseline_flag: bool = typer.Option(
            False,
            "--save-baseline",
            help="Save this diagnostic run as an AgentDoctor baseline.",
        ),
        baseline_name: str | None = typer.Option(
            None,
            "--baseline-name",
            help="Optional human-readable name for a saved baseline.",
        ),
        compare_baseline_ref: str | None = typer.Option(
            None,
            "--compare-baseline",
            help="Compare this run with a saved baseline. Use latest or a baseline name.",
        ),
    ) -> None:
        raise typer.Exit(
            _cmd_auto(
                target_confidence,
                max_rounds,
                max_time_minutes,
                max_patches,
                min_improvement,
                review,
                contract,
                out,
                repo_root,
                agent,
                save_baseline_flag,
                baseline_name,
                compare_baseline_ref,
            )
        )

    @app.command()
    def triage(
        agent: Path | None = typer.Option(
            None,
            "--agent",
            help="Optional path to the agent config to inspect.",
        ),
        goal: str | None = typer.Option(
            None,
            "--goal",
            help="Optional user goal used as an additional static classification signal.",
        ),
        project_root: Path = typer.Option(
            Path("."),
            "--project-root",
            help="Project root to inspect. Defaults to the current working directory.",
        ),
        triage_format: str = typer.Option(
            "markdown",
            "--format",
            help="Terminal output format: markdown or json. Reports always write both formats.",
        ),
        output: Path | None = typer.Option(
            None,
            "--output",
            help="Report output directory. Defaults to .agentdoctor/triage/ under the project root.",
        ),
        allow_auto: bool = typer.Option(
            False,
            "--allow-auto",
            help="Allow triage to recommend auto mode when readiness checks pass.",
        ),
        include_cost: bool = typer.Option(
            False,
            "--include-cost",
            help="Also write a static pre-run time/cost estimate from the triage report.",
        ),
    ) -> None:
        raise typer.Exit(
            _cmd_triage(
                agent,
                goal,
                project_root,
                triage_format,
                output,
                allow_auto,
                include_cost,
            )
        )

    @app.command(name="cost-estimate")
    def cost_estimate(
        from_triage: Path | None = typer.Option(
            None,
            "--from-triage",
            help="Path to a triage JSON report. Defaults to .agentdoctor/triage/latest.json.",
        ),
        mode: str | None = typer.Option(
            None,
            "--mode",
            help="Mode to estimate: quick, deep, or auto. Defaults to the triage recommendation.",
        ),
        budget: str = typer.Option(
            "balanced",
            "--budget",
            help="Budget profile: conservative, balanced, or thorough.",
        ),
        max_rounds: int | None = typer.Option(None, "--max-rounds"),
        max_tests: int | None = typer.Option(None, "--max-tests"),
        max_runtime_minutes: int | None = typer.Option(None, "--max-runtime-minutes"),
        max_llm_calls: int | None = typer.Option(None, "--max-llm-calls"),
        max_tool_calls: int | None = typer.Option(None, "--max-tool-calls"),
        max_tool_calls_per_test: int | None = typer.Option(
            None,
            "--max-tool-calls-per-test",
        ),
        max_repeated_runs: int | None = typer.Option(None, "--max-repeated-runs"),
        max_auto_iterations: int | None = typer.Option(None, "--max-auto-iterations"),
        max_patch_attempts: int | None = typer.Option(None, "--max-patch-attempts"),
        output: Path | None = typer.Option(
            None,
            "--output",
            help="Report output directory. Defaults to .agentdoctor/cost/ under the project root.",
        ),
        cost_format: str = typer.Option(
            "markdown",
            "--format",
            help="Terminal output format: markdown summary or full json. Reports always write both.",
        ),
    ) -> None:
        raise typer.Exit(
            _cmd_cost_estimate(
                from_triage,
                mode,
                budget,
                max_rounds,
                max_tests,
                max_runtime_minutes,
                max_llm_calls,
                max_tool_calls,
                max_tool_calls_per_test,
                max_repeated_runs,
                max_auto_iterations,
                max_patch_attempts,
                output,
                cost_format,
            )
        )

    @app.command(name="patch-preview")
    def patch_preview_command(
        from_run: Path | None = typer.Option(
            None,
            "--from-run",
            help="Path to a diagnostic run/report JSON file.",
        ),
        from_findings: Path | None = typer.Option(
            None,
            "--from-findings",
            help="Path to a findings/report JSON file.",
        ),
        failure_type: str | None = typer.Option(
            None,
            "--failure-type",
            help="Optional failure type filter, such as OUTPUT_SCHEMA_ERROR.",
        ),
        output: Path | None = typer.Option(
            None,
            "--output",
            "-o",
            help="Output directory. Defaults to .agentdoctor/patches/.",
        ),
        patch_format: str = typer.Option(
            "markdown",
            "--format",
            help="Terminal output format: markdown or json. Reports always write both formats.",
        ),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--no-dry-run",
            help="Preview-only mode. Patch Preview v0.1 never applies by default.",
        ),
        allow_apply: bool = typer.Option(
            False,
            "--allow-apply",
            help="Accepted for forward compatibility; v0.1 remains preview-only.",
        ),
        apply_patch_id: str | None = typer.Option(
            None,
            "--apply",
            help="Patch id to apply. v0.1 refuses apply and writes a preview-only report.",
        ),
        project_root: Path = typer.Option(
            Path("."),
            "--project-root",
            help="Project root used for safe target selection.",
        ),
    ) -> None:
        raise typer.Exit(
            _cmd_patch_preview(
                from_run,
                from_findings,
                failure_type,
                output,
                patch_format,
                dry_run,
                allow_apply,
                apply_patch_id,
                project_root,
            )
        )

    @app.command()
    def counterexamples(
        contract: Path = typer.Argument(..., help="Path to agent_contract.yaml."),
        out: Path = typer.Option(
            ...,
            "--out",
            "-o",
            help="Output directory for generated traces.",
        ),
    ) -> None:
        _cmd_counterexamples(contract, out)

    @app.command(name="check-all")
    def check_all(
        contract: Path = typer.Option(..., "--contract", help="Path to contract YAML."),
        traces: Path = typer.Option(..., "--traces", help="Directory of trace JSON files."),
        diagnose: bool = typer.Option(
            False,
            "--diagnose",
            help="Also write reports/diagnosis_report.md.",
        ),
        profile: str = typer.Option(
            "balanced",
            "--profile",
            help="Diagnosis profile: permissive, balanced, or strict.",
        ),
        write_regression_traces_dir: Path | None = typer.Option(
            None,
            "--write-regression-traces",
            help="Optional directory for suggested regression trace JSON files.",
        ),
    ) -> None:
        raise typer.Exit(
            _cmd_check_all(
                contract,
                traces,
                diagnose,
                profile,
                write_regression_traces_dir,
            )
        )

    @app.command()
    def diagnose(
        contract: Path = typer.Option(..., "--contract", help="Path to contract YAML."),
        traces: Path = typer.Option(..., "--traces", help="Directory of trace JSON files."),
        manifest: Path | None = typer.Option(
            None,
            "--manifest",
            help="Optional counterexample manifest YAML.",
        ),
        out: Path = typer.Option(..., "--out", "-o", help="Diagnosis report path."),
        requirement: Path | None = typer.Option(
            None,
            "--requirement",
            help="Optional natural-language requirement text file.",
        ),
        eval_dataset: Path | None = typer.Option(
            None,
            "--eval-dataset",
            help="Optional user eval dataset YAML.",
        ),
        diagnosis_format: str = typer.Option(
            "markdown",
            "--format",
            help="Report format: markdown or yaml.",
        ),
        profile: str = typer.Option(
            "balanced",
            "--profile",
            help="Diagnosis profile: permissive, balanced, or strict.",
        ),
        write_regression_traces_dir: Path | None = typer.Option(
            None,
            "--write-regression-traces",
            help="Optional directory for suggested regression trace JSON files.",
        ),
    ) -> None:
        raise typer.Exit(
            _cmd_diagnose(
                contract,
                traces,
                manifest,
                out,
                requirement,
                eval_dataset,
                diagnosis_format,
                profile,
                write_regression_traces_dir,
            )
        )

    @app.command()
    def why(
        contract: Path = typer.Option(..., "--contract", help="Path to contract YAML."),
        trace: Path = typer.Option(..., "--trace", help="Path to one trace JSON file."),
        manifest: Path | None = typer.Option(
            None,
            "--manifest",
            help="Optional counterexample manifest YAML.",
        ),
        requirement: Path | None = typer.Option(
            None,
            "--requirement",
            help="Optional natural-language requirement text file.",
        ),
        out: Path | None = typer.Option(
            None,
            "--out",
            "-o",
            help="Optional Markdown why report path.",
        ),
        profile: str = typer.Option(
            "balanced",
            "--profile",
            help="Diagnosis profile: permissive, balanced, or strict.",
        ),
    ) -> None:
        raise typer.Exit(_cmd_why(contract, trace, manifest, requirement, out, profile))

    @app.command()
    def restrictions(
        contract: Path = typer.Argument(..., help="Path to agent_contract.yaml."),
    ) -> None:
        _cmd_restrictions(contract)

    @app.command()
    def capabilities(
        contract: Path = typer.Argument(..., help="Path to agent_contract.yaml."),
        eval_report: Path | None = typer.Option(
            None,
            "--eval-report",
            help="Optional evaluation report with PASS evidence.",
        ),
        out: Path | None = typer.Option(
            None,
            "--out",
            "-o",
            help="Optional report output path.",
        ),
        generate_tests: Path | None = typer.Option(
            None,
            "--generate-tests",
            help="Optional output path for suggested eval cases.",
        ),
    ) -> None:
        _cmd_capabilities(contract, eval_report, out, generate_tests)

else:

    def app() -> None:
        raise SystemExit(_main_argparse())


def _main_argparse() -> int:
    parser = argparse.ArgumentParser(prog="c2a")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new")
    new_parser.add_argument("requirement")
    new_parser.add_argument("--out", "-o", required=True, type=Path)

    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("contract", type=Path)
    compile_parser.add_argument("--out", "-o", required=True, type=Path)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--contract", required=True, type=Path)
    check_parser.add_argument("--trace", required=True, type=Path)

    demo_parser = subparsers.add_parser("demo")
    demo_parser.add_argument("--out", "-o", default=Path("demo_project"), type=Path)

    quick_parser = subparsers.add_parser("quick")
    quick_parser.add_argument("--contract", type=Path)
    quick_parser.add_argument("--out", "-o", default=Path("reports"), type=Path)
    quick_parser.add_argument("--agent", type=Path)
    quick_parser.add_argument("--save-baseline", action="store_true")
    quick_parser.add_argument("--baseline-name")
    quick_parser.add_argument("--compare-baseline", nargs="?", const="latest")

    deep_parser = subparsers.add_parser("deep")
    deep_parser.add_argument("--rounds", required=True, type=int)
    deep_parser.add_argument(
        "--review",
        choices=("never", "on-fail", "each-round"),
        default="on-fail",
    )
    deep_parser.add_argument("--contract", type=Path)
    deep_parser.add_argument("--out", "-o", default=Path("reports"), type=Path)
    deep_parser.add_argument("--agent", type=Path)
    deep_parser.add_argument("--save-baseline", action="store_true")
    deep_parser.add_argument("--baseline-name")
    deep_parser.add_argument("--compare-baseline", nargs="?", const="latest")
    deep_parser.add_argument("--focus")

    auto_parser = subparsers.add_parser("auto")
    auto_parser.add_argument("--target-confidence", type=float, default=0.85)
    auto_parser.add_argument("--max-rounds", type=int, default=6)
    auto_parser.add_argument("--max-time-minutes", type=int, default=30)
    auto_parser.add_argument("--max-patches", type=int, default=8)
    auto_parser.add_argument("--min-improvement", type=float, default=0.03)
    auto_parser.add_argument(
        "--review",
        choices=("never", "on-fail", "each-round"),
        default="on-fail",
    )
    auto_parser.add_argument("--contract", type=Path)
    auto_parser.add_argument("--out", "-o", default=Path("reports"), type=Path)
    auto_parser.add_argument("--repo-root", default=Path("."), type=Path)
    auto_parser.add_argument("--agent", type=Path)
    auto_parser.add_argument("--save-baseline", action="store_true")
    auto_parser.add_argument("--baseline-name")
    auto_parser.add_argument("--compare-baseline", nargs="?", const="latest")

    triage_parser = subparsers.add_parser("triage")
    triage_parser.add_argument("--agent", type=Path)
    triage_parser.add_argument("--goal")
    triage_parser.add_argument("--project-root", default=Path("."), type=Path)
    triage_parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
    )
    triage_parser.add_argument("--output", type=Path)
    triage_parser.add_argument("--allow-auto", action="store_true")
    triage_parser.add_argument("--include-cost", action="store_true")

    cost_parser = subparsers.add_parser("cost-estimate")
    cost_parser.add_argument("--from-triage", type=Path)
    cost_parser.add_argument("--mode", choices=("quick", "deep", "auto"))
    cost_parser.add_argument(
        "--budget",
        choices=("conservative", "balanced", "thorough"),
        default="balanced",
    )
    cost_parser.add_argument("--max-rounds", type=int)
    cost_parser.add_argument("--max-tests", type=int)
    cost_parser.add_argument("--max-runtime-minutes", type=int)
    cost_parser.add_argument("--max-llm-calls", type=int)
    cost_parser.add_argument("--max-tool-calls", type=int)
    cost_parser.add_argument("--max-tool-calls-per-test", type=int)
    cost_parser.add_argument("--max-repeated-runs", type=int)
    cost_parser.add_argument("--max-auto-iterations", type=int)
    cost_parser.add_argument("--max-patch-attempts", type=int)
    cost_parser.add_argument("--output", type=Path)
    cost_parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
    )

    patch_preview_parser = subparsers.add_parser("patch-preview")
    patch_preview_parser.add_argument("--from-run", type=Path)
    patch_preview_parser.add_argument("--from-findings", type=Path)
    patch_preview_parser.add_argument("--failure-type")
    patch_preview_parser.add_argument("--output", "-o", type=Path)
    patch_preview_parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
    )
    patch_preview_parser.add_argument("--dry-run", action="store_true", default=True)
    patch_preview_parser.add_argument("--allow-apply", action="store_true")
    patch_preview_parser.add_argument("--apply", dest="apply_patch_id")
    patch_preview_parser.add_argument("--project-root", default=Path("."), type=Path)

    counterexamples_parser = subparsers.add_parser("counterexamples")
    counterexamples_parser.add_argument("contract", type=Path)
    counterexamples_parser.add_argument("--out", "-o", required=True, type=Path)

    check_all_parser = subparsers.add_parser("check-all")
    check_all_parser.add_argument("--contract", required=True, type=Path)
    check_all_parser.add_argument("--traces", required=True, type=Path)
    check_all_parser.add_argument("--diagnose", action="store_true")
    check_all_parser.add_argument(
        "--profile",
        choices=("permissive", "balanced", "strict"),
        default="balanced",
    )
    check_all_parser.add_argument("--write-regression-traces", type=Path)

    diagnose_parser = subparsers.add_parser("diagnose")
    diagnose_parser.add_argument("--contract", required=True, type=Path)
    diagnose_parser.add_argument("--traces", required=True, type=Path)
    diagnose_parser.add_argument("--manifest", type=Path)
    diagnose_parser.add_argument("--out", "-o", required=True, type=Path)
    diagnose_parser.add_argument("--requirement", type=Path)
    diagnose_parser.add_argument("--eval-dataset", type=Path)
    diagnose_parser.add_argument(
        "--profile",
        choices=("permissive", "balanced", "strict"),
        default="balanced",
    )
    diagnose_parser.add_argument("--write-regression-traces", type=Path)
    diagnose_parser.add_argument(
        "--format",
        choices=("markdown", "yaml"),
        default="markdown",
    )

    why_parser = subparsers.add_parser("why")
    why_parser.add_argument("--contract", required=True, type=Path)
    why_parser.add_argument("--trace", required=True, type=Path)
    why_parser.add_argument("--manifest", type=Path)
    why_parser.add_argument("--requirement", type=Path)
    why_parser.add_argument("--out", "-o", type=Path)
    why_parser.add_argument(
        "--profile",
        choices=("permissive", "balanced", "strict"),
        default="balanced",
    )

    restrictions_parser = subparsers.add_parser("restrictions")
    restrictions_parser.add_argument("contract", type=Path)

    capabilities_parser = subparsers.add_parser("capabilities")
    capabilities_parser.add_argument("contract", type=Path)
    capabilities_parser.add_argument("--eval-report", type=Path)
    capabilities_parser.add_argument("--out", "-o", type=Path)
    capabilities_parser.add_argument("--generate-tests", type=Path)

    args = parser.parse_args()
    if args.command == "new":
        _cmd_new(args.requirement, args.out)
        return 0
    if args.command == "compile":
        _cmd_compile(args.contract, args.out)
        return 0
    if args.command == "check":
        return _cmd_check(args.contract, args.trace)
    if args.command == "demo":
        _cmd_demo(args.out)
        return 0
    if args.command == "quick":
        return _cmd_quick(
            args.contract,
            args.out,
            args.agent,
            args.save_baseline,
            args.baseline_name,
            args.compare_baseline,
        )
    if args.command == "deep":
        return _cmd_deep(
            args.rounds,
            args.review,
            args.contract,
            args.out,
            args.agent,
            args.save_baseline,
            args.baseline_name,
            args.compare_baseline,
            args.focus,
        )
    if args.command == "auto":
        return _cmd_auto(
            args.target_confidence,
            args.max_rounds,
            args.max_time_minutes,
            args.max_patches,
            args.min_improvement,
            args.review,
            args.contract,
            args.out,
            args.repo_root,
            args.agent,
            args.save_baseline,
            args.baseline_name,
            args.compare_baseline,
        )
    if args.command == "triage":
        return _cmd_triage(
            args.agent,
            args.goal,
            args.project_root,
            args.format,
            args.output,
            args.allow_auto,
            args.include_cost,
        )
    if args.command == "cost-estimate":
        return _cmd_cost_estimate(
            args.from_triage,
            args.mode,
            args.budget,
            args.max_rounds,
            args.max_tests,
            args.max_runtime_minutes,
            args.max_llm_calls,
            args.max_tool_calls,
            args.max_tool_calls_per_test,
            args.max_repeated_runs,
            args.max_auto_iterations,
            args.max_patch_attempts,
            args.output,
            args.format,
        )
    if args.command == "patch-preview":
        return _cmd_patch_preview(
            args.from_run,
            args.from_findings,
            args.failure_type,
            args.output,
            args.format,
            args.dry_run,
            args.allow_apply,
            args.apply_patch_id,
            args.project_root,
        )
    if args.command == "counterexamples":
        _cmd_counterexamples(args.contract, args.out)
        return 0
    if args.command == "check-all":
        return _cmd_check_all(
            args.contract,
            args.traces,
            args.diagnose,
            args.profile,
            args.write_regression_traces,
        )
    if args.command == "diagnose":
        return _cmd_diagnose(
            args.contract,
            args.traces,
            args.manifest,
            args.out,
            args.requirement,
            args.eval_dataset,
            args.format,
            args.profile,
            args.write_regression_traces,
        )
    if args.command == "why":
        return _cmd_why(
            args.contract,
            args.trace,
            args.manifest,
            args.requirement,
            args.out,
            args.profile,
        )
    if args.command == "restrictions":
        _cmd_restrictions(args.contract)
        return 0
    if args.command == "capabilities":
        _cmd_capabilities(
            args.contract,
            args.eval_report,
            args.out,
            args.generate_tests,
        )
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    main()
