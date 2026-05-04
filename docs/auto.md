# Auto Mode

Auto mode runs automatic diagnosis and limited safe repair. It tests the agent, classifies failures, proposes safe prompt/config changes, applies low-risk allowlisted changes when possible, validates, and repeats until a stopping condition is reached.

Auto should be used carefully. Diagnostic confidence is a deterministic heuristic, not a mathematical probability or formal guarantee.

## Command

```bash
agentdoctor auto --target-confidence 0.85
```

Common variants:

```bash
agentdoctor auto --target-confidence 0.85
agentdoctor auto --target-confidence 0.90 --max-rounds 8
agentdoctor auto --target-confidence 0.90 --max-rounds 8 --max-time-minutes 30
agentdoctor auto --target-confidence 0.85 --max-patches 4 --review on-fail
agentdoctor auto --target-confidence 0.85 --save-baseline
agentdoctor auto --target-confidence 0.85 --compare-baseline
```

Current auto mode does not expose `--preview-patches` or `--require-patch-approval`. Use preview-only patch review separately:

```bash
agentdoctor patch-preview --from-run reports/latest.json
```

## Target Confidence

Recommended target confidence range:

```text
0.80 to 0.90
```

Targets such as `0.95` or higher are risky because they can encourage overfitting, long runs, and fragile prompt/config edits. Auto prints stronger warnings for very high targets.

## Heuristic Confidence Warning

AgentDoctor combines available weighted components such as key task pass rate, tool-call correctness, output schema score, regression score, stability score, and safety score. Missing components are normalized instead of crashing.

This number is a diagnostic heuristic. It is useful for comparing runs, triggering stop conditions, and summarizing progress. It is not proof that the agent is correct or safe.

## Safe Patch Boundaries

Auto uses `SafePatcher` and refuses unsafe targets. Default safe targets include:

- `prompts/*.md`
- prompt-like `.md`, `.txt`, `.yaml`, or `.yml` files
- `agent.yaml`, `agent.yml`
- `tool_descriptions.yaml`, `tool_descriptions.yml`
- `workflow_config.yaml`, `workflow_config.yml`
- `eval_config.yaml`, `eval_config.yml`

Auto refuses:

- source code such as `.py`, `.js`, `.ts`, `.go`, `.rs`, `.java`
- `.env` and secret-like files
- lock files such as `poetry.lock`, `uv.lock`, `package-lock.json`
- report and trace directories
- `.git`, `__pycache__`, and unsafe paths
- names containing auth, secret, token, credential, permission, or api

## Stopping Conditions

Auto stops when:

- target confidence is reached
- max rounds is reached
- max time is reached
- max patches is reached
- improvement is too small for repeated rounds
- a high-risk patch is required
- human review is required
- validation detects a regression and rolls back
- safety, forbidden tool, regression, scorer-uncertain, or unknown findings block continuation

## Patch History

When auto applies a safe patch, the diagnostic report includes patch history. Diffs are written under:

```text
reports/patches/patch_001.diff
```

Patch history records:

- round index
- previous confidence
- new confidence
- files changed
- patch summary
- reason for patch
- diff path
- regression detection
- rollback state

## Overfitting Warning

Auto mode can improve agent behavior against the current diagnostic test set, but it may also overfit to those tests. Use holdout tests, baseline comparison, and human review before trusting auto-generated changes.

Auto reports can include holdout confidence and overfitting warnings when diagnostic improvement does not generalize or when the test set is too small.

## Efficiency Warning

Auto tracks elapsed runtime, patch attempts, confidence improvement, slow/repeated failure types, and low-improvement rounds. It can warn when continued auto-repair is becoming inefficient.

Example warning:

```text
The last two rounds improved confidence by less than 0.03.
Further auto-repair may be inefficient.
```

## Human Review Recommendation

Use auto only after a triage or deep run has shown:

- clear safe patch targets
- usable eval coverage
- no unresolved high-risk tool policy
- review policy chosen
- baseline available or intentionally deferred
- target confidence in a conservative range

After auto, inspect `reports/latest.md`, `reports/latest.json`, any `reports/patches/*.diff` files, and baseline comparison before keeping generated changes.
