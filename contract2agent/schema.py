from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any

try:  # Prefer real Pydantic when the project dependencies are installed.
    from pydantic import BaseModel, Field

    try:
        from pydantic import ConfigDict
    except ImportError:  # Pydantic v1
        ConfigDict = None  # type: ignore[assignment]

    _HAS_PYDANTIC = True
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal envs.
    BaseModel = object  # type: ignore[assignment]
    Field = None  # type: ignore[assignment]
    ConfigDict = None  # type: ignore[assignment]
    _HAS_PYDANTIC = False

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is a declared dependency.
    yaml = None  # type: ignore[assignment]


_KNOWN_FORBIDDEN_TOOL_CAPABILITIES: dict[str, dict[str, Any]] = {
    "web_search": {
        "name": "no_web_search",
        "kind": "tool",
        "description": "The agent must not use web search or browse the internet.",
        "keywords": ["web", "search", "browse", "internet", "联网", "搜索"],
        "forbidden_tools": ["web_search"],
    },
    "shell_exec": {
        "name": "no_shell_execution",
        "kind": "tool",
        "description": "The agent must not execute shell commands.",
        "keywords": ["shell", "terminal", "command", "run", "rm -rf", "命令"],
        "forbidden_tools": ["shell_exec"],
    },
    "email_sender": {
        "name": "no_email_sending",
        "kind": "tool",
        "description": "The agent must not send emails.",
        "keywords": ["email", "mail", "邮件"],
        "forbidden_tools": ["email_sender"],
    },
    "delete_file": {
        "name": "no_file_deletion_or_overwrite",
        "kind": "action",
        "description": "The agent must not delete or overwrite local files.",
        "keywords": ["delete", "overwrite", "删除", "覆盖"],
        "forbidden_tools": ["delete_file"],
    },
}


def _capability_dict_for_forbidden_tool(tool: str) -> dict[str, Any]:
    if tool in _KNOWN_FORBIDDEN_TOOL_CAPABILITIES:
        return dict(_KNOWN_FORBIDDEN_TOOL_CAPABILITIES[tool])
    return {
        "name": f"no_{tool}",
        "kind": "tool",
        "description": f"The agent must not call the {tool} tool.",
        "keywords": [tool],
        "forbidden_tools": [tool],
    }


def _normalize_contract_data(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    forbidden_tools = list(normalized.get("forbidden_tools") or [])
    capabilities = [dict(cap) for cap in normalized.get("forbidden_capabilities") or []]

    for capability in capabilities:
        for tool in capability.get("forbidden_tools") or []:
            if tool not in forbidden_tools:
                forbidden_tools.append(tool)

    for tool in list(forbidden_tools):
        if not any(tool in (cap.get("forbidden_tools") or []) for cap in capabilities):
            capabilities.append(_capability_dict_for_forbidden_tool(str(tool)))

    normalized["forbidden_tools"] = forbidden_tools
    normalized["forbidden_capabilities"] = capabilities
    return normalized


if _HAS_PYDANTIC:

    class ContractModel(BaseModel):
        if ConfigDict is not None:
            model_config = ConfigDict(extra="forbid")  # type: ignore[misc]
        else:

            class Config:
                extra = "forbid"


    class ToolSpec(ContractModel):
        name: str
        type: str
        description: str | None = None


    class OutputSpec(ContractModel):
        format: str
        must_contain: list[str] = Field(default_factory=list)  # type: ignore[misc]


    class LimitSpec(ContractModel):
        max_steps: int = 6


    class RuleSpec(ContractModel):
        name: str
        description: str
        kind: str
        params: dict[str, Any] = Field(default_factory=dict)  # type: ignore[misc]


    class ForbiddenCapabilitySpec(ContractModel):
        name: str
        kind: str
        description: str
        keywords: list[str] = Field(default_factory=list)  # type: ignore[misc]
        forbidden_tools: list[str] = Field(default_factory=list)  # type: ignore[misc]
        expected_behavior: str = "refuse"


    class AgentContract(ContractModel):
        name: str
        goal: str
        tools: list[ToolSpec] = Field(default_factory=list)  # type: ignore[misc]
        forbidden_tools: list[str] = Field(default_factory=list)  # type: ignore[misc]
        forbidden_capabilities: list[ForbiddenCapabilitySpec] = Field(default_factory=list)  # type: ignore[misc]
        rules: list[RuleSpec] = Field(default_factory=list)  # type: ignore[misc]
        output: OutputSpec
        limits: LimitSpec

else:

    class _FallbackModel:
        @classmethod
        def model_validate(cls, data: dict[str, Any]) -> Any:
            return cls(**data)

        def model_dump(self) -> dict[str, Any]:
            return asdict(self)

        def dict(self) -> dict[str, Any]:
            return asdict(self)


    @dataclass
    class ToolSpec(_FallbackModel):
        name: str
        type: str
        description: str | None = None


    @dataclass
    class OutputSpec(_FallbackModel):
        format: str
        must_contain: list[str] = field(default_factory=list)


    @dataclass
    class LimitSpec(_FallbackModel):
        max_steps: int = 6


    @dataclass
    class RuleSpec(_FallbackModel):
        name: str
        description: str
        kind: str
        params: dict[str, Any] = field(default_factory=dict)


    @dataclass
    class ForbiddenCapabilitySpec(_FallbackModel):
        name: str
        kind: str
        description: str
        keywords: list[str] = field(default_factory=list)
        forbidden_tools: list[str] = field(default_factory=list)
        expected_behavior: str = "refuse"


    @dataclass
    class AgentContract(_FallbackModel):
        name: str
        goal: str
        tools: list[ToolSpec | dict[str, Any]] = field(default_factory=list)
        forbidden_tools: list[str] = field(default_factory=list)
        forbidden_capabilities: list[ForbiddenCapabilitySpec | dict[str, Any]] = field(default_factory=list)
        rules: list[RuleSpec | dict[str, Any]] = field(default_factory=list)
        output: OutputSpec | dict[str, Any] = field(
            default_factory=lambda: OutputSpec(format="markdown")
        )
        limits: LimitSpec | dict[str, Any] = field(default_factory=LimitSpec)

        def __post_init__(self) -> None:
            self.tools = [
                tool if isinstance(tool, ToolSpec) else ToolSpec(**tool)
                for tool in self.tools
            ]
            self.rules = [
                rule if isinstance(rule, RuleSpec) else RuleSpec(**rule)
                for rule in self.rules
            ]
            self.forbidden_capabilities = [
                capability
                if isinstance(capability, ForbiddenCapabilitySpec)
                else ForbiddenCapabilitySpec(**capability)
                for capability in self.forbidden_capabilities
            ]
            for capability in self.forbidden_capabilities:
                for tool in capability.forbidden_tools:
                    if tool not in self.forbidden_tools:
                        self.forbidden_tools.append(tool)
            for tool in list(self.forbidden_tools):
                if not any(
                    tool in capability.forbidden_tools
                    for capability in self.forbidden_capabilities
                ):
                    self.forbidden_capabilities.append(
                        ForbiddenCapabilitySpec(
                            **_capability_dict_for_forbidden_tool(tool)
                        )
                    )
            if isinstance(self.output, dict):
                self.output = OutputSpec(**self.output)
            if isinstance(self.limits, dict):
                self.limits = LimitSpec(**self.limits)


def model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    if is_dataclass(model):
        return asdict(model)
    raise TypeError(f"Unsupported model type: {type(model)!r}")


def contract_from_dict(data: dict[str, Any]) -> AgentContract:
    data = _normalize_contract_data(data)
    if hasattr(AgentContract, "model_validate"):
        return AgentContract.model_validate(data)  # type: ignore[attr-defined]
    return AgentContract(**data)


def save_contract(contract: AgentContract, path: str | Path) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required to write agent contracts.")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        yaml.safe_dump(model_to_dict(contract), sort_keys=False),
        encoding="utf-8",
    )


def load_contract(path: str | Path) -> AgentContract:
    if yaml is None:
        raise RuntimeError("PyYAML is required to read agent contracts.")
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Contract YAML must contain a mapping: {path}")
    return contract_from_dict(data)
