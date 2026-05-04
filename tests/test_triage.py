from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from contract2agent.triage import TriageOptions, run_triage
from contract2agent.triage.classifiers import classify_tools


NOW = datetime(2026, 5, 3, 21, 30, 12, tzinfo=timezone.utc)


@pytest.fixture
def tmp_path() -> Path:
    base = Path(
        os.environ.get(
            "AGENTDOCTOR_TEST_ROOT",
            str(Path(__file__).resolve().parents[1] / ".tmp_pytest_base" / "agentdoctor-test-runs"),
        )
    )
    root = base / "triage"
    path = root / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_agentdoctor_triage_cli_command_exists(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=[])

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "triage",
            "--project-root",
            str(tmp_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "AgentDoctor Triage Plan" in completed.stdout
    assert (tmp_path / ".agentdoctor" / "triage" / "latest.md").exists()


def test_agent_config_discovery_finds_agent_yaml(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=[])

    plan = _triage(tmp_path)

    assert plan.input_sources["agent_config"].status == "found"
    assert plan.input_sources["agent_config"].path == "agent.yaml"


def test_agent_option_takes_priority(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", name="default_agent", tools=[])
    _write_agent(tmp_path / "agents" / "coder.yaml", name="coder_agent", tools=["file_editor"])

    plan = _triage(tmp_path, agent=Path("agents/coder.yaml"))

    assert plan.agent_summary.name == "coder_agent"
    assert plan.input_sources["agent_config"].path == "agents/coder.yaml"


def test_triage_rejects_agent_path_outside_project_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside_agent.yaml"
    _write_agent(project / "agent.yaml", name="inside_agent", tools=[])
    _write_agent(outside, name="outside_secret_agent", tools=[])

    plan = _triage(project, agent=Path("../outside_agent.yaml"))
    report = (project / ".agentdoctor" / "triage" / "latest.json").read_text(encoding="utf-8")

    assert plan.input_sources["agent_config"].status == "skipped"
    assert plan.agent_summary.name != "outside_secret_agent"
    assert "outside_secret_agent" not in report
    assert any(warning.id == "agent_path_outside_project_root" for warning in plan.warnings)


def test_multiple_agents_warning_uses_sorted_default(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", name="root_agent", tools=[])
    _write_agent(tmp_path / "agents" / "other.yaml", name="other_agent", tools=[])

    plan = _triage(tmp_path)

    assert plan.agent_summary.name == "root_agent"
    assert any(warning.id == "multiple_agent_configs" for warning in plan.warnings)


def test_missing_config_does_not_crash(tmp_path: Path) -> None:
    plan = _triage(tmp_path)

    assert plan.agent_classification.agent_type == "unknown"
    assert plan.risk_assessment.risk_level == "unknown"
    assert _has_missing(plan, "missing_agent_config")
    assert plan.recommended_next_command == "agentdoctor triage --agent ./agent.yaml"


def test_research_agent_classification(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=["document_reader"])
    _write(
        tmp_path / "prompts" / "system.md",
        "Summarize academic papers in Markdown. If the file is missing, ask for clarification.",
    )

    plan = _triage(tmp_path, goal="paper reading agent")

    assert plan.agent_classification.agent_type == "research_agent"
    assert plan.agent_classification.classification_confidence == "high"
    behavior_ids = {behavior.id for behavior in plan.key_behaviors_to_test}
    assert "behavior_document_reading" in behavior_ids
    assert "behavior_source_grounding" in behavior_ids


def test_coding_agent_classification(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=["file_editor", "test_runner"])
    _write(
        tmp_path / "prompts" / "system.md",
        "Fix repository bugs. Inspect files before patching and return Markdown. Handle test failures.",
    )

    plan = _triage(tmp_path)

    assert plan.agent_classification.agent_type == "coding_agent"
    behavior_ids = {behavior.id for behavior in plan.key_behaviors_to_test}
    assert "behavior_minimal_patch" in behavior_ids
    assert "behavior_run_or_suggest_tests" in behavior_ids


def test_workflow_agent_classification_and_review_policy(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=["email_sender", "calendar_creator"])
    _write(tmp_path / "prompts" / "system.md", "Schedule meetings and send email summaries in Markdown.")

    plan = _triage(tmp_path)

    assert plan.agent_classification.agent_type == "workflow_agent"
    assert plan.risk_assessment.risk_level == "high"
    assert plan.risk_assessment.recommended_review_policy == "each-round"
    assert _has_missing(plan, "missing_human_approval_rule")


def test_tool_risk_detection_mappings() -> None:
    capabilities = classify_tools(
        [
            {"name": "document_reader", "description": "Read documents"},
            {"name": "file_writer", "description": "Write local files"},
            {"name": "shell", "description": "Run shell commands"},
            {"name": "email_sender", "description": "Send email"},
        ]
    )
    by_name = {tool.name: tool for tool in capabilities.tools}

    assert by_name["document_reader"].side_effect_level == "read_only"
    assert by_name["document_reader"].risk_level == "medium"
    assert by_name["file_writer"].side_effect_level == "write_local"
    assert by_name["file_writer"].risk_level == "high"
    assert by_name["shell"].risk_level == "high"
    assert by_name["email_sender"].side_effect_level == "external_write"
    assert by_name["email_sender"].risk_level == "high"


def test_missing_output_schema_and_error_handling(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=[])
    _write(tmp_path / "prompt.md", "You are helpful.")

    plan = _triage(tmp_path)

    assert _has_missing(plan, "missing_output_schema_or_format")
    assert _has_missing(plan, "missing_error_handling")


def test_missing_source_grounding_for_research_agent(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=["document_reader"])
    _write(tmp_path / "prompt.md", "Summarize academic papers in Markdown. Handle missing files.")

    plan = _triage(tmp_path, goal="paper reading agent")

    assert _has_missing(plan, "missing_source_grounding")


def test_missing_tool_call_order_for_multiple_tools(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=["document_reader", "markdown_writer"])
    _write(tmp_path / "prompt.md", "Summarize papers in Markdown. Handle missing files.")

    plan = _triage(tmp_path)

    assert _has_missing(plan, "missing_tool_call_order")


def test_eval_coverage_from_tags(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=["document_reader"])
    _write(tmp_path / "prompt.md", "Use Markdown. If missing, handle the error.")
    _write(
        tmp_path / "evals" / "basic.yaml",
        """
cases:
  - name: key path
    tags: [task_completion, tool_use]
    assertions: [contains_answer]
""",
    )

    plan = _triage(tmp_path)

    assert "task_completion" in plan.eval_coverage.covered_areas
    assert "tool_use" in plan.eval_coverage.covered_areas
    assert "error_handling" in plan.eval_coverage.missing_areas
    assert "safety" in plan.eval_coverage.missing_areas


def test_baseline_detection_and_missing_baseline(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=[])
    _write(tmp_path / "prompt.md", "Return Markdown. If input is invalid, ask for clarification.")

    missing = _triage(tmp_path)
    assert not missing.baseline_status.exists
    assert _has_missing(missing, "missing_baseline")

    _write(
        tmp_path / ".agentdoctor" / "baselines" / "latest.json",
        json.dumps({"created_at": "2026-05-03T21:00:00+00:00", "mode": "deep", "confidence": 0.82}),
    )
    found = _triage(tmp_path)
    assert found.baseline_status.exists
    assert found.baseline_status.mode == "deep"


def test_patch_preview_readiness(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=[])
    _write(tmp_path / "prompts" / "system.md", "Return Markdown. If invalid, ask for clarification.")

    ready = _triage(tmp_path)
    assert ready.patch_preview_readiness.eligible
    assert "prompts/system.md" in ready.patch_preview_readiness.allowed_files_detected

    empty = _triage(tmp_path / "empty")
    assert not empty.patch_preview_readiness.eligible
    assert "No safe patch target found." in empty.patch_preview_readiness.risk_notes


def test_auto_readiness_and_recommendation_rules(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=[])
    _write(tmp_path / "prompts" / "system.md", "Return Markdown. If invalid, ask for clarification.")
    _write(tmp_path / "evals" / "basic.yaml", "cases:\n  - name: key path\n    tags: [task_completion]\n")

    no_auto = _triage(tmp_path)
    assert no_auto.recommendation.recommended_mode != "auto"

    allow_auto = _triage(tmp_path, allow_auto=True)
    assert allow_auto.auto_readiness.eligible
    assert allow_auto.recommendation.recommended_mode == "auto"

    unsafe_root = tmp_path / "unsafe"
    _write_agent(unsafe_root / "agents" / "coder.yaml", tools=[])
    _write(unsafe_root / "evals" / "basic.yaml", "cases:\n  - name: key path\n")
    unsafe = _triage(unsafe_root, agent=Path("agents/coder.yaml"), allow_auto=True)
    assert not unsafe.auto_readiness.eligible
    assert unsafe.recommendation.recommended_mode != "auto"


def test_triage_auto_recommendation_uses_supported_auto_flags(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=[])
    _write(tmp_path / "prompts" / "system.md", "Return Markdown. If invalid, ask for clarification.")
    _write(tmp_path / "evals" / "basic.yaml", "cases:\n  - name: key path\n    tags: [task_completion]\n")

    plan = _triage(tmp_path, agent=Path("agent.yaml"), allow_auto=True)

    assert plan.recommendation.recommended_mode == "auto"
    assert "--preview-patches" not in plan.recommended_next_command
    assert "--target-confidence" in plan.recommended_next_command
    assert "--max-rounds" in plan.recommended_next_command
    assert "--review" in plan.recommended_next_command


def test_recommendation_rules_low_medium_high(tmp_path: Path) -> None:
    low_root = tmp_path / "low"
    _write_agent(low_root / "agent.yaml", tools=[])
    _write(low_root / "prompt.md", "Return Markdown. If invalid, ask for clarification.")
    _write(low_root / "evals" / "basic.yaml", "cases:\n  - name: key path\n")
    _write(low_root / ".agentdoctor" / "baselines" / "latest.json", "{}")
    low = _triage(low_root)
    assert low.recommendation.recommended_mode == "quick"
    assert low.recommendation.recommended_rounds == 1

    medium_root = tmp_path / "medium"
    _write_agent(medium_root / "agent.yaml", tools=["document_reader"])
    _write(medium_root / "prompt.md", "First read the document, then return Markdown. If missing, stop.")
    medium = _triage(medium_root)
    assert medium.recommendation.recommended_mode == "deep"
    assert medium.recommendation.recommended_rounds == 3
    assert medium.recommendation.suggested_review_policy == "on-fail"

    high_root = tmp_path / "high"
    _write_agent(high_root / "agent.yaml", tools=["shell"])
    _write(high_root / "prompt.md", "Return Markdown.")
    high = _triage(high_root)
    assert high.recommendation.recommended_mode == "deep"
    assert high.recommendation.recommended_rounds == 5
    assert high.recommendation.suggested_review_policy == "each-round"


def test_report_outputs_exist_and_contain_required_fields(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=[])

    plan = _triage(tmp_path)
    latest_md = tmp_path / ".agentdoctor" / "triage" / "latest.md"
    latest_json = tmp_path / ".agentdoctor" / "triage" / "latest.json"

    assert latest_md.exists()
    assert latest_json.exists()
    assert (tmp_path / ".agentdoctor" / "triage" / f"{plan.triage_id}.md").exists()
    assert (tmp_path / ".agentdoctor" / "triage" / f"{plan.triage_id}.json").exists()
    data = json.loads(latest_json.read_text(encoding="utf-8"))
    assert "agent_summary" in data
    assert "recommended_next_command" in data
    assert "Recommended Next Step" in latest_md.read_text(encoding="utf-8")


def test_secret_exclusion_does_not_read_env_contents(tmp_path: Path) -> None:
    _write_agent(tmp_path / "agent.yaml", tools=[])
    _write(tmp_path / ".env", "SECRET_VALUE=do-not-leak")

    plan = _triage(tmp_path)
    report = (tmp_path / ".agentdoctor" / "triage" / "latest.json").read_text(encoding="utf-8")

    assert "do-not-leak" not in report
    assert ".env" not in report


def _triage(
    root: Path,
    *,
    agent: Path | None = None,
    goal: str | None = None,
    allow_auto: bool = False,
):
    root.mkdir(parents=True, exist_ok=True)
    return run_triage(
        TriageOptions(
            project_root=root,
            agent=agent,
            goal=goal,
            allow_auto=allow_auto,
            now=NOW,
        )
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _write_agent(path: Path, name: str = "test_agent", tools: list[str] | None = None) -> None:
    tools = tools or []
    tool_lines = "\n".join(f"  - name: {tool}\n    description: {tool}" for tool in tools)
    _write(
        path,
        f"""
name: {name}
description: Test agent
tools:
{tool_lines if tool_lines else "  []"}
""",
    )


def _has_missing(plan, missing_id: str) -> bool:
    return any(item.id == missing_id for item in plan.missing_information)
