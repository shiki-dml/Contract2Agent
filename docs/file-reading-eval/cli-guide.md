# File-Reading CLI User Guide

This guide documents implemented commands only. Use `python -m contract2agent.cli ...` from a fresh clone; use `c2a ...` after `python -m pip install -e ".[dev]"` places the console script on `PATH`.

## Installation

```bash
python -m pip install -e ".[dev]"
```

For documentation checks:

```bash
python -m pip install -e ".[docs]"
```

No API key is required for deterministic graders. Optional LLM judging requires an explicit judge command or provider selection.

## Basic Help Commands

```bash
python -m contract2agent.cli --help
python -m contract2agent.cli file-eval --help
python -m contract2agent.cli file-eval doctor --plain
python -m contract2agent.cli file-eval help workflow
python -m contract2agent.cli file-eval help scoring
python -m contract2agent.cli file-eval help llm
python -m contract2agent.cli file-eval help examples
python -m contract2agent.cli file-eval help references
```

Installed console-script equivalents:

```bash
c2a --help
c2a file-eval --help
```

If `c2a` is not found, run the module form above or reinstall with `python -m pip install -e ".[dev]"`.

## Concepts And Files

- Agent profile: JSON file with `agent_id`, tools, permissions, citation support, output schema support, trace support, and policy constraints.
- Corpus: directory imported with `import-local`, plus a generated `manifest.json`.
- Eval task: JSONL row with `task_id`, `task_type`, question, allowed/forbidden files, gold answer, and evidence spans.
- Gold evidence span: `file_id`, `line_start`, `line_end`, `quote`, `label`, and `required`.
- Target output: target-agent JSON with `answer`, `citations`, optional `confidence`, `files_read`, and `notes`.
- Run directory: local output path containing `run.json`, `run.jsonl`, task inputs, target outputs, stdout, and stderr.
- Grade JSON: deterministic `grades` and `scorecard`.
- Report directory: generated Markdown/JSON report artifacts.

## Deterministic Local Grading Workflow

Use an absolute adapter path because the target command runs with the run directory as its current working directory.

PowerShell:

```powershell
$C2A_READER = (Resolve-Path examples/file_reading_eval/agents/dummy_good_reader.py).Path
```

Bash:

```bash
C2A_READER="$PWD/examples/file_reading_eval/agents/dummy_good_reader.py"
```

```bash
python -m contract2agent.cli file-eval import-local \
  --input examples/file_reading_eval/corpus \
  --out .runs/example-corpus \
  --manifest .runs/example-corpus/manifest.json

python -m contract2agent.cli file-eval validate \
  --corpus .runs/example-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl

python -m contract2agent.cli file-eval run \
  --profile examples/file_reading_eval/profiles/cautious_reader_profile.json \
  --agent-command "python ${C2A_READER} {input_json} {output_json}" \
  --corpus .runs/example-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --time-budget-seconds 30 \
  --max-tasks 4 \
  --seed 7 \
  --out .runs/example-good

python -m contract2agent.cli file-eval grade \
  --run .runs/example-good \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --out .runs/example-good/grades.json

python -m contract2agent.cli file-eval report \
  --run .runs/example-good \
  --format md,json \
  --out .runs/example-report
```

The `.runs/` directory is ignored. Do not commit generated run artifacts unless a future task explicitly creates tiny fixtures.

## Debugging Evidence Spans

Use `validate` before running an agent:

```bash
python -m contract2agent.cli file-eval validate \
  --corpus .runs/example-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl
```

Typical failures:

- Invalid line range: `line_start` must be at least 1 and `line_end` must be greater than or equal to `line_start`.
- Quote mismatch: the `quote` text is not found in the selected file lines.
- Missing evidence span: an answerable task lacks gold answers and evidence.
- Unknown file ID: `allowed_files`, `supporting_files`, `distractor_files`, or evidence spans reference a file outside the manifest.

## Debugging Target Output

Target outputs must be JSON objects. A minimal valid output is:

```json
{
  "answer": "Approved refunds require a written service-impact notice within 7 calendar days.",
  "citations": [
    {
      "file_id": "contract_policy.md",
      "line_start": 3,
      "line_end": 3,
      "quote": "Approved refunds require a written service-impact notice within 7 calendar days."
    }
  ],
  "confidence": 0.92,
  "files_read": ["contract_policy.md"]
}
```

Common target-output errors:

- Malformed citation JSON: a citation is not an object or has non-integer line fields.
- Target answer has no citations: answer text may be correct, but citation presence and grounding fail.
- Forbidden file read: `files_read` or trace data includes a task forbidden file.
- Unanswerable question answered incorrectly: the task has `unanswerable: true`, so the expected behavior is an insufficient-evidence answer.
- Secret-like answer redacted: generated reports hide sensitive-looking values; use deterministic graders for sensitive corpora.

## Optional LLM Judge Workflow

LLM judging is disabled by default. It is optional, non-deterministic, and supplementary.

Dry-run estimate without API calls:

```bash
python -m contract2agent.cli file-eval judge \
  --run .runs/example-good \
  --provider openai \
  --dry-run-cost-estimate \
  --judge-only failed \
  --max-judge-tasks 3
```

Command-based local judge:

```bash
python -m contract2agent.cli file-eval judge \
  --run .runs/example-good \
  --provider command \
  --judge-command "python examples/file_reading_eval/agents/dummy_command_judge.py {input_json} {output_json}"
```

OpenAI-compatible provider:

```bash
python -m contract2agent.cli file-eval judge \
  --run .runs/example-good \
  --provider openai \
  --judge-only failed \
  --max-judge-tasks 5 \
  --llm-max-input-chars 12000 \
  --llm-max-output-tokens 500 \
  --evidence-snippet-limit 5 \
  --cost-budget-usd 1.00
```

API key handling:

- `OPENAI_API_KEY` is read from the environment by default.
- `--prompt-for-key` uses hidden session-only input only in an interactive terminal.
- Keys are never written to reports, logs, caches, browser code, docs examples, or committed files.
- Judge input is compact and excludes full corpora, forbidden files, and unsanitized local paths.

## Report Export Workflow

```bash
python -m contract2agent.cli file-eval report \
  --run .runs/example-good \
  --format md,json \
  --out .runs/example-report
```

Report fields include run summary, corpus summary, task coverage, scores by dimension, citation quality, file selection, answer correctness, abstention quality, forbidden-file safety, robustness, reference comparison, failure modes, recommended changes, optional LLM judge status, limitations, and trace artifact locations.

## Reference And Benchmark Workflow

List contextual references:

```bash
python -m contract2agent.cli file-eval list-references
```

Import local reference files as contextual sources:

```bash
python -m contract2agent.cli file-eval import-local \
  --input ./my-paper-notes.md \
  --source-type paper \
  --title "My curated paper notes" \
  --out .runs/reference-corpus \
  --manifest .runs/reference-corpus/manifest.json
```

Compare only against observed reference results:

```bash
python -m contract2agent.cli file-eval compare \
  --run .runs/example-good \
  --reference examples/file_reading_eval/expected_reports/reference_result.example.json \
  --out .runs/example-good/comparison.md
```

Rules:

- Reference paper does not equal observed score.
- Benchmark description does not equal agent performance.
- User-imported paper is not trusted truth unless curated into tasks with gold evidence.
- Public result is not comparable unless model/agent, task set, environment, and metric are documented.
- Reports should label source type as `same-task`, `similar-task`, or `contextual-only`.

## Doctor And Troubleshooting

```bash
python -m contract2agent.cli file-eval doctor --plain
python -m contract2agent.cli file-eval doctor --json
```

Common errors:

- `c2a` not found: use `python -m contract2agent.cli` or reinstall editable package.
- Local path redacted in report: expected safety behavior for reportable artifacts.
- Optional judge unavailable or disabled: deterministic grading still works; configure a provider or command judge explicitly.
- No observed score: run a target command first; profile-only mode cannot report performance.
- Network import blocked: expected default; `import-reference` requires explicit `--allow-network` and currently records metadata only.
