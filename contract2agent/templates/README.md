# templates

## Responsibility

This directory contains Jinja templates used to generate example contract/eval
projects and supporting files.

## Functionality

- Template generated agent, tools, monitor, trace, eval, and README files.
- Support legacy contract scaffold generation.

## Important Files And Entry Points

- `agent.py.j2`, `tools.py.j2`, `mock_tools.py.j2`: generated agent/tool surfaces.
- `run.py.j2`, `run_eval.py.j2`: generated execution helpers.
- `eval.yaml.j2`, `failing_trace.json.j2`, `passing_trace.json.j2`: generated eval artifacts.
- `generated_README.md.j2`: generated project documentation.

## Public Behavior Contracts

- Template changes can alter generated project output and should be covered by
  tests or golden expectations.
- Do not introduce secrets, local absolute paths, or environment-specific data
  into generated templates.

## Related Tests

- `../../tests/test_contract2agent.py`

## Related Docs

- `../../docs/CODEMAP.md`
- `../../docs/examples.md`

## Agent Notes

Keep template edits focused and verify generated output expectations.
