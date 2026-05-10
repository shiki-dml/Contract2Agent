from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


JsonObject = dict[str, Any]


@dataclass
class PrivacyDataFlow:
    flow_id: str
    channel: str
    source: str = ""
    destination: str = ""
    contains_sensitive_data: bool = False
    data_categories: list[str] = field(default_factory=list)
    controls: list[str] = field(default_factory=list)
    untrusted_input: bool = False
    external_destination: bool = False
    retention: str = "unknown"
    notes: str = ""


@dataclass
class PrivacyTool:
    name: str
    category: str = "tool"
    receives_sensitive_data: bool = False
    sends_external: bool = False
    untrusted_input_source: bool = False
    requires_approval: bool = False
    controls: list[str] = field(default_factory=list)


@dataclass
class PrivacyTrainingConfig:
    uses_private_training: bool = False
    sensitive_training_data: bool = False
    privacy_mechanism: str = "none"
    privacy_unit: str = ""
    epsilon: float | None = None
    delta: float | None = None
    clipping_norm: float | None = None
    noise_multiplier: float | None = None
    accountant: str = ""
    federated: bool = False
    multi_participation: bool = False
    participation_bound: int | None = None
    notes: str = ""


@dataclass
class PrivacyEvalProfile:
    profile_id: str
    name: str
    description: str = ""
    domain: str = "general"
    sensitive_data: list[str] = field(default_factory=list)
    data_flows: list[PrivacyDataFlow] = field(default_factory=list)
    tools: list[PrivacyTool] = field(default_factory=list)
    training: PrivacyTrainingConfig = field(default_factory=PrivacyTrainingConfig)
    declared_controls: list[str] = field(default_factory=list)
    policy_constraints: list[str] = field(default_factory=list)
    approved_disclosures: list[str] = field(default_factory=list)
    forbidden_disclosures: list[str] = field(default_factory=list)
    metadata: JsonObject = field(default_factory=dict)


@dataclass
class PrivacyFinding:
    finding_id: str
    severity: str
    category: str
    summary: str
    evidence: list[str] = field(default_factory=list)
    recommendation: str = ""
    source_reference: str = ""


@dataclass
class PrivacyScorecard:
    profile_id: str
    overall_privacy_readiness: float = 0.0
    leakage_risk_score: float = 0.0
    channel_coverage: float = 0.0
    dp_readiness: float = 0.0
    prompt_injection_resilience: float = 0.0
    auditability: float = 0.0
    minimization: float = 0.0
    approval_safety: float = 0.0
    findings: list[PrivacyFinding] = field(default_factory=list)
    recommended_next_tests: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    source_references: list[JsonObject] = field(default_factory=list)


@dataclass
class PrivacyEvalReport:
    profile: PrivacyEvalProfile
    scorecard: PrivacyScorecard
    markdown: str
    json_report: JsonObject


def to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dict(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def profile_from_dict(data: JsonObject) -> PrivacyEvalProfile:
    profile_data = dict(data)
    profile_data["data_flows"] = [
        data_flow_from_dict(item) for item in profile_data.get("data_flows", [])
    ]
    profile_data["tools"] = [
        tool_from_dict(item) for item in profile_data.get("tools", [])
    ]
    training = profile_data.get("training") or {}
    profile_data["training"] = training_from_dict(training)
    return PrivacyEvalProfile(**_filter_kwargs(PrivacyEvalProfile, profile_data))


def data_flow_from_dict(data: JsonObject) -> PrivacyDataFlow:
    return PrivacyDataFlow(**_filter_kwargs(PrivacyDataFlow, dict(data)))


def tool_from_dict(data: JsonObject) -> PrivacyTool:
    return PrivacyTool(**_filter_kwargs(PrivacyTool, dict(data)))


def training_from_dict(data: JsonObject) -> PrivacyTrainingConfig:
    return PrivacyTrainingConfig(**_filter_kwargs(PrivacyTrainingConfig, dict(data)))


def _filter_kwargs(cls: type, data: JsonObject) -> JsonObject:
    field_names = set(getattr(cls, "__dataclass_fields__", {}))
    return {key: value for key, value in data.items() if key in field_names}
