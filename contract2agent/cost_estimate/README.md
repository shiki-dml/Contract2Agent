# cost_estimate

## Responsibility

This directory implements static estimates for diagnostic time, cost, review
burden, test count, tool calls, LLM calls, slow paths, and guardrails.

## Functionality

- Load triage or mode inputs.
- Estimate complexity, runtime, failure cost, tool/LLM call burden, and repeated runs.
- Compare budget profiles and diagnostic modes.
- Render Markdown or JSON-style summaries.

## Important Files And Entry Points

- `models.py`: estimate data models.
- `commands.py`, `cli.py`: command formatting and CLI support.
- `runtime.py`, `complexity.py`, `test_count.py`: estimate dimensions.
- `guardrails.py`, `slow_paths.py`, `failure_cost.py`: risk and cost modifiers.
- `report.py`: output rendering.

## Public Behavior Contracts

- Cost estimates are static planning aids, not actual billing records.
- The subsystem should not execute tests, run agents, call APIs, or mutate code.

## Related Tests

- `../../tests/test_cost_estimate.py`

## Related Docs

- `../../docs/time-cost.md`
- `../../docs/CODEMAP.md`

## Agent Notes

Future changes should keep estimates deterministic and transparent. Do not add
provider-specific runtime calls here.
