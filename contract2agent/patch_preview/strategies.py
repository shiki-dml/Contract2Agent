from __future__ import annotations

from dataclasses import dataclass

from contract2agent.patch_preview.models import FindingGroup


READ_ONLY_TOOLS = {
    "document_reader",
    "pdf_reader",
    "file_reader",
    "retriever",
    "search_reader",
    "web_search",
    "browser",
    "database_reader",
}

SIDE_EFFECT_TOOLS = {
    "email_sender",
    "calendar_creator",
    "file_writer",
    "database_writer",
    "shell",
    "shell_exec",
    "code_executor",
    "markdown_writer",
}


@dataclass(frozen=True)
class FixStrategy:
    strategy_id: str
    patch_type: str
    title: str
    guidance_lines: list[str]
    expected_effect: list[str]
    regression_risks: list[str]
    reviewer_notes: list[str]


def select_strategy(
    group: FindingGroup,
    *,
    previous_patch_metadata: dict | None = None,
) -> FixStrategy:
    types = set(group.failure_types)
    tool = group.tool_name or "the required tool"

    if "UNKNOWN" in types:
        return FixStrategy(
            strategy_id="review_unknown_failure",
            patch_type="no_agent_patch_review_only",
            title="Review unknown failure",
            guidance_lines=[],
            expected_effect=["Better instrumentation should make the next diagnosis actionable."],
            regression_risks=["Changing agent behavior without a known cause can overfit or mask the real issue."],
            reviewer_notes=[
                "No agent patch was generated because the failure type is UNKNOWN.",
                "Collect trace, scorer, or tool-call evidence before proposing a behavior change.",
            ],
        )

    if "SCORER_UNCERTAIN" in types:
        return FixStrategy(
            strategy_id="review_scorer_uncertain",
            patch_type="no_agent_patch_review_only",
            title="Review scorer uncertainty",
            guidance_lines=[],
            expected_effect=["Human review can decide whether the eval or scorer should change."],
            regression_risks=["Patching the agent to satisfy an uncertain scorer can encode the scorer's ambiguity."],
            reviewer_notes=[
                "No agent prompt patch was generated for SCORER_UNCERTAIN.",
                "Review the eval expectation, scoring rubric, or test fixture before changing agent behavior.",
            ],
        )

    if "REGRESSION" in types:
        if previous_patch_metadata:
            return FixStrategy(
                strategy_id="rollback_previous_patch",
                patch_type="rollback_patch",
                title="Rollback previous patch",
                guidance_lines=[],
                expected_effect=["Restores behavior changed by the latest patch if the regression is linked to it."],
                regression_risks=[
                    "Rollback may reintroduce the original failure that the previous patch addressed.",
                    "Rollback should be validated against both baseline and the target regression case.",
                ],
                reviewer_notes=["Previous patch metadata exists, so rollback is preferred over stacking a new fix."],
            )
        return FixStrategy(
            strategy_id="review_regression_without_rollback",
            patch_type="no_agent_patch_review_only",
            title="Review regression",
            guidance_lines=[],
            expected_effect=["Reviewer can identify the changed behavior and choose rollback or a targeted fix."],
            regression_risks=["A new patch without rollback metadata can stack fixes and hide the original regression."],
            reviewer_notes=["No rollback metadata was found, so no rollback diff was generated."],
        )

    if "SAFETY_RISK" in types:
        return FixStrategy(
            strategy_id="fix_safety_permission_boundary",
            patch_type="workflow_config_update",
            title="Add safety and approval boundaries",
            guidance_lines=[
                "Do not perform external writes, destructive actions, shell/code execution, or permission-sensitive actions unless the user explicitly requests the action and confirms it.",
                "If a requested action could affect external systems, credentials, private data, or irreversible state, stop and ask for human approval before using the tool.",
                "If approval is absent or ambiguous, explain the blocked action instead of calling the tool.",
            ],
            expected_effect=[
                "Safety-risk findings should become explicit approval or refusal paths.",
                "Unsafe tool calls should be blocked before execution.",
            ],
            regression_risks=[
                "The agent may refuse legitimate high-privilege tasks until approval rules are clarified.",
                "Workflow behavior can become more conservative across unrelated tasks.",
            ],
            reviewer_notes=["Critical safety proposals are preview-only and must be reviewed by a human."],
        )

    if "FORBIDDEN_TOOL_CALL" in types:
        return FixStrategy(
            strategy_id="fix_forbidden_tool_policy",
            patch_type="workflow_config_update",
            title="Add forbidden tool policy",
            guidance_lines=[
                "Do not call forbidden or side-effectful tools such as shell, file_writer, email_sender, calendar_creator, database_writer, or external write tools unless the user explicitly requests and confirms the action.",
                "If a test or request conflicts with the forbidden-tool policy, follow the safety policy and report that the action is blocked.",
            ],
            expected_effect=[
                "Forbidden tool calls should be replaced by explicit refusal or clarification behavior.",
            ],
            regression_risks=[
                "The agent may avoid a tool that is actually allowed in a narrower context if permissions are not modeled clearly.",
            ],
            reviewer_notes=["Forbidden-tool proposals are critical risk and never auto-applicable."],
        )

    if {"TOOL_MISSING", "HALLUCINATION_RISK"}.issubset(types):
        return FixStrategy(
            strategy_id="fix_missing_tool_use_source_grounding",
            patch_type="prompt_update",
            title="Add source inspection and grounding rules",
            guidance_lines=[
                f"Before answering questions that depend on a provided document or source, call {tool} with the exact path or identifier supplied by the user.",
                "Base factual claims only on tool-provided source content.",
                "If the source does not contain enough evidence, say so explicitly instead of inferring or guessing.",
            ],
            expected_effect=[
                "The agent should call the source-reading tool before answering source-dependent questions.",
                "Unsupported factual claims should decrease.",
            ],
            regression_risks=[
                "The agent may ask for sources more often in open-ended tasks.",
                "Grounding rules can reduce useful synthesis if source evidence is incomplete.",
            ],
            reviewer_notes=["This combines compatible TOOL_MISSING and HALLUCINATION_RISK findings."],
        )

    if "OUTPUT_SCHEMA_ERROR" in types:
        return FixStrategy(
            strategy_id="fix_output_schema_strict_json",
            patch_type="prompt_update",
            title="Add strict schema-only output rule",
            guidance_lines=[
                "Return only valid JSON matching the required schema.",
                "Do not include Markdown fences, prose explanations, comments, trailing commas, or extra fields.",
                "If required information is unavailable, use the schema's allowed empty/null value rather than adding unsupported fields.",
            ],
            expected_effect=[
                "OUTPUT_SCHEMA_ERROR count should decrease.",
                "JSON schema tests should pass more consistently.",
            ],
            regression_risks=[
                "The agent may become too schema-focused and reduce task completeness.",
                "Strict JSON output may omit useful explanation when a task expects prose.",
            ],
            reviewer_notes=["Validate task completion as well as schema compliance after applying."],
        )

    if "OUTPUT_FORMAT_ERROR" in types:
        return FixStrategy(
            strategy_id="fix_output_format_template",
            patch_type="prompt_update",
            title="Add output template",
            guidance_lines=[
                "Use the required output format exactly.",
                "When Markdown is requested, include the expected sections with stable headings and no extra top-level sections unless the task asks for them.",
                "If a table or list is required, keep column names and item order consistent with the eval expectation.",
            ],
            expected_effect=[
                "OUTPUT_FORMAT_ERROR findings should decrease.",
                "Required headings, tables, or list structure should be more stable.",
            ],
            regression_risks=[
                "A rigid template may be too verbose or too narrow for open-ended tasks.",
            ],
            reviewer_notes=["Low-risk prompt-format patches are still preview-only in v0.1."],
        )

    if "TOOL_MISSING" in types:
        if is_side_effect_tool(tool):
            return FixStrategy(
                strategy_id="review_missing_side_effect_tool",
                patch_type="no_agent_patch_review_only",
                title="Review side-effectful tool trigger",
                guidance_lines=[],
                expected_effect=[
                    "Reviewer can decide whether the side-effectful tool should be used and under what approval rule.",
                ],
                regression_risks=[
                    "Forcing side-effectful tool use can send messages, write files, mutate data, or perform external actions unexpectedly.",
                ],
                reviewer_notes=[
                    f"No direct tool-use patch was generated because {tool} appears side-effectful.",
                    "Add an approval-gated workflow rule before enabling this behavior.",
                ],
            )
        return FixStrategy(
            strategy_id="fix_missing_tool_use",
            patch_type="prompt_update",
            title="Add tool-use trigger",
            guidance_lines=[
                f"Before answering tasks that require information available through {tool}, call {tool} with the exact input supplied by the user.",
                f"If the required input for {tool} is missing, ask for clarification instead of answering from assumptions.",
            ],
            expected_effect=[
                "Required read-only tool calls should occur before final answers.",
            ],
            regression_risks=[
                "The agent may call the tool for borderline cases that could be answered without it.",
            ],
            reviewer_notes=["This is auto-apply eligible only when the selected tool is read-only."],
        )

    if "TOOL_ORDER_ERROR" in types:
        return FixStrategy(
            strategy_id="fix_tool_order_sequence",
            patch_type="workflow_config_update",
            title="Add required tool order",
            guidance_lines=[
                "Follow the required tool order for multi-step tasks.",
                "Call source/read tools before extraction or write tools.",
                "Produce the final answer only after required tool results are available.",
            ],
            expected_effect=["Tool sequence failures should decrease."],
            regression_risks=["A strict sequence may block valid alternate workflows."],
            reviewer_notes=["Review carefully if any tool in the sequence has side effects."],
        )

    if "TOOL_ARGUMENT_ERROR" in types:
        return FixStrategy(
            strategy_id="fix_tool_arguments_and_error_handling",
            patch_type="tool_description_update",
            title="Clarify tool arguments",
            guidance_lines=[
                f"When calling {tool}, use argument values exactly from the user's request or validated prior tool output.",
                "Do not invent file paths, identifiers, or permission-sensitive argument values.",
                "If a required argument is missing or invalid, ask for clarification instead of calling the tool.",
            ],
            expected_effect=["Tool argument validation failures should decrease."],
            regression_risks=[
                "The agent may ask for clarification more often when argument inference would have been acceptable.",
            ],
            reviewer_notes=["Argument changes involving paths or writes require human approval."],
        )

    if "ERROR_HANDLING_MISSING" in types:
        return FixStrategy(
            strategy_id="fix_error_handling_fallbacks",
            patch_type="prompt_update",
            title="Add fallback and clarification rules",
            guidance_lines=[
                "If a required file path, identifier, or input is missing or invalid, do not infer the missing content.",
                "Ask for a valid input or report the tool error clearly.",
                "If a required tool fails twice with the same error, stop and summarize the failure instead of retrying indefinitely.",
            ],
            expected_effect=["Missing-input and tool-error findings should decrease."],
            regression_risks=["The agent may stop earlier instead of attempting recovery in ambiguous cases."],
            reviewer_notes=["Review if the failed tool can perform writes or external actions."],
        )

    if "HALLUCINATION_RISK" in types:
        return FixStrategy(
            strategy_id="fix_source_grounding",
            patch_type="prompt_update",
            title="Add source grounding",
            guidance_lines=[
                "When a document, retrieved source, or tool result is provided, base all factual claims on that source content.",
                "Include evidence or citations when the task asks for factual conclusions.",
                "If the source lacks enough evidence, say so instead of inferring.",
            ],
            expected_effect=["Unsupported factual claims should decrease."],
            regression_risks=["The agent may be more conservative when source evidence is incomplete."],
            reviewer_notes=["Source-critical domains may require stricter human review."],
        )

    if "LOOP_RISK" in types:
        return FixStrategy(
            strategy_id="fix_loop_stop_conditions",
            patch_type="agent_config_update",
            title="Add loop stop conditions",
            guidance_lines=[
                "Do not call the same tool with the same arguments more than once unless new information is available.",
                "If a tool fails twice with the same error, stop and report the issue.",
                "Respect max step and max tool-call limits before producing the final answer.",
            ],
            expected_effect=["Repeated-call and max-step findings should decrease."],
            regression_risks=["The agent may stop earlier during legitimate multi-step troubleshooting."],
            reviewer_notes=["Validate runtime and task completion after changing loop behavior."],
        )

    if "LOW_STABILITY" in types:
        return FixStrategy(
            strategy_id="fix_deterministic_behavior",
            patch_type="prompt_update",
            title="Add deterministic behavior rules",
            guidance_lines=[
                "Use a stable decision process for tool selection and output formatting.",
                "When two valid output forms are possible, choose the one specified by the eval or task instructions.",
                "Keep field names, section names, and tool ordering consistent across repeated runs.",
            ],
            expected_effect=["Repeated runs should vary less on format and tool sequence."],
            regression_risks=["The agent may become less flexible on tasks with intentionally open-ended answers."],
            reviewer_notes=["Repeated validation is required before treating stability as improved."],
        )

    if "CONFIG_ERROR" in types:
        return FixStrategy(
            strategy_id="review_or_fix_simple_config",
            patch_type="agent_config_update",
            title="Review simple config issue",
            guidance_lines=[
                "Add only unambiguous missing config values, paths, or tool descriptions.",
                "If the intended value is unclear, stop and request human review instead of guessing.",
            ],
            expected_effect=["Obvious missing config references should be easier to repair."],
            regression_risks=["Incorrect config defaults can change runtime behavior broadly."],
            reviewer_notes=["Auto-apply is disabled for config changes by default."],
        )

    return FixStrategy(
        strategy_id="fix_task_completion_criteria",
        patch_type="prompt_update",
        title="Add task completion criteria",
        guidance_lines=[
            "Before finalizing, check that every explicit user requirement has been addressed.",
            "If a required step cannot be completed, state what is missing and what action is needed.",
            "Do not claim the task is complete until required tool calls, outputs, and error handling are complete.",
        ],
        expected_effect=["TASK_INCOMPLETE findings should decrease."],
        regression_risks=["The agent may spend extra tokens on completion checks."],
        reviewer_notes=["Keep the checklist concise to avoid overfitting open-ended tasks."],
    )


def is_side_effect_tool(tool_name: str | None) -> bool:
    if not tool_name:
        return False
    lowered = tool_name.casefold()
    if lowered in SIDE_EFFECT_TOOLS:
        return True
    return any(term in lowered for term in ("writer", "sender", "creator", "delete", "shell", "exec", "database"))


def is_read_only_tool(tool_name: str | None) -> bool:
    if not tool_name:
        return False
    lowered = tool_name.casefold()
    if is_side_effect_tool(lowered):
        return False
    return lowered in READ_ONLY_TOOLS or any(term in lowered for term in ("reader", "search", "retriev", "browser"))
