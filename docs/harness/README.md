# Agent-First Development Harness

The harness makes future Codex sessions restartable from repository files rather
than chat history. It supports contract-first planning, scoped implementation,
skeptical evaluation, and durable handoff without changing Contract2Agent
application behavior.

## Workflow

1. Bootstrap: read `AGENTS.md`, [../AGENT_HANDOFF.md](../AGENT_HANDOFF.md), [PROGRESS.md](PROGRESS.md), [../CODEMAP.md](../CODEMAP.md), and [feature_registry.json](feature_registry.json).
2. Plan: create or update a sprint contract from [SPRINT_CONTRACT_TEMPLATE.md](SPRINT_CONTRACT_TEMPLATE.md).
3. Generate: make the smallest bounded change that satisfies the contract.
4. Evaluate: run relevant gates from [QUALITY_GATES.md](QUALITY_GATES.md) and record exact results.
5. Handoff: update [PROGRESS.md](PROGRESS.md), [feature_registry.json](feature_registry.json) when evidence changes, and [../AGENT_HANDOFF.md](../AGENT_HANDOFF.md).

## Role Map

| Role | Responsibility | Writes |
| --- | --- | --- |
| Planner | Defines scope, non-goals, risks, acceptance criteria, allowed files, forbidden files, and validation commands before implementation. | Sprint contract artifacts or progress entries only. |
| Contract generator | Drafts the sprint contract and keeps it aligned with the task. | Sprint contract artifact or `PROGRESS.md` contract section. |
| Feature generator | Implements the bounded change after a contract exists. | Only scoped files named by the contract. |
| Evaluator | Reviews evidence, runs gates, checks regressions, and challenges unsupported claims. | Progress and handoff notes unless explicitly asked to patch tests/docs. |
| Bug reviewer | Reviews failures, regressions, and missing test coverage without broad refactors. | Review notes or scoped fixes only when authorized. |
| Doc gardener | Updates README, architecture, codemap, runbook, and docs alignment without changing product behavior. | Docs allowed by the sprint contract. |
| Handoff writer | Summarizes current state for the next session. | `docs/AGENT_HANDOFF.md` and `docs/harness/PROGRESS.md`. |

Keep planner, generator, evaluator, reviewer, docs, and handoff responsibilities
separate. A feature generator should not quietly expand scope; an evaluator
should not convert missing evidence into a pass.

## Harness Files

| File | Use |
| --- | --- |
| [QUALITY_GATES.md](QUALITY_GATES.md) | Select blocking and advisory checks. |
| [EVAL_MATRIX.md](EVAL_MATRIX.md) | Map feature areas to static, test, runtime, and docs evidence. |
| [SPRINT_CONTRACT_TEMPLATE.md](SPRINT_CONTRACT_TEMPLATE.md) | Define done before implementation starts. |
| [RUNBOOK.md](RUNBOOK.md) | Execute common workflows and recover from environment issues. |
| [FEATURE_REGISTRY.schema.json](FEATURE_REGISTRY.schema.json) | Validate the registry shape. |
| [feature_registry.json](feature_registry.json) | Track feature status, evidence, risks, and verification gaps. |
| [PROGRESS.md](PROGRESS.md) | Chronological work log and command record. |

## Feature Registry

[feature_registry.json](feature_registry.json) is the canonical feature status
map. Use `needs_verification` for inferred behavior by default. Use
`verified_pass` only when concrete evaluator, test, command, or artifact
evidence exists. Use `implemented_pending_evaluation` when code or docs exist
but relevant gates have not been run after the latest change. Unknown behavior
must not be marked failed.

## Harness Scripts

```bash
bash scripts/harness/doctor.sh
bash scripts/harness/run_tests.sh
python scripts/harness/validate_docs.py
python scripts/harness/update_codemap.py
```

Scripts should call existing project commands, report state, and avoid changing
application behavior.
