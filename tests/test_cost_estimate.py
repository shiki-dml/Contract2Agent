from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from contract2agent.cost_estimate import CostEstimateOptions, build_cost_estimate, run_cost_estimate
from contract2agent.cost_estimate.models import STATIC_ESTIMATE_NOTE, to_plain_data


@pytest.fixture
def tmp_path() -> Path:
    root = Path(__file__).resolve().parents[1] / ".test_runs" / "cost_estimate"
    path = root / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_estimated_diagnostic_cost_model_serializes_to_json(tmp_path: Path) -> None:
    triage = _write_triage(tmp_path, risk_level="low", tools=[], recommended_mode="quick")

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)
    data = to_plain_data(estimate)

    assert json.loads(json.dumps(data))["note"] == STATIC_ESTIMATE_NOTE
    assert data["estimated_tool_call_range"]["total"] == [0, 0]


def test_agentdoctor_cost_estimate_cli_command_exists(tmp_path: Path) -> None:
    triage = _write_triage(tmp_path, risk_level="low", tools=[], recommended_mode="quick")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "cost-estimate",
            "--from-triage",
            str(triage),
            "--output",
            str(tmp_path / ".agentdoctor" / "cost"),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "AgentDoctor Time Cost Estimate" in completed.stdout
    assert (tmp_path / ".agentdoctor" / "cost" / "latest.md").exists()


def test_triage_include_cost_writes_cost_report(tmp_path: Path) -> None:
    _write(tmp_path / "agent.yaml", "name: test_agent\ntools: []")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "triage",
            "--project-root",
            str(tmp_path),
            "--include-cost",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "AgentDoctor Time Cost Estimate" in completed.stdout
    assert (tmp_path / ".agentdoctor" / "cost" / "latest.md").exists()


def test_missing_triage_does_not_crash(tmp_path: Path) -> None:
    estimate, _ = run_cost_estimate(
        CostEstimateOptions(
            from_triage=tmp_path / ".agentdoctor" / "triage" / "missing.json",
            output=tmp_path / ".agentdoctor" / "cost",
        ),
        cwd=tmp_path,
    )

    assert estimate.confidence == "unknown"
    assert estimate.complexity_level == "unknown"
    assert estimate.recommended_command == "agentdoctor triage --include-cost"
    assert any("Run agentdoctor triage first" in warning for warning in estimate.warnings)


def test_low_risk_quick_estimate(tmp_path: Path) -> None:
    triage = _write_triage(
        tmp_path,
        risk_level="low",
        tools=[],
        recommended_mode="quick",
        tags=["task_completion", "output_format"],
        rounds=1,
    )

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)

    assert estimate.complexity_level == "low"
    assert estimate.estimated_rounds == 1
    assert 3 <= estimate.estimated_test_count_range[0] <= estimate.estimated_test_count_range[1] <= 24
    assert estimate.recommended_command == "agentdoctor quick"


def test_medium_risk_deep_estimate(tmp_path: Path) -> None:
    triage = _write_triage(
        tmp_path,
        risk_level="medium",
        tools=[_tool("document_reader", "document_reading", "medium", "read_only")],
        recommended_mode="deep",
        tags=["tool_use", "source_grounding", "error_handling"],
        rounds=3,
    )

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)

    assert estimate.complexity_level == "medium"
    assert estimate.estimated_rounds == 3
    assert any(driver.id == "source_grounding_validation" for driver in estimate.cost_drivers)


def test_high_risk_deep_estimate(tmp_path: Path) -> None:
    triage = _write_triage(
        tmp_path,
        risk_level="high",
        tools=[_tool("shell", "shell_execution", "high", "unknown")],
        recommended_mode="deep",
        tags=["tool_use", "safety", "regression"],
        rounds=5,
    )

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)

    assert estimate.complexity_level in {"high", "very_high"}
    assert estimate.estimated_human_review_items.review_burden_level == "high"
    assert estimate.budget_guardrails.stop_on_safety_risk is True


def test_auto_estimate_with_eligible_readiness_and_baseline(tmp_path: Path) -> None:
    _write_baseline(tmp_path, {"avg_runtime_seconds": 120, "slowest_tests": ["tool_use"]})
    triage = _write_triage(
        tmp_path,
        risk_level="medium",
        tools=[],
        recommended_mode="auto",
        mode="auto",
        tags=["task_completion", "output_schema"],
        baseline_exists=True,
        patch_eligible=True,
        auto_eligible=True,
    )

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage, mode="auto"), cwd=tmp_path)

    assert estimate.auto_cost_plan is not None
    assert estimate.auto_cost_plan.auto_recommended is True
    assert estimate.estimated_auto_iterations[1] >= 1
    assert estimate.estimated_patch_attempts[1] >= 1
    assert estimate.auto_cost_plan.overfitting_risk in {"low", "medium", "high"}


def test_auto_unsafe_recommends_deep_first(tmp_path: Path) -> None:
    triage = _write_triage(
        tmp_path,
        risk_level="high",
        tools=[_tool("email_sender", "email", "high", "external_write")],
        recommended_mode="deep",
        mode="deep",
        tags=["safety", "tool_use"],
        patch_eligible=False,
        auto_eligible=False,
        auto_blockers=["external write tool exists without approval rule"],
    )

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage, mode="auto"), cwd=tmp_path)

    assert estimate.auto_cost_plan is not None
    assert estimate.auto_cost_plan.auto_recommended is False
    assert estimate.recommended_command.startswith("agentdoctor deep")
    assert any("Auto is not recommended" in warning for warning in estimate.warnings)


def test_loop_risk_adds_cost_risk_and_guardrail(tmp_path: Path) -> None:
    triage = _write_triage(
        tmp_path,
        risk_level="medium",
        tools=[_tool("retriever", "retrieval", "medium", "read_only")],
        tags=["tool_use"],
    )

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)
    failures = {risk.failure_type for risk in estimate.failure_type_cost_risks}

    assert "LOOP_RISK" in failures
    assert estimate.budget_guardrails.max_tool_calls_per_test is not None
    assert estimate.budget_guardrails.stop_on_loop_risk is True


def test_low_stability_increases_repeated_run_estimate(tmp_path: Path) -> None:
    triage = _write_triage(tmp_path, risk_level="medium", tools=[], tags=["stability"])

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)

    assert any(risk.failure_type == "LOW_STABILITY" for risk in estimate.failure_type_cost_risks)
    assert estimate.budget_guardrails.max_repeated_runs == 3
    assert any(driver.id == "repeated_stability_runs" for driver in estimate.cost_drivers)


def test_tool_argument_error_adds_retry_risk(tmp_path: Path) -> None:
    triage = _write_triage(
        tmp_path,
        risk_level="medium",
        tools=[_tool("document_reader", "document_reading", "medium", "read_only")],
        tags=["tool_arguments"],
    )

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)

    assert any(risk.failure_type == "TOOL_ARGUMENT_ERROR" for risk in estimate.failure_type_cost_risks)


def test_error_handling_missing_adds_wasted_tool_call_risk(tmp_path: Path) -> None:
    triage = _write_triage(tmp_path, risk_level="medium", tools=[], tags=["error_handling"])

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)

    assert any(risk.failure_type == "ERROR_HANDLING_MISSING" for risk in estimate.failure_type_cost_risks)


def test_hallucination_risk_adds_source_grounding_cost(tmp_path: Path) -> None:
    triage = _write_triage(
        tmp_path,
        risk_level="medium",
        tools=[_tool("document_reader", "document_reading", "medium", "read_only")],
        tags=["hallucination", "source_grounding"],
    )

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)

    assert any(risk.failure_type == "HALLUCINATION_RISK" for risk in estimate.failure_type_cost_risks)
    assert any(driver.id == "source_grounding_validation" for driver in estimate.cost_drivers)
    assert "source_grounding" in estimate.patch_preview_cost_context.recommended_validation_tags


def test_baseline_missing_does_not_crash(tmp_path: Path) -> None:
    triage = _write_triage(tmp_path, risk_level="medium", tools=[])

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)

    assert estimate.baseline_cost_context is not None
    assert estimate.baseline_cost_context.baseline_exists is False
    assert any("No baseline found" in warning for warning in estimate.warnings)


def test_baseline_with_historical_runtime_refines_runtime_context(tmp_path: Path) -> None:
    _write_baseline(
        tmp_path,
        {
            "avg_runtime_seconds": 180,
            "previous_slowest_tests": ["source_grounding"],
            "previous_slowest_failure_types": ["HALLUCINATION_RISK"],
        },
    )
    triage = _write_triage(tmp_path, risk_level="medium", tools=[], baseline_exists=True)

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)

    assert estimate.baseline_cost_context.historical_cost_used is True
    assert estimate.estimated_runtime_range.min_seconds == 90
    assert estimate.estimated_runtime_range.max_seconds == 360


def test_mode_comparison_generated_with_one_recommendation(tmp_path: Path) -> None:
    triage = _write_triage(tmp_path, risk_level="medium", tools=[], recommended_mode="deep")

    estimate = build_cost_estimate(CostEstimateOptions(from_triage=triage), cwd=tmp_path)

    assert {item.mode for item in estimate.mode_comparison} == {"quick", "deep", "auto"}
    assert sum(1 for item in estimate.mode_comparison if item.recommended) == 1


def test_budget_profile_conservative_lowers_guardrails(tmp_path: Path) -> None:
    triage = _write_triage(tmp_path, risk_level="medium", tools=[], recommended_mode="deep", rounds=3)

    estimate = build_cost_estimate(
        CostEstimateOptions(from_triage=triage, budget_profile="conservative"),
        cwd=tmp_path,
    )

    assert estimate.budget_guardrails.max_rounds <= 2
    assert estimate.budget_guardrails.max_tests <= 16
    assert estimate.budget_guardrails.max_auto_iterations == 0


def test_budget_profile_thorough_expands_guardrails(tmp_path: Path) -> None:
    triage = _write_triage(tmp_path, risk_level="high", tools=[], recommended_mode="deep", rounds=5)

    estimate = build_cost_estimate(
        CostEstimateOptions(from_triage=triage, budget_profile="thorough"),
        cwd=tmp_path,
    )

    assert estimate.budget_guardrails.max_rounds >= 5
    assert estimate.budget_guardrails.max_tests >= 75
    assert estimate.budget_guardrails.max_repeated_runs >= 5


def test_report_output_writes_latest_markdown_and_json(tmp_path: Path) -> None:
    triage = _write_triage(tmp_path, risk_level="low", tools=[], recommended_mode="quick")

    estimate, _ = run_cost_estimate(
        CostEstimateOptions(from_triage=triage, output=tmp_path / ".agentdoctor" / "cost"),
        cwd=tmp_path,
    )
    latest_md = tmp_path / ".agentdoctor" / "cost" / "latest.md"
    latest_json = tmp_path / ".agentdoctor" / "cost" / "latest.json"

    assert latest_md.exists()
    assert latest_json.exists()
    assert STATIC_ESTIMATE_NOTE in latest_md.read_text(encoding="utf-8")
    assert json.loads(latest_json.read_text(encoding="utf-8"))["cost_estimate_id"] == estimate.cost_estimate_id


def test_secret_exclusion_does_not_include_env_contents(tmp_path: Path) -> None:
    _write(tmp_path / ".env", "SECRET_VALUE=do-not-leak")
    triage = _write_triage(
        tmp_path,
        risk_level="low",
        tools=[],
        recommended_mode="quick",
        eval_sources=[{"path": ".env", "status": "found"}],
    )

    estimate, _ = run_cost_estimate(
        CostEstimateOptions(from_triage=triage, output=tmp_path / ".agentdoctor" / "cost"),
        cwd=tmp_path,
    )
    report = json.dumps(to_plain_data(estimate))

    assert "do-not-leak" not in report
    assert "SECRET_VALUE" not in report


def _write_triage(
    root: Path,
    *,
    risk_level: str,
    tools: list[dict] | None,
    recommended_mode: str = "deep",
    mode: str | None = None,
    tags: list[str] | None = None,
    rounds: int | None = None,
    baseline_exists: bool = False,
    patch_eligible: bool = True,
    auto_eligible: bool = False,
    auto_blockers: list[str] | None = None,
    eval_sources: list[dict] | None = None,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    tags = tags or ["task_completion", "output_format", "error_handling"]
    mode = mode or recommended_mode
    rounds = rounds or (1 if mode == "quick" else 6 if mode == "auto" else 5 if risk_level == "high" else 3)
    data = {
        "triage_id": "triage_20260503_001",
        "created_at": "2026-05-03T22:40:00+08:00",
        "project_root": str(root),
        "input_sources": {
            "evals": eval_sources or [],
            "baseline": {
                "path": ".agentdoctor/baselines/latest.json",
                "status": "found" if baseline_exists else "missing",
            },
        },
        "agent_summary": {"name": "test_agent", "tool_count": len(tools or []), "eval_case_count": 0},
        "detected_capabilities": {"tools": tools or []},
        "agent_classification": {"agent_type": "unknown", "classification_confidence": "low"},
        "risk_assessment": {
            "risk_level": risk_level,
            "risk_score": 1,
            "high_risk_tools": [tool["name"] for tool in tools or [] if tool.get("risk_level") == "high"],
            "recommended_review_policy": "each-round" if risk_level == "high" else "on-fail",
        },
        "eval_coverage": {
            "eval_case_count": 0,
            "detected_tags": tags,
            "covered_areas": tags,
            "missing_areas": [],
        },
        "key_behaviors_to_test": [
            {"id": "behavior_max_tool_calls", "related_risks": ["LOOP_RISK"]} if tools else {},
            {"id": "behavior_stability", "related_risks": ["LOW_STABILITY"]} if "stability" in tags else {},
        ],
        "missing_information": [
            {"id": "missing_error_handling", "related_failure_type": "ERROR_HANDLING_MISSING"}
            if "error_handling" in tags
            else {}
        ],
        "warnings": [],
        "suggested_test_tags": tags,
        "suggested_round_plan": {
            "mode": mode,
            "rounds": rounds,
            "review_policy": "each-round" if risk_level == "high" else "on-fail",
            "round_focuses": [{"round_index": 1, "focus": "static", "suggested_tags": tags}],
        },
        "baseline_status": {
            "exists": baseline_exists,
            "path": ".agentdoctor/baselines/latest.json",
        },
        "patch_preview_readiness": {
            "eligible": patch_eligible,
            "allowed_files_detected": ["prompts/system.md"] if patch_eligible else [],
            "missing_patch_targets": [],
            "risk_notes": [] if patch_eligible else ["No safe patch target found."],
        },
        "auto_readiness": {
            "eligible": auto_eligible,
            "reasons": ["safe prompt/config patch target detected"] if auto_eligible else [],
            "blockers": auto_blockers or ([] if auto_eligible else ["auto disabled"]),
        },
        "recommendation": {
            "recommended_mode": recommended_mode,
            "recommended_rounds": rounds,
            "suggested_review_policy": "each-round" if risk_level == "high" else "on-fail",
        },
        "recommended_next_command": f"agentdoctor {recommended_mode}",
    }
    path = root / ".agentdoctor" / "triage" / "latest.json"
    _write(path, json.dumps(data, indent=2))
    return path


def _tool(name: str, category: str, risk: str, side_effect: str) -> dict:
    return {
        "name": name,
        "description": name,
        "category": category,
        "risk_level": risk,
        "side_effect_level": side_effect,
        "requires_confirmation": risk == "high",
    }


def _write_baseline(root: Path, data: dict) -> None:
    _write(root / ".agentdoctor" / "baselines" / "latest.json", json.dumps(data, indent=2))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
