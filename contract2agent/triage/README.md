# triage

## Responsibility

This directory implements static project and agent triage. It identifies missing
information, risk, coverage signals, recommended diagnostic mode, and next
actions before deeper work.

## Functionality

- Discover local project/config files.
- Parse agent and goal inputs.
- Classify risk and eval coverage.
- Recommend quick, deep, auto, or manual follow-up modes.
- Render terminal and JSON summaries.

## Important Files And Entry Points

- `models.py`: triage data models.
- `discovery.py`, `parsers.py`: project and config inspection.
- `classifiers.py`, `coverage.py`, `risk.py`: signal classification.
- `planner.py`, `recommendations.py`: next-action logic.
- `runner.py`, `report.py`: orchestration and rendering.

## Public Behavior Contracts

- Triage is read-heavy planning by default.
- It should not mutate project files or run arbitrary agent experiments.

## Related Tests

- `../../tests/test_triage.py`

## Related Docs

- `../../docs/triage.md`
- `../../docs/CODEMAP.md`

## Agent Notes

Future agents may add better detection heuristics with tests. Keep output
scriptable and avoid overclaiming readiness from missing evidence.
