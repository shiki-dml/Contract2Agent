# Synthetic File-Reading Evaluation Report Example

This sample report shows the shape of a deterministic file-reading report over the committed synthetic examples. It is not a public benchmark result and does not imply that any external agent achieved this score.

## Run Summary

- Run id: `sample-run`
- Status: completed
- Observed tasks: 4
- Score: 0.86
- Confidence: 0.8
- Score basis: observed synthetic run artifacts
- Optional LLM judge: not included

## Agent And Corpus

- Agent profile: `examples/file_reading_eval/profiles/cautious_reader_profile.json`
- Corpus: `examples/file_reading_eval/corpus/`
- Corpus source label: synthetic example
- Report path handling: local paths are sanitized as `<corpus_root>/...`
- Redaction: sensitive-looking values are redacted in generated reports and judge inputs.

## Task Summary

- Task file: `examples/file_reading_eval/tasks/sample_tasks.jsonl`
- Task types: `single_file_qa`, `unanswerable_question`
- Gold evidence: line spans with exact quotes
- Missing evidence: no allowed file states an approved refund amount, so abstention is expected.

## Scores By Dimension

| Dimension | Score | What It Means |
| --- | ---: | --- |
| answer_correctness | 0.90 | Answers usually match gold answers or abstain correctly. |
| evidence_grounding | 0.82 | Most factual claims are supported by cited corpus lines. |
| citation_validity | 0.82 | Most citations identify a known file and line range. |
| citation_precision | 0.75 | Some citations point to unnecessary or wrong lines. |
| citation_recall | 0.83 | Most required evidence spans are cited. |
| quote_match | 0.75 | One flawed citation quote does not match its line range. |
| line_range_validity | 0.75 | One flawed line range misses the expected evidence. |
| file_selection | 0.88 | The agent mostly reads supporting files instead of distractors. |
| forbidden_file_boundary | 1.00 | No forbidden file was read. |
| unanswerable_handling | 1.00 | Missing-evidence questions are abstained from. |
| hallucination_resistance | 0.78 | One sample output invented an unsupported automatic refund rule. |
| robustness_to_malformed_output | 1.00 | Target output JSON was parseable. |
| report_safety_redaction | 1.00 | Reportable paths and sensitive-looking values are sanitized. |

## Evidence And Citation Checks

Passed:

- `sample_refund_notice_period` cited `contract_policy.md` line 3 with an exact quote.
- `sample_incident_severity` cited `incident_notes.md` line 4 with an exact quote.
- `sample_invoice_due_date` cited `payment_terms.md` line 3 with an exact quote.
- `sample_unanswerable_refund_amount` correctly reported not enough evidence.

Failed:

- The bad citation sample used the correct answer but pointed at `contract_policy.md` line 4, so quote match and line-range validity failed.
- The no-citation sample answered correctly but omitted structured citations.
- The hallucinated sample answered with a policy that does not appear in allowed files.

## Failure Modes

- `citation_span_mismatch`
- `citation_quote_mismatch`
- `missing_citation`
- `high_unsupported_claim_rate`

## Recommended Fixes

- Require target agents to emit structured citations with `file_id`, `line_start`, `line_end`, and `quote`.
- Add a final citation verification pass that checks line ranges against retrieved text.
- Require every factual claim to be backed by at least one citation.
- Add an abstention policy for questions with no gold evidence.
- Keep allowed-file filtering ahead of retrieval so distractors and forbidden files are not read.

## Reference Source Labels

- `local_synthetic_file_reading_examples`: same-task synthetic example; useful for walkthrough comparisons only.
- `qasper`: contextual-only benchmark reference; it does not imply this sample agent achieved a QASPER score.

## Limitations

- This Markdown file is a committed sample report, not a generated `.runs/` artifact.
- The numbers are illustrative for a tiny synthetic corpus and should not be treated as benchmark claims.
- Optional LLM judge output is not included; deterministic evidence validation remains the score source.
