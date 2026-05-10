# Privacy Eval

`privacy-eval` is a static pre-runtime privacy-risk evaluator for AI agent
profiles. It complements `file-eval`: file-reading checks whether an agent can
answer from bounded files, while privacy-eval checks whether a proposed agent
workflow exposes sensitive data through output, internal agent messages, memory,
tool calls, logs, artifacts, vector stores, or private-training updates.

It does not install or run privacy libraries. It records what should be checked
before deployment and keeps external projects and papers as contextual
references.

## GitHub Reference Comparison

The feature was shaped by these public projects:

- AgentLeak covers full-stack privacy leakage across output, internal messages,
  tools, memory, logs, and artifacts. `privacy-eval` borrows the channel idea,
  but keeps it as static profile analysis unless a local trace is supplied later.
- AgentDojo evaluates prompt-injection attacks and defenses for LLM agents.
  `privacy-eval` adds privacy-specific findings when untrusted tool or retrieval
  input can mix with private context.
- Opacus is a PyTorch differential-privacy training library. `privacy-eval`
  checks for DP training metadata such as epsilon, delta, clipping, noise, and
  accountant configuration, but does not execute a training run.
- OpenDP is a differential-privacy algorithm library. `privacy-eval` uses it as
  a reference for explicit DP mechanism metadata and proof boundaries.
- The BLT-DP-FTRL paper motivates a check for multi-participation federated
  private learning that still uses tree aggregation.

The innovation is the combined profile: agent-channel leakage plus DP/private
training readiness in one reproducible report.

## Command

```bash
python -m contract2agent.cli privacy-eval \
  --profile examples/privacy_eval/healthcare_multi_agent_privacy.json \
  --out .runs/privacy-healthcare.md
```

JSON output:

```bash
python -m contract2agent.cli privacy-eval \
  --profile examples/privacy_eval/federated_keyboard_blt_profile.json \
  --format json \
  --out .runs/privacy-keyboard.json
```

Reference metadata:

```bash
python -m contract2agent.cli privacy-eval --list-references
```

## Profile Shape

A profile records:

- sensitive data categories
- data flows by channel
- tool privacy properties
- declared controls
- private-training and DP metadata
- forbidden disclosures and policy constraints

The evaluator returns:

- overall privacy readiness
- leakage risk score
- channel coverage
- DP readiness
- prompt-injection privacy resilience
- auditability, minimization, and approval safety
- findings, recommendations, references, and limitations

## Example Set

See `examples/privacy_eval/README.md` for healthcare multi-agent, federated
keyboard BLT-DP-FTRL, and RAG customer-support examples.

## Limitations

- Static analysis does not prove runtime privacy behavior.
- No AgentLeak, AgentDojo, Opacus, OpenDP, or BLT benchmark run is executed.
- DP parameters are checked for readiness, not mathematically verified.
- Real privacy claims require observed traces, accountant outputs, and
  deployment-specific review.
