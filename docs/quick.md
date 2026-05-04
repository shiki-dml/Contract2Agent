# Quick Check

Quick is a single-round efficient diagnostic mode. It runs a small set of high-priority behavior checks and writes a human-reviewable report.

Quick is incomplete by design. It is useful for development checks, smoke tests after prompt/config changes, and deciding whether a deeper diagnostic run is needed. It should not be treated as full certification.

## Command

```bash
agentdoctor quick
```

Variants:

```bash
agentdoctor quick --contract ./agent_contract.yaml
agentdoctor quick --out reports/quick
agentdoctor quick --save-baseline --baseline-name quick-smoke
agentdoctor quick --compare-baseline
```

## What Runs

With the built-in paper-reader contract, quick selects six high-priority cases:

| Test id | Behavior |
|---|---|
| `AD001` | Read before summarization. |
| `AD002` | Extract theorem-like content. |
| `AD003` | Stop on missing file without writing notes. |
| `AD004` | Avoid forbidden web search. |
| `AD005` | Use Markdown heading structure. |
| `AD006` | Surface tool-call arguments for manual review. |

If you pass `--contract`, the contract affects forbidden tools and limits used by the deterministic checks.

## Output

Quick writes:

```text
reports/latest.md
reports/latest.json
reports/rounds/round_001.json
```

The Markdown report includes:

- status
- heuristic diagnostic confidence
- test counts
- key findings
- failure taxonomy summary
- review items
- recommended next round focus
- recommendations

The JSON report includes machine-readable `rounds`, `findings`, `taxonomy_summary`, `review_items`, and score fields.

## Example Output

```text
AgentDoctor Quick Diagnosis

Status: NEEDS_REVIEW
Diagnostic confidence: 0.72
Tests: 6 run, 4 passed, 1 failed, 1 warning

Key findings:
1. PASS: document_reader was called before summarization.
2. FAIL: expected theorem extraction, but no theorem-like statement was found.
3. WARN: final output is Markdown-like, but heading structure is incomplete.
4. REVIEW: tool call argument path="paper.pdf" should be manually checked.

Recommendation:
Run deep diagnosis before trusting this agent in production.
```

## Review Items

Quick always includes a review item explaining that quick mode is incomplete. Additional review items are generated when tests fail, warnings occur, suspicious tool behavior appears, or a test asks for manual argument review.

## Relation to Triage

Triage recommends quick when static risk is low and the agent type is known. If triage finds medium/high risk, missing safety controls, or incomplete eval coverage, use deep mode instead.

## Relation to Baselines

Quick can save a baseline:

```bash
agentdoctor quick --save-baseline --baseline-name quick-smoke
```

Use quick baselines only as smoke-test references. For regression decisions, prefer a reliable deep baseline:

```bash
agentdoctor deep --rounds 3 --save-baseline --baseline-name stable-v1
```
