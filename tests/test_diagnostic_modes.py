from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from contract2agent.diagnostic_modes import (
    DiagnosticReport,
    DiagnosticMode,
    DiagnosticRound,
    Finding,
    MAX_DEEP_ROUNDS,
    PatchHistory,
    PatchProposal,
    ReviewPolicy,
    SafePatcher,
    SyntheticDiagnosticAgent,
    TestCase as ADTestCase,
    TestResult as ADTestResult,
    auto_mode_warnings,
    compute_diagnostic_confidence,
    default_contract,
    default_test_cases,
    format_markdown_report,
    is_safe_patch_target,
    parse_review_policy,
    plan_test_cases,
    round_requires_review,
    run_auto_diagnosis,
    run_deep_diagnosis,
    run_diagnostic_round,
    run_quick_diagnosis,
)
from contract2agent.failure_taxonomy import FailureType, TimeCostSummary


@pytest.fixture
def tmp_path() -> Path:
    return _test_output_dir("diagnostic_tmp")


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


def test_cli_invalid_deep_rounds_prints_clean_error_without_traceback() -> None:
    root = Path(__file__).resolve().parents[1]
    for value in ("0", "-1"):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "contract2agent.cli",
                "deep",
                "--rounds",
                value,
                "--out",
                str(_test_output_dir(f"deep_invalid_{value.replace('-', 'neg')}") / "reports"),
            ],
            cwd=root,
            text=True,
            input="",
            capture_output=True,
        )
        output = completed.stdout + completed.stderr

        assert completed.returncode != 0
        assert "--rounds must be at least 1" in output
        assert "Traceback" not in output


def test_typer_cli_invalid_deep_review_prints_clean_error_without_traceback() -> None:
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "deep",
            "--rounds",
            "1",
            "--review",
            "bogus",
            "--out",
            str(_test_output_dir("deep_invalid_review") / "reports"),
        ],
        cwd=root,
        text=True,
        input="",
        capture_output=True,
    )
    output = completed.stdout + completed.stderr

    assert completed.returncode != 0
    assert "--review must be never, on-fail, or each-round" in output
    assert "Traceback" not in output


def test_auto_validates_target_confidence_before_warnings() -> None:
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "auto",
            "--target-confidence",
            "1.5",
            "--out",
            str(_test_output_dir("auto_invalid_confidence") / "reports"),
        ],
        cwd=root,
        text=True,
        input="",
        capture_output=True,
    )
    output = completed.stdout + completed.stderr

    assert completed.returncode != 0
    assert "--target-confidence must be between 0 and 1" in output
    assert "Warning 1" not in output
    assert "Traceback" not in output


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


def test_deep_rounds_rejects_unreasonably_large_values() -> None:
    with pytest.raises(ValueError, match=f"no more than {MAX_DEEP_ROUNDS}"):
        run_deep_diagnosis(
            rounds=MAX_DEEP_ROUNDS + 1,
            review_policy=ReviewPolicy.NEVER,
            out_dir=_test_output_dir("deep_rounds_too_many") / "reports",
            interactive=False,
        )


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


def test_deep_clean_run_recommendation_does_not_claim_failed_or_warning_cases() -> None:
    report = run_deep_diagnosis(
        rounds=1,
        review_policy=ReviewPolicy.NEVER,
        agent=SyntheticDiagnosticAgent(profile="default"),
        out_dir=_test_output_dir("deep_clean_recommendation") / "reports",
        interactive=False,
    )

    assert report.status == "passed"
    assert report.fail_count == 0
    assert report.warning_count == 0
    assert not any("failed or warning cases" in item for item in report.recommendations)
    assert any("No deep-run failures or warnings" in item for item in report.recommendations)


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


def test_auto_status_uses_post_patch_validation_when_patch_reaches_target(monkeypatch: pytest.MonkeyPatch) -> None:
    rounds = iter(
        [
            _round_with_confidence(1, 0.4),
            _round_with_confidence(1, 0.4),
            _round_with_confidence(1, 0.9),
            _round_with_confidence(0, 0.9),
        ]
    )

    def fake_run_diagnostic_round(**kwargs):
        return next(rounds)

    class FakePatcher:
        def __init__(self, repo_root):
            self.repo_root = Path(repo_root)

        def create_patch_proposal(self, round_report):
            return PatchProposal(
                file_path=self.repo_root / "eval_config.yaml",
                new_text="name: patched\n",
                patch_summary="Patch fixture",
                reason_for_patch="Exercise post-patch validation status",
            )

        def apply(self, proposal, *, round_index: int, previous_confidence: float):
            return PatchHistory(
                round_index=round_index,
                previous_confidence=previous_confidence,
                new_confidence=previous_confidence,
                files_changed=[str(proposal.file_path)],
                patch_summary=proposal.patch_summary,
                reason_for_patch=proposal.reason_for_patch,
                diff="",
            )

    monkeypatch.setattr("contract2agent.diagnostic_modes.run_diagnostic_round", fake_run_diagnostic_round)
    monkeypatch.setattr("contract2agent.diagnostic_modes.SafePatcher", FakePatcher)

    report = run_auto_diagnosis(
        target_confidence=0.8,
        max_rounds=1,
        repo_root=_test_output_dir("auto_post_patch_validation") / "repo",
        out_dir=_test_output_dir("auto_post_patch_validation") / "reports",
        interactive=False,
        review_policy=ReviewPolicy.NEVER,
    )

    assert report.status == "passed"
    assert report.overall_confidence == 0.9
    assert report.budget_summary["post_patch_validation_confidence"] == 0.9
    assert report.patch_history[0].new_confidence == 0.9


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


def test_auto_patcher_rejects_agentdoctor_baseline_paths(tmp_path: Path) -> None:
    target = tmp_path / ".agentdoctor" / "baselines" / "baseline_1" / "eval_config.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("baseline: original\n", encoding="utf-8")
    proposal = PatchProposal(
        file_path=target,
        new_text="baseline: changed\n",
        patch_summary="Unsafe baseline change",
        reason_for_patch="Do not patch generated baselines",
    )

    assert not is_safe_patch_target(target, tmp_path)
    with pytest.raises(ValueError):
        SafePatcher(tmp_path).apply(
            proposal,
            round_index=1,
            previous_confidence=0.2,
        )
    assert target.read_text(encoding="utf-8") == "baseline: original\n"


def test_auto_patcher_missing_default_target_stays_in_root_allowlist(tmp_path: Path) -> None:
    patcher = SafePatcher(tmp_path)
    target = patcher._find_patch_target([])

    assert target == tmp_path.resolve() / "eval_config.yaml"
    assert is_safe_patch_target(target, tmp_path)
    assert not target.exists()

    history = patcher.apply(
        PatchProposal(
            file_path=target,
            new_text="agentdoctor_repair_guidance: []\n",
            patch_summary="Create safe root eval config",
            reason_for_patch="Document missing target creation invariant",
        ),
        round_index=1,
        previous_confidence=0.2,
    )

    assert history.file_existed is False
    assert target.exists()
    assert target.relative_to(tmp_path.resolve()).as_posix() == "eval_config.yaml"
    assert not (tmp_path / ".agentdoctor").exists()


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


def test_diagnostic_markdown_includes_time_cost_summary() -> None:
    test_case = ADTestCase(
        id="slow",
        name="slow",
        description="fixture",
        input="fixture",
        expected_behavior="fixture",
    )
    result = ADTestResult(
        test_case_id="slow",
        trace_id="trace-slow",
        passed=False,
        warning_count=0,
        score=0.0,
        check_rule=None,
        check_message="slow failure",
        duration_seconds=9.0,
    )
    finding = Finding(
        id="F-slow",
        severity="error",
        title="Slow task",
        description="Slow task failed.",
        related_test_id="slow",
        failure_type=FailureType.TASK_INCOMPLETE,
    )
    round_report = DiagnosticRound(
        round_index=1,
        mode="deep",
        test_cases=[test_case],
        traces=[],
        scores={},
        findings=[finding],
        review_items=[],
        confidence=0.0,
        started_at="2026-05-03T21:00:00+00:00",
        finished_at="2026-05-03T21:00:10+00:00",
        test_results=[result],
    )
    report = DiagnosticReport(
        mode="deep",
        status="failed",
        total_rounds_requested=1,
        total_rounds_executed=1,
        overall_confidence=0.0,
        pass_count=0,
        fail_count=1,
        findings=[finding],
        rounds=[round_report],
        efficiency_warning="Slow diagnostic path detected.",
        budget_summary={"elapsed_seconds": 10.0},
        time_cost_summary=TimeCostSummary(
            slowest_tests_by_failure_type={
                "TASK_INCOMPLETE": [{"test_id": "slow", "duration_seconds": 9.0}]
            },
            time_by_failure_type={"TASK_INCOMPLETE": 9.0},
            inefficient_failure_types=["TASK_INCOMPLETE"],
            efficiency_warning="Slow failure type detected.",
        ),
    )

    markdown = format_markdown_report(report)

    assert "## Time Cost" in markdown
    assert "Total elapsed seconds: 10" in markdown
    assert "Rounds executed: 1" in markdown
    assert "Tests executed: 1" in markdown
    assert "Average test time: 9" in markdown
    assert "- slow: 9 (TASK_INCOMPLETE)" in markdown
    assert "Warning: Slow diagnostic path detected." in markdown


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
    root = Path(
        os.environ.get(
            "AGENTDOCTOR_TEST_ROOT",
            str(Path(__file__).resolve().parents[1] / ".tmp_pytest_base" / "agentdoctor-test-runs"),
        )
    )
    path = root / f"{prefix}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _round_with_confidence(round_index: int, confidence: float) -> DiagnosticRound:
    test_case = ADTestCase(
        id=f"case_{round_index}_{confidence}",
        name="fixture",
        description="fixture",
        input="fixture",
        expected_behavior="fixture",
    )
    result = ADTestResult(
        test_case_id=test_case.id,
        trace_id=f"trace_{round_index}_{confidence}",
        passed=confidence >= 0.8,
        warning_count=0,
        score=confidence,
        check_rule=None,
        check_message="",
        duration_seconds=0.1,
    )
    return DiagnosticRound(
        round_index=round_index,
        mode="auto",
        test_cases=[test_case],
        traces=[],
        scores={"key_task_pass_rate": confidence},
        findings=[],
        review_items=[],
        confidence=confidence,
        started_at="2026-05-03T21:00:00+00:00",
        finished_at="2026-05-03T21:00:01+00:00",
        test_results=[result],
    )
