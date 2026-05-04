# Paper Reader Agent Example

This example shows how an AgentDoctor-friendly agent configuration can describe a paper-reading workflow.

It is designed to exercise:

- triage intake
- document reading
- tool-call order
- theorem extraction
- structured Markdown output
- missing-file handling
- source-grounding and hallucination risk

## Files

| File | Purpose |
|---|---|
| [agent.yaml](agent.yaml) | Example agent configuration for triage and snapshot docs. |
| [expected-report.md](expected-report.md) | Example diagnostic report shape for this agent. |

## Triage

Run:

```bash
agentdoctor triage --agent examples/paper-reader-agent/agent.yaml --goal "paper reading agent"
```

Expected triage themes:

- agent type: `research_agent`
- risk level: `medium`
- detected tools: `document_reader`, `theorem_extractor`, `markdown_writer`
- key behaviors: read before summarizing, extract theorem statements, write Markdown, handle missing files, avoid unsupported claims
- recommended mode: usually `deep`
- recommended rounds: usually `3`
- suggested review policy: `on-fail`

## Diagnosis

Fast smoke check:

```bash
agentdoctor quick
```

Detailed diagnosis:

```bash
agentdoctor deep --rounds 3 --review on-fail
```

Save a baseline after a reliable run:

```bash
agentdoctor deep --rounds 3 --save-baseline --baseline-name paper-reader-stable
```

Preview patches after a diagnostic run:

```bash
agentdoctor patch-preview --from-run reports/latest.json
```

## Behaviors to Review

1. `document_reader` should be called before any summary or note-writing step.
2. `theorem_extractor` should be used or the final report should clearly state when no theorem-like content is found.
3. `markdown_writer` should only write after a successful document read.
4. Missing or invalid files should stop the workflow and avoid note-writing.
5. Factual claims should be grounded in document content, not prior knowledge.
