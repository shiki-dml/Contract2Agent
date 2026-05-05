# File-Reading Agent Evaluation

Contract2Agent includes a specialized `file_reading_agent` adapter for observed local evaluation. It is for agents that read a bounded corpus, select evidence, answer questions, cite source lines, abstain when evidence is missing, and respect forbidden-file boundaries.

This adapter is evaluation-first. A profile-only report can describe readiness and risk, but observed performance scores require a real `file-eval run` artifact.

## What It Does

- Imports approved local text-like files into a corpus manifest.
- Loads or builds JSONL tasks with gold answers and evidence spans.
- Runs a target agent through a black-box JSON command adapter.
- Captures target outputs, traces, stdout, stderr, timing, and files read.
- Grades deterministic dimensions such as answer correctness, citations, file selection, abstention, schema compliance, and forbidden-file safety.
- Optionally runs an explicit LLM or command-based judge after deterministic grading.
- Compares against compatible observed reference results, while keeping public benchmark references contextual.
- Renders Markdown and JSON reports with evidence basis, failures, recommendations, limitations, and artifact labels.

## What It Does Not Do

- It does not score file-reading performance from declared capabilities alone.
- It does not make API calls in deterministic mode.
- It does not make GitHub Pages run live evaluations.
- It does not read private files outside the configured corpus.
- It does not treat papers, benchmark descriptions, or imported methodology notes as target-agent scores.
- It does not implement network dataset pulling in the default dependency-free path.

## Documentation Map

- [CLI user guide](cli-guide.md)
- [Sample run walkthrough](sample-run.md)
- [Report examples and scoring guide](report-examples.md)
- [中文概览](README.zh-CN.md)
- [中文 CLI 指南](cli-guide.zh-CN.md)
- [中文样例运行](sample-run.zh-CN.md)
- [中文报告示例](report-examples.zh-CN.md)

Repository examples:

- `examples/file_reading_eval/README.md`
- `examples/file_reading_eval/tasks/sample_tasks.jsonl`
- `examples/file_reading_eval/target_outputs/good_output.json`
- `examples/file_reading_eval/expected_reports/deterministic_report.example.md`
- `examples/file_reading_eval/expected_reports/deterministic_report.example.json`

## Minimum Workflow

Install from a fresh clone:

```bash
python -m pip install -e ".[dev]"
```

Use the module entry point first because it works before console scripts are on `PATH`:

```bash
python -m contract2agent.cli --help
python -m contract2agent.cli file-eval --help
python -m contract2agent.cli file-eval doctor --plain
python -m contract2agent.cli file-eval help llm
```

After installation, the `c2a` console script should also be available:

```bash
c2a --help
c2a file-eval --help
```

## Core Concepts

- Agent profile: JSON metadata describing tools, permissions, citation support, trace support, and safety constraints.
- Corpus: approved local files copied into a manifest-bounded evaluation corpus.
- Eval task: one JSONL record with a question, allowed files, forbidden files, gold answer, and expected evidence spans.
- Gold answer: expected answer text or accepted aliases.
- Gold evidence spans: machine-checkable `file_id`, line range, quote, label, and required flag.
- Target output: target-agent JSON with `answer`, `citations`, optional `confidence`, `files_read`, and `notes`.
- Citation validation: deterministic checks for known file IDs, line range overlap, and exact quote match.
- Deterministic grader: default local scorer; no API key required.
- Optional LLM judge: explicit supplementary semantic judge; non-deterministic and separate from deterministic scores.
- Report JSON and Markdown report: generated artifacts that explain scores, evidence, failure modes, and limitations.
- Run directory: ignored local output directory, usually under `.runs/`.

## Safety Model

`import-local` skips common secret, cache, virtual environment, browser data, `.git`, `.env`, and credential-like paths. Generated reports sanitize local absolute paths and redact sensitive-looking values where report redaction is implemented.

The runner sends only task-scoped inputs to the target command. The target command is responsible for obeying `allowed_files` and `forbidden_files`; the grader detects reported forbidden-file reads through output and trace artifacts.

Reference papers, public methodology files, CSV metadata, and benchmark summaries are treated as user-provided or contextual evidence. They are not trusted target-agent performance results unless they are curated into tasks and linked to an observed run with compatible metrics.

## Current Reference Import Support

Implemented:

- `import-local --source-type paper|reference|methodology` records local provenance, license, and limitations metadata.
- `list-references` prints curated contextual source metadata.
- `import-reference --allow-network` records curated metadata for a known reference source, but the dependency-free adapter does not download dataset examples.
- `compare` checks compatibility before computing metric deltas from observed reference results.

Planned:

- Rich local paper ingestion beyond text/Markdown conversion.
- Full reference pack ingestion with licenses, provenance, and reproducible task construction.
- More comparison labels beyond same-task compatibility checks.

## Static Demo Constraint

GitHub Pages remains a static viewer and demo. File-reading evaluations should run through the CLI, local scripts, or CI-generated artifacts, not in the browser.
