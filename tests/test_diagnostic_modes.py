from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from contract2agent.diagnostic_modes import (
    DiagnosticMode,
    PatchProposal,
    ReviewPolicy,
    SafePatcher,
    SyntheticDiagnosticAgent,
    auto_mode_warnings,
    compute_diagnostic_confidence,
    default_contract,
    default_test_cases,
    is_safe_patch_target,
    parse_review_policy,
    plan_test_cases,
    round_requires_review,
    run_auto_diagnosis,
    run_deep_diagnosis,
    run_diagnostic_round,
    run_quick_diagnosis,
)


def test_agentdoctor_cli_quick_deep_auto_commands() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = _test_output_dir("cli_modes")

    quick = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "quick",
            "--out",
            str(output_dir / "quick_reports"),
        ],
        cwd=root,
        text=True,
        input="",
        capture_output=True,
    )
    assert quick.returncode == 0, quick.stderr
    assert "AgentDoctor Quick Diagnosis" in quick.stdout

    deep = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "deep",
            "--rounds",
            "1",
            "--review",
            "never",
            "--out",
            str(output_dir / "deep_reports"),
        ],
        cwd=root,
        text=True,
        input="",
        capture_output=True,
    )
    assert deep.returncode == 0, deep.stderr
    assert "AgentDoctor Deep Diagnosis" in deep.stdout

    repo_root = output_dir / "repo"
    repo_root.mkdir()
    auto = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "auto",
            "--target-confidence",
            "0.50",
            "--max-rounds",
            "1",
            "--repo-root",
            str(repo_root),
            "--out",
            str(output_dir / "auto_reports"),
        ],
        cwd=root,
        text=True,
        input="",
        capture_output=True,
    )
    assert auto.returncode == 0, auto.stderr
    assert "AgentDoctor Auto Report" in auto.stdout
    assert "Warning 1" in auto.stdout


def test_review_policy_parsing_and_behavior() -> None:
    contract = default_contract()
    agent = SyntheticDiagnosticAgent(profile="weak")
    round_report = run_diagnostic_round(
        round_index=1,
        mode=DiagnosticMode.DEEP,
        contract=contract,
        agent=agent,
        test_cases=plan_test_cases(DiagnosticMode.DEEP, 1, default_test_cases(contract)),
    )

    assert parse_review_policy("on-fail") == ReviewPolicy.ON_FAIL
    assert round_requires_review(round_report, ReviewPolicy.ON_FAIL)
    assert round_requires_review(round_report, ReviewPolicy.EACH_ROUND)
    assert not round_requires_review(round_report, ReviewPolicy.NEVER)
    with pytest.raises(ValueError):
        parse_review_policy("sometimes")


def test_quick_mode_runs_one_round_and_selects_key_tests() -> None:
    output_dir = _test_output_dir("quick_mode")
    report = run_quick_diagnosis(out_dir=output_dir / "reports")
    selected = report.rounds[0].test_cases

    assert report.total_rounds_executed == 1
    assert len(report.rounds) == 1
    assert all(case.priority >= 75 for case in selected)
    assert {case.id for case in selected} == {
        "AD001",
        "AD002",
        "AD003",
        "AD004",
        "AD005",
        "AD006",
    }


def test_deep_mode_runs_exactly_n_rounds() -> None:
    output_dir = _test_output_dir("deep_rounds")
    report = run_deep_diagnosis(
        rounds=3,
        review_policy=ReviewPolicy.NEVER,
        out_dir=output_dir / "reports",
        interactive=False,
    )

    assert report.total_rounds_requested == 3
    assert report.total_rounds_executed == 3
    assert [round_report.round_index for round_report in report.rounds] == [1, 2, 3]


def test_deep_mode_respects_review_policies() -> None:
    output_dir = _test_output_dir("deep_review")
    never_report = run_deep_diagnosis(
        rounds=1,
        review_policy=ReviewPolicy.NEVER,
        agent=SyntheticDiagnosticAgent(profile="weak"),
        out_dir=output_dir / "never_reports",
        interactive=False,
    )
    on_fail_report = run_deep_diagnosis(
        rounds=1,
        review_policy=ReviewPolicy.ON_FAIL,
        agent=SyntheticDiagnosticAgent(profile="weak"),
        out_dir=output_dir / "on_fail_reports",
        interactive=False,
    )
    each_round_report = run_deep_diagnosis(
        rounds=1,
        review_policy=ReviewPolicy.EACH_ROUND,
        out_dir=output_dir / "each_round_reports",
        interactive=False,
    )

    assert never_report.review_required
    assert any(
        finding.requires_human_review
        for finding in never_report.findings
    )
    assert on_fail_report.review_required
    assert each_round_report.review_required


def test_auto_mode_stops_when_target_confidence_is_reached() -> None:
    output_dir = _test_output_dir("auto_target")
    report = run_auto_diagnosis(
        target_confidence=0.50,
        max_rounds=6,
        repo_root=output_dir / "repo",
        out_dir=output_dir / "reports",
        interactive=False,
    )

    assert report.total_rounds_executed == 1
    assert report.status in {"passed", "passed_with_review_recommended"}


def test_auto_mode_stops_when_max_rounds_is_reached() -> None:
    output_dir = _test_output_dir("auto_max_rounds")
    repo_root = output_dir / "repo"
    repo_root.mkdir()
    report = run_auto_diagnosis(
        target_confidence=0.99,
        max_rounds=2,
        repo_root=repo_root,
        out_dir=output_dir / "reports",
        interactive=False,
    )

    assert report.total_rounds_executed == 2
    assert report.status == "stopped_budget_exceeded"


def test_auto_mode_warns_for_high_target_confidence() -> None:
    warnings = auto_mode_warnings(0.95)

    assert any("very high" in warning for warning in warnings)
    assert any("heuristic" in warning for warning in warnings)


def test_auto_mode_refuses_unsafe_file_modifications() -> None:
    output_dir = _test_output_dir("unsafe_patch")
    source_dir = output_dir / "contract2agent"
    source_dir.mkdir()
    unsafe_file = source_dir / "checker.py"
    unsafe_file.write_text("# source\n", encoding="utf-8")
    proposal = PatchProposal(
        file_path=unsafe_file,
        new_text="# changed\n",
        patch_summary="Unsafe source change",
        reason_for_patch="Test unsafe refusal",
    )

    assert not is_safe_patch_target(unsafe_file, output_dir)
    with pytest.raises(ValueError):
        SafePatcher(output_dir).apply(
            proposal,
            round_index=1,
            previous_confidence=0.2,
        )


def test_diagnostic_confidence_normalizes_available_weights() -> None:
    confidence = compute_diagnostic_confidence(
        {
            "key_task_pass_rate": 1.0,
            "tool_call_correctness": 0.5,
        }
    )

    assert confidence == 0.8


def test_report_generation_includes_required_sections() -> None:
    output_dir = _test_output_dir("report_sections")
    report = run_quick_diagnosis(out_dir=output_dir / "reports")
    markdown = (output_dir / "reports" / "latest.md").read_text(encoding="utf-8")
    data = json.loads((output_dir / "reports" / "latest.json").read_text(encoding="utf-8"))

    assert report.review_required
    assert "# AgentDoctor Quick Diagnosis" in markdown
    assert "Diagnostic confidence is heuristic" in markdown
    assert "## Key Findings" in markdown
    assert "review_items" in data
    assert data["rounds"]


def test_patch_rollback_restores_safe_config_file() -> None:
    output_dir = _test_output_dir("rollback")
    repo_root = output_dir / "repo"
    repo_root.mkdir()
    config = repo_root / "eval_config.yaml"
    config.write_text("name: baseline\n", encoding="utf-8")
    patcher = SafePatcher(repo_root)
    patch = patcher.apply(
        PatchProposal(
            file_path=config,
            new_text="name: changed\n",
            patch_summary="Change safe config",
            reason_for_patch="Exercise rollback",
        ),
        round_index=1,
        previous_confidence=0.7,
    )

    assert config.read_text(encoding="utf-8") == "name: changed\n"
    patcher.rollback(patch)
    assert patch.rollback_performed
    assert config.read_text(encoding="utf-8") == "name: baseline\n"


def _test_output_dir(prefix: str) -> Path:
    root = Path(__file__).resolve().parents[1] / ".test_runs"
    path = root / f"{prefix}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path
