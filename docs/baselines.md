# Baselines

Baselines are saved diagnostic states used for regression comparison. They help answer whether the agent got better or worse after a prompt, config, tool-description, model, eval, or auto-repair change.

## Save a Baseline

Use deep mode for the strongest baseline:

```bash
agentdoctor deep --rounds 3 --save-baseline --baseline-name stable-v1
```

Quick and auto can also save baselines:

```bash
agentdoctor quick --save-baseline
agentdoctor auto --target-confidence 0.85 --save-baseline
```

Quick baselines are smoke-test references. For release or regression workflows, prefer a deep baseline.

## Compare a Baseline

```bash
agentdoctor deep --rounds 3 --compare-baseline
agentdoctor deep --rounds 3 --compare-baseline latest
agentdoctor deep --rounds 3 --compare-baseline stable-v1
agentdoctor auto --target-confidence 0.85 --compare-baseline
```

Bare `--compare-baseline` is normalized to `latest`.

## Baseline Contents

Baseline records include:

- `baseline_id`
- `baseline_name`
- `created_at`
- baseline quality and warnings
- command used
- mode
- agent identity
- diagnostic confidence
- pass/fail/warning counts
- findings summary
- failure taxonomy summary
- test result summary
- review summary
- time-cost summary
- patch summary
- eval suite summary
- report paths
- AgentDoctor version
- reference to the agent state snapshot

## Snapshot Contents

Each baseline saves an `AgentStateSnapshot` with prompt/config state:

- safe config file hashes
- copied safe config files up to 1 MB
- agent config snapshot
- prompt file metadata
- tool configuration summary
- workflow/review/approval state
- eval suite metadata
- patch history summary
- git commit and dirty-state metadata when available
- Python/platform metadata
- excluded file patterns
- snapshot warnings

Safe snapshot files include:

```text
agent.yaml, agent.yml, agent.json
prompts/*.md, prompts/*.txt
prompt.md, system_prompt.md, instructions.md
tool_descriptions.yaml, tool_descriptions.yml
tools.yaml, tools.yml
workflow_config.yaml, workflow_config.yml
eval_config.yaml, eval_config.yml
agentdoctor.yaml, agentdoctor.yml
.agentdoctor/config.yaml, .agentdoctor/config.yml
```

Eval files such as `evals/*.yaml`, `tests/evals/*.yaml`, and `.agentdoctor/evals/*.json` are hashed and included in eval-suite comparison metadata.

## Secret Exclusions

Snapshots must exclude:

- `.env`, `.env.*`
- API keys
- credentials
- private tokens
- auth files
- `*.key`, `*.pem`, `*.crt`
- `secrets.*`, `credentials.*`, `token.*`, `auth.*`
- sensitive local files
- virtual environments, build output, and `.git/`

Secret contents are not read, copied, printed, or written to reports.

## Output Layout

Baseline artifacts are local files under `.agentdoctor/`:

```text
.agentdoctor/
  baselines/
    latest.json
    baseline_<timestamp>/
      baseline.json
      snapshot.json
      file_hashes.json
      baseline_saved.md
      comparison_latest.json
      comparison_latest.md
      copied_configs/
```

## Example Comparison

```text
Baseline Comparison

Confidence: 0.82 -> 0.76 (-0.06)

Regressions:
1. markdown_schema: passed -> failed
2. tool_sequence: score 0.91 -> 0.62

Improvements:
1. missing_file_handling: failed -> passed

Changed config files:
- prompts/system.md
- tool_descriptions.yaml
```

## What Comparison Detects

Baseline comparison can detect:

- confidence deltas
- pass/fail/warning deltas
- test regressions
- test improvements
- new and removed tests
- failure type changes
- severity changes
- prompt/config/tool/workflow/eval hash changes
- model changes
- tool-list changes
- approval-policy changes
- git commit changes
- dirty-state changes
- runtime increases when timing data exists
- rollback recommendations for severe regressions

## Regression Workflow

1. Run `agentdoctor deep --rounds 3 --save-baseline --baseline-name stable-v1`.
2. Change prompts, tool descriptions, workflow, or eval config.
3. Run `agentdoctor deep --rounds 3 --compare-baseline stable-v1`.
4. Review `comparison_latest.md`.
5. Use patch preview or rollback review when regressions appear.

Baselines do not prove correctness. They make behavior changes visible and reviewable.
