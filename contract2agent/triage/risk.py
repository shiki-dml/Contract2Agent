from __future__ import annotations

from contract2agent.triage.classifiers import HIGH_RISK_SIDE_EFFECTS
from contract2agent.triage.discovery import DiscoveryResult
from contract2agent.triage.models import (
    AgentClassification,
    DetectedCapabilities,
    MissingInformation,
    RiskAssessment,
    TriageWarning,
)
from contract2agent.triage.parsers import PromptSignals, RawProjectData


def assess_risk(
    *,
    discovery: DiscoveryResult,
    data: RawProjectData,
    capabilities: DetectedCapabilities,
    prompt_signals: PromptSignals,
    eval_case_count: int,
    baseline_exists: bool,
) -> RiskAssessment:
    tools = capabilities.tools
    score = 0
    reasons: list[str] = []
    high_risk_tools: list[str] = []
    missing_safety_controls: list[str] = []

    if not tools:
        reasons.append("No tools detected.")
    elif all(tool.category in {"formatting", "validation"} and tool.side_effect_level == "none" for tool in tools):
        score = max(score, 1)
        reasons.append("Only formatting or validation tools detected.")
    elif any(tool.side_effect_level in {"read_only", "external_read"} for tool in tools):
        score = max(score, 2)
        reasons.append("Read-only or external-read tools detected.")

    if len(tools) > 1:
        score += 1
        reasons.append("Agent uses multiple tools.")

    for tool in tools:
        if tool.category == "filesystem_read":
            score += 2
            reasons.append(f"Agent can read local files through {tool.name}.")
        if tool.side_effect_level == "external_read":
            score += 2
            reasons.append(f"Agent can read external resources through {tool.name}.")
        if tool.side_effect_level == "write_local":
            score += 4
            reasons.append(f"Agent can write local files through {tool.name}.")
        if tool.side_effect_level == "external_write":
            score += 5
            reasons.append(f"Agent can perform external writes through {tool.name}.")
        if tool.category in {"shell_execution", "code_execution"}:
            score += 5
            reasons.append(f"Agent has shell/code execution capability through {tool.name}.")
        if tool.side_effect_level == "destructive":
            score += 6
            reasons.append(f"Agent has potentially destructive capability through {tool.name}.")
        if tool.side_effect_level == "unknown":
            score += 2
            reasons.append(f"Tool side effect is unknown for {tool.name}.")
        if tool.risk_level == "high" or tool.side_effect_level in HIGH_RISK_SIDE_EFFECTS:
            high_risk_tools.append(tool.name)

    if not prompt_signals.has_output_format:
        score += 1
        missing_safety_controls.append("no output schema or output format")
    if not prompt_signals.has_error_handling:
        score += 1
        missing_safety_controls.append("no error handling instruction")
    if tools and not prompt_signals.has_max_tool_calls:
        score += 1
        missing_safety_controls.append("no max tool-call or max-step limit")
    if high_risk_tools and not prompt_signals.has_safety:
        score += 1
        missing_safety_controls.append("no forbidden action policy")
    if _has_side_effectful_tool(capabilities) and not prompt_signals.has_human_approval:
        score += 2
        missing_safety_controls.append("no confirmation before side-effectful actions")
    if eval_case_count == 0:
        score += 1
        reasons.append("No eval cases found.")
    if not baseline_exists:
        score += 1
        reasons.append("No baseline found.")

    if high_risk_tools:
        risk_level = "high"
    elif discovery.agent_config.status != "found" and not data.agent_config_text:
        risk_level = "unknown"
    elif score <= 2:
        risk_level = "low"
    elif score <= 6:
        risk_level = "medium"
    else:
        risk_level = "high"

    review_policy = "each-round" if risk_level == "high" else "on-fail"
    return RiskAssessment(
        risk_level=risk_level,
        risk_score=score,
        reasons=_dedupe(reasons),
        high_risk_tools=sorted(set(high_risk_tools)),
        missing_safety_controls=_dedupe(missing_safety_controls),
        recommended_review_policy=review_policy,
    )


def detect_missing_information(
    *,
    discovery: DiscoveryResult,
    data: RawProjectData,
    capabilities: DetectedCapabilities,
    classification: AgentClassification,
    prompt_signals: PromptSignals,
    eval_case_count: int,
    baseline_exists: bool,
    patch_targets_available: bool,
    allow_auto: bool,
) -> list[MissingInformation]:
    missing: list[MissingInformation] = []
    tool_count = len(capabilities.tools)

    if discovery.agent_config.status != "found":
        missing.append(
            MissingInformation(
                id="missing_agent_config",
                severity="error",
                title="No agent config found",
                description="Triage could not find an agent config under the selected project root.",
                why_it_matters="Agent identity, tool wiring, provider, model, and safety controls may be incomplete.",
                suggested_action="Provide an agent.yaml or pass --agent.",
                related_failure_type="CONFIG_ERROR",
            )
        )
    if not data.prompt_texts:
        missing.append(
            MissingInformation(
                id="missing_prompt",
                severity="error",
                title="No prompt found",
                description="Triage could not find prompt.md, system_prompt.md, instructions.md, or prompt files under prompts/.",
                why_it_matters="Prompt instructions define expected behavior, output format, safety boundaries, and error handling.",
                suggested_action="Add a prompt file such as prompts/system.md or configure the prompt path.",
                related_failure_type="CONFIG_ERROR",
            )
        )
    if tool_count and not data.tool_configs and _tool_descriptions_incomplete(capabilities):
        missing.append(
            MissingInformation(
                id="missing_tool_descriptions",
                severity="warning",
                title="Tools referenced but no tool descriptions found",
                description="Tools were detected, but triage found no dedicated tool description/config file with side-effect documentation.",
                why_it_matters="Undocumented tool purpose, parameters, and side effects make tool selection and safety harder to test.",
                suggested_action="Add tool_descriptions.yaml or document each tool's purpose, parameters, and side effects.",
                related_failure_type="TOOL_MISSING",
            )
        )
    if not prompt_signals.has_output_format:
        missing.append(
            MissingInformation(
                id="missing_output_schema_or_format",
                severity="warning",
                title="No explicit output schema or output format found",
                description="Triage did not find JSON, schema, Markdown, table, YAML, or exact-format instructions.",
                why_it_matters="Output checks become ambiguous without a declared format.",
                suggested_action="Add an explicit output format such as Markdown sections, JSON schema, YAML schema, or structured table requirements.",
                related_failure_type="OUTPUT_SCHEMA_ERROR",
            )
        )
    if not prompt_signals.has_error_handling:
        missing.append(
            MissingInformation(
                id="missing_error_handling",
                severity="warning",
                title="No explicit error handling instruction found",
                description="Triage did not find instructions for missing, invalid, or failed tool results.",
                why_it_matters="Agents often continue unsafe work after failed reads or invalid inputs unless told how to stop or recover.",
                suggested_action="Add instructions for missing files, empty inputs, invalid paths, invalid tool results, and tool failures.",
                related_failure_type="ERROR_HANDLING_MISSING",
            )
        )
    if tool_count > 1 and not prompt_signals.has_tool_call_order:
        missing.append(
            MissingInformation(
                id="missing_tool_call_order",
                severity="warning",
                title="No explicit tool-call order found",
                description="Multiple tools were detected, but triage did not find sequencing rules.",
                why_it_matters="Tool-using agents can call write/action tools before read/validation tools without clear order constraints.",
                suggested_action="Add explicit sequencing rules, such as reading/retrieving before summarizing or validating before writing.",
                related_failure_type="TOOL_ORDER_ERROR",
            )
        )
    if classification.agent_type == "research_agent" and not prompt_signals.has_source_grounding:
        missing.append(
            MissingInformation(
                id="missing_source_grounding",
                severity="warning",
                title="No source grounding rule found",
                description="This appears to be a research/source-dependent agent, but no citation, source, evidence, or hallucination rule was found.",
                why_it_matters="Research agents can answer from prior knowledge instead of retrieved or provided source content.",
                suggested_action="Require the agent to cite retrieved/tool-provided content and avoid answering from prior knowledge when source files are provided.",
                related_failure_type="HALLUCINATION_RISK",
            )
        )
    if tool_count and not prompt_signals.has_max_tool_calls:
        missing.append(
            MissingInformation(
                id="missing_max_tool_calls",
                severity="warning",
                title="No max tool-call or max-step limit found",
                description="Triage did not find a max tool-call, max-step, or loop limit.",
                why_it_matters="Agents without step limits can loop or repeatedly call tools.",
                suggested_action="Add max tool-call or max-step constraints.",
                related_failure_type="LOOP_RISK",
            )
        )
    if any(tool.risk_level == "high" for tool in capabilities.tools) and not prompt_signals.has_safety:
        missing.append(
            MissingInformation(
                id="missing_forbidden_action_policy",
                severity="warning",
                title="No forbidden action policy found",
                description="High-risk tools were detected, but triage did not find forbidden action/path/argument rules.",
                why_it_matters="High-risk tools need explicit boundaries for dangerous operations.",
                suggested_action="Define forbidden tools, forbidden arguments, forbidden paths, and unsafe operations.",
                related_failure_type="SAFETY_RISK",
            )
        )
    if _has_side_effectful_tool(capabilities) and not prompt_signals.has_human_approval:
        missing.append(
            MissingInformation(
                id="missing_human_approval_rule",
                severity="warning",
                title="No human approval rule found",
                description="Side-effectful tools were detected, but no confirmation or approval rule was found.",
                why_it_matters="Writes, external actions, shell/code execution, and database updates should be reviewed before execution.",
                suggested_action="Require user confirmation before side-effectful actions.",
                related_failure_type="SAFETY_RISK",
            )
        )
    if eval_case_count == 0:
        missing.append(
            MissingInformation(
                id="missing_eval_cases",
                severity="warning",
                title="No eval cases found",
                description="Triage could not find eval files under evals/, tests/evals/, agentdoctor_tests/, or .agentdoctor/evals/.",
                why_it_matters="Without eval cases, quick/deep/auto cannot select existing project-specific behavior checks.",
                suggested_action="Add eval cases for key behaviors or run with default diagnostic templates if available.",
                related_failure_type="UNKNOWN",
            )
        )
    if not baseline_exists:
        missing.append(
            MissingInformation(
                id="missing_baseline",
                severity="info",
                title="No baseline found",
                description="Triage could not find .agentdoctor/baselines/latest.json or another baseline JSON file.",
                why_it_matters="Baselines help detect regressions after future prompt/config changes.",
                suggested_action="Run `agentdoctor deep --rounds 3 --save-baseline` after the first reliable diagnostic run.",
                related_failure_type="REGRESSION",
            )
        )
    if allow_auto and not patch_targets_available:
        missing.append(
            MissingInformation(
                id="missing_safe_patch_boundary",
                severity="warning",
                title="No safe patch boundary found",
                description="Auto mode was allowed for consideration, but no allowlisted prompt/config patch target was found.",
                why_it_matters="Auto repair needs a narrow prompt/config target to preview patches safely.",
                suggested_action="Configure patch allowlist before using auto mode.",
                related_failure_type="SAFETY_RISK",
            )
        )
    return _dedupe_missing(missing)


def generate_warnings(
    *,
    discovery: DiscoveryResult,
    capabilities: DetectedCapabilities,
    classification: AgentClassification,
    prompt_signals: PromptSignals,
    eval_covered_areas: list[str],
    allow_auto: bool,
    auto_eligible: bool,
    auto_blockers: list[str],
) -> list[TriageWarning]:
    warnings: list[TriageWarning] = [*discovery.warnings]
    for tool in capabilities.tools:
        if tool.risk_level == "high":
            warnings.append(
                TriageWarning(
                    id=f"high_risk_tool_{_slug(tool.name)}",
                    severity="warning",
                    title=f"High-risk tool detected: {tool.name}",
                    description=f"{tool.name} is classified as {tool.category} with {tool.side_effect_level} side effects.",
                    evidence=tool.evidence,
                    recommended_action="Run deep diagnosis with each-round review.",
                )
            )
        if tool.side_effect_level == "external_write":
            warnings.append(
                TriageWarning(
                    id=f"external_write_tool_{_slug(tool.name)}",
                    severity="warning",
                    title=f"External write tool detected: {tool.name}",
                    description=f"{tool.name} can write to an external system.",
                    evidence=tool.evidence,
                    recommended_action="Require human approval before external actions.",
                )
            )
        if tool.side_effect_level == "unknown":
            warnings.append(
                TriageWarning(
                    id=f"unknown_side_effect_{_slug(tool.name)}",
                    severity="warning",
                    title=f"Tool side effect unknown: {tool.name}",
                    description="Triage could not determine whether this tool is read-only, local-write, external-write, or destructive.",
                    evidence=tool.evidence,
                    recommended_action="Document whether the tool is read-only, local-write, external-write, or destructive.",
                )
            )
    if prompt_signals.prompt_char_count == 0 or prompt_signals.prompt_char_count < 80 or not (
        prompt_signals.has_output_format and prompt_signals.has_safety
    ):
        warnings.append(
            TriageWarning(
                id="prompt_underspecified",
                severity="warning",
                title="Prompt appears underspecified",
                description="The prompt is missing, very short, or lacks explicit task/format/safety constraints.",
                evidence=[f"prompt_char_count={prompt_signals.prompt_char_count}"],
                recommended_action="Add explicit task, output format, error handling, and safety instructions.",
            )
        )
    if capabilities.tools and not prompt_signals.has_tool_usage:
        warnings.append(
            TriageWarning(
                id="tools_without_usage_rule",
                severity="warning",
                title="Tools configured but no usage rule found",
                description="Tools exist, but triage did not find prompt instructions for when or how to use them.",
                evidence=[tool.name for tool in capabilities.tools],
                recommended_action="Add tool usage rules and examples to the prompt or agent config.",
            )
        )
    if prompt_signals.has_output_format and not ({"output_format", "output_schema"} & set(eval_covered_areas)):
        warnings.append(
            TriageWarning(
                id="format_without_eval",
                severity="warning",
                title="Output format has no matching eval coverage",
                description="The prompt/config appears to define output format, but eval coverage lacks output_format/output_schema.",
                evidence=list(eval_covered_areas),
                recommended_action="Add an output format or schema eval case.",
            )
        )
    if not allow_auto:
        warnings.append(
            TriageWarning(
                id="auto_not_considered",
                severity="info",
                title="Auto mode not recommended by default",
                description="Triage does not recommend auto mode unless --allow-auto is passed.",
                evidence=[],
                recommended_action="Pass --allow-auto only when safe patch boundaries and review policies are configured.",
            )
        )
    elif not auto_eligible:
        warnings.append(
            TriageWarning(
                id="auto_not_safe",
                severity="warning",
                title="Auto mode not recommended",
                description="Auto mode was considered but blockers were found.",
                evidence=auto_blockers,
                recommended_action="Run deep diagnosis and resolve blockers before using auto mode.",
            )
        )
    return _dedupe_warnings(warnings)


def _has_side_effectful_tool(capabilities: DetectedCapabilities) -> bool:
    return any(
        tool.side_effect_level in {"write_local", "external_write", "destructive"}
        or tool.category in {"shell_execution", "code_execution"}
        for tool in capabilities.tools
    )


def _tool_descriptions_incomplete(capabilities: DetectedCapabilities) -> bool:
    return any(tool.description == "unknown" or not tool.evidence for tool in capabilities.tools)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _dedupe_missing(items: list[MissingInformation]) -> list[MissingInformation]:
    seen = set()
    result = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        result.append(item)
    return result


def _dedupe_warnings(items: list[TriageWarning]) -> list[TriageWarning]:
    seen = set()
    result = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        result.append(item)
    return result


def _slug(value: str) -> str:
    cleaned = []
    for char in value.casefold():
        if char.isalnum():
            cleaned.append(char)
        elif cleaned and cleaned[-1] != "_":
            cleaned.append("_")
    return "".join(cleaned).strip("_") or "item"
