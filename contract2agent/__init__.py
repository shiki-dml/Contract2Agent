"""AgentTraceDoctor compatibility package for offline agent trace diagnosis."""

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
    "ReviewItem",
    "ReviewPolicy",
    "TestCase",
    "build_rule_coverage_matrix",
    "capability_to_eval_case",
    "compute_diagnostic_confidence",
    "diagnose_evaluation",
    "explain_trace_result",
    "generate_capability_report",
    "generate_counterexamples",
    "generate_regression_trace_for_issue",
    "run_auto_diagnosis",
    "run_deep_diagnosis",
    "run_quick_diagnosis",
    "suggest_minimal_patch",
    "write_regression_traces",
]

__version__ = "0.1.0"
