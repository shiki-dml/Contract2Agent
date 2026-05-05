# File Reading Eval Examples

This directory contains small, intentional fixtures for the `file-eval` CLI. They are synthetic, safe to run locally, and do not require API calls.

Use module commands from a fresh clone:

```bash
python -m contract2agent.cli file-eval --help
```

After `python -m pip install -e ".[dev]"`, the `c2a` console script should also work.

## Directory Map

- `agents/`: deterministic dummy target agents and a command-based dummy judge.
- `corpus/`: synthetic Markdown files used by examples and tests.
- `tasks/`: JSONL task packs, including `sample_tasks.jsonl` for the walkthrough.
- `profiles/`: sample file-reading agent profiles.
- `target_outputs/`: standalone good and flawed target output JSON examples.
- `references/`: contextual reference metadata and tiny reference-result fixture.
- `expected_reports/`: committed `.example` report and manifest/reference shapes.
- `configs/`: keyless optional LLM judge config example.

## Deterministic Sample Run

Set an absolute adapter path first because `file-eval run` executes the target command from the run directory.

PowerShell:

```powershell
$C2A_READER = (Resolve-Path examples/file_reading_eval/agents/dummy_good_reader.py).Path
```

Bash:

```bash
C2A_READER="$PWD/examples/file_reading_eval/agents/dummy_good_reader.py"
```

```bash
python -m contract2agent.cli file-eval import-local --input examples/file_reading_eval/corpus --out .runs/example-corpus --manifest .runs/example-corpus/manifest.json
python -m contract2agent.cli file-eval validate --corpus .runs/example-corpus/manifest.json --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl
python -m contract2agent.cli file-eval run --profile examples/file_reading_eval/profiles/cautious_reader_profile.json --agent-command "python ${C2A_READER} {input_json} {output_json}" --corpus .runs/example-corpus/manifest.json --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl --out .runs/example-good
python -m contract2agent.cli file-eval grade --run .runs/example-good --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl --out .runs/example-good/grades.json
python -m contract2agent.cli file-eval report --run .runs/example-good --format md,json --out .runs/example-report
```

Generated `.runs/` artifacts are intentionally ignored.

## Walkthrough And Report Docs

- [CLI guide](../../docs/file-reading-eval/cli-guide.md)
- [Sample run walkthrough](../../docs/file-reading-eval/sample-run.md)
- [Report examples and scoring guide](../../docs/file-reading-eval/report-examples.md)
- [中文概览](../../docs/file-reading-eval/README.zh-CN.md)

Committed report examples:

- [deterministic_report.example.md](expected_reports/deterministic_report.example.md)
- [deterministic_report.example.json](expected_reports/deterministic_report.example.json)

## Profile-Only Mode

```bash
python -m contract2agent.cli file-eval profile-only --profile examples/file_reading_eval/profiles/weak_file_reader.json --out .runs/profile-only
```

Profile-only output is readiness analysis. It does not claim observed reading performance.

## Optional LLM Judge Dry Run

```bash
python -m contract2agent.cli file-eval judge --run .runs/example-good --provider openai --dry-run-cost-estimate --judge-only failed --max-judge-tasks 3
```

This estimates request size and cost. It does not call an API.

## Command-Based Judge

```bash
python -m contract2agent.cli file-eval judge --run .runs/example-good --provider command --judge-command "python examples/file_reading_eval/agents/dummy_command_judge.py {input_json} {output_json}"
```

The command adapter is useful for local/custom judges and CI tests because it avoids provider-specific API dependencies.

## Failure Fixtures

- `dummy_bad_citation_reader.py`: returns a plausible answer with an incorrect quote or span.
- `dummy_forbidden_reader.py`: records a forbidden file in `files_read`.
- `dummy_timeout_reader.py`: sleeps long enough to trip short task budgets.
- `bad_citation_output.json`: correct answer with wrong citation line and quote match.
- `hallucinated_output.json`: unsupported answer from a distractor.
- `no_citation_output.json`: correct answer without structured citations.

Use `sample_tasks.jsonl`, `citation_tasks.jsonl`, `unanswerable_tasks.jsonl`, and `distractor_tasks.jsonl` to exercise citation mismatch, abstention, distractor resistance, forbidden-file behavior, reference comparison, and report generation.
