# Failure Taxonomy

Failure taxonomy is the structured classification layer for diagnostic findings. Raw failures say what happened. Structured findings explain the class of problem, likely cause, review risk, and patch direction.

Raw failure:

```text
Expected document_reader to be called, but no tool call was recorded.
```

Structured finding:

```yaml
failure_type: TOOL_MISSING
likely_cause: The prompt did not clearly require document reading before answering.
suggested_fix: Add a tool-use instruction requiring document_reader before summarization.
```

This structure matters because auto repair, patch preview, baseline comparison, next-round planning, and human-readable reports need more than a pass/fail label.

## Failure Types

AgentDoctor v0.1 implements the requested taxonomy plus additional tool-argument, loop-risk, and scorer-uncertain categories used by the current code.

| Failure type | Meaning | Typical evidence | Likely cause | Suggested fix | Patch preview implication |
|---|---|---|---|---|---|
| `CONFIG_ERROR` | Configuration is incomplete, invalid, or inconsistent. | Missing agent config, malformed eval config, tool registry mismatch. | Project setup is incomplete or paths are wrong. | Fix agent, prompt, tool, workflow, or eval config before broader diagnosis. | Usually targets `agent.yaml`, `tool_descriptions.yaml`, `workflow_config.yaml`, or `eval_config.yaml`; requires review. |
| `TASK_INCOMPLETE` | The agent did not complete the requested task. | Required answer section missing, tool result not integrated, early stop. | Prompt lacks task completion criteria or checklist. | Add explicit completion checklist and required output expectations. | Usually affects `prompts/*.md`, `prompt.md`, `instructions.md`, or `agent.yaml`. |
| `TOOL_MISSING` | A required tool was not called. | Expected tool `document_reader`, but trace contains no `document_reader` call. | Prompt or workflow does not clearly require tool usage. | Add explicit tool-use instruction or update workflow configuration. | Usually affects `prompts/*.md`, `tool_descriptions.yaml`, `workflow_config.yaml`, or `agent.yaml`; often low risk for read-only tools. |
| `TOOL_ORDER_ERROR` | Tools were called in an invalid or suspicious order. | Agent summarized before reading the document. | Tool sequence is underspecified. | Clarify required tool-call order and prerequisites. | Usually affects prompt or workflow config; often low risk for read-only sequences. |
| `TOOL_ARGUMENT_ERROR` | Tool arguments are missing, malformed, unsafe, or unclear. | Tool call has `path: null`, wrong field name, or invalid value. | Tool schema/examples are unclear or input validation is missing. | Document exact required arguments and clarification rules. | Usually affects `tool_descriptions.yaml`, prompt guidance, or workflow config; usually requires approval. |
| `FORBIDDEN_TOOL_CALL` | A forbidden tool was called. | Trace includes `web_search`, `shell`, or another forbidden tool. | Permission boundary is too loose or exposed tools are inconsistent with policy. | Tighten forbidden-tool policy, permissions, and safety tests. | High/critical risk; never auto-applies; requires human review. |
| `OUTPUT_FORMAT_ERROR` | Final output does not match expected text/Markdown format. | Missing headings, wrong table layout, loose labels instead of required sections. | Prompt lacks an output template or eval expectation differs from prompt. | Add a clear output template with required sections. | Usually affects prompt or eval config; often low/medium risk. |
| `OUTPUT_SCHEMA_ERROR` | Final output does not match an expected structured schema. | Invalid JSON, missing required field, extra text around schema output. | Output contract is not explicit enough or scorer is stricter than prompt. | Add stricter JSON/YAML/schema instructions and prohibit extra text. | Usually affects prompts or `eval_config.yaml`; usually requires approval. |
| `ERROR_HANDLING_MISSING` | Missing-input, invalid-input, or tool-error behavior is absent. | `document_reader` returns `file_not_found`, but the agent writes notes anyway. | Prompt lacks fallback and stop rules for failures. | Add explicit error handling, clarification, and stop conditions. | Usually affects prompt, tool descriptions, or eval config. |
| `HALLUCINATION_RISK` | Agent may answer without grounding in provided source/tool results. | Claims not supported by `document_reader` output. | Prompt does not require source-grounded responses or citations/evidence. | Require citations, source-grounded evidence, and explicit uncertainty. | Usually affects system prompt and sometimes eval config; requires review. |
| `LOOP_RISK` | Agent may repeat actions or exceed step/tool-call budgets. | Repeated same tool call, too many trace events, no stop condition. | No max tool-call limit or repeated-call guard. | Add max calls, repeated-call prevention, and stop conditions. | Usually affects `agent.yaml`, `workflow_config.yaml`, or prompts; auto may stop. |
| `LOW_STABILITY` | Repeated runs are unstable. | Only 2 of 5 repeated runs pass, or outputs vary across required contracts. | Prompt, model settings, tool rules, or tests are underspecified. | Add deterministic process instructions or stricter output contract. | Usually affects prompts, agent config, or eval config; often requires review. |
| `REGRESSION` | Current behavior is worse than baseline. | Baseline passed, current failed; confidence dropped. | Recent prompt/config/tool/eval change or auto patch degraded behavior. | Compare changed files and consider rollback. | Prefer rollback or baseline review before stacking new patches. |
| `SAFETY_RISK` | Safety or permission boundary may be violated. | External write without approval, unsafe path, shell command, secret-like input. | Missing approval gates, forbidden action rules, or permission boundaries. | Add approval gates, safety rules, and safety tests. | Critical risk; never auto-applies; requires human review. |
| `SCORER_UNCERTAIN` | The scorer/eval result is too uncertain to patch agent behavior. | Low scorer confidence, ambiguous rubric, judge disagreement. | Eval/scorer is unclear or lacks evidence. | Review eval/scorer before patching agent behavior. | Review-only; no agent patch by default. |
| `UNKNOWN` | AgentDoctor lacks enough evidence to classify the failure. | Custom scorer failure with no known mapping, incomplete trace. | Instrumentation, scorer evidence, or taxonomy mapping is missing. | Improve traces, eval metadata, or failure evidence. | Review-only; no agent patch by default. |

## Example: Tool Missing

```yaml
failure_type: TOOL_MISSING
meaning: A required tool was not called.
typical_evidence: Expected tool document_reader, but trace contains no document_reader call.
likely_cause: Prompt or workflow does not clearly require tool usage.
suggested_fix: Add explicit tool-use instruction or update workflow configuration.
patch_implication: Usually affects prompts/*.md or workflow_config.yaml.
```

## Example: Tool Order Error

```yaml
failure_type: TOOL_ORDER_ERROR
meaning: Tools were called in an invalid or suspicious order.
typical_evidence: Agent summarized before reading the document.
likely_cause: Tool sequence is underspecified.
suggested_fix: Clarify required tool-call order.
patch_implication: Usually affects prompt or workflow config.
```

## Example: Output Schema Error

```yaml
failure_type: OUTPUT_SCHEMA_ERROR
meaning: Final output does not match expected schema.
typical_evidence: Required field missing or invalid JSON/Markdown structure.
likely_cause: Output contract is not explicit enough.
suggested_fix: Add stricter output schema instructions.
patch_implication: Usually affects prompts or eval_config.
```

## Example: Hallucination Risk

```yaml
failure_type: HALLUCINATION_RISK
meaning: Agent may be answering without grounding in provided source/tool results.
typical_evidence: Claims not supported by document_reader output.
likely_cause: Prompt does not require source-grounded responses.
suggested_fix: Require citations or tool-grounded evidence.
patch_implication: Usually affects system prompt.
```

## Severity and Review

Failure type and severity are separate. A missing Markdown heading can be an `OUTPUT_FORMAT_ERROR` warning. A broken production JSON API contract can be an `OUTPUT_SCHEMA_ERROR` error. `SAFETY_RISK` and `FORBIDDEN_TOOL_CALL` are critical by default and require human review.

## Reports

Markdown diagnostic reports include a `Failure Taxonomy Summary` section. JSON reports include `findings`, `taxonomy_summary`, `failure_type_counts`, `review_required_findings`, `auto_fix_eligible_findings`, `patch_target_candidates`, and `recommended_next_round_tags`.
