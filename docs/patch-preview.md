# Patch Preview

Patch preview is the human-reviewable diff layer before changing prompt/config files. It explains why a change is proposed, which finding triggered it, which files would change, what the diff is, the risk level, whether approval is required, expected effects, validation tags, and rollback guidance.

In v0.1, `agentdoctor patch-preview` is preview-only. It writes reports and diffs but does not modify files.

## Command

```bash
agentdoctor patch-preview --from-run reports/latest.json
```

Variants:

```bash
agentdoctor patch-preview --from-run reports/latest.json --failure-type OUTPUT_SCHEMA_ERROR
agentdoctor patch-preview --from-findings .agentdoctor/reports/latest.json --output .agentdoctor/patches/
agentdoctor patch-preview --from-run reports/latest.json --format json
agentdoctor patch-preview --apply patch_20260503_001
```

`--apply` and `--allow-apply` are accepted for forward compatibility, but v0.1 refuses to apply changes and records that no files were modified.

## PatchProposal Fields

Patch preview proposal fields include:

- `patch_id`
- `created_at`
- `source_run_id`
- `source_round_id`
- `related_finding_ids`
- `failure_types`
- `grouped_failure_summary`
- `reason`
- `patch_type`
- `strategy_id`
- `target_files`
- `files_changed`
- `diff`
- `before_summary`
- `after_summary`
- `expected_effect`
- `validation_tags`
- `validation_command`
- `regression_risks`
- `baseline_impact`
- `risk_level`
- `requires_approval`
- `auto_apply_eligible`
- `do_not_apply_automatically`
- `rollback_available`
- `rollback_plan`
- `reviewer_notes`

## Safe Allowlist

Patch preview recognizes safe targets such as:

- `prompts/*.md`, `prompts/*.txt`
- `prompt.md`, `system_prompt.md`, `instructions.md`
- `agent.yaml`, `agent.yml`, `agent.json`
- `.agentdoctor/agent.yaml`
- `tool_descriptions.yaml`, `tool_descriptions.yml`
- `tools.yaml`, `tools.yml`, `agent_tools.yaml`
- `workflow_config.yaml`, `workflow_config.yml`
- `eval_config.yaml`, `eval_config.yml`
- `evals/*.yaml`, `evals/*.yml`, `evals/*.json`
- `.agentdoctor/evals/*.yaml`, `.agentdoctor/evals/*.yml`, `.agentdoctor/evals/*.json`

Auto mode uses a stricter safe patcher. It refuses source-code and secret-like targets by default.

## Disallowed Files

Patch preview and auto mode must not patch:

- `.env`, `.env.*`
- secrets, credentials, tokens, keys, certificates
- source code implementing real tools
- auth logic
- filesystem permission logic
- external API integration logic
- generated reports
- baseline files
- lock files
- `.git/`, virtual environments, build output, cache directories

## Risk Levels

| Risk | Meaning |
|---|---|
| `low` | Prompt wording or output-format clarification with limited side effects. |
| `medium` | Schema, source-grounding, tool-argument, or eval-related change. |
| `high` | Tool permissions, workflow behavior, rollback, or side-effectful tool changes. |
| `critical` | Safety, forbidden tool, shell/code execution, destructive, or external-write risk. |
| `unknown` | Insufficient evidence to classify the change. |

`SAFETY_RISK` and `FORBIDDEN_TOOL_CALL` always require approval and are never auto-applicable. `SCORER_UNCERTAIN` and `UNKNOWN` are review-only by default.

## Dry-Run Behavior

Patch Preview v0.1 is always preview-only. The report says no files were modified. When a diff can be generated, it writes a `.diff` artifact. When no safe target exists, it creates a review-only proposal instead.

## Example Patch Preview

```text
Proposed Patch

Reason:
Agent failed to call document_reader before summarization.

Failure type:
TOOL_MISSING

File:
prompts/system.md

Diff:
- Summarize the document.
+ Before summarizing, always call document_reader on the provided file.
+ Do not answer from prior knowledge if a document path is provided.

Risk:
low

Expected effect:
Improves tool-call correctness for document-reading tasks.
```

## Output Files

```text
.agentdoctor/patches/latest.md
.agentdoctor/patches/latest.json
.agentdoctor/patches/patch_<timestamp>_<index>.md
.agentdoctor/patches/patch_<timestamp>_<index>.json
.agentdoctor/patches/patch_<timestamp>_<index>.diff
```

## Role in Auto Mode

Patch preview is the review workflow around auto repair. Auto mode can apply low-risk safe prompt/config changes internally, but reviewable diffs and patch reports remain important for deciding whether to keep, revert, or manually edit changes.
