# Sample AgentDoctor Deep Diagnosis

This is an illustrative example, not an actual run output.

Status: `NEEDS_REVIEW`

Diagnostic confidence: `0.78`

Rounds executed: `3`

Tests: `28` run, `22` passed, `4` failed, `2` warnings

## Per-Round Summary

| Round | Focus | Confidence | Summary |
|---|---|---:|---|
| 1 | Key task and tool-use paths | 0.82 | Read-before-write passed; theorem extraction was incomplete. |
| 2 | Output format and error handling | 0.79 | Markdown schema failed; missing-file handling passed. |
| 3 | Regression and stability | 0.78 | Tool sequence regression appeared in one boundary case. |

## Failure Taxonomy Summary

| Failure type | Count | Evidence | Suggested fix |
|---|---:|---|---|
| `TOOL_ORDER_ERROR` | 1 | Agent summarized before `document_reader` returned. | Clarify required tool sequence. |
| `OUTPUT_SCHEMA_ERROR` | 2 | Required Markdown section missing or malformed. | Add stricter output template. |
| `ERROR_HANDLING_MISSING` | 1 | Invalid input path was not surfaced clearly. | Add explicit invalid-input handling. |

## Baseline Comparison

Confidence: `0.82 -> 0.78 (-0.04)`

Regressions:

1. `markdown_schema`: passed -> failed
2. `tool_sequence`: score `0.91 -> 0.62`

Improvements:

1. `missing_file_handling`: failed -> passed

Changed config files:

- `prompts/system.md`
- `tool_descriptions.yaml`

## Time Cost

Total runtime: `4m 32s`

Rounds executed: `3`

Tests executed: `28`

Average test time: `9.7s`

Slowest test: `missing_file_recovery`

Efficiency warning:

```text
The final round produced little confidence improvement. Review failures manually before running auto mode.
```

## Recommendations

1. Review tool-call order and output schema before enabling auto mode.
2. Save a new baseline only after `markdown_schema` and `tool_sequence` pass.
3. Run patch preview for `OUTPUT_SCHEMA_ERROR` and `TOOL_ORDER_ERROR`.

```bash
agentdoctor patch-preview --from-run reports/latest.json
```
