from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from contract2agent.baseline import (
    build_rollback_recommendation,
    compare_against_baseline,
    detect_overfitting_from_failure_type_changes,
    load_baseline,
    save_baseline,
)
from contract2agent.diagnostic_modes import (
    DiagnosticReport,
    DiagnosticRound,
    Finding,
    RuleScore,
    TestCase as ADTestCase,
    TestResult as ADTestResult,
)


NOW = datetime(2026, 5, 3, 21, 30, 12, tzinfo=timezone.utc)


def test_save_baseline_writes_baseline_snapshot_latest_hashes_and_copies() -> None:
    tmp_path = _test_output_dir("save_baseline")
    _write_agent(tmp_path / "agent.yaml")
    _write(tmp_path / "prompts" / "system.md", "Return Markdown. Handle missing files.")
    _write(tmp_path / ".env", "SECRET_VALUE=do-not-leak")
    _write(tmp_path / "prompts" / "large.md", "x" * (1024 * 1024 + 1), strip=False)

    result = save_baseline(
        report=_report([_case("document_summary_basic", True)], confidence=0.91),
        project_root=tmp_path,
        baseline_name="stable-v1",
        command="agentdoctor deep --rounds 3 --save-baseline --baseline-name stable-v1",
        agent_config_path="agent.yaml",
        report_dir="reports",
        now=NOW,
    )

    assert result.baseline_path.exists()
    assert result.snapshot_path.exists()
    assert result.file_hashes_path.exists()
    assert result.latest_path.exists()

    baseline = json.loads(result.baseline_path.read_text(encoding="utf-8"))
    snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
    latest = json.loads(result.latest_path.read_text(encoding="utf-8"))

    assert baseline["baseline_name"] == "stable-v1"
    assert baseline["diagnostic_summary"]["pass_count"] == 1
    assert baseline["failure_taxonomy_summary"]["failure_type_counts"] == {}
    assert baseline["test_result_summary"]["tests"][0]["test_id"] == "document_summary_basic"
    assert latest["latest_baseline_id"] == baseline["baseline_id"]
    assert snapshot["file_hashes"]["agent.yaml"].startswith("sha256:")
    assert snapshot["file_hashes"]["prompts/system.md"].startswith("sha256:")
    assert snapshot["file_hashes"]["prompts/large.md"].startswith("sha256:")
    assert "prompts/large.md" not in {
        item["source"] for item in snapshot["copied_config_files"]["copied_files"]
    }
    assert any("over 1 MB" in warning for warning in snapshot["warnings"])
    assert (result.baseline_dir / "copied_configs" / "agent.yaml").exists()
    assert (result.baseline_dir / "copied_configs" / "prompts" / "system.md").exists()
    assert ".env" in snapshot["excluded_files"]["excluded_files_detected"]
    assert _artifact_text(result.baseline_dir).find("do-not-leak") == -1


def test_non_git_project_snapshot_does_not_crash() -> None:
    tmp_path = _test_output_dir("non_git")
    result = save_baseline(
        report=_report([_case("key_path", True)], confidence=1.0),
        project_root=tmp_path,
        now=NOW,
    )

    snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["repo_state"]["git_available"] is False


def test_baseline_quality_high_and_low() -> None:
    tmp_path = _test_output_dir("quality")
    high = save_baseline(
        report=_report([_case("key_path", True)], confidence=0.96, mode="deep"),
        project_root=tmp_path / "high",
        now=NOW,
    )
    assert high.baseline.baseline_quality == "high"

    low = save_baseline(
        report=_report(
            [_case("forbidden_tool", False, tags=["safety", "tool_use"], failed_rule="tool_not_called")],
            confidence=0.2,
            mode="quick",
            review_required=True,
        ),
        project_root=tmp_path / "low",
        now=NOW,
    )
    assert low.baseline.baseline_quality == "low"
    assert "SAFETY_RISK" in low.baseline.failure_taxonomy_summary["critical_failure_types"]


def test_compare_detects_deltas_regressions_improvements_failure_types_and_state() -> None:
    tmp_path = _test_output_dir("compare")
    _write_agent(tmp_path / "agent.yaml")
    _write(tmp_path / "prompts" / "system.md", "Return Markdown.")
    _write(tmp_path / "tool_descriptions.yaml", "tools:\n  - name: document_reader\n")
    _write(tmp_path / "eval_config.yaml", "cases:\n  - id: markdown_schema\n")

    baseline = _report(
        [
            _case("markdown_schema", True, score=1.0, tags=["output_format"]),
            _case("missing_tool", False, score=0.2, failed_rule="tool_called", tags=["tool_use"]),
            _case("removed_case", True, score=1.0),
        ],
        confidence=0.84,
    )
    saved = save_baseline(
        report=baseline,
        project_root=tmp_path,
        baseline_name="stable-v1",
        agent_config_path="agent.yaml",
        now=NOW,
    )

    _write(tmp_path / "prompts" / "system.md", "Return strict JSON.")
    _write(tmp_path / "tool_descriptions.yaml", "tools:\n  - name: document_reader\n    description: changed\n")
    _write(tmp_path / "eval_config.yaml", "cases:\n  - id: markdown_schema\n  - id: safety_case\n")
    current = _report(
        [
            _case("markdown_schema", False, score=0.4, failed_rule="json_schema", tags=["output_format"]),
            _case("missing_tool", True, score=1.0, tags=["tool_use"]),
            _case("new_case", True, score=1.0),
            _case("safety_case", False, score=0.0, failed_rule="tool_not_called", tags=["safety", "tool_use"]),
        ],
        confidence=0.78,
        review_required=True,
    )
    compared = compare_against_baseline(
        report=current,
        project_root=tmp_path,
        baseline_ref="stable-v1",
        agent_config_path="agent.yaml",
        now=NOW,
    )

    assert compared.comparison is not None
    comparison = compared.comparison
    changes = {item.test_id: item.change_status for item in comparison.test_result_changes}
    failure_changes = {item.failure_type: item.change_status for item in comparison.failure_type_changes}

    assert comparison.overall_delta["confidence_delta"] == -0.06
    assert comparison.overall_delta["pass_count_delta"] == 0
    assert comparison.overall_delta["fail_count_delta"] == 1
    assert changes["markdown_schema"] == "regressed"
    assert changes["missing_tool"] == "improved"
    assert changes["new_case"] == "new_test"
    assert changes["removed_case"] == "removed_test"
    assert failure_changes["OUTPUT_SCHEMA_ERROR"] == "new"
    assert failure_changes["TOOL_MISSING"] == "resolved"
    assert failure_changes["SAFETY_RISK"] == "new"
    assert comparison.rollback_recommendation.rollback_recommended
    assert "prompts/system.md" in {
        item["path"] for item in comparison.agent_state_diff.changed_prompt_files
    }
    assert "tool_descriptions.yaml" in {
        item["path"] for item in comparison.agent_state_diff.changed_tool_configs
    }
    assert comparison.eval_suite_diff.eval_suite_changed
    assert comparison.comparable in {"partial", "weak"}
    assert compared.json_path and compared.json_path.exists()
    assert compared.markdown_path and "## 5. Failure Type Changes" in compared.markdown_path.read_text(encoding="utf-8")
    assert saved.baseline_path.exists()


def test_compare_latest_and_named_baseline_loading() -> None:
    tmp_path = _test_output_dir("load")
    saved = save_baseline(
        report=_report([_case("key_path", True)], confidence=0.9),
        project_root=tmp_path,
        baseline_name="stable-v1",
        now=NOW,
    )

    latest = load_baseline(tmp_path, "latest")
    named = load_baseline(tmp_path, "stable-v1")

    assert latest.baseline is not None
    assert named.baseline is not None
    assert latest.baseline["baseline_id"] == saved.baseline.baseline_id
    assert named.baseline["baseline_name"] == "stable-v1"


def test_compare_handles_corrupt_baseline_without_stack_trace() -> None:
    tmp_path = _test_output_dir("corrupt")
    latest = tmp_path / ".agentdoctor" / "baselines" / "latest.json"
    latest.parent.mkdir(parents=True)
    latest.write_text("{not json", encoding="utf-8")

    compared = compare_against_baseline(
        report=_report([_case("key_path", True)], confidence=1.0),
        project_root=tmp_path,
    )

    assert compared.comparison is None
    assert any("Corrupt baseline JSON" in warning for warning in compared.warnings)


def test_missing_snapshot_still_compares_partially() -> None:
    tmp_path = _test_output_dir("missing_snapshot")
    saved = save_baseline(
        report=_report([_case("key_path", True)], confidence=0.9),
        project_root=tmp_path,
        now=NOW,
    )
    saved.snapshot_path.unlink()

    compared = compare_against_baseline(
        report=_report([_case("key_path", True)], confidence=0.88),
        project_root=tmp_path,
        now=NOW,
    )

    assert compared.comparison is not None
    assert compared.comparison.agent_state_diff.missing_snapshot
    assert compared.comparison.comparable == "partial"


def test_compare_warns_when_agent_name_differs() -> None:
    tmp_path = _test_output_dir("agent_mismatch")
    _write_agent(tmp_path / "agent.yaml")
    save_baseline(
        report=_report([_case("key_path", True)], confidence=0.9),
        project_root=tmp_path,
        agent_config_path="agent.yaml",
        now=NOW,
    )
    _write(
        tmp_path / "agent.yaml",
        """
name: other_agent
tools: []
""",
    )

    compared = compare_against_baseline(
        report=_report([_case("key_path", True)], confidence=0.9),
        project_root=tmp_path,
        agent_config_path="agent.yaml",
        now=NOW,
    )

    assert compared.comparison is not None
    assert compared.comparison.comparable == "not_comparable"
    assert "Baseline agent name differs" in " ".join(compared.comparison.comparability_warnings)


def test_no_rollback_when_scorer_uncertain_dominates() -> None:
    recommendation = build_rollback_recommendation(
        comparison_comparable="full",
        baseline_quality="high",
        failure_type_changes=[
            _failure_change("SCORER_UNCERTAIN", 0, 5, "new"),
            _failure_change("UNKNOWN", 0, 1, "new"),
        ],
        severity_changes={"critical": {"delta": 0}},
        confidence_delta=-0.1,
        agent_state_diff=_empty_agent_state_diff(),
    )

    assert not recommendation.rollback_recommended
    assert recommendation.requires_human_review
    assert "scorers" in recommendation.reason


def test_overfitting_detection_from_failure_type_changes() -> None:
    assert detect_overfitting_from_failure_type_changes(
        [
            _failure_change("OUTPUT_SCHEMA_ERROR", 3, 0, "resolved"),
            _failure_change("TASK_INCOMPLETE", 0, 2, "new"),
            _failure_change("HALLUCINATION_RISK", 0, 1, "new"),
        ]
    )


def test_cli_save_and_compare_baseline_parse() -> None:
    tmp_path = _test_output_dir("cli")
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root)

    save = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "deep",
            "--rounds",
            "1",
            "--review",
            "never",
            "--save-baseline",
            "--baseline-name",
            "stable-v1",
            "--out",
            "reports",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )
    assert save.returncode == 0, save.stderr
    assert "Baseline Saved" in save.stdout
    assert (tmp_path / ".agentdoctor" / "baselines" / "latest.json").exists()

    compare = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "deep",
            "--rounds",
            "1",
            "--review",
            "never",
            "--compare-baseline",
            "--out",
            "reports_compare",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )
    assert compare.returncode == 0, compare.stderr
    assert "Baseline Comparison" in compare.stdout


def _report(
    cases: list[dict[str, object]],
    *,
    confidence: float,
    mode: str = "deep",
    review_required: bool = False,
) -> DiagnosticReport:
    test_cases: list[ADTestCase] = []
    test_results: list[ADTestResult] = []
    findings: list[Finding] = []
    scores = {
        "key_task_pass_rate": confidence,
        "tool_call_correctness": confidence,
        "output_schema_score": confidence,
        "safety_score": confidence,
    }
    for item in cases:
        test_case = ADTestCase(
            id=str(item["id"]),
            name=str(item.get("name") or item["id"]),
            description="fixture",
            input="fixture",
            expected_behavior="fixture",
            tags=list(item.get("tags") or ["task_completion"]),
        )
        failed_rule = item.get("failed_rule")
        rule_scores = []
        if failed_rule:
            rule_scores.append(
                RuleScore(
                    kind=str(failed_rule),
                    passed=False,
                    score=0.0,
                    severity=str(item.get("severity") or "error"),
                    message=str(item.get("message") or failed_rule),
                )
            )
        passed = bool(item["passed"])
        result = ADTestResult(
            test_case_id=test_case.id,
            trace_id=f"trace-{test_case.id}",
            passed=passed,
            warning_count=0,
            score=float(item.get("score", 1.0 if passed else 0.0)),
            check_rule=None,
            check_message=str(item.get("message") or ""),
            rule_scores=rule_scores,
        )
        test_cases.append(test_case)
        test_results.append(result)
        findings.append(
            Finding(
                id=f"F-{test_case.id}",
                severity="info" if passed else str(item.get("severity") or "error"),
                status="PASS" if passed else "FAIL",
                title=test_case.name,
                description=str(item.get("message") or test_case.name),
                related_test_id=test_case.id,
            )
        )
    round_report = DiagnosticRound(
        round_index=1,
        mode=mode,
        test_cases=test_cases,
        traces=[],
        scores=scores,
        findings=findings,
        review_items=[],
        confidence=confidence,
        started_at="2026-05-03T21:00:00+00:00",
        finished_at="2026-05-03T21:00:10+00:00",
        test_results=test_results,
    )
    pass_count = sum(1 for result in test_results if result.passed)
    fail_count = sum(1 for result in test_results if not result.passed)
    return DiagnosticReport(
        mode=mode,
        status="needs_review" if review_required else ("failed" if fail_count else "passed"),
        total_rounds_requested=1,
        total_rounds_executed=1,
        overall_confidence=confidence,
        pass_count=pass_count,
        fail_count=fail_count,
        warning_count=0,
        review_required=review_required,
        findings=findings,
        review_items=[],
        rounds=[round_report],
    )


def _case(
    test_id: str,
    passed: bool,
    *,
    score: float | None = None,
    failed_rule: str | None = None,
    tags: list[str] | None = None,
    message: str | None = None,
) -> dict[str, object]:
    return {
        "id": test_id,
        "passed": passed,
        "score": score if score is not None else (1.0 if passed else 0.0),
        "failed_rule": failed_rule,
        "tags": tags or ["task_completion"],
        "message": message or failed_rule or test_id,
    }


def _failure_change(failure_type: str, old: int, new: int, status: str):
    from contract2agent.baseline import FailureTypeChange

    return FailureTypeChange(
        failure_type=failure_type,
        baseline_count=old,
        current_count=new,
        delta=new - old,
        change_status=status,
        max_current_severity="error",
    )


def _empty_agent_state_diff():
    from contract2agent.baseline import AgentStateDiff

    return AgentStateDiff(
        changed_prompt_files=[],
        changed_tool_configs=[],
        changed_workflow_configs=[],
        changed_eval_configs=[],
        file_hash_changes=[],
        model_changed=False,
        tool_list_changed=False,
        tool_list_diff={"added_tools": [], "removed_tools": [], "changed_tools": []},
        approval_policy_changed=False,
        git_commit_changed=False,
        dirty_state_changed=False,
    )


def _write(path: Path, text: str, *, strip: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((text.strip() if strip else text) + ("\n" if strip else ""), encoding="utf-8")


def _write_agent(path: Path) -> None:
    _write(
        path,
        """
name: test_agent
agent_type: research_agent
goal: paper reading agent
model:
  provider: openai
  name: gpt-test
  temperature: 0.2
tools:
  - name: document_reader
    description: Read documents
workflow:
  review_policy: on-fail
""",
    )


def _artifact_text(path: Path) -> str:
    chunks = []
    for item in path.rglob("*"):
        if item.is_file():
            chunks.append(item.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def _test_output_dir(prefix: str) -> Path:
    import uuid

    root = Path(__file__).resolve().parents[1] / ".test_runs" / "baseline"
    path = root / f"{prefix}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path
