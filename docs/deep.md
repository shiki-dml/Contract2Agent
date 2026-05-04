# Deep Diagnosis

Deep is the multi-round detailed diagnostic mode. It runs diagnosis-only tests, records traces and tool calls, scores behavior, classifies failures, writes round reports, and aggregates findings into a final report.

Deep does not automatically modify the agent.

## Command

```bash
agentdoctor deep --rounds 3 --review on-fail
```

Common variants:

```bash
agentdoctor deep --rounds 3
agentdoctor deep --rounds 5 --review never
agentdoctor deep --rounds 5 --review on-fail
agentdoctor deep --rounds 5 --review each-round
agentdoctor deep --rounds 3 --save-baseline
agentdoctor deep --rounds 3 --compare-baseline
agentdoctor deep --rounds 2 --focus tool_order,output_schema
```

Deep currently does not implement `--max-time-minutes`; use `agentdoctor cost-estimate --mode deep` before running or use auto mode when a hard runtime budget is needed.

## Round Behavior

With the built-in paper-reader test set:

- Round 1 focuses on basic functionality and key paths.
- Round 2 adds more detailed tool, format, and error-handling checks.
- Later rounds include boundary, regression, stability, forbidden-tool, and malformed-trace checks.

Each round contains:

- selected test cases
- trace events
- tool-call lists
- final output
- rule scores
- pass/fail/warning result
- duration per test
- findings
- review items
- failure taxonomy summary
- next-round focus tags

## Review Policies

| Policy | Behavior |
|---|---|
| `never` | Does not pause during the run, but findings can still mark `review_required=true` in reports. |
| `on-fail` | Requires review when a round has failures, warnings, suspicious tool behavior, or review-required findings. |
| `each-round` | Requires review after every round. Recommended for high-risk agents. |

In non-interactive environments, AgentDoctor does not wait forever for input. It records review requirements and follows a safe mode default.

## Output

Deep writes:

```text
reports/latest.md
reports/latest.json
reports/rounds/round_001.json
reports/rounds/round_002.json
reports/rounds/round_003.json
```

The final report aggregates all rounds. Round JSON files preserve per-round traces, test cases, scores, findings, and timing.

## Baseline Comparison

Save a stable baseline:

```bash
agentdoctor deep --rounds 3 --save-baseline --baseline-name stable-v1
```

Compare a future run:

```bash
agentdoctor deep --rounds 3 --compare-baseline stable-v1
```

Bare `--compare-baseline` compares with `latest`.

Baseline comparison can identify:

- confidence delta
- pass/fail/warning delta
- test regressions and improvements
- failure type changes
- prompt/config/tool/eval hash changes
- snapshot differences
- rollback recommendations

## Time Cost

Deep stores measured per-test durations in each round JSON and builds a `time_cost_summary` in the report JSON. For static planning before a run, use:

```bash
agentdoctor cost-estimate --mode deep --budget balanced
```

## When to Use Deep

Use deep mode for:

- detailed tool-call behavior inspection
- multi-round diagnosis
- regression checks
- pre-release validation
- investigating suspicious behavior
- preparing for patch preview or auto mode

Deep is the best default for agents with tools, medium/high risk, missing baselines, or incomplete eval coverage.
