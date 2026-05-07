# Harness Runbook

## Start A New Task

```bash
pwd
git status --short
git branch --show-current
git rev-parse --show-toplevel
```

Then read:

- `AGENTS.md`
- `docs/AGENT_HANDOFF.md`
- `docs/harness/PROGRESS.md`
- `docs/CODEMAP.md`
- `docs/harness/feature_registry.json`
- The docs or source files directly related to the request

If sandbox or shell issues block these commands, record the exact failure and
use the safest available read-only fallback.

## Baseline Inspection

Record:

- repository root
- branch
- initial dirty files
- pre-existing untracked files
- shell/environment notes
- known historical pytest/test status from docs or reports

Do not treat historical validation as a fresh run.

## Create A Sprint Contract

1. Choose one bounded feature, bug, or docs unit.
2. Fill out [SPRINT_CONTRACT_TEMPLATE.md](SPRINT_CONTRACT_TEMPLATE.md) or append a completed contract to [PROGRESS.md](PROGRESS.md).
3. Identify allowed files and forbidden files.
4. Select blocking gates from [QUALITY_GATES.md](QUALITY_GATES.md).
5. Confirm non-goals before implementation.

Feature generation starts only after the contract is approved.

## Implement With Feature Generator

1. Read the local patterns first.
2. Edit only scoped files.
3. Preserve existing behavior unless the contract explicitly changes it.
4. Do not add dependencies, test harnesses, generated files, or broad refactors unless the contract allows them.
5. Keep declared, inferred, observed, reference, prediction, and missing evidence separate.

## Evaluate

Run only the relevant commands, then record exact results:

```bash
git status --short
git diff --stat
git diff --name-only
python scripts/harness/validate_docs.py
python scripts/check_docs_links.py
python -m mkdocs build --strict
python -m compileall -q contract2agent tests scripts
python -m pytest
```

Use a subset when the sprint is narrower, but record why any broader gate was
not run. The evaluator result is `PASS`, `FAIL`, `INCONCLUSIVE`, or `BLOCKED`.

## Run Bug Review

Use bug review when a test fails, a report changes unexpectedly, or a risky
boundary is touched. Focus on:

- correctness
- regression risk
- missing tests
- unsafe path/secret/command behavior
- unsupported claims

Do not use bug review as permission for broad cleanup.

## Update Docs

Update docs when public behavior, CLI usage, architecture boundaries, examples,
or evidence status changes. Keep docs concise and link to source-of-truth files
instead of duplicating full manuals.

## Update Feature Registry

Update [feature_registry.json](feature_registry.json) only when evidence or
status changes. Default inferred features to `needs_verification`. Use
`implemented_pending_evaluation` when files changed but gates have not run. Use
`verified_pass` only with concrete evidence.

## Update Handoff And Progress

Before ending a session:

1. Update [PROGRESS.md](PROGRESS.md) with commands and results.
2. Update [feature_registry.json](feature_registry.json) only for features whose evidence changed.
3. Update [../AGENT_HANDOFF.md](../AGENT_HANDOFF.md) with current branch, status, changed files, unchanged behavior, risks, and the next recommended prompt.
4. Check `git status --short` and mention untracked or modified files.

## Handle Missing Pytest Or Dependencies

- If `pytest` is missing, record `dependency_missing` and the exact command output.
- Do not install dependencies unless the user explicitly authorizes it for the task.
- Do not claim tests passed when they were not run.
- If WSL reports `externally-managed-environment`, use the repository's documented Python environment or ask for authorization before changing environment state.

## Handle A Dirty Worktree

- Capture `git status --short` before edits.
- Treat pre-existing modified/untracked files as user or prior-agent work.
- Do not revert, delete, move, stage, or commit them unless explicitly asked.
- If a pre-existing change overlaps the requested files, inspect it and work with it.

## Handle Sandbox Or WSL Issues

- Prefer read-only fallbacks such as `git ls-files`, `tree`, and targeted file reads when `rg` or shell setup fails.
- Record sandbox failures as environment issues, not product failures.
- Request escalation only when a required command is blocked by sandbox or environment restrictions.

## Recommended Next Prompts

```text
Use the repo-local harness. Read AGENTS.md, docs/AGENT_HANDOFF.md,
docs/harness/PROGRESS.md, docs/CODEMAP.md, and
docs/harness/feature_registry.json. Pick one needs_verification feature, write
a sprint contract, make the smallest safe change, run relevant gates, and
update handoff/progress.
```

```text
Act as evaluator. Review the latest diff against docs/harness/QUALITY_GATES.md
and docs/harness/feature_registry.json. Report PASS, FAIL, INCONCLUSIVE, or
BLOCKED with exact evidence.
```

## Recover From Missing Context

If chat history is missing or compacted, do not restart from memory. Use the
repository files above, run the doctor when allowed, and continue from the
latest progress entry.
