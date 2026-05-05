# Contract2Agent Bug Audit

## File-Reading Eval Bug and Harness Audit

### Scope

Focused post-change correctness audit for recent file-reading evaluation docs, CLI guide, sample walkthrough, report examples, safety cleanup, and generalized evaluation consistency. Scope was limited to `contract2agent/evaluation/`, `contract2agent/evaluation/file_reading/`, `contract2agent/cli.py`, file-reading tests, relevant docs/examples, README link correctness, `.gitignore`, and audit notes.

### Skills Used

- `pr-reviewer`: used first for review posture, checklist, and risk-oriented inspection.
- `smart-patcher`: used for the confirmed minimal docs/help mismatch fix.
- `unit-test-starter`: used for a focused regression test after the docs/help bug was confirmed.
- `simple-refactor`: inspected but no harness extraction was made.

### Files Inspected

- `AGENTS.md`
- `README.md`
- `README.zh-CN.md`
- `.gitignore`
- `contract2agent/cli.py`
- `contract2agent/evaluation/file_reading/cli.py`
- `contract2agent/evaluation/file_reading/help.py`
- `contract2agent/evaluation/file_reading/runner.py`
- `contract2agent/evaluation/file_reading/tasks.py`
- `contract2agent/evaluation/file_reading/graders.py`
- `contract2agent/evaluation/file_reading/reports.py`
- `contract2agent/evaluation/file_reading/llm_judge.py`
- `docs/file-reading-eval/`
- `examples/file_reading_eval/`
- `tests/test_file_reading_eval.py`
- `tests/test_file_reading_llm_judge.py`
- `tests/test_file_reading_docs_examples.py`

### Bugs/Conflicts Found

#### Bug ID: FRA-BUG-2026-05-05-001

- Area: file-reading docs, CLI help, sample walkthrough.
- Severity: medium.
- Symptom: documented `--agent-command "python examples/file_reading_eval/agents/..."` commands used repository-relative adapter paths, but `run_file_reading_eval()` executes target commands with `cwd=out_dir`. Those commands can therefore fail from `.runs/...` even though the docs present them as runnable walkthrough commands.
- Root cause: documentation and CLI help did not account for the runner's run-directory current working directory.
- Files inspected: `contract2agent/evaluation/file_reading/runner.py`, `contract2agent/evaluation/file_reading/help.py`, `docs/file-reading-eval/*.md`, `examples/file_reading_eval/README.md`, `README.md`, `README.zh-CN.md`, `tests/test_file_reading_docs_examples.py`.

### Production Fixes Made

- No file-reading evaluator scoring, runner, schema, redaction, judge, or generalized evaluation production behavior was changed.
- CLI help text in `contract2agent/evaluation/file_reading/help.py` was corrected to tell users to provide an absolute adapter path.

### Test Harness Changes

- No new harness was added.
- Rationale: the confirmed issue was a narrow docs/help contradiction, and existing file-reading tests plus the focused docs/example test file were clear enough. A shared harness would have added indirection without reducing a repeated setup problem in the audited patch.

### Regression Tests Added/Updated

- Updated `tests/test_file_reading_docs_examples.py` with `test_documented_agent_commands_use_absolute_adapter_path_guidance`.
- The regression checks docs and `file-eval help` topics so repository-relative sample agent commands are not reintroduced.

### Docs/Example Fixes

- Updated `README.md` and `README.zh-CN.md` generic file-reading examples to use `<absolute/path/to/my_agent_adapter.py>`.
- Updated English and zh-CN CLI/sample-run docs to instruct users to set an absolute adapter path before `file-eval run`.
- Updated `examples/file_reading_eval/README.md` with the same guidance.
- Updated `contract2agent/evaluation/file_reading/help.py` examples and deterministic help.

### Safety Checks

- No backend, network pull, browser eval, production dependency, or financial action path was added.
- No `.runs/`, `.judge_cache/`, generated `file_reading_eval/`, cache, or pycache artifacts were added by this patch.
- No benchmark/reference source was changed into a direct score without observed results.
- Existing redaction and validation behavior was not weakened.

### Commands Run And Results

- `python -m pytest tests\test_file_reading_docs_examples.py` - 12 passed.
- `python -m pytest tests\test_file_reading_eval.py` - 26 passed.
- `python -m pytest tests\test_file_reading_llm_judge.py` - 21 passed.
- `python -m pytest tests\test_agent_evaluation_framework.py` - 21 passed.
- `python -m pytest` - 355 passed.
- `python -m compileall -q contract2agent tests scripts` - passed.
- `python scripts\check_docs_links.py` - checked 46 Markdown files; all relative links resolve.
- `python -m mkdocs build --strict` - passed.
- `node --check docs\assets\agent-eval.js` - passed.
- `node --check docs\assets\app.js` - passed.
- `python -m contract2agent.cli --help` - passed.
- `python -m contract2agent.cli file-eval --help` - passed.
- `python -m contract2agent.cli file-eval help llm` - passed.
- `python -m contract2agent.cli file-eval doctor --plain` - passed.
- `c2a --help` - not available on PATH in this shell; module CLI entrypoint passed and docs state `c2a` requires package installation/PATH.
- `git diff --check` - passed.
- `git status --short` - showed only recent docs/examples/tests/help/audit changes plus unrelated untracked local skill directories.
- Local docs/examples safety scan for Windows paths, `/Users|/home|/tmp|/var` paths, `sk-...` keys, and `api_key|token|password|secret` assignments - passed with no hits.

### No-Change Areas

- No production scorer, task parser, evidence span validator, report renderer, LLM judge behavior, generalized framework logic, GitHub Pages JavaScript, or `.gitignore` behavior was changed.
- No test harness was added.

### Remaining Follow-Ups

- `c2a` may remain unavailable on PATH in this shell; module entrypoint verification is the authoritative local check.

## File-Reading Eval User Guide and Sample Report Pass

### Goal

Add high-quality file-reading evaluation documentation, report examples, CLI user guide, and a reproducible sample run walkthrough without redesigning the file-reading evaluation framework.

### Files Inspected

- `README.md`
- `README.zh-CN.md`
- `AGENTS.md`
- `bug_audit.md`
- `pyproject.toml`
- `mkdocs.yml`
- `.gitignore`
- `contract2agent/cli.py`
- `contract2agent/evaluation/file_reading/cli.py`
- `contract2agent/evaluation/file_reading/help.py`
- `contract2agent/evaluation/file_reading/schema.py`
- `contract2agent/evaluation/file_reading/corpus.py`
- `contract2agent/evaluation/file_reading/tasks.py`
- `contract2agent/evaluation/file_reading/graders.py`
- `contract2agent/evaluation/file_reading/reports.py`
- `contract2agent/evaluation/file_reading/references.py`
- `contract2agent/evaluation/file_reading/compare.py`
- `tests/test_file_reading_eval.py`
- `tests/test_file_reading_llm_judge.py`
- `tests/test_docs_site.py`
- `docs/file-reading-eval/`
- `examples/file_reading_eval/`

### Files Changed

- `README.md`
- `README.zh-CN.md`
- `mkdocs.yml`
- `docs/file-reading-eval/README.md`
- `docs/file-reading-eval/README.zh-CN.md`
- `docs/file-reading-eval/cli-guide.md`
- `docs/file-reading-eval/cli-guide.zh-CN.md`
- `docs/file-reading-eval/sample-run.md`
- `docs/file-reading-eval/sample-run.zh-CN.md`
- `docs/file-reading-eval/report-examples.md`
- `docs/file-reading-eval/report-examples.zh-CN.md`
- `examples/file_reading_eval/README.md`
- `examples/file_reading_eval/agents/dummy_good_reader.py`
- `examples/file_reading_eval/agents/dummy_bad_citation_reader.py`
- `examples/file_reading_eval/corpus/contract_policy.md`
- `examples/file_reading_eval/corpus/incident_notes.md`
- `examples/file_reading_eval/corpus/payment_terms.md`
- `examples/file_reading_eval/corpus/distractor_release_notes.md`
- `examples/file_reading_eval/tasks/sample_tasks.jsonl`
- `examples/file_reading_eval/profiles/cautious_reader_profile.json`
- `examples/file_reading_eval/target_outputs/good_output.json`
- `examples/file_reading_eval/target_outputs/bad_citation_output.json`
- `examples/file_reading_eval/target_outputs/hallucinated_output.json`
- `examples/file_reading_eval/target_outputs/no_citation_output.json`
- `examples/file_reading_eval/expected_reports/corpus_manifest.example.json`
- `examples/file_reading_eval/expected_reports/reference_result.example.json`
- `examples/file_reading_eval/expected_reports/deterministic_report.example.json`
- `examples/file_reading_eval/expected_reports/deterministic_report.example.md`
- `tests/test_file_reading_docs_examples.py`
- `bug_audit.md`

### Docs Added

- `docs/file-reading-eval/cli-guide.md`
- `docs/file-reading-eval/cli-guide.zh-CN.md`
- `docs/file-reading-eval/sample-run.md`
- `docs/file-reading-eval/sample-run.zh-CN.md`
- `docs/file-reading-eval/report-examples.md`
- `docs/file-reading-eval/report-examples.zh-CN.md`
- Updated `docs/file-reading-eval/README.md`
- Updated `docs/file-reading-eval/README.zh-CN.md`

### Examples Added

- Synthetic corpus files under `examples/file_reading_eval/corpus/`.
- `examples/file_reading_eval/tasks/sample_tasks.jsonl`.
- `examples/file_reading_eval/profiles/cautious_reader_profile.json`.
- Target output examples under `examples/file_reading_eval/target_outputs/`.
- Report, manifest, and reference result examples under `examples/file_reading_eval/expected_reports/`.

### Tests Added

- `tests/test_file_reading_docs_examples.py`
  - Parses committed file-reading sample JSON files.
  - Imports the sample corpus into a temp directory and validates `sample_tasks.jsonl`.
  - Validates target output JSON examples.
  - Checks sample report JSON/Markdown for expected fields, local path safety, and obvious secret-like placeholder absence.
  - Confirms CLI guide commands exist and module help commands run.
  - Confirms English and zh-CN docs exist and mention required example paths.
  - Confirms `.gitignore` keeps runtime artifacts ignored without ignoring committed examples.
  - Confirms LLM judge docs are optional/safety-sensitive and benchmark/reference language remains contextual.
  - Runs a deterministic grader smoke check over good, bad-citation, hallucinated, and no-citation target output examples.
  - Runs a tiny sample-run smoke check through `dummy_good_reader.py` against `sample_tasks.jsonl` and asserts a high deterministic score.

### Commands Run

- `python -m contract2agent.cli --help` - passed.
- `python -m contract2agent.cli file-eval --help` - passed.
- `python -m contract2agent.cli file-eval help llm` - passed.
- `python -m contract2agent.cli file-eval doctor --plain` - passed.
- `c2a --help` - skipped as unavailable in the current shell; `python -m contract2agent.cli` was verified and docs explain that `c2a` requires installation/PATH.
- `python -m pytest tests\test_file_reading_docs_examples.py` - 11 passed.
- `python -m pytest tests\test_file_reading_eval.py tests\test_file_reading_llm_judge.py` - 47 passed.
- `python -m pytest tests\test_docs_site.py` - 62 passed.
- `python -m pytest` - 354 passed.
- `python -m compileall -q contract2agent tests scripts` - passed.
- `python scripts\check_docs_links.py` - checked 46 Markdown files; all relative links resolve.
- `python -m mkdocs build --strict` - first run failed with 44 warnings because MkDocs strict mode treats links from docs pages to files outside `docs/` as unresolved documentation links; fixed by converting those example references to code paths and adding tests that verify the files exist.
- `python -m mkdocs build --strict` - passed after the link-shape fix.
- `git diff --check` - passed.
- `node --check docs/assets/agent-eval.js` - skipped; JavaScript assets were not changed.
- `node --check docs/assets/app.js` - skipped; JavaScript assets were not changed.

### Results

- Added English and zh-CN file-reading documentation for overview, CLI use, sample run walkthrough, report examples, scoring dimensions, failure modes, improvement guidance, reference import discipline, and comparison rules.
- Added small synthetic sample corpus, task pack, target outputs, profile, and report/reference examples.
- Added regression tests for docs/example integrity and deterministic sample grading.
- Preserved existing file-reading CLI behavior, deterministic default grading, optional LLM judge separation, report redaction behavior, and benchmark-reference contextual language.

### Safety Checks

- Examples are synthetic.
- No committed example is under `.runs/`, `.judge_cache/`, or generated `file_reading_eval/`.
- Documentation uses module CLI commands first and explains `c2a` requires installation.
- Documentation states deterministic grading requires no API key and optional LLM judging is explicit and safety-sensitive.
- Benchmark and reference language remains contextual unless tied to compatible observed results.
- Expected reports contain no local absolute paths or API-key-like placeholder values.
- Docs do not instruct GitHub Pages to run live evaluations, make API calls, or perform network imports by default.
- Runtime directories remain ignored by `.gitignore`.

### Remaining Follow-Ups

- `c2a` is not currently available on PATH in this shell; use `python -m contract2agent.cli` or install the package editable before relying on the console script.
- Rich reference ingestion remains planned; current docs describe implemented local metadata support and mark broader reference import as roadmap.

## Full Project Audit - Brooks Lint Pass

### Audit Scope

- Mode: Full Sweep correctness and consistency audit, scoped to actual bugs and contradictions only.
- Date: 2026-05-05.
- Repository areas inspected:
  - Generalized agent evaluation framework: `contract2agent/evaluation/schema.py`, `capability_classifier.py`, `registry.py`, `evidence.py`, `scoring.py`, `prediction.py`, `reports.py`, `tests/test_agent_evaluation_framework.py`.
  - File-reading evaluation adapter: `contract2agent/evaluation/file_reading/*.py`, `tests/test_file_reading_eval.py`, `tests/test_file_reading_llm_judge.py`.
  - Optional LLM judge: `contract2agent/evaluation/file_reading/llm_judge.py`, `help.py`, reports, README/docs/examples.
  - CLI: `contract2agent/cli.py`, `contract2agent/evaluation/file_reading/cli.py`, CLI subprocess tests, direct module help smoke tests.
  - GitHub Pages/static demo: `docs/assets/agent-eval.js`, `docs/assets/app.js`, `docs/data/agent_eval/*.json`, `tests/test_docs_site.py`.
  - Docs and examples: `README.md`, `README.zh-CN.md`, `docs/file-reading-eval/`, `examples/file_reading_eval/`, `mkdocs.yml`.
  - Safety/cleanup: `.gitignore`, corpus import filtering, report sanitization, judge input/report sanitization.

### Baseline Results Before Fixes

| Command | Result | Notes |
| --- | --- | --- |
| `python -m pytest` | Passed | 333 passed in 38.55s before this pass's edits. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Baseline syntax compilation passed. |
| Direct CLI smoke commands | Partially blocked, later rerun | Early approval checks timed out for CLI helps; direct module CLI checks passed later after retry. |

### Issue AUDIT-001

- Bug ID: AUDIT-001
- Area: File-reading evaluation cleanup / generated artifacts
- Severity: medium
- Symptom: File-reading examples and help use `.runs/`, `file-eval init` creates a default `file_reading_eval/` workspace, and optional judge caching writes `.judge_cache/`, but `.gitignore` did not ignore those generated artifacts.
- Root cause: New file-reading runtime paths were documented/implemented without corresponding generated-artifact ignore rules.
- Files inspected: `.gitignore`, `contract2agent/evaluation/file_reading/cli.py`, `contract2agent/evaluation/file_reading/llm_judge.py`, `README.md`, `docs/file-reading-eval/README.md`.
- Files changed: `.gitignore`, `tests/test_file_reading_llm_judge.py`.
- Tests added or updated: `test_generated_file_eval_artifacts_are_gitignored`.
- Fix summary: Added `/.runs/`, `/file_reading_eval/`, and `.judge_cache/` ignore rules while preserving intentional `examples/file_reading_eval/` fixtures.
- Verification commands: `python -m pytest tests\test_file_reading_llm_judge.py -k gitignored`; final full suite.
- Results: Focused test failed before the ignore update and passed after it; final `python -m pytest` passed.
- Remaining limitations or follow-ups: No remaining issue found.

### Issue AUDIT-002

- Bug ID: AUDIT-002
- Area: File-reading task validation
- Severity: high
- Symptom: `validate_tasks` checked task file lists and answerability metadata but did not validate `gold_evidence_spans` or `expected_citations` for manifest file IDs, valid line ranges, quote matches, or malformed line-number types.
- Root cause: Evidence-span validation existed only indirectly in graders; task validation did not inspect span integrity and could raise `TypeError` for string line numbers.
- Files inspected: `contract2agent/evaluation/file_reading/tasks.py`, `graders.py`, `schema.py`, `tests/test_file_reading_eval.py`.
- Files changed: `contract2agent/evaluation/file_reading/tasks.py`, `tests/test_file_reading_eval.py`.
- Tests added or updated: `test_task_validation_catches_bad_evidence_spans`, `test_task_validation_reports_non_integer_evidence_lines`.
- Fix summary: Added deterministic span validation for file IDs, integer line numbers, line range ordering/bounds, and quote match against manifest text.
- Verification commands: `python -m pytest tests\test_file_reading_eval.py -k "bad_evidence_spans or non_integer_evidence_lines"`; final full suite.
- Results: New tests failed before the fix and passed after it; final `python -m pytest` passed.
- Remaining limitations or follow-ups: Character-offset validation remains a future enhancement; current implemented task format is line-oriented.

### Issue AUDIT-003

- Bug ID: AUDIT-003
- Area: File-reading target output validation
- Severity: high
- Symptom: `validate_target_output` recorded citation schema errors but still attempted to construct `Citation` with missing `file_id` or unsafe line types, causing a crash instead of a deterministic schema failure.
- Root cause: Citation coercion used `from_dict(Citation, item)` before normalizing required and optional citation fields.
- Files inspected: `contract2agent/evaluation/file_reading/graders.py`, `schema.py`, `tests/test_file_reading_eval.py`.
- Files changed: `contract2agent/evaluation/file_reading/graders.py`, `tests/test_file_reading_eval.py`.
- Tests added or updated: `test_output_schema_validation_handles_malformed_citation_objects`.
- Fix summary: Citation validation now preserves an invalid output as `schema_valid=False`, reports concrete field errors, and coerces unsafe citation fields to non-crashing defaults.
- Verification commands: `python -m pytest tests\test_file_reading_eval.py -k malformed_citation`; final full suite.
- Results: New test failed before the fix and passed after it; final `python -m pytest` passed.
- Remaining limitations or follow-ups: Confidence bounds remain permissive because current schema treats confidence as optional metadata rather than a scored requirement.

### Issue AUDIT-004

- Bug ID: AUDIT-004
- Area: File-reading report safety
- Severity: high
- Symptom: Report JSON sanitized values that were exactly absolute paths, but leaked local absolute paths embedded inside target-agent answer text, notes, raw output, grade warnings, optional comparison, or optional judge report structures.
- Root cause: `_sanitize_report_value` only tested `Path(value).is_absolute()` and did not scan string content.
- Files inspected: `contract2agent/evaluation/file_reading/reports.py`, `runner.py`, `schema.py`, `tests/test_file_reading_llm_judge.py`.
- Files changed: `contract2agent/evaluation/file_reading/reports.py`, `tests/test_file_reading_llm_judge.py`.
- Tests added or updated: `test_embedded_absolute_paths_are_sanitized_in_report_json`.
- Fix summary: Added embedded Windows/POSIX local path redaction and applied report sanitization to grades, scorecards, comparison payloads, and optional LLM judge payloads.
- Verification commands: `python -m pytest tests\test_file_reading_llm_judge.py -k embedded_absolute_paths`; final full suite.
- Results: New test failed before the fix and passed after it; final `python -m pytest` passed.
- Remaining limitations or follow-ups: Sanitizer targets common local absolute path forms; it intentionally does not rewrite ordinary relative artifact names.

### Issue AUDIT-005

- Bug ID: AUDIT-005
- Area: Optional LLM judge failure reports
- Severity: high
- Symptom: A failing command-based judge could write stderr containing local absolute paths into `llm_judge.json`.
- Root cause: Judge failure text was stored verbatim in `FileReadingJudgeTaskResult.error` and `FileReadingJudgeReport.failures`.
- Files inspected: `contract2agent/evaluation/file_reading/llm_judge.py`, `tests/test_file_reading_llm_judge.py`.
- Files changed: `contract2agent/evaluation/file_reading/llm_judge.py`, `tests/test_file_reading_llm_judge.py`.
- Tests added or updated: `test_judge_failure_report_sanitizes_local_absolute_paths`.
- Fix summary: Judge failure strings now redact common local absolute path forms before being written to report artifacts.
- Verification commands: `python -m pytest tests\test_file_reading_llm_judge.py -k judge_failure_report_sanitizes`; final full suite.
- Results: New test failed before the fix and passed after it; final `python -m pytest` passed.
- Remaining limitations or follow-ups: Command adapters can still emit arbitrary non-path diagnostic text; secrets are handled separately by AUDIT-006/AUDIT-007.

### Issue AUDIT-006

- Bug ID: AUDIT-006
- Area: Optional LLM judge input safety
- Severity: critical
- Symptom: If a target-agent answer contained an API-key-like or secret-assignment token, `build_judge_input` could include it in compact optional judge input.
- Root cause: Judge input sanitization handled local paths and forbidden citations, but not secret-like text embedded in answers or quoted fields.
- Files inspected: `contract2agent/evaluation/file_reading/llm_judge.py`, `tests/test_file_reading_llm_judge.py`.
- Files changed: `contract2agent/evaluation/file_reading/llm_judge.py`, `tests/test_file_reading_llm_judge.py`.
- Tests added or updated: `test_judge_input_redacts_secret_like_answer_text`.
- Fix summary: Added conservative redaction for API-key/token/password/secret assignments and OpenAI-key-shaped values before judge inputs are serialized.
- Verification commands: `python -m pytest tests\test_file_reading_llm_judge.py -k redacts_secret_like`; final full suite.
- Results: New test failed before the fix and passed after it; final `python -m pytest` passed.
- Remaining limitations or follow-ups: This is a deterministic safety filter, not a full DLP engine; the importer still skips common secret files by default.

### Issue AUDIT-007

- Bug ID: AUDIT-007
- Area: File-reading report secret filtering
- Severity: critical
- Symptom: Generated report JSON could include API-key-shaped or secret-assignment values embedded in target-agent output text.
- Root cause: Report sanitization did not redact secret-like content before serializing run outputs and raw output.
- Files inspected: `contract2agent/evaluation/file_reading/reports.py`, `tests/test_file_reading_llm_judge.py`.
- Files changed: `contract2agent/evaluation/file_reading/reports.py`, `tests/test_file_reading_llm_judge.py`.
- Tests added or updated: `test_secret_like_values_are_sanitized_in_report_json`.
- Fix summary: Reused conservative secret-like redaction in report string sanitization before path redaction.
- Verification commands: `python -m pytest tests\test_file_reading_llm_judge.py -k "secret_like_values_are_sanitized or embedded_absolute_paths"`; final full suite.
- Results: New test failed before the fix and passed after it; final `python -m pytest` passed.
- Remaining limitations or follow-ups: Redaction intentionally prioritizes common credential shapes and explicit secret/key assignments.

### Issue AUDIT-008

- Bug ID: AUDIT-008
- Area: README/docs consistency
- Severity: medium
- Symptom: `README.zh-CN.md` had a new file-reading LLM judge update appended in English, and `docs/file-reading-eval/README.zh-CN.md` was an English placeholder despite being linked as zh-CN documentation.
- Root cause: English docs were updated first and the bilingual docs were not localized.
- Files inspected: `README.md`, `README.zh-CN.md`, `docs/file-reading-eval/README.md`, `docs/file-reading-eval/README.zh-CN.md`, `mkdocs.yml`, `tests/test_file_reading_llm_judge.py`.
- Files changed: `README.zh-CN.md`, `docs/file-reading-eval/README.zh-CN.md`, `tests/test_file_reading_llm_judge.py`.
- Tests added or updated: `test_readme_zh_cn_file_reading_llm_judge_section_is_localized`, `test_file_reading_eval_zh_cn_guide_is_localized`.
- Fix summary: Localized the README LLM judge section and replaced the zh-CN file-reading guide placeholder with a concise Chinese guide covering deterministic defaults, explicit LLM enablement, API-key handling, budgets, static Pages constraints, and limitations.
- Verification commands: `python -m pytest tests\test_file_reading_llm_judge.py -k readme_zh_cn`; `python -m pytest tests\test_file_reading_llm_judge.py -k file_reading_eval_zh_cn`; docs link/build checks.
- Results: New tests failed before localization and passed after it; docs link checker and strict MkDocs build passed.
- Remaining limitations or follow-ups: The zh-CN file-reading guide is intentionally concise rather than a line-for-line full translation of the English guide.

### Areas Inspected With No Code Change Required

- Generalized agent evaluation framework: no change required. Existing tests cover JSON-serializable schemas, non-name classification, unknown-agent fallback, benchmark contextuality, declared-only confidence limits, simulation-only financial classification, and evidence/limitations in reports.
- GitHub Pages/static demo: no change required. Static asset scan found no external API calls, WebSockets, `eval()`, API key exposure, backend behavior, or real financial execution. The only `fetch` in `docs/assets/agent-eval.js` loads local static JSON metadata.
- Research/benchmark metadata: no change required. Static and file-reading references remain contextual and low-reliability; comparison logic requires compatible task pack, scoring method, environment, and comparable conditions before computing deltas.
- Old contract playground preservation: no change required. Existing docs/static tests still cover the legacy route and deterministic browser-side diagnosis behavior.
- Production dependencies and backend architecture: no change required. No dependencies, backend, live eval runner in browser, or real financial action path was added.

### Final Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `python -m pytest tests\test_file_reading_eval.py tests\test_file_reading_llm_judge.py` | Passed | 47 passed in 5.90s. |
| `python -m contract2agent.cli --help` | Passed | Module CLI help rendered and listed `file-eval`. |
| `python -m contract2agent.cli file-eval --help` | Passed | Listed file-eval options and subcommands. |
| `python -m contract2agent.cli file-eval help llm` | Passed | States deterministic default, explicit LLM enablement, key handling, and budget controls. |
| `python -m contract2agent.cli file-eval doctor --plain` | Passed | Doctor checks rendered without ANSI color; `OPENAI_API_KEY` warned when absent. |
| `c2a --help` | Failed due environment | `c2a` is not installed on PATH in this environment; module entry point and pyproject script metadata were verified instead. |
| `node --check docs\assets\agent-eval.js` | Passed | Static agent-eval JavaScript syntax is valid. |
| `node --check docs\assets\app.js` | Passed | Legacy playground JavaScript syntax is valid. |
| `python scripts\check_docs_links.py` | Passed | Checked 35 Markdown files; all relative links resolve. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Final syntax compilation passed. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully. |
| `python -m pytest` | Passed | 343 passed in 34.95s after the final audit log update. |
| `git diff --check` | Passed | No whitespace errors. |

### Commands Skipped Or Substituted

- `c2a --help` could not be used because the console script is not installed on PATH in the current environment. Equivalent `python -m contract2agent.cli --help` passed, and `pyproject.toml` still declares `c2a = "contract2agent.cli:main"`.
- No network import or live LLM judge API call was run. That is intentional: baseline file-reading evaluation is deterministic/offline, and optional LLM judging must be explicitly enabled with credentials.
- No destructive git operations, commits, pushes, dependency installs, backend services, or browser live experiments were run.

### Risks Left As Follow-Up

- File-reading evidence validation is line-oriented. Character-offset validation remains a possible future enhancement if tasks begin relying on character spans.
- Secret redaction is conservative and deterministic, not a complete DLP system. It covers common key/token/password/secret assignments and OpenAI-key-shaped values.
- The zh-CN file-reading guide is concise; a future documentation pass could fully translate the English guide if desired.

### Preservation Confirmation

- Existing correct behavior was preserved: generalized classification, benchmark contextuality, profile-only no observed score, deterministic default grading, optional LLM separation, CLI command surface, GitHub Pages static constraints, and legacy contract playground tests all still pass.
- No production dependency, backend, live browser eval, real financial transaction path, or exact fixture-name hard-coding was added.

## File Reading Agent Evaluation Adapter

### 1. Why profile-only classification is insufficient

File-reading performance depends on observed behavior: selecting the right files, extracting the right spans, citing them correctly, abstaining when evidence is missing, and respecting forbidden-file boundaries. The new adapter keeps profile-only output as readiness/risk analysis and explicitly reports: "No observed performance score because no agent run was executed."

### 2. CLI runner added

Added `c2a file-eval` with local corpus import, reference listing/import skeleton, task validation, smoke task generation, sequential black-box target runs, grading, comparison, reporting, and profile-only readiness reports. The runner requires an explicit `--agent-command` with `{input_json}` and `{output_json}` placeholders, enforces `--time-budget-seconds` and `--max-tasks`, captures stdout/stderr, records trace metadata, and writes `run.json` / `run.jsonl`.

### 3. Corpus, task, and reference schemas added

Added JSON-serializable dataclasses for file-reading profiles, corpus manifests, document records, tasks, evidence spans, target inputs/outputs, citations, traces, runs, grades, scorecards, reference sources/results, and comparison reports under `contract2agent/evaluation/file_reading/`.

### 4. Graders added

Added deterministic graders for answer exact/F1 scoring, citation presence, citation span overlap, quote matching, supporting-file recall/precision, forbidden-file violations, unanswerable abstention, schema compliance, latency/timeout, trace completeness, and unsupported-claim heuristics.

### 5. Reference comparison avoids fake benchmark claims

Curated references for OpenAI eval methodology, QASPER, SQuAD, HotpotQA, DocVQA, and LongBench are stored as contextual metadata. Comparison checks task pack, scoring method, environment, and `comparable_conditions`; incompatible references are marked contextual only and no leaderboard-style ranking is produced.

### 6. User-provided papers/files

`c2a file-eval import-local --source-type paper --title ...` imports a user-provided file or paper into a local corpus and writes a `reference_source.json` with provenance, license, limitations, and no metrics. The import remains offline.

### 7. Safety and path boundaries

The local importer skips `.env`, credential/key-like files, `.git` internals, caches, virtualenvs, `node_modules`, `__pycache__`, browser-data-like directories, and unsupported binary/PDF files by default. Document records use sanitized reportable absolute paths. The runner does not use `shell=True`, does not delete user files, and does not use network access by default.

### 8. Tests added

Added `tests/test_file_reading_eval.py` covering schema serialization, manifest creation, unsafe-path skipping, document hashes/line counts, task JSONL loading/validation, citation quote checks, supporting-file scoring, forbidden-file scoring, abstention scoring, output schema validation, dummy-agent CLI runs, task budget enforcement, run/grade/report artifacts, profile-only no-score behavior, reference registry discipline, contextual-only incompatible comparisons, CLI help, and user paper import.

### 9. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `python -m pytest` | Failed, then passed | Initial run found a Windows command-splitting bug in the runner; after fixing it and adding `file-eval --help` coverage, 319 tests passed in 33.78s. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Syntax compilation succeeded after adding the adapter and tests. |
| `python scripts\check_docs_links.py` | Passed | Checked 27 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully on final runs. |
| `python -m contract2agent.cli --help` | Blocked by tool sandbox | Direct shell invocation hit a sandbox setup/approval timeout; equivalent subprocess coverage is included in `python -m pytest`. |
| `python -m contract2agent.cli file-eval --help` | Blocked by tool sandbox | Direct shell invocation hit a sandbox setup/approval timeout; equivalent subprocess coverage is included in `python -m pytest`. |

### 10. Limitations and follow-ups

- PDF extraction is not bundled; users should convert PDFs to text/Markdown or a future optional extra can add extraction.
- Network dataset import is intentionally a controlled skeleton and requires `--allow-network`; the dependency-free core records metadata rather than downloading large datasets.
- Grading is deterministic and lexical/span-based. Optional semantic or LLM rubric judging is a future extension and should be disabled by default.
- Runs are sequential for now; parallel scheduling can be added once trace and artifact isolation requirements are stable.

## Agent Evaluation Generalization and Overfitting Audit

### Files inspected

- `contract2agent/evaluation/schema.py`
- `contract2agent/evaluation/capability_classifier.py`
- `contract2agent/evaluation/registry.py`
- `contract2agent/evaluation/evidence.py`
- `contract2agent/evaluation/scoring.py`
- `contract2agent/evaluation/prediction.py`
- `contract2agent/evaluation/reports.py`
- `contract2agent/cli.py`
- `README.md`
- `AGENTS.md`
- `mkdocs.yml`
- `docs/playground/index.html`
- `docs/assets/app.js`
- `tests/test_agent_evaluation_framework.py`
- `tests/test_docs_site.py`
- `examples/agent_eval/*`

### Overfit patterns found

- The initial generalized evaluation layer defined detailed type-specific eval pack ids such as `coding_patch_correctness`, `browser_task_completion`, and `simulated_trade_risk_controls`. That looked like a deeper specialist-evaluator surface than the current architecture should claim.
- The report and scorecard exposed an `overall_score` path that could look like a single opaque judgment if experiment summaries were present.
- The schema did not explicitly separate `CapabilitySignal`, `EvidenceSource`, `ExperimentSummary`, `PreliminaryScore`, and final `Prediction`.
- The classifier already avoided exact agent-name scoring, but its matched signal trail was string-only and did not record source field, strength, or explanation.
- Unknown-agent handling was present, but missing-evidence and recommended-test behavior needed to be made more explicit for vague profiles.
- Benchmark references were not used as direct scores, but the old `BenchmarkReference` model sat beside scoring in a way that needed clearer contextual-source semantics.

### Stale project-positioning content found

- The tracked baseline still contained `AgentDoctor` wording in `AGENTS.md` and sample report names.
- `docs/playground/index.html` still describes the legacy contract-dispute playground as turning contract disputes into structured reports. That page is intentionally kept as a legacy/specialized demo, but it should not define the project identity.
- `mkdocs.yml` still described the site as contract-driven diagnosis and did not expose the new agent-evaluation static demo route.

### Logic removed or refactored

- Refactored the evaluation core from detailed eval packs to broad `EvalCategory` selection.
- Added explicit `CapabilitySignal` objects with source field, matched value, strength, confidence, and explanation.
- Added `EvidenceSource` records that distinguish user-declared, inferred, observed/imported, benchmark, curated methodology, synthetic, and missing evidence.
- Replaced type-specific score dimensions with a simple preliminary scorecard: `capability_fit`, `evidence_strength`, `tool_risk`, `autonomy_risk`, `task_clarity`, `approval_safety`, `data_access_risk`, `expected_reliability`, and `missing_evidence_penalty`.
- Kept benchmark and methodology references capped as contextual low-reliability sources; they do not produce direct scores.
- Added a static `docs/agent-eval/` demo that explains signals, evidence basis, missing evidence, source references, and next tests without backend or API calls.

### Logic intentionally kept

- Existing legacy contract diagnosis and GitHub Pages playground behavior remain intact.
- The `c2a eval-agent` command remains additive and local-file-only.
- Broad agent-family classification remains deterministic phrase/signal matching rather than a learned or universal judge.
- Financial transaction classification remains simulation-only and high-risk by default.

### Risks remaining

- The framework is still heuristic and preliminary; it does not replace specialized eval packs or grader-backed experiment runs.
- The static demo and Python classifier use curated signal lists, so new terminology may require registry expansion.
- Pasted experiment summaries in the static demo are user-provided and not independently verified.
- Reference metadata is intentionally contextual; stronger claims require linked experiment summaries or imported traces.

## Invoice Dispute Issue-Family Gate

### Symptom

Cost/evidence invoices were incorrectly promoted to active invoice disputes. Cost-support records such as alternative supplier invoices, repair invoices, remediation vendor invoices, and outside counsel invoices could leak into active issue surfaces even when the facts denied unpaid invoices, disputed invoices, billing disputes, invoice nonpayment, or any invoice-payment controversy.

### Root cause

The issue activation framework treated generic invoice mentions as active triggers and did not distinguish clause signals, active invoice-payment disputes, blockers, and evidence-only invoices. `hasInvoiceDisputeFactTrigger(data)` and `deriveActiveIssueTags` could activate `invoice dispute` once invoice-like factual wording was present, while timeline extraction collected generic invoice-dated segments without distinguishing cost evidence from invoice-payment dispute dates.

### Framework Change

The existing `issueFamilyRegistry` and `shouldActivateIssueFamily(...)` path now support a role-aware invoice family definition:

- `active_triggers` are factual payment-controversy triggers.
- `clause_triggers` are contract-text and clause-signal terms only.
- `blocker_triggers` are explicit negative factual terms.
- `evidence_only_triggers` and `evidence_context_triggers` mark cost/damages invoice references that must not become active issue candidates.
- `activation_gate: "invoice_payment_dispute"` routes invoice dispute through `shouldActivateInvoiceDispute(data)` before `finalDiagnosis.active_issue_tags` is produced.

`issueFamilyCandidateSegments(...)` now filters blocked and evidence-only segments at the issue-family candidate layer. Downstream builders still consume the filtered final diagnosis rather than re-running invoice activation.

### Files Inspected

- `docs/assets/app.js`
- `docs/playground/index.html`
- `tests/test_docs_site.py`
- `bug_audit.md`
- `pyproject.toml`

### Files Changed

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### Invoice Dispute Trigger Model

- Clause triggers: invoice due date, payment terms, billing terms, net 30, invoice dispute notice/procedure, late payment charge, payment schedule, and payment timing. These can create `clause_signals` but not active issues by themselves.
- Active triggers: unpaid invoice, invoice nonpayment, disputed invoice, billing dispute, payment dispute, payment demand, overdue invoice, late payment, failure/refusal to pay invoice, rejected invoice, charge dispute, disputed amount, invoice dispute notice, customer disputed the invoice, provider/seller claims the invoice remains unpaid, buyer claims the invoice was improper, invoice amount contested, invoice not paid by the due date, and payment withheld because the invoice was disputed.
- Blocker triggers: no invoice dispute, no unpaid invoices, no late payment, no payment dispute, no billing dispute, no invoice nonpayment, no disputed invoice, no payment controversy, no party claims unpaid invoices, no party claims invoice dispute, and no party claims late payment.
- Evidence-only triggers: alternative/substitute supplier invoice, cover-cost invoice, repair invoice, remediation invoice, remediation vendor invoice, outside counsel invoice, attorney/legal-fee invoice, vendor invoice proving costs, contractor invoice proving repairs, supplier invoice used as evidence, invoice used to support damages or calculate cover costs, invoice attached as proof of cost, replacement-goods invoice, audit/access-review invoice, investigation-cost invoice, and remediation-cost invoice.

### Active Invoice-Dispute Trigger Rule

`shouldActivateInvoiceDispute(data)` requires factual-field support for an invoice-payment controversy, such as unpaid invoices, invoice nonpayment, a disputed invoice amount, billing dispute, payment demand, overdue invoice, rejected invoice, charge dispute, invoice dispute notice, failure or refusal to pay an invoice, or facts that a customer/provider disputes whether an invoice is owed. Contract payment terms and invoice dispute procedures do not activate the issue by themselves.

### Blocker / Non-Active Evidence Rule

Explicit negatives such as no invoice dispute, no unpaid invoices, no late payment, no payment dispute, no billing dispute, no invoice nonpayment, no disputed invoice, no payment controversy, and no party claiming unpaid invoices block active invoice-dispute activation unless another factual segment clearly alleges a real payment controversy. Cost-evidence phrases such as alternative supplier invoice, cover cost invoice, repair invoice, remediation invoice, remediation vendor invoice, outside counsel invoice, attorney invoice, legal fee invoice, vendor invoice proving costs, invoice used to support damages, invoice used to calculate cover costs, and invoice attached as proof of cost are treated as non-active evidence.

### Regression Tests Added Or Updated

- Updated `test_playground_alternative_supplier_invoice_is_not_invoice_dispute`.
- Added `test_playground_real_unpaid_invoice_dispute_still_activates`.
- Added `test_playground_invoice_clause_only_does_not_activate`.
- Added `test_playground_cost_evidence_invoices_are_not_invoice_disputes`.
- Added `test_playground_invoice_dispute_state_does_not_leak_to_cover_invoice_case`.
- Added `test_playground_invoice_dispute_export_consistency_for_cover_invoice`.

### Commands Run

| Command | Result | Summary |
| --- | --- | --- |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript parses successfully. |
| `python -m pytest tests/test_docs_site.py -k "invoice"` | Passed | 6 passed, 48 deselected. |
| `python -m pytest tests/test_docs_site.py` | Passed | 54 passed. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python -m pytest` | Passed | 267 passed. |
| `Test-Path package.json` | Passed | Returned `False`; no npm project is present, so `npm test`, `npm run build`, `npm run lint`, and `npm run typecheck` are not applicable. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully. |
| `git diff --check` | Passed | No whitespace errors. |

### Results

- Alternative supplier and cover-cost invoices remain damages evidence and do not activate `invoice dispute`.
- Real unpaid/disputed invoice facts still activate `invoice dispute`.
- Invoice/payment contract clauses remain clause signals unless factual payment controversy exists.
- Repair, remediation, vendor, and counsel invoices are classified as cost evidence, not invoice-dispute dates.
- Sequential positive-to-negative runs do not leak invoice-dispute issues, gaps, next steps, or Evaluation Lab expected issues.
- JSON, Markdown, structured preview, and Evaluation Lab outputs exclude `invoice dispute` when the final diagnosis excludes it.

### Remaining Follow-Ups

No known follow-up is required for this invoice-dispute false positive. The gate remains deterministic phrase matching, so future examples with new invoice-payment wording may need additional trigger terms.

## Force Majeure Active/Blocker Trigger Fix

### Symptom

Force majeure could be treated as active from clause-like text, desired-outcome wording, or stale issue-family state even when the factual fields denied any qualifying external event. In the Sales late-delivery clause-only scenario, that meant force majeure could leak beyond `clause_signals` into active issue surfaces such as `active_issue_tags`, `dispute_type`, risk rationale, suggested next steps, Markdown/JSON exports, and Evaluation Lab preview fields.

### Root cause

The active path was `extractFactualTriggers` -> `hasForceMajeureFactTrigger` -> `triggers.forceMajeure` -> `deriveActiveIssueTags`. The old force majeure fact trigger list mixed broad active terms with event/clause-like terms such as `government order`, `natural disaster`, `port closure`, `strike`, `war`, `impossibility`, and `uncontrollable event`. Desired-outcome text also participated in factual activation, so wording like whether a seller could rely on force majeure language could make `triggers.forceMajeure` look true before the family gate had a precise active/blocker model. Once `force majeure` reached `active_issue_tags`, `detectDisputeTypes` added `Force Majeure`, `scoreRisk` listed it in the active issue rationale, and force-majeure-specific issue/next-step templates became eligible.

### Trigger Model

Force majeure now has separate clause, active, and blocker trigger sets:

- Clause triggers are contract-text-only signals, including force majeure, natural disaster, government order, port closure, strike, war, emergency closure, pandemic/epidemic, widespread infrastructure outage, extraordinary external event, external uncontrollable event, act of God, external-event mitigation, and prompt written external-event notice language.
- Active triggers are factual-field-only signals. `shouldActivateForceMajeure(data)` requires either a real invocation/defense/notice or a specific qualifying external event segment tied to causation, prevention, closure, excusal, or qualification.
- Blocker triggers are factual-field-only negatives and ordinary-business explanations, including no force majeure notice, no qualifying external event, no government order, no natural disaster, no port closure, no strike, no war, no emergency closure, no widespread infrastructure outage, internal staffing shortage, ordinary raw-material/vendor backlog, ordinary supplier/vendor backlog, internal delay only, internal resource constraints, normal supply delay, and ordinary business difficulty.

### Blocker Precedence

`shouldActivateForceMajeure(data)` filters out blocked factual segments before looking for active force majeure support. If blockers are present and there is no clear, specific qualifying external event alleged in the factual fields, force majeure remains clause-signal-only. This blocks no-notice/no-event/internal-staffing/vendor-backlog fact patterns even when the desired outcome asks whether a party can rely on force majeure language.

### Files Inspected

- `docs/assets/app.js`
- `docs/playground/index.html`
- `tests/test_docs_site.py`
- `bug_audit.md`
- `pyproject.toml`

### Files Changed

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### Helper/Gate Functions Added Or Updated

- Added `hasForceMajeureClauseTrigger(contractText)`.
- Added `hasForceMajeureBlocker(data)`.
- Added `segmentIsForceMajeureQuestionOnly(segment)`.
- Added `segmentHasForceMajeureInvocation(segment)`.
- Added `segmentHasForceMajeureQualifyingEvent(segment)`.
- Added `shouldActivateForceMajeure(data)`.
- Updated `hasForceMajeureFactTrigger(data)` to delegate to the new gate.
- Updated `shouldActivateIssueFamily(...)` so the `force_majeure` family cannot activate unless `shouldActivateForceMajeure(data)` passes.

### Tests Added Or Updated

- Updated `SALES_FORCE_MAJEURE_CLAUSE_ONLY_FIXTURE` to include the Sales late-delivery clause-only facts with internal staffing shortages, ordinary raw-material/vendor backlog, no notice, and no qualifying external event.
- Strengthened `test_playground_force_majeure_clause_only_stays_clause_signal` for structured diagnosis, JSON `active_issue_tags`/`issue_tags`, Markdown active tags, risk rationale, suggested next steps, and Evaluation Lab consistency.
- Updated `test_playground_positive_force_majeure_still_activates` to verify Evaluation Lab positive force majeure behavior.
- Added `test_playground_force_majeure_blockers_win_over_desired_outcome_wording`.
- Added `test_playground_internal_staffing_and_vendor_backlog_are_not_force_majeure`.

### Commands Run And Results

| Command | Result | Summary |
| --- | --- | --- |
| `python -m pytest tests/test_docs_site.py -k "force_majeure or clause_active or evaluation_preview or exports_use_corrected"` | Passed | 13 passed, 36 deselected. |
| `node --check docs/assets/app.js` | Passed | Static playground JavaScript parses successfully. |
| `python -m pytest tests/test_docs_site.py` | Passed | 49 passed. |
| `python -m pytest` | Passed | 262 passed. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts/check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully. |

### Playwright Verification

Playwright verification was run after the code/tests passed. The static playground was served locally from `docs/`, and the Sales late-delivery force-majeure-negative fixture was filled in the browser. The smoke check passed: visible Active Issue Tags excluded force majeure, Clause Signals showed force majeure as clause-only, Markdown active tags excluded force majeure, JSON `active_issue_tags` and `issue_tags` excluded force majeure, Evaluation Lab `must_include_issues` excluded force majeure, and the generated case name was `sales_contract_delivery_golden`.

The first attempt to use the Bash wrapper hit Windows/WSL quoting/session instability, so the final successful smoke used the same `npx --package @playwright/cli playwright-cli` command path directly. Generated Playwright artifacts were removed after verification.

### Remaining Limitations Or Follow-Ups

The gate remains deterministic phrase matching, not semantic legal analysis. Contradictory facts with both a specific qualifying external event and broad negative wording are handled by the current blocker-precedence rule, but more nuanced party-position disputes may need additional fixture coverage if new examples appear.

## 2026-05-05 Force Majeure Blocker Follow-Up

### Symptom

The Sales Contract clause-only fixture could still surface force majeure outside `clause_signals` when the desired outcome mentioned force majeure notice or mitigation, even though the factual fields denied force majeure notice, government order, natural disaster, port closure, strike, war, emergency closure, extraordinary external event, and identified ordinary staffing/vendor backlog facts.

### Root cause

The exact active path was `deriveActiveIssueTags` -> `shouldActivateIssueFamily` -> `familyBlocked(data, family, activeTrigger)`. `familyBlocked` intentionally returned `false` whenever `activeTrigger` was truthy, so force majeure blockers were skipped after a phrase such as `force majeure notice` made `triggers.forceMajeure` true. A second visible leak came from `buildNextSteps`, which echoed `desiredOutcome` verbatim even when force majeure had been blocked from active tags.

### Files changed

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### Fix summary

- Added `hasFamilyBlocker(data, family)` and made `shouldActivateIssueFamily` always enforce it for `force_majeure`.
- Added `addDesiredOutcomeStep` so a blocked, inactive force majeure phrase in `desiredOutcome` is not reintroduced into suggested next steps.
- Kept force majeure clause detection intact; force majeure can still appear in `clause_signals`.

### Regression test

- Updated `test_playground_force_majeure_clause_only_stays_clause_signal` so the Sales fixture includes a desired-outcome force majeure phrase plus explicit negative facts.
- The test asserts force majeure remains clause-signal-only and is absent from `active_issue_tags`, `dispute_type`, risk rationale, suggested next steps, Evaluation Lab `case_name`, and Evaluation Lab `must_include_issues`.

### Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `python -m pytest tests\test_docs_site.py::test_playground_force_majeure_clause_only_stays_clause_signal` | Passed | 1 passed after the targeted fix. |
| `python -m pytest` | Passed | 260 passed in 20.94s on the final run. |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript parses successfully. |

### Remaining follow-ups

This was intentionally narrow. Other issue-family blockers still use the existing `familyBlocked(data, family, positiveTrigger)` behavior unless a concrete regression shows the same blocker-after-positive-trigger failure.

## 2026-05-05 Clause Signal vs Active Issue Separation

### Symptom

Contract clauses could be promoted into active disputes. A clause-only family could then flow through the final diagnosis into `active_issue_tags`, `dispute_type`, key issues, risk rationale, suggested next steps, Markdown/JSON exports, and Evaluation Lab `expected_outputs.must_include_issues`.

### Examples observed

- Force majeure clause-only false positive: a Sales Contract force majeure clause plus facts denying force majeure notice, government order, natural disaster, port closure, strike, war, emergency closure, and extraordinary external event could still be at risk of activating force majeure through broad factual matching.
- Invoice/payment false positive: invoice dates or invoice evidence, such as an alternative supplier invoice used to prove cover costs, could be treated as an invoice dispute even without an unpaid invoice, disputed invoice, billing dispute, or invoice nonpayment.
- Other clause-only families covered by regressions: confidentiality, indemnity, and liquidated damages now remain clause signals unless factual fields show an actual disclosure, tender/third-party claim, or liquidated-damages demand/penalty dispute.

### Root cause

The active-trigger layer did not have one explicit gate separating contract clause text from factual issue activation. `factText` included the selected dispute type, some active trigger lists included clause-like terms such as `invoice date` or generic `liquidated damages`, and `deriveActiveIssueTags` had repeated ad hoc checks instead of a shared issue-family activation rule. This allowed clause context or evidence labels to look like active disputes.

### Files inspected

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### Files changed

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### New helper/gate functions

- `activeTriggerText(data)` defines the factual activation source: desired outcome, dispute description, claimant position, respondent position, evidence, and metadata. It excludes contract text and the selected dispute type label.
- `shouldActivateIssueFamily(data, family, clauseSignals, activeTrigger, clausePhrases, options)` is the active issue gate used by `deriveActiveIssueTags`.

### Active triggers vs clause triggers

Clause triggers still come from `buildClauseSignals(data)` and may be detected from contract text alone. Active triggers now come from factual fields through `hasIssueFactTrigger` and family-specific helpers. A clause signal may support the analysis, but it does not by itself create an active issue tag.

### Blocker triggers

Blocker and negative terms remain in the issue-family registry and are evaluated against factual activation text. The force majeure registry now includes explicit blockers such as no force majeure notice, no government order, no natural disaster, no port closure, no strike, no war, no emergency closure, no extraordinary external event, and ordinary backlog/staffing-only facts. Confidentiality, indemnity, invoice dispute, and liquidated-damages blockers were tightened as well.

### Exports and Evaluation Lab

The prior final diagnosis source-of-truth path is preserved. Markdown, JSON, structured preview, risk rationale, suggested next steps, and Evaluation Lab preview still consume `finalDiagnosis`; because `active_issue_tags` is now filtered at the activation gate, clause-only families remain in `clause_signals` and do not appear in legacy `issue_tags` or Evaluation Lab `must_include_issues`.

### Regression tests added

- `test_playground_force_majeure_clause_only_stays_clause_signal`
- `test_playground_positive_force_majeure_still_activates`
- `test_playground_confidentiality_and_indemnity_clause_only_stay_clause_signals`
- `test_playground_liquidated_damages_requires_active_remedy_or_dispute`
- `test_playground_liability_limitation_active_when_damages_are_disputed`
- `test_playground_alternative_supplier_invoice_is_not_invoice_dispute`
- `test_playground_clause_active_separation_survives_sequential_runs`

### Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `Test-Path package.json` | Passed | Returned `False`; no npm project is present, so `npm test`, `npm run build`, `npm run lint`, and `npm run typecheck` are not applicable. |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript parses successfully. |
| `python -m pytest tests\test_docs_site.py` | Passed | 47 passed in 4.41s on the final focused docs-site run. |
| `python -m pytest` | Passed | 260 passed in 21.78s. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully. |
| `git diff --check` | Passed | No whitespace errors. |
| `git status --short` | Passed | Only `bug_audit.md`, `docs/assets/app.js`, and `tests/test_docs_site.py` are modified. |

### Results

- Clause text alone no longer creates active issue tags in the covered families.
- Force majeure positive facts still activate force majeure.
- Confidentiality and indemnity clause-only facts remain clause signals only.
- Liquidated damages activates when sought or contested, not from the clause alone.
- Liability limitation activates when damages/cap recovery is actually disputed.
- Alternative supplier invoice evidence does not activate invoice dispute or invoice-dispute timeline/gap templates.
- Cross-run regression coverage verifies a positive force majeure run does not leak active force majeure templates into a later clause-only run.

### Remaining follow-ups

This patch focuses on the clause-signal/active-issue separation layer for the issue families covered by the requested examples. Deeper semantic tuning may still be needed for less-covered families such as termination, audit rights, complex payment allocation, sales acceptance, or issue-specific jurisdictional nuances.

## 2026-05-05 Final Diagnosis Source-of-Truth Audit

### Symptom

Multiple playground output surfaces could diverge or reuse stale/pre-filtered diagnosis data. The risk display, suggested next steps, Markdown export, JSON export, structured preview, and Evaluation Lab preview all accepted diagnosis-shaped data, but there was no explicit final normalized diagnosis boundary that every output path was required to consume.

### Root cause

The static playground produced a diagnosis object after raw detection, but final filtering, compatibility aliases, risk rationale, next-step generation, export JSON assembly, and Evaluation Lab expected-output generation were not guarded by a single canonical normalization step. Several functions already consumed a passed diagnosis object, but they could still receive partially normalized fields or legacy aliases, and `render` assembled JSON inline instead of using a final-diagnosis export builder. `buildNextSteps` also preferred legacy camelCase aliases, which made it easier for stale or pre-final state to drive user-visible steps.

### Field-generation audit

| Field or surface | Canonical source after this patch |
| --- | --- |
| `contract_type` | `detectContractTypes` in `diagnose`, then normalized by `normalizeFinalDiagnosis`. |
| `dispute_type` | `detectDisputeTypes` in `diagnose`, then normalized from `dispute_types` by `normalizeFinalDiagnosis`. |
| `active_issue_tags` | `deriveActiveIssueTags` in `diagnose`, then deduplicated and filtered by `normalizeFinalDiagnosis`. |
| `issue_tags` | Legacy compatibility field created by `normalizeFinalDiagnosis`; it mirrors `active_issue_tags`. |
| `clause_signals` | `buildClauseSignals` in `diagnose`, then normalized by `normalizeFinalDiagnosis`. |
| `key_issues` | `buildIssues` receives the preliminary normalized diagnosis fields and is normalized into the final diagnosis. |
| `timeline_facts` | `extractTimelineFacts` in `diagnose`, then normalized by `normalizeFinalDiagnosis`. |
| `evidence_gaps` | `buildEvidenceGaps` in `diagnose`, then normalized by `normalizeFinalDiagnosis`. |
| Risk level | `scoreRisk` receives normalized active issues, evidence gaps, and timeline facts; `normalizeFinalDiagnosis` stores it in `risk.level`. |
| Risk rationale | `scoreRisk` builds it from final active issues, evidence gaps, and timeline facts before final normalization. |
| `critical_evidence_gaps` | `scoreRisk` produces them from normalized gaps, and `normalizeFinalDiagnosis` clones them under `risk`. |
| `suggested_next_steps` | `buildNextSteps(data, finalDiagnosis)` runs after risk/key issue normalization and is stored back into `finalDiagnosis`. |
| Structured diagnosis preview | `structuredPreview(finalDiagnosis)`. |
| Markdown report preview/export | `markdownReport(finalDiagnosis)`. |
| JSON-style output preview/export | `jsonReport(finalDiagnosis)`. |
| Evaluation Lab generated test preview | `buildEvaluationPreview(input, finalDiagnosis)`, which calls `computeEvaluationMetrics` and `buildTestCasePreview`. |
| Evaluation Lab `must_include_issues` | `buildTestCasePreview` copies from `finalDiagnosis.active_issue_tags`. |
| Evaluation Lab `must_include_evidence_gaps` | `buildTestCasePreview` copies from `finalDiagnosis.evidence_gaps`. |
| Evaluation Lab `risk_signal` | `buildTestCasePreview` copies from `finalDiagnosis.risk_signal`. |
| Evaluation Lab `case_name` | `caseNameFor` normalizes its diagnosis input and derives the name from final active issue tags only. |

### Files inspected

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### Files changed

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### How `finalDiagnosis` is produced

`diagnose` now runs raw deterministic detection first, then creates `finalDiagnosis` through `normalizeFinalDiagnosis`. Key issues and risk are generated from that normalized object, the object is normalized again, suggested next steps are generated from `finalDiagnosis`, and a final normalization pass returns the canonical result. This keeps raw signals upstream and makes the returned diagnosis the source of truth for all user-visible and export-visible fields.

### Output builders now consuming `finalDiagnosis`

- `render`
- `markdownReport`
- `jsonReport`
- `structuredPreview`
- `computeEvaluationMetrics`
- `buildTestCasePreview`
- `buildEvaluationPreview`
- `caseNameFor`

### Legacy compatibility

`normalizeFinalDiagnosis` preserves compatibility fields while making them canonical aliases. `issue_tags` is always a fresh clone of `active_issue_tags`, `relevant_clause_signals` mirrors `clause_signals`, `dispute_type` is derived from `dispute_types`, and `risk_signal` mirrors `risk.level`.

### Fresh per-run state

Every `diagnose` call creates a new `finalDiagnosis` object. `normalizeFinalDiagnosis` clones arrays and nested objects, removes empty strings, deduplicates values with stable ordering, and avoids mutating shared template/default arrays. Output builders normalize their input before rendering, so a caller cannot accidentally export a stale intermediate object.

### Tests added or updated

- Updated `_run_playground_diagnosis` to exercise the rendered copy/export path for Markdown, JSON, and Evaluation Lab generated test cases.
- Added `test_playground_final_diagnosis_is_source_for_json_and_markdown_exports`.
- Added `test_playground_evaluation_preview_uses_final_diagnosis`.
- Added `test_playground_no_post_final_regeneration_of_active_issues`.
- Added `test_playground_final_diagnosis_runs_have_fresh_state`.

### Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `Test-Path package.json` | Passed | Returned `False`; no npm project is present, so `npm install`, `npm test`, `npm run build`, `npm run lint`, and `npm run typecheck` are not applicable. |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript parses successfully. |
| `python -m pytest tests\test_docs_site.py` | Passed | 40 passed in 3.82s on the final focused docs-site regression run. |
| `python -m pytest` | Passed | 253 passed in 19.69s on the final full run. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully after the final `docs/assets/app.js` and audit edits. |
| `git diff --check` | Passed | No whitespace errors. |
| `git status --short` | Passed | Only `bug_audit.md`, `docs/assets/app.js`, and `tests/test_docs_site.py` are modified. |

### Results

- The returned `finalDiagnosis` is now the single source used by UI preview, Markdown export, JSON export, risk display, suggested next steps, and Evaluation Lab preview.
- JSON `issue_tags` mirrors `active_issue_tags` after final filtering.
- Markdown and JSON active issues, key issues, timeline facts, evidence gaps, and suggested next steps match the final diagnosis object.
- Evaluation Lab `expected_outputs.must_include_issues`, `must_include_evidence_gaps`, `risk_signal`, and case naming derive from the final diagnosis.
- Sequential diagnosis runs are covered by a regression test that checks arrays and generated text do not inherit stale values from a prior fixture.

### Remaining follow-ups

- This patch centralizes the diagnosis source of truth. It intentionally does not fully redesign semantic issue-family trigger gates.
- Force majeure, invoice dispute, lease, sales, SaaS/SLA, refund, indemnity, confidentiality, and IP trigger rules may still need separate semantic follow-up when a false positive or false negative comes from raw detection rather than post-final output construction.

## 2026-05-05 Playground Deterministic Diagnosis Bug Catalog and Verification

### Scope

- Area: static GitHub Pages playground diagnosis in `docs/assets/app.js`.
- Goal: keep clause signals separate from active issue tags, block denied force majeure facts, preserve lease-specific active issues, prevent stale template contamination, and keep UI, Markdown, JSON, and Evaluation Lab preview aligned with the final filtered diagnosis.
- Non-goals respected: no backend, no browser runtime network calls, no route/styling/navigation/sample-loading/copy-button/export-button changes, no external API dependencies, and no global deletion of issue families.

### Structured bug catalog

#### PG-DIAG-001: force majeure false positive

- Symptom: a contract containing a force majeure clause could produce an active `force majeure` issue even when facts denied government orders, natural disasters, strikes, war, or other external uncontrollable events.
- Root cause: clause terms and factual invocation terms were previously too easy to conflate.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: force majeure remains a clause signal unless non-blocked facts invoke an external event; blocker triggers run before active issue generation.
- Tests: `test_playground_force_majeure_clause_signal_is_not_active_issue`, `test_playground_late_delivery_blocks_denied_force_majeure_issue`, and positive force-majeure tests.

#### PG-DIAG-002: clause signal vs active issue separation

- Symptom: clause-only concepts such as indemnity, confidentiality, force majeure, SLA, refund, or liquidated damages could leak into active issue tags and downstream previews.
- Root cause: issue-family detection mixed contract clause terms, dropdown/default categories, and fact terms.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: active triggers, clause triggers, negative triggers, and blocker terms are evaluated separately; `issue_tags` mirrors final filtered `active_issue_tags`.
- Tests: static playground structured-output, export, refund, confidentiality/IP, force-majeure, and lease tests.

#### PG-DIAG-003: missing lease active issues

- Symptom: the lease repair / notice / rent abatement / security deposit fixture could miss repair obligation, rent abatement, rent withholding/payment default, security deposit, tenant-caused damage, property damage causation, damages, and liability limitation.
- Root cause: the issue-family registry lacked lease-specific active and clause gates.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: lease maintenance, rent abatement, rent withholding, security deposit, tenant damage, and property-damage causation families are detected through lease-specific fact and clause signals.
- Tests: `test_playground_lease_repair_abatement_filters_false_issue_families`.

#### PG-DIAG-004: stale key issue and next-step template contamination

- Symptom: unrelated SaaS, SLA, invoice, refund, force majeure, indemnity, confidentiality, IP, liquidated-damages, cover-cost, and lost-revenue boilerplate could appear in lease output.
- Root cause: generic output builders ran after broad tags had been activated or when no scoped family branch existed.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: lease, force-majeure, refund/termination/acceptance, and confidentiality/IP branches return scoped key issues, evidence gaps, next steps, and risk rationale from final active tags.
- Tests: lease key issue, next-step/export, refund, confidentiality/IP, positive force-majeure, and cross-contamination tests.

#### PG-DIAG-005: timeline role classification

- Symptom: timeline output could fall back to generic notice/deemed-receipt text instead of classifying dated facts by role.
- Root cause: generic notice extraction did not know lease, refund, force majeure, and confidentiality/IP roles.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: timeline extractors classify dates as tenant notice, landlord response, contractor inspection, rent withholding, repair completion, move-out/surrender, force-majeure order/notice, refund milestones, and confidentiality/IP events.
- Tests: lease, refund, positive force majeure, and confidentiality/IP timeline assertions.

#### PG-DIAG-006: Evaluation Lab preview contamination

- Symptom: generated test-case previews could be named or populated from stale/default/unfiltered state.
- Root cause: previews needed to derive `case_name` and `must_include_issues` from the final filtered diagnosis; export readiness also referenced module-level latest export strings.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: preview expected issues use `diagnosis.active_issue_tags`; case naming uses filtered tags; export readiness now derives from the current diagnosis object rather than `latestMarkdown`/`latestJson`.
- Tests: lease, confidentiality/IP, export consistency, and cross-contamination preview assertions.

#### PG-DIAG-007: Markdown/JSON export consistency

- Symptom: Markdown, JSON, UI diagnosis, and Evaluation Lab preview could diverge if one path used stale or unfiltered fields.
- Root cause: legacy aliases and preview state needed to point at the final diagnosis object.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: `active_issue_tags`, legacy `issue_tags`, key issues, clause signals, evidence gaps, timeline facts, risk rationale, and suggested next steps are copied from the final filtered diagnosis for export paths.
- Tests: SaaS, late-delivery force-majeure-negative, positive force-majeure, refund, confidentiality/IP, and lease export parity tests.

#### PG-DIAG-008: cross-run stale state prevention

- Symptom: running a force-majeure, SaaS/SLA, refund, or confidentiality/IP fixture before the lease fixture could leak prior issue templates.
- Root cause: shared browser module state and mutable output arrays needed stronger isolation from per-run diagnosis data.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: each diagnosis builds fresh arrays and clones legacy aliases; Evaluation Lab previews derive from the passed diagnosis.
- Tests: `test_playground_diagnosis_runs_do_not_cross_contaminate_issue_templates`.

#### PG-DIAG-009: exact lease fixture literals in generated evidence gaps

- Symptom: lease evidence gaps still included `September 4` and `$8,500` as literal fallback text.
- Root cause: the lease evidence-gap branch had fixture-specific strings instead of using extracted notice date and deposit amount values.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: notice date, email label, repair cure period, deposit deduction amount, and deposit statement period now come from `extractLeaseTimeline`; the `September 4` trigger literal was replaced with generic repair/maintenance/tenant notice triggers.
- Tests: added `test_playground_lease_evidence_gaps_use_extracted_values_not_fixture_literals`.

### Files changed in this pass

- `docs/assets/app.js`
  - Generalized lease evidence-gap labels to use extracted values rather than fixed fixture literals.
  - Removed the hard-coded `september 4 notice` trigger in favor of generic repair, maintenance, and tenant notice signals.
  - Made Evaluation Lab export readiness derive from the current diagnosis object rather than stale module-level export strings.
- `tests/test_docs_site.py`
  - Added a lease regression variant that changes dates and the security-deposit deduction amount and asserts generated outputs follow the new values.
- `bug_audit.md`
  - Added this structured catalog and current verification record.

### Commands run and results

| Command | Result | Notes |
| --- | --- | --- |
| `Test-Path package.json` | Passed, returned `False` | No npm project is present, so `npm install`, `npm test`, `npm run build`, `npm run lint`, and `npm run typecheck` are not applicable. |
| `Test-Path mkdocs.yml` | Passed, returned `True` | Strict MkDocs build command exists in repo context. |
| `Test-Path scripts\check_docs_links.py` | Passed, returned `True` | Static docs link checker exists. |
| `Test-Path tests` | Passed, returned `True` | Pytest suite exists. |
| `git diff --check` | Passed | No whitespace errors after the production and test patches. |
| `node --check docs\assets\app.js` | Blocked by approval timeout | Attempted twice; automatic permission approval review did not finish before its deadline. |
| `python -m pytest tests\test_docs_site.py` | Blocked by approval timeout | Attempted before and after patching; automatic permission approval review did not finish before its deadline. |
| `python -m pytest` | Blocked by approval timeout | Attempted twice; automatic permission approval review did not finish before its deadline. |
| `python -m compileall -q contract2agent tests scripts` | Blocked by approval timeout | Attempted twice; automatic permission approval review did not finish before its deadline. |
| `python scripts\check_docs_links.py` | Blocked by approval timeout | Attempted twice; automatic permission approval review did not finish before its deadline. |
| `python -m mkdocs build --strict` | Blocked by approval timeout | Attempted twice; automatic permission approval review did not finish before its deadline. |

### Verification results

- Verified by diff inspection that only `docs/assets/app.js`, `tests/test_docs_site.py`, and `bug_audit.md` are modified.
- Verified by `git diff --check` that the patch has no whitespace errors.
- Verified by source inspection that lease evidence-gap dates and dollar amounts are derived from extracted values rather than unconditional fixture literals.
- Full executable verification is still pending because Python and Node execution approval timed out in this session.

### Remaining limitations and follow-ups

- The playground remains a deterministic static analyzer and depends on explicit textual triggers.
- Business-day arithmetic is still described as an evidence-dependent calculation rather than computed.
- Re-run `node --check docs\assets\app.js`, `python -m pytest tests\test_docs_site.py`, `python -m pytest`, `python -m compileall -q contract2agent tests scripts`, `python scripts\check_docs_links.py`, and `python -m mkdocs build --strict` in an environment where command execution is approved.

## 2026-05-04 Lease Repair / Rent Abatement / Security Deposit Trigger-Gate Follow-Up

### 1. What was wrong

- The deterministic playground analyzer still handled a lease repair dispute through generic notice/cure, damages, invoice/payment, SaaS/SLA, and force-majeure template paths.
- A force majeure clause mention plus negative fact text could still contaminate active issue outputs, dispute type, key issues, next steps, Evaluation Lab preview, and exports.
- Lease-specific facts for roof repair, rent abatement, rent withholding, security deposit deductions, tenant-caused damage, property-damage causation, and base-rent liability limits were under-detected.

### 2. Root cause

- Clause signals and factual issue activation were still not separated for the lease family.
- Existing issue-family gates covered prior SaaS, refund, force majeure, and confidentiality/IP regressions, but there was no lease issue-family registry or lease-specific generation path.
- The generic notice/cure branch assumed invoice, suspension, order-form, or service-platform context.
- The generic damages branch could emit lost-revenue wording whenever damages exclusions appeared, even when the facts requested display-fixture damages, rent abatement, deposit return, and repair-related remedies.
- Evaluation Lab case naming used filtered active tags, but without a lease-specific case-name path it could still choose misleading generic families when active tags were wrong.

### 3. Why force majeure was incorrectly activated

- The contract contained a force majeure clause, and the fixture's negative sentence listed government orders, natural disasters, strikes, war, and force majeure events.
- The correct behavior is clause-only: those terms are clause signals unless a party invokes force majeure, sends force-majeure notice, or claims delay/nonperformance was caused by an external uncontrollable event.
- The fix keeps force majeure as `force majeure clause mentioned but not fact-triggered` and relies on blocker triggers to prevent active issue, dispute type, key issue, next-step, Evaluation Lab, and export activation.

### 4. Why lease-specific issues were missing

- There were no explicit lease-family gates for landlord maintenance, commercially reasonable repairs, rent abatement, unauthorized rent withholding/payment default, security deposit deductions, ordinary wear and tear, tenant-caused damage, or property-damage causation.
- Rent withholding was too easy to confuse with generic payment/invoice disputes, even though lease rent withholding is not an invoice dispute.
- Liability-cap extraction did not preserve the lease-specific `twelve months of base rent` language.

### 5. Trigger-gate changes

- Added lease issue families in `docs/assets/app.js`:
  - `lease_maintenance`
  - `rent_abatement`
  - `rent_withholding`
  - `security_deposit`
  - `tenant_damage`
- Added lease factual trigger helpers for:
  - lease maintenance / repair obligation
  - rent abatement
  - rent withholding / payment default
  - security deposit
  - tenant-caused damage
  - property damage causation
- Added clause signals for lease schedule notice addresses, email plus certified mail notice, 10-business-day repair cure period, commercially reasonable repairs, rent abatement by affected period/area, unauthorized rent withholding as payment default, deposit deductions, itemized deposit statement timing, ordinary wear and tear, base-rent liability cap, and unpaid-rent / intentional-misconduct / tenant-caused-property-damage carve-outs.
- Kept rent withholding separate from generic `payment` and `invoice dispute` active tags.

### 6. Timeline role classification

- Added lease timeline extraction for:
  - September 3 water-intrusion discovery.
  - September 4 tenant email notice.
  - September 7 landlord response.
  - September 15 roof contractor inspection.
  - October rent withholding.
  - October 12 roof repair completion.
  - November 1 move-out / surrender.
  - 30-day deposit statement deadline.
  - 10-business-day repair cure period.
  - email plus certified-mail deemed receipt rule.
- The lease path returns role-specific timeline facts instead of falling through to generic notice/deemed-receipt text.

### 7. Key issues, gaps, next steps, and risk

- Added lease-specific key issues for notice method, lease schedule address, deemed receipt, cure period, commercially reasonable repair start, September 15 inspection, October 12 completion, material interference, rent abatement, 40% October rent withholding, $8,500 deposit deduction, roof-leak versus tenant-misuse causation, itemized statement timing, display-fixture damages, and the base-rent liability cap/carve-outs.
- Added lease-specific evidence gaps and prevented signed-contract, invoice, SLA, integration-log, indemnity, IP-comparison, and lost-revenue gaps from being added to the lease branch.
- Added lease-specific next steps and prevented invoice/suspension/SaaS/force-majeure/refund/indemnity/IP boilerplate from running.
- Added lease-specific risk rationale and avoided generic suspension/termination wording in the lease risk rationale.

### 8. Evaluation Lab and exports

- Evaluation Lab preview now names the fixture `lease_repair_notice_abatement_deposit_golden`.
- `must_include_issues` comes from final filtered `active_issue_tags`.
- Markdown and JSON exports already used the final diagnosis object; the new tests assert active tags, key issues, clause signals, evidence gaps, risk rationale, timeline facts, suggested next steps, and legacy `issue_tags` match the filtered diagnosis.

### 9. Files changed

- `docs/assets/app.js`
  - Added lease issue-family registry entries, factual triggers, clause signals, lease timeline extraction, lease key issues, lease evidence gaps, lease next steps, lease risk rationale, lease dispute types, and lease Evaluation Lab case naming.
- `tests/test_docs_site.py`
  - Added the Lease repair / rent abatement / security deposit fixture.
  - Added regression assertions for active tags, forbidden issue families, clause-only force majeure, fact-specific key issues, role-classified timeline facts, evidence gaps, lease-specific next steps, Evaluation Lab preview, Markdown/JSON export parity, and cross-run contamination.
- `bug_audit.md`
  - Added this audit entry.

### 10. Tests added or updated

- `test_playground_lease_repair_abatement_filters_false_issue_families`
- `test_playground_lease_repair_key_issues_timeline_and_gaps_are_fact_specific`
- `test_playground_lease_repair_next_steps_preview_and_exports_are_scoped`
- Extended `test_playground_diagnosis_runs_do_not_cross_contaminate_issue_templates` to run the lease fixture after force majeure, SaaS/SLA, refund, and confidentiality/IP fixtures.

### 11. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `Test-Path package.json` | Passed | Returned `False`; no npm package file exists, so npm install/test/build/lint/typecheck scripts are not applicable. |
| `git diff --check` | Passed | No whitespace errors in the patch. |
| `node --check docs\assets\app.js` | Blocked by approval timeout | Attempted more than once; the automatic permission approval review did not finish before its deadline. |
| `python -m pytest tests\test_docs_site.py -q` | Blocked by approval timeout | Attempted; the automatic permission approval review did not finish before its deadline. |
| `python -m pytest` | Blocked by approval timeout | Attempted; the automatic permission approval review did not finish before its deadline. |
| `python -m compileall -q contract2agent tests scripts` | Blocked by approval timeout | Attempted; the automatic permission approval review did not finish before its deadline. |
| `python scripts\check_docs_links.py` | Blocked by approval timeout | Attempted; the automatic permission approval review did not finish before its deadline. |
| `python -m mkdocs build --strict` | Blocked by approval timeout | Attempted; the automatic permission approval review did not finish before its deadline. |

### 12. Build/test results

- `git diff --check` passed.
- The repository has no `package.json`, so npm commands are not present.
- Node, pytest, compileall, docs-link, and MkDocs verification could not be executed in this session because executable commands requiring escalation timed out in the approval reviewer.
- The static playground route remains `docs/playground/index.html`, preserving the GitHub Pages `/Contract2Agent/playground/` path. No backend, runtime network call, route, sample loading, export button, copy button, styling, navigation, or unrelated UI change was added.

### 13. Remaining limitations

- The playground remains a deterministic static analyzer. It now has lease-specific trigger gates and blockers, but still depends on explicit textual signals.
- Exact business-day date arithmetic is still described as evidence-dependent rather than computed.
- Full executable verification should be rerun in an environment where `node`, `pytest`, `compileall`, `check_docs_links.py`, and `mkdocs build --strict` are approved.

## 2026-05-04 Confidentiality / IP Indemnity Trigger-Gate Follow-Up

### 1. What was wrong

- The playground diagnosis engine could still let stale/default issue-family templates contaminate an unrelated confidentiality and IP indemnity case.
- A Service Agreement involving public confidential-information exposure, third-party IP demand, indemnity notice, damages, and liability-cap carve-outs could incorrectly receive SaaS, payment, invoice, refund, delivery, force-majeure, SLA, suspension, liquidated-damages, and cover-cost concepts.
- Evaluation Lab generated test-case previews could use active issues from broad selected/default dispute categories instead of the final filtered diagnosis.

### 2. Root cause

- Issue families were still triggered by broad substring and dropdown/default signals before factual trigger gates and negative facts were applied.
- Clause signals, selected dispute type, and fact terms were not consistently separated. Examples:
  - `software` matched the short force-majeure trigger `war`.
  - a negative statement such as `No party claims ... service credits` could still support SaaS classification.
  - `delivered under the project` could be confused with an active late-delivery dispute.
- Template generation for key issues, evidence gaps, timeline facts, next steps, risk, and Evaluation Lab preview did not have a confidentiality/IP indemnity scoped path.

### 3. Evidence of template contamination

- The reported fixture should focus on May 3 public workspace disclosure, May 6 customer discovery, May 8 removal, May 10 third-party IP demand, May 12 indemnity notice, 3-business-day unauthorized-disclosure notice, 10-day indemnity notice, and twelve-month cap carve-outs.
- The stale output instead included refund-calculation, performed-vs-unperformed services, invoice-date, force-majeure notice, migration deadline, temporary consultant, liquidated-damages, SLA/uptime, service-credit, and suspension terms from other playground fixtures.
- The generated test-case preview used payment/refund/default golden state rather than current final active issues.

### 4. Fix

- Added an issue-family registry in `docs/assets/app.js` with active triggers, clause triggers, negative triggers, and blocker terms for payment, invoice dispute, refund, force majeure, confidentiality, indemnity, delivery, SLA, suspension, liquidated damages, and cover costs.
- Added segment-level blocker filtering so negative facts such as `No party claims unpaid invoices`, `No party claims refunds`, `No party claims SLA downtime`, and `No party claims government order` block inactive families unless a separate positive factual trigger exists.
- Tightened contract-type detection so `Service Agreement` is not upgraded to `SaaS Agreement` unless contract text or non-blocked facts contain SaaS-specific support.
- Added confidentiality/IP indemnity timeline extraction, key-issue generation, evidence-gap generation, and next-step generation tied to active confidentiality, unauthorized disclosure, indemnity, third-party IP, damages, liability limitation, and liability-cap carve-out tags.
- Added clause signals for unauthorized-disclosure notice timing, indemnity notice timing, defense control / settlement consent, confidentiality carve-outs, and indemnity carve-outs while keeping force majeure clause-only when not fact-triggered.
- Made Evaluation Lab previews derive `case_name`, `must_include_issues`, and `must_include_evidence_gaps` from the final filtered diagnosis object.
- Cloned diagnosis arrays before assigning legacy aliases so `issue_tags` mirrors `active_issue_tags` without reusing stale mutable output arrays.

### 5. Files changed

- `docs/assets/app.js`
  - Added trigger-gated issue-family registry and blockers.
  - Added confidentiality/IP indemnity fact triggers, timeline extraction, key issues, evidence gaps, next steps, dispute types, and preview generation.
  - Tightened SaaS, force-majeure, delivery, refund, payment, SLA, suspension, and export alias behavior.
- `tests/test_docs_site.py`
  - Added the confidentiality/IP indemnity regression fixture.
  - Added tests for active issue filtering, dispute type filtering, clause signals, role-classified timeline facts, key issues, evidence gaps, next steps, Evaluation Lab preview, export parity, and sequential cross-contamination.
- `bug_audit.md`
  - Added this audit entry.

### 6. Tests added

- `test_playground_confidentiality_ip_indemnity_filters_false_issue_families`
- `test_playground_confidentiality_ip_clauses_issues_and_timeline`
- `test_playground_confidentiality_ip_gaps_next_steps_preview_and_exports_are_scoped`
- `test_playground_diagnosis_runs_do_not_cross_contaminate_issue_templates`

### 7. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript syntax is valid. |
| `python -m pytest tests\test_docs_site.py -q` | Passed | 32 passed in 2.06s. |
| `python -m pytest` | Passed | 245 passed in 20.51s. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully in 0.97s. |
| `Test-Path package.json` | No package file | No npm `test`, `build`, `lint`, or `typecheck` scripts are present to run. |

### 8. Build/test result

- The static playground route remains `docs/playground/index.html`, preserving the GitHub Pages `/Contract2Agent/playground/` path.
- Markdown and JSON exports now use the same final filtered diagnosis object shown in the UI.
- Legacy `issue_tags` mirrors filtered `active_issue_tags`.
- Sequential same-process playground runs no longer leak refund, force-majeure/migration, liquidated-damages, cover-cost, SLA/uptime, service-credit, suspension, invoice, or payment templates into the later confidentiality/IP diagnosis.

### 9. Remaining limitations

- The playground remains a deterministic browser-side analyzer. It now uses stricter trigger gates and blockers, but still depends on explicit text signals and nearby date context rather than legal NLP or a backend.
- The issue-family registry is intentionally conservative; ambiguous facts may remain `unclear` or clause-only until the user provides stronger factual triggers.

## 2026-05-04 Refund / Termination / Acceptance Template Contamination Follow-Up

### 1. Remaining issue

- The prior force-majeure follow-up fixed clause-only force majeure handling, but a refund / termination / acceptance case still received unrelated active issue families and stale templates.
- The analyzer could incorrectly:
  - activate `indemnity` when the facts expressly denied any third-party IP or infringement claim.
  - activate or signal `confidentiality` because substring matching treated `non-refundable` as containing `nda`.
  - convert a prepaid-fee refund dispute into `Payment/Invoice Dispute`.
  - generate unpaid-invoice, suspension, service-credit, stale delivery, and lost-revenue wording.
  - classify March 28 as rejection context and April 2 as a delivery-delay notice instead of provider partial delivery and customer breach notice.

### 2. Root cause

- Active issue tags still relied on broad keyword groups and clause mentions instead of factual invocation.
- Invoice-dispute detection treated generic fee/refund disputes as invoice disputes.
- Indemnity and confidentiality lacked required factual triggers and negative context guards.
- Timeline and next-step generation did not have a scoped refund / termination / acceptance path, so generic payment, suspension, and delivery templates could leak.

### 3. Files changed

- `docs/assets/app.js`
  - Added factual trigger guards for invoice disputes, indemnity, and confidentiality.
  - Kept indemnity and force majeure as clause-only signals when not fact-triggered.
  - Added refund / prepaid-fee / acceptance-rejection active tags separate from payment and invoice disputes.
  - Added refund / termination / acceptance timeline extraction for payment, milestones, delivery, breach notice, response, termination, cure period, and rejection period.
  - Added scoped key issues, evidence gaps, and suggested next steps for refund / prepaid-fee / acceptance disputes.
  - Removed service-credit wording from risk/contested-fact rationale unless service-credit is actually active.
  - Fixed `nda` substring contamination from `non-refundable`.
- `tests/test_docs_site.py`
  - Added a refund / termination / acceptance regression fixture.
  - Added tests for active tag filtering, clause-only signals, case-specific key issues, timeline role classification, evidence gaps, next steps, and Markdown/JSON exports.
- `bug_audit.md`
  - Added this follow-up note.

### 4. Tests added

- `test_playground_refund_termination_filters_false_positive_issue_families`
- `test_playground_refund_termination_clause_signals_are_clause_only_scoped`
- `test_playground_refund_termination_key_issues_and_timeline_are_case_specific`
- `test_playground_refund_termination_gaps_next_steps_and_exports_are_scoped`

### 5. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript syntax is valid. |
| `python -m pytest tests\test_docs_site.py -q` | Passed | 28 passed in 1.30s on the final focused run. |
| `python -m pytest` | Passed | 241 passed in 21.96s. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully in 0.69s. |
| `Test-Path package.json` | No package file | No npm install/test/build/lint/typecheck scripts are present in this repository. |

### 6. Build/test result

- The static playground and `/Contract2Agent/playground/` route remain covered by the existing docs tests and MkDocs strict build.
- No backend, runtime network call, route, sample-loading, export-button, styling, or unrelated UI change was added.
- The refund / termination / acceptance fixture now:
  - excludes indemnity, confidentiality, force majeure, SLA, service credit, suspension, and invoice dispute from active issue tags.
  - keeps indemnity and force majeure as clause-only signals when not fact-triggered.
  - separates refund and prepaid-fee analysis from invoice-dispute analysis.
  - produces case-specific key issues, evidence gaps, timeline facts, suggested next steps, and Markdown/JSON exports.

### 7. Remaining limitations

- The playground remains deterministic and text-pattern based. It now filters each issue family more narrowly, but it still depends on reasonably explicit dates, amounts, clause names, and factual descriptions in the user input.
- No static reference pack was added in this follow-up; the fix stayed inside the existing checked-in static analyzer.

## 2026-05-04 Force Majeure Template Contamination Follow-Up

### 1. Remaining bug

- A positive force-majeure Service Agreement late-delivery case correctly activated force majeure and produced non-low risk, but unrelated SaaS/SLA/payment/suspension templates still leaked into the diagnosis.
- The analyzer could add:
  - `SLA` active issue tags.
  - `SLA/Service Credit` dispute type.
  - SLA/uptime key issues and service-credit next steps.
  - payment timing and suspension clause signals from generic service or fee language.
  - incorrect liquidated-damages cap text because percentage extraction split decimal percentages and selected the wrong percent.
  - lumped notice dates instead of classifying force-majeure dates by event role.

### 2. Root cause

- Template family selection was still too broad:
  - generic `service` words could activate SaaS/SLA logic.
  - generic `fees` language inside liability caps could activate payment timing clause signals.
  - notice and delivery templates were not filtered for force-majeure-specific notice/delay cases.
  - liquidated damages extraction reused a generic first-percent helper and did not preserve both the weekly rate and cap.
  - timeline extraction had no force-majeure event roles.

### 3. Files changed

- `docs/assets/app.js`
  - Tightened active SLA/service-credit selection so it requires explicit SLA/uptime/downtime/service-credit triggers and matching contract clause signals.
  - Tightened payment timing clause detection so fee-cap language does not imply payment timing.
  - Added force-majeure timeline extraction for government order, awareness, force-majeure notice, migration deadline, consultant cover cost, partial completion, and final completion dates.
  - Added liquidated-damages term extraction for rate, unit, and cap.
  - Added force-majeure-specific key issues and next steps.
  - Guarded delivery/notice/cure templates so force-majeure notice cases do not receive invoice/cure/suspension/SLA boilerplate.
- `tests/test_docs_site.py`
  - Added a positive force-majeure Service Agreement fixture.
  - Added regression tests for active tags, forbidden SaaS/SLA leakage, clause signals, case-specific key issues, timeline role classification, scoped next steps, and Markdown/JSON exports.
- `bug_audit.md`
  - Added this follow-up note.

### 4. Tests added

- `test_playground_positive_force_majeure_avoids_saas_template_leakage`
- `test_playground_positive_force_majeure_clauses_issues_and_timeline`
- `test_playground_positive_force_majeure_next_steps_and_exports_are_scoped`

### 5. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript syntax is valid. |
| `python -m pytest tests\test_docs_site.py -q` | Passed | 24 passed in 0.74s on the final focused run. |
| `python -m pytest` | Passed | 237 passed in 18.98s. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully in 0.53s. |

### 6. Build/test result

- The static playground still builds through MkDocs.
- No backend, runtime network call, route, sample-loading, export-button, or styling change was added.
- The positive force-majeure fixture now:
  - includes force majeure as an active issue.
  - excludes SLA, service credit, suspension, invoice, uptime, downtime, support-ticket, and customer-side integration concepts when unsupported by the fixture.
  - extracts the liquidated damages rate as `1.5% per full week` and cap as `12%`.
  - classifies June 20, June 21, June 28, June 30, July 18, July 20, and August 5 by event role.
  - exports corrected structured Markdown and JSON.

## 2026-05-04 Playground Delivery Follow-Up Fix

### 1. Previous partial fix result

- The first playground diagnosis-quality fix separated the main structured fields and made the SaaS notice/cure fixture risk non-low.
- It still left a visible late-delivery failure mode:
  - explicit denial of external-event causation could still activate force majeure because the same sentence contained trigger words such as natural disaster, government order, strike, war, and external uncontrollable event.
  - late-delivery key issues still fell back to broad delivery/liability templates when enough dated delivery, cure, rejection, defect, and damages facts were available.
  - the result header still combined contract/dispute type badges with active issue tags, making the conceptual separation less visible.

### 2. Remaining bug and root cause

- Root cause:
  - force majeure trigger detection looked for positive trigger phrases before understanding sentence-level denial context.
  - delivery-specific dates and remedy terms were not extracted into a delivery timeline shape before key issue generation.
  - the rendered detected badge list grouped type labels and active issue tags together.
- Corrected behavior:
  - active force majeure now requires factual invocation and is blocked when the facts explicitly deny force majeure or external uncontrollable event causation.
  - clause-only force majeure remains available as `force majeure clause mentioned but not fact-triggered`.
  - late-delivery key issues now use extracted delivery milestone, actual delivery, notice, cure, revised package, rejection, review-period, API defect, liquidated-damages, lost-revenue, and liability-cap facts when present.

### 3. Files changed

- `docs/assets/app.js`
  - Added sentence-level external-event denial detection for force majeure.
  - Added delivery timeline extraction helpers for milestone, delivery, delay notice, revised package, rejection, review period, liquidated damages cap, API mapping defects, lost revenue exclusion, and liability cap period.
  - Updated delivery/notice/cure/damages/liability key issue generation to prefer fact-specific issues.
  - Split the rendered detected type badges from active issue tags so clause-only signals do not appear in the active tag list.
- `tests/test_docs_site.py`
  - Added a late-delivery regression fixture with the explicit negative force-majeure context.
  - Added tests for active issue tags, clause signals, fact-specific key issues, and Markdown/JSON export separation.
- `bug_audit.md`
  - Added this follow-up note.

### 4. Tests added

- `test_playground_late_delivery_blocks_denied_force_majeure_issue`
- `test_playground_late_delivery_key_issues_are_fact_specific`
- `test_playground_late_delivery_exports_keep_force_majeure_clause_only`

### 5. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript syntax is valid. |
| `python -m pytest tests\test_docs_site.py -q` | Passed | 21 passed in 0.78s. |
| `python -m pytest` | Passed | 234 passed in 21.43s. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully in 0.55s. |

### 6. Build/test result

- The static playground still builds through MkDocs.
- No backend, runtime network call, route, sample-loading, export-button, or styling change was added.
- The late-delivery fixture now keeps force majeure out of `active_issue_tags`, retains it only in `clause_signals`, and exports the corrected separation in Markdown and JSON.

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
  - `clause_signals`: includes force majeure as a not fact-triggered clause signal
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
