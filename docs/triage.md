# Triage

Triage is the pre-diagnosis intake stage. It runs before formal testing and inspects the available project context: agent configuration, prompt text, tool descriptions, eval configuration, baseline state, and safe patch targets.

Think of triage as the doctor asking questions before making a diagnosis. It does not run the agent, call tools, execute shell commands, contact external services, or apply patches.

## Command

```bash
agentdoctor triage --agent ./agent.yaml
```

Useful variants:

```bash
agentdoctor triage
agentdoctor triage --goal "paper reading agent"
agentdoctor triage --project-root .
agentdoctor triage --allow-auto
agentdoctor triage --include-cost
agentdoctor triage --format json
```

## Inputs

Triage discovers common project files:

- agent configs: `agent.yaml`, `agent.yml`, `agent.json`, `agents/*.yaml`
- prompts: `prompts/*.md`, `prompt.md`, `system_prompt.md`, `instructions.md`
- tools: `tool_descriptions.yaml`, `tools.yaml`, `workflow_config.yaml`
- evals: `eval_config.yaml`, `evals/*.yaml`, `tests/evals/*.yaml`
- baselines: `.agentdoctor/baselines/latest.json`
- AgentDoctor config: `.agentdoctor/config.yaml`, `agentdoctor.yaml`

It excludes secrets, credentials, virtual environments, build outputs, and unreadable or oversized files.

## TriagePlan Fields

The JSON report contains a `TriagePlan` with these major fields:

| Field | Meaning |
|---|---|
| `triage_id` | Timestamped triage id. |
| `created_at` | Creation timestamp. |
| `project_root` | Scanned project root. |
| `input_sources` | Found/missing/skipped agent, prompt, tool, eval, baseline, and AgentDoctor config sources. |
| `agent_summary` | Agent name, description, model/provider, prompt files, config files, tool count, eval count. |
| `detected_capabilities` | Detected tools, inputs, outputs, side effects, external dependencies. |
| `agent_classification` | Agent type and classification confidence. |
| `risk_assessment` | Risk level, risk score, high-risk tools, missing safety controls, recommended review policy. |
| `eval_coverage` | Covered, missing, weak, and recommended test areas. |
| `key_behaviors_to_test` | Prioritized behaviors to test first. |
| `missing_information` | Missing output schema, missing baseline, missing tool order, missing safety rules, and similar gaps. |
| `warnings` | Non-blocking concerns from discovery and classification. |
| `suggested_test_tags` | Tags that should shape quick/deep/auto tests. |
| `suggested_round_plan` | Mode, rounds, review policy, and round focus. |
| `baseline_status` | Whether a baseline exists and whether it may be stale or mismatched. |
| `patch_preview_readiness` | Whether safe prompt/config patch targets were found. |
| `auto_readiness` | Whether auto mode is eligible and which blockers exist. |
| `estimated_diagnostic_cost` | Static rough estimate embedded in the triage report. |
| `recommendation` | Recommended mode, rounds, review policy, confidence target when relevant. |
| `recommended_next_command` | Concrete next command. |
| `report_paths` | Markdown and JSON report paths. |

## Agent Types

Triage can classify common agent types:

- `research_agent`
- `coding_agent`
- `workflow_agent`
- `data_analysis_agent`
- `file_operation_agent`
- `general_tool_agent`
- `chat_agent`
- `unknown`

Classification confidence is about agent-type detection only. It is not diagnostic confidence.

## Risk Levels

| Risk | Meaning |
|---|---|
| `low` | No tools or low-side-effect behavior was detected. |
| `medium` | Read-only tools, external reads, multiple tools, or incomplete coverage were detected. |
| `high` | Write, shell/code execution, external-write, destructive, or high-risk tools were detected. |
| `unknown` | Core config is missing/unreadable or risk cannot be reliably inferred. |

## Recommended Mode Logic

Current recommendation behavior:

- Low risk with a known agent type usually recommends `quick`.
- Medium risk usually recommends `deep --rounds 3 --review on-fail`.
- High risk recommends `deep --rounds 5 --review each-round`.
- Unknown risk or unknown agent type recommends selecting an agent config or running deep.
- Auto is considered only when `--allow-auto` is passed and readiness checks pass.

Auto readiness requires clear patch boundaries, an agent config, prompt/config content, eval cases, known agent type, known non-high risk, safe patch targets, and appropriate safety controls. Auto should only be used when review policy and patch boundaries are clear.

## Example Output

```text
AgentDoctor Triage Plan

Agent: paper_reader_agent
Agent type: research_agent
Risk level: medium

Detected tools:
- document_reader
- theorem_extractor
- markdown_writer

Key behaviors to test:
1. Read the document before summarizing.
2. Extract definitions and theorem statements.
3. Produce structured Markdown notes.
4. Handle missing or invalid files.
5. Avoid unsupported claims not grounded in the input document.

Missing information:
- No explicit output schema found.
- No max tool-call limit found.
- No baseline exists yet.

Recommended mode:
deep

Recommended rounds:
3

Suggested review policy:
on-fail

Recommended next command:
agentdoctor deep --rounds 3 --review on-fail
```

## Reports

Triage writes:

```text
.agentdoctor/triage/latest.md
.agentdoctor/triage/latest.json
.agentdoctor/triage/triage_<timestamp>.md
.agentdoctor/triage/triage_<timestamp>.json
```

Use the Markdown report for review and the JSON report for automation or CI.
