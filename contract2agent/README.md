# contract2agent Package

## Responsibility

This is the main Python package for Contract2Agent. It contains the public CLI,
legacy contract diagnosis workflow, generalized agent evaluation framework, and
developer workflow helpers.

## Functionality

- Contract parsing, generation, checking, counterexamples, and diagnosis.
- Quick/deep/auto diagnostic modes and baseline comparison.
- Capability reporting and failure taxonomy.
- Generalized agent profile evaluation under `evaluation/`.
- Triage, cost estimate, and patch preview helper subsystems.

## Important Files And Entry Points

- `cli.py`: `c2a` and `agentdoctor` console entry point.
- `schema.py`, `parser.py`, `checker.py`: legacy contract model and trace checks.
- `diagnosis.py`, `diagnostic_modes.py`: report and diagnostic mode orchestration.
- `capabilities.py`, `failure_taxonomy.py`, `baseline.py`: supporting diagnostic outputs.
- `evaluation/`, `triage/`, `cost_estimate/`, `patch_preview/`: major subsystems.

## Public Behavior Contracts

- Keep CLI behavior deterministic and scriptable.
- Preserve legacy contract diagnosis behavior unless a sprint explicitly changes it.
- Do not add real financial side effects.
- Do not collapse missing evidence into positive scores.

## Related Tests

- `../tests/test_contract2agent.py`
- `../tests/test_diagnostic_modes.py`
- `../tests/test_baseline.py`
- `../tests/test_failure_taxonomy.py`
- `../tests/test_docs_site.py`

## Related Docs

- `../docs/CODEMAP.md`
- `../docs/ARCHITECTURE.md`
- `../docs/PROJECT_CONTEXT.md`
- `../docs/cli.md`

## Agent Notes

Future agents may make scoped changes covered by a sprint contract and relevant
tests. Do not do broad package rewrites, move public entry points, or rename the
project as part of harness or docs work.
