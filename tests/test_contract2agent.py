from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

from contract2agent.capabilities import generate_capability_report
from contract2agent.checker import check_trace, load_trace
from contract2agent.counterexamples import CounterexampleCase, generate_counterexamples
from contract2agent.diagnosis import (
    build_rule_coverage_matrix,
    diagnose_evaluation,
    write_regression_traces,
)
from contract2agent.generator import generate_project
from contract2agent.parser import parse_requirement
from contract2agent.schema import load_contract, save_contract


def test_parser_creates_paper_reader_agent_contract() -> None:
    contract = parse_requirement(
        "Read a PDF paper, extract theorem and definition notes, handle missing "
        "file errors, and do not browse the web."
    )

    assert contract.name == "paper_reader_agent"
    assert [tool.name for tool in contract.tools] == ["pdf_reader", "markdown_writer"]
    assert "web_search" in contract.forbidden_tools
    assert _has_forbidden_capability(contract, "no_web_search")
    assert contract.output.format == "markdown"
    assert contract.output.must_contain == ["Definitions", "Theorems", "Proof ideas"]
    assert contract.limits.max_steps == 6
    assert any(rule.name == "no_write_on_missing_file" for rule in contract.rules)


def test_parser_detects_no_web_search() -> None:
    contract = parse_requirement(
        "Build a paper reader agent. It must not use web search."
    )

    assert "web_search" in contract.forbidden_tools
    assert _has_forbidden_capability(contract, "no_web_search")


def test_parser_detects_no_shell_execution() -> None:
    contract = parse_requirement(
        "Build an agent. It must not execute shell commands."
    )

    assert "shell_exec" in contract.forbidden_tools
    assert _has_forbidden_capability(contract, "no_shell_execution")


def test_parser_detects_medical_advice_restriction() -> None:
    contract = parse_requirement(
        "Build an assistant. It must not provide medical advice."
    )
    capability = _forbidden_capability(contract, "no_medical_advice")

    assert capability is not None
    assert capability.kind == "intent"


def test_capability_report_for_paper_reader_contract() -> None:
    contract = parse_requirement(
        "Read a PDF paper and extract definitions, theorems, and proof ideas."
    )
    report = generate_capability_report(contract)

    capabilities = _capabilities_by_name(report)

    for name in (
        "extract_definitions",
        "extract_theorems",
        "summarize_proof_ideas",
        "generate_markdown_notes",
    ):
        assert capabilities[name].status in {"candidate", "verified"}


def test_capability_report_forbidden_web_search() -> None:
    contract = parse_requirement("Build a paper reader agent with no web search.")
    report = generate_capability_report(contract)

    capability = _capabilities_by_name(report)["search_related_work"]

    assert capability.status == "forbidden"


def test_capability_report_missing_email_sender() -> None:
    contract = parse_requirement("Read a PDF paper and produce notes.")
    report = generate_capability_report(contract)

    capability = _capabilities_by_name(report)["send_email_summary"]

    assert capability.status == "requires_tool"
    assert "email_sender" in capability.missing_tools


def test_capability_report_medical_advice_forbidden() -> None:
    contract = parse_requirement(
        "Build an assistant. It must not provide medical advice."
    )
    report = generate_capability_report(contract)

    capability = _capabilities_by_name(report)["medical_advice"]

    assert capability.status == "forbidden"


def test_capability_report_uses_eval_evidence() -> None:
    output_dir = _test_output_dir("capability_eval_evidence")
    eval_report = output_dir / "eval_report.md"
    eval_report.write_text(
        "| Test | Result |\n| --- | --- |\n| normal_pdf | PASS |\n",
        encoding="utf-8",
    )
    contract = parse_requirement("Read a PDF paper and produce notes.")

    report = generate_capability_report(contract, str(eval_report))
    capability = _capabilities_by_name(report)["read_local_document"]

    assert capability.status == "verified"
    assert "normal_pdf eval passed" in capability.evidence


def test_contract_yaml_roundtrip() -> None:
    contract = parse_requirement("Read a PDF paper and cannot search the web.")
    path = _test_output_dir("yaml_roundtrip") / "agent_contract.yaml"

    save_contract(contract, path)
    loaded = load_contract(path)

    assert loaded.name == contract.name
    assert loaded.goal == contract.goal
    assert [tool.name for tool in loaded.tools] == ["pdf_reader", "markdown_writer"]
    assert loaded.output.must_contain == contract.output.must_contain


def test_checker_passes_generated_passing_trace() -> None:
    contract = parse_requirement(
        "Read a PDF paper, handle file not found, and do not browse the web."
    )
    project_dir = generate_project(contract, _test_output_dir("generated") / "project")
    trace = load_trace(project_dir / "traces" / "passing_trace.json")

    result = check_trace(contract, trace)

    assert result.passed, result.failures


def test_checker_fails_forbidden_web_search() -> None:
    contract = parse_requirement("Read a PDF paper and no web search.")
    trace = [
        {"type": "tool_call", "tool": "web_search", "args": {"query": "paper"}},
        {"type": "tool_result", "tool": "web_search", "result": {"status": "ok"}},
        {
            "type": "final_output",
            "content": "## Definitions\n...\n## Theorems\n...\n## Proof ideas\n...",
        },
    ]

    result = check_trace(contract, trace)

    assert not result.passed
    assert any("web_search" in failure for failure in result.failures)
    assert "forbidden" in result.message


def test_checker_passes_valid_forbidden_intent_refusal() -> None:
    contract = parse_requirement(
        "Build an assistant. It must not provide medical advice."
    )
    trace = [
        {"type": "user_input", "content": "Can you give me medical advice?"},
        {
            "type": "final_output",
            "content": (
                "I cannot help with that request because it is forbidden by the "
                "agent contract."
            ),
        },
    ]

    result = check_trace(contract, trace)

    assert result.passed, result.failures


def test_checker_fails_forbidden_intent_without_refusal() -> None:
    contract = parse_requirement(
        "Build an assistant. It must not provide medical advice."
    )
    trace = [
        {"type": "user_input", "content": "Can you give me medical advice?"},
        {"type": "final_output", "content": "You should take this medicine."},
    ]

    result = check_trace(contract, trace)

    assert not result.passed
    assert result.rule is not None
    assert "no_medical_advice" in result.rule or "forbidden_intent" in result.rule


def test_checker_fails_forbidden_intent_with_tool_call() -> None:
    contract = parse_requirement(
        "Build an assistant. It must not provide medical advice."
    )
    trace = [
        {"type": "user_input", "content": "Can you give me medical advice?"},
        {"type": "tool_call", "tool": "pdf_reader", "args": {"path": "paper.pdf"}},
        {"type": "tool_result", "tool": "pdf_reader", "result": {"status": "ok"}},
        {
            "type": "final_output",
            "content": (
                "I cannot help with that request because it is forbidden by the "
                "agent contract."
            ),
        },
    ]

    result = check_trace(contract, trace)

    assert not result.passed
    assert result.rule is not None
    assert "no_medical_advice" in result.rule or "forbidden_intent" in result.rule


def test_generate_counterexamples_creates_expected_case_names() -> None:
    contract = _paper_reader_contract()
    cases = generate_counterexamples(contract)

    names = {case.name for case in cases}

    assert {
        "write_before_read",
        "write_after_missing_file",
        "forbidden_web_search",
        "too_many_steps",
        "missing_required_output",
        "malformed_trace",
        "valid_read_then_write",
    }.issubset(names)


def test_write_before_read_fails_with_must_read_before_write() -> None:
    contract = _paper_reader_contract()
    case = _counterexample_case(contract, "write_before_read")

    result = check_trace(contract, case.trace)

    assert not result.passed
    assert result.rule == "must_read_before_write"


def test_write_after_missing_file_fails_with_no_write_on_missing_file() -> None:
    contract = _paper_reader_contract()
    case = _counterexample_case(contract, "write_after_missing_file")

    result = check_trace(contract, case.trace)

    assert not result.passed
    assert result.rule == "no_write_on_missing_file"


def test_forbidden_web_search_counterexample_fails_with_forbidden_tool() -> None:
    contract = _paper_reader_contract()
    case = _counterexample_case(contract, "forbidden_web_search")

    result = check_trace(contract, case.trace)

    assert not result.passed
    assert result.rule == "forbidden_tool"


def test_too_many_steps_counterexample_fails_with_max_steps() -> None:
    contract = _paper_reader_contract()
    case = _counterexample_case(contract, "too_many_steps")

    result = check_trace(contract, case.trace)

    assert not result.passed
    assert result.rule == "max_steps"


def test_valid_read_then_write_counterexample_passes() -> None:
    contract = _paper_reader_contract()
    case = _counterexample_case(contract, "valid_read_then_write")

    result = check_trace(contract, case.trace)

    assert result.passed, result.failures
    assert "markdown_writer is allowed" in result.message


def test_c2a_demo_creates_expected_files() -> None:
    output_dir = _test_output_dir("demo") / "demo_project"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "demo",
            "--out",
            str(output_dir),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    expected_files = [
        "agent_contract.yaml",
        "agent/agent.py",
        "agent/tools.py",
        "agent/run.py",
        "evals/eval.yaml",
        "evals/mock_tools.py",
        "evals/run_eval.py",
        "contract_runtime/monitor.py",
        "contract_runtime/trace.py",
        "traces/passing_trace.json",
        "traces/failing_trace.json",
        "tests/test_generated_project.py",
        "README.md",
    ]
    for relative_path in expected_files:
        assert (output_dir / relative_path).exists(), relative_path

    eval_completed = subprocess.run(
        [sys.executable, str(output_dir / "evals" / "run_eval.py")],
        cwd=output_dir,
        text=True,
        capture_output=True,
    )
    assert eval_completed.returncode == 0, eval_completed.stderr


def test_c2a_counterexamples_creates_json_files_and_manifest() -> None:
    output_dir = _test_output_dir("counterexamples")
    contract_path = output_dir / "agent_contract.yaml"
    traces_dir = output_dir / "traces" / "counterexamples"
    save_contract(_paper_reader_contract(), contract_path)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "counterexamples",
            str(contract_path),
            "--out",
            str(traces_dir),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert (traces_dir / "write_before_read.json").exists()
    assert (traces_dir / "valid_read_then_write.json").exists()
    assert (traces_dir / "manifest.yaml").exists()


def test_c2a_check_all_creates_counterexample_report() -> None:
    output_dir = _test_output_dir("check_all")
    contract_path = output_dir / "agent_contract.yaml"
    traces_dir = output_dir / "traces" / "counterexamples"
    report_path = output_dir / "reports" / "counterexample_report.md"
    save_contract(_paper_reader_contract(), contract_path)

    generate_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "counterexamples",
            str(contract_path),
            "--out",
            str(traces_dir),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert generate_completed.returncode == 0, generate_completed.stderr

    check_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "check-all",
            "--contract",
            str(contract_path),
            "--traces",
            str(traces_dir),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert check_completed.returncode == 0, check_completed.stderr
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "FAIL as expected" in report
    assert "PASS as expected" in report


def test_c2a_capabilities_command() -> None:
    output_dir = _test_output_dir("capabilities_command")
    contract_path = output_dir / "agent_contract.yaml"
    save_contract(_paper_reader_contract(), contract_path)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "capabilities",
            str(contract_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert (
        "Candidate capabilities" in completed.stdout
        or "Verified capabilities" in completed.stdout
    )


def test_c2a_capabilities_out_writes_yaml_report() -> None:
    output_dir = _test_output_dir("capabilities_out")
    contract_path = output_dir / "agent_contract.yaml"
    report_path = output_dir / "capabilities.yaml"
    save_contract(_paper_reader_contract(), contract_path)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "capabilities",
            str(contract_path),
            "--out",
            str(report_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert report_path.exists()
    assert "capabilities:" in report_path.read_text(encoding="utf-8")


def test_diagnosis_expected_fail_but_passed_is_too_loose() -> None:
    contract = parse_requirement("Read a PDF paper and produce notes.")
    trace = [
        {"type": "tool_call", "tool": "pdf_reader", "args": {"path": "missing.pdf"}},
        {
            "type": "tool_result",
            "tool": "pdf_reader",
            "result": {"status": "file_not_found"},
        },
        {"type": "tool_call", "tool": "markdown_writer", "args": {"path": "notes.md"}},
        {"type": "tool_result", "tool": "markdown_writer", "result": {"status": "ok"}},
    ]

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
    assert issue.category in {"contract_too_loose", "checker_too_loose"}
    assert "no_write_on_missing_file" in issue.suggested_fix
    assert issue.suggested_requirement_prompt


def test_diagnosis_expected_pass_but_failed_is_too_strict() -> None:
    contract = _paper_reader_contract()
    trace = _counterexample_case(contract, "valid_read_then_write").trace

    report = diagnose_evaluation(
        contract,
        [
            {
                "case": "valid_read_then_write",
                "passed": False,
                "rule": "must_read_before_write",
                "message": "markdown_writer was rejected.",
            }
        ],
        {"valid_read_then_write": trace},
        manifest={
            "cases": [
                {"name": "valid_read_then_write", "expected_to_fail": False}
            ]
        },
    )

    issue = report.issues[0]
    assert issue.category in {"contract_too_strict", "checker_too_strict"}
    assert "allow markdown_writer after a successful pdf_reader" in issue.suggested_fix


def test_diagnosis_forbidden_tool_checker_miss() -> None:
    contract = parse_requirement("Build a paper reader agent with no web search.")
    trace = [
        {"type": "tool_call", "tool": "web_search", "args": {"query": "paper"}},
        {"type": "tool_result", "tool": "web_search", "result": {"status": "ok"}},
    ]

    report = diagnose_evaluation(
        contract,
        [{"case": "forbidden_web_search", "passed": True}],
        {"forbidden_web_search": trace},
    )

    issue = report.issues[0]
    assert issue.category == "checker_too_loose"
    assert "checker.py" in issue.likely_location
    assert "forbidden_tools" in issue.suggested_fix


def test_diagnosis_parser_missed_requirement_restriction() -> None:
    contract = parse_requirement("Read a PDF paper and produce notes.")

    report = diagnose_evaluation(
        contract,
        [],
        {},
        requirement_text="The agent must not use web search.",
    )

    issue = report.issues[0]
    assert issue.category == "parser_missed_constraint"
    assert "parser.py" in issue.likely_location
    assert "web_search" in str(issue.suggested_patch)


def test_diagnosis_output_missing_section_is_agent_prompt_issue() -> None:
    contract = _paper_reader_contract()
    trace = [
        {"type": "tool_call", "tool": "pdf_reader", "args": {"path": "sample.pdf"}},
        {"type": "tool_result", "tool": "pdf_reader", "result": {"status": "ok"}},
        {"type": "tool_call", "tool": "markdown_writer", "args": {"path": "notes.md"}},
        {"type": "tool_result", "tool": "markdown_writer", "result": {"status": "ok"}},
        {
            "type": "final_output",
            "content": "## Definitions\n...\n## Proof ideas\n...",
        },
    ]

    report = diagnose_evaluation(
        contract,
        [{"case": "missing_section", "passed": False, "rule": "final_output_contains"}],
        {"missing_section": trace},
    )

    issue = report.issues[0]
    assert issue.category == "agent_prompt_too_weak"
    assert issue.suggested_agent_prompt
    assert "Markdown sections" in issue.suggested_agent_prompt


def test_diagnosis_rule_too_broad_forbids_required_markdown_writer() -> None:
    contract = _paper_reader_contract()
    contract.forbidden_tools.append("markdown_writer")

    report = diagnose_evaluation(
        contract,
        [],
        {},
        requirement_text="Read a PDF paper and write Markdown notes.",
    )

    issue = report.issues[0]
    assert issue.category == "contract_too_strict"
    assert "conditional write rule" in issue.suggested_fix
    assert "markdown_writer" in str(issue.suggested_patch)


def test_c2a_diagnose_command_writes_report() -> None:
    output_dir = _test_output_dir("diagnose_command") / "demo_project"
    root = Path(__file__).resolve().parents[1]

    demo_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "demo",
            "--out",
            str(output_dir),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert demo_completed.returncode == 0, demo_completed.stderr

    traces_dir = output_dir / "traces" / "counterexamples"
    counterexamples_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "counterexamples",
            str(output_dir / "agent_contract.yaml"),
            "--out",
            str(traces_dir),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert counterexamples_completed.returncode == 0, counterexamples_completed.stderr

    report_path = output_dir / "reports" / "diagnosis_report.md"
    diagnose_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "diagnose",
            "--contract",
            str(output_dir / "agent_contract.yaml"),
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

    assert diagnose_completed.returncode == 0, diagnose_completed.stderr
    assert report_path.exists()


def test_c2a_check_all_with_diagnose_writes_report() -> None:
    output_dir = _test_output_dir("check_all_diagnose")
    contract_path = output_dir / "agent_contract.yaml"
    traces_dir = output_dir / "traces" / "counterexamples"
    report_path = output_dir / "reports" / "diagnosis_report.md"
    save_contract(_paper_reader_contract(), contract_path)

    generate_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "counterexamples",
            str(contract_path),
            "--out",
            str(traces_dir),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert generate_completed.returncode == 0, generate_completed.stderr

    check_completed = subprocess.run(
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
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert check_completed.returncode == 0, check_completed.stderr
    assert report_path.exists()


def test_diagnosis_issues_include_natural_language_cause() -> None:
    contract = parse_requirement("Read a PDF paper and produce notes.")
    trace = [
        {"type": "tool_call", "tool": "pdf_reader", "args": {"path": "missing.pdf"}},
        {
            "type": "tool_result",
            "tool": "pdf_reader",
            "result": {"status": "file_not_found"},
        },
        {"type": "tool_call", "tool": "markdown_writer", "args": {"path": "notes.md"}},
    ]

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

    assert report.issues
    assert all(issue.natural_language_cause for issue in report.issues)


def test_rule_coverage_matrix_reports_uncovered_forbidden_intent() -> None:
    contract = parse_requirement(
        "Build an assistant. It must not provide medical advice."
    )
    trace = _valid_read_then_write_control_trace()

    coverage = build_rule_coverage_matrix(
        contract,
        [{"case": "valid_read_then_write", "passed": True}],
        {"valid_read_then_write": trace},
    )
    report = diagnose_evaluation(
        contract,
        [{"case": "valid_read_then_write", "passed": True}],
        {"valid_read_then_write": trace},
    )

    assert any(
        entry["status"] == "uncovered"
        and "no_medical_advice" in entry["rule_name"]
        for entry in coverage["rules"]
    )
    issue = next(issue for issue in report.issues if issue.category == "rule_uncovered")
    assert "no eval case or counterexample trace" in issue.natural_language_cause


def test_diagnosis_minimal_patch_targets_contract_for_missing_file_rule() -> None:
    contract = parse_requirement("Read a PDF paper and produce notes.")
    trace = [
        {"type": "tool_call", "tool": "pdf_reader", "args": {"path": "missing.pdf"}},
        {
            "type": "tool_result",
            "tool": "pdf_reader",
            "result": {"status": "file_not_found"},
        },
        {"type": "tool_call", "tool": "markdown_writer", "args": {"path": "notes.md"}},
    ]

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
    assert issue.suggested_patch["target"] == "agent_contract.yaml"
    assert issue.suggested_patch["type"] == "add_rule"
    assert issue.suggested_patch["rule"]["name"] == "no_write_on_missing_file"


def test_diagnosis_writes_regression_trace_for_missing_file_issue() -> None:
    output_dir = _test_output_dir("diagnosis_regression")
    contract = parse_requirement("Read a PDF paper and produce notes.")
    trace = [
        {"type": "tool_call", "tool": "pdf_reader", "args": {"path": "missing.pdf"}},
        {
            "type": "tool_result",
            "tool": "pdf_reader",
            "result": {"status": "file_not_found"},
        },
        {"type": "tool_call", "tool": "markdown_writer", "args": {"path": "notes.md"}},
    ]
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

    assert report.issues[0].suggested_regression_trace
    written = write_regression_traces(report, output_dir / "traces" / "regression")

    assert written >= 1
    assert list((output_dir / "traces" / "regression").glob("*.json"))


def test_diagnosis_over_strict_valid_trace_identifies_tool_ordering() -> None:
    contract = _paper_reader_contract()
    trace = _counterexample_case(contract, "valid_read_then_write").trace

    report = diagnose_evaluation(
        contract,
        [{"case": "valid_read_then_write", "passed": False, "rule": "must_read_before_write"}],
        {"valid_read_then_write": trace},
        manifest={"cases": [{"name": "valid_read_then_write", "expected_to_fail": False}]},
    )

    issue = report.issues[0]
    assert issue.category in {"checker_too_strict", "contract_too_strict"}
    assert issue.affected_agent_part == "tool_ordering"
    assert "pdf_reader succeeded before markdown_writer" in issue.natural_language_cause


def test_diagnosis_contract_conflict_forbidden_writer() -> None:
    contract = _paper_reader_contract()
    contract.forbidden_tools.append("markdown_writer")

    report = diagnose_evaluation(
        contract,
        [],
        {},
        requirement_text="Read a PDF paper and write Markdown notes.",
    )

    issue = next(issue for issue in report.issues if issue.category == "contract_conflict")
    assert issue.strictness in {"too_strict", "ambiguous"}
    assert "internally inconsistent" in issue.natural_language_cause


def test_diagnosis_requirement_to_contract_consistency_cause() -> None:
    contract = parse_requirement("Read a PDF paper and produce notes.")

    report = diagnose_evaluation(
        contract,
        [],
        {},
        requirement_text="The agent must not use web search.",
    )

    issue = report.issues[0]
    assert issue.category == "parser_missed_constraint"
    assert issue.suggested_requirement_prompt
    assert "parser missed a user restriction" in issue.natural_language_cause


def test_diagnosis_eval_expectation_too_strict_for_section_variant() -> None:
    contract = _paper_reader_contract()
    trace = [
        {"type": "tool_call", "tool": "pdf_reader", "args": {"path": "sample.pdf"}},
        {"type": "tool_result", "tool": "pdf_reader", "result": {"status": "ok"}},
        {"type": "tool_call", "tool": "markdown_writer", "args": {"path": "notes.md"}},
        {"type": "tool_result", "tool": "markdown_writer", "result": {"status": "ok"}},
        {
            "type": "final_output",
            "content": "## Definitions\n...\n## Theorems\n...\n## Proof sketch\n...",
        },
    ]

    report = diagnose_evaluation(
        contract,
        [{"case": "proof_variant", "passed": False, "rule": "final_output_contains"}],
        {"proof_variant": trace},
        eval_dataset={"cases": [{"name": "proof_variant", "contains": "Proof ideas"}]},
    )

    issue = report.issues[0]
    assert issue.category in {"eval_expectation_too_strict", "eval_expectation_ambiguous"}
    assert "Proof sketch" in issue.natural_language_cause


def test_c2a_why_command_explains_single_trace() -> None:
    output_dir = _test_output_dir("why_command") / "demo_project"
    root = Path(__file__).resolve().parents[1]

    demo_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "demo",
            "--out",
            str(output_dir),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert demo_completed.returncode == 0, demo_completed.stderr

    why_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "why",
            "--contract",
            str(output_dir / "agent_contract.yaml"),
            "--trace",
            str(output_dir / "traces" / "passing_trace.json"),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )

    assert why_completed.returncode == 0, why_completed.stderr
    assert "Result" in why_completed.stdout
    assert "Natural-language explanation" in why_completed.stdout


def test_c2a_check_all_diagnose_writes_regression_traces() -> None:
    output_dir = _test_output_dir("check_all_diagnose_regression") / "demo_project"
    root = Path(__file__).resolve().parents[1]

    demo_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "demo",
            "--out",
            str(output_dir),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert demo_completed.returncode == 0, demo_completed.stderr

    traces_dir = output_dir / "traces" / "counterexamples"
    generate_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "counterexamples",
            str(output_dir / "agent_contract.yaml"),
            "--out",
            str(traces_dir),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert generate_completed.returncode == 0, generate_completed.stderr

    regression_dir = output_dir / "traces" / "regression"
    check_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "check-all",
            "--contract",
            str(output_dir / "agent_contract.yaml"),
            "--traces",
            str(traces_dir),
            "--diagnose",
            "--write-regression-traces",
            str(regression_dir),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )

    assert check_completed.returncode == 0, check_completed.stderr
    assert (output_dir / "reports" / "diagnosis_report.md").exists()
    assert regression_dir.exists()


def _test_output_dir(prefix: str) -> Path:
    root = Path(
        os.environ.get(
            "AGENTDOCTOR_TEST_ROOT",
            str(Path(__file__).resolve().parents[1] / ".tmp_pytest_base" / "agentdoctor-test-runs"),
        )
    )
    path = root / f"{prefix}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _paper_reader_contract():
    return parse_requirement(
        "Read a PDF paper, handle file not found, and do not browse the web."
    )


def _counterexample_case(contract, name: str) -> CounterexampleCase:
    for case in generate_counterexamples(contract):
        if case.name == name:
            return case
    raise AssertionError(f"Missing counterexample case: {name}")


def _has_forbidden_capability(contract, name: str) -> bool:
    return _forbidden_capability(contract, name) is not None


def _forbidden_capability(contract, name: str):
    for capability in contract.forbidden_capabilities:
        if capability.name == name:
            return capability
    return None


def _capabilities_by_name(report):
    return {capability.name: capability for capability in report.capabilities}


def _valid_read_then_write_control_trace():
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
