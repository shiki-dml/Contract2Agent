# Time Cost

AgentDoctor has two time-cost surfaces:

1. Measured diagnostic timing inside quick, deep, and auto reports.
2. Static pre-run estimates from `agentdoctor cost-estimate`.

Measured timing tells you how long current tests took. Static estimates help decide whether to run quick, deep, or auto before spending runtime and review effort.

## Measured Diagnostic Timing

Diagnostic JSON reports can include:

- per-test `duration_seconds`
- per-round start and finish timestamps
- report-level `time_cost_summary`
- slow or repeated failure types
- auto-mode `budget_summary.elapsed_seconds`
- auto-mode `max_rounds`, `max_time_minutes`, and `max_patches`
- holdout confidence when available
- efficiency warnings

Round files live under:

```text
reports/rounds/round_001.json
reports/rounds/round_002.json
```

Auto patch diffs live under:

```text
reports/patches/patch_001.diff
```

## Static Cost Estimate

`agentdoctor cost-estimate` performs a rough static estimate. It does not run tests, call the agent, call tools, call LLM APIs, or measure actual runtime.

```bash
agentdoctor cost-estimate --from-triage .agentdoctor/triage/latest.json
agentdoctor cost-estimate --mode deep --budget balanced
agentdoctor cost-estimate --mode auto --max-auto-iterations 4
agentdoctor cost-estimate --budget conservative --max-rounds 2 --max-tests 12
```

Reports are written to:

```text
.agentdoctor/cost/latest.md
.agentdoctor/cost/latest.json
.agentdoctor/cost/cost_<timestamp>.md
.agentdoctor/cost/cost_<timestamp>.json
```

## Runtime Fields

Time-cost reports and estimates can include:

- total elapsed time
- per-round runtime
- per-test runtime
- average test time
- slowest tests
- patch generation or patch application context when available
- report generation context
- runtime budget
- budget used percentage when enough data exists
- human review burden
- estimated test count
- estimated tool calls
- estimated LLM calls
- budget guardrails
- efficiency warnings

## Slowest Tests

Measured reports store durations per test id. Cost summaries can associate slow tests with failure types, for example:

```text
Slowest tests:
1. ambiguous_document_summary: 71.2s
2. missing_file_recovery: 54.8s
3. markdown_schema_validation: 43.1s
```

Slow tests are especially important for `LOOP_RISK`, `LOW_STABILITY`, `TOOL_ARGUMENT_ERROR`, and `ERROR_HANDLING_MISSING`, because those failures can cause repeated tool calls, retries, or extra validation runs.

## Budget Warnings

Budget warnings are most relevant in auto mode:

- max rounds reached
- max time reached
- max patches reached
- runtime budget nearly exhausted
- repeated patches modified the same file
- patch validation regressed

Static cost estimate also recommends guardrails such as:

- `max_rounds`
- `max_tests`
- `max_tool_calls_per_test`
- `max_repeated_runs`
- `stop_on_safety_risk`
- `stop_on_regression`
- `stop_on_low_improvement`

## Efficiency Warnings

Auto mode can warn when continued repair is no longer efficient:

```text
The last round improved confidence by only 0.01 while consuming 38% of total runtime.
```

The current code can also warn when the last two rounds improve confidence by less than `--min-improvement`, when runtime budget is nearly exhausted, or when repeated patches touch the same file without clear score improvement.

## Example Summary

```text
Time Cost Summary

Total runtime: 12m 34s
Rounds executed: 3
Tests executed: 28
Average test time: 18.4s

Slowest tests:
1. ambiguous_document_summary: 71.2s
2. missing_file_recovery: 54.8s
3. markdown_schema_validation: 43.1s

Efficiency warning:
The last round improved confidence by only 0.01 while consuming 38% of total runtime.
```

## Deep Mode Usage

Use a static estimate before a larger deep run:

```bash
agentdoctor cost-estimate --mode deep --budget balanced
agentdoctor deep --rounds 3 --review on-fail
```

Inspect measured timing afterward in `reports/latest.json` and `reports/rounds/*.json`.

## Auto Mode Usage

Use explicit budgets for auto:

```bash
agentdoctor auto --target-confidence 0.85 --max-rounds 6 --max-time-minutes 30 --max-patches 4
```

Stop and review manually when efficiency warnings appear.
