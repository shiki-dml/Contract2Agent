# Sample AgentDoctor Auto Report

This is an illustrative example, not an actual run output.

Status: `PASSED_WITH_REVIEW_RECOMMENDED`

Target confidence: `0.85`

Final confidence: `0.87`

Rounds executed: `4`

Patches attempted: `2`

## Patch Preview

Proposed patch:

```text
Failure type: TOOL_MISSING
File: prompts/system.md
Risk: low
Requires approval: false
Expected effect: Improve tool-call correctness for document-reading tasks.
```

Diff excerpt:

```diff
- Summarize the document.
+ Before summarizing, always call document_reader on the provided file.
+ Do not answer from prior knowledge if a document path is provided.
```

## Patch Summary

| Round | File | Failure type | Result |
|---|---|---|---|
| 1 | `prompts/system.md` | `TOOL_MISSING` | Applied and validation improved. |
| 2 | `eval_config.yaml` | `OUTPUT_FORMAT_ERROR` | Applied and validation improved. |

## Overfitting Warning

Auto mode can improve behavior against the current diagnostic tests, but it may overfit to those tests. Use holdout tests, baseline comparison, and human review before trusting auto-generated changes.

Holdout confidence: `0.79`

## Efficiency Warning

The final round improved confidence by only `0.01`. Continued auto-repair may be inefficient.

## Human Review Recommendation

Before keeping the generated changes:

1. Inspect `reports/latest.md`.
2. Review all `reports/patches/*.diff` files.
3. Run a deep comparison against the last accepted baseline.
4. Add or run holdout tests that were not used during auto repair.

```bash
agentdoctor deep --rounds 3 --compare-baseline latest
```
