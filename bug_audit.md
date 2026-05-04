# Contract2Agent Bug Audit

## 2026-05-04 Playground Diagnosis Quality Fix

### 1. What was wrong

- The GitHub Pages playground diagnosis in `docs/assets/app.js` mixed contract clause mentions with active dispute issues.
- Force majeure could become an active issue merely because it appeared as an SLA exclusion.
- Key issues were generated from broad taxonomy-style templates instead of the case facts, dates, party positions, and evidence gaps.
- Risk scoring could be too optimistic because it treated a case with multiple critical notice/cure evidence gaps as low when the rest of the text looked well populated.
- Timeline reasoning did not separately classify invoice dates, notice dates, deemed receipt, cure period, suspension date, or evidence-dependent procedural prerequisites.

### 2. Root cause

- The browser analyzer used one keyword-group pass over contract text, facts, evidence, and metadata.
- The same detected groups fed active issue tags, key issues, clause signals, evidence gaps, and risk.
- There were no negative-trigger rules for clause-only concepts such as force majeure.
- Evidence gaps were mostly generic and were not tied back to core procedural prerequisites before risk scoring.

### 3. Files changed

- `docs/assets/app.js`
  - Added deterministic separation for:
    - contract type detection
    - dispute type detection
    - active issue tags
    - clause signals
    - evidence gaps
    - timeline facts
    - risk object and risk label
    - suggested next steps
  - Preserved the existing static browser playground and existing aliases such as `issue_tags`, `relevant_clause_signals`, and `risk_signal`.
  - Added force majeure negative-trigger behavior: force majeure remains a clause signal when only present in an SLA exclusion, but becomes active only when dispute facts or party positions invoke an external event or force majeure theory.
  - Updated Markdown and JSON output to include the corrected structured diagnosis fields.
- `tests/test_docs_site.py`
  - Added Node-backed tests that execute the actual static `docs/assets/app.js` diagnosis code with a minimal DOM stub.
  - Added regression coverage for force majeure negative triggers, critical evidence gaps, case-specific key issues, output structure separation, Markdown/JSON exports, and the MkDocs playground route.

### 4. Tests added or updated

- `test_playground_force_majeure_clause_signal_is_not_active_issue`
- `test_playground_notice_cure_critical_gaps_prevent_low_risk`
- `test_playground_saas_key_issues_are_case_specific`
- `test_playground_structured_output_separates_core_fields`
- `test_playground_exports_use_corrected_structured_diagnosis`
- `test_mkdocs_nav_preserves_github_pages_playground_route`

### 5. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `rg --files` | Passed | Inspected repository structure and located the static playground assets. |
| `rg -n "function diagnose\|function markdownReport\|force majeure\|risk" docs contract2agent tests` | Passed | Located the active diagnosis/export implementation in `docs/assets/app.js`. |
| `node --check docs\assets\app.js` | Passed | Browser playground JavaScript syntax is valid. |
| `python -m pytest tests\test_docs_site.py` | Passed | 18 passed in 0.47s on the final targeted run. |
| `python -m pytest` | Passed | 231 passed in 23.31s on the final full run. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully. |
| `Test-Path site\playground\index.html` | Passed | Built playground page exists. This preserves the GitHub Pages route that maps to `/Contract2Agent/playground/`. |
| `Test-Path package.json` | Passed | Returned `False`; no npm scripts are present, so `npm test`, `npm run build`, `npm run lint`, and `npm run typecheck` were not applicable. |

### 6. Build and test results

- Playground static build succeeds.
- `site/playground/index.html` is produced by MkDocs.
- The MkDocs nav still includes `Playground: playground/index.html`.
- The static app still contains no runtime `fetch`, `XMLHttpRequest`, `WebSocket`, or dynamic browser import calls.
- The SaaS regression fixture now produces:
  - `contract_type`: includes `SaaS Agreement`
  - `dispute_type`: includes `Notice/Cure Period` and `Payment/Suspension`
  - `active_issue_tags`: includes payment, invoice dispute, notice, cure period, suspension, SLA, service credit, damages, and liability limitation
  - `active_issue_tags`: does not include force majeure
  - `clause_signals`: includes force majeure as an exclusion signal
  - `risk_signal`: `medium`, not low
  - case-specific key issues containing February 1, March 1, March 5, March 18, 10-day cure period, SLA/downtime, service credits, lost revenue, and liability cap concepts

### 7. Remaining limitations

- This remains a deterministic static playground, not legal advice and not an exhaustive legal analyzer.
- Date math is classified and explained, but exact business-day calendar calculation is not performed in the browser.
- Risk scoring is conservative around critical evidence gaps but still heuristic.
- The analyzer does not infer facts that are not present in contract text, dispute facts, party positions, evidence, or metadata.

### 8. Reference pack decision

- A static reference pack was deferred.
- The fix uses curated deterministic phrase maps and negative triggers directly in `docs/assets/app.js`, which keeps the GitHub Pages playground offline, static, and backend-free.
- No runtime browser scraping, external API dependency, CORS proxy, or network call was added.

## 1. Audit Summary

- Audit timestamp: 2026-05-04T17:07:04+08:00
- Repository: Contract2Agent
- Branch/worktree at start of this pass: `main...origin/main` with an already dirty worktree.
- Scope:
  - Repository structure and packaging metadata.
  - `contract2agent/` package import paths, CLI wiring, diagnosis/checker/report-adjacent code paths, and obvious path/error-handling risks.
  - Existing `tests/` suite.
  - MkDocs configuration and Markdown links because docs assets and docs configuration are present in the current worktree.
  - Generated/cache hygiene.
- Final test status: `python -m pytest` passed with 206 tests.
- Source-code fix status for this pass: no new confirmed implementation bug was found after validating the current dirty tree. This file records the audit and environment limitation.

## 2. Environment Notes

- Python command: `python`
- Python version: Python 3.13.7
- Python executable: `D:\tools\python\python.exe`
- Pytest availability before install attempt: already installed.
- Pytest version: 9.0.3
- Runtime/test packages observed:
  - Typer 0.25.1
  - Pydantic 2.13.3
  - PyYAML 6.0.3
  - Jinja2 3.1.6
  - MkDocs 1.6.1
- Packages installed during this pass: none.
- Editable install attempt:
  - Command: `python -m pip install -e .`
  - Result: failed due to Windows permission errors creating pip temporary build-tracker files under `C:\Users\18254\AppData\Local\Temp`.
  - Escalation was requested twice for the same command; automatic approval review timed out both times.
  - Impact: the `c2a` console script could not be verified through PATH in this environment. The module CLI was verified with `python -m contract2agent.cli --help`, and the packaging metadata declares `c2a = "contract2agent.cli:main"`.

## 3. Bugs Found

No new confirmed implementation bugs were found during this pass.

### ENV-001: Editable install blocked by local temp directory permissions

- Files involved:
  - `pyproject.toml`
  - local Python/pip environment
- Symptom:
  - `c2a --help` failed because `c2a` is not installed on PATH.
  - `python -m pip install -e .` failed before installing console scripts.
- Root cause:
  - Pip could not create or access its temporary build tracker under the user's temp directory. This is an external environment permission issue, not a packaging metadata defect in the repository.
- Fix applied:
  - No repository code change was appropriate. The module entry point was validated directly with `python -m contract2agent.cli --help`.
- Why this does not change intended functionality:
  - No product behavior was changed.
  - Existing public console script metadata remains intact: `c2a` is still the primary CLI and `agentdoctor` is retained as a legacy alias.
- Test or verification performed:
  - `python -m contract2agent.cli --help` passed and listed the expected commands.
  - `python -m pytest` passed.

## 4. Tests and Checks Run

| Command | Result | Summary |
| --- | --- | --- |
| `git status --short --branch` | Passed | Worktree was already dirty on `main...origin/main`. |
| `git diff --stat` | Passed | Confirmed broad existing modifications before this pass. |
| `rg --files` | Passed | Inspected repository layout. |
| `python --version` | Passed | Python 3.13.7. |
| `python -c "import sys; print(sys.executable)"` | Passed | `D:\tools\python\python.exe`. |
| `python -m pytest` | Passed | 206 passed in 17.75s. |
| `python -c "import contract2agent; print(contract2agent.__version__ if hasattr(contract2agent, '__version__') else 'import ok')"` | Passed | Printed `0.1.0`. |
| `python -m contract2agent.cli --help` | Passed | CLI module help rendered and listed expected commands. |
| `c2a --help` | Failed due to environment | `c2a` was not on PATH because editable install could not complete. |
| `python -m compileall -q contract2agent tests scripts` | Passed | No syntax errors. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully. |
| `python -m pip install -e .` | Failed due to environment | Pip temp build-tracker permission error. |
| `python -m pytest --version` | Passed | pytest 9.0.3. |
| `python -m mkdocs --version` | Passed | MkDocs 1.6.1. |
| Static `rg` scans for stale branding, broad exception handling, stale CLI notes, and docs asset references | Passed | No new confirmed source bug found. Legacy `agentdoctor` references are documented compatibility paths or aliases. |

## 5. Remaining Risks

- Editable installation and PATH-level `c2a` verification remain blocked by local pip temporary-directory permission errors. This could not be fixed inside the repository during this pass.
- No known repository implementation or test-suite failures remain from this audit pass.

## 6. Final Status

- `python -m pytest`: passed, 206 tests.
- `python -m compileall -q contract2agent tests scripts`: passed.
- `python scripts\check_docs_links.py`: passed.
- `python -m mkdocs build --strict`: passed.
- Commands that could not be run successfully:
  - `python -m pip install -e .`: blocked by local pip temp permission errors.
  - `c2a --help`: blocked because editable install could not complete and the script is not on PATH.
