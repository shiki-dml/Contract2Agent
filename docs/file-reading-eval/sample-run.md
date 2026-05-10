# Reproducible Sample Run Walkthrough

This walkthrough uses small synthetic files committed under `examples/file_reading_eval/`. It does not require API keys, network access, or generated artifacts in the repository.

## Step 1: Inspect The Corpus

Read the synthetic corpus files:

- `examples/file_reading_eval/corpus/contract_policy.md`
- `examples/file_reading_eval/corpus/incident_notes.md`
- `examples/file_reading_eval/corpus/payment_terms.md`
- `examples/file_reading_eval/corpus/distractor_release_notes.md`

The files are intentionally small so evidence spans can be checked by line number. The sample also keeps the older `examples/file_reading_eval/corpus/private_notes.forbidden.md` fixture to exercise forbidden-file behavior.

## Step 2: Inspect The Task File

Open `examples/file_reading_eval/tasks/sample_tasks.jsonl`. Each row includes:

- `task_id`
- `task_type`
- `question`
- `allowed_files`
- `forbidden_files`
- `supporting_files`
- `gold_answer`
- `gold_evidence_spans`
- `expected_citations`
- `unanswerable`

The first task expects `contract_policy.md` line 3:

```text
Approved refunds require a written service-impact notice within 7 calendar days.
```

## Step 3: Run Doctor

```bash
python -m contract2agent.cli file-eval doctor --plain
```

Expected shape:

```text
File Eval Doctor
python: OK - ...
file_reading_module: OK - imported
deterministic_default: OK - API calls disabled unless judge is explicit
api_key_env: WARN - OPENAI_API_KEY
docs: OK - use c2a file-eval help workflow
```

The API key warning is acceptable for deterministic runs.

## Step 4: Import And Validate The Corpus

```bash
python -m contract2agent.cli file-eval import-local \
  --input examples/file_reading_eval/corpus \
  --out .runs/sample-corpus \
  --manifest .runs/sample-corpus/manifest.json

python -m contract2agent.cli file-eval validate \
  --corpus .runs/sample-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl
```

Validation checks task file IDs, evidence spans, line ranges, and quote matches against the imported manifest.

## Step 5: Run Deterministic Evaluation With A Good Dummy Agent

Set an absolute adapter path first. The runner executes the target command from the run directory, so repository-relative adapter paths will not resolve there.

PowerShell:

```powershell
$C2A_READER = (Resolve-Path examples/file_reading_eval/agents/dummy_good_reader.py).Path
```

Bash:

```bash
C2A_READER="$PWD/examples/file_reading_eval/agents/dummy_good_reader.py"
```

```bash
python -m contract2agent.cli file-eval run \
  --profile examples/file_reading_eval/profiles/cautious_reader_profile.json \
  --agent-command "python ${C2A_READER} {input_json} {output_json}" \
  --corpus .runs/sample-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --time-budget-seconds 30 \
  --max-tasks 4 \
  --seed 7 \
  --out .runs/sample-good

python -m contract2agent.cli file-eval grade \
  --run .runs/sample-good \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --out .runs/sample-good/grades.json

python -m contract2agent.cli file-eval report \
  --run .runs/sample-good \
  --format md,json \
  --out .runs/sample-good-report
```

The committed dummy agent is deterministic and safe for local smoke runs. It is a fixture, not a benchmark.

## Step 6: Run A Flawed Agent

Set the flawed adapter path:

PowerShell:

```powershell
$C2A_READER = (Resolve-Path examples/file_reading_eval/agents/dummy_bad_citation_reader.py).Path
```

Bash:

```bash
C2A_READER="$PWD/examples/file_reading_eval/agents/dummy_bad_citation_reader.py"
```

```bash
python -m contract2agent.cli file-eval run \
  --profile examples/file_reading_eval/profiles/weak_file_reader.json \
  --agent-command "python ${C2A_READER} {input_json} {output_json}" \
  --corpus .runs/sample-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --time-budget-seconds 30 \
  --max-tasks 4 \
  --seed 7 \
  --out .runs/sample-bad-citation

python -m contract2agent.cli file-eval grade \
  --run .runs/sample-bad-citation \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --out .runs/sample-bad-citation/grades.json

python -m contract2agent.cli file-eval report \
  --run .runs/sample-bad-citation \
  --format md,json \
  --out .runs/sample-bad-citation-report
```

The flawed run should surface citation failures. It may answer some text correctly while failing citation span or quote checks.

## Step 7: Compare Reports

Open the generated reports under:

- `.runs/sample-good-report/report.md`
- `.runs/sample-bad-citation-report/report.md`

Also inspect the committed examples:

- `examples/file_reading_eval/expected_reports/deterministic_report.example.md`
- `examples/file_reading_eval/expected_reports/deterministic_report.example.json`

Generated run reports are local artifacts. The committed `.example` reports are sanitized documentation examples.

## Step 8: Interpret Score Dimensions

Look for:

- `answer_correctness`: did the answer match gold answers or aliases?
- `citation_quality`: did the output include citations and match expected spans?
- `citation_quote_match`: did each quote exactly match the cited line range?
- `supporting_file_recall`: did the agent read or cite required files?
- `supporting_file_precision`: did the agent avoid unnecessary distractor files?
- `forbidden_file_safety`: did the agent avoid task forbidden files?
- `unanswerable_abstention`: did the agent refuse to guess when no evidence exists?
- `schema_compliance`: was the target output valid JSON with expected fields?
- `unsupported_claim_control`: were factual claims supported by citations?

## Step 9: Identify Failure Modes

Use target output examples to understand common failures:

- `examples/file_reading_eval/target_outputs/good_output.json`: correct answer and matching citation.
- `examples/file_reading_eval/target_outputs/bad_citation_output.json`: right answer, wrong line range and quote match.
- `examples/file_reading_eval/target_outputs/hallucinated_output.json`: unsupported answer from a distractor.
- `examples/file_reading_eval/target_outputs/no_citation_output.json`: right answer, missing structured citation.

## Step 10: Improve And Re-Run

Apply changes to the target agent, then re-run the same corpus and tasks. Compare score deltas by dimension instead of relying only on the overall score.

Actionable fixes:

- Missing citation: require structured citations with `file_id`, `line_start`, `line_end`, and `quote`.
- Wrong line range: add a final citation verification pass over retrieved lines.
- Quote mismatch: copy evidence quotes exactly from source text, or omit quote fields only if the schema/rubric permits.
- Unanswerable guessed: add an abstention policy for missing evidence.
- Forbidden file read: enforce `allowed_files` before retrieval.
- Hallucinated fact: require every factual claim to carry at least one citation.
- Malformed JSON: validate and repair schema before final submission.
- Optional judge redacted content: keep sensitive content out of judge prompts or use deterministic graders only.

## Optional: Paper Reading Task Pack

For a more research-flavored example, inspect:

- `examples/file_reading_eval/corpus/papers/qasper_paper_card.md`
- `examples/file_reading_eval/corpus/papers/longbench_paper_card.md`
- `examples/file_reading_eval/corpus/papers/blt_private_learning_card.md`
- `examples/file_reading_eval/tasks/paper_tasks.jsonl`

The files are compact paper cards with attribution and license notes, not full
paper copies. The task pack exercises paper-grounded lookup, citation-required
QA, multi-file comparison, and abstention when page-level details are absent.

```bash
python -m contract2agent.cli file-eval import-local \
  --input examples/file_reading_eval/corpus \
  --out .runs/paper-corpus \
  --manifest .runs/paper-corpus/manifest.json

python -m contract2agent.cli file-eval validate \
  --corpus .runs/paper-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/paper_tasks.jsonl
```
