# Report Examples And Scoring Guide

This page explains how to read file-reading reports and how to connect score dimensions to concrete agent improvements.

Committed examples:

- `examples/file_reading_eval/expected_reports/deterministic_report.example.md`
- `examples/file_reading_eval/expected_reports/deterministic_report.example.json`
- `examples/file_reading_eval/expected_reports/corpus_manifest.example.json`
- `examples/file_reading_eval/expected_reports/reference_result.example.json`

These are sample/synthetic artifacts. They are not generated `.runs/` directories and are not benchmark claims.

## Report Shape

A Markdown report should include:

- Run summary and observed task count.
- Agent/profile summary.
- Corpus summary and source labels.
- Task summary.
- Overall result and confidence.
- Score by dimension.
- Citation accuracy.
- Evidence span validity.
- Quote match status.
- Answer correctness.
- Grounding and hallucination checks.
- Forbidden-file or boundary checks.
- Missing evidence and abstention behavior.
- Failure modes.
- Recommended fixes.
- Data source and reference source labels.
- Redaction note.
- Limitations.

The JSON report should carry the same concepts in script-friendly form.

## Scoring Dimensions

| Dimension | What It Measures | High Score Means | Low Score Means | Improve By | Report Field |
| --- | --- | --- | --- | --- | --- |
| `answer_correctness` | Match to gold answer, aliases, or correct abstention. | Answers are correct for observed tasks. | Answers are wrong or unsupported. | Tighten retrieval and answer synthesis from evidence. | `scorecard.scores_by_dimension.answer_correctness` |
| `evidence_grounding` | Whether factual claims are backed by expected evidence. | Claims are supported by cited corpus text. | Claims are unsupported or invented. | Require claim-level citation before final answer. | `unsupported_claim_control` plus failure modes |
| `citation_validity` | Presence and structure of citations. | Citations include known `file_id`, line range, and quote. | Missing or malformed citations. | Enforce structured output schema. | `citation_quality` |
| `citation_precision` | Avoiding unnecessary or wrong evidence. | Cited files and lines are focused. | Citations point to distractors or unrelated lines. | Filter retrieved evidence before final citation. | `supporting_file_precision` |
| `citation_recall` | Covering required evidence. | Required spans or support files are cited. | Important evidence is missing. | Add retrieval recall and final evidence checks. | `supporting_file_recall`, `citation_span_accuracy` |
| `quote_match` | Exact quote-to-line match. | Quote text appears in cited line range. | Quote differs from source lines. | Copy source quote exactly or omit quote only when allowed. | `citation_quote_match` |
| `line_range_validity` | Whether line ranges overlap expected spans. | Cited line range covers gold evidence. | Line range points elsewhere. | Re-read cited lines before final output. | `citation_span_accuracy` |
| `file_selection` | Reading/citing supporting files while avoiding distractors. | Required files are used with few irrelevant reads. | Supporting files are missed or distractors dominate. | Use task `allowed_files` and rank files by question relevance. | `supporting_file_recall`, `supporting_file_precision` |
| `forbidden_file_boundary` | Respect for task forbidden files. | No forbidden file is read or cited. | Forbidden file appears in `files_read` or trace. | Enforce allowlist before retrieval. | `forbidden_file_safety` |
| `unanswerable_handling` | Abstention on missing-evidence tasks. | Agent says insufficient evidence and does not guess. | Agent fabricates an answer. | Add a missing-evidence policy and threshold. | `unanswerable_abstention` |
| `hallucination_resistance` | Avoiding unsupported facts. | Answers stay within corpus evidence. | Unsupported claims or invented facts appear. | Require citation for every factual claim. | `unsupported_claim_control` |
| `robustness_to_malformed_output` | Parseable target output and schema compliance. | JSON is valid and expected fields exist. | Output cannot be parsed or fields are wrong type. | Validate and repair JSON before submission. | `schema_compliance` |
| `optional_judge_agreement` | Agreement between deterministic score and optional judge, if enabled. | Judge supplements deterministic findings without contradiction. | Judge fails, disagrees, or is unavailable. | Keep judge prompts compact and review only selected tasks. | `llm_judge` |
| `report_safety_redaction` | Report redaction and path safety. | Reports avoid local absolute paths and sensitive-looking values. | Reportable artifacts leak local paths or sensitive values. | Use generated report redaction and avoid raw prompt dumps. | report safety notes and tests |

## Failure Modes And Fixes

Failure: answer correct but citation missing.

Suggested fix: require the target agent to emit structured citations with `file_id`, `line_start`, `line_end`, and `quote`.

Failure: citation file is correct but line range is wrong.

Suggested fix: add a final citation verification pass that checks line ranges against retrieved text.

Failure: quote mismatch.

Suggested fix: make the agent copy evidence quotes exactly from the source or omit quote fields only when unsupported by the configured schema.

Failure: answered an unanswerable question.

Suggested fix: add an abstention policy and require "not enough evidence" when gold evidence is absent.

Failure: reads distractor or forbidden files.

Suggested fix: narrow corpus permissions and enforce `allowed_files` before retrieval.

Failure: hallucinates facts not in files.

Suggested fix: require every factual claim to be backed by at least one citation.

Failure: malformed JSON output.

Suggested fix: add schema validation and retry/repair logic before final submission.

Failure: optional LLM judge redacted content.

Suggested fix: move sensitive content out of judge prompts or use deterministic graders for sensitive tasks.

## Comparing A Target Agent To Reference Results

Compare only when the evaluation category, task definitions, metrics, environment, and scoring method are compatible. Prefer comparing on the same corpus and same JSONL task file.

Labels:

- `same-task`: same task pack, scoring method, environment, and comparable conditions.
- `similar-task`: related task family but not identical conditions; use as qualitative context.
- `contextual-only`: methodology, paper, benchmark description, or public result that is not directly comparable.

Do not compare a local file-reading agent directly against unrelated public benchmark leaderboards. Public benchmark references can help design tasks, but they do not imply your target agent achieved any score.

## Reference Import Guidance

Supported local reference files:

- Markdown papers.
- TXT exports.
- JSONL task sets.
- CSV metadata.
- Manually curated benchmark summaries.

Use:

```bash
python -m contract2agent.cli file-eval import-local \
  --input ./reference-notes.md \
  --source-type reference \
  --title "Curated local reference notes" \
  --out .runs/reference-corpus \
  --manifest .runs/reference-corpus/manifest.json
```

Public benchmark or methodology references:

- QASPER-like paper QA references.
- SQuAD-like span-grounded QA references.
- HotpotQA-like multi-hop evidence references.
- OpenAI eval methodology references.
- Other curated references.

These are contextual unless linked to observed experiment results.

Observed experiment results:

- This is the only category that can directly affect score comparison.
- Store task pack ID, scoring method, environment, model/agent summary, metrics, comparable conditions, and limitations.
- Use missing-evidence warnings when comparability is weak.
