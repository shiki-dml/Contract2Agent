# AgentDoctor Examples

This directory contains GitHub-readable examples for AgentDoctor. The sample reports are illustrative examples, not actual run outputs from this repository checkout.

## Example Agents

| Example | What it demonstrates |
|---|---|
| [Paper reader agent](paper-reader-agent/README.md) | Triage, document reading, tool-call order, Markdown output, missing-file handling, and source grounding. |

## Sample Reports

| Report | What it shows |
|---|---|
| [Quick report](reports/quick-report.md) | Single-round smoke diagnosis with pass/fail/warn/review items. |
| [Deep report](reports/deep-report.md) | Multi-round diagnosis, taxonomy summary, baseline comparison, time cost, and recommendations. |
| [Auto report](reports/auto-report.md) | Target confidence, patch summary, warnings, efficiency signals, and human review recommendation. |

## Typical Workflow

```bash
agentdoctor triage --agent examples/paper-reader-agent/agent.yaml
agentdoctor quick
agentdoctor deep --rounds 3 --review on-fail
agentdoctor patch-preview --from-run reports/latest.json
agentdoctor auto --target-confidence 0.85 --max-rounds 6 --review on-fail
```

The current quick/deep/auto implementation uses deterministic offline traces and can run without an LLM API key.
