from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from contract2agent.evaluation import (
    AgentProfile,
    AgentTypeRegistry,
    CapabilityClassifier,
    EvalCategoryRegistry,
    EvidenceResolver,
    ExperimentSummary,
    ReportRenderer,
    ScoringEngine,
    ToolSurface,
    default_source_references,
    evaluate_agent_profile,
    load_agent_profile,
    load_experiment_results,
    to_dict,
)


ROOT = Path(__file__).resolve().parents[1]


def test_agent_profile_schema_serializes_to_json() -> None:
    profile = _coding_profile()

    data = json.loads(json.dumps(to_dict(profile)))

    assert data["agent_id"] == "agent-under-test"
    assert data["allowed_actions"] == ["read_workspace", "write_workspace"]
    assert data["tools"][0]["name"] == "file_reader"
    assert data["can_run_code"] is True


def test_tool_surface_schema_serializes_to_json() -> None:
    tool = ToolSurface(
        name="submit_button",
        category="browser",
        mode="submit",
        side_effect_level="high",
        requires_approval=True,
        can_modify_state=True,
        can_access_private_data=True,
        risk_tags=["external_state"],
        evidence=["tool inventory"],
    )

    data = json.loads(json.dumps(to_dict(tool)))

    assert data["can_modify_state"] is True
    assert data["can_access_private_data"] is True
    assert data["evidence"] == ["tool inventory"]


def test_agent_type_registry_contains_required_types() -> None:
    registry = AgentTypeRegistry.default()

    assert {
        "coding_agent",
        "file_reading_agent",
        "contract_review_agent",
        "browser_navigation_agent",
        "financial_transaction_agent_simulated",
        "research_agent",
        "workflow_automation_agent",
        "general_tool_use_agent",
        "unknown_agent",
    }.issubset(set(registry.type_ids()))
    assert registry.get("financial_transaction_agent_simulated").simulation_only is True


def test_eval_category_registry_is_broad_not_deep_specialized() -> None:
    categories = EvalCategoryRegistry.default().all()
    category_ids = {category.category_id for category in categories}

    assert "coding_change_safety" in category_ids
    assert "browser_task_flow" in category_ids
    assert "profile_completion" in category_ids
    assert "coding_patch_correctness" not in category_ids


def test_classification_uses_tools_and_tasks_not_exact_agent_name() -> None:
    profile = _coding_profile(name="Calendar assistant")

    classification = CapabilityClassifier().classify(profile)

    assert "coding_agent" in classification.primary_types
    assert classification.confidence_by_type["coding_agent"] >= 0.42
    assert any(
        signal.source_field == "tools/tool_permissions/data_access"
        for signal in classification.matched_signals["coding_agent"]
    )


def test_changing_name_alone_does_not_change_classification_materially() -> None:
    first = _coding_profile(name="Repo helper")
    second = replace(first, name="Browser Finance Super Agent")

    first_classification = CapabilityClassifier().classify(first)
    second_classification = CapabilityClassifier().classify(second)

    assert first_classification.primary_types == second_classification.primary_types
    assert first_classification.secondary_types == second_classification.secondary_types
    assert first_classification.confidence_by_type == second_classification.confidence_by_type


def test_changing_tools_tasks_with_same_name_changes_classification() -> None:
    coding = _coding_profile(name="Generic assistant")
    browser = replace(
        coding,
        agent_id="browser-agent",
        declared_capabilities=["navigate websites"],
        tools=[
            ToolSurface(name="browser_navigate", category="browser", mode="navigate"),
            ToolSurface(name="form_fill", category="browser", mode="write"),
        ],
        tool_permissions=["use_browser", "read_page_state"],
        can_write_files=False,
        can_run_code=False,
        can_use_browser=True,
        can_use_network=True,
        sample_tasks=["Navigate a controlled website and verify page state."],
    )

    coding_classification = CapabilityClassifier().classify(coding)
    browser_classification = CapabilityClassifier().classify(browser)

    assert "coding_agent" in coding_classification.primary_types
    assert "browser_navigation_agent" in browser_classification.primary_types
    assert coding_classification.primary_types != browser_classification.primary_types


def test_unknown_agent_returns_unknown_and_recommended_next_evidence() -> None:
    profile = AgentProfile(agent_id="unknown", name="Sparse profile")

    evidence, scorecard, prediction = evaluate_agent_profile(profile)

    assert evidence.classification.primary_types == ["unknown_agent"]
    assert prediction.predicted_success is None
    assert prediction.confidence <= 0.05
    assert "complete_agent_profile" in prediction.recommended_next_tests
    assert any("Tool surface" in item for item in prediction.missing_evidence)


def test_declared_only_capabilities_have_lower_confidence_than_observed_evidence() -> None:
    declared_only = AgentProfile(
        agent_id="declared-only",
        name="Assistant",
        description="Claims it can edit code and run tests.",
        declared_capabilities=["edit code", "run tests"],
    )
    observed = _coding_profile()

    declared_evidence, declared_scorecard, declared_prediction = evaluate_agent_profile(declared_only)
    observed_evidence, observed_scorecard, observed_prediction = evaluate_agent_profile(
        observed,
        [_experiment(observed.agent_id, "observed_experiment")],
    )

    assert declared_evidence.evidence_quality_score < observed_evidence.evidence_quality_score
    assert declared_scorecard.confidence < observed_scorecard.confidence
    assert declared_prediction.confidence < observed_prediction.confidence


def test_benchmark_references_do_not_become_direct_scores() -> None:
    profile = _coding_profile()
    classification = CapabilityClassifier().classify(profile)
    evidence = EvidenceResolver().resolve(
        profile,
        classification,
        experiment_results=[],
        benchmark_references=default_source_references(),
    )
    scorecard = ScoringEngine().score(evidence)

    assert any(source.source_type == "benchmark_reference" for source in evidence.data_sources)
    assert scorecard.overall_score is None
    assert not any(
        source_id in {"swe_bench_reference", "webarena_reference"}
        for score in scorecard.preliminary_scores
        for source_id in score.evidence_sources
    )
    assert any("Reference sources" in item for item in scorecard.missing_evidence)


def test_financial_transaction_agent_is_simulation_only_and_high_risk() -> None:
    profile = AgentProfile(
        agent_id="financial-agent",
        name="Approval workflow",
        description="Simulates payment and trade confirmation only.",
        declared_capabilities=["simulate payment", "refuse unsafe transaction"],
        tools=[
            ToolSurface(
                name="simulated_payment_gateway",
                category="transaction_simulator",
                mode="authorize",
                side_effect_level="high",
                requires_approval=True,
                risk_tags=["payment", "simulation_only"],
            )
        ],
        can_execute_transactions=True,
        requires_human_approval=True,
        environment="simulated_sandbox",
        sample_tasks=["Authorize a simulated payment only after explicit confirmation."],
        policy_constraints=["simulation only", "no real funds"],
    )

    evidence, _scorecard, prediction = evaluate_agent_profile(profile)

    assert "financial_transaction_agent_simulated" in evidence.classification.primary_types
    assert "financial_transaction_simulation_only" in evidence.classification.risk_flags
    assert "high_risk_action_surface" in evidence.classification.risk_flags
    assert "run_simulated_authorization_and_refusal_tests" in prediction.recommended_next_tests


def test_multi_label_classification_works() -> None:
    profile = _coding_profile()
    profile.declared_capabilities.append("navigate websites")
    profile.tools.append(ToolSurface(name="browser_navigate", category="browser", mode="navigate"))
    profile.can_use_browser = True
    profile.can_use_network = True
    profile.sample_tasks.append("Navigate a controlled website and inspect page state.")

    classification = CapabilityClassifier().classify(profile)

    assert "coding_agent" in classification.primary_types
    assert "browser_navigation_agent" in classification.primary_types


def test_evidence_source_reliability_affects_confidence() -> None:
    profile = _coding_profile()
    classification = CapabilityClassifier().classify(profile)
    resolver = EvidenceResolver()

    synthetic = resolver.resolve(
        profile,
        classification,
        experiment_results=[_experiment(profile.agent_id, "synthetic_sample")],
    )
    observed = resolver.resolve(
        profile,
        classification,
        experiment_results=[_experiment(profile.agent_id, "observed_experiment")],
    )

    assert synthetic.evidence_quality_score < observed.evidence_quality_score
    assert ScoringEngine().score(synthetic).confidence < ScoringEngine().score(observed).confidence


def test_outcome_prediction_includes_missing_evidence_and_next_tests() -> None:
    profile = _coding_profile()
    _evidence, _scorecard, prediction = evaluate_agent_profile(profile)

    assert prediction.missing_evidence
    assert prediction.recommended_next_tests
    assert any("no linked observed" in basis.lower() for basis in prediction.evidence_basis)


def test_report_json_is_serializable() -> None:
    profile = _coding_profile()
    evidence, scorecard, prediction = evaluate_agent_profile(
        profile,
        [_experiment(profile.agent_id, "observed_experiment")],
    )

    data = ReportRenderer().to_dict(profile, evidence, scorecard, prediction)

    assert json.loads(json.dumps(data))["agent_profile"]["agent_id"] == profile.agent_id


def test_markdown_report_includes_evidence_basis_and_limitations() -> None:
    profile = AgentProfile(agent_id="unknown", name="Sparse profile")
    evidence, scorecard, prediction = evaluate_agent_profile(profile)

    markdown = ReportRenderer().render_markdown(profile, evidence, scorecard, prediction)

    assert "## Evidence Basis" in markdown
    assert "## Limitations" in markdown
    assert "Benchmark references are contextual" in markdown


def test_vague_input_does_not_produce_high_confidence() -> None:
    profile = AgentProfile(
        agent_id="vague",
        name="Great Agent",
        description="A helpful assistant that can do anything.",
        declared_capabilities=["help users"],
    )

    evidence, scorecard, prediction = evaluate_agent_profile(profile)

    assert evidence.classification.primary_types == ["unknown_agent"]
    assert scorecard.confidence < 0.5
    assert prediction.predicted_success is None


def test_sample_source_references_do_not_imply_direct_performance_scores() -> None:
    sources = default_source_references()

    assert sources
    assert all(source.reliability <= 0.2 for source in sources)
    assert all(
        any("no " in limitation.lower() and "score" in limitation.lower() for limitation in source.limitations)
        or source.source_type == "curated_research_reference"
        for source in sources
    )


def test_overfit_audit_section_exists() -> None:
    audit = (ROOT / "bug_audit.md").read_text(encoding="utf-8")

    assert "Agent Evaluation Generalization and Overfitting Audit" in audit
    assert "Overfit patterns found" in audit
    assert "Logic removed or refactored" in audit


def test_eval_agent_cli_writes_markdown_report(tmp_path: Path) -> None:
    report_path = tmp_path / "agent_eval.md"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "eval-agent",
            "--profile",
            str(ROOT / "examples" / "agent_eval" / "coding_agent_profile.json"),
            "--results",
            str(ROOT / "examples" / "agent_eval" / "sample_experiment_results.json"),
            "--benchmarks",
            str(ROOT / "examples" / "agent_eval" / "benchmark_references.json"),
            "--out",
            str(report_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert report_path.exists()
    markdown = report_path.read_text(encoding="utf-8")
    assert "# Agent Evaluation Report" in markdown
    assert "Applicable Eval Categories" in markdown


def test_sample_profiles_and_results_load_from_examples() -> None:
    profile = load_agent_profile(ROOT / "examples" / "agent_eval" / "coding_agent_profile.json")
    results = load_experiment_results(ROOT / "examples" / "agent_eval" / "sample_experiment_results.json")

    assert profile.agent_id == "sample-coding-agent"
    assert any(result.agent_id == profile.agent_id for result in results)


def _coding_profile(name: str = "Generic coding assistant") -> AgentProfile:
    return AgentProfile(
        agent_id="agent-under-test",
        name=name,
        description="Repairs repository code with tests and patch summaries.",
        declared_capabilities=["edit code", "run tests"],
        tools=[
            ToolSurface(name="file_reader", category="filesystem", mode="read"),
            ToolSurface(name="code_editor", category="filesystem", mode="write"),
            ToolSurface(name="shell", category="execution", mode="command"),
            ToolSurface(name="test_runner", category="execution", mode="command"),
        ],
        tool_permissions=["read_workspace", "write_workspace", "run_tests"],
        data_access=["repository_files"],
        allowed_actions=["read_workspace", "write_workspace"],
        forbidden_actions=["destructive shell commands"],
        can_read_files=True,
        can_write_files=True,
        can_run_code=True,
        requires_human_approval=True,
        autonomy_level="medium",
        environment="local_workspace",
        sample_tasks=["Fix failing tests with a minimal patch.", "Run tests before reporting success."],
        policy_constraints=["stay inside workspace"],
    )


def _experiment(agent_id: str, source_type: str) -> ExperimentSummary:
    return ExperimentSummary(
        result_id=f"{source_type}-001",
        agent_id=agent_id,
        agent_type="coding_agent",
        eval_category="coding_change_safety",
        task_summary="Edited a small fixture and reported test output.",
        metrics={"task_success": 0.8},
        verdict="pass_with_limitations",
        evidence_source=source_type,
        trace_available=True,
        limitations=["Synthetic test fixture."],
    )
