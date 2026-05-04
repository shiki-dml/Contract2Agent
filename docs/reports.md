# Reports

AgentDoctor writes local Markdown and JSON artifacts. Markdown reports are intended for human review. JSON reports are intended for automation, CI, and downstream tooling.

## Diagnostic Reports

Quick, deep, and auto write to `reports/` by default:

```text
reports/latest.md
reports/latest.json
reports/rounds/round_001.json
reports/patches/patch_001.diff
```

`reports/patches/` is populated when auto mode applies a safe patch and has a diff to record.

## Markdown Report Structure

Diagnostic Markdown reports include:

- title: `AgentDoctor Quick Diagnosis`, `AgentDoctor Deep Diagnosis`, or `AgentDoctor Auto Report`
- status
- confidence
- target confidence for auto
- rounds executed
- test counts
- review required flag
- heuristic confidence warning
- key findings
- failure taxonomy summary
- failure type changes
- review-required findings
- auto-fix eligible findings
- recommended next-round focus
- review items
- auto warnings and patch history for auto mode
- round summaries
- recommendations

## JSON Report Structure

Diagnostic JSON reports include:

- `mode`
- `status`
- `total_rounds_requested`
- `total_rounds_executed`
- `overall_confidence`
- `target_confidence`
- `pass_count`
- `fail_count`
- `warning_count`
- `review_required`
- `findings`
- `review_items`
- `rounds`
- `taxonomy_summary`
- `failure_type_counts`
- `failure_type_severity_counts`
- `review_required_findings`
- `auto_fix_eligible_findings`
- `patch_target_candidates`
- `recommended_next_round_tags`
- `baseline_comparison`
- `time_cost_summary`
- `persistent_failure_types`
- `new_failure_types`
- `resolved_failure_types`
- `critical_regressions`
- auto-only `patch_history`, `budget_summary`, `overfitting_warning`, and `efficiency_warning`

Round JSON files include test cases, traces, tool calls, final output, rule scores, findings, review items, confidence, timestamps, and per-test duration.

## Triage Reports

Triage writes:

```text
.agentdoctor/triage/latest.md
.agentdoctor/triage/latest.json
.agentdoctor/triage/triage_<timestamp>.md
.agentdoctor/triage/triage_<timestamp>.json
```

Triage reports include agent summary, input sources, detected capabilities, classification, risk assessment, eval coverage, key behaviors, missing information, warnings, suggested round plan, baseline status, patch preview readiness, auto readiness, estimated diagnostic cost, and recommended next command.

## Patch Preview Reports

Patch preview writes:

```text
.agentdoctor/patches/latest.md
.agentdoctor/patches/latest.json
.agentdoctor/patches/patch_<timestamp>_<index>.md
.agentdoctor/patches/patch_<timestamp>_<index>.json
.agentdoctor/patches/patch_<timestamp>_<index>.diff
```

Patch proposal reports include target failure types, related findings, reason, proposed files, diff, expected effect, validation plan, baseline impact, regression risks, risk and approval, rollback plan, rollback conditions, and reviewer notes.

## Baseline Reports

Baselines write:

```text
.agentdoctor/baselines/latest.json
.agentdoctor/baselines/baseline_<timestamp>/baseline.json
.agentdoctor/baselines/baseline_<timestamp>/snapshot.json
.agentdoctor/baselines/baseline_<timestamp>/file_hashes.json
.agentdoctor/baselines/baseline_<timestamp>/baseline_saved.md
.agentdoctor/baselines/baseline_<timestamp>/comparison_latest.json
.agentdoctor/baselines/baseline_<timestamp>/comparison_latest.md
```

Use `comparison_latest.md` to review regressions, improvements, failure type changes, snapshot diffs, and rollback recommendations.

## Time-Cost Reports

Cost estimate writes:

```text
.agentdoctor/cost/latest.md
.agentdoctor/cost/latest.json
.agentdoctor/cost/cost_<timestamp>.md
.agentdoctor/cost/cost_<timestamp>.json
```

These reports are static estimates, not measured runtime. Measured timing is in diagnostic JSON reports.

## Trace Diagnosis Reports

The original contract/trace workflow can write:

```text
demo_project/reports/counterexample_report.md
demo_project/reports/diagnosis_report.md
demo_project/reports/diagnosis_report.yaml
```

Use these when working directly with `AgentContract` and saved trace JSON files.

## Recommendations

Read reports in this order:

1. `reports/latest.md` for the human summary.
2. `reports/latest.json` for machine-readable findings and taxonomy.
3. `reports/rounds/*.json` for trace/tool-call details.
4. `.agentdoctor/baselines/*/comparison_latest.md` for regression context.
5. `.agentdoctor/patches/latest.md` for patch review.
6. `.agentdoctor/cost/latest.md` for estimate and guardrail context.
