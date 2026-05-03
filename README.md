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

## Failure Taxonomy v0.1

Failure taxonomy turns raw test, scorer, trace, and baseline failures into
structured diagnostic findings. These findings drive reports, deep mode
planning, auto repair strategy selection, patch previews, baseline comparison,
time-cost warnings, rollback decisions, and human review gates.

Failure types are stable machine-readable labels:

- `CONFIG_ERROR`
- `TASK_INCOMPLETE`
- `TOOL_MISSING`
- `TOOL_ORDER_ERROR`
- `TOOL_ARGUMENT_ERROR`
- `FORBIDDEN_TOOL_CALL`
- `OUTPUT_FORMAT_ERROR`
- `OUTPUT_SCHEMA_ERROR`
- `ERROR_HANDLING_MISSING`
- `HALLUCINATION_RISK`
- `LOOP_RISK`
- `LOW_STABILITY`
- `REGRESSION`
- `SAFETY_RISK`
- `SCORER_UNCERTAIN`
- `UNKNOWN`

Severity is tracked separately as `info`, `warning`, `error`, or `critical`.
This lets the same failure type have different operational impact in different
contexts. For example, a missing Markdown heading can be an
`OUTPUT_FORMAT_ERROR` warning, while a broken API JSON contract can be an
`OUTPUT_SCHEMA_ERROR` error.

Triage and diagnostic modes use different evidence levels:

- Triage produces potential risks. A missing source-grounding instruction can
  reference `HALLUCINATION_RISK`, but triage has not run a failing test.
- Quick, deep, and auto produce actual findings. A failed citation scorer can
  produce a `HALLUCINATION_RISK` finding with trace/scorer evidence.

Failure types guide updates directly:

- `TOOL_MISSING` routes to prompt or tool-description updates and validates
  with `tool_use` and `tool_order` tests.
- `OUTPUT_SCHEMA_ERROR` routes to strict schema instructions and validates with
  `json_schema` or `output_schema` tests.
- `SAFETY_RISK` and `FORBIDDEN_TOOL_CALL` require human review and are not
  auto-applied.
- `SCORER_UNCERTAIN` routes to eval/scorer review instead of agent patching.
- `REGRESSION` compares baseline behavior and prefers rollback review.

Markdown reports include a `Failure Taxonomy Summary` section grouped by failure
type. JSON reports include machine-readable `findings`, `taxonomy_summary`,
failure-type counts, review-required finding ids, auto-fix eligible finding ids,
patch target candidates, next-round tags, baseline comparison fields, and
time-cost summaries.

Auto mode repairs failure type clusters, not individual failed tests. It stops
or requires review for safety findings, forbidden tool calls, dominant scorer
uncertainty, dominant unknown failures, and regressions introduced by patches.
Patch previews include the triggering failure types, related finding ids,
expected effect, validation tags, risk level, and approval requirements.

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
agentdoctor cost-estimate --from-triage .agentdoctor/triage/latest.json
agentdoctor quick
agentdoctor deep --rounds 3 --review on-fail
agentdoctor patch-preview --from-run reports/latest.json
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
agentdoctor triage --include-cost
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

## Patch Preview

`agentdoctor patch-preview` generates reviewable patch proposals from
diagnostic findings. It explains which failure types triggered the patch, shows
a unified diff when a safe target exists, estimates risk, records approval
requirements, and recommends validation tests.

Patch preview is the review gate between diagnosis and modification:

```text
Finding / GroupedFinding
-> FailureType
-> FixStrategy
-> PatchProposal
-> Patch Preview Report
```

Run it after quick or deep diagnosis:

```powershell
agentdoctor patch-preview --from-run reports/latest.json
agentdoctor patch-preview --from-run .agentdoctor/runs/latest.json --failure-type OUTPUT_SCHEMA_ERROR
agentdoctor patch-preview --from-findings .agentdoctor/reports/latest.json --output .agentdoctor/patches/
agentdoctor patch-preview --from-run reports/latest.json --format json
```

Patch preview writes:

```text
.agentdoctor/patches/latest.md
.agentdoctor/patches/latest.json
.agentdoctor/patches/patch_<timestamp>_<index>.md
.agentdoctor/patches/patch_<timestamp>_<index>.json
.agentdoctor/patches/patch_<timestamp>_<index>.diff
```

It does not silently apply patches, run full auto repair, patch secrets or
denied paths, or patch agent behavior for `SCORER_UNCERTAIN` or `UNKNOWN`
findings. Patch Preview v0.1 is preview-only even when a proposal is marked
eligible for a future auto-apply flow.

Example proposal excerpt:

```text
Target failure type: OUTPUT_SCHEMA_ERROR
Reason: The agent produced invalid JSON in output_schema tests.
Diff: adds "Return only valid JSON matching the required schema."
Validation command: agentdoctor deep --rounds 2 --review on-fail
Risk: medium
Requires approval: true
```

Risk levels:

- `low`: output-format prompt clarification, read-only tool trigger, or local
  error-handling instruction.
- `medium`: output schema, source grounding, tool argument, or read-only
  workflow sequence changes.
- `high`: tool-permission config changes, side-effectful workflows, or
  rollback of a non-trivial patch.
- `critical`: safety, forbidden-tool, shell/code execution, external-write, or
  permission-boundary changes.
- `unknown`: insufficient evidence to classify the change.

Approval rules:

- `SAFETY_RISK` and `FORBIDDEN_TOOL_CALL` always require approval and are never
  auto-applicable.
- `SCORER_UNCERTAIN` and `UNKNOWN` generate review-only proposals instead of
  agent prompt patches.
- Low-risk prompt patches may be eligible for a future auto-apply flow, but
  v0.1 still writes previews only.

Every proposal includes validation tags and a runnable validation command. Use
the proposal's validation tags with `agentdoctor deep --focus ...`, and use
`--compare-baseline` when validating behavior against a saved baseline.

## Time Cost Estimate

`agentdoctor cost-estimate` performs a static pre-run estimate of diagnostic
complexity, expected test volume, LLM/tool call ranges, runtime level, human
review burden, slow paths, and budget guardrails. It reads triage output, eval
metadata, tool metadata, baseline/history metadata when available, and explicit
budget options.

This is a rough static estimate, not measured runtime.

Example commands:

```powershell
agentdoctor cost-estimate --from-triage .agentdoctor/triage/latest.json
agentdoctor cost-estimate --mode deep --budget balanced
agentdoctor cost-estimate --mode auto --max-auto-iterations 4
agentdoctor cost-estimate --budget conservative --max-rounds 2 --max-tests 12
```

Cost estimate reports are written to:

```text
.agentdoctor/cost/latest.md
.agentdoctor/cost/latest.json
.agentdoctor/cost/cost_<timestamp>.md
.agentdoctor/cost/cost_<timestamp>.json
```

`triage --include-cost` runs triage and then writes the static cost estimate
from the generated triage JSON:

```powershell
agentdoctor triage --include-cost
```

What it does not do:

- It does not run tests.
- It does not call the agent.
- It does not call tools.
- It does not call LLM APIs.
- It does not report measured runtime.
- It does not estimate exact dollar cost unless measured pricing and usage data
  exists in the repo.

Example terminal summary:

```text
AgentDoctor Time Cost Estimate

Mode: deep
Complexity: medium
Estimate confidence: medium
Estimated rounds: 3
Estimated tests: 12-24
Runtime level: medium
Review burden: medium

Key cost drivers:
- Multiple tools
- Source-grounding validation
- No baseline found

Recommended guardrails:
- max_rounds: 3
- max_tests: 24
- max_tool_calls_per_test: 5
- stop_on_safety_risk: True

Recommended command:
agentdoctor deep --rounds 3 --review on-fail

Note:
This is a rough static estimate, not measured runtime.
```

Budget profiles:

- `conservative`: fast, bounded, low-risk diagnosis. It prefers quick or a
  small deep run, avoids auto by default, limits repeated runs, and stops on
  safety, regression, and loop risks.
- `balanced`: default reliable diagnosis. It follows the triage recommendation,
  uses moderate rounds/tests, keeps patch preview before repair, and includes
  regression-oriented guardrails.
- `thorough`: broader pre-release diagnosis. It allows more rounds, tests,
  regression, and stability checks. Auto is still only recommended when explicit
  readiness and safety conditions pass.

Failure-type cost risks are reflected in guardrails:

- `LOOP_RISK` can increase runtime through repeated tool calls or retries.
- `LOW_STABILITY` can require repeated validation runs.
- `TOOL_ARGUMENT_ERROR` can cause tool errors, retries, and fallback checks.
- `ERROR_HANDLING_MISSING` can waste calls after invalid inputs or tool
  failures.
- `HALLUCINATION_RISK` can add document reads, retrieval checks, citation
  checks, and sometimes LLM judge calls.
- `SAFETY_RISK` and `FORBIDDEN_TOOL_CALL` increase review burden and should
  stop auto mode.
- `REGRESSION` requires baseline comparison and can add validation loops.
- `SCORER_UNCERTAIN` and `UNKNOWN` lower confidence and usually require review
  or better instrumentation before repair.

The estimate is intentionally broad. It should help decide whether to start
with quick, deep, or auto; whether auto should be avoided; and which static
guardrails to set. It should not be treated as an actual runtime, actual token
count, or exact cost report. This is a rough static estimate, not measured
runtime.

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

## Baselines and Agent State Snapshots

An AgentDoctor baseline is a saved diagnostic reference for an agent: how the
agent performed under one mode, one configuration, and one eval/test suite. An
agent state snapshot is the matching saved state for that baseline: config,
prompt, tool, workflow, eval, model, patch, git, environment, and file-hash
metadata.

The distinction is intentional:

- Baseline = performance/result.
- Snapshot = agent state/config.

Use `deep` mode for stable baselines. `quick` can save a baseline, but it is an
incomplete smoke diagnosis and is usually a weaker regression reference.

Save a baseline:

```powershell
agentdoctor deep --rounds 3 --save-baseline
agentdoctor deep --rounds 3 --save-baseline --baseline-name stable-v1
agentdoctor quick --save-baseline
agentdoctor auto --target-confidence 0.85 --save-baseline
```

Compare a future run with the latest or a named baseline:

```powershell
agentdoctor deep --rounds 3 --compare-baseline
agentdoctor deep --rounds 3 --compare-baseline latest
agentdoctor deep --rounds 3 --compare-baseline stable-v1
agentdoctor auto --target-confidence 0.85 --compare-baseline
```

If you select an agent config, the same path is used for snapshot identity and
hashing:

```powershell
agentdoctor deep --agent ./agent.yaml --rounds 3 --save-baseline --baseline-name stable-v1
agentdoctor deep --agent ./agent.yaml --rounds 3 --compare-baseline stable-v1
```

Baseline artifacts are local JSON and Markdown files under `.agentdoctor/`:

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

`baseline.json` stores the `BaselineRecord`: diagnostic summary, confidence
summary, per-test statuses, failure taxonomy counts, review summary, measured
time data when available, patch history summary, eval suite summary, report
paths, baseline quality, and a reference to the snapshot.

`snapshot.json` stores the `AgentStateSnapshot`: agent identity, model state,
prompt state, tool state, workflow/review/approval state, eval state, patch
state, git state when available, runtime environment, stable SHA-256 file
hashes, copied safe config files, excluded file patterns, and warnings.

Safe snapshot files copied by default include:

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

Eval files such as `evals/*.yaml`, `evals/*.yml`, and `evals/*.json` are hashed
and included in eval-suite comparison metadata. Large allowlisted files over 1
MB are hashed when possible but not copied.

Secret and build/cache files are excluded and their contents are not read,
copied, printed, or written to reports:

```text
.env, .env.*, *.key, *.pem, *.crt
secrets.*, credentials.*, token.*, auth.*
node_modules/, .venv/, venv/, .git/, dist/, build/, __pycache__/
```

Baseline comparison detects:

- diagnostic confidence delta
- pass/fail/warning delta
- test regressions, improvements, new tests, and removed tests
- failure type changes such as `OUTPUT_SCHEMA_ERROR: 0 -> 3`
- severity changes such as new critical findings
- prompt/config/tool/workflow/eval hash changes
- eval suite changes that make comparison partial
- model, tool-list, review/approval, git, and dirty-state changes
- measured runtime increases when timing data exists
- rollback recommendations for severe regressions

Failure taxonomy is stored even when only deterministic local inference is
available. Future taxonomy modules can populate the same fields directly.
Comparison tracks counts such as `SAFETY_RISK: 0 -> 1` and uses new critical
`SAFETY_RISK` or `FORBIDDEN_TOOL_CALL` evidence as strong rollback signals.

Auto mode can use baseline comparison data to detect regressions, overfitting,
and rollback candidates. In v0.1, AgentDoctor writes the comparison and
recommendation; it does not automatically roll back baseline files as part of
baseline comparison.

Limitations in v0.1:

- Baselines are local files only; there is no database or cloud sync.
- Comparison is partial when eval suites, modes, or metadata differ.
- Possible causes are candidate explanations, not definitive root causes.
- Token or dollar costs are not invented when usage data is unavailable.

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
