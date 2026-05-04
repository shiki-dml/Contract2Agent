# CLI Reference

The installed commands are `agentdoctor` and `c2a`. They point to the same implementation. The examples below use `agentdoctor`.

If Typer is installed, the CLI has rich help output. A minimal argparse fallback is also implemented so the same subcommands remain available in lean environments.

## Command Summary

| Command | Purpose | Main output |
|---|---|---|
| `triage` | Static pre-diagnosis intake | `.agentdoctor/triage/` |
| `quick` | Single-round smoke diagnosis | `reports/` |
| `deep` | Multi-round detailed diagnosis | `reports/` |
| `auto` | Bounded diagnosis and safe prompt/config repair loop | `reports/` |
| `patch-preview` | Preview-only patch proposal report | `.agentdoctor/patches/` |
| `cost-estimate` | Static pre-run time/cost estimate | `.agentdoctor/cost/` |
| `new` | Create a generated scaffold from a requirement | selected output directory |
| `compile` | Compile an `agent_contract.yaml` scaffold | selected output directory |
| `demo` | Create the built-in offline demo project | `demo_project/` by default |
| `counterexamples` | Generate deterministic trace cases | selected trace directory |
| `check` | Check one trace against a contract | terminal |
| `check-all` | Check a trace directory | `reports/counterexample_report.md` |
| `diagnose` | Write trace diagnosis report | selected report path |
| `why` | Explain one trace | terminal or selected report path |
| `restrictions` | Print forbidden tools/capabilities | terminal |
| `capabilities` | Summarize capability evidence | terminal or selected report path |

## Triage

Purpose: inspect agent config, prompts, tools, eval metadata, baseline status, patch readiness, risk level, and recommended mode.

Syntax:

```bash
agentdoctor triage [--agent PATH] [--goal TEXT] [--project-root PATH] [--format markdown|json] [--output PATH] [--allow-auto] [--include-cost]
```

Options:

| Option | Meaning |
|---|---|
| `--agent PATH` | Agent config to inspect. |
| `--goal TEXT` | Additional goal/classification signal. |
| `--project-root PATH` | Project root to scan. Defaults to the current directory. |
| `--format markdown|json` | Terminal output format. Reports always write Markdown and JSON. |
| `--output PATH` | Triage report directory. Defaults to `.agentdoctor/triage/`. |
| `--allow-auto` | Allows triage to recommend auto if readiness checks pass. |
| `--include-cost` | Also writes a static cost estimate from the generated triage JSON. |

Examples:

```bash
agentdoctor triage
agentdoctor triage --agent ./agent.yaml
agentdoctor triage --goal "paper reading agent"
agentdoctor triage --project-root .
agentdoctor triage --allow-auto
agentdoctor triage --include-cost
```

Output files:

```text
.agentdoctor/triage/latest.md
.agentdoctor/triage/latest.json
.agentdoctor/triage/triage_<timestamp>.md
.agentdoctor/triage/triage_<timestamp>.json
```

## Quick

Purpose: run one fast smoke-diagnosis round over the highest-priority behavior checks.

Syntax:

```bash
agentdoctor quick [--contract PATH] [--out PATH] [--agent PATH] [--save-baseline] [--baseline-name NAME] [--compare-baseline [REF]]
```

Options:

| Option | Meaning |
|---|---|
| `--contract PATH` | Optional `agent_contract.yaml`. Defaults to `./agent_contract.yaml` or a built-in paper-reader contract. |
| `--out PATH`, `-o PATH` | Report output directory. Defaults to `reports/`. |
| `--agent PATH` | Agent config path used for baseline snapshots. |
| `--save-baseline` | Save this quick run as a baseline. Deep is usually a stronger baseline. |
| `--baseline-name NAME` | Human-readable baseline name. |
| `--compare-baseline [REF]` | Compare with `latest`, a baseline id, or a baseline name. |

Examples:

```bash
agentdoctor quick
agentdoctor quick --contract ./agent_contract.yaml
agentdoctor quick --save-baseline --baseline-name quick-smoke
agentdoctor quick --compare-baseline
```

Output files:

```text
reports/latest.md
reports/latest.json
reports/rounds/round_001.json
```

## Deep

Purpose: run multi-round diagnosis with review policies, traces, tool calls, scores, findings, taxonomy summaries, and optional baseline actions.

Syntax:

```bash
agentdoctor deep --rounds N [--review never|on-fail|each-round] [--contract PATH] [--out PATH] [--agent PATH] [--save-baseline] [--baseline-name NAME] [--compare-baseline [REF]] [--focus TAGS]
```

Options:

| Option | Meaning |
|---|---|
| `--rounds N` | Required number of diagnostic rounds. |
| `--review never|on-fail|each-round` | Review policy. Defaults to `on-fail`. |
| `--contract PATH` | Optional `agent_contract.yaml`. |
| `--out PATH`, `-o PATH` | Report output directory. Defaults to `reports/`. |
| `--agent PATH` | Agent config path used for baseline snapshots. |
| `--save-baseline` | Save this diagnostic run as a baseline. |
| `--baseline-name NAME` | Human-readable baseline name. |
| `--compare-baseline [REF]` | Compare with latest, id, or name. Bare `--compare-baseline` means `latest`. |
| `--focus TAGS` | Comma-separated focus tags for test ordering. |

Examples:

```bash
agentdoctor deep --rounds 3
agentdoctor deep --rounds 5 --review never
agentdoctor deep --rounds 5 --review on-fail
agentdoctor deep --rounds 5 --review each-round
agentdoctor deep --rounds 3 --save-baseline
agentdoctor deep --rounds 3 --compare-baseline
agentdoctor deep --rounds 2 --focus tool_order,output_schema
```

Deep mode does not currently expose `--max-time-minutes`; runtime budgeting is available in `agentdoctor auto`, and static pre-run estimates are available through `agentdoctor cost-estimate`.

## Auto

Purpose: run diagnosis, create/apply limited safe prompt/config patches, validate, and stop on target confidence, budget, low improvement, high-risk patch, or review gates.

Syntax:

```bash
agentdoctor auto [--target-confidence FLOAT] [--max-rounds N] [--max-time-minutes N] [--max-patches N] [--min-improvement FLOAT] [--review never|on-fail|each-round] [--contract PATH] [--out PATH] [--repo-root PATH] [--agent PATH] [--save-baseline] [--baseline-name NAME] [--compare-baseline [REF]]
```

Options:

| Option | Meaning |
|---|---|
| `--target-confidence FLOAT` | Heuristic confidence target. Defaults to `0.85`. |
| `--max-rounds N` | Maximum auto diagnosis/repair rounds. Defaults to `6`. |
| `--max-time-minutes N` | Runtime budget. Defaults to `30`. |
| `--max-patches N` | Maximum allowlisted prompt/config patches. Defaults to `8`. |
| `--min-improvement FLOAT` | Minimum useful confidence improvement. Defaults to `0.03`. |
| `--review never|on-fail|each-round` | Review policy. Defaults to `on-fail`. |
| `--contract PATH` | Optional `agent_contract.yaml`. |
| `--out PATH`, `-o PATH` | Report output directory. Defaults to `reports/`. |
| `--repo-root PATH` | Repository root for safe patch target selection. Defaults to `.`. |
| `--agent PATH` | Agent config path used for baseline snapshots. |
| `--save-baseline` | Save this auto run as a baseline. |
| `--baseline-name NAME` | Human-readable baseline name. |
| `--compare-baseline [REF]` | Compare with latest, id, or name. |

Examples:

```bash
agentdoctor auto --target-confidence 0.85
agentdoctor auto --target-confidence 0.90 --max-rounds 8
agentdoctor auto --target-confidence 0.90 --max-rounds 8 --max-time-minutes 30
agentdoctor auto --target-confidence 0.85 --max-patches 4 --review on-fail
```

Current auto mode does not implement `--preview-patches` or `--require-patch-approval` flags. For preview-only patch proposals, run `agentdoctor patch-preview --from-run reports/latest.json`.

## Patch Preview

Purpose: generate human-reviewable patch proposals from diagnostic findings. In v0.1, this command is preview-only and does not modify files.

Syntax:

```bash
agentdoctor patch-preview [--from-run PATH] [--from-findings PATH] [--failure-type TYPE] [--output PATH] [--format markdown|json] [--dry-run] [--allow-apply] [--apply PATCH_ID] [--project-root PATH]
```

Examples:

```bash
agentdoctor patch-preview --from-run reports/latest.json
agentdoctor patch-preview --from-run reports/latest.json --failure-type OUTPUT_SCHEMA_ERROR
agentdoctor patch-preview --from-findings .agentdoctor/reports/latest.json --output .agentdoctor/patches/
agentdoctor patch-preview --from-run reports/latest.json --format json
```

Output files:

```text
.agentdoctor/patches/latest.md
.agentdoctor/patches/latest.json
.agentdoctor/patches/patch_<timestamp>_<index>.md
.agentdoctor/patches/patch_<timestamp>_<index>.json
.agentdoctor/patches/patch_<timestamp>_<index>.diff
```

`--allow-apply` and `--apply` are accepted for forward compatibility, but Patch Preview v0.1 still refuses to apply changes.

## Cost Estimate

Purpose: estimate diagnostic complexity, test count, tool-call ranges, runtime level, review burden, patch attempts, and guardrails before running expensive diagnosis.

Syntax:

```bash
agentdoctor cost-estimate [--from-triage PATH] [--mode quick|deep|auto] [--budget conservative|balanced|thorough] [--max-rounds N] [--max-tests N] [--max-runtime-minutes N] [--max-llm-calls N] [--max-tool-calls N] [--max-tool-calls-per-test N] [--max-repeated-runs N] [--max-auto-iterations N] [--max-patch-attempts N] [--output PATH] [--format markdown|json]
```

Examples:

```bash
agentdoctor cost-estimate --from-triage .agentdoctor/triage/latest.json
agentdoctor cost-estimate --mode deep --budget balanced
agentdoctor cost-estimate --mode auto --max-auto-iterations 4
agentdoctor cost-estimate --budget conservative --max-rounds 2 --max-tests 12
```

Output files:

```text
.agentdoctor/cost/latest.md
.agentdoctor/cost/latest.json
.agentdoctor/cost/cost_<timestamp>.md
.agentdoctor/cost/cost_<timestamp>.json
```

This is a static estimate. It does not run tests, call tools, call LLM APIs, or report measured runtime.

## Contract and Trace Commands

The original trace-diagnosis commands remain available:

```bash
agentdoctor demo --out demo_project
agentdoctor counterexamples demo_project/agent_contract.yaml --out demo_project/traces/counterexamples
agentdoctor check --contract demo_project/agent_contract.yaml --trace demo_project/traces/passing_trace.json
agentdoctor check-all --contract demo_project/agent_contract.yaml --traces demo_project/traces/counterexamples --diagnose
agentdoctor diagnose --contract demo_project/agent_contract.yaml --traces demo_project/traces/counterexamples --manifest demo_project/traces/counterexamples/manifest.yaml --out demo_project/reports/diagnosis_report.md
agentdoctor why --contract demo_project/agent_contract.yaml --trace demo_project/traces/passing_trace.json
agentdoctor restrictions demo_project/agent_contract.yaml
agentdoctor capabilities demo_project/agent_contract.yaml --out demo_project/capabilities.yaml
```

Use these commands when you are working directly with `AgentContract` files and saved traces.
