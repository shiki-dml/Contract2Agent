# scripts/harness

## Responsibility

This directory contains minimal shell/Python helpers for the repo-local
agent-first development harness.

## Functionality

- `doctor.sh`: prints project root, git status, detected commands, and harness document status.
- `run_tests.sh`: calls the existing safest test command.
- `validate_docs.py`: validates required docs, module README coverage, and feature registry shape.
- `update_codemap.py`: reports codemap drift or writes an explicit draft without overwriting hand-written docs by default.

## Public Behavior Contracts

- Do not mutate application code.
- Do not invent a new test/build system.
- Keep output plain and scriptable.

## Related Docs

- `../../docs/harness/README.md`
- `../../docs/harness/RUNBOOK.md`
- `../../docs/harness/QUALITY_GATES.md`

## Agent Notes

These scripts support handoff and validation. If a script starts changing
behavior, it belongs in a future sprint contract with tests.
