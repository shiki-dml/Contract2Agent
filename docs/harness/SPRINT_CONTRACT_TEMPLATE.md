# Sprint Contract Template

Create or update this contract before implementation. A `feature_generator`
cannot work without an approved contract. No scope expansion is allowed without
updating the contract first.

## Sprint ID

Short stable identifier:

## Status

One of: proposed, approved, in_progress, evaluator_review, blocked, complete.

## Owner Agent

Primary role responsible for implementation:

## Scope

One bounded feature, bug, or documentation unit.

Allowed files:

- `path/to/file`

## Non-Goals

Explicitly list behavior, files, or refactors this sprint will not touch.

## Forbidden Files

- Source, test, docs, config, generated, or runtime paths that must not change.

## Acceptance Criteria

- Criterion 1
- Criterion 2
- Criterion 3

## Implementation Plan

1. Inspect relevant files.
2. Make the smallest scoped change.
3. Update docs or registry only when evidence changes.

## Test Strategy

Commands, tests, examples, or manual checks that will prove the criteria:

```bash
python -m pytest
```

State which gates are blocking and which are advisory.

## Docs Requirements

- Docs files to update:
- Claims that need evidence:
- Claims intentionally left as `needs_verification`:

## Feature Registry Requirements

- Registry entries to add/update:
- Status before:
- Status after:
- Evidence supporting status:

## Validation Commands

```bash
git status --short
git diff --stat
git diff --name-only
```

Add focused tests, docs checks, JSON validation, MkDocs, or full pytest as
needed by the sprint.

## Evaluator Checklist

The evaluator returns `PASS`, `FAIL`, `INCONCLUSIVE`, or `BLOCKED`.

- Scope matched the approved contract.
- No forbidden paths changed.
- Tests or validation ran, or blockers are recorded honestly.
- No feature is marked `verified_pass` without concrete evidence.
- No benchmark, observed-run, score, or experiment claim is fabricated.
- Handoff/progress records exact commands and results.

## Rollback Plan

- Files that can be reverted if the sprint fails:
- Data or artifacts that must be preserved:
- Manual cleanup needed:

## Handoff Requirements

- Update `docs/harness/PROGRESS.md`.
- Update `docs/harness/feature_registry.json` if feature status changes.
- Update `docs/AGENT_HANDOFF.md` with branch, status, changed files, validation results, risks, blockers, and the recommended next prompt.
