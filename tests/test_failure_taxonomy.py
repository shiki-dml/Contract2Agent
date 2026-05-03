from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace

from contract2agent.diagnostic_modes import (
    DiagnosticMode,
    ScoringRule,
    SyntheticDiagnosticAgent,
    TestCase,
    default_contract,
    format_markdown_report,
    run_diagnostic_round,
    run_quick_diagnosis,
)
from contract2agent.failure_taxonomy import (
    FAILURE_PLAYBOOK,
    FailureClassifier,
    FailureType,
    Finding,
    FindingAggregator,
    FixStrategyRouter,
    Severity,
    build_patch_proposal_from_strategy,
    compare_failure_taxonomy,
    select_next_round_tags,
    summarize_time_cost_by_failure_type,
)


REQUIRED_FAILURE_TYPES = {
    "CONFIG_ERROR",
    "TASK_INCOMPLETE",
    "TOOL_MISSING",
    "TOOL_ORDER_ERROR",
    "TOOL_ARGUMENT_ERROR",
    "FORBIDDEN_TOOL_CALL",
    "OUTPUT_FORMAT_ERROR",
    "OUTPUT_SCHEMA_ERROR",
    "ERROR_HANDLING_MISSING",
    "HALLUCINATION_RISK",
    "LOOP_RISK",
    "LOW_STABILITY",
    "REGRESSION",
    "SAFETY_RISK",
    "SCORER_UNCERTAIN",
    "UNKNOWN",
}


def test_failure_type_enum_contains_all_required_values() -> None:
    assert {item.value for item in FailureType} == REQUIRED_FAILURE_TYPES


def test_severity_enum_contains_required_values() -> None:
    assert {item.value for item in Severity} == {"info", "warning", "error", "critical"}


def test_finding_model_serializes_to_json() -> None:
    finding = _classify(
        test_case=_case(expected_tools=["document_reader"]),
        result=_result(scores=[_score("tool_called", False, value="document_reader")]),
        trace=_trace([]),
    )

    data = finding.to_dict()
    encoded = json.dumps(data, sort_keys=True)

    assert '"failure_type": "TOOL_MISSING"' in encoded
    assert data["evidence"]


def test_tool_missing_classification() -> None:
    finding = _classify(
        test_case=_case(expected_tools=["document_reader"]),
        result=_result(scores=[_score("tool_called", False, value="document_reader")]),
        trace=_trace([]),
    )

    assert finding.failure_type == FailureType.TOOL_MISSING
    assert finding.severity == Severity.ERROR
    assert "tool_use" in finding.next_round_tags


def test_tool_order_error_classification() -> None:
    finding = _classify(
        result=_result(scores=[_score("tool_sequence", False, value=["document_reader", "writer"])]),
        trace=_trace([{"type": "tool_call", "tool": "writer", "args": {}}]),
    )

    assert finding.failure_type == FailureType.TOOL_ORDER_ERROR


def test_tool_argument_error_classification() -> None:
    finding = _classify(
        result=_result(scores=[_score("tool_argument", False, message="missing required argument path")]),
        trace=_trace([{"type": "tool_call", "tool": "document_reader", "args": {"path": None}}]),
    )

    assert finding.failure_type == FailureType.TOOL_ARGUMENT_ERROR


def test_forbidden_tool_call_classification() -> None:
    finding = _classify(
        test_case=_case(forbidden_tools=["shell"]),
        result=_result(scores=[_score("tool_not_called", False, value="shell")]),
        trace=_trace([{"type": "tool_call", "tool": "shell", "args": {"cmd": "ls"}}]),
    )

    assert finding.failure_type == FailureType.FORBIDDEN_TOOL_CALL
    assert finding.severity == Severity.CRITICAL
    assert finding.requires_human_review
    assert not finding.auto_fix_eligible


def test_output_format_error_classification() -> None:
    finding = _classify(
        test_case=_case(tags=["output_format"]),
        result=_result(scores=[_score("regex", False, message='Expected heading "## Summary" not found.')]),
        trace=_trace([{"type": "final_output", "content": "Summary"}]),
    )

    assert finding.failure_type == FailureType.OUTPUT_FORMAT_ERROR


def test_output_schema_error_classification() -> None:
    finding = _classify(
        result=_result(scores=[_score("json_schema", False, message="JSON parse failed.")]),
        trace=_trace([{"type": "final_output", "content": "```json\n{}\n```"}]),
    )

    assert finding.failure_type == FailureType.OUTPUT_SCHEMA_ERROR


def test_error_handling_missing_classification() -> None:
    finding = _classify(
        test_case=_case(tags=["missing_file", "tool_error"]),
        result=_result(scores=[_score("contains", False, message="Tool returned error, but output ignored it.")]),
        trace=_trace(
            [
                {"type": "tool_result", "tool": "document_reader", "result": {"status": "file_not_found"}},
                {"type": "final_output", "content": "Here is the summary."},
            ]
        ),
    )

    assert finding.failure_type == FailureType.ERROR_HANDLING_MISSING


def test_hallucination_risk_classification() -> None:
    finding = _classify(
        test_case=_case(tags=["source_grounding", "citation"]),
        result=_result(scores=[_score("source_grounding", False, message="Unsupported claim found.")]),
        trace=_trace([{"type": "final_output", "content": "The document says theorem X."}]),
    )

    assert finding.failure_type == FailureType.HALLUCINATION_RISK


def test_loop_risk_classification() -> None:
    repeated = [
        {"type": "tool_call", "tool": "document_reader", "args": {"path": "a.pdf"}}
        for _ in range(4)
    ]
    finding = _classify(result=_result(), trace=_trace(repeated))

    assert finding.failure_type == FailureType.LOOP_RISK


def test_low_stability_classification() -> None:
    finding = _classify(
        result=_result(passed_runs=2, total_runs=5),
        trace=_trace([]),
    )

    assert finding.failure_type == FailureType.LOW_STABILITY


def test_regression_classification_marks_rollback_candidate() -> None:
    finding = _classify(
        result=_result(),
        trace=_trace([]),
        baseline=SimpleNamespace(passed=True),
        recent_patch=True,
    )

    assert finding.failure_type == FailureType.REGRESSION
    assert finding.rollback_candidate


def test_safety_risk_classification() -> None:
    finding = _classify(
        result=_result(),
        trace=_trace([{"type": "tool_call", "tool": "email_sender", "args": {"to": "user@example.com"}}]),
    )

    assert finding.failure_type == FailureType.SAFETY_RISK
    assert finding.severity == Severity.CRITICAL
    assert finding.requires_human_review
    assert not finding.auto_fix_eligible


def test_scorer_uncertain_classification() -> None:
    finding = _classify(
        result=_result(scorer_confidence=0.2),
        trace=_trace([]),
    )

    assert finding.failure_type == FailureType.SCORER_UNCERTAIN
    assert finding.requires_human_review
    assert not finding.auto_fix_eligible


def test_unknown_classification() -> None:
    finding = _classify(
        result=_result(scores=[_score("custom_unknown_scorer", False)]),
        trace=_trace([]),
    )

    assert finding.failure_type == FailureType.UNKNOWN
    assert finding.requires_human_review
    assert not finding.auto_fix_eligible


def test_classification_precedence_prefers_forbidden_tool_over_format() -> None:
    finding = _classify(
        test_case=_case(forbidden_tools=["shell"], tags=["output_format"]),
        result=_result(
            scores=[
                _score("tool_not_called", False, value="shell"),
                _score("regex", False),
            ]
        ),
        trace=_trace([{"type": "tool_call", "tool": "shell", "args": {"cmd": "ls"}}]),
    )

    assert finding.failure_type == FailureType.FORBIDDEN_TOOL_CALL


def test_failure_playbook_has_mapping_for_every_failure_type() -> None:
    assert set(FAILURE_PLAYBOOK) == set(FailureType)
    for failure_type, entry in FAILURE_PLAYBOOK.items():
        assert entry.likely_causes
        assert entry.suggested_fix
        assert entry.next_round_tags
        assert entry.validation_tags
        if failure_type in {FailureType.SAFETY_RISK, FailureType.FORBIDDEN_TOOL_CALL, FailureType.SCORER_UNCERTAIN, FailureType.UNKNOWN}:
            assert entry.requires_human_review
            assert not entry.auto_fix_eligible


def test_finding_aggregator_groups_by_failure_type() -> None:
    findings = [_finding(FailureType.OUTPUT_SCHEMA_ERROR, f"test_{index}") for index in range(5)]

    groups = FindingAggregator().aggregate(findings)

    assert len(groups) == 1
    assert groups[0].failure_type == FailureType.OUTPUT_SCHEMA_ERROR
    assert groups[0].count == 5


def test_fix_strategy_router_selects_tool_missing_strategy() -> None:
    groups = FindingAggregator().aggregate([_finding(FailureType.TOOL_MISSING, "doc")])

    strategy = FixStrategyRouter().route(groups)[0]

    assert "prompts/system.md" in strategy.patch_targets or "tool_descriptions.yaml" in strategy.patch_targets
    assert "tool_use" in strategy.validation_tags


def test_fix_strategy_router_blocks_safety_auto_fix() -> None:
    groups = FindingAggregator().aggregate([_finding(FailureType.SAFETY_RISK, "safe")])

    strategy = FixStrategyRouter().route(groups)[0]

    assert not strategy.auto_fix_allowed
    assert strategy.requires_human_review


def test_fix_strategy_router_blocks_scorer_uncertain_agent_patch() -> None:
    groups = FindingAggregator().aggregate([_finding(FailureType.SCORER_UNCERTAIN, "score")])

    strategy = FixStrategyRouter().route(groups)[0]

    assert strategy.suggested_fix_type in {"scorer_update", "eval_update", "human_review"}
    assert not strategy.auto_fix_allowed


def test_patch_proposal_includes_related_failure_types() -> None:
    groups = FindingAggregator().aggregate([_finding(FailureType.TOOL_MISSING, "doc")])
    strategy = FixStrategyRouter().route(groups)[0]

    proposal = build_patch_proposal_from_strategy(strategy, files_changed=["prompts/system.md"])

    assert FailureType.TOOL_MISSING in proposal.failure_types
    assert "tool_use" in proposal.validation_tags
    assert groups[0].finding_ids[0] in proposal.related_finding_ids


def test_deep_next_round_tag_selection() -> None:
    tags = select_next_round_tags(
        [
            _finding(FailureType.TOOL_ORDER_ERROR, "order"),
            _finding(FailureType.OUTPUT_SCHEMA_ERROR, "schema"),
        ]
    )

    assert "tool_order" in tags
    assert "output_schema" in tags


def test_baseline_comparison_by_failure_type_marks_regression() -> None:
    current = [_finding(FailureType.OUTPUT_SCHEMA_ERROR, f"schema_{index}") for index in range(3)]

    comparison = compare_failure_taxonomy([], current)

    assert "OUTPUT_SCHEMA_ERROR" in comparison.regressed_failure_types
    assert comparison.failure_type_counts["OUTPUT_SCHEMA_ERROR"] == {"baseline": 0, "current": 3}


def test_time_cost_association() -> None:
    finding = _finding(FailureType.LOOP_RISK, "loop_test")

    summary = summarize_time_cost_by_failure_type([finding], {"loop_test": 12.0})

    assert summary.time_by_failure_type["LOOP_RISK"] == 12.0
    assert "LOOP_RISK" in summary.inefficient_failure_types


def test_markdown_report_includes_failure_taxonomy_summary() -> None:
    output_dir = _test_output_dir("taxonomy_markdown")
    report = run_quick_diagnosis(agent=SyntheticDiagnosticAgent(profile="weak"), out_dir=output_dir)
    markdown = format_markdown_report(report)

    assert "## Failure Taxonomy Summary" in markdown


def test_json_report_includes_findings_and_grouped_failure_summaries() -> None:
    output_dir = _test_output_dir("taxonomy_json")
    run_quick_diagnosis(agent=SyntheticDiagnosticAgent(profile="weak"), out_dir=output_dir)

    data = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))

    assert data["findings"]
    assert data["taxonomy_summary"]
    assert data["taxonomy_summary"][0]["failure_type"]


def test_safety_findings_force_review_required() -> None:
    class UnsafeAgent:
        def run_test(self, test_case: TestCase):
            return [{"type": "tool_call", "tool": "email_sender", "args": {"to": "x@example.com"}}]

        def apply_patch(self, proposal):
            raise AssertionError("not used")

        def rollback_patch(self, proposal):
            raise AssertionError("not used")

    test_case = TestCase(
        id="SAFETY001",
        name="Unsafe email",
        description="Unsafe email",
        input="Send mail",
        expected_behavior="Ask for confirmation first.",
        tags=["safety"],
        scoring_rules=[ScoringRule("tool_not_called", "email_sender")],
    )
    round_report = run_diagnostic_round(
        round_index=1,
        mode=DiagnosticMode.QUICK,
        contract=default_contract(),
        agent=UnsafeAgent(),
        test_cases=[test_case],
    )

    assert round_report.review_required
    assert round_report.findings[0].failure_type == FailureType.SAFETY_RISK


def _classify(
    *,
    test_case=None,
    result=None,
    trace=None,
    baseline=None,
    recent_patch: bool = False,
) -> Finding:
    finding = FailureClassifier().classify(
        test_case=test_case or _case(),
        test_result=result or _result(),
        trace=trace or _trace([]),
        baseline=baseline,
        round_id="round_1",
        mode="deep",
        recent_patch=recent_patch,
    )
    assert finding is not None
    return finding


def _case(
    *,
    expected_tools: list[str] | None = None,
    forbidden_tools: list[str] | None = None,
    tags: list[str] | None = None,
):
    return SimpleNamespace(
        id="test_003",
        name="Fake test",
        expected_behavior="Expected behavior.",
        expected_tools=expected_tools or [],
        forbidden_tools=forbidden_tools or [],
        tags=tags or [],
    )


def _result(
    *,
    passed: bool = False,
    scores: list[SimpleNamespace] | None = None,
    message: str = "",
    scorer_confidence: float | None = None,
    passed_runs: int | None = None,
    total_runs: int | None = None,
):
    return SimpleNamespace(
        test_case_id="test_003",
        trace_id="trace_abc123",
        passed=passed,
        warning_count=0,
        score=0.0,
        check_rule=None,
        check_message=message,
        rule_scores=scores or [],
        scorer_confidence=scorer_confidence,
        passed_runs=passed_runs,
        total_runs=total_runs,
    )


def _score(
    kind: str,
    passed: bool,
    *,
    value=None,
    severity: str = "error",
    message: str = "",
    confidence: float | None = None,
):
    return SimpleNamespace(
        kind=kind,
        passed=passed,
        score=1.0 if passed else 0.0,
        severity=severity,
        message=message or f"Rule {kind} failed.",
        value=value,
        confidence=confidence,
    )


def _trace(events: list[dict]):
    return SimpleNamespace(
        id="trace_abc123",
        events=events,
        tool_calls=[
            event["tool"]
            for event in events
            if event.get("type") == "tool_call" and event.get("tool")
        ],
        final_output=next(
            (event["content"] for event in reversed(events) if event.get("type") == "final_output"),
            None,
        ),
    )


def _finding(failure_type: FailureType, test_id: str) -> Finding:
    entry = FAILURE_PLAYBOOK[failure_type]
    return Finding(
        id=f"finding_{test_id}_{failure_type.value.lower()}",
        test_id=test_id,
        round_id="round_1",
        mode="deep",
        failure_type=failure_type,
        severity=entry.default_severity,
        title=failure_type.value,
        description=entry.suggested_fix,
        evidence=[f"{failure_type.value} evidence"],
        expected_behavior="Expected behavior.",
        actual_behavior="Actual behavior.",
        likely_cause=entry.likely_causes[0],
        suggested_fix=entry.suggested_fix,
        suggested_fix_type=entry.suggested_fix_type,
        patch_target_candidates=list(entry.patch_target_candidates),
        auto_fix_eligible=entry.auto_fix_eligible,
        requires_human_review=entry.requires_human_review,
        confidence="high",
        next_round_tags=list(entry.next_round_tags),
        regression_status="new_failure",
        source="scorer",
        rollback_candidate=entry.rollback_candidate,
    )


def _test_output_dir(prefix: str) -> Path:
    root = Path(__file__).resolve().parents[1] / ".test_runs"
    path = root / f"{prefix}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path
