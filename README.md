# AgentTraceDoctor

Trace-based diagnosis and repair suggestions for LLM agents.

AgentTraceDoctor is a lightweight offline CLI tool for trace-based diagnosis of
LLM agent behavior. Its main focus is not simply generating agents. Its main
focus is checking agent execution traces, diagnosing which part of the agent
system is too loose or too strict, and giving actionable repair suggestions.

AgentTraceDoctor is not an autonomous agent platform. It is a debugging layer
for agent behavior. It uses contracts, traces, counterexamples, and
deterministic diagnosis rules to help developers understand where an agent
system is too loose, too strict, or underspecified.

Instead of only reporting PASS or FAIL, AgentTraceDoctor explains the likely
cause in natural language and suggests where to modify the contract, checker,
monitor, parser, prompt, or eval dataset.

The Python package is still named `contract2agent`, and the CLI command is
currently `c2a` for compatibility. The tool stays deterministic and offline; it
does not call any LLM API.

The CLI also installs the `agentdoctor` command. `c2a` remains available for
compatibility, and both commands expose the same diagnostic modes.

## What It Does

AgentTraceDoctor checks agent execution traces against an `AgentContract` and
diagnoses failures in structured data and natural language.

AgentTraceDoctor does not only tell you that an agent failed. It tries to
explain why it failed, which part of the system is likely responsible, whether
the relevant rule is too loose or too strict, and what change should be made.

It is built for subtle LLM agent failures such as:

- calling tools in the wrong order
- calling forbidden tools
- writing files after a failed read
- ignoring missing-file errors
- producing output with missing required sections
- having checker rules that are too loose
- having checker rules that are too strict
- having monitor rules that fail to block unsafe actions
- having parser logic that misses natural-language restrictions
- having eval expectations that are too strict or ambiguous

Given a contract and traces, AgentTraceDoctor helps answer:

- What went wrong?
- Which part of the agent system is responsible?
- Is the rule too loose or too strict?
- Did the checker miss a violation?
- Did the monitor fail to block a forbidden action?
- Did the generated prompt fail to specify the required behavior?
- Did the parser miss a user restriction?
- Is the eval dataset too strict?
- What should the user change?

## Why Trace-Based Diagnosis

Final-output-only evals are useful, but they often miss where the failure
happened. An agent can produce a plausible final answer after using the wrong
tool, ignoring a tool error, or violating a runtime constraint.

Agent behavior is often defined by intermediate events:

- the order of tool calls
- whether forbidden tools were called
- whether tool errors stopped later side effects
- whether required output sections were produced
- whether checker logic rejected valid behavior
- whether monitor logic failed to block unsafe behavior

Trace-based diagnosis keeps those intermediate events visible. That makes it
easier to separate agent behavior failures from contract, checker, monitor,
parser, prompt, and eval-design problems.

## Core Workflow

The full workflow is:

```text
natural-language requirement
-> AgentContract
-> generated agent scaffold and eval harness
-> trace collection
-> trace checking
-> counterexample testing
-> strictness diagnosis
-> repair suggestions and regression traces
```

Scaffold generation is included to make the workflow runnable end to end, but
it is a supporting feature. The main value is trace checking, strictness
diagnosis, and repair guidance.

## Core Diagnosis Categories

- `contract_too_loose`: the contract does not express a restriction needed to
  reject the observed behavior.
- `contract_too_strict`: the contract forbids behavior that should be allowed.
- `checker_too_loose`: the contract has a rule, but the trace checker accepted
  a violating trace.
- `checker_too_strict`: the checker rejected a valid trace because its logic is
  broader than the intended rule.
- `monitor_too_loose`: the runtime monitor failed to block a forbidden action
  before or during execution.
- `monitor_too_strict`: the runtime monitor blocks behavior that the contract
  and checker should allow.
- `agent_prompt_too_weak`: the agent prompt does not clearly specify required
  behavior, formatting, refusal, or error handling.
- `parser_missed_constraint`: the natural-language requirement contained a
  restriction that was not captured in the contract.
- `eval_expectation_too_strict`: the eval requires a narrower output form than
  the contract or reasonable behavior implies.
- `eval_expectation_ambiguous`: the eval expectation is unclear or can be read
  in more than one reasonable way.
- `contract_conflict`: two contract requirements conflict or make the expected
  behavior internally inconsistent.
- `rule_uncovered`: a rule exists, but no current trace or eval case exercises
  it.
- `agent_behavior_failure`: the contract and checker are reasonable, but the
  agent behavior in the trace violates them.

## Example Diagnosis

Trace:

```text
pdf_reader returns file_not_found, but markdown_writer is still called.
```

Diagnosis:

```text
The agent's missing-file handling is too loose. The trace shows that pdf_reader returned file_not_found, but markdown_writer was still called. The agent should stop after a missing file and must not write notes.
```

Likely location:

```text
agent_contract.yaml or checker.py
```

Suggested fix:

```text
Add or enforce no_write_on_missing_file.
```

Suggested requirement rewrite:

```text
If the file cannot be read, the agent must stop and must not write notes.
```

## Quick Start

Install for local development:

```powershell
python -m pip install -e ".[dev]"
```

Recommended first commands:

```powershell
agentdoctor triage
agentdoctor quick
agentdoctor deep --rounds 3 --review on-fail
agentdoctor auto --target-confidence 0.85 --max-rounds 6
```

Generate the offline demo project:

```powershell
c2a demo --out demo_project
```

Generate deterministic counterexample traces:

```powershell
c2a counterexamples demo_project/agent_contract.yaml --out demo_project/traces/counterexamples
```

Check the traces and write diagnosis output:

```powershell
c2a check-all --contract demo_project/agent_contract.yaml --traces demo_project/traces/counterexamples --diagnose
```

Run diagnosis directly:

```powershell
c2a diagnose --contract demo_project/agent_contract.yaml --traces demo_project/traces/counterexamples --manifest demo_project/traces/counterexamples/manifest.yaml --out demo_project/reports/diagnosis_report.md
```

Explain one trace:

```powershell
c2a why --contract demo_project/agent_contract.yaml --trace demo_project/traces/passing_trace.json
```

Typical diagnosis outputs are written under:

```text
demo_project/reports/counterexample_report.md
demo_project/reports/diagnosis_report.md
```

## Upload to GitHub from PowerShell

Use PowerShell variables for repository placeholders. Avoid angle-bracket
placeholders such as `<owner>` or `<repo>` in commands, because PowerShell can
interpret them as redirection syntax.

```powershell
$GitHubUser = "your-github-username"
$RepoName = "AgentTraceDoctor"
$RemoteUrl = "https://github.com/$GitHubUser/$RepoName.git"

git status
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin $RemoteUrl
git push -u origin main
```

If `origin` already exists, update it instead of adding it again:

```powershell
git remote set-url origin $RemoteUrl
git push -u origin main
```

## Triage

`agentdoctor triage` performs a static pre-diagnosis of an agent project. It
detects the agent type, tools, risk level, missing configuration, eval coverage,
baseline status, safe patch-preview readiness, and whether the user should run
quick, deep, or auto diagnosis next.

Triage is the recommended first AgentDoctor command:

```powershell
agentdoctor triage
agentdoctor triage --agent ./agent.yaml
agentdoctor triage --goal "paper reading agent"
agentdoctor triage --project-root .
agentdoctor triage --allow-auto
```

Triage writes both human-readable and machine-readable reports:

```text
.agentdoctor/triage/latest.md
.agentdoctor/triage/latest.json
.agentdoctor/triage/triage_<timestamp>.md
.agentdoctor/triage/triage_<timestamp>.json
```

Example terminal output:

```text
Recommended next command:
agentdoctor deep --rounds 3 --review on-fail
```

Triage does not run the agent. It does not call tools, execute shell commands,
contact external services, apply patches, or require an LLM API key. Triage is
deterministic in v0.1 and only reads bounded prompt/config/eval metadata while
excluding secret files such as `.env`, keys, credentials, and large/unreadable
files.

Risk levels:

- `low`: no tools or only low-side-effect behavior was detected.
- `medium`: read-only, external-read, multiple-tool, or incomplete safety
  coverage was detected.
- `high`: write, shell/code execution, external-write, destructive, or unknown
  side-effect tools were detected.
- `unknown`: core config was missing or unreadable and no reliable risk
  conclusion can be made.

Classification confidence is about agent-type detection only, not diagnostic
confidence:

- `low`: signals are vague, missing, or conflicting.
- `medium`: one or two clear signals exist.
- `high`: multiple independent sources point to the same agent type.

Auto is not recommended by default. Pass `--allow-auto` if you want triage to
consider auto mode. Triage still avoids recommending auto when safe patch
boundaries, eval cases, approval policies, or other readiness checks are
missing.

## Diagnostic Modes

AgentTraceDoctor supports three AgentDoctor diagnostic modes:

`quick` is a fast smoke diagnosis for key behavior. It runs exactly one round,
selects high-priority tests for task completion, tool use, output format, and
error handling, and writes reviewable findings. It is incomplete by design and
must not be treated as full certification.

```powershell
agentdoctor quick
```

`deep` is a multi-round detailed diagnosis. It does not modify the agent. Round
1 focuses on basic functionality and key paths, round 2 adds more detailed tool,
format, and error-handling checks, and later rounds add boundary, regression,
stability, forbidden-tool, and malformed-trace checks.

```powershell
agentdoctor deep --rounds 3
agentdoctor deep --rounds 5 --review never
agentdoctor deep --rounds 5 --review on-fail
agentdoctor deep --rounds 5 --review each-round
```

`auto` is an automatic diagnosis and limited repair loop. It can modify only
allowlisted prompt/config files such as `prompts/*.md`, `agent.yaml`,
`tool_descriptions.yaml`, `workflow_config.yaml`, and `eval_config.yaml`. It
does not modify core Python or TypeScript source files by default. It stops when
the target confidence is reached or when a budget limit, low-improvement stop,
high-risk patch, rollback, or review condition blocks continuation.

```powershell
agentdoctor auto --target-confidence 0.85
agentdoctor auto --target-confidence 0.90 --max-rounds 8
agentdoctor auto --target-confidence 0.90 --max-rounds 8 --max-time-minutes 30
agentdoctor auto --target-confidence 0.90 --review on-fail
```

Review policies:

- `never`: never pause during the run, but still include review items in the
  final report.
- `on-fail`: require review when a round has failed tests, high-risk warnings,
  unsafe patch suggestions, or suspicious tool behavior.
- `each-round`: require review after every round before continuing.

In non-interactive CLI environments, AgentDoctor does not block forever waiting
for input. It marks `review_required=true` in the report and follows a safe
default for the mode.

## Diagnostic Confidence

Diagnostic confidence is a deterministic heuristic score, not a mathematical
probability and not a formal guarantee. It combines available weighted
components and normalizes missing components instead of crashing:

```text
0.30 * key_task_pass_rate
+ 0.20 * tool_call_correctness
+ 0.15 * output_schema_score
+ 0.15 * regression_score
+ 0.10 * stability_score
+ 0.10 * safety_score
```

Auto mode prints warnings before running:

- A high target confidence can cause overfitting to the generated diagnostic
  tests.
- Auto mode can require multiple test/repair rounds and consume significant
  time and tokens.
- Diagnostic confidence is heuristic and should not be treated as a formal
  guarantee.

If `--target-confidence` is `0.95` or higher, AgentDoctor prints a stronger
warning because very high targets can produce fragile prompt/config changes and
long inefficient runs. The recommended target confidence range is `0.80` to
`0.90`.

Mode reports are written to:

```text
reports/latest.md
reports/latest.json
reports/rounds/round_001.json
reports/patches/patch_001.diff
```

## Main Commands

Diagnosis and checking commands:

- `c2a check --contract agent_contract.yaml --trace traces/run.json`
  checks one saved trace against a contract and returns PASS or FAIL.
- `c2a check-all --contract agent_contract.yaml --traces traces/counterexamples`
  checks a directory of trace JSON files and writes a counterexample report.
- `c2a diagnose --contract agent_contract.yaml --traces traces/counterexamples --out reports/diagnosis_report.md`
  writes a structured diagnosis report for a trace set.
- `c2a why --contract agent_contract.yaml --trace traces/run.json`
  explains one trace in natural language.
- `c2a counterexamples agent_contract.yaml --out traces/counterexamples`
  generates deterministic violating traces and valid control traces.

Useful diagnosis options:

- `--manifest` supplies expected pass/fail outcomes and expected rules.
- `--requirement` lets diagnosis compare the contract with the original
  natural-language requirement.
- `--eval-dataset` lets diagnosis identify overly strict or ambiguous eval
  expectations.
- `--profile permissive|balanced|strict` controls how aggressively uncovered
  rules are reported.
- `--write-regression-traces` writes suggested regression trace JSON files.
- `--format markdown|yaml` controls diagnosis report format.

Supporting commands:

- `c2a new` creates a project from a natural-language requirement.
- `c2a compile` compiles an existing contract into a runnable scaffold.
- `c2a demo` creates the built-in offline demo project.
- `c2a restrictions` prints forbidden tools and forbidden capabilities.
- `c2a capabilities` prints inferred, verified, forbidden, missing-tool, and
  unsupported capabilities.

## What the Report Contains

`diagnosis_report.md` includes:

- natural-language cause
- affected agent part
- strictness: `too_loose`, `too_strict`, `ambiguous`, or `not_applicable`
- evidence from trace
- confidence
- responsibility attribution
- likely location
- suggested fix
- suggested patch
- suggested requirement prompt
- suggested agent prompt
- suggested regression trace
- rule coverage matrix

The report is designed to point at the next concrete repair, not to claim that
the agent is correct in all possible situations.

## Supporting Features

AgentTraceDoctor includes several supporting features so diagnosis can run
without external services:

1. Contract-first scaffold generation: creates a small deterministic agent
   scaffold and eval harness from an `AgentContract`.
2. Runtime monitor generation: emits local monitor code that can block
   forbidden tools and record trace events.
3. Counterexample-driven testing: generates likely violating traces and valid
   control traces for the checker.
4. User-defined forbidden capabilities: parses supported natural-language
   restrictions into forbidden tools and intent-level refusals.
5. Capability discovery and recommendation: summarizes verified, candidate,
   forbidden, missing-tool, and unsupported capabilities.
6. Markdown evaluation reports: writes local reports for eval and
   counterexample runs.

## Example AgentContract

A shortened paper-reader contract:

```yaml
name: paper_reader_agent
tools:
  - name: pdf_reader
    type: read_only
  - name: markdown_writer
    type: side_effect
forbidden_tools:
  - web_search
rules:
  - name: must_read_before_write
    kind: require_tool_before_tool
    params:
      tool: markdown_writer
      required_tool: pdf_reader
      required_status: ok
  - name: no_write_on_missing_file
    kind: forbid_tool_after_tool_error
    params:
      tool: markdown_writer
      after_tool: pdf_reader
      error_status: file_not_found
  - name: final_output_has_sections
    kind: final_output_contains
    params:
      items: [Definitions, Theorems, Proof ideas]
output:
  format: markdown
  must_contain: [Definitions, Theorems, Proof ideas]
limits:
  max_steps: 6
```

## Limitations

- Diagnosis is deterministic and heuristic, not formal verification.
- The tool does not prove semantic safety.
- The MVP is offline and template-based.
- The first supported template is `paper_reader_agent`.
- The natural-language parser is keyword-based.
- LLM-as-judge is not included in the MVP.
- The tool does not guarantee agent correctness or claim the agent has
  self-awareness.
- Auto mode does not implement `--allow-code-edits`; automatic repair is limited
  to allowlisted prompt/config files.
- Real production agent adapters are future work. The built-in modes use
  deterministic offline traces so tests do not require an LLM API key.

## Development

Run tests:

```powershell
python -m pytest
```

If plain Python is missing dependencies, use the project virtual environment:

```powershell
.venv_uv\Scripts\python.exe -m pytest
.venv_uv\Scripts\c2a.exe demo --out demo_project
```
