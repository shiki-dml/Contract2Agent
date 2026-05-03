from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from contract2agent.patch_preview import PatchPreviewOptions, run_patch_preview
from contract2agent.patch_preview.models import PatchProposal, to_plain_data


NOW = datetime(2026, 5, 3, 22, 0, 0, tzinfo=timezone.utc)


def test_patch_proposal_model_serializes_to_json() -> None:
    proposal = PatchProposal(
        patch_id="patch_20260503_001",
        created_at=NOW.isoformat(),
        source_run_id="run_001",
        source_round_id="round_001",
        related_finding_ids=["finding_001"],
        failure_types=["OUTPUT_SCHEMA_ERROR"],
        grouped_failure_summary="One schema finding.",
        reason="The agent emitted Markdown fences around JSON.",
        patch_type="prompt_update",
        strategy_id="fix_output_schema_strict_json",
        target_files=["prompt.md"],
        files_changed=["prompt.md"],
        diff="--- prompt.md\n+++ prompt.md\n",
        before_summary="Missing JSON-only rule.",
        after_summary="Adds JSON-only rule.",
        expected_effect=["Schema failures decrease."],
        validation_tags=["output_schema", "regression"],
        validation_command="agentdoctor deep --rounds 2 --review on-fail",
        regression_risks=["May reduce task completeness."],
        baseline_impact={"baseline_exists": False},
        risk_level="medium",
        requires_approval=True,
        auto_apply_eligible=True,
        do_not_apply_automatically=True,
        rollback_available=False,
        rollback_plan="Revert the diff.",
        reviewer_notes=[],
    )

    data = json.dumps(to_plain_data(proposal))
    assert "fix_output_schema_strict_json" in data


def test_patch_preview_cli_command_exists() -> None:
    root = _project("cli")
    _write(root / "prompt.md", "You are helpful.")
    run_path = _write_run(
        root,
        [{"id": "f1", "failure_type": "OUTPUT_SCHEMA_ERROR", "description": "Invalid JSON."}],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "patch-preview",
            "--from-run",
            str(run_path),
            "--project-root",
            str(root),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "AgentDoctor Patch Preview" in completed.stdout
    assert (root / ".agentdoctor" / "patches" / "latest.md").exists()


def test_empty_findings_do_not_crash() -> None:
    root = _project("empty")
    run_path = _write_run(root, [])

    report = _preview(root, run_path)

    assert report.proposals == []
    assert any("No findings" in item for item in report.skipped_items)
    assert (root / ".agentdoctor" / "patches" / "latest.json").exists()


def test_output_schema_error_generates_prompt_patch() -> None:
    root = _project("schema")
    _write(root / "prompt.md", "Return the answer.")
    run_path = _write_run(
        root,
        [
            {
                "id": "schema_1",
                "failure_type": "OUTPUT_SCHEMA_ERROR",
                "description": "The agent produced invalid JSON in output_schema tests.",
            }
        ],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert proposal.patch_type == "prompt_update"
    assert proposal.files_changed == ["prompt.md"]
    assert "Return only valid JSON" in proposal.diff
    assert "output_schema" in proposal.validation_tags
    assert "regression" in proposal.validation_tags


def test_output_format_error_generates_template_patch() -> None:
    root = _project("format")
    _write(root / "prompt.md", "Answer clearly.")
    run_path = _write_run(
        root,
        [{"id": "format_1", "failure_type": "OUTPUT_FORMAT_ERROR", "description": "Missing Markdown sections."}],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert "Use the required output format exactly." in proposal.diff
    assert "output_format" in proposal.validation_tags
    assert proposal.risk_level in {"low", "medium"}


def test_tool_missing_read_only_tool_generates_trigger_patch() -> None:
    root = _project("tool_read")
    _write(root / "prompt.md", "Summarize documents.")
    run_path = _write_run(
        root,
        [
            {
                "id": "tool_1",
                "failure_type": "TOOL_MISSING",
                "tool": "document_reader",
                "description": "document_reader was not called before answering.",
            }
        ],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert "document_reader" in proposal.diff
    assert proposal.auto_apply_eligible
    assert "tool_use" in proposal.validation_tags


def test_tool_missing_side_effect_tool_requires_approval() -> None:
    root = _project("tool_side_effect")
    _write(root / "prompt.md", "Send updates.")
    run_path = _write_run(
        root,
        [
            {
                "id": "tool_1",
                "failure_type": "TOOL_MISSING",
                "tool": "email_sender",
                "description": "email_sender was not called.",
            }
        ],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert proposal.requires_approval
    assert not proposal.auto_apply_eligible
    assert proposal.risk_level in {"high", "critical"}


def test_hallucination_risk_generates_source_grounding_patch() -> None:
    root = _project("hallucination")
    _write(root / "prompt.md", "Answer from documents.")
    run_path = _write_run(
        root,
        [{"id": "h1", "failure_type": "HALLUCINATION_RISK", "description": "The answer guessed facts without evidence."}],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert "base all factual claims" in proposal.diff
    assert "source_grounding" in proposal.validation_tags
    assert "hallucination" in proposal.validation_tags


def test_safety_risk_requires_approval_and_never_auto_applies() -> None:
    root = _project("safety")
    _write(root / "prompt.md", "Use tools.")
    run_path = _write_run(
        root,
        [{"id": "s1", "failure_type": "SAFETY_RISK", "description": "Unsafe external write without approval."}],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert proposal.risk_level == "critical"
    assert proposal.requires_approval
    assert not proposal.auto_apply_eligible
    assert proposal.do_not_apply_automatically


def test_forbidden_tool_call_never_auto_applies() -> None:
    root = _project("forbidden")
    _write(root / "prompt.md", "Do work.")
    run_path = _write_run(
        root,
        [{"id": "f1", "failure_type": "FORBIDDEN_TOOL_CALL", "tool": "shell", "description": "Forbidden shell call."}],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert proposal.risk_level == "critical"
    assert proposal.requires_approval
    assert not proposal.auto_apply_eligible
    assert "safety" in proposal.validation_tags
    assert "forbidden_tool_call" in proposal.validation_tags


def test_scorer_uncertain_does_not_patch_agent() -> None:
    root = _project("scorer")
    _write(root / "prompt.md", "Answer.")
    run_path = _write_run(
        root,
        [{"id": "sc1", "failure_type": "SCORER_UNCERTAIN", "description": "Scorer could not decide."}],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert proposal.patch_type == "no_agent_patch_review_only"
    assert proposal.diff == ""
    assert proposal.requires_approval


def test_unknown_does_not_patch_agent() -> None:
    root = _project("unknown")
    _write(root / "prompt.md", "Answer.")
    run_path = _write_run(
        root,
        [{"id": "u1", "failure_type": "UNKNOWN", "description": "Insufficient evidence."}],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert proposal.patch_type == "no_agent_patch_review_only"
    assert proposal.diff == ""


def test_regression_prefers_rollback_when_previous_patch_metadata_exists() -> None:
    root = _project("regression_with_patch")
    _write(root / "prompt.md", "Answer.")
    run_path = _write_run(
        root,
        [{"id": "r1", "failure_type": "REGRESSION", "description": "New regression after patch."}],
        extra={"patch_history": [{"files_changed": ["prompt.md"], "diff": "--- prompt.md\n"}]},
    )

    proposal = _preview(root, run_path).proposals[0]

    assert proposal.patch_type == "rollback_patch"
    assert proposal.rollback_available


def test_regression_without_metadata_is_review_only() -> None:
    root = _project("regression_no_patch")
    _write(root / "prompt.md", "Answer.")
    run_path = _write_run(
        root,
        [{"id": "r1", "failure_type": "REGRESSION", "description": "New regression after patch."}],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert proposal.patch_type == "no_agent_patch_review_only"
    assert not proposal.rollback_available


def test_denied_path_protection_never_leaks_secret_contents() -> None:
    root = _project("denied")
    _write(root / "prompt.md", "Answer.")
    _write(root / ".env", "SECRET_TOKEN=do-not-leak")
    run_path = _write_run(
        root,
        [
            {
                "id": "d1",
                "failure_type": "OUTPUT_SCHEMA_ERROR",
                "target_file": ".env",
                "description": "Bad config SECRET_TOKEN=do-not-leak",
            }
        ],
    )

    report = _preview(root, run_path)
    proposal = report.proposals[0]
    latest = (root / ".agentdoctor" / "patches" / "latest.json").read_text(encoding="utf-8")

    assert proposal.diff == ""
    assert proposal.patch_type == "no_agent_patch_review_only"
    assert "do-not-leak" not in latest


def test_allowlist_enforcement_creates_review_only_item() -> None:
    root = _project("allowlist")
    _write(root / "prompt.md", "Answer.")
    _write(root / "src" / "agent.py", "print('agent')\n")
    run_path = _write_run(
        root,
        [
            {
                "id": "a1",
                "failure_type": "OUTPUT_SCHEMA_ERROR",
                "target_file": "src/agent.py",
                "description": "Invalid JSON.",
            }
        ],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert proposal.diff == ""
    assert proposal.patch_type == "no_agent_patch_review_only"
    assert any("outside the patch allowlist" in note for note in proposal.reviewer_notes)


def test_baseline_impact_is_populated_when_baseline_exists() -> None:
    root = _project("baseline")
    _write(root / "prompt.md", "Answer.")
    _write(
        root / ".agentdoctor" / "baselines" / "latest.json",
        json.dumps(
            {
                "run_id": "baseline",
                "findings": [
                    {"id": "b1", "failure_type": "OUTPUT_SCHEMA_ERROR", "description": "Old schema fail."}
                ],
            }
        ),
    )
    run_path = _write_run(
        root,
        [{"id": "s1", "failure_type": "OUTPUT_SCHEMA_ERROR", "description": "Current schema fail."}],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert proposal.baseline_impact["baseline_exists"] is True
    assert proposal.baseline_impact["target_failure_type_in_baseline"]["OUTPUT_SCHEMA_ERROR"] == 1
    assert proposal.baseline_impact["recommended_regression_checks"]


def test_missing_baseline_does_not_crash() -> None:
    root = _project("no_baseline")
    _write(root / "prompt.md", "Answer.")
    run_path = _write_run(
        root,
        [{"id": "s1", "failure_type": "OUTPUT_SCHEMA_ERROR", "description": "Current schema fail."}],
    )

    proposal = _preview(root, run_path).proposals[0]

    assert proposal.baseline_impact["baseline_exists"] is False
    assert "No baseline found" in proposal.baseline_impact["warning"]


def test_finding_aggregation_groups_same_failure_type_and_cause() -> None:
    root = _project("aggregation")
    _write(root / "prompt.md", "Answer.")
    findings = [
        {"id": f"s{index}", "failure_type": "OUTPUT_SCHEMA_ERROR", "description": "Invalid JSON."}
        for index in range(5)
    ]
    run_path = _write_run(root, findings)

    report = _preview(root, run_path)

    assert len(report.proposals) == 1
    assert len(report.proposals[0].related_finding_ids) == 5


def test_compatible_merge_for_tool_missing_and_hallucination() -> None:
    root = _project("merge")
    _write(root / "prompt.md", "Answer from documents.")
    run_path = _write_run(
        root,
        [
            {
                "id": "m1",
                "failure_type": "TOOL_MISSING",
                "tool": "document_reader",
                "description": "document_reader was missing.",
            },
            {
                "id": "m2",
                "failure_type": "HALLUCINATION_RISK",
                "tool": "document_reader",
                "description": "Answer was not grounded in document evidence.",
            },
        ],
    )

    report = _preview(root, run_path)
    proposal = report.proposals[0]

    assert len(report.proposals) == 1
    assert proposal.failure_types == ["HALLUCINATION_RISK", "TOOL_MISSING"]
    assert "tool_use" in proposal.validation_tags
    assert "source_grounding" in proposal.validation_tags


def test_report_outputs_include_latest_json_markdown_and_diff() -> None:
    root = _project("report_outputs")
    _write(root / "prompt.md", "Answer.")
    run_path = _write_run(
        root,
        [{"id": "s1", "failure_type": "OUTPUT_SCHEMA_ERROR", "description": "Invalid JSON."}],
    )

    report = _preview(root, run_path)
    proposal = report.proposals[0]
    latest_md = root / ".agentdoctor" / "patches" / "latest.md"
    latest_json = root / ".agentdoctor" / "patches" / "latest.json"
    diff_path = root / ".agentdoctor" / "patches" / f"{proposal.patch_id}.diff"

    assert latest_md.exists()
    assert latest_json.exists()
    assert diff_path.exists()
    markdown = latest_md.read_text(encoding="utf-8")
    assert "Target Failure Types" in markdown
    assert "#### Reason" in markdown
    assert "#### Diff" in markdown
    assert "Validation Plan" in markdown
    assert "Risk and Approval" in markdown


def _preview(root: Path, run_path: Path):
    return run_patch_preview(
        PatchPreviewOptions(
            project_root=root,
            from_run=run_path,
            now=NOW,
        )
    )


def _write_run(root: Path, findings: list[dict], extra: dict | None = None) -> Path:
    data = {"run_id": "run_001", "findings": findings}
    if extra:
        data.update(extra)
    path = root / ".agentdoctor" / "runs" / "latest.json"
    _write(path, json.dumps(data))
    return path


def _project(prefix: str) -> Path:
    root = Path(__file__).resolve().parents[1] / ".test_runs" / "patch_preview"
    path = root / f"{prefix}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
