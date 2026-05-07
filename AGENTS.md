# AGENTS.md

This is the short operating contract for future agents. Repository docs are the
source of truth; do not rely on prior chat history or unverified feature claims.

## Project Identity

- Project: Contract2Agent.
- Purpose: pre-runtime AI agent diagnosis, capability classification, eval
  selection, evidence-backed preliminary scoring, and cautious prediction.
- Status: evolving and incomplete; treat inventories as evidence to verify.
- Non-goal: not a fake universal judge. It uses typed schemas, deterministic
  logic, eval packs, observed evidence, and explicit missing-evidence records.

## Hard Rules

- Preserve behavior unless an approved sprint contract changes it; do not
  rename, rewrite business logic, or perform broad harness refactors.
- Keep GitHub Pages static; do not add a backend, browser-run tests, or real
  financial transactions.
- Do not fabricate benchmark claims, observed runs, scores, or experiment
  results.
- Do not mark features verified without evaluator evidence.
- Keep declared, inferred, observed, reference, prediction, and missing
  evidence separate.
- Do not add production dependencies unless the sprint contract justifies them.
- Do not weaken path containment, secret filtering, generated-artifact
  exclusions, or command safety checks.
- Check `git status --short` before and after work; do not stage, commit, reset,
  delete, or rename files unless explicitly asked.

## Where To Look First

- `README.md`: public overview and quick usage.
- `docs/PROJECT_CONTEXT.md`: scope, constraints, evidence discipline.
- `docs/ARCHITECTURE.md` and `docs/CODEMAP.md`: architecture and repo map.
- `docs/GOLDEN_PRINCIPLES.md` and `docs/DECISIONS.md`: principles and ADRs.
- `docs/AGENT_HANDOFF.md`: current status, risks, and next prompt.
- `docs/harness/README.md`, `QUALITY_GATES.md`, `PROGRESS.md`: harness flow.
- `docs/harness/feature_registry.json`: feature status evidence.

## Repository Map

- `contract2agent/`: package code, CLI, contract checks, diagnosis, reports.
- `contract2agent/evaluation/`: schemas, evidence, scoring, prediction, reports.
- `contract2agent/evaluation/file_reading/`: corpus/task/run/grade/report flow.
- `contract2agent/triage/`, `cost_estimate/`, `patch_preview/`: static planning,
  estimate, and preview-only patch proposal subsystems.
- `tests/`, `examples/`, `docs/`, `scripts/`: tests, fixtures, docs, helpers.
- `.codex/` and `.agents/skills/`: project-local agent/skill configuration when
  available; verify runtime support before relying on it.

Use `docs/CODEMAP.md` for the full map; do not copy it here.

## Common Commands

Use the repository Python environment. In WSL or POSIX shells, `python3` may be
the active interpreter; on Windows docs may show `python`.

```bash
python -m pip install -e ".[dev]"
python -m pytest
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
python -m compileall -q contract2agent tests scripts
python scripts/check_docs_links.py
python -m pip install -e ".[docs]"
python -m mkdocs build --strict
bash scripts/harness/doctor.sh
bash scripts/harness/run_tests.sh
python scripts/harness/validate_docs.py
```

Validation note, 2026-05-06: WSL `/usr/bin/python3` had pip 24.0, but
`python3 -m pip install --user "pytest>=7.0"` failed with `externally-managed-environment`;
pytest remained missing, so runtime validation is not proven in that environment.

## Agent Roles

- `codebase_mapper`, `test_inventory_agent`, `docs_inventory_agent`, `feature_inventory_agent`, and `harness_planner` are read-only.
- `contract_generator` writes only approved/proposed sprint contracts, normally under `docs/harness/sprints/<id>/contract.md`.
- `evaluator` is read-only, gives PASS / FAIL / INCONCLUSIVE / BLOCKED, and must not fix issues; only evaluator evidence can justify verified claims.
- `bug_reviewer` is read-only, reports correctness/regression risks, and must not fix issues.
- `doc_gardener` writes approved docs/README/CODEMAP/ARCHITECTURE docs only; it must not edit feature registry, sprint contracts, handoff, or progress unless a specific approved task says so.
- `handoff_writer` writes only handoff/progress artifacts such as `docs/AGENT_HANDOFF.md` and `docs/harness/PROGRESS.md`.
- `feature_generator` modifies implementation/docs/tests only under an approved sprint contract and only inside allowed files.
- No agent may mark features verified or sprints complete without explicit evaluator evidence.

## Handoff And Progress

- Before changing files, read handoff/progress and relevant codemap/architecture docs.
- Sprint contracts belong to `contract_generator`; implementation changes belong to `feature_generator` under an approved contract and allowed files.
- Feature registry updates require explicit scope and evidence; never mark unknown features failed.
- Handoff/progress belongs to `handoff_writer`; record branch, status, files, commands, tests, blockers, risks, and next prompt there.
- Broad writers must not casually edit registry, contracts, handoff, or progress.
- Do not fabricate validation, and do not reinterpret failed or blocked commands as passing.

## Done Definition

- Scope matches the request or sprint contract, and changed files are allowed.
- Tests or validation ran, or blockers are recorded honestly.
- Docs, CLI help, examples, registry, and handoff/progress are aligned when
  required.
- Evaluator evidence exists for verified claims.
- No generated caches, secrets, local runtime data, or unrelated edits are left
  for future agents to untangle.

## What Not To Put Here

- Full architecture, codemap, CLI manual, harness manual, or feature registry.
- Generated inventories, sample reports, audit narratives, or static data JSON.
- Exhaustive feature lists, completion claims, or unverified benchmark/results
  claims.
