from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from contract2agent.privacy_eval import (
    PrivacyDataFlow,
    PrivacyEvalProfile,
    PrivacyTool,
    PrivacyTrainingConfig,
    analyze_privacy_profile,
    build_privacy_report,
    load_privacy_profile,
    privacy_source_references,
    to_dict,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = ROOT / "examples" / "privacy_eval"


def test_privacy_profile_schema_serializes() -> None:
    profile = PrivacyEvalProfile(
        profile_id="p1",
        name="Privacy profile",
        sensitive_data=["email"],
        data_flows=[
            PrivacyDataFlow(
                flow_id="flow1",
                channel="output",
                contains_sensitive_data=True,
                controls=["redaction"],
            )
        ],
        tools=[
            PrivacyTool(
                name="external_tool",
                receives_sensitive_data=True,
                sends_external=True,
                requires_approval=True,
            )
        ],
        training=PrivacyTrainingConfig(
            uses_private_training=True,
            sensitive_training_data=True,
            privacy_mechanism="BLT-DP-FTRL",
            privacy_unit="user",
            epsilon=3.0,
            delta=1e-7,
            clipping_norm=1.0,
            noise_multiplier=1.2,
            accountant="RDP",
            federated=True,
            multi_participation=True,
        ),
    )

    data = json.loads(json.dumps(to_dict(profile)))

    assert data["profile_id"] == "p1"
    assert data["data_flows"][0]["flow_id"] == "flow1"
    assert data["training"]["privacy_mechanism"] == "BLT-DP-FTRL"


def test_healthcare_example_flags_internal_and_tool_privacy_risks() -> None:
    profile = load_privacy_profile(EXAMPLE_ROOT / "healthcare_multi_agent_privacy.json")

    scorecard = analyze_privacy_profile(profile)
    finding_ids = {finding.finding_id for finding in scorecard.findings}

    assert scorecard.overall_privacy_readiness < 0.7
    assert "triage_to_scheduler_tool:unprotected_sensitive_flow" in finding_ids
    assert "debug_log_dump:unprotected_sensitive_flow" in finding_ids
    assert "tool:external_scheduler:external_sensitive_no_approval" in finding_ids
    assert "trace_inter_agent_messages_for_sensitive_fields" in scorecard.recommended_next_tests


def test_blt_profile_records_context_without_fake_observed_score() -> None:
    profile = load_privacy_profile(EXAMPLE_ROOT / "federated_keyboard_blt_profile.json")

    scorecard = analyze_privacy_profile(profile)
    finding_ids = {finding.finding_id for finding in scorecard.findings}

    assert scorecard.dp_readiness >= 0.9
    assert "training:blt_context_recorded" in finding_ids
    assert "attach_dp_accountant_output_and_training_artifacts" in scorecard.recommended_next_tests
    assert any("does not prove runtime privacy" in item for item in scorecard.limitations)


def test_tree_aggregation_multi_participation_recommends_blt() -> None:
    profile = PrivacyEvalProfile(
        profile_id="tree-profile",
        name="Tree aggregation FL",
        sensitive_data=["private updates"],
        training=PrivacyTrainingConfig(
            uses_private_training=True,
            sensitive_training_data=True,
            privacy_mechanism="tree_aggregation_dp_ftrl",
            privacy_unit="user",
            epsilon=4.0,
            delta=1e-7,
            clipping_norm=1.0,
            noise_multiplier=1.0,
            accountant="RDP",
            federated=True,
            multi_participation=True,
        ),
    )

    scorecard = analyze_privacy_profile(profile)

    assert any(
        finding.finding_id == "training:tree_aggregation_multi_participation"
        and "BLT" in finding.recommendation
        for finding in scorecard.findings
    )


def test_privacy_report_includes_references_and_findings() -> None:
    profile = load_privacy_profile(EXAMPLE_ROOT / "rag_customer_support_privacy.json")

    report = build_privacy_report(profile)

    assert "Privacy Evaluation Report" in report.markdown
    assert "tool_debug_artifact:unprotected_sensitive_flow" in report.markdown
    assert "agentdojo" in report.markdown
    assert json.loads(json.dumps(report.json_report))["profile"]["profile_id"] == profile.profile_id


def test_privacy_source_references_are_contextual() -> None:
    sources = privacy_source_references()

    assert {"agentleak", "agentdojo", "opacus", "opendp", "blt_dp_ftrl"}.issubset(
        {str(source["source_id"]) for source in sources}
    )
    assert all("limitations" in source for source in sources)
    assert all(
        not any("score" in str(note).casefold() for note in source.get("notes", []))
        for source in sources
    )


def test_privacy_eval_cli_writes_markdown_report(tmp_path: Path) -> None:
    report_path = tmp_path / "privacy.md"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "privacy-eval",
            "--profile",
            str(EXAMPLE_ROOT / "healthcare_multi_agent_privacy.json"),
            "--out",
            str(report_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert report_path.exists()
    assert "# Privacy Evaluation Report" in report_path.read_text(encoding="utf-8")


def test_privacy_eval_cli_lists_references() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "contract2agent.cli", "privacy-eval", "--list-references"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "agentleak" in completed.stdout
    assert "blt_dp_ftrl" in completed.stdout
