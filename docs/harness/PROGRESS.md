# Harness Progress

Use this file as the append-only work log for agent sessions. Record commands,
results, and follow-up risks without relying on chat history.

## 2026-05-06 - Harness Bootstrap

### Sprint Contract

- Goal: create a repo-local agent-first development harness, documentation
  system of record, project-scoped Codex agent configs, and minimal validation
  scripts.
- Scope: documentation, `.codex/` config, module README files, and
  `scripts/harness/`.
- Out of scope: production application logic changes, project rename, broad
  refactors, production dependency additions, GitHub Pages runtime backend.
- Done means:
  - `AGENTS.md` is short and points to docs.
  - Required docs and harness files exist.
  - Major source/test directories have README files.
  - Harness scripts exist and call existing commands.
  - Validation results are recorded here and in `docs/AGENT_HANDOFF.md`.

### Baseline Inspection

| Command | Result |
| --- | --- |
| `pwd` | `D:\Projects\Contract2Agent` |
| `git status --short` | Clean before edits |
| `rg --files` | Failed with `Access is denied`; used `git ls-files` fallback |
| `python -m pytest` | 355 passed in 65.94s |

### Read-Only Subagent Findings

- `codebase_mapper`: mapped package layout, CLI entry points, docs, tests,
  examples, scripts, and noted that existing `AGENTS.md` was too large.
- `feature_inventory_agent`: produced existing feature list and evidence for
  the initial feature registry.
- `test_inventory_agent`: confirmed pytest as the safest full test command and
  listed optional compile/docs/MkDocs gates.
- `docs_inventory_agent`: identified missing system-of-record docs, useful
  module READMEs, and harness doc placement.

### Implementation Log

- Replaced the oversized root `AGENTS.md` with a short operating contract that
  points future agents to repository docs.
- Added system-of-record docs under `docs/`: project context, architecture,
  codemap, golden principles, decisions, and handoff.
- Added harness docs under `docs/harness/`: overview, schema, feature registry,
  progress log, quality gates, eval matrix, sprint contract template, and
  runbook.
- Added module README files for major source, test, and script directories.
- Added project-scoped Codex config and custom agent role files under `.codex/`.
- Added minimal harness scripts under `scripts/harness/`.
- Updated `mkdocs.yml` to include the new repository/harness docs while
  excluding only root `docs/README.md` from site generation to avoid the
  MkDocs `index.md` conflict.
- No application business logic was changed.

### Validation Log

| Command | Result |
| --- | --- |
| `bash scripts/harness/doctor.sh` | Passed after a portability fix; printed project root, git status, detected commands, package entry points, and harness docs status. WSL emitted a non-fatal localhost/NAT warning in this environment. |
| `python scripts/harness/validate_docs.py` | Passed: validated 16 required docs, 10 module READMEs, AGENTS length, and feature registry shape. |
| `python -m compileall -q contract2agent tests scripts` | Passed. |
| `python scripts/check_docs_links.py` | Passed: checked 59 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Initially failed because `docs/README.md` conflicted with `docs/index.md`; passed after narrowing `exclude_docs` to `/README.md`. |
| `python -m pytest` | Passed: 355 tests passed in 47.25s after changes. |

### Current Git Status Snapshot

As of the handoff update, the expected changed paths are:

- Modified: `AGENTS.md`, `mkdocs.yml`
- Added/untracked: `.codex/`, module README files, `docs/AGENT_HANDOFF.md`,
  `docs/ARCHITECTURE.md`, `docs/CODEMAP.md`, `docs/DECISIONS.md`,
  `docs/GOLDEN_PRINCIPLES.md`, `docs/PROJECT_CONTEXT.md`, `docs/README.md`,
  `docs/harness/`, `scripts/README.md`, `scripts/harness/`, `tests/README.md`

## 2026-05-07 - Docs/Harness Bootstrap Refresh

### Scope

- Approved task: create or update core documentation and harness bootstrap files only.
- Allowed write set: docs system-of-record files and `docs/harness/` files named by the task.
- Out of scope: source code, tests, examples, root README, AGENTS, package files, lockfiles, CI/config files, scripts, fixtures, generated files, sprint contracts, staging, commits, resets, deletes, renames, installs, tests, builds, formatters, and doc generators.

### Baseline Inspection

| Command | Result |
| --- | --- |
| `Get-Location` | `D:\Projects\Contract2Agent` |
| `git branch --show-current` | `main` |
| `git rev-parse --show-toplevel` | `D:/Projects/Contract2Agent` |
| `git status --short` | Dirty before edits: modified `AGENTS.md`, modified `mkdocs.yml`, untracked `.codex/`, `=7.0`, module README files, docs system-of-record files, `docs/harness/`, scripts harness files, and `tests/README.md`. |
| `Write-Output $PSVersionTable.PSVersion` | PowerShell 5.1.26100.8115 |
| `rg --files` | Failed with `Access is denied`; used `git ls-files`, `tree`, `Select-String`, and targeted reads. |

Historical context only: prior docs record `python -m pytest` passing 355 tests
on 2026-05-06. No tests were run in this 2026-05-07 task.

### Agent Reports

| Agent | Result |
| --- | --- |
| `codebase_mapper` | Completed. Mapped repo structure, public entry points, modules, CLI commands, docs/harness locations, and risks. |
| `feature_inventory_agent` | Completed. Identified user-visible, developer-visible, internal, and inferred feature candidates with registry cautions. |
| `test_inventory_agent` | Completed. Inventoried pytest framework, commands, layout, fixtures, coverage links, gaps, and runtime status `not_run`. |
| `docs_inventory_agent` | Completed. Inventoried docs, stale/risky claims, missing module explanations, missing harness docs, and placement recommendations. |
| `harness_planner` | Completed. Planned harness docs, quality gates, eval matrix, registry fields, sprint contract template, runbook, and risks. |

### Files Updated

- `docs/README.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/ARCHITECTURE.md`
- `docs/CODEMAP.md`
- `docs/GOLDEN_PRINCIPLES.md`
- `docs/DECISIONS.md`
- `docs/AGENT_HANDOFF.md`
- `docs/harness/README.md`
- `docs/harness/FEATURE_REGISTRY.schema.json`
- `docs/harness/feature_registry.json`
- `docs/harness/PROGRESS.md`
- `docs/harness/QUALITY_GATES.md`
- `docs/harness/EVAL_MATRIX.md`
- `docs/harness/SPRINT_CONTRACT_TEMPLATE.md`
- `docs/harness/RUNBOOK.md`

### Validation Log

| Command | Result | Notes |
| --- | --- | --- |
| `git status --short` | Ran | Shows pre-existing forbidden dirty files and untracked docs/harness/module README files. |
| `git diff --stat` | Ran | Only tracked pre-existing changes appeared: `AGENTS.md` and `mkdocs.yml`; untracked docs are visible in status, not diff. |
| `git diff --name-only` | Ran | Returned `AGENTS.md` and `mkdocs.yml` only for tracked changes. |
| `python3 -m json.tool docs/harness/FEATURE_REGISTRY.schema.json` | Passed | Valid JSON after retry; first approval review timed out. |
| `python3 -m json.tool docs/harness/feature_registry.json` | Passed | Valid JSON. |
| `python -m pytest` | Not run | Explicitly forbidden for this task. |
| `python -m mkdocs build --strict` | Not run | Explicitly forbidden for this task. |
| `python scripts/check_docs_links.py` | Not run | Not part of the required validation for this task and broader docs gates were not authorized. |

### Risks And Blockers

- Worktree was dirty before this task; forbidden paths `AGENTS.md` and `mkdocs.yml` remain modified but were not edited by this task.
- Untracked `=7.0` remains present and was not removed.
- `rg.exe` is blocked in this environment.
- Feature registry uses dated historical evidence for existing `verified_pass` entries; it does not claim fresh pytest validation.
- `harness_agent_first_workflow` is `implemented_pending_evaluation` until harness/docs gates are rerun after this docs refresh.
- `.codex/` runtime support remains `needs_verification`.

### Next Step

Run an evaluator pass over the current docs/harness bootstrap, then run the
docs/harness gates that the environment allows before upgrading harness status.

## 2026-05-09 - ECC-Inspired Codex Tooling Organization

### Scope

- User request: adapt useful organization patterns from `affaan-m/everything-claude-code` for this repository's agent, skill, and MCP setup.
- Allowed write set by request: project-local Codex configuration, project-local skills, and harness state records needed to keep evidence aligned.
- Out of scope: production package code, tests, examples, dependency installation, enabled networked MCP startup, Git staging/commit/reset/delete/rename, and verified feature status upgrades.

### Baseline Inspection

| Command | Result |
| --- | --- |
| `git status --short` | Initial sandboxed attempt failed with `windows sandbox: setup refresh failed`; escalated retry returned clean output. |
| `git branch --show-current` | `main` |
| `docs/AGENT_HANDOFF.md`, `docs/harness/PROGRESS.md`, `docs/ARCHITECTURE.md`, `docs/CODEMAP.md` | Read before edits. |
| `.codex/config.toml`, `.codex/agents`, `.agents/skills` | Existing project-local Codex config, agent roles, and skills inspected before edits. |

### Files Updated

- `.codex/config.toml`
- `.agents/skills/codex-tooling-orchestrator/SKILL.md`
- `.agents/skills/codex-tooling-orchestrator/agents/openai.yaml`
- `docs/harness/feature_registry.json`
- `docs/harness/PROGRESS.md`
- `docs/AGENT_HANDOFF.md`

### What Changed

- Reworked `.codex/config.toml` into an explicit project-scoped Codex config with schema pointer, local role references, skill settings, conservative multi-agent feature flags, and disabled optional MCP candidates.
- Added optional disabled MCP entries for `context7`, `github`, `playwright`, `sequential_thinking`, and `memory`; no server was enabled or installed.
- Added the `codex-tooling-orchestrator` skill to guide future agents on role selection, skill selection, MCP use, enablement checks, and evidence boundaries.
- Updated the `codex_project_agents` registry entry with source/command evidence while keeping status at `needs_verification`.

### Validation Log

| Command | Result | Notes |
| --- | --- | --- |
| `python -c "import pathlib, tomllib; tomllib.loads(pathlib.Path('.codex/config.toml').read_text(encoding='utf-8')); print('toml ok')"` | Passed | Confirms `.codex/config.toml` is valid TOML. |
| `python D:\DevData\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents\skills\codex-tooling-orchestrator` | Passed | Skill frontmatter and naming validated. |
| `codex --help` | Passed | Codex CLI is available. |
| `codex mcp --help` | Passed | MCP management subcommand is available. |
| `codex mcp list` | Passed | Parsed configured MCP entries and reported all five as `disabled`; no MCP server startup was attempted. |
| `git status --short` | Ran | Final status shows modified `.codex/config.toml`, `docs/AGENT_HANDOFF.md`, `docs/harness/PROGRESS.md`, `docs/harness/feature_registry.json`, and untracked `.agents/skills/codex-tooling-orchestrator/`. |
| `git diff --stat` | Ran | Final tracked diff covers `.codex/config.toml`, `docs/AGENT_HANDOFF.md`, `docs/harness/PROGRESS.md`, and `docs/harness/feature_registry.json`; untracked skill files are visible in status. |
| `git diff --name-only` | Ran | Final tracked diff names `.codex/config.toml`, `docs/AGENT_HANDOFF.md`, `docs/harness/PROGRESS.md`, and `docs/harness/feature_registry.json`. |
| `python -c "import json, pathlib; json.loads(pathlib.Path('docs/harness/feature_registry.json').read_text(encoding='utf-8')); print('feature_registry json ok')"` | Passed | Confirms updated feature registry is valid JSON. |
| `python scripts/harness/validate_docs.py` | Passed | Validated 16 required docs, 10 module READMEs, AGENTS.md length, and feature registry shape. |
| `python -m pytest` | Not run | No production Python behavior or tests changed. |
| `python -m mkdocs build --strict` | Not run | No MkDocs navigation or site content changed. |

### Risks And Blockers

- MCP servers are configured but disabled. Enabling them may require network access, `npx` package downloads, and credentials.
- `codex mcp list` validates that Codex can parse/list the MCP entries, not that the servers start successfully.
- Fresh-session skill discovery and custom agent dispatch were not exercised, so `codex_project_agents` remains `needs_verification`.
- No evaluator pass was run after this configuration change.

### Next Step

Run an evaluator pass for the Codex tooling configuration, then enable and test
only the specific MCP server needed for a concrete task with explicit network
and credential approval.

## 2026-05-10 - PaperQA2 Open-Source File-Reading Reference

### Scope

- User request: find a suitable GitHub file-reading agent and use its
  open-source content to enrich the file-reading feature.
- Selected reference: Future-House PaperQA2
  (`https://github.com/Future-House/paper-qa`), Apache-2.0.
- Allowed write set used: file-reading reference metadata, example profile,
  file-reading docs, MkDocs nav, focused tests, and handoff/progress records.
- Out of scope: vendoring upstream code or datasets, adding dependencies,
  running PaperQA2, importing benchmark results, updating feature status,
  staging, committing, resetting, deleting, or renaming files.

### Baseline Inspection

| Command | Result |
| --- | --- |
| `git status --short` | Initial sandboxed attempt failed with `windows sandbox: setup refresh failed`; escalated retry returned clean output. |
| `docs/AGENT_HANDOFF.md`, `docs/harness/PROGRESS.md`, `docs/ARCHITECTURE.md`, `docs/CODEMAP.md` | Read before edits. |
| `.agents/skills/file-reading-eval-architect/SKILL.md` | Read and applied. |
| `.agents/skills/research-grounded-eval/SKILL.md` | Read and applied. |

### External Sources Consulted

- `https://github.com/Future-House/paper-qa`
- `https://github.com/Future-House/paper-qa/blob/main/README.md`
- `https://github.com/Future-House/paper-qa/blob/main/pyproject.toml`
- `https://github.com/Future-House/paper-qa/tree/main/docs`
- `https://github.com/Future-House/paper-qa/tree/main/packages`
- `https://github.com/Future-House/paper-qa/tree/main/src/paperqa/agents`
- `https://github.com/Future-House/paper-qa/tree/main/src/paperqa/sources`
- `https://github.com/Future-House/paper-qa/tree/main/tests`

### Files Updated

- `contract2agent/evaluation/file_reading/references.py`
- `docs/file-reading-eval/README.md`
- `docs/file-reading-eval/open-source-agent-references.md`
- `examples/file_reading_eval/profiles/paperqa2_open_source_profile.json`
- `examples/file_reading_eval/references/reference_sources.json`
- `mkdocs.yml`
- `tests/test_file_reading_eval.py`
- `tests/test_file_reading_docs_examples.py`
- `docs/AGENT_HANDOFF.md`
- `docs/harness/PROGRESS.md`

### What Changed

- Added PaperQA2 to `curated_reference_sources()` as contextual
  `open_source_agent_reference` metadata with license, provenance,
  applicable task families, and limitations.
- Added a PaperQA2 profile fixture to support profile-only analysis and future
  adapter planning.
- Added a file-reading docs page that inventories the upstream open-source
  repository content and converts it into task-family, safety, and adapter
  guidance.
- Added PaperQA2 to example reference metadata and MkDocs navigation.
- Added regression tests that require PaperQA2 to remain contextual metadata
  without imported metrics or observed scores.

### Validation Log

| Command | Result | Notes |
| --- | --- | --- |
| `python -m pytest tests\test_file_reading_eval.py tests\test_file_reading_docs_examples.py` | Passed | 39 tests passed. |
| `python scripts\check_docs_links.py` | Passed | Checked 60 Markdown files; all relative links resolve. |
| `python -m compileall -q contract2agent tests scripts` | Passed | No output. |
| `python -m mkdocs build --strict` | Passed | Built docs into `site/`. |
| `python scripts\harness\validate_docs.py` | Passed | Validated required docs, module READMEs, AGENTS.md length, and feature registry shape. |
| `python -m contract2agent.cli file-eval list-references` | Passed | Output includes `paperqa2` as `open_source_agent_reference`. |
| `git status --short` | Ran | Shows expected modified and new files from this task. |

### Risks And Blockers

- PaperQA2 was researched from public GitHub sources but not installed or run;
  no observed Contract2Agent result exists.
- Upstream PaperQA2 claims, papers, examples, and benchmark artifacts were not
  imported as scores.
- A future adapter needs API verification, citation normalization, corpus
  containment, cache containment, and explicit network/LLM/embedding controls.
- `site/` was produced by MkDocs and should remain an ignored build artifact.

### Next Step

Prototype a PaperQA2 black-box adapter only if optional dependency installation
and provider/network behavior are explicitly approved, then run it against a
small local corpus and store the observed run separately from contextual
reference metadata.

## 2026-05-10 - Open Paper Cards For File-Reading Examples

### Scope

- User request: find two suitable papers and turn them into examples for the
  reading-files feature.
- Selected papers:
  - QASPER (`https://arxiv.org/abs/2105.03011`), CC BY 4.0.
  - LongBench (`https://aclanthology.org/2024.acl-long.172/`), CC BY 4.0 under
    ACL Anthology policy for 2016+ materials.
- Allowed write set used: file-reading example corpus, tasks, reference
  metadata, docs, tests, and handoff/progress records.
- Out of scope: vendoring full paper PDFs or full paper text, adding
  dependencies, network import implementation, benchmark/result import,
  feature status changes, staging, committing, resetting, deleting, or renaming
  files.

### External Sources Consulted

- `https://arxiv.org/abs/2105.03011`
- `https://creativecommons.org/licenses/by/4.0/`
- `https://aclanthology.org/2024.acl-long.172/`
- `https://aclanthology.org/faq/copyright/`

### Files Updated

- `examples/file_reading_eval/corpus/papers/qasper_paper_card.md`
- `examples/file_reading_eval/corpus/papers/longbench_paper_card.md`
- `examples/file_reading_eval/tasks/paper_tasks.jsonl`
- `examples/file_reading_eval/references/reference_sources.json`
- `examples/file_reading_eval/README.md`
- `docs/file-reading-eval/sample-run.md`
- `tests/test_file_reading_docs_examples.py`
- `docs/AGENT_HANDOFF.md`
- `docs/harness/PROGRESS.md`

### What Changed

- Added two compact paper-card corpus files with source URLs, license notes,
  attribution, and line-level facts for deterministic citation checks.
- Added `paper_tasks.jsonl` covering key-value lookup, citation-required QA,
  multi-file comparison, and unanswerable abstention.
- Added structured example reference metadata for both paper cards with
  contextual-only limitations and no imported metrics.
- Documented the paper-card workflow in the examples README and sample-run
  guide.
- Added a test that imports the sample corpus and validates `paper_tasks.jsonl`
  against the generated manifest.

### Validation Log

| Command | Result | Notes |
| --- | --- | --- |
| `python -m pytest tests\test_file_reading_eval.py tests\test_file_reading_docs_examples.py` | Passed | 40 tests passed. |
| `python scripts\check_docs_links.py` | Passed | Checked 62 Markdown files; all relative links resolve. |
| `python -m compileall -q contract2agent tests scripts` | Passed | No output. |
| `python -m mkdocs build --strict` | Passed | Built docs into `site/`. |
| `python scripts\harness\validate_docs.py` | Passed | Validated required docs, module READMEs, AGENTS.md length, and feature registry shape. |
| `python -m contract2agent.cli file-eval import-local --input examples/file_reading_eval/corpus --out .runs/paper-corpus --manifest .runs/paper-corpus/manifest.json` | Passed | Imported 11 documents. |
| `python -m contract2agent.cli file-eval validate --corpus .runs/paper-corpus/manifest.json --tasks examples/file_reading_eval/tasks/paper_tasks.jsonl` | Passed | Task file IDs, spans, and quotes validated. |
| `git diff --check` | Passed | No whitespace errors. |

### Risks And Blockers

- The examples are paper cards, not full-paper ingestion. Full PDF/text
  ingestion remains future work.
- Source paper claims are contextual examples only; they are not observed
  Contract2Agent scores or benchmark claims.
- `.runs/paper-corpus` and `site/` are local generated artifacts from
  validation and should remain ignored.

### Next Step

Add a small paper-aware dummy reader or adapter fixture if future tasks need
observed run artifacts for `paper_tasks.jsonl`; otherwise keep these examples as
validated corpus/task fixtures.

## 2026-05-10 - BLT Paper Card And Privacy Eval

### Scope

- User request: add another AI paper example, specifically the BLTs
  private-learning paper, and add one complete feature beyond reading-files
  based on related GitHub project comparison and current privacy/eval themes.
- Added paper reference: `A Hassle-free Algorithm for Private Learning in
  Practice: Don't Use Tree Aggregation, Use BLTs`
  (`https://arxiv.org/abs/2408.08868` and Google Research publication page).
- Added feature: dependency-free `privacy-eval` static privacy-risk analysis
  for agent profiles, with CLI, schemas, reports, docs, examples, and tests.
- External GitHub references used as contextual design input only:
  AgentLeak, AgentDojo, Opacus, and OpenDP.
- Out of scope: importing benchmark scores, running privacy attacks, executing
  DP accounting, adding dependencies, GitHub Pages runtime calls, or marking any
  feature verified from external claims.

### Files Updated

- `contract2agent/privacy_eval/`
- `contract2agent/cli.py`
- `contract2agent/evaluation/file_reading/references.py`
- `examples/file_reading_eval/corpus/papers/`
- `examples/file_reading_eval/tasks/paper_tasks.jsonl`
- `examples/file_reading_eval/references/reference_sources.json`
- `examples/privacy_eval/`
- `docs/privacy-eval/README.md`
- `docs/file-reading-eval/README.md`
- `docs/file-reading-eval/sample-run.md`
- `docs/ARCHITECTURE.md`
- `docs/CODEMAP.md`
- `docs/README.md`
- `docs/harness/EVAL_MATRIX.md`
- `README.md`
- `mkdocs.yml`
- `tests/test_privacy_eval.py`
- `tests/test_file_reading_eval.py`
- `tests/test_file_reading_docs_examples.py`
- `docs/AGENT_HANDOFF.md`
- `docs/harness/PROGRESS.md`

### What Changed

- Added a BLT paper-card corpus file and a citation-checked task that exercises
  mechanism lookup for private-learning reading examples.
- Added `privacy-eval` profile schemas, curated privacy reference metadata,
  deterministic finding generation, report rendering, and CLI integration
  through both Typer and argparse paths.
- Added examples for healthcare multi-agent workflows, federated keyboard BLT
  deployment analysis, and RAG customer-support privacy review.
- Added docs that compare related GitHub project capabilities while keeping
  their outputs as framework references, not Contract2Agent results.
- Added tests that cover schema serialization, report rendering, CLI writes,
  curated references, BLT context, and file-reading task validation.

### Validation Log

| Command | Result | Notes |
| --- | --- | --- |
| `python -m pytest tests\test_privacy_eval.py tests\test_file_reading_eval.py tests\test_file_reading_docs_examples.py tests\test_agent_evaluation_framework.py` | Passed | 69 tests passed. |
| `python -m pytest` | Passed | 365 tests passed. |
| `python -m compileall -q contract2agent tests scripts` | Passed | No output. |
| `git diff --check` | Passed | No whitespace errors. |
| `python scripts\check_docs_links.py` | Passed | Checked 65 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Built docs into `site/`. |
| `python scripts\harness\validate_docs.py` | Passed | Validated required docs, module READMEs, AGENTS length, and feature registry shape. |
| `python -m contract2agent.cli privacy-eval --profile examples/privacy_eval/healthcare_multi_agent_privacy.json --out .runs/privacy-healthcare.md` | Passed | Wrote Markdown report. |
| `python -m contract2agent.cli privacy-eval --profile examples/privacy_eval/federated_keyboard_blt_profile.json --format json --out .runs/privacy-keyboard.json` | Passed | Wrote JSON report. |
| `python -m contract2agent.cli privacy-eval --list-references` | Passed | Listed privacy references. |
| `python -m contract2agent.cli file-eval import-local --input examples/file_reading_eval/corpus --out .runs/paper-corpus --manifest .runs/paper-corpus/manifest.json` | Passed | Imported 12 documents. |
| `python -m contract2agent.cli file-eval validate --corpus .runs/paper-corpus/manifest.json --tasks examples/file_reading_eval/tasks/paper_tasks.jsonl` | Passed | Task file IDs, spans, and quotes validated. |

### Review-Agent Status

- `bug_reviewer` Einstein timed out and was closed before returning a result.
- `bug_reviewer` Euclid timed out and was closed before returning a result.
- Newton was interrupted with a narrower final-review request, timed out, and
  was closed before returning a result.
- `bug_reviewer` Aristotle was started for a final blocker review, timed out,
  and was closed before returning a result.
- These attempts are recorded as attempted independent review, not evaluator
  evidence and not PASS results.

### Risks And Blockers

- `privacy-eval` is static profile analysis only; it does not prove runtime
  privacy behavior.
- AgentLeak, AgentDojo, Opacus, OpenDP, and BLT references are contextual
  framework inputs, not observed local benchmark results.
- The paper examples are compact paper cards, not full paper ingestion.
- Generated `.runs/` and `site/` artifacts should remain ignored.

### Next Step

Add an observed trace importer for `privacy-eval` so future work can compare
declared privacy controls, static findings, and runtime evidence without
collapsing those evidence types into a single unsupported score.
