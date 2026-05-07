# Documentation System Of Record

This directory is the source of truth for Contract2Agent project context,
architecture, code navigation, harness state, and future agent handoffs. The
root `AGENTS.md` is intentionally short; deeper docs here carry the durable
detail. Do not duplicate full manuals into this landing page.

## Start Here

| Need | File |
| --- | --- |
| Project purpose, non-goals, current scope, and evidence model | [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) |
| Architecture boundaries, data flow, CLI flow, and artifact boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Directory, module, CLI, examples, docs, and test coverage map | [CODEMAP.md](CODEMAP.md) |
| Product, evidence, safety, and harness principles | [GOLDEN_PRINCIPLES.md](GOLDEN_PRINCIPLES.md) |
| Architecture and governance decisions | [DECISIONS.md](DECISIONS.md) |
| Current branch/status, baseline notes, risks, and next prompt | [AGENT_HANDOFF.md](AGENT_HANDOFF.md) |
| Harness workflow overview | [harness/README.md](harness/README.md) |
| Harness progress log | [harness/PROGRESS.md](harness/PROGRESS.md) |

## Harness Docs

| Need | File |
| --- | --- |
| Gate selection and blocking rules | [harness/QUALITY_GATES.md](harness/QUALITY_GATES.md) |
| Capability-to-evidence matrix | [harness/EVAL_MATRIX.md](harness/EVAL_MATRIX.md) |
| Sprint planning template | [harness/SPRINT_CONTRACT_TEMPLATE.md](harness/SPRINT_CONTRACT_TEMPLATE.md) |
| Operational runbook | [harness/RUNBOOK.md](harness/RUNBOOK.md) |
| Feature registry data | [harness/feature_registry.json](harness/feature_registry.json) |
| Feature registry schema | [harness/FEATURE_REGISTRY.schema.json](harness/FEATURE_REGISTRY.schema.json) |

## Existing Documentation Areas

- Static site entry points live in [index.md](index.md), [getting-started.md](getting-started.md), and [cli.md](cli.md).
- Diagnostic mode docs live in [quick.md](quick.md), [deep.md](deep.md), and [auto.md](auto.md).
- Feature docs include [triage.md](triage.md), [time-cost.md](time-cost.md), [patch-preview.md](patch-preview.md), [baselines.md](baselines.md), and [failure-taxonomy.md](failure-taxonomy.md).
- File-reading evaluation docs live under [file-reading-eval/](file-reading-eval/README.md).
- Static demos live under [agent-eval/](agent-eval/index.html) and [playground/](playground/index.html).
- Historical audits live under [audits/](audits/2026-05-04-bug-audit.md).

## Maintenance Contract

- Keep these docs aligned with code, tests, examples, and CLI behavior.
- Add architectural decisions to [DECISIONS.md](DECISIONS.md) instead of relying on chat history.
- Keep current work state in [AGENT_HANDOFF.md](AGENT_HANDOFF.md) and [harness/PROGRESS.md](harness/PROGRESS.md).
- Treat tests, docs, examples, and command output as evidence, not absolute proof of full feature completeness.
- Treat benchmark and research references as contextual unless this repository actually ran a comparable evaluation.
