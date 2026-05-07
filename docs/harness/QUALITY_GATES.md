# Quality Gates

Run the smallest relevant gate set for the sprint. Record every command,
result, blocker, and skipped gate in [PROGRESS.md](PROGRESS.md) and
[../AGENT_HANDOFF.md](../AGENT_HANDOFF.md). Do not report PASS without real
output.

## Gate Categories

| Gate | Evidence source | Command/check | Blocks acceptance? | Notes |
| --- | --- | --- | --- | --- |
| Scope gate | Sprint contract, `git status --short`, diff name list | Confirm changed files match allowed paths and no forbidden files were edited by the task. | Yes | Always run before final response. Pre-existing dirty files must be labeled. |
| Contract gate | Sprint contract or explicit user task | Confirm scope, non-goals, allowed files, forbidden files, acceptance criteria, and validation plan exist. | Yes for implementation work | Docs-only bootstrap can use the user task as the approved contract. |
| Test gate | Pytest suite and focused tests | `python -m pytest` or focused pytest command. | Yes for behavior/shared code changes | Not required for docs-only tasks unless docs tests are part of acceptance. |
| Compile gate | Python source/tests/scripts | `python -m compileall -q contract2agent tests scripts` | Yes for Python edits | May write `__pycache__`; do not run for docs-only tasks unless needed. |
| Docs gate | Markdown and MkDocs | `python scripts/check_docs_links.py`; `python -m mkdocs build --strict` when docs deps are installed. | Yes for docs/site changes when authorized | If not run, record why and avoid claiming docs build passed. |
| Feature registry gate | Registry schema and policy | `python3 -m json.tool docs/harness/FEATURE_REGISTRY.schema.json`; `python3 -m json.tool docs/harness/feature_registry.json`; schema validator when available. | Yes when registry JSON changes | `json.tool` proves valid JSON only, not schema conformance. |
| Harness docs gate | Harness docs/module README consistency | `python scripts/harness/validate_docs.py` | Yes for harness status upgrades | If skipped, keep harness status at `implemented_pending_evaluation` or `needs_verification`. |
| Evaluator gate | Evidence review | Check overclaims, fake benchmarks, unsupported `verified_pass`, and missing risk records. | Yes | Final review mindset; no fabricated evidence. |
| Handoff gate | Handoff/progress docs | Update `docs/AGENT_HANDOFF.md` and `docs/harness/PROGRESS.md`; run final `git status --short`. | Yes when state changes | Include branch, dirty files, tests run/not run, risks, and next prompt. |

## Command Examples

```bash
git status --short
git diff --stat
git diff --name-only
python3 -m json.tool docs/harness/FEATURE_REGISTRY.schema.json
python3 -m json.tool docs/harness/feature_registry.json
python scripts/harness/validate_docs.py
python scripts/check_docs_links.py
python -m mkdocs build --strict
python -m pytest
```

Use `python` instead of `python3` on Windows if `python3` is unavailable.

## JavaScript Static Demo Gates

| Gate | Command | When |
| --- | --- | --- |
| Legacy demo syntax | `node --check docs/assets/app.js` | Legacy playground JS changed. |
| Agent eval syntax | `node --check docs/assets/agent-eval.js` | Agent-eval demo JS changed. |

## Blocking Versus Advisory

- Blocking: scope violations, missing sprint contract for implementation, invalid JSON after registry changes, failed focused tests for changed behavior, docs build failure after docs/site changes when the build is part of acceptance, unsupported `verified_pass`, and missing handoff/progress for state changes.
- Advisory: broad full-suite pytest for narrow docs-only changes when the user explicitly forbids tests, live GitHub Actions status when offline, live GitHub Pages health unless the task is deployment validation.

## Environment Failures

- `dependency_missing`: required tool or Python package is unavailable. Record exact command and message. Do not claim pass.
- `environment_failed`: sandbox, WSL, path, permission, or OS issue blocks a gate. Record exact command and message. Do not reinterpret as product failure.
- `blocked`: the gate is required but cannot run under current task restrictions. Keep affected feature status below `verified_pass`.

## Evidence Rules

- Passing tests are evidence for implemented behavior only when they cover the relevant surface.
- Documentation claims need code, test, example, or command evidence.
- Benchmark references are contextual unless a comparable observed run exists.
- A failed or skipped gate must be recorded as a risk, not hidden by changing unrelated behavior.
