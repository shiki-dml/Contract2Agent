# Codemap

This map describes where functionality lives by directory, module, CLI command,
examples, docs, and test coverage. It is navigation, not exhaustive API
documentation. Full verification requires evaluator, test, command, or artifact
evidence, not this map alone.

## Top-Level Layout

| Path | Responsibility | Notes |
| --- | --- | --- |
| `contract2agent/` | Main Python package and CLI-backed application logic. | Legacy contract diagnosis plus newer evaluation subsystems. |
| `contract2agent/evaluation/` | Generalized agent profile evaluation framework. | Schemas, classification, evidence, scoring, prediction, reports. |
| `contract2agent/evaluation/file_reading/` | File-reading agent corpus/task/run/grade/report adapter. | Local CLI-driven observed evaluation path. |
| `contract2agent/cost_estimate/` | Static diagnostic cost and time estimation. | Estimate-only, no tests or APIs run. |
| `contract2agent/patch_preview/` | Preview-only patch proposal analysis and report generation. | Must not be documented as applying patches by default. |
| `contract2agent/triage/` | Static triage, risk, coverage, and recommendation planning. | Intake and next-step guidance. |
| `contract2agent/templates/` | Jinja templates for generated contract/eval projects. | Included as package data. |
| `docs/` | MkDocs site, static demos, architecture docs, harness records, and static data. | Source of truth for future agents. |
| `examples/` | Sample profiles, reports, file-reading corpora, dummy agents, and reference outputs. | Examples are fixtures or illustrations unless linked to a documented run. |
| `tests/` | Pytest suite and golden fixtures. | Test inventory found 355 `def test_` functions, but this bootstrap task did not run them. |
| `scripts/` | Repository validation and harness helper scripts. | Scripts call existing project commands. |
| `.agents/skills/` | Project-local skill instructions. | Agent workflow support, not production runtime. |
| `.codex/` | Project-scoped Codex configuration. | Present but runtime support remains `needs_verification`. |

## Core Package Modules

| Module | Public behavior |
| --- | --- |
| `contract2agent/cli.py` | `c2a` and `agentdoctor` console entry point. Registers legacy contract commands, diagnostic modes, triage, cost estimate, patch preview, generalized agent eval, and file-eval commands. |
| `schema.py`, `parser.py`, `checker.py` | Contract schema loading, requirement parsing, and trace validation. |
| `compiler.py`, `generator.py` | Demo/project generation and contract compilation from requirements. |
| `counterexamples.py` | Deterministic counterexample trace generation. |
| `diagnosis.py`, `diagnosis_schema.py`, `diagnostic_modes.py` | Trace diagnosis, quick/deep/auto modes, regression traces, reports, and review policies. |
| `capabilities.py` | Capability evidence reports and suggested eval cases. |
| `baseline.py` | Baseline save/compare support for diagnostic runs. |
| `failure_taxonomy.py` | Failure categories, aggregation, severity, strategies, and playbooks. |
| `path_safety.py` | Path containment and safety helpers. |

## Generalized Evaluation Modules

| Module | Public behavior |
| --- | --- |
| `evaluation/schema.py` | JSON-serializable dataclasses for profiles, tools, evidence, scores, predictions, and reports. |
| `evaluation/capability_classifier.py`, `evaluation/classifier.py` | Multi-label broad agent classification from tools, tasks, permissions, and policy signals. |
| `evaluation/registry.py`, `evaluation/data.py`, `evaluation/sample_data.py` | Agent type, eval category, sample data, and benchmark/reference registries. |
| `evaluation/evidence.py` | Observed, imported, reference, declared-only, and missing-evidence resolution. |
| `evaluation/scoring.py` | Evidence-aware preliminary score dimensions. |
| `evaluation/prediction.py` | Cautious pre-runtime outcome prediction. |
| `evaluation/report.py`, `evaluation/reports.py` | Markdown/JSON report rendering and orchestration. |

## File-Reading Adapter Modules

| Module | Public behavior |
| --- | --- |
| `file_reading/cli.py`, `help.py` | `c2a file-eval` commands, rich help topics, doctor checks, plain/no-color/json modes. |
| `corpus.py`, `importers.py` | Local corpus import, manifest creation, safe path handling, provenance metadata. |
| `tasks.py` | Task JSONL loading/building, validation, citation expectations, abstention settings. |
| `runner.py` | Black-box target command execution with input/output artifacts, time budgets, and trace capture. |
| `graders.py` | Deterministic answer, citation, file-selection, abstention, schema, and forbidden-file grading. |
| `compare.py`, `references.py` | Reference metadata and compatibility-aware reference-result comparison. |
| `llm_judge.py` | Optional LLM/command judge supplements, budgets, cache keys, key redaction, and deterministic fallback. |
| `recommendations.py`, `reports.py`, `schema.py` | Improvement recommendations, reports, and JSON-serializable file-reading schemas. |

## CLI Commands

Primary entry points from `pyproject.toml`:

- `c2a = contract2agent.cli:main`
- `agentdoctor = contract2agent.cli:main` legacy alias

| Command group | Commands | Behavior summary |
| --- | --- | --- |
| Project and contract workflow | `new`, `compile`, `demo`, `check`, `check-all`, `counterexamples`, `restrictions`, `capabilities`, `diagnose`, `why` | Generate contracts/projects, validate traces, explain failures, and report capability evidence. |
| Diagnostic modes | `quick`, `deep`, `auto` | Run bounded diagnostic workflows with review policy, confidence, reports, and optional baseline comparison. |
| Planning and estimates | `triage`, `cost-estimate` | Static intake and estimate reports. These do not execute agents or tests. |
| Patch analysis | `patch-preview` | Preview-only patch proposals and report/diff artifacts. |
| General agent evaluation | `eval-agent` | Profile-based agent classification, evidence resolution, scoring, prediction, Markdown/JSON report output. |
| File-reading evaluation | `file-eval help`, `doctor`, `init`, `import-local`, `list-references`, `import-reference`, `validate`, `build-tasks`, `run`, `profile-only`, `grade`, `compare`, `report`, `configure-llm`, `llm-check`, `judge` | Local corpus/task/run/grade/report flow with optional judge support. |

## Examples Map

| Path | Purpose |
| --- | --- |
| `examples/agent_eval/` | Agent profiles, benchmark references, and sample experiment results for generalized evaluation examples. |
| `examples/file_reading_eval/` | File-reading corpus, task packs, dummy readers, target outputs, expected report shapes, references, profiles, and keyless judge config. |
| `examples/paper-reader-agent/` | Legacy/simple paper-reader example. |
| `examples/reports/` | Illustrative diagnostic reports, not proof of current runs. |
| `docs/examples/` | Static playground sample dispute JSON. |

## Docs Map

| Path | Purpose |
| --- | --- |
| `docs/README.md` | Documentation landing page and source-of-truth links. |
| `docs/PROJECT_CONTEXT.md`, `docs/ARCHITECTURE.md`, `docs/CODEMAP.md` | Project scope, architecture, and code navigation. |
| `docs/GOLDEN_PRINCIPLES.md`, `docs/DECISIONS.md` | Evidence/safety principles and decision log. |
| `docs/AGENT_HANDOFF.md`, `docs/harness/PROGRESS.md` | Durable current state and chronological work log. |
| `docs/harness/` | Harness workflow, gates, eval matrix, registry, sprint template, runbook. |
| `docs/file-reading-eval/` | File-reading user and example docs. |
| `docs/agent-eval/`, `docs/playground/`, `docs/assets/`, `docs/data/` | Static demos and local static metadata. |

## Tests And Coverage Map

| Test file | Covered area |
| --- | --- |
| `tests/test_contract2agent.py` | Core contract parsing, generation, checking, CLI behavior, capabilities, counterexamples, diagnosis surfaces. |
| `tests/test_diagnosis_schema.py` | Diagnosis issue protocol, rule coverage matrix, report fields, and CLI smoke checks. |
| `tests/test_diagnostic_modes.py` | Quick/deep/auto diagnosis modes, review policies, auto safety, rollback behavior. |
| `tests/test_baseline.py` | Baseline snapshots, hashes, comparisons, and overfitting/rollback signals. |
| `tests/test_agent_evaluation_framework.py` | General agent schemas, classification, evidence, scoring, benchmark discipline, reports, and CLI smoke coverage. |
| `tests/test_file_reading_eval.py` | Corpus/task/run/grade/report behavior and file-reading safety cases. |
| `tests/test_file_reading_llm_judge.py` | Optional judge safety, budgets, caching, API key handling, and fallback behavior. |
| `tests/test_file_reading_docs_examples.py` | File-reading examples and documentation alignment. |
| `tests/test_docs_site.py` | README/docs/static demo/MkDocs/GitHub Pages regression checks. |
| `tests/test_cost_estimate.py`, `tests/test_triage.py`, `tests/test_patch_preview.py` | Developer workflow helpers. |
| `tests/test_failure_taxonomy.py`, `tests/test_report_rendering.py`, `tests/test_golden_diagnosis.py` | Failure taxonomy, reports, and golden diagnosis stability. |

## Known Gaps And Stale Signals

- `docs/AGENT_HANDOFF.md` and `docs/harness/PROGRESS.md` contain useful 2026-05-06 validation history, but this task did not rerun pytest or MkDocs.
- `.codex/` role/config files are present but runtime support remains `needs_verification`.
- `rg.exe` returned `Access is denied` in this environment; file discovery used `git ls-files`, `tree`, and targeted reads.
- The worktree was dirty before this task, including modified forbidden files and untracked docs/harness/module README files.
- Live GitHub Pages deployment and current GitHub Actions status were not inspected in this task.

## Update Discipline

- Do not use this codemap as a substitute for reading source before changes.
- Update module README files when responsibilities or public contracts move.
- Use `python scripts/harness/update_codemap.py` to report drift before editing this file when the helper is available.
- Do not mark a feature `verified_pass` from this codemap alone.
