from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from contract2agent.triage.models import AgentClassification, DetectedCapabilities, DetectedTool
from contract2agent.triage.parsers import RawProjectData


HIGH_RISK_SIDE_EFFECTS = {"write_local", "external_write", "destructive", "unknown"}
EXTERNAL_SIDE_EFFECTS = {"external_read", "external_write"}


def classify_tools(tool_specs: list[dict[str, Any]]) -> DetectedCapabilities:
    tools: list[DetectedTool] = []
    for spec in tool_specs:
        name = str(spec.get("name") or spec.get("id") or "").strip()
        if not name:
            continue
        description = str(spec.get("description") or spec.get("summary") or "").strip()
        category, category_evidence = _tool_category(name, description, spec)
        side_effect, side_effect_evidence = _side_effect_level(name, description, category, spec)
        risk = _tool_risk_level(category, side_effect, name, description)
        requires_confirmation = side_effect in {"write_local", "external_write", "destructive"}
        evidence = [*category_evidence, *side_effect_evidence]
        source = spec.get("_source")
        if source:
            evidence.append(f"source: {source}")
        tools.append(
            DetectedTool(
                name=name,
                description=description or "unknown",
                category=category,
                risk_level=risk,
                side_effect_level=side_effect,
                requires_confirmation=requires_confirmation,
                evidence=evidence,
            )
        )

    tools = sorted(tools, key=lambda item: item.name.casefold())
    inputs = _infer_inputs(tools)
    outputs = []
    side_effects = sorted({tool.side_effect_level for tool in tools if tool.side_effect_level != "none"})
    external_dependencies = sorted(
        {
            tool.category
            for tool in tools
            if tool.side_effect_level in EXTERNAL_SIDE_EFFECTS or tool.category in {"web_search", "browser", "external_api", "email", "calendar", "database"}
        }
    )
    return DetectedCapabilities(
        tools=tools,
        inputs=inputs,
        outputs=outputs,
        side_effects=side_effects,
        external_dependencies=external_dependencies,
    )


def classify_agent_type(
    *,
    goal: str | None,
    data: RawProjectData,
    prompt_text: str,
    capabilities: DetectedCapabilities,
    eval_cases: list[dict[str, Any]],
) -> AgentClassification:
    evidence_by_type: dict[str, list[str]] = defaultdict(list)
    text = "\n".join(
        [
            goal or "",
            prompt_text,
            data.agent_config_text,
            " ".join(str(case.get("name", "")) + " " + str(case.get("tags", "")) for case in eval_cases),
        ]
    ).casefold()

    for tool in capabilities.tools:
        name_desc = f"{tool.name} {tool.description}".casefold()
        _score_tool_signal(name_desc, tool.name, evidence_by_type)

    _score_text_signal(
        text,
        "research_agent",
        [
            "paper",
            "research",
            "academic",
            "summarize",
            "citation",
            "theorem",
            "definition",
            "source",
            "evidence",
            "pdf",
            "document",
        ],
        evidence_by_type,
        source="prompt/goal/eval",
    )
    _score_text_signal(
        text,
        "coding_agent",
        ["code", "implement", "fix", "patch", "test", "repository", "bug", "pr", "diff"],
        evidence_by_type,
        source="prompt/goal/eval",
    )
    _score_text_signal(
        text,
        "workflow_agent",
        ["schedule", "send", "notify", "create", "update", "workflow", "assistant", "productivity"],
        evidence_by_type,
        source="prompt/goal/eval",
    )
    _score_text_signal(
        text,
        "data_analysis_agent",
        ["analyze", "dataset", "chart", "statistics", "table", "spreadsheet", "report", "calculation"],
        evidence_by_type,
        source="prompt/goal/eval",
    )
    _score_text_signal(
        text,
        "file_operation_agent",
        ["read file", "write file", "edit file", "save", "directory", "path", "filesystem"],
        evidence_by_type,
        source="prompt/goal/eval",
    )

    if capabilities.tools:
        if not any(evidence_by_type.values()):
            return AgentClassification(
                agent_type="general_tool_agent",
                classification_confidence="medium",
                evidence=["Detected tools but no specialized agent-type signal dominated."],
            )
    else:
        if prompt_text.strip() or data.agent_config_text.strip() or (goal and goal.strip()):
            return AgentClassification(
                agent_type="chat_agent",
                classification_confidence="medium",
                evidence=["No tools detected; prompt/config/goal indicates prompt-driven behavior."],
            )
        return AgentClassification(
            agent_type="unknown",
            classification_confidence="low",
            evidence=["No useful config, prompt, tool, eval, or goal signal found."],
        )

    counts = Counter({agent_type: len(evidence) for agent_type, evidence in evidence_by_type.items()})
    if not counts:
        return AgentClassification(
            agent_type="unknown",
            classification_confidence="low",
            evidence=["Signals were too weak to classify this agent."],
        )
    best_type, best_score = counts.most_common(1)[0]
    second_score = counts.most_common(2)[1][1] if len(counts) > 1 else 0
    evidence = evidence_by_type[best_type]

    independent_sources = _independent_source_count(evidence, goal, data, prompt_text, capabilities)
    if best_score >= 3 and independent_sources >= 3 and best_score >= second_score + 1:
        confidence = "high"
    elif best_score >= 2 and best_score >= second_score:
        confidence = "medium"
    else:
        confidence = "low"

    if best_score == second_score and second_score > 0:
        confidence = "low"
        evidence.append("Multiple agent types have similarly strong signals.")

    return AgentClassification(
        agent_type=best_type,
        classification_confidence=confidence,
        evidence=evidence,
    )


def _tool_category(name: str, description: str, spec: dict[str, Any]) -> tuple[str, list[str]]:
    text = f"{name} {description} {spec.get('type', '')} {spec.get('category', '')}".casefold()
    checks = [
        ("shell_execution", ["shell", "bash", "terminal", "command", "exec", "subprocess", "powershell"]),
        ("code_execution", ["code_runner", "python", "node", "interpreter", "execute", "test_runner", "run_code"]),
        ("email", ["email", "mail", "gmail", "outlook"]),
        ("calendar", ["calendar", "schedule", "event"]),
        ("communication", ["slack", "teams", "message", "notification", "notify", "sms"]),
        ("database", ["database", "sql", "postgres", "mysql", "sqlite", "warehouse"]),
        ("browser", ["browser", "browse", "page", "click"]),
        ("web_search", ["web_search", "web search", "search_web", "internet search"]),
        ("filesystem_write", ["file_writer", "file_editor", "write_file", "save_file", "config_editor", "patch", "diff"]),
        ("filesystem_read", ["file_reader", "read_file", "filesystem", "directory", "path"]),
        ("document_reading", ["document_reader", "pdf_reader", "pdf", "docx", "paper", "document"]),
        ("retrieval", ["retriever", "retrieve", "vector", "embedding", "rag"]),
        ("memory", ["memory", "remember", "recall"]),
        ("formatting", ["format", "markdown_formatter", "formatter"]),
        ("validation", ["validate", "validator", "json_schema", "schema"]),
        ("external_api", ["api", "http", "request", "client"]),
    ]
    for category, keywords in checks:
        for keyword in keywords:
            if keyword in text:
                return category, [f"Matched {category} keyword: {keyword}"]
    return "unknown", ["No category keyword matched."]


def _side_effect_level(name: str, description: str, category: str, spec: dict[str, Any]) -> tuple[str, list[str]]:
    explicit = str(spec.get("side_effect_level") or spec.get("side_effect") or spec.get("type") or "").casefold()
    explicit_map = {
        "none": "none",
        "read_only": "read_only",
        "readonly": "read_only",
        "read-only": "read_only",
        "write_local": "write_local",
        "local_write": "write_local",
        "external_read": "external_read",
        "external_write": "external_write",
        "destructive": "destructive",
        "side_effect": "write_local",
    }
    if explicit in explicit_map:
        return explicit_map[explicit], [f"Explicit side effect/type: {explicit}"]

    text = f"{name} {description}".casefold()
    destructive_keywords = ["delete", "remove", "deploy", "payment", "charge", "shell", "exec", "run", "destroy"]
    for keyword in destructive_keywords:
        if keyword in text:
            return "destructive", [f"Matched destructive keyword: {keyword}"]

    write_keywords = ["write", "edit", "update", "save", "create", "send", "insert", "post"]
    for keyword in write_keywords:
        if keyword in text:
            if category in {"email", "calendar", "communication", "database", "external_api"}:
                return "external_write", [f"Matched external write keyword: {keyword}"]
            return "write_local", [f"Matched local write keyword: {keyword}"]

    read_keywords = ["read", "load", "retrieve", "search", "fetch", "get", "query"]
    for keyword in read_keywords:
        if keyword in text:
            if category in {"web_search", "browser", "external_api", "email", "calendar", "database"}:
                return "external_read", [f"Matched external read keyword: {keyword}"]
            return "read_only", [f"Matched read-only keyword: {keyword}"]

    if category in {"formatting", "validation"}:
        return "none", [f"{category} tools are treated as no side effect."]
    if category in {"web_search", "browser", "external_api", "email", "calendar", "database"}:
        return "external_read", [f"{category} defaults to external read."]
    if category in {"document_reading", "filesystem_read", "retrieval", "memory"}:
        return "read_only", [f"{category} defaults to read-only."]
    return "unknown", ["Side effect could not be determined."]


def _tool_risk_level(category: str, side_effect: str, name: str, description: str) -> str:
    text = f"{name} {description}".casefold()
    if side_effect in {"write_local", "external_write", "destructive", "unknown"}:
        return "high"
    if category in {"shell_execution", "code_execution"}:
        return "high"
    if any(keyword in text for keyword in ["delete", "remove", "deploy", "payment", "charge"]):
        return "high"
    if side_effect in {"read_only", "external_read"}:
        return "medium"
    return "low"


def _infer_inputs(tools: list[DetectedTool]) -> list[str]:
    inputs = set()
    for tool in tools:
        if tool.category in {"document_reading", "filesystem_read", "filesystem_write"}:
            inputs.add("files")
        if tool.category in {"web_search", "browser", "external_api"}:
            inputs.add("web")
        if tool.category == "database":
            inputs.add("database_rows")
        if tool.category in {"email", "calendar", "communication"}:
            inputs.add("external_records")
    return sorted(inputs)


def _score_tool_signal(name_desc: str, tool_name: str, evidence_by_type: dict[str, list[str]]) -> None:
    specs = {
        "research_agent": ["document_reader", "pdf_reader", "web_search", "retriever", "citation", "paper", "theorem", "summarizer"],
        "coding_agent": ["code_runner", "test_runner", "file_editor", "shell", "git", "patch", "diff"],
        "workflow_agent": ["calendar", "email", "todo", "reminder", "task", "crm", "ticket", "notification"],
        "data_analysis_agent": ["csv_reader", "dataframe", "sql", "chart", "calculator", "python", "spreadsheet"],
        "file_operation_agent": ["file_reader", "file_writer", "filesystem", "directory", "path"],
    }
    for agent_type, keywords in specs.items():
        for keyword in keywords:
            if keyword in name_desc:
                evidence_by_type[agent_type].append(f"Detected {tool_name} tool matching {keyword}.")
                break


def _score_text_signal(
    text: str,
    agent_type: str,
    keywords: list[str],
    evidence_by_type: dict[str, list[str]],
    *,
    source: str,
) -> None:
    for keyword in keywords:
        if keyword in text:
            evidence_by_type[agent_type].append(f"{source} mentions {keyword}.")


def _independent_source_count(
    evidence: list[str],
    goal: str | None,
    data: RawProjectData,
    prompt_text: str,
    capabilities: DetectedCapabilities,
) -> int:
    count = 0
    if goal:
        count += 1
    if data.agent_config_text:
        count += 1
    if prompt_text:
        count += 1
    if capabilities.tools:
        count += 1
    return min(count, len(evidence))
