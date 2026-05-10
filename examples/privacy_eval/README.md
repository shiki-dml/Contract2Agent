# Privacy Eval Examples

This directory contains static example profiles for `c2a privacy-eval`. They do
not call external APIs, train models, run benchmarks, or prove privacy claims.

## Examples

- `healthcare_multi_agent_privacy.json`: multi-agent healthcare workflow with
  inter-agent, tool-call, and log leakage risks.
- `federated_keyboard_blt_profile.json`: on-device keyboard language-model
  update workflow with BLT-style DP-FTRL metadata.
- `rag_customer_support_privacy.json`: customer-support RAG workflow with vector
  store, output, and artifact privacy checks.

## Commands

```bash
python -m contract2agent.cli privacy-eval --profile examples/privacy_eval/healthcare_multi_agent_privacy.json --out .runs/privacy-healthcare.md
python -m contract2agent.cli privacy-eval --profile examples/privacy_eval/federated_keyboard_blt_profile.json --format json --out .runs/privacy-keyboard.json
python -m contract2agent.cli privacy-eval --list-references
```

Generated `.runs/` reports are local artifacts and should not be committed.
