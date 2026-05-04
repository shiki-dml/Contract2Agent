# Configuration

AgentDoctor reads a bounded set of agent, prompt, tool, eval, baseline, and AgentDoctor config files. It excludes secrets, credentials, virtual environments, build output, and unreadable or oversized files from triage and snapshot content.

## Common Project Files

| File | Purpose |
|---|---|
| `agent.yaml`, `agent.yml`, `agent.json` | Main agent metadata, model, tools, workflow, output contract. |
| `agents/*.yaml`, `agents/*.yml`, `agents/*.json` | Alternative named agent configs. Use `--agent` to select one. |
| `prompts/*.md`, `prompts/*.txt` | Prompt files inspected by triage and allowed as safe patch targets. |
| `prompt.md`, `system_prompt.md`, `instructions.md` | Root-level prompt files. |
| `tool_descriptions.yaml`, `tool_descriptions.yml` | Tool metadata and descriptions. |
| `tools.yaml`, `tools.yml`, `agent_tools.yaml` | Additional tool config names recognized by triage/patch preview. |
| `workflow_config.yaml`, `workflow_config.yml` | Workflow, review, approval, limits, and tool-order policy. |
| `eval_config.yaml`, `eval_config.yml` | Evaluation metadata and scoring hints. |
| `evals/*.yaml`, `evals/*.yml`, `evals/*.json` | Eval cases discovered by triage and baseline snapshots. |
| `agentdoctor.yaml`, `agentdoctor.yml`, `.agentdoctor/config.yaml` | AgentDoctor-specific local configuration. |

## Minimal Agent Config

```yaml
name: paper_reader_agent
description: Reads local research papers and produces structured notes.
model:
  provider: openai
  name: gpt-test
  temperature: 0.2
tools:
  - name: document_reader
    description: Read a local PDF or text document.
  - name: theorem_extractor
    description: Extract definitions and theorem-like statements.
  - name: markdown_writer
    description: Write Markdown notes.
output:
  format: markdown
workflow:
  review_policy: on-fail
  max_tool_calls: 5
  forbidden_tools:
    - web_search
```

Triage extracts `agent_name`, description, model/provider fields, tools, detected inputs, detected outputs, prompt signals, safety controls, eval coverage, and baseline status from these files.

## Prompt Files

Prompt files are used for triage signals and safe patch targets. Useful prompt content includes:

- required tool-use triggers
- tool-call order
- output format or schema
- missing-input and tool-error behavior
- source-grounding rules
- human approval and safety boundaries
- max tool-call or repeated-call limits

## Tool Description Files

Tool descriptions help triage classify tools by category and risk. A tool named `document_reader` is usually read-only. A tool named `file_writer`, `email_sender`, `shell`, or `database_writer` increases risk and may trigger stricter review.

```yaml
tools:
  - name: document_reader
    description: Read a local document and return extracted text.
    side_effect_level: read_only
  - name: markdown_writer
    description: Write Markdown notes to a local file.
    side_effect_level: write_local
```

## Eval Configuration

Eval files can contain cases, tests, tags, scorers, and assertions. Triage uses these to estimate coverage and cost. Tags such as `task_completion`, `tool_use`, `output_format`, `error_handling`, `safety`, `source_grounding`, `regression`, and `stability` improve recommendations.

```yaml
cases:
  - id: read_before_summary
    tags: [task_completion, tool_use, tool_order]
  - id: missing_file_recovery
    tags: [error_handling, safety]
  - id: markdown_schema
    tags: [output_format, regression]
```

## AgentContract Files

Quick, deep, and auto can use an `agent_contract.yaml` through `--contract`. If no contract is provided, AgentDoctor uses a built-in paper-reader sample contract.

The contract schema includes:

- `name`
- `goal`
- `tools`
- `forbidden_tools`
- `forbidden_capabilities`
- `rules`
- `output`
- `limits`

Example:

```yaml
name: paper_reader_agent
goal: Read a PDF paper and write structured notes.
tools:
  - name: pdf_reader
    type: read_only
  - name: markdown_writer
    type: side_effect
forbidden_tools:
  - web_search
rules:
  - name: must_read_before_write
    description: markdown_writer requires a successful pdf_reader call first.
    kind: require_tool_before_tool
    params:
      tool: markdown_writer
      required_tool: pdf_reader
      required_status: ok
output:
  format: markdown
  must_contain: [Definitions, Theorems, Proof ideas]
limits:
  max_steps: 6
```

## Snapshot Behavior

Baselines save an `AgentStateSnapshot` next to the baseline. Snapshots help connect behavior changes to prompt/config changes.

Snapshots may include:

- `agent.yaml`, `agent.yml`, `agent.json`
- `prompts/*.md`, `prompts/*.txt`
- `prompt.md`, `system_prompt.md`, `instructions.md`
- `tool_descriptions.yaml`, `tool_descriptions.yml`
- `tools.yaml`, `tools.yml`
- `workflow_config.yaml`, `workflow_config.yml`
- `eval_config.yaml`, `eval_config.yml`
- `agentdoctor.yaml`, `agentdoctor.yml`
- `.agentdoctor/config.yaml`, `.agentdoctor/config.yml`
- eval file hashes from `evals/`, `tests/evals/`, `agentdoctor_tests/`, and `.agentdoctor/evals/`
- command used
- timestamp
- AgentDoctor version
- Python/platform metadata
- git commit and dirty-state metadata when available
- stable SHA-256 file hashes
- copied safe config files up to 1 MB

## Secret Exclusions

Snapshots, triage, patch preview, and cost estimate must exclude secret-like files and directories:

- `.env`, `.env.*`
- `*.key`, `*.pem`, `*.crt`
- `secrets.*`, `credentials.*`, `token.*`, `auth.*`
- private tokens and API keys
- `node_modules/`, `.venv/`, `venv/`, `.git/`, `dist/`, `build/`, `__pycache__/`

Secret contents are not read, copied, printed, or written to reports. This is why some reports may mention that files were excluded without showing their contents.
