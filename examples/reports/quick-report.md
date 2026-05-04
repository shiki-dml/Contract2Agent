# Sample AgentDoctor Quick Diagnosis

This is an illustrative example, not an actual run output.

Status: `NEEDS_REVIEW`

Diagnostic confidence: `0.72`

Tests: `6` run, `4` passed, `1` failed, `1` warning

## Key Findings

1. `PASS`: `document_reader` was called before summarization.
2. `PASS`: missing file handling stopped before `markdown_writer`.
3. `FAIL`: expected theorem extraction, but no theorem-like statement was found.
4. `WARN`: final output is Markdown-like, but heading structure is incomplete.
5. `REVIEW`: tool call argument `path="paper.pdf"` should be manually checked.

## Review Items

- Quick mode is incomplete and should not be treated as full certification.
- Review theorem extraction behavior before release.
- Manually verify the local document path in the trace.

## Failure Taxonomy Summary

| Failure type | Count | Meaning |
|---|---:|---|
| `TASK_INCOMPLETE` | 1 | The theorem extraction task was not fully completed. |
| `OUTPUT_FORMAT_ERROR` | 1 | Markdown headings did not match the expected structure. |

## Recommendation

Run deep diagnosis before trusting this agent in production:

```bash
agentdoctor deep --rounds 3 --review on-fail
```
