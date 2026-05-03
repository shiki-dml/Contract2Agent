from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from contract2agent.triage.discovery import DiscoveryResult, is_excluded_path
from contract2agent.triage.models import (
    AgentClassification,
    AgentSummary,
    AutoReadiness,
    BaselineStatus,
    DetectedCapabilities,
    PatchPreviewReadiness,
    Recommendation,
    RiskAssessment,
    TriageWarning,
)
from contract2agent.triage.parsers import PromptSignals, RawProjectData


ALLOWED_PATCH_TARGET_PATTERNS = [
    "prompts/*.md",
    "agent.yaml",
    "agent.yml",
    "tool_descriptions.yaml",
    "tool_descriptions.yml",
    "workflow_config.yaml",
    "workflow_config.yml",
    "eval_config.yaml",
    "eval_config.yml",
]


def evaluate_baseline_status(
    *,
    discovery: DiscoveryResult,
    data: RawProjectData,
    agent_summary: AgentSummary | None,
    now: datetime,
) -> tuple[BaselineStatus, list[TriageWarning]]:
    warnings: list[TriageWarning] = []
    if discovery.baseline_path is None or not data.baseline_data:
        return BaselineStatus(exists=False, warning="No baseline found."), warnings

    baseline = data.baseline_data
    created_at = _first_string(
        baseline.get("created_at"),
        baseline.get("timestamp"),
        baseline.get("finished_at"),
    )
    mode = _first_string(baseline.get("mode"), baseline.get("diagnostic_mode"))
    confidence = _to_float(baseline.get("confidence") or baseline.get("overall_confidence"))
    agent_name = _first_string(
        baseline.get("agent_name"),
        baseline.get("agent"),
        _mapping(baseline.get("agent_summary")).get("name"),
    )
    warning_text = None

    if agent_summary and agent_name and agent_summary.name not in {None, "unknown"} and agent_name != agent_summary.name:
        warning_text = "Baseline appears to belong to a different agent."
        warnings.append(
            TriageWarning(
                id="baseline_agent_mismatch",
                severity="warning",
                title="Baseline may belong to a different agent",
                description=warning_text,
                evidence=[f"baseline_agent={agent_name}", f"current_agent={agent_summary.name}"],
                recommended_action="Create a fresh baseline for this agent after a reliable deep run.",
            )
        )

    parsed = _parse_datetime(created_at)
    if parsed is not None and (now - parsed.replace(tzinfo=now.tzinfo)).days > 30:
        warning_text = "Baseline may be stale."
        warnings.append(
            TriageWarning(
                id="baseline_stale",
                severity="warning",
                title="Baseline may be stale",
                description="Baseline may be stale.",
                evidence=[created_at or ""],
                recommended_action="Refresh the baseline after a reliable deep run.",
            )
        )

    return (
        BaselineStatus(
            exists=True,
            path=_relative(discovery.project_root, discovery.baseline_path),
            created_at=created_at,
            mode=mode,
            confidence=confidence,
            agent_name=agent_name,
            warning=warning_text,
        ),
        warnings,
    )


def evaluate_patch_preview_readiness(project_root: Path) -> PatchPreviewReadiness:
    detected: list[str] = []
    for pattern in ALLOWED_PATCH_TARGET_PATTERNS:
        for path in project_root.glob(pattern):
            if path.is_file() and not is_excluded_path(path, project_root):
                detected.append(_relative(project_root, path))
    detected = sorted(set(detected), key=str.casefold)
    missing = [pattern for pattern in ALLOWED_PATCH_TARGET_PATTERNS if not _pattern_has_match(pattern, detected)]
    notes = [] if detected else ["No safe patch target found."]
    return PatchPreviewReadiness(
        eligible=bool(detected),
        allowed_files_detected=detected,
        missing_patch_targets=missing,
        risk_notes=notes,
    )


def evaluate_auto_readiness(
    *,
    discovery: DiscoveryResult,
    data: RawProjectData,
    capabilities: DetectedCapabilities,
    classification: AgentClassification,
    risk: RiskAssessment,
    prompt_signals: PromptSignals,
    eval_case_count: int,
    patch_readiness: PatchPreviewReadiness,
) -> AutoReadiness:
    blockers: list[str] = []
    reasons: list[str] = []
    required_controls = [
        "review policy can stop on failures",
        "patch previews are limited to prompt/config targets",
        "human approval is required for side-effectful actions",
    ]

    if discovery.agent_config.status != "found":
        blockers.append("agent config not found")
    else:
        reasons.append("agent config found")
    if not data.prompt_texts and not data.agent_config_text:
        blockers.append("no prompt/config file found to patch")
    else:
        reasons.append("prompt/config file found")
    if not patch_readiness.eligible:
        blockers.append("no patch allowlist configured")
    else:
        reasons.append("safe prompt/config patch target detected")
    if eval_case_count == 0:
        blockers.append("no eval cases found")
    else:
        reasons.append("eval cases found")
    if classification.agent_type == "unknown":
        blockers.append("agent type unknown")
    if risk.risk_level == "unknown":
        blockers.append("risk level unknown")
    if risk.risk_level == "high":
        blockers.append("risk level high")

    for tool in capabilities.tools:
        if tool.category in {"shell_execution", "code_execution"} and not prompt_signals.has_safety:
            blockers.append("shell tool exists without safety policy")
        if tool.side_effect_level == "external_write" and not prompt_signals.has_human_approval:
            blockers.append("external write tool exists without approval rule")
        if tool.side_effect_level == "destructive" and not prompt_signals.has_safety:
            blockers.append("destructive tool without explicit restrictions")

    blockers = list(dict.fromkeys(blockers))
    return AutoReadiness(
        eligible=not blockers,
        reasons=list(dict.fromkeys(reasons)),
        blockers=blockers,
        required_safety_controls=required_controls,
    )


def generate_recommendation(
    *,
    risk: RiskAssessment,
    classification: AgentClassification,
    auto_readiness: AutoReadiness,
    allow_auto: bool,
    agent_arg: str | None,
    goal: str | None,
) -> tuple[Recommendation, str]:
    agent_part = f" --agent {agent_arg}" if agent_arg else ""
    goal_part = f" --goal {_quote(goal)}" if goal else ""
    alternatives: list[str] = []
    reasoning: list[str] = []

    if allow_auto and auto_readiness.eligible:
        command = f"agentdoctor auto{agent_part}{goal_part} --target-confidence 0.85 --max-rounds 6 --preview-patches --review on-fail"
        alternatives.append(f"agentdoctor deep{agent_part}{goal_part} --rounds 3 --review on-fail")
        return (
            Recommendation(
                recommended_mode="auto",
                recommended_rounds=6,
                suggested_review_policy="on-fail",
                target_confidence=0.85,
                reasoning=["--allow-auto was passed and auto readiness checks passed."],
                alternative_commands=alternatives,
            ),
            command,
        )

    if risk.risk_level == "low" and classification.agent_type != "unknown":
        command = f"agentdoctor quick{agent_part}{goal_part}"
        alternatives.append(f"agentdoctor deep{agent_part}{goal_part} --rounds 3 --review on-fail")
        reasoning.append("Low static risk was detected.")
        return (
            Recommendation("quick", 1, "on-fail", None, reasoning, alternatives),
            command,
        )
    if risk.risk_level == "high":
        command = f"agentdoctor deep{agent_part}{goal_part} --rounds 5 --review each-round"
        alternatives.append(f"agentdoctor deep{agent_part}{goal_part} --rounds 3 --review on-fail")
        reasoning.extend(["High static risk was detected.", "Each-round review is recommended for high-risk tools or side effects."])
        return (
            Recommendation("deep", 5, "each-round", None, reasoning, alternatives),
            command,
        )
    if risk.risk_level == "unknown" or classification.agent_type == "unknown":
        if not agent_arg:
            command = "agentdoctor triage --agent ./agent.yaml"
            alternatives.append(f"agentdoctor deep{goal_part} --rounds 3 --review on-fail")
            reasoning.append("Agent config or agent type is unknown; select an agent config before formal diagnosis.")
            return (
                Recommendation("deep", 3, "on-fail", None, reasoning, alternatives),
                command,
            )
        command = f"agentdoctor deep{agent_part}{goal_part} --rounds 3 --review on-fail"
        reasoning.append("Risk or type is unknown, so deep diagnosis gives broader coverage than quick mode.")
        return (
            Recommendation("deep", 3, "on-fail", None, reasoning, alternatives),
            command,
        )

    command = f"agentdoctor deep{agent_part}{goal_part} --rounds 3 --review on-fail"
    alternatives.append(f"agentdoctor quick{agent_part}{goal_part}")
    if not allow_auto and auto_readiness.eligible:
        alternatives.append(f"agentdoctor triage{agent_part}{goal_part} --allow-auto")
    reasoning.append("Medium static risk or incomplete coverage was detected.")
    return (
        Recommendation("deep", 3, "on-fail", None, reasoning, alternatives),
        command,
    )


def _pattern_has_match(pattern: str, detected: list[str]) -> bool:
    if "*" not in pattern:
        return pattern in detected
    prefix, suffix = pattern.split("*", 1)
    return any(item.startswith(prefix) and item.endswith(suffix) for item in detected)


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed


def _quote(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def _relative(root: Path, path: Path | str | None) -> str:
    if path is None:
        return ""
    target = Path(path)
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return target.as_posix()
