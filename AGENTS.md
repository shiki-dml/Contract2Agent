# AGENTS.md

## Project

AgentDoctor is a diagnostic and repair toolkit for LLM agents.

## Setup

Use the repository's Python environment. If dependencies are missing, prefer the project's configured optional extras.

Common commands:

```bash
pip install -e ".[dev]"
pip install -e ".[docs]"
python -m pytest
python -m compileall -q contract2agent tests scripts
python scripts/check_docs_links.py
python -m mkdocs build --strict
```

## Cleanup Rules

- Do not commit generated output, caches, local virtual environments, or runtime `.agentdoctor` data.
- Keep intentional sample reports and fixtures under `examples/` or `tests/fixtures/`.
- Keep local audit/temp output under ignored `.tmp/` paths.
- Sanitize local absolute paths before adding audit or troubleshooting notes to the repository.

## Safety Rules

- Do not weaken path containment, patch target allowlists, secret filtering, or generated-artifact exclusions.
- Do not remove regression tests added for bug fixes.
- Do not modify secrets, `.env` files, credentials, lock files, generated baselines, generated reports, or user configs except to ensure they are ignored.
- Keep CLI and docs behavior aligned with implemented commands and flags.
