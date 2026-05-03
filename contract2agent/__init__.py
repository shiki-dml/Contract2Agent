"""AgentTraceDoctor compatibility package for offline agent trace diagnosis."""

__version__ = "0.1.0"

from contract2agent.capabilities import (
    CapabilityReport,
    CapabilitySpec,
    capability_to_eval_case,
    generate_capability_report,
)
from contract2agent.counterexamples import CounterexampleCase, generate_counterexamples
from contract2agent.diagnostic_modes import (
    DiagnosticMode,
    DiagnosticReport as AgentDiagnosticReport,
    DiagnosticRound,
    ReviewItem,
    ReviewPolicy,
    TestCase,
    compute_diagnostic_confidence,
    run_auto_diagnosis,
    run_deep_diagnosis,
    run_quick_diagnosis,
)
from contract2agent.baseline import (
    AgentStateSnapshot,
    BaselineComparison,
    BaselineRecord,
    build_patch_preview_baseline_context,
    build_rollback_recommendation,
    compare_against_baseline,
    detect_baseline_status,
    save_baseline,
)
from contract2agent.diagnosis import (
    DiagnosisIssue,
    DiagnosisReport,
    build_rule_coverage_matrix,
    diagnose_evaluation,
    explain_trace_result,
    generate_regression_trace_for_issue,
    suggest_minimal_patch,
    write_regression_traces,
)
from contract2agent.schema import AgentContract, ForbiddenCapabilitySpec

__all__ = [
    "AgentContract",
    "CapabilityReport",
    "CapabilitySpec",
    "CounterexampleCase",
    "DiagnosisIssue",
    "DiagnosisReport",
    "DiagnosticMode",
    "DiagnosticRound",
    "ForbiddenCapabilitySpec",
    "AgentDiagnosticReport",
    "AgentStateSnapshot",
    "BaselineComparison",
    "BaselineRecord",
    "build_patch_preview_baseline_context",
    "ReviewItem",
    "ReviewPolicy",
    "TestCase",
    "build_rule_coverage_matrix",
    "build_rollback_recommendation",
    "capability_to_eval_case",
    "compute_diagnostic_confidence",
    "compare_against_baseline",
    "detect_baseline_status",
    "diagnose_evaluation",
    "explain_trace_result",
    "generate_capability_report",
    "generate_counterexamples",
    "generate_regression_trace_for_issue",
    "run_auto_diagnosis",
    "run_deep_diagnosis",
    "run_quick_diagnosis",
    "save_baseline",
    "suggest_minimal_patch",
    "write_regression_traces",
]
