from __future__ import annotations

import json
from pathlib import Path

from contract2agent.privacy_eval.schema import (
    PrivacyEvalProfile,
    PrivacyFinding,
    PrivacyScorecard,
    PrivacyTrainingConfig,
    profile_from_dict,
)


CHANNEL_WEIGHTS = {
    "output": 1.0,
    "inter_agent": 1.55,
    "shared_memory": 1.45,
    "tool_call": 1.35,
    "log": 1.25,
    "artifact": 1.15,
    "training_update": 1.35,
    "vector_store": 1.25,
}

PROTECTIVE_CONTROLS = {
    "access_control",
    "allowlist",
    "approval",
    "audit_log",
    "consent",
    "data_minimization",
    "dp_accounting",
    "dp_noise",
    "encryption",
    "firewall",
    "human_review",
    "private_aggregation",
    "redaction",
    "retention_policy",
    "sandbox",
    "tokenization",
}


def load_privacy_profile(path: str | Path) -> PrivacyEvalProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Privacy profile must contain a JSON object: {path}")
    return profile_from_dict(data)


def analyze_privacy_profile(profile: PrivacyEvalProfile) -> PrivacyScorecard:
    findings: list[PrivacyFinding] = []
    flow_risks: list[float] = []

    for flow in profile.data_flows:
        risk = _flow_risk(flow.controls, flow.channel, flow.contains_sensitive_data, flow.external_destination, flow.untrusted_input)
        flow_risks.append(risk)
        if flow.contains_sensitive_data and not _has_any(flow.controls, PROTECTIVE_CONTROLS):
            findings.append(
                PrivacyFinding(
                    finding_id=f"{flow.flow_id}:unprotected_sensitive_flow",
                    severity="high",
                    category="leakage_channel",
                    summary=f"Sensitive data crosses `{flow.channel}` without a declared protection.",
                    evidence=[flow.flow_id, flow.source, flow.destination],
                    recommendation="Add redaction, allowlisting, access control, encryption, or channel-specific minimization.",
                    source_reference="agentleak",
                )
            )
        if flow.channel in {"inter_agent", "shared_memory"} and flow.contains_sensitive_data:
            findings.append(
                PrivacyFinding(
                    finding_id=f"{flow.flow_id}:internal_channel_sensitive_data",
                    severity="medium" if _has_any(flow.controls, PROTECTIVE_CONTROLS) else "high",
                    category="internal_channel_privacy",
                    summary=f"Sensitive data is present in internal channel `{flow.channel}`.",
                    evidence=[flow.flow_id, "output-only privacy checks would miss this path"],
                    recommendation="Trace and grade internal channels, not only final user-facing output.",
                    source_reference="agentleak",
                )
            )
        if flow.untrusted_input and not _has_control(flow.controls, "firewall"):
            findings.append(
                PrivacyFinding(
                    finding_id=f"{flow.flow_id}:untrusted_input_without_firewall",
                    severity="medium",
                    category="prompt_injection_privacy",
                    summary="Untrusted input reaches an agent/tool path without a declared firewall.",
                    evidence=[flow.flow_id, flow.channel],
                    recommendation="Add a tool-input minimizer and tool-output sanitizer before private context is exposed.",
                    source_reference="agentdojo",
                )
            )

    for tool in profile.tools:
        if tool.receives_sensitive_data and tool.sends_external and not tool.requires_approval:
            findings.append(
                PrivacyFinding(
                    finding_id=f"tool:{tool.name}:external_sensitive_no_approval",
                    severity="high",
                    category="tool_privacy",
                    summary=f"Tool `{tool.name}` can send sensitive data externally without approval.",
                    evidence=[tool.name, tool.category],
                    recommendation="Require explicit approval or remove sensitive fields before the tool call.",
                    source_reference="agentdojo",
                )
            )
        if tool.untrusted_input_source and tool.receives_sensitive_data and not _has_control(tool.controls, "firewall"):
            findings.append(
                PrivacyFinding(
                    finding_id=f"tool:{tool.name}:untrusted_tool_private_context",
                    severity="medium",
                    category="prompt_injection_privacy",
                    summary=f"Tool `{tool.name}` mixes untrusted input with private context.",
                    evidence=[tool.name],
                    recommendation="Sanitize tool outputs and minimize private context passed to tool-mediated reasoning.",
                    source_reference="agentdojo",
                )
            )

    findings.extend(_training_findings(profile.training))

    leakage_risk = round(sum(flow_risks) / max(1, len(flow_risks)), 3)
    channel_coverage = _channel_coverage(profile)
    dp_readiness = _dp_readiness(profile.training)
    prompt_resilience = _prompt_resilience(profile, findings)
    auditability = _control_score(profile, {"audit_log", "access_control", "retention_policy"})
    minimization = _control_score(profile, {"data_minimization", "redaction", "tokenization", "allowlist"})
    approval_safety = _approval_score(profile)

    positive = (
        channel_coverage * 0.18
        + dp_readiness * 0.17
        + prompt_resilience * 0.18
        + auditability * 0.15
        + minimization * 0.17
        + approval_safety * 0.15
    )
    penalty = min(0.45, leakage_risk / 100 * 0.45)
    overall = max(0.0, min(1.0, positive - penalty))

    return PrivacyScorecard(
        profile_id=profile.profile_id,
        overall_privacy_readiness=round(overall, 3),
        leakage_risk_score=leakage_risk,
        channel_coverage=round(channel_coverage, 3),
        dp_readiness=round(dp_readiness, 3),
        prompt_injection_resilience=round(prompt_resilience, 3),
        auditability=round(auditability, 3),
        minimization=round(minimization, 3),
        approval_safety=round(approval_safety, 3),
        findings=sorted(findings, key=lambda item: (_severity_rank(item.severity), item.finding_id)),
        recommended_next_tests=_recommended_tests(profile, findings),
        limitations=[
            "Static privacy-eval does not prove runtime privacy behavior.",
            "No external benchmark, training run, or DP accountant is executed.",
            "Reference projects and papers shape checks but do not create target-agent scores.",
        ],
        source_references=privacy_source_references(),
    )


def privacy_source_references() -> list[dict[str, object]]:
    return [
        {
            "source_id": "agentleak",
            "source_type": "open_source_agent_privacy_benchmark",
            "title": "AgentLeak",
            "url": "https://github.com/Privatris/AgentLeak",
            "license": "MIT",
            "notes": [
                "Useful for full-stack privacy leakage channels in multi-agent systems.",
                "Contract2Agent uses the channel concept as contextual methodology.",
            ],
            "limitations": [
                "No AgentLeak run is executed by privacy-eval.",
                "No imported AgentLeak score is assigned.",
            ],
        },
        {
            "source_id": "agentdojo",
            "source_type": "open_source_agent_security_benchmark",
            "title": "AgentDojo",
            "url": "https://github.com/ethz-spylab/agentdojo",
            "license": "MIT",
            "notes": [
                "Useful for untrusted tool data, prompt injection attacks, and defense concepts."
            ],
            "limitations": ["No AgentDojo benchmark run is executed by privacy-eval."],
        },
        {
            "source_id": "opacus",
            "source_type": "open_source_dp_training_library",
            "title": "Opacus",
            "url": "https://github.com/pytorch/opacus",
            "license": "Apache-2.0",
            "notes": [
                "Useful reference for DP-SGD controls such as clipping, noise, and privacy budget tracking."
            ],
            "limitations": ["No PyTorch or Opacus training run is executed."],
        },
        {
            "source_id": "opendp",
            "source_type": "open_source_dp_algorithm_library",
            "title": "OpenDP",
            "url": "https://github.com/opendp/opendp",
            "license": "MIT",
            "notes": ["Useful reference for modular DP transformations and measurements."],
            "limitations": ["No OpenDP proof or measurement chain is executed."],
        },
        {
            "source_id": "blt_dp_ftrl",
            "source_type": "paper_reference",
            "title": "A Hassle-free Algorithm for Private Learning in Practice: Don't Use Tree Aggregation, Use BLTs",
            "url": "https://research.google/pubs/a-hassle-free-algorithm-for-private-learning-in-practice-dont-use-tree-aggregation-use-blts/",
            "license": "CC BY 4.0",
            "notes": [
                "Useful for DP-FTRL mechanism selection in multi-participation federated learning."
            ],
            "limitations": ["Paper claims are contextual and not local observed results."],
        },
    ]


def _flow_risk(
    controls: list[str],
    channel: str,
    contains_sensitive: bool,
    external_destination: bool,
    untrusted_input: bool,
) -> float:
    risk = 16.0 * CHANNEL_WEIGHTS.get(channel, 1.1)
    if contains_sensitive:
        risk += 24.0
    if external_destination:
        risk += 18.0
    if untrusted_input:
        risk += 12.0
    risk -= min(30.0, 7.0 * len(_normalized_controls(controls) & PROTECTIVE_CONTROLS))
    return max(0.0, min(100.0, risk))


def _training_findings(training: PrivacyTrainingConfig) -> list[PrivacyFinding]:
    findings: list[PrivacyFinding] = []
    mechanism = training.privacy_mechanism.casefold()
    if training.sensitive_training_data and not training.uses_private_training:
        findings.append(
            PrivacyFinding(
                finding_id="training:sensitive_without_private_training",
                severity="high",
                category="dp_training",
                summary="Sensitive training data is declared but private training is not enabled.",
                recommendation="Add a documented DP or private aggregation configuration before claiming privacy protection.",
                source_reference="opacus",
            )
        )
        return findings
    if not training.uses_private_training:
        return findings

    required = {
        "privacy_unit": training.privacy_unit,
        "epsilon": training.epsilon,
        "delta": training.delta,
        "clipping_norm": training.clipping_norm,
        "accountant": training.accountant,
    }
    for field_name, value in required.items():
        if value in {None, ""}:
            findings.append(
                PrivacyFinding(
                    finding_id=f"training:missing_{field_name}",
                    severity="medium",
                    category="dp_training",
                    summary=f"Private training is enabled but `{field_name}` is missing.",
                    recommendation="Record the missing DP parameter in the profile and report.",
                    source_reference="opacus",
                )
            )
    if "tree" in mechanism and training.federated and training.multi_participation:
        findings.append(
            PrivacyFinding(
                finding_id="training:tree_aggregation_multi_participation",
                severity="medium",
                category="dp_training",
                summary="Multi-participation federated DP-FTRL uses tree aggregation.",
                recommendation="Review BLT-DP-FTRL as a practical alternative before finalizing the mechanism.",
                source_reference="blt_dp_ftrl",
            )
        )
    if "blt" in mechanism and training.federated and training.multi_participation:
        findings.append(
            PrivacyFinding(
                finding_id="training:blt_context_recorded",
                severity="info",
                category="dp_training",
                summary="Profile records a BLT-style DP-FTRL mechanism for multi-participation FL.",
                recommendation="Link an actual accountant output or training artifact before treating this as observed privacy evidence.",
                source_reference="blt_dp_ftrl",
            )
        )
    return findings


def _dp_readiness(training: PrivacyTrainingConfig) -> float:
    if not training.uses_private_training:
        return 0.2 if training.sensitive_training_data else 0.55
    fields = [
        training.privacy_unit,
        training.epsilon is not None,
        training.delta is not None,
        training.clipping_norm is not None,
        training.noise_multiplier is not None or "blt" in training.privacy_mechanism.casefold(),
        training.accountant,
    ]
    score = sum(1 for item in fields if item) / len(fields)
    if "blt" in training.privacy_mechanism.casefold() and training.federated:
        score += 0.1
    return min(1.0, score)


def _channel_coverage(profile: PrivacyEvalProfile) -> float:
    if not profile.data_flows:
        return 0.0
    channels = {flow.channel for flow in profile.data_flows}
    important = {"output", "tool_call", "inter_agent", "shared_memory", "log", "artifact", "training_update"}
    return min(1.0, len(channels & important) / 5)


def _prompt_resilience(profile: PrivacyEvalProfile, findings: list[PrivacyFinding]) -> float:
    if not any(flow.untrusted_input for flow in profile.data_flows) and not any(tool.untrusted_input_source for tool in profile.tools):
        return 0.65
    bad = sum(1 for finding in findings if finding.category == "prompt_injection_privacy")
    return max(0.0, 0.9 - bad * 0.25)


def _control_score(profile: PrivacyEvalProfile, controls: set[str]) -> float:
    declared = _normalized_controls(profile.declared_controls)
    flow_controls = set().union(*[_normalized_controls(flow.controls) for flow in profile.data_flows]) if profile.data_flows else set()
    tool_controls = set().union(*[_normalized_controls(tool.controls) for tool in profile.tools]) if profile.tools else set()
    found = declared | flow_controls | tool_controls
    return min(1.0, len(found & controls) / max(1, min(3, len(controls))))


def _approval_score(profile: PrivacyEvalProfile) -> float:
    external_sensitive = [
        tool for tool in profile.tools if tool.receives_sensitive_data and tool.sends_external
    ]
    if not external_sensitive:
        return 0.75
    approved = sum(1 for tool in external_sensitive if tool.requires_approval or _has_control(tool.controls, "approval"))
    return approved / len(external_sensitive)


def _recommended_tests(profile: PrivacyEvalProfile, findings: list[PrivacyFinding]) -> list[str]:
    tests = {
        "run_output_channel_pii_leakage_check",
        "run_log_and_artifact_secret_scan",
    }
    if any(flow.channel == "inter_agent" for flow in profile.data_flows):
        tests.add("trace_inter_agent_messages_for_sensitive_fields")
    if any(flow.channel == "shared_memory" for flow in profile.data_flows):
        tests.add("trace_shared_memory_privacy_boundaries")
    if any(finding.category == "prompt_injection_privacy" for finding in findings):
        tests.add("run_untrusted_tool_output_prompt_injection_privacy_case")
    if profile.training.uses_private_training:
        tests.add("attach_dp_accountant_output_and_training_artifacts")
    if profile.training.federated:
        tests.add("validate_federated_participation_bound_and_privacy_unit")
    return sorted(tests)


def _normalized_controls(controls: list[str]) -> set[str]:
    return {str(control).strip().casefold().replace("-", "_") for control in controls if str(control).strip()}


def _has_control(controls: list[str], name: str) -> bool:
    return name.casefold().replace("-", "_") in _normalized_controls(controls)


def _has_any(controls: list[str], names: set[str]) -> bool:
    return bool(_normalized_controls(controls) & names)


def _severity_rank(severity: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(severity, 5)
