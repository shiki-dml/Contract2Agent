from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from contract2agent.counterexamples import generate_counterexamples
from contract2agent.checker import check_trace
from contract2agent.diagnosis import (
    build_rule_coverage_matrix,
    diagnose_evaluation,
    explain_trace_result,
    write_diagnosis_report_markdown,
)
from contract2agent.diagnosis_schema import (
    AffectedAgentPart,
    DiagnosisCategory,
    RuleCoverageItem,
    Severity,
    Strictness,
    issue_from_legacy_failure,
    make_issue,
)
from contract2agent.parser import parse_requirement
from contract2agent.schema import save_contract


def test_make_issue_enforces_required_protocol_fields() -> None:
    issue = make_issue(
        severity=Severity.ERROR,
        category=DiagnosisCategory.CONTRACT_TOO_LOOSE,
        strictness=Strictness.TOO_LOOSE,
        affected_agent_part=AffectedAgentPart.ERROR_HANDLING,
        summary="Missing-file writes are allowed.",
        evidence={"trace_name": "write_after_missing_file"},
        confidence=0.9,
    )

    assert issue.category == "contract_too_loose"
    assert issue.strictness == "too_loose"
    assert issue.affected_agent_part == "error_handling"
    assert issue.summary
    assert issue.natural_language_cause
    assert issue.evidence
    assert 0.0 <= issue.confidence <= 1.0


def test_make_issue_rejects_empty_summary_and_bad_confidence() -> None:
    with pytest.raises(ValueError):
        make_issue(
            severity="error",
            category="contract_too_loose",
            strictness="too_loose",
            affected_agent_part="error_handling",
            summary="",
        )
    with pytest.raises(ValueError):
        make_issue(
            severity="error",
            category="contract_too_loose",
            strictness="too_loose",
            affected_agent_part="error_handling",
            summary="Bad confidence.",
            confidence=1.5,
        )


def test_legacy_failure_mapping_preserves_old_labels() -> None:
    issue = issue_from_legacy_failure(
        "forbidden_tool_not_caught",
        evidence={"tool": "web_search"},
    )

    assert issue.category == "checker_too_loose"
    assert issue.strictness == "too_loose"
    assert issue.affected_agent_part == "forbidden_tool_control"
    assert issue.natural_language_cause


def test_legacy_rule_failures_map_to_agent_behavior_not_checker_strictness() -> None:
    missing_file_issue = issue_from_legacy_failure(
        "no_write_on_missing_file",
        evidence={"tool": "markdown_writer", "error_status": "file_not_found"},
    )
    order_issue = issue_from_legacy_failure(
        "must_read_before_write",
        evidence={"tool": "markdown_writer", "required_tool": "pdf_reader"},
    )

    assert missing_file_issue.category == "agent_behavior_failure"
    assert missing_file_issue.strictness == "not_applicable"
    assert missing_file_issue.affected_agent_part == "error_handling"
    assert "file_not_found" in missing_file_issue.natural_language_cause
    assert order_issue.category == "agent_behavior_failure"
    assert order_issue.strictness == "not_applicable"
    assert order_issue.affected_agent_part == "tool_ordering"


def test_top_level_tool_result_status_is_supported() -> None:
    contract = parse_requirement(
        "Read a PDF paper, handle file not found, and produce notes."
    )
    trace = [
        {"type": "tool_call", "tool": "pdf_reader", "args": {"path": "missing.pdf"}},
        {"type": "tool_result", "tool": "pdf_reader", "status": "file_not_found"},
        {"type": "tool_call", "tool": "markdown_writer", "args": {"path": "notes.md"}},
        {"type": "tool_result", "tool": "markdown_writer", "status": "ok"},
        {"type": "final_output", "content": "Done."},
    ]

    result = check_trace(contract, trace)

    assert result.passed is False
    assert result.rule == "no_write_on_missing_file"


def test_expected_failure_passed_maps_to_too_loose_contract_or_checker() -> None:
    contract = parse_requirement("Read a PDF paper and produce notes.")
    trace = _missing_file_then_write_trace()

    report = diagnose_evaluation(
        contract,
        [{"case": "write_after_missing_file", "passed": True}],
        {"write_after_missing_file": trace},
        manifest={
            "cases": [
                {
                    "name": "write_after_missing_file",
                    "expected_to_fail": True,
                    "expected_rule": "no_write_on_missing_file",
                }
            ]
        },
    )

    issue = report.issues[0]
    assert issue.id == "ATD001"
    assert issue.strictness == "too_loose"
    assert issue.category in {"contract_too_loose", "checker_too_loose"}
    assert "passed unexpectedly" in issue.summary
    assert "file_not_found" in issue.natural_language_cause


def test_expected_pass_failed_maps_to_too_strict() -> None:
    contract = _paper_reader_contract()
    trace = _counterexample_trace(contract, "valid_read_then_write")

    report = diagnose_evaluation(
        contract,
        [{"case": "valid_read_then_write", "passed": False, "rule": "must_read_before_write"}],
        {"valid_read_then_write": trace},
        manifest={"cases": [{"name": "valid_read_then_write", "expected_to_fail": False}]},
    )

    issue = report.issues[0]
    assert issue.strictness == "too_strict"
    assert issue.category in {"checker_too_strict", "contract_too_strict"}
    assert issue.affected_agent_part == "tool_ordering"


def test_missing_file_then_write_has_patch_and_regression_trace() -> None:
    contract = parse_requirement("Read a PDF paper and produce notes.")
    trace = _missing_file_then_write_trace()

    report = diagnose_evaluation(
        contract,
        [{"case": "write_after_missing_file", "passed": True}],
        {"write_after_missing_file": trace},
        manifest={
            "cases": [
                {
                    "name": "write_after_missing_file",
                    "expected_to_fail": True,
                    "expected_rule": "no_write_on_missing_file",
                }
            ]
        },
    )

    issue = report.issues[0]
    assert issue.affected_agent_part == "error_handling"
    assert issue.strictness == "too_loose"
    assert "file_not_found" in issue.natural_language_cause
    assert "markdown_writer" in issue.natural_language_cause
    assert issue.suggested_patch
    assert issue.suggested_regression_trace


def test_requirement_restriction_missing_from_contract_is_parser_issue() -> None:
    contract = parse_requirement("Read a PDF paper and produce notes.")

    report = diagnose_evaluation(
        contract,
        [],
        {},
        requirement_text="The agent must not use web search.",
    )

    issue = report.issues[0]
    assert issue.category == "parser_missed_constraint"
    assert issue.strictness == "too_loose"
    assert issue.affected_agent_part == "contract_parser"
    assert "parser missed a user restriction" in issue.natural_language_cause


def test_contract_conflict_names_goal_and_forbidden_tool() -> None:
    contract = _paper_reader_contract()
    contract.forbidden_tools.append("markdown_writer")

    report = diagnose_evaluation(
        contract,
        [],
        {},
        requirement_text="Read a PDF paper and write Markdown notes.",
    )

    issue = next(item for item in report.issues if item.category == "contract_conflict")
    assert issue.affected_agent_part == "contract_consistency"
    assert "Markdown notes" in issue.natural_language_cause
    assert "markdown_writer" in issue.natural_language_cause


def test_rule_uncovered_uses_rule_coverage_protocol() -> None:
    contract = parse_requirement("Build an assistant. It must not provide medical advice.")
    trace = _valid_read_then_write_trace()

    coverage = build_rule_coverage_matrix(
        contract,
        [{"case": "valid_read_then_write", "passed": True}],
        {"valid_read_then_write": trace},
    )
    item = RuleCoverageItem.from_dict(
        next(entry for entry in coverage["rules"] if "no_medical_advice" in entry["rule_name"])
    )
    report = diagnose_evaluation(
        contract,
        [{"case": "valid_read_then_write", "passed": True}],
        {"valid_read_then_write": trace},
    )

    assert item.status == "uncovered"
    issue = next(issue for issue in report.issues if issue.category == "rule_uncovered")
    assert issue.affected_agent_part == "rule_coverage"
    assert issue.severity in {"info", "warning"}
    assert issue.strictness == "not_applicable"


def test_report_counts_by_category_and_affected_part_are_stable() -> None:
    contract = parse_requirement("Read a PDF paper and produce notes.")
    report = diagnose_evaluation(
        contract,
        [{"case": "write_after_missing_file", "passed": True}],
        {"write_after_missing_file": _missing_file_then_write_trace()},
        manifest={
            "cases": [
                {
                    "name": "write_after_missing_file",
                    "expected_to_fail": True,
                    "expected_rule": "no_write_on_missing_file",
                }
            ]
        },
    )

    assert report.total_issues == len(report.issues)
    assert report.issue_counts_by_category[report.issues[0].category] >= 1
    assert report.issue_counts_by_affected_part["error_handling"] == 1


def test_markdown_report_renders_schema_fields() -> None:
    output_dir = _test_output_dir("diagnosis_schema_report")
    contract = parse_requirement("Read a PDF paper and produce notes.")
    report = diagnose_evaluation(
        contract,
        [{"case": "write_after_missing_file", "passed": True}],
        {"write_after_missing_file": _missing_file_then_write_trace()},
        manifest={
            "cases": [
                {
                    "name": "write_after_missing_file",
                    "expected_to_fail": True,
                    "expected_rule": "no_write_on_missing_file",
                }
            ]
        },
    )
    report_path = output_dir / "diagnosis.md"

    write_diagnosis_report_markdown(report, report_path)
    markdown = report_path.read_text(encoding="utf-8")

    assert "# Diagnosis Report" in markdown
    assert "## Issue Counts by Affected Agent Part" in markdown
    assert "### ATD001:" in markdown
    assert "- Category:" in markdown
    assert "Suggested regression trace" in markdown
    assert "```json" in markdown
    assert "```yaml" not in markdown


def test_why_uses_diagnosis_issue_schema_for_failed_trace() -> None:
    contract = _paper_reader_contract()
    trace = _counterexample_trace(contract, "write_after_missing_file")
    explanation = explain_trace_result(
        contract,
        trace,
        manifest_case={"expected_to_fail": False},
    )

    assert explanation["issues"]
    assert explanation["issues"][0]["category"]
    assert explanation["issues"][0]["affected_agent_part"]
    assert explanation["natural_language_cause"]


def test_why_preserves_manifest_case_name_for_unexpected_pass() -> None:
    contract = parse_requirement("Read a PDF paper and produce notes.")
    explanation = explain_trace_result(
        contract,
        [],
        check_result={"passed": True},
        manifest_case={
            "name": "write_after_missing_file",
            "expected_to_fail": True,
            "expected_rule": "no_write_on_missing_file",
        },
    )

    issue = explanation["issues"][0]
    assert issue["strictness"] == "too_loose"
    assert issue["category"] in {"contract_too_loose", "checker_too_loose"}
    assert issue["evidence"]["case"] == "write_after_missing_file"
    assert "output_formatting" not in issue["affected_agent_part"]


def test_valid_trace_without_expectation_has_no_diagnosis_issue() -> None:
    contract = _paper_reader_contract()
    trace = _counterexample_trace(contract, "valid_read_then_write")

    explanation = explain_trace_result(contract, trace)

    assert explanation["passed"] is True
    assert explanation["issues"] == []


def test_cli_diagnose_check_all_and_why_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = _test_output_dir("diagnosis_cli")
    contract_path = output_dir / "agent_contract.yaml"
    traces_dir = output_dir / "traces"
    report_path = output_dir / "reports" / "diagnosis.md"
    save_contract(_paper_reader_contract(), contract_path)

    generated = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "counterexamples",
            str(contract_path),
            "--out",
            str(traces_dir),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert generated.returncode == 0, generated.stderr

    diagnosed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "diagnose",
            "--contract",
            str(contract_path),
            "--traces",
            str(traces_dir),
            "--manifest",
            str(traces_dir / "manifest.yaml"),
            "--out",
            str(report_path),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert diagnosed.returncode == 0, diagnosed.stderr
    assert report_path.exists()
    assert "Diagnosis summary:" in diagnosed.stdout
    assert "Issue counts by category" in diagnosed.stdout

    check_all = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "check-all",
            "--contract",
            str(contract_path),
            "--traces",
            str(traces_dir),
            "--diagnose",
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert check_all.returncode == 0, check_all.stderr
    assert "Diagnosis summary:" in check_all.stdout

    why = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "why",
            "--contract",
            str(contract_path),
            "--trace",
            str(traces_dir / "write_after_missing_file.json"),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert why.returncode == 0, why.stderr
    assert "Natural-language explanation" in why.stdout
    assert "Issue ID:" in why.stdout
    assert "Suggested patch:" in why.stdout


def _paper_reader_contract():
    return parse_requirement(
        "Read a PDF paper, handle file not found, and do not browse the web."
    )


def _counterexample_trace(contract, name: str) -> list[dict]:
    for case in generate_counterexamples(contract):
        if case.name == name:
            return case.trace
    raise AssertionError(f"Missing counterexample: {name}")


def _missing_file_then_write_trace() -> list[dict]:
    return [
        {"type": "tool_call", "tool": "pdf_reader", "args": {"path": "missing.pdf"}},
        {
            "type": "tool_result",
            "tool": "pdf_reader",
            "result": {"status": "file_not_found"},
        },
        {"type": "tool_call", "tool": "markdown_writer", "args": {"path": "notes.md"}},
        {"type": "tool_result", "tool": "markdown_writer", "result": {"status": "ok"}},
    ]


def _valid_read_then_write_trace() -> list[dict]:
    return [
        {"type": "tool_call", "tool": "pdf_reader", "args": {"path": "sample.pdf"}},
        {"type": "tool_result", "tool": "pdf_reader", "result": {"status": "ok"}},
        {"type": "tool_call", "tool": "markdown_writer", "args": {"path": "notes.md"}},
        {"type": "tool_result", "tool": "markdown_writer", "result": {"status": "ok"}},
        {
            "type": "final_output",
            "content": "## Definitions\n...\n## Theorems\n...\n## Proof ideas\n...",
        },
    ]


def _test_output_dir(prefix: str) -> Path:
    root = Path(__file__).resolve().parents[1] / ".test_runs"
    path = root / f"{prefix}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path
