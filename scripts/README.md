# scripts

## Responsibility

This directory contains repository maintenance and validation scripts.

## Functionality

- `check_docs_links.py`: scans Markdown docs and examples for broken relative links.
- `harness/`: agent-first harness helper scripts that report state, run existing tests, validate docs, and report codemap drift.

## Public Behavior Contracts

- Scripts should use the standard library unless a project dependency is already required.
- Harness scripts should call existing project commands and avoid changing application behavior.
- Generated reports or runtime data should not be committed unless intentionally placed under docs, tests, or examples.

## Related Tests

- `../tests/test_docs_site.py`

## Related Docs

- `../docs/harness/RUNBOOK.md`
- `../docs/harness/QUALITY_GATES.md`

## Agent Notes

Future agents may add small validation helpers with docs and tests. Do not build
a parallel build system here.
