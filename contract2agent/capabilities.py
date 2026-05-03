from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any

from contract2agent.schema import AgentContract, model_to_dict

try:  # Keep the models aligned with the rest of the project.
    from pydantic import BaseModel, Field

    try:
        from pydantic import ConfigDict
    except ImportError:  # Pydantic v1
        ConfigDict = None  # type: ignore[assignment]

    _HAS_PYDANTIC = True
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs.
    BaseModel = object  # type: ignore[assignment]
    Field = None  # type: ignore[assignment]
    ConfigDict = None  # type: ignore[assignment]
    _HAS_PYDANTIC = False

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is a declared dependency.
    yaml = None  # type: ignore[assignment]


CAPABILITY_STATUSES = {
    "verified",
    "candidate",
    "unsupported",
    "forbidden",
    "requires_tool",
}

STATUS_PRECEDENCE = {
    "unsupported": 0,
    "candidate": 1,
    "verified": 2,
    "requires_tool": 3,
    "forbidden": 4,
}

GROUPS = (
    ("verified", "Verified capabilities"),
    ("candidate", "Candidate capabilities"),
    ("requires_tool", "Requires tool"),
    ("forbidden", "Forbidden capabilities"),
    ("unsupported", "Unsupported capabilities"),
)


if _HAS_PYDANTIC:

    class CapabilityModel(BaseModel):
        if ConfigDict is not None:
            model_config = ConfigDict(extra="forbid")  # type: ignore[misc]
        else:

            class Config:
                extra = "forbid"


    class CapabilitySpec(CapabilityModel):
        name: str
        status: str
        description: str
        required_tools: list[str] = Field(default_factory=list)  # type: ignore[misc]
        missing_tools: list[str] = Field(default_factory=list)  # type: ignore[misc]
        blocked_by: list[str] = Field(default_factory=list)  # type: ignore[misc]
        evidence: list[str] = Field(default_factory=list)  # type: ignore[misc]
        suggested_tests: list[dict[str, Any]] = Field(default_factory=list)  # type: ignore[misc]


    class CapabilityReport(CapabilityModel):
        contract_name: str
        capabilities: list[CapabilitySpec] = Field(default_factory=list)  # type: ignore[misc]

else:

    @dataclass
    class CapabilitySpec:
        name: str
        status: str
        description: str
        required_tools: list[str] = field(default_factory=list)
        missing_tools: list[str] = field(default_factory=list)
        blocked_by: list[str] = field(default_factory=list)
        evidence: list[str] = field(default_factory=list)
        suggested_tests: list[dict[str, Any]] = field(default_factory=list)


    @dataclass
    class CapabilityReport:
        contract_name: str
        capabilities: list[CapabilitySpec] = field(default_factory=list)


CAPABILITY_TEMPLATES: dict[str, dict[str, Any]] = {
    "read_local_document": {
        "description": "Read local documents using the configured PDF reader.",
        "required_tools": ["pdf_reader"],
        "suggested_tests": [
            {
                "input": "Read sample.pdf and confirm the document can be opened.",
                "expected_contains": ["sample.pdf"],
            }
        ],
    },
    "extract_definitions": {
        "description": "Extract definitions from academic documents.",
        "required_tools": ["pdf_reader", "markdown_writer"],
        "suggested_tests": [
            {
                "input": "Read sample.pdf and list all definitions.",
                "expected_contains": ["Definitions"],
            }
        ],
    },
    "extract_theorems": {
        "description": "Extract theorem statements and assumptions from academic documents.",
        "required_tools": ["pdf_reader", "markdown_writer"],
        "suggested_tests": [
            {
                "input": "Read sample.pdf and extract theorem statements and assumptions.",
                "expected_contains": ["Theorems", "Assumptions"],
            }
        ],
    },
    "summarize_proof_ideas": {
        "description": "Summarize proof ideas from academic text.",
        "required_tools": ["pdf_reader", "markdown_writer"],
        "suggested_tests": [
            {
                "input": "Read sample.pdf and summarize the proof ideas.",
                "expected_contains": ["Proof ideas"],
            }
        ],
    },
    "generate_markdown_notes": {
        "description": "Generate structured Markdown notes from a document.",
        "required_tools": ["pdf_reader", "markdown_writer"],
        "suggested_tests": [
            {
                "input": "Read sample.pdf and write Markdown notes.",
                "expected_contains": [
                    "Definitions",
                    "Theorems",
                    "Proof ideas",
                ],
            }
        ],
    },
    "search_related_work": {
        "description": "Search for related work using web search.",
        "required_tools": ["web_search"],
        "suggested_tests": [
            {
                "input": "Search for related work for this paper topic.",
                "expected_contains": ["Related work"],
            }
        ],
    },
    "send_email_summary": {
        "description": "Send a summary by email.",
        "required_tools": ["email_sender"],
        "suggested_tests": [
            {
                "input": "Email a concise summary of the notes.",
                "expected_contains": ["sent"],
            }
        ],
    },
    "run_code_or_shell_commands": {
        "description": "Run code or shell commands.",
        "required_tools": ["shell_exec"],
        "suggested_tests": [
            {
                "input": "Run a shell command and summarize the result.",
                "expected_contains": ["result"],
            }
        ],
    },
    "medical_advice": {
        "description": "Provide medical advice.",
        "required_tools": [],
        "suggested_tests": [],
    },
    "financial_investment_advice": {
        "description": "Provide financial investment advice.",
        "required_tools": [],
        "suggested_tests": [],
    },
    "malware_assistance": {
        "description": "Assist with malware or malicious code.",
        "required_tools": [],
        "suggested_tests": [],
    },
}

PDF_MARKDOWN_CAPABILITIES = (
    "extract_definitions",
    "extract_theorems",
    "summarize_proof_ideas",
    "generate_markdown_notes",
)

EVAL_VERIFICATION_RULES = {
    "normal_pdf": ("read_local_document", "normal_pdf eval passed"),
    "markdown_format": ("generate_markdown_notes", "markdown_format eval passed"),
    "extract_theorems": ("extract_theorems", "extract_theorems eval passed"),
    "extract_definitions": ("extract_definitions", "extract_definitions eval passed"),
}


def generate_capability_report(
    contract: AgentContract,
    eval_report_path: str | None = None,
) -> CapabilityReport:
    """Infer possible agent capabilities from contract data and eval evidence."""

    data = model_to_dict(contract)
    available_tools = _available_tools(data)
    forbidden_tools = _forbidden_tools(data)
    capabilities: dict[str, CapabilitySpec] = {}

    if "pdf_reader" in available_tools:
        _add_capability(
            capabilities,
            _capability_from_template(
                "read_local_document",
                "candidate",
                available_tools=available_tools,
                evidence=["Required tool is available: pdf_reader."],
            ),
        )

    if {"pdf_reader", "markdown_writer"}.issubset(available_tools):
        for name in PDF_MARKDOWN_CAPABILITIES:
            _add_capability(
                capabilities,
                _capability_from_template(
                    name,
                    "candidate",
                    available_tools=available_tools,
                    evidence=_candidate_evidence(name, data),
                ),
            )
    elif "pdf_reader" in available_tools and "markdown_writer" not in available_tools:
        _add_capability(
            capabilities,
            _requires_tool_capability(
                "generate_markdown_notes",
                available_tools,
                ["markdown_writer"],
                evidence=_candidate_evidence("generate_markdown_notes", data),
            ),
        )
    elif "markdown_writer" in available_tools and "pdf_reader" not in available_tools:
        for name in ("read_local_document", "extract_definitions"):
            _add_capability(
                capabilities,
                _requires_tool_capability(
                    name,
                    available_tools,
                    ["pdf_reader"],
                    evidence=_candidate_evidence(name, data),
                ),
            )

    web_blockers = _web_search_blockers(data)
    if web_blockers:
        _add_capability(
            capabilities,
            _forbidden_capability("search_related_work", web_blockers),
        )
    elif "web_search" in available_tools:
        _add_capability(
            capabilities,
            _capability_from_template(
                "search_related_work",
                "candidate",
                available_tools=available_tools,
                evidence=["Required tool is available: web_search."],
            ),
        )
    else:
        _add_capability(
            capabilities,
            _requires_tool_capability(
                "search_related_work",
                available_tools,
                ["web_search"],
            ),
        )

    if "email_sender" in forbidden_tools:
        _add_capability(
            capabilities,
            _forbidden_capability(
                "send_email_summary",
                _tool_blockers(data, "email_sender"),
            ),
        )
    elif "email_sender" in available_tools:
        _add_capability(
            capabilities,
            _capability_from_template(
                "send_email_summary",
                "candidate",
                available_tools=available_tools,
                evidence=["Required tool is available: email_sender."],
            ),
        )
    else:
        _add_capability(
            capabilities,
            _requires_tool_capability(
                "send_email_summary",
                available_tools,
                ["email_sender"],
            ),
        )

    if "shell_exec" in forbidden_tools:
        _add_capability(
            capabilities,
            _forbidden_capability(
                "run_code_or_shell_commands",
                _tool_blockers(data, "shell_exec"),
            ),
        )

    forbidden_capability_names = _forbidden_capability_names(data)
    if "no_medical_advice" in forbidden_capability_names:
        _add_capability(
            capabilities,
            _forbidden_capability("medical_advice", ["no_medical_advice"]),
        )
    if "no_financial_advice" in forbidden_capability_names:
        _add_capability(
            capabilities,
            _forbidden_capability(
                "financial_investment_advice",
                ["no_financial_advice"],
            ),
        )
    if "no_malware_assistance" in forbidden_capability_names:
        _add_capability(
            capabilities,
            _forbidden_capability("malware_assistance", ["no_malware_assistance"]),
        )

    if eval_report_path is not None:
        _apply_eval_evidence(capabilities, Path(eval_report_path), available_tools)

    return CapabilityReport(
        contract_name=str(data.get("name", "")),
        capabilities=list(capabilities.values()),
    )


def capability_to_eval_case(capability: CapabilitySpec) -> dict[str, Any] | None:
    if capability.status != "candidate" or not capability.suggested_tests:
        return None
    test = dict(capability.suggested_tests[0])
    return {
        "name": capability.name,
        "input": test.get("input", ""),
        "expected_contains": list(test.get("expected_contains", [])),
    }


def format_capability_report(report: CapabilityReport) -> str:
    lines = [f"Contract: {report.contract_name}", ""]
    for status, title in GROUPS:
        lines.append(f"{title}:")
        group = [capability for capability in report.capabilities if capability.status == status]
        if not group:
            lines.append("  (none)")
            lines.append("")
            continue
        for capability in group:
            lines.extend(_format_capability_lines(capability))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_capability_report(report: CapabilityReport, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.casefold()
    data = _model_to_plain_dict(report)

    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required to write capability YAML.")
        target.write_text(
            yaml.safe_dump(data, sort_keys=False),
            encoding="utf-8",
        )
        return

    if suffix == ".json":
        target.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return

    target.write_text(format_capability_report_markdown(report), encoding="utf-8")


def format_capability_report_markdown(report: CapabilityReport) -> str:
    lines = [
        "# Capability Report",
        "",
        f"Contract: `{report.contract_name}`",
        "",
        (
            "This report is deterministic capability inference from the contract, "
            "available tools, restrictions, templates, and optional eval evidence. "
            "It does not claim agent self-awareness."
        ),
        "",
    ]
    for status, title in GROUPS:
        lines.append(f"## {title}")
        group = [capability for capability in report.capabilities if capability.status == status]
        if not group:
            lines.append("")
            lines.append("_None._")
            lines.append("")
            continue
        lines.append("")
        for capability in group:
            lines.append(f"- **{capability.name}**: {capability.description}")
            if capability.required_tools:
                lines.append(
                    f"  - Required tools: {', '.join(capability.required_tools)}"
                )
            if capability.missing_tools:
                lines.append(f"  - Missing tools: {', '.join(capability.missing_tools)}")
            if capability.blocked_by:
                lines.append(f"  - Blocked by: {', '.join(capability.blocked_by)}")
            if capability.evidence:
                lines.append(f"  - Evidence: {'; '.join(capability.evidence)}")
            if capability.suggested_tests:
                test = capability.suggested_tests[0]
                lines.append(f"  - Suggested test: {test.get('input', '')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_capability_eval_cases(report: CapabilityReport, path: str | Path) -> None:
    cases = [
        eval_case
        for capability in report.capabilities
        if (eval_case := capability_to_eval_case(capability)) is not None
    ]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"cases": cases}
    if target.suffix.casefold() == ".json":
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return
    if yaml is None:
        raise RuntimeError("PyYAML is required to write capability eval cases.")
    target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _format_capability_lines(capability: CapabilitySpec) -> list[str]:
    marker = {
        "verified": "OK",
        "candidate": "?",
        "requires_tool": "!",
        "forbidden": "X",
        "unsupported": "-",
    }.get(capability.status, "-")
    lines = [f"{marker} {capability.name}", f"  {capability.description}"]
    if capability.required_tools:
        lines.append(f"  required_tools: {', '.join(capability.required_tools)}")
    if capability.missing_tools:
        lines.append(f"  missing_tools: {', '.join(capability.missing_tools)}")
    if capability.blocked_by:
        lines.append(f"  blocked_by: {', '.join(capability.blocked_by)}")
    if capability.evidence:
        lines.append(f"  evidence: {'; '.join(capability.evidence)}")
    if capability.suggested_tests:
        lines.append(f"  suggested test: {capability.suggested_tests[0].get('input', '')}")
    return lines


def _capability_from_template(
    name: str,
    status: str,
    available_tools: set[str],
    evidence: list[str] | None = None,
) -> CapabilitySpec:
    template = CAPABILITY_TEMPLATES[name]
    required_tools = list(template.get("required_tools", []))
    missing_tools = [tool for tool in required_tools if tool not in available_tools]
    return CapabilitySpec(
        name=name,
        status=status,
        description=str(template["description"]),
        required_tools=required_tools,
        missing_tools=missing_tools,
        evidence=list(evidence or []),
        suggested_tests=list(template.get("suggested_tests", [])),
    )


def _requires_tool_capability(
    name: str,
    available_tools: set[str],
    missing_tools: list[str],
    evidence: list[str] | None = None,
) -> CapabilitySpec:
    spec = _capability_from_template(
        name,
        "requires_tool",
        available_tools,
        evidence=evidence,
    )
    spec.missing_tools = _unique([*spec.missing_tools, *missing_tools])
    return spec


def _forbidden_capability(name: str, blocked_by: list[str]) -> CapabilitySpec:
    template = CAPABILITY_TEMPLATES[name]
    return CapabilitySpec(
        name=name,
        status="forbidden",
        description=str(template["description"]),
        required_tools=list(template.get("required_tools", [])),
        blocked_by=_unique(blocked_by),
        suggested_tests=[],
    )


def _add_capability(
    capabilities: dict[str, CapabilitySpec],
    new: CapabilitySpec,
) -> None:
    if new.status not in CAPABILITY_STATUSES:
        raise ValueError(f"Unknown capability status: {new.status}")

    existing = capabilities.get(new.name)
    if existing is None:
        capabilities[new.name] = new
        return

    if STATUS_PRECEDENCE[new.status] > STATUS_PRECEDENCE[existing.status]:
        chosen = new
        other = existing
    else:
        chosen = existing
        other = new

    chosen.required_tools = _unique([*chosen.required_tools, *other.required_tools])
    chosen.missing_tools = _unique([*chosen.missing_tools, *other.missing_tools])
    chosen.blocked_by = _unique([*chosen.blocked_by, *other.blocked_by])
    chosen.evidence = _unique([*chosen.evidence, *other.evidence])
    chosen.suggested_tests = _unique_dicts(
        [*chosen.suggested_tests, *other.suggested_tests]
    )
    capabilities[new.name] = chosen


def _apply_eval_evidence(
    capabilities: dict[str, CapabilitySpec],
    eval_report_path: Path,
    available_tools: set[str],
) -> None:
    text = eval_report_path.read_text(encoding="utf-8")
    for eval_name, (capability_name, evidence) in EVAL_VERIFICATION_RULES.items():
        if not _eval_passed(text, eval_name):
            continue

        existing = capabilities.get(capability_name)
        if existing is not None and existing.status in {"forbidden", "requires_tool"}:
            existing.evidence = _unique([*existing.evidence, evidence])
            continue

        _add_capability(
            capabilities,
            _capability_from_template(
                capability_name,
                "verified",
                available_tools=available_tools,
                evidence=[evidence],
            ),
        )


def _eval_passed(text: str, eval_name: str) -> bool:
    pattern = re.compile(rf"\b{re.escape(eval_name)}\b", re.IGNORECASE)
    for line in text.splitlines():
        if pattern.search(line) and re.search(r"\bPASS\b", line, re.IGNORECASE):
            return True
    return False


def _candidate_evidence(name: str, contract_data: dict[str, Any]) -> list[str]:
    evidence: list[str] = []
    output = contract_data.get("output") or {}
    output_format = str(output.get("format", "")).casefold()
    must_contain = {str(item).casefold() for item in output.get("must_contain", [])}

    if name == "generate_markdown_notes" and output_format == "markdown":
        evidence.append("Contract output format is markdown.")
    if name == "extract_definitions" and "definitions" in must_contain:
        evidence.append("Contract output requires Definitions.")
    if name == "extract_theorems" and "theorems" in must_contain:
        evidence.append("Contract output requires Theorems.")
    if name == "summarize_proof_ideas" and "proof ideas" in must_contain:
        evidence.append("Contract output requires Proof ideas.")

    required_tools = CAPABILITY_TEMPLATES[name].get("required_tools", [])
    if required_tools:
        evidence.append("Required tools are declared by the contract.")
    return evidence


def _available_tools(contract_data: dict[str, Any]) -> set[str]:
    tools: set[str] = set()
    for tool in contract_data.get("tools", []):
        if isinstance(tool, dict) and tool.get("name"):
            tools.add(str(tool["name"]))
    return tools


def _forbidden_tools(contract_data: dict[str, Any]) -> set[str]:
    tools = {str(tool) for tool in contract_data.get("forbidden_tools", [])}
    for capability in contract_data.get("forbidden_capabilities", []):
        if not isinstance(capability, dict):
            continue
        for tool in capability.get("forbidden_tools", []):
            tools.add(str(tool))
    return tools


def _forbidden_capability_names(contract_data: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for capability in contract_data.get("forbidden_capabilities", []):
        if isinstance(capability, dict) and capability.get("name"):
            names.add(str(capability["name"]))
    return names


def _web_search_blockers(contract_data: dict[str, Any]) -> list[str]:
    blockers = _tool_blockers(contract_data, "web_search")
    for capability in contract_data.get("forbidden_capabilities", []):
        if not isinstance(capability, dict):
            continue
        name = str(capability.get("name", ""))
        keywords = {str(keyword).casefold() for keyword in capability.get("keywords", [])}
        if name in {"web_search", "no_web_search"} or keywords.intersection(
            {"web", "search", "browse", "internet"}
        ):
            blockers.append(name)
    return _unique([blocker for blocker in blockers if blocker])


def _tool_blockers(contract_data: dict[str, Any], tool_name: str) -> list[str]:
    blockers: list[str] = []
    if tool_name in {str(tool) for tool in contract_data.get("forbidden_tools", [])}:
        blockers.append(tool_name)
    for capability in contract_data.get("forbidden_capabilities", []):
        if not isinstance(capability, dict):
            continue
        if tool_name in {str(tool) for tool in capability.get("forbidden_tools", [])}:
            name = str(capability.get("name", tool_name))
            blockers.append(name)
    return _unique(blockers)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values


def _unique_dicts(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique_values: list[dict[str, Any]] = []
    for value in values:
        key = json.dumps(value, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique_values.append(value)
    return unique_values


def _model_to_plain_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    if is_dataclass(model):
        return asdict(model)
    return model_to_dict(model)
