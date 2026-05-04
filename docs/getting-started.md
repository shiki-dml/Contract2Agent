# Getting Started

Use this path when you want a local diagnosis run quickly: install the CLI,
point Contract2Agent at a small agent config, then inspect the Markdown report.

The examples use `c2a`.

Want to try the idea before creating files? Open the [Playground](playground/index.html)
for a static browser-side preview.

## Install

Install from a local checkout:

```bash
cd path/to/contract2agent
python -m pip install -e .
```

For development and documentation work:

```bash
python -m pip install -e ".[dev,docs]"
```

## Minimal Agent Files

Contract2Agent can run quick/deep/auto with a built-in sample contract, but triage
is more useful when it can inspect your files. A minimal research-agent setup
can look like this:

```yaml
# agent.yaml
name: paper_reader_agent
description: Reads local research papers and writes structured Markdown notes.
tools:
  - name: document_reader
    description: Read a local PDF or text document.
  - name: markdown_writer
    description: Write structured Markdown notes.
output:
  format: markdown
workflow:
  review_policy: on-fail
```

```markdown
<!-- prompts/system.md -->
Before summarizing a provided document path, call document_reader.
Use document evidence for factual claims.
Return Markdown with Definitions, Theorems, and Proof ideas sections.
If the file is missing or invalid, stop and ask for clarification.
```

```yaml
# evals/basic.yaml
cases:
  - id: read_before_summary
    tags: [task_completion, tool_use, output_format]
  - id: missing_file_handling
    tags: [error_handling, safety]
```

Triage discovers common files such as `agent.yaml`, `prompts/*.md`, `tool_descriptions.yaml`, `workflow_config.yaml`, `eval_config.yaml`, and `evals/*.yaml`.

## First Triage

```bash
c2a triage --agent ./agent.yaml
```

Triage writes:

```text
.agentdoctor/triage/latest.md
.agentdoctor/triage/latest.json
.agentdoctor/triage/triage_<timestamp>.md
.agentdoctor/triage/triage_<timestamp>.json
```

Use the recommended next command from the terminal output or from `.agentdoctor/triage/latest.md`.

## First Quick Check

```bash
c2a quick
```

Quick mode runs one smoke-diagnosis round and writes:

```text
reports/latest.md
reports/latest.json
reports/rounds/round_001.json
```

Quick is intentionally incomplete. Treat it as a fast development check, not a production certificate.

## First Deep Diagnosis

```bash
c2a deep --rounds 3 --review on-fail
```

Deep mode runs multiple rounds, aggregates findings, writes round JSON files, and keeps review items in the final report. It does not modify agent files.

## Save and Compare a Baseline

Save a reliable reference after a deep run:

```bash
c2a deep --rounds 3 --save-baseline --baseline-name stable-v1
```

Compare a later run:

```bash
c2a deep --rounds 3 --compare-baseline stable-v1
```

Baseline artifacts are written under `.agentdoctor/baselines/`.

## Inspect Reports

Open the Markdown report first:

```text
reports/latest.md
```

Use the JSON report when you need machine-readable details:

```text
reports/latest.json
reports/rounds/round_001.json
```

For preview-only patch proposals after a diagnostic run:

```bash
c2a patch-preview --from-run reports/latest.json
```

Patch preview writes `.agentdoctor/patches/latest.md`, `.agentdoctor/patches/latest.json`, and per-proposal `.md`, `.json`, and `.diff` artifacts when a diff can be generated.
