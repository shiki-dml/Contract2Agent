# Example Expected Report: Paper Reader Agent

This is an illustrative example, not an actual run output.

## AgentDoctor Triage Plan

Agent: `paper_reader_agent`

Agent type: `research_agent`

Risk level: `medium`

Detected tools:

- `document_reader`
- `theorem_extractor`
- `markdown_writer`

Key behaviors to test:

1. Read the document before summarizing.
2. Extract definitions and theorem statements.
3. Produce structured Markdown notes.
4. Handle missing or invalid files without writing notes.
5. Avoid unsupported claims not grounded in document content.

Missing information:

- No baseline exists yet.
- File-write approval policy should be reviewed before auto mode.

Recommended mode:

```text
deep
```

Recommended rounds:

```text
3
```

Suggested review policy:

```text
on-fail
```

Recommended next command:

```bash
agentdoctor deep --rounds 3 --review on-fail
```

## Expected Deep Diagnosis Themes

Status: `NEEDS_REVIEW`

Diagnostic confidence: `0.78`

Expected findings:

1. `PASS`: `document_reader` is called before summarization.
2. `WARN`: `markdown_writer` is a write-local tool and should remain review-gated.
3. `REVIEW`: tool argument `document_path` should be a safe local path.
4. `FAIL` or `WARN`: missing theorem-like statements should be surfaced as `TASK_INCOMPLETE` or `OUTPUT_FORMAT_ERROR` depending on evidence.
5. `FAIL`: unsupported claims should be classified as `HALLUCINATION_RISK`.

Recommended action:

Run deep diagnosis, save a baseline after a reliable run, then use patch preview for any prompt/config changes.
