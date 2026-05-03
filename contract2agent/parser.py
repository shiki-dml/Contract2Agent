from __future__ import annotations

from contract2agent.schema import (
    AgentContract,
    ForbiddenCapabilitySpec,
    LimitSpec,
    OutputSpec,
    RuleSpec,
    ToolSpec,
)

PAPER_KEYWORDS = ("paper", "pdf", "theorem", "definition", "proof")
MISSING_FILE_PHRASES = ("missing file", "file not found", "missing.pdf", "not found")
DEFAULT_OUTPUT_SECTIONS = ["Definitions", "Theorems", "Proof ideas"]

FORBIDDEN_CAPABILITY_PATTERNS = (
    (
        (
            "must not use web search",
            "cannot browse",
            "do not search online",
            "do not browse",
            "don't browse",
            "must not browse",
            "cannot search",
            "no web",
            "without web",
            "no internet",
            "offline",
            "use web search",
            "不能联网",
            "不能搜索",
            "不能浏览网页",
        ),
        ForbiddenCapabilitySpec(
            name="no_web_search",
            kind="tool",
            description="The agent must not use web search or browse the internet.",
            keywords=["web", "search", "browse", "internet", "联网", "搜索"],
            forbidden_tools=["web_search"],
        ),
    ),
    (
        (
            "must not execute shell commands",
            "cannot run terminal commands",
            "must not run terminal commands",
            "cannot execute shell commands",
            "execute shell commands",
            "run terminal commands",
            "不能执行命令",
            "不能运行 shell",
        ),
        ForbiddenCapabilitySpec(
            name="no_shell_execution",
            kind="tool",
            description="The agent must not execute shell commands.",
            keywords=["shell", "terminal", "command", "run", "rm -rf", "命令"],
            forbidden_tools=["shell_exec"],
        ),
    ),
    (
        (
            "must not send emails",
            "cannot email users",
            "cannot send emails",
            "send emails",
            "email users",
            "不能发邮件",
        ),
        ForbiddenCapabilitySpec(
            name="no_email_sending",
            kind="tool",
            description="The agent must not send emails.",
            keywords=["email", "mail", "邮件"],
            forbidden_tools=["email_sender"],
        ),
    ),
    (
        (
            "must not delete files",
            "must not overwrite files",
            "should not delete",
            "delete or overwrite",
            "cannot delete files",
            "cannot overwrite files",
            "不能删除文件",
            "不能覆盖文件",
        ),
        ForbiddenCapabilitySpec(
            name="no_file_deletion_or_overwrite",
            kind="action",
            description="The agent must not delete or overwrite local files.",
            keywords=["delete", "overwrite", "file", "删除", "覆盖", "文件"],
            forbidden_tools=["delete_file"],
        ),
    ),
    (
        (
            "must not provide medical advice",
            "cannot give medical advice",
            "must not give medical advice",
            "provide medical advice",
            "不能提供医疗建议",
        ),
        ForbiddenCapabilitySpec(
            name="no_medical_advice",
            kind="intent",
            description="The agent must refuse requests asking for medical advice.",
            keywords=[
                "medical",
                "medicine",
                "diagnosis",
                "symptom",
                "drug",
                "doctor",
                "医疗",
                "药",
                "诊断",
                "症状",
            ],
        ),
    ),
    (
        (
            "must not provide financial advice",
            "cannot give investment advice",
            "must not give investment advice",
            "financial investment advice",
            "provide financial advice",
            "provide investment advice",
            "不能提供投资建议",
        ),
        ForbiddenCapabilitySpec(
            name="no_financial_advice",
            kind="intent",
            description="The agent must refuse requests asking for financial investment advice.",
            keywords=[
                "investment",
                "stock",
                "buy",
                "sell",
                "portfolio",
                "financial",
                "投资",
                "股票",
                "买入",
                "卖出",
            ],
        ),
    ),
    (
        (
            "must not help with malware",
            "must refuse malicious code requests",
            "must refuse requests related to malware",
            "requests related to malware",
            "cannot help with malware",
            "malicious code requests",
            "不能写恶意代码",
        ),
        ForbiddenCapabilitySpec(
            name="no_malware_assistance",
            kind="intent",
            description="The agent must refuse requests related to malware or malicious code.",
            keywords=[
                "malware",
                "virus",
                "phishing",
                "credential theft",
                "恶意代码",
                "病毒",
                "钓鱼",
            ],
        ),
    ),
)


def parse_requirement(requirement: str) -> AgentContract:
    text = requirement.casefold()
    goal = requirement.strip() or "Read a PDF paper and produce structured notes."
    forbidden_capabilities = _forbidden_capabilities_for(text)
    forbidden_tools = _forbidden_tools_for(forbidden_capabilities)

    return AgentContract(
        name=_agent_name_for(text),
        goal=goal,
        tools=_paper_reader_tools(),
        forbidden_tools=forbidden_tools,
        forbidden_capabilities=forbidden_capabilities,
        rules=_rules_for(text, forbidden_tools),
        output=OutputSpec(format="markdown", must_contain=DEFAULT_OUTPUT_SECTIONS),
        limits=LimitSpec(max_steps=6),
    )


def _agent_name_for(text: str) -> str:
    if any(keyword in text for keyword in PAPER_KEYWORDS):
        return "paper_reader_agent"
    return "paper_reader_agent"


def _paper_reader_tools() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="pdf_reader",
            type="read_only",
            description="Reads a local PDF and extracts text for note generation.",
        ),
        ToolSpec(
            name="markdown_writer",
            type="side_effect",
            description="Writes structured Markdown notes to disk.",
        ),
    ]


def _forbidden_capabilities_for(text: str) -> list[ForbiddenCapabilitySpec]:
    capabilities: list[ForbiddenCapabilitySpec] = []
    for phrases, capability in FORBIDDEN_CAPABILITY_PATTERNS:
        if any(phrase in text for phrase in phrases):
            capabilities.append(capability)
    return capabilities


def _forbidden_tools_for(
    forbidden_capabilities: list[ForbiddenCapabilitySpec],
) -> list[str]:
    tools: list[str] = []
    for capability in forbidden_capabilities:
        for tool in capability.forbidden_tools:
            if tool not in tools:
                tools.append(tool)
    return tools


def _rules_for(text: str, forbidden_tools: list[str]) -> list[RuleSpec]:
    rules = [
        RuleSpec(
            name="must_read_before_write",
            description="markdown_writer requires a previous successful pdf_reader result.",
            kind="require_tool_before_tool",
            params={
                "tool": "markdown_writer",
                "required_tool": "pdf_reader",
                "required_status": "ok",
            },
        ),
        RuleSpec(
            name="final_output_has_sections",
            description="Final Markdown output must include the required paper note sections.",
            kind="final_output_contains",
            params={"items": DEFAULT_OUTPUT_SECTIONS},
        ),
        RuleSpec(
            name="max_trace_steps",
            description="Trace length must not exceed 6 events.",
            kind="max_steps",
            params={"max_steps": 6},
        ),
    ]

    if any(phrase in text for phrase in MISSING_FILE_PHRASES):
        rules.append(
            RuleSpec(
                name="no_write_on_missing_file",
                description="markdown_writer is forbidden if pdf_reader returns file_not_found.",
                kind="forbid_tool_after_tool_error",
                params={
                    "tool": "markdown_writer",
                    "after_tool": "pdf_reader",
                    "error_status": "file_not_found",
                },
            )
        )

    for tool_name in forbidden_tools:
        rules.append(
            RuleSpec(
                name=f"forbid_{tool_name}",
                description=f"{tool_name} is forbidden by the contract.",
                kind="forbid_tool",
                params={"tool": tool_name},
            )
        )

    return rules
