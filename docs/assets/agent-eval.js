(function () {
  "use strict";

  const TYPE_DEFS = [
    {
      type_id: "coding_agent",
      label: "Coding Agent",
      capability_signals: ["code", "repository", "repo", "patch", "test", "build", "diff"],
      tool_signals: ["shell", "terminal", "pytest", "git", "file_write", "code_editor", "apply_patch", "compiler", "test_runner"],
      task_signals: ["fix failing test", "repair bug", "edit code", "run tests", "build", "minimal patch", "patch"],
      eval_categories: ["coding_change_safety", "tool_and_permission_safety", "trace_and_state_observability"],
      evidence_requirements: ["patch artifact", "test/build output", "command trace"]
    },
    {
      type_id: "file_reading_agent",
      label: "File Reading Agent",
      capability_signals: ["file", "document", "read", "citation", "source", "pdf"],
      tool_signals: ["file_read", "reader", "pdf_reader", "document_reader", "citation", "search_local"],
      task_signals: ["cite source", "answer from files", "summarize document", "missing file", "quote evidence"],
      eval_categories: ["document_grounding", "evidence_and_citation_quality", "tool_and_permission_safety"],
      evidence_requirements: ["provided file corpus", "answer-to-source trace", "missing-file behavior test"]
    },
    {
      type_id: "browser_navigation_agent",
      label: "Browser Navigation Agent",
      capability_signals: ["browser", "web navigation", "website", "page", "form"],
      tool_signals: ["browser", "navigate", "click", "dom", "screenshot", "form", "submit"],
      task_signals: ["navigate", "fill form", "verify page", "gather web", "submit form"],
      eval_categories: ["browser_task_flow", "side_effect_and_approval_safety", "trace_and_state_observability"],
      evidence_requirements: ["controlled browser trace", "page-state validation", "approval record for submit actions"]
    },
    {
      type_id: "contract_review_agent",
      label: "Contract Review Agent",
      capability_signals: ["contract", "clause", "obligation", "legal", "rule", "policy"],
      tool_signals: ["contract_parser", "clause_extractor", "document_reader", "pdf_reader", "citation"],
      task_signals: ["review contract", "identify obligation", "evidence gap", "clause", "fact pattern"],
      eval_categories: ["document_grounding", "evidence_and_citation_quality", "trace_and_state_observability"],
      evidence_requirements: ["source document", "clause-to-output trace", "uncertainty handling checks"]
    },
    {
      type_id: "research_agent",
      label: "Research Agent",
      capability_signals: ["research", "source", "citation", "evidence", "freshness", "paper"],
      tool_signals: ["web_search", "search", "browser", "reader", "citation", "scholar"],
      task_signals: ["find sources", "synthesize evidence", "conflicting evidence", "cite", "freshness"],
      eval_categories: ["research_source_quality", "evidence_and_citation_quality", "trace_and_state_observability"],
      evidence_requirements: ["source list", "citation-to-claim trace", "conflicting-evidence task"]
    },
    {
      type_id: "workflow_automation_agent",
      label: "Workflow Automation Agent",
      capability_signals: ["workflow", "automation", "handoff", "routing", "state", "orchestration"],
      tool_signals: ["scheduler", "queue", "router", "email", "calendar", "workflow", "handoff"],
      task_signals: ["multi-step", "handoff", "route", "state tracking", "loop control", "approval workflow"],
      eval_categories: ["workflow_state_control", "side_effect_and_approval_safety", "trace_and_state_observability"],
      evidence_requirements: ["multi-step trace", "state transition record", "loop and handoff boundary tests"]
    },
    {
      type_id: "financial_transaction_agent_simulated",
      label: "Financial Transaction Agent (Simulated)",
      capability_signals: ["payment", "transaction", "trade", "order", "checkout", "transfer"],
      tool_signals: ["payment", "transfer", "trade", "order", "checkout", "bank", "card", "transaction"],
      task_signals: ["authorize payment", "confirm transfer", "place order", "simulate trade", "audit trail", "refuse unsafe"],
      eval_categories: ["simulated_transaction_safety", "side_effect_and_approval_safety", "trace_and_state_observability"],
      evidence_requirements: ["simulation sandbox", "approval trace", "refusal tests for unsafe transaction requests"],
      simulation_only: true
    },
    {
      type_id: "general_tool_use_agent",
      label: "General Tool-Use Agent",
      capability_signals: ["tool", "api", "action", "assistant"],
      tool_signals: ["tool", "api", "connector", "integration", "function"],
      task_signals: ["use tool", "call api", "complete task", "take action"],
      eval_categories: ["tool_and_permission_safety", "trace_and_state_observability"],
      evidence_requirements: ["tool inventory", "sample task trace", "permission boundary description"]
    }
  ];

  const FALLBACK_CATEGORIES = [
    { category_id: "profile_completion", label: "Profile Completion", applicable_agent_types: ["unknown_agent"], required_evidence: ["tools", "sample tasks", "permission boundaries"], limitations: ["No performance score is available for sparse profiles."] },
    { category_id: "trace_and_state_observability", label: "Trace And State Observability", applicable_agent_types: ["coding_agent", "browser_navigation_agent", "contract_review_agent", "research_agent", "workflow_automation_agent", "financial_transaction_agent_simulated", "general_tool_use_agent"], required_evidence: ["trace summary", "artifacts", "verdict"], limitations: ["Trace availability does not by itself prove correctness."] }
  ];

  const FALLBACK_SOURCES = [
    {
      source_id: "openai_agent_evals_methodology",
      source_type: "curated_research_reference",
      title: "OpenAI agent evaluation methodology",
      url: "https://developers.openai.com/api/docs/guides/agent-evals",
      reliability: 0.2,
      applies_to: ["evaluation_methodology", "workflow_automation_agent", "research_agent"],
      limitations: ["Methodology reference only.", "No API call is made by this page."]
    },
    {
      source_id: "swe_bench_reference",
      source_type: "benchmark_reference",
      title: "SWE-bench",
      url: "https://www.swebench.com/SWE-bench/guides/evaluation/",
      reliability: 0.2,
      applies_to: ["coding_agent"],
      limitations: ["No score is assigned without a linked experiment summary."]
    },
    {
      source_id: "webarena_reference",
      source_type: "benchmark_reference",
      title: "WebArena",
      url: "https://github.com/web-arena-x/webarena",
      reliability: 0.2,
      applies_to: ["browser_navigation_agent"],
      limitations: ["No score is assigned without a linked experiment summary."]
    }
  ];

  const FALLBACK_SAMPLE_PROFILES = [
    {
      profile_id: "vague_unknown_agent",
      label: "Vague unknown agent",
      description: "A helpful assistant that can do many tasks.",
      declared_capabilities: "help users, answer questions",
      tools: "",
      tool_permissions: "",
      sample_tasks: "",
      policy_constraints: "",
      experiment_summary: "",
      can_read_files: false,
      can_write_files: false,
      can_run_code: false,
      can_use_browser: false,
      can_use_network: false,
      can_execute_transactions: false,
      can_modify_external_state: false,
      requires_human_approval: false,
      autonomy_level: "unknown"
    },
    {
      profile_id: "coding_file_reading_hybrid",
      label: "Coding / file-reading hybrid",
      description: "Reads repository files, edits local code, runs tests, and cites file evidence in patch reports.",
      declared_capabilities: "read files, edit code, run tests, summarize diffs, cite sources",
      tools: "file_reader, search_local, code_editor, shell, test_runner",
      tool_permissions: "read_workspace, write_workspace, run_tests, cite_file_paths",
      sample_tasks: "Fix failing tests with a minimal patch. Answer implementation questions from repository files with citations.",
      policy_constraints: "Stay inside the workspace. Do not run destructive commands. Report test output and changed files.",
      experiment_summary: "",
      can_read_files: true,
      can_write_files: true,
      can_run_code: true,
      can_use_browser: false,
      can_use_network: false,
      can_execute_transactions: false,
      can_modify_external_state: false,
      requires_human_approval: true,
      autonomy_level: "medium"
    },
    {
      profile_id: "browser_navigation_agent",
      label: "Browser-navigation agent",
      description: "Uses a browser to navigate websites, inspect page state, fill forms, and gather web information under approval controls.",
      declared_capabilities: "browser navigation, web page inspection, form filling, page-state verification",
      tools: "browser, navigate, click, dom_inspector, screenshot, form_filler",
      tool_permissions: "read_web_pages, fill_forms, submit_only_after_approval, capture_screenshots",
      sample_tasks: "Navigate to a site, gather information, fill a form, verify page state, and do not submit without approval.",
      policy_constraints: "No unapproved submit actions. Explicit approval is required before changing external state.",
      experiment_summary: "",
      can_read_files: false,
      can_write_files: false,
      can_run_code: false,
      can_use_browser: true,
      can_use_network: true,
      can_execute_transactions: false,
      can_modify_external_state: true,
      requires_human_approval: true,
      autonomy_level: "medium"
    },
    {
      profile_id: "simulated_financial_transaction_agent",
      label: "Simulated financial transaction agent",
      description: "Simulates payment, order, and transfer workflows with explicit confirmation and audit logging.",
      declared_capabilities: "simulate payment, authorize transaction, confirm transfer, produce audit trail, refuse unsafe requests",
      tools: "simulated_payment_gateway, simulated_order_tool, confirmation_prompt, audit_log",
      tool_permissions: "simulation_only, requires_approval, no_real_funds, audit_log_required",
      sample_tasks: "Authorize a simulated payment only after explicit confirmation. Refuse unapproved transfer requests. Produce an audit trail.",
      policy_constraints: "Simulation only. No real funds, cards, bank accounts, trades, or orders. Explicit approval required.",
      experiment_summary: "",
      can_read_files: false,
      can_write_files: false,
      can_run_code: false,
      can_use_browser: false,
      can_use_network: false,
      can_execute_transactions: true,
      can_modify_external_state: false,
      requires_human_approval: true,
      autonomy_level: "low"
    },
    {
      profile_id: "contract_review_agent",
      label: "Contract-review agent",
      description: "Reads contract documents, identifies clauses and obligations, separates facts from clauses, and reports evidence gaps with citations.",
      declared_capabilities: "review contract, identify obligations, extract clauses, cite sources, identify evidence gaps",
      tools: "document_reader, contract_parser, clause_extractor, citation",
      tool_permissions: "read_documents, cite_clauses, no_legal_advice_final_decision",
      sample_tasks: "Review a contract, identify obligations, cite supporting clauses, flag missing evidence, and distinguish facts from contract terms.",
      policy_constraints: "Do not make unsupported legal conclusions. Cite source clauses and mark missing facts.",
      experiment_summary: "",
      can_read_files: true,
      can_write_files: false,
      can_run_code: false,
      can_use_browser: false,
      can_use_network: false,
      can_execute_transactions: false,
      can_modify_external_state: false,
      requires_human_approval: true,
      autonomy_level: "low"
    }
  ];

  const I18N = {
    en: {
      htmlLang: "en",
      page: {
        kicker: "Static pre-runtime agent evaluation",
        title: "Agent Evaluation Demo",
        description: "Enter an agent profile to get a preliminary, evidence-aware report. The demo classifies broad agent types, recommends eval categories, and keeps benchmark references contextual.",
        staticNote: "No backend, external API calls, live model calls, or real financial actions."
      },
      language: {
        aria: "Language"
      },
      form: {
        title: "Agent Profile",
        description: "Describe the agent surface before runtime. Sparse inputs intentionally produce low-confidence results.",
        sampleProfile: "Sample profile",
        agentName: "Agent name",
        autonomyLevel: "Autonomy level",
        agentDescription: "Agent description",
        declaredCapabilities: "Declared capabilities",
        toolNames: "Tools / tool names",
        toolPermissions: "Tool permissions",
        permissionFlags: "Capability and safety flags",
        sampleTasks: "Sample tasks",
        policyConstraints: "Policy constraints",
        experimentSummary: "Optional pasted experiment summary",
        experimentPlaceholder: "Paste a short trace/result summary or JSON summary."
      },
      flags: {
        canReadFiles: "Can read files",
        canWriteFiles: "Can write files",
        canRunCode: "Can run code",
        canUseBrowser: "Can use browser",
        canUseNetwork: "Can use network",
        canExecuteTransactions: "Can execute transactions",
        canModifyExternalState: "Can modify external state",
        requiresHumanApproval: "Requires human approval"
      },
      options: {
        autonomy: {
          unknown: "Unknown",
          low: "Low",
          medium: "Medium",
          high: "High"
        }
      },
      actions: {
        loadSample: "Load sample",
        generateReport: "Generate report"
      },
      report: {
        title: "Preliminary Report",
        description: "Static classification and evidence-aware prediction, not a benchmark score."
      },
      exports: {
        json: "JSON Export",
        markdown: "Markdown Export"
      },
      sections: {
        classifiedTypes: "Classified agent type(s)",
        predictionSummary: "Confidence / prediction summary",
        inferredCapabilities: "Inferred capabilities",
        riskFlags: "Risk flags",
        evalCategories: "Applicable eval categories",
        scorecard: "Preliminary scorecard",
        evidenceBasis: "Evidence basis",
        matchedSignals: "Matched signals",
        missingEvidence: "Missing evidence",
        nextTests: "Recommended next evals",
        sourceReferences: "Data/source references used",
        limitations: "Limitations"
      },
      labels: {
        outcomePrediction: "Outcome prediction",
        predictedSuccess: "Predicted success",
        predictionConfidence: "Prediction confidence",
        score: "score",
        confidence: "confidence",
        reliability: "reliability",
        unsupported: "unsupported",
        none: "none",
        noItems: "No items.",
        sourceType: "source type"
      },
      markdown: {
        title: "Agent Evaluation Report",
        classifiedTypes: "Classified Agent Types",
        primary: "Primary",
        secondary: "Secondary",
        matchedSignals: "Matched Signals",
        evidenceBasis: "Evidence Basis",
        sourceReferences: "Data/Source References",
        outcomePrediction: "Outcome Prediction",
        predictedSuccess: "Predicted success",
        predictionConfidence: "Prediction confidence",
        missingEvidence: "Missing Evidence",
        nextEvals: "Recommended Next Evals",
        limitations: "Limitations"
      },
      sampleProfiles: {
        vague_unknown_agent: "Vague unknown agent",
        coding_file_reading_hybrid: "Coding / file-reading hybrid",
        browser_navigation_agent: "Browser-navigation agent",
        simulated_financial_transaction_agent: "Simulated financial transaction agent",
        contract_review_agent: "Contract-review agent"
      },
      agentTypes: {
        coding_agent: "Coding Agent",
        file_reading_agent: "File Reading Agent",
        browser_navigation_agent: "Browser Navigation Agent",
        contract_review_agent: "Contract Review Agent",
        research_agent: "Research Agent",
        workflow_automation_agent: "Workflow Automation Agent",
        financial_transaction_agent_simulated: "Financial Transaction Agent (Simulated)",
        general_tool_use_agent: "General Tool-Use Agent",
        unknown_agent: "Unknown Agent"
      },
      categories: {
        coding_change_safety: "Coding Change Safety",
        document_grounding: "Document Grounding",
        browser_task_flow: "Browser Task Flow",
        research_source_quality: "Research Source Quality",
        simulated_transaction_safety: "Simulated Transaction Safety",
        tool_and_permission_safety: "Tool And Permission Safety",
        trace_and_state_observability: "Trace And State Observability",
        profile_completion: "Profile Completion",
        complete_agent_profile: "Complete agent profile",
        run_simulated_authorization_and_refusal_tests: "Run simulated authorization and refusal tests",
        record_minimal_trace_or_experiment_summary: "Record minimal trace or experiment summary"
      },
      scoreDimensions: {
        capability_fit: "Capability fit",
        evidence_strength: "Evidence strength",
        tool_risk: "Tool risk",
        autonomy_risk: "Autonomy risk",
        task_clarity: "Task clarity",
        approval_safety: "Approval safety",
        data_access_risk: "Data access risk",
        missing_evidence_penalty: "Missing evidence penalty",
        expected_reliability: "Expected reliability"
      },
      sourceTypes: {
        user_declared: "user declared",
        inferred_from_tools: "inferred from tools",
        observed_experiment: "observed experiment",
        imported_trace: "imported trace",
        curated_research_reference: "curated research reference",
        benchmark_reference: "benchmark reference"
      },
      sourceTitles: {
        profile_declared_capabilities: "User-entered description and declared capabilities",
        profile_tool_task_inference: "Inferred from supplied tools, permissions, and sample tasks",
        pasted_experiment_summary: "Pasted experiment or trace summary",
        openai_agent_evals_methodology: "OpenAI agent evaluation methodology",
        swe_bench_reference: "SWE-bench",
        webarena_reference: "WebArena"
      },
      sourceFields: {
        "description/declared_capabilities": "description/declared capabilities",
        "tools/tool_permissions": "tools/tool permissions",
        sample_tasks: "sample tasks",
        profile_flags: "profile flags"
      },
      riskFlags: {
        explicit_approval_required: "explicit approval required",
        external_state_modification: "external state modification",
        financial_transaction_simulation_only: "financial transaction simulation only",
        filesystem_or_code_execution: "filesystem or code execution",
        high_autonomy: "high autonomy",
        high_risk_action_surface: "high-risk action surface",
        human_approval_required: "human approval required",
        network_or_browser_access: "network or browser access",
        transaction_like_action_surface: "transaction-like action surface"
      }
    },
    zh: {
      htmlLang: "zh-CN",
      page: {
        kicker: "静态预运行智能体评估",
        title: "智能体评估演示",
        description: "输入智能体画像，生成初步的、基于证据的报告。演示会分类广义智能体类型、推荐评估类别，并把基准引用保持为上下文证据。",
        staticNote: "无后端、无外部 API 调用、无实时模型调用，也不会执行真实金融操作。"
      },
      language: {
        aria: "语言"
      },
      form: {
        title: "智能体画像",
        description: "在运行前描述智能体的能力边界。信息稀疏时会有意给出低置信度结果。",
        sampleProfile: "示例画像",
        agentName: "智能体名称",
        autonomyLevel: "自主程度",
        agentDescription: "智能体描述",
        declaredCapabilities: "声明能力",
        toolNames: "工具 / 工具名称",
        toolPermissions: "工具权限",
        permissionFlags: "能力与安全标记",
        sampleTasks: "示例任务",
        policyConstraints: "策略约束",
        experimentSummary: "可选的实验摘要",
        experimentPlaceholder: "粘贴简短的轨迹/结果摘要或 JSON 摘要。"
      },
      flags: {
        canReadFiles: "可读取文件",
        canWriteFiles: "可写入文件",
        canRunCode: "可运行代码",
        canUseBrowser: "可使用浏览器",
        canUseNetwork: "可使用网络",
        canExecuteTransactions: "可执行交易类操作",
        canModifyExternalState: "可修改外部状态",
        requiresHumanApproval: "需要人工批准"
      },
      options: {
        autonomy: {
          unknown: "未知",
          low: "低",
          medium: "中",
          high: "高"
        }
      },
      actions: {
        loadSample: "加载示例",
        generateReport: "生成报告"
      },
      report: {
        title: "初步报告",
        description: "静态分类与证据感知预测；不是基准分数。"
      },
      exports: {
        json: "JSON 导出",
        markdown: "Markdown 导出"
      },
      sections: {
        classifiedTypes: "智能体类型分类",
        predictionSummary: "置信度 / 预测摘要",
        inferredCapabilities: "推断能力",
        riskFlags: "风险标记",
        evalCategories: "适用评估类别",
        scorecard: "初步评分卡",
        evidenceBasis: "证据依据",
        matchedSignals: "匹配信号",
        missingEvidence: "缺失证据",
        nextTests: "建议的下一步评估",
        sourceReferences: "使用的数据 / 来源引用",
        limitations: "限制"
      },
      labels: {
        outcomePrediction: "结果预测",
        predictedSuccess: "预测成功率",
        predictionConfidence: "预测置信度",
        score: "分数",
        confidence: "置信度",
        reliability: "可靠度",
        unsupported: "证据不足",
        none: "无",
        noItems: "无项目。",
        sourceType: "来源类型"
      },
      markdown: {
        title: "智能体评估报告",
        classifiedTypes: "智能体类型分类",
        primary: "主要类型",
        secondary: "次要类型",
        matchedSignals: "匹配信号",
        evidenceBasis: "证据依据",
        sourceReferences: "数据 / 来源引用",
        outcomePrediction: "结果预测",
        predictedSuccess: "预测成功率",
        predictionConfidence: "预测置信度",
        missingEvidence: "缺失证据",
        nextEvals: "建议的下一步评估",
        limitations: "限制"
      },
      sampleProfiles: {
        vague_unknown_agent: "信息稀疏的未知智能体",
        coding_file_reading_hybrid: "代码 / 文件读取混合智能体",
        browser_navigation_agent: "浏览器导航智能体",
        simulated_financial_transaction_agent: "模拟金融交易智能体",
        contract_review_agent: "合同审阅智能体"
      },
      agentTypes: {
        coding_agent: "代码智能体",
        file_reading_agent: "文件读取智能体",
        browser_navigation_agent: "浏览器导航智能体",
        contract_review_agent: "合同审阅智能体",
        research_agent: "研究智能体",
        workflow_automation_agent: "工作流自动化智能体",
        financial_transaction_agent_simulated: "金融交易智能体（仅模拟）",
        general_tool_use_agent: "通用工具使用智能体",
        unknown_agent: "未知智能体"
      },
      categories: {
        coding_change_safety: "代码变更安全",
        document_grounding: "文档依据性",
        browser_task_flow: "浏览器任务流程",
        research_source_quality: "研究来源质量",
        simulated_transaction_safety: "模拟交易安全",
        tool_and_permission_safety: "工具与权限安全",
        trace_and_state_observability: "轨迹与状态可观测性",
        profile_completion: "画像完整性",
        complete_agent_profile: "补全智能体画像",
        run_simulated_authorization_and_refusal_tests: "运行模拟授权与拒绝测试",
        record_minimal_trace_or_experiment_summary: "记录最小轨迹或实验摘要"
      },
      scoreDimensions: {
        capability_fit: "能力匹配度",
        evidence_strength: "证据强度",
        tool_risk: "工具风险",
        autonomy_risk: "自主性风险",
        task_clarity: "任务清晰度",
        approval_safety: "审批安全性",
        data_access_risk: "数据访问风险",
        missing_evidence_penalty: "缺失证据惩罚",
        expected_reliability: "预期可靠性"
      },
      sourceTypes: {
        user_declared: "用户声明",
        inferred_from_tools: "根据工具推断",
        observed_experiment: "观察到的实验",
        imported_trace: "导入轨迹",
        curated_research_reference: "精选研究引用",
        benchmark_reference: "基准引用"
      },
      sourceTitles: {
        profile_declared_capabilities: "用户输入的描述与声明能力",
        profile_tool_task_inference: "根据工具、权限和示例任务推断",
        pasted_experiment_summary: "粘贴的实验或轨迹摘要",
        openai_agent_evals_methodology: "OpenAI 智能体评估方法",
        swe_bench_reference: "SWE-bench",
        webarena_reference: "WebArena"
      },
      sourceFields: {
        "description/declared_capabilities": "描述/声明能力",
        "tools/tool_permissions": "工具/工具权限",
        sample_tasks: "示例任务",
        profile_flags: "画像标记"
      },
      riskFlags: {
        explicit_approval_required: "需要明确批准",
        external_state_modification: "外部状态修改",
        financial_transaction_simulation_only: "金融交易仅限模拟",
        filesystem_or_code_execution: "文件系统或代码执行",
        high_autonomy: "高自主性",
        high_risk_action_surface: "高风险操作面",
        human_approval_required: "需要人工批准",
        network_or_browser_access: "网络或浏览器访问",
        transaction_like_action_surface: "交易类操作面"
      },
      generated: {
        "Pasted summary is user-provided and not independently verified.": "粘贴的摘要由用户提供，尚未被独立验证。",
        "This static page performs preliminary classification only.": "此静态页面只执行初步分类。",
        "Benchmark references are contextual and are not direct scores.": "基准引用仅作为上下文证据，不是直接分数。",
        "Financial transaction workflows are simulation-only.": "金融交易工作流仅限模拟。",
        "Run real eval categories and import traces before relying on predictions.": "在依赖预测前，应运行真实评估类别并导入轨迹。",
        "Insufficient non-name evidence for a concrete primary type.": "缺少足够的非名称证据来确定具体主要类型。",
        "Classification uses declared, tool, task, permission, and policy signals; agent name is not scored.": "分类使用声明、工具、任务、权限和策略信号；智能体名称不会计分。",
        "Tool surface is missing.": "缺少工具表面信息。",
        "Representative sample tasks are missing.": "缺少代表性示例任务。",
        "Declared capability or description is missing.": "缺少声明能力或描述。",
        "Autonomy level is unknown.": "自主程度未知。",
        "Insufficient evidence for a non-unknown primary classification.": "缺少足够证据来给出非未知的主要分类。",
        "No observed experiment summary or imported trace is linked to this agent.": "没有与该智能体关联的观察实验摘要或导入轨迹。",
        "Benchmark references are contextual only; no comparable run is present.": "基准引用仅为上下文；当前没有可比运行结果。",
        "Fit between non-name signals and broad agent types.": "非名称信号与广义智能体类型的匹配度。",
        "Observed or imported evidence improves confidence; references do not score performance.": "观察或导入的证据会提高置信度；引用本身不为性能打分。",
        "Higher side-effect tools lower this safety-oriented score.": "副作用更强的工具会降低此安全导向分数。",
        "High autonomy increases risk unless constrained by approval and traces.": "如果没有审批和轨迹约束，高自主性会增加风险。",
        "Specific sample tasks improve eval-category selection.": "具体示例任务有助于选择评估类别。",
        "Human approval can reduce risk but does not prove competence.": "人工审批可以降低风险，但不能证明能力。",
        "Sensitive data access requires boundary tests.": "敏感数据访问需要边界测试。",
        "Missing evidence lowers prediction confidence.": "缺失证据会降低预测置信度。",
        "Preliminary reliability estimate from fit, evidence, clarity, and risk.": "根据匹配度、证据、清晰度和风险生成的初步可靠性估计。",
        "insufficient profile detail": "画像细节不足",
        "no observed experiment or trace evidence": "没有观察实验或轨迹证据",
        "unsupported claim: classification is unknown": "证据不足：分类仍为未知",
        "declared descriptions are not performance evidence": "声明性描述不是性能证据",
        "The agent may have capabilities that were not supplied.": "该智能体可能具有未提供的能力。",
        "Insufficient evidence to predict performance.": "证据不足，无法预测性能。",
        "profile signals fit broad agent categories": "画像信号匹配广义智能体类别",
        "sample tasks are specific enough to pick eval categories": "示例任务足够具体，可用于选择评估类别",
        "pasted experiment summary provides direct evidence": "粘贴的实验摘要提供了直接证据",
        "missing evidence may hide important failure modes": "缺失证据可能掩盖重要失败模式",
        "web or browser state may differ from declared tasks": "网页或浏览器状态可能与声明任务不同",
        "code or filesystem changes may regress without tests": "缺少测试时，代码或文件系统变更可能引入回归",
        "transaction workflow must remain simulated and approval-gated": "交易工作流必须保持模拟并经过审批",
        "low-confidence estimate": "低置信度估计",
        "evidence-backed preliminary estimate": "有证据支持的初步估计",
        "classification uses tool, permission, task, and policy signals rather than agent name": "分类使用工具、权限、任务和策略信号，而不是智能体名称",
        "benchmark and methodology references are contextual, not direct scores": "基准和方法论引用是上下文证据，不是直接分数",
        "pasted experiment summary increased confidence": "粘贴的实验摘要提高了置信度",
        "no linked observed/imported experiment evidence is available": "没有可用的关联观察/导入实验证据",
        "Target tasks resemble the sample tasks.": "目标任务与示例任务相似。",
        "No hidden tools are added at runtime.": "运行时不会加入隐藏工具。",
        "Low confidence preliminary success estimate; replace with observed eval results before deployment.": "低置信度的初步成功率估计；部署前应替换为观察到的评估结果。",
        "Moderate confidence preliminary success estimate; replace with observed eval results before deployment.": "中等置信度的初步成功率估计；部署前应替换为观察到的评估结果。",
        "Declared capability is weak evidence.": "声明能力是弱证据。",
        "Signal supports broad capability inference.": "该信号支持广义能力推断。",
        "User-entered description and declared capabilities": "用户输入的描述与声明能力",
        "Inferred from supplied tools, permissions, and sample tasks": "根据提供的工具、权限和示例任务推断",
        "Tool/task inference needs observed traces.": "工具/任务推断需要观察轨迹。",
        "Contextual reference only; not a direct score.": "仅为上下文引用；不是直接分数。"
      },
      generatedPatterns: {
        noExperimentForCategory: "缺少评估类别的实验摘要：{category}。"
      }
    }
  };

  const state = {
    categories: FALLBACK_CATEGORIES,
    sources: FALLBACK_SOURCES,
    sampleProfiles: FALLBACK_SAMPLE_PROFILES,
    language: "en"
  };

  document.addEventListener("DOMContentLoaded", () => {
    state.language = initialLanguage();
    setupLanguageSwitch();
    applyTranslations();
    populateSampleSelector(state.sampleProfiles);
    loadStaticData();
    const form = document.getElementById("agent-eval-form");
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      runEvaluation();
    });
    document.getElementById("load-sample-profile").addEventListener("click", loadSelectedSampleProfile);
    document.getElementById("sample-profile").addEventListener("change", loadSelectedSampleProfile);
    runEvaluation();
  });

  function initialLanguage() {
    return normalizeLanguage(languageFromUrl() || storedLanguage() || "en");
  }

  function languageFromUrl() {
    try {
      if (!window.location || !window.location.search || typeof URLSearchParams !== "function") {
        return "";
      }
      return new URLSearchParams(window.location.search).get("lang") || "";
    } catch (_error) {
      return "";
    }
  }

  function storedLanguage() {
    try {
      return window.localStorage ? window.localStorage.getItem("contract2agent.agentEval.lang") || "" : "";
    } catch (_error) {
      return "";
    }
  }

  function persistLanguage(language) {
    try {
      if (window.localStorage) {
        window.localStorage.setItem("contract2agent.agentEval.lang", language);
      }
    } catch (_error) {
      // localStorage can be unavailable in strict browser contexts.
    }
  }

  function normalizeLanguage(language) {
    const normalized = String(language || "").toLowerCase();
    return normalized === "zh" || normalized === "zh-cn" || normalized.startsWith("zh_") ? "zh" : "en";
  }

  function setupLanguageSwitch() {
    if (typeof document.querySelectorAll !== "function") {
      return;
    }
    document.querySelectorAll("[data-lang]").forEach((button) => {
      button.addEventListener("click", () => setLanguage(button.dataset.lang));
    });
  }

  function setLanguage(language) {
    state.language = normalizeLanguage(language);
    persistLanguage(state.language);
    applyTranslations();
    populateSampleSelector(state.sampleProfiles);
    const form = document.getElementById("agent-eval-form");
    if (form) {
      runEvaluation();
    }
  }

  function applyTranslations() {
    if (document.documentElement) {
      document.documentElement.lang = t("htmlLang", state.language);
    }
    if (typeof document.querySelectorAll !== "function") {
      return;
    }
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      element.textContent = t(element.dataset.i18n, element.textContent);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
      element.setAttribute("placeholder", t(element.dataset.i18nPlaceholder, element.getAttribute("placeholder") || ""));
    });
    document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
      element.setAttribute("aria-label", t(element.dataset.i18nAria, element.getAttribute("aria-label") || ""));
    });
    document.querySelectorAll("[data-lang]").forEach((button) => {
      const active = button.dataset.lang === state.language;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function t(path, fallback) {
    const activeValue = valueAt(I18N[state.language] || I18N.en, path);
    if (typeof activeValue === "string") {
      return activeValue;
    }
    const englishValue = valueAt(I18N.en, path);
    if (typeof englishValue === "string") {
      return englishValue;
    }
    return fallback || path;
  }

  function valueAt(source, path) {
    return String(path || "").split(".").reduce((current, key) => (
      current && Object.prototype.hasOwnProperty.call(current, key) ? current[key] : undefined
    ), source);
  }

  function translatedMapValue(mapName, key, fallback) {
    const activeMap = (I18N[state.language] && I18N[state.language][mapName]) || {};
    const englishMap = I18N.en[mapName] || {};
    return activeMap[key] || englishMap[key] || fallback || key;
  }

  function translateGenerated(value) {
    const text = String(value || "");
    const generated = (I18N[state.language] && I18N[state.language].generated) || {};
    if (generated[text]) {
      return generated[text];
    }
    if (state.language === "zh" && text.startsWith("No experiment summary for eval category: ")) {
      const category = text.replace("No experiment summary for eval category: ", "").replace(/\.$/, "");
      return I18N.zh.generatedPatterns.noExperimentForCategory.replace("{category}", category);
    }
    return text;
  }

  async function loadStaticData() {
    const [categoryData, sourceData, sampleData] = await Promise.all([
      loadJson("../data/agent_eval/eval_categories.json"),
      loadJson("../data/agent_eval/source_references.json"),
      loadJson("../data/agent_eval/sample_profiles.json")
    ]);
    if (categoryData && Array.isArray(categoryData.eval_categories)) {
      state.categories = categoryData.eval_categories;
    }
    if (sourceData && Array.isArray(sourceData.sources)) {
      state.sources = sourceData.sources;
    }
    if (sampleData && Array.isArray(sampleData.profiles) && sampleData.profiles.length) {
      state.sampleProfiles = sampleData.profiles;
      populateSampleSelector(state.sampleProfiles);
    }
    runEvaluation();
  }

  async function loadJson(path) {
    if (typeof fetch !== "function") {
      return null;
    }
    try {
      const response = await fetch(path);
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (_error) {
      return null;
    }
  }

  function runEvaluation() {
    const profile = collectProfile();
    const experiment = parseExperimentSummary(profile);
    const report = analyzeProfile(profile, experiment);
    renderReport(report);
  }

  function populateSampleSelector(profiles) {
    const select = document.getElementById("sample-profile");
    if (!select || !profiles.length) {
      return;
    }
    const currentValue = select.value || "coding_file_reading_hybrid";
    select.innerHTML = profiles.map((profile) => {
      const selected = profile.profile_id === currentValue ? " selected" : "";
      return `<option value="${escapeHtml(profile.profile_id)}"${selected}>${escapeHtml(sampleProfileLabel(profile))}</option>`;
    }).join("");
    if (!profiles.some((profile) => profile.profile_id === select.value)) {
      select.value = profiles[0].profile_id;
    }
  }

  function loadSelectedSampleProfile() {
    const selectedId = valueOf("sample-profile");
    const profile = state.sampleProfiles.find((item) => item.profile_id === selectedId) || state.sampleProfiles[0];
    if (!profile) {
      return;
    }
    applySampleProfile(profile);
    runEvaluation();
  }

  function applySampleProfile(profile) {
    setValue("agent-name", profile.name || profile.label || "Sample agent");
    setValue("agent-description", textField(profile.description));
    setValue("declared-capabilities", textField(profile.declared_capabilities));
    setValue("tool-names", textField(profile.tools));
    setValue("tool-permissions", textField(profile.tool_permissions));
    setValue("sample-tasks", textField(profile.sample_tasks));
    setValue("policy-constraints", textField(profile.policy_constraints));
    setValue("experiment-summary", textField(profile.experiment_summary));
    setValue("autonomy-level", profile.autonomy_level || "unknown");
    setChecked("can-read-files", profile.can_read_files);
    setChecked("can-write-files", profile.can_write_files);
    setChecked("can-run-code", profile.can_run_code);
    setChecked("can-use-browser", profile.can_use_browser);
    setChecked("can-use-network", profile.can_use_network);
    setChecked("can-execute-transactions", profile.can_execute_transactions);
    setChecked("can-modify-external-state", profile.can_modify_external_state);
    setChecked("requires-human-approval", profile.requires_human_approval);
  }

  function collectProfile() {
    const tools = listFromText(valueOf("tool-names"));
    return {
      agent_id: "demo-agent",
      name: valueOf("agent-name").trim() || "Unnamed agent",
      description: valueOf("agent-description"),
      declared_capabilities: listFromText(valueOf("declared-capabilities")),
      tools,
      tool_permissions: listFromText(valueOf("tool-permissions")),
      can_read_files: checked("can-read-files"),
      can_write_files: checked("can-write-files"),
      can_run_code: checked("can-run-code"),
      can_use_browser: checked("can-use-browser"),
      can_use_network: checked("can-use-network"),
      can_execute_transactions: checked("can-execute-transactions"),
      can_modify_external_state: checked("can-modify-external-state"),
      requires_human_approval: checked("requires-human-approval"),
      autonomy_level: valueOf("autonomy-level"),
      sample_tasks: splitSentences(valueOf("sample-tasks")),
      policy_constraints: splitSentences(valueOf("policy-constraints"))
    };
  }

  function parseExperimentSummary(profile) {
    const raw = valueOf("experiment-summary").trim();
    if (!raw) {
      return null;
    }
    try {
      const parsed = JSON.parse(raw);
      return {
        result_id: parsed.result_id || parsed.run_id || "pasted-experiment",
        agent_id: profile.agent_id,
        agent_type: parsed.agent_type || "",
        eval_category: parsed.eval_category || parsed.eval_pack_id || "trace_and_state_observability",
        verdict: parsed.verdict || "user_pasted",
        evidence_source: parsed.evidence_source || "observed_experiment",
        trace_available: Boolean(parsed.trace_available || parsed.trace_summary),
        limitations: ["Pasted summary is user-provided and not independently verified."]
      };
    } catch (_error) {
      return {
        result_id: "pasted-summary",
        agent_id: profile.agent_id,
        agent_type: "",
        eval_category: "trace_and_state_observability",
        verdict: "user_pasted_summary",
        evidence_source: raw.toLowerCase().includes("trace") ? "imported_trace" : "observed_experiment",
        trace_available: /trace|log|tool|test|verdict/i.test(raw),
        limitations: ["Pasted summary is user-provided and not independently verified."],
        notes: raw.slice(0, 240)
      };
    }
  }

  function analyzeProfile(profile, experiment) {
    const classification = classifyProfile(profile);
    const categories = selectCategories(classification);
    const sources = resolveSources(classification, experiment);
    const missing = missingEvidence(profile, classification, categories, experiment, sources);
    const scores = scoreProfile(profile, classification, experiment, missing, sources);
    const prediction = predictOutcome(classification, scores, missing, experiment);
    return {
      agent_profile: profile,
      classification,
      inferred_capabilities: inferredCapabilities(classification),
      applicable_eval_categories: categories,
      preliminary_scores: scores,
      outcome_prediction: prediction,
      evidence_summary: sources,
      missing_evidence: missing,
      limitations: [
        "This static page performs preliminary classification only.",
        "Benchmark references are contextual and are not direct scores.",
        "Financial transaction workflows are simulation-only.",
        "Run real eval categories and import traces before relying on predictions."
      ]
    };
  }

  function classifyProfile(profile) {
    const declaredText = normalize([profile.description].concat(profile.declared_capabilities, profile.policy_constraints));
    const toolText = normalize(profile.tools.concat(profile.tool_permissions));
    const taskText = normalize(profile.sample_tasks);
    const scores = TYPE_DEFS.map((def) => {
      const signals = [];
      let confidence = 0;
      matchSignals(def.capability_signals, declaredText).forEach((value) => {
        confidence += 0.08;
        signals.push(signal(def.type_id, "declared", "description/declared_capabilities", value, "low", 0.08));
      });
      matchSignals(def.tool_signals, toolText).forEach((value) => {
        confidence += 0.17;
        signals.push(signal(def.type_id, "tool", "tools/tool_permissions", value, "medium", 0.17));
      });
      matchSignals(def.task_signals, taskText).forEach((value) => {
        confidence += 0.14;
        signals.push(signal(def.type_id, "task", "sample_tasks", value, "medium", 0.14));
      });
      profileFlagSignals(profile, def.type_id).forEach((item) => {
        confidence += item.confidence;
        signals.push(signal(def.type_id, "profile_flag", "profile_flags", item.value, "medium", item.confidence));
      });
      return {
        type_id: def.type_id,
        label: def.label,
        confidence: Math.min(0.96, confidence),
        signals
      };
    }).sort((a, b) => b.confidence - a.confidence || a.type_id.localeCompare(b.type_id));

    let primary = scores.filter((score) => score.confidence >= 0.42).map((score) => score.type_id);
    let secondary = scores.filter((score) => score.confidence >= 0.28 && score.confidence < 0.42).map((score) => score.type_id);
    if (!primary.length) {
      primary = ["unknown_agent"];
      secondary = scores.filter((score) => score.confidence >= 0.1).map((score) => score.type_id).slice(0, 3);
    }
    const confidenceByType = {};
    scores.forEach((score) => {
      if (score.confidence >= 0.1) {
        confidenceByType[score.type_id] = round(score.confidence);
      }
    });
    if (primary.includes("unknown_agent")) {
      confidenceByType.unknown_agent = Object.keys(confidenceByType).length ? 0.58 : 0.82;
    }
    const matchedSignals = {};
    scores.forEach((score) => {
      if (score.signals.length) {
        matchedSignals[score.type_id] = score.signals;
      }
    });
    const riskFlags = riskFlagsFor(profile, primary.concat(secondary));
    return {
      primary_types: primary,
      secondary_types: secondary,
      rejected_types: [],
      confidence_by_type: confidenceByType,
      matched_signals: matchedSignals,
      negative_signals: {},
      risk_flags: riskFlags,
      missing_evidence: [],
      explanation: primary.includes("unknown_agent")
        ? "Insufficient non-name evidence for a concrete primary type."
        : "Classification uses declared, tool, task, permission, and policy signals; agent name is not scored."
    };
  }

  function profileFlagSignals(profile, typeId) {
    const flags = [];
    if (typeId === "coding_agent") {
      if (profile.can_write_files) flags.push({ value: "can_write_files", confidence: 0.1 });
      if (profile.can_run_code) flags.push({ value: "can_run_code", confidence: 0.12 });
      if (profile.can_read_files) flags.push({ value: "can_read_files", confidence: 0.05 });
    }
    if (typeId === "file_reading_agent" && profile.can_read_files) {
      flags.push({ value: "can_read_files", confidence: 0.17 });
    }
    if (typeId === "browser_navigation_agent") {
      if (profile.can_use_browser) flags.push({ value: "can_use_browser", confidence: 0.18 });
      if (profile.can_use_network) flags.push({ value: "can_use_network", confidence: 0.05 });
    }
    if (typeId === "financial_transaction_agent_simulated") {
      if (profile.can_execute_transactions) flags.push({ value: "can_execute_transactions", confidence: 0.22 });
      if (profile.requires_human_approval) flags.push({ value: "requires_human_approval", confidence: 0.05 });
    }
    if (typeId === "general_tool_use_agent" && profile.tools.length) {
      flags.push({ value: "tools_present", confidence: 0.22 });
    }
    if (typeId === "research_agent" && profile.can_use_network) {
      flags.push({ value: "can_use_network", confidence: 0.07 });
    }
    return flags;
  }

  function selectCategories(classification) {
    const types = classification.primary_types.concat(classification.secondary_types);
    if (classification.primary_types.includes("unknown_agent")) {
      types.push("unknown_agent");
    }
    const selected = state.categories.filter((category) => {
      const applicable = category.applicable_agent_types || [];
      return applicable.some((typeId) => types.includes(typeId));
    });
    return selected.length ? selected : state.categories.filter((category) => category.category_id === "profile_completion");
  }

  function resolveSources(classification, experiment) {
    const types = classification.primary_types.concat(classification.secondary_types);
    const sources = [
      {
        source_id: "profile_declared_capabilities",
        source_type: "user_declared",
        title: "User-entered description and declared capabilities",
        reliability: 0.25,
        limitations: ["Declared capability is weak evidence."]
      },
      {
        source_id: "profile_tool_task_inference",
        source_type: "inferred_from_tools",
        title: "Inferred from supplied tools, permissions, and sample tasks",
        reliability: 0.55,
        limitations: ["Tool/task inference needs observed traces."]
      }
    ];
    if (experiment) {
      sources.push({
        source_id: "pasted_experiment_summary",
        source_type: experiment.evidence_source,
        title: "Pasted experiment or trace summary",
        reliability: experiment.evidence_source === "imported_trace" ? 0.8 : 0.95,
        limitations: experiment.limitations || []
      });
    }
    state.sources.forEach((source) => {
      const applies = source.applies_to || [];
      if (applies.includes("evaluation_methodology") || applies.some((typeId) => types.includes(typeId))) {
        sources.push(Object.assign({}, source, {
          reliability: Math.min(Number(source.reliability || 0.2), 0.2),
          limitations: (source.limitations || []).concat(["Contextual reference only; not a direct score."])
        }));
      }
    });
    return sources;
  }

  function missingEvidence(profile, classification, categories, experiment, sources) {
    const missing = [];
    if (!profile.tools.length) missing.push("Tool surface is missing.");
    if (!profile.sample_tasks.length) missing.push("Representative sample tasks are missing.");
    if (!profile.declared_capabilities.length && !profile.description.trim()) missing.push("Declared capability or description is missing.");
    if (profile.autonomy_level === "unknown") missing.push("Autonomy level is unknown.");
    if (classification.primary_types.includes("unknown_agent")) missing.push("Insufficient evidence for a non-unknown primary classification.");
    if (!experiment) missing.push("No observed experiment summary or imported trace is linked to this agent.");
    categories.forEach((category) => {
      if (!experiment || experiment.eval_category !== category.category_id) {
        missing.push(`No experiment summary for eval category: ${category.category_id}.`);
      }
    });
    if (sources.some((source) => source.source_type === "benchmark_reference") && !experiment) {
      missing.push("Benchmark references are contextual only; no comparable run is present.");
    }
    return Array.from(new Set(missing)).sort();
  }

  function scoreProfile(profile, classification, experiment, missing, sources) {
    const typedConfidences = Object.entries(classification.confidence_by_type)
      .filter(([typeId]) => typeId !== "unknown_agent")
      .map(([, value]) => Number(value));
    const evidenceStrength = experiment ? (experiment.evidence_source === "imported_trace" ? 0.8 : 0.9) : Math.min(0.6, average(sources.filter((source) => !/reference/.test(source.source_type)).map((source) => Number(source.reliability || 0))));
    const riskCount = classification.risk_flags.filter((flag) => /risk|external|network|filesystem|transaction|private/.test(flag)).length;
    const approvalRisky = classification.risk_flags.includes("high_risk_action_surface");
    const approvalScore = approvalRisky ? (profile.requires_human_approval ? 0.62 : 0.25) : 0.76;
    const scores = [
      score("capability_fit", typedConfidences.length ? Math.max.apply(null, typedConfidences) : 0.08, 0.35, "Fit between non-name signals and broad agent types."),
      score("evidence_strength", evidenceStrength, experiment ? 0.8 : 0.3, "Observed or imported evidence improves confidence; references do not score performance."),
      score("tool_risk", Math.max(0, 1 - riskCount * 0.14), 0.55, "Higher side-effect tools lower this safety-oriented score."),
      score("autonomy_risk", profile.autonomy_level === "high" ? 0.55 : 0.78, 0.45, "High autonomy increases risk unless constrained by approval and traces."),
      score("task_clarity", profile.sample_tasks.length ? 0.75 : 0.25, profile.sample_tasks.length ? 0.55 : 0.25, "Specific sample tasks improve eval-category selection."),
      score("approval_safety", approvalScore, 0.5, "Human approval can reduce risk but does not prove competence."),
      score("data_access_risk", classification.risk_flags.includes("private_or_sensitive_data_access") ? 0.42 : 0.75, 0.45, "Sensitive data access requires boundary tests."),
      score("missing_evidence_penalty", Math.max(0, 1 - Math.min(0.75, missing.length * 0.06)), 0.65, "Missing evidence lowers prediction confidence.")
    ];
    const byDimension = Object.fromEntries(scores.map((item) => [item.dimension, item.score]));
    const expected = byDimension.capability_fit * 0.32 + byDimension.evidence_strength * 0.3 + byDimension.task_clarity * 0.14 + byDimension.approval_safety * 0.1 + byDimension.tool_risk * 0.08 + byDimension.missing_evidence_penalty * 0.06;
    scores.push(score("expected_reliability", expected, experiment ? 0.55 : 0.28, "Preliminary reliability estimate from fit, evidence, clarity, and risk."));
    return scores;
  }

  function predictOutcome(classification, scores, missing, experiment) {
    const byDimension = Object.fromEntries(scores.map((item) => [item.dimension, item.score]));
    const riskFlags = classification.risk_flags;
    if (classification.primary_types.includes("unknown_agent") && byDimension.expected_reliability < 0.35) {
      return {
        predicted_success: null,
        confidence: 0.05,
        likely_strengths: [],
        likely_failures: ["insufficient profile detail", "no observed experiment or trace evidence"],
        risk_flags: riskFlags,
        evidence_basis: ["unsupported claim: classification is unknown", "declared descriptions are not performance evidence"],
        assumptions: ["The agent may have capabilities that were not supplied."],
        missing_evidence: missing,
        recommended_next_tests: recommendedTests(classification, missing),
        explanation: "Insufficient evidence to predict performance."
      };
    }
    let penalty = 0;
    if (riskFlags.includes("high_risk_action_surface")) penalty += 0.08;
    if (riskFlags.includes("external_state_modification")) penalty += 0.05;
    if (riskFlags.includes("financial_transaction_simulation_only")) penalty += 0.08;
    const predicted = Math.max(0, Math.min(1, byDimension.expected_reliability - penalty));
    const confidence = Math.max(0.05, Math.min(0.85, average(scores.map((item) => item.confidence)) * 0.45 + byDimension.evidence_strength * 0.35 + (experiment ? 0.2 : 0)));
    return {
      predicted_success: round(predicted),
      confidence: round(confidence),
      likely_strengths: strengthsFor(byDimension, experiment),
      likely_failures: failuresFor(classification, missing),
      risk_flags: riskFlags,
      evidence_basis: [
        confidence < 0.55 ? "low-confidence estimate" : "evidence-backed preliminary estimate",
        "classification uses tool, permission, task, and policy signals rather than agent name",
        "benchmark and methodology references are contextual, not direct scores",
        experiment ? "pasted experiment summary increased confidence" : "no linked observed/imported experiment evidence is available"
      ],
      assumptions: ["Target tasks resemble the sample tasks.", "No hidden tools are added at runtime."],
      missing_evidence: missing,
      recommended_next_tests: recommendedTests(classification, missing),
      explanation: `${confidence < 0.35 ? "Low" : "Moderate"} confidence preliminary success estimate; replace with observed eval results before deployment.`
    };
  }

  function riskFlagsFor(profile, typeIds) {
    const flags = [];
    if (profile.can_write_files || profile.can_run_code) flags.push("filesystem_or_code_execution");
    if (profile.can_use_browser || profile.can_use_network) flags.push("network_or_browser_access");
    if (profile.can_modify_external_state) flags.push("external_state_modification");
    if (profile.can_execute_transactions) flags.push("transaction_like_action_surface", "high_risk_action_surface");
    if (profile.requires_human_approval) flags.push("human_approval_required");
    if (profile.autonomy_level === "high") flags.push("high_autonomy");
    if (typeIds.includes("financial_transaction_agent_simulated")) flags.push("financial_transaction_simulation_only", "explicit_approval_required", "high_risk_action_surface");
    return Array.from(new Set(flags)).sort();
  }

  function inferredCapabilities(classification) {
    const capabilities = [];
    Object.values(classification.matched_signals).forEach((signals) => {
      signals.forEach((item) => capabilities.push(item.matched_value));
    });
    return Array.from(new Set(capabilities)).sort();
  }

  function recommendedTests(classification) {
    const tests = [];
    const types = classification.primary_types.concat(classification.secondary_types);
    state.categories.forEach((category) => {
      if ((category.applicable_agent_types || []).some((typeId) => types.includes(typeId))) {
        tests.push(category.category_id);
      }
    });
    if (classification.primary_types.includes("unknown_agent")) tests.push("complete_agent_profile");
    if (classification.risk_flags.includes("financial_transaction_simulation_only")) tests.push("run_simulated_authorization_and_refusal_tests");
    tests.push("record_minimal_trace_or_experiment_summary");
    return Array.from(new Set(tests)).sort();
  }

  function strengthsFor(scores, experiment) {
    const strengths = [];
    if (scores.capability_fit >= 0.55) strengths.push("profile signals fit broad agent categories");
    if (scores.task_clarity >= 0.7) strengths.push("sample tasks are specific enough to pick eval categories");
    if (experiment) strengths.push("pasted experiment summary provides direct evidence");
    return strengths;
  }

  function failuresFor(classification, missing) {
    const failures = [];
    if (missing.length) failures.push("missing evidence may hide important failure modes");
    if (classification.risk_flags.includes("network_or_browser_access")) failures.push("web or browser state may differ from declared tasks");
    if (classification.risk_flags.includes("filesystem_or_code_execution")) failures.push("code or filesystem changes may regress without tests");
    if (classification.risk_flags.includes("financial_transaction_simulation_only")) failures.push("transaction workflow must remain simulated and approval-gated");
    return Array.from(new Set(failures)).sort();
  }

  function renderReport(report) {
    const output = document.getElementById("agent-eval-output");
    output.innerHTML = [
      section(t("sections.classifiedTypes"), chips(report.classification.primary_types.concat(report.classification.secondary_types), "", typeLabel)),
      section(t("sections.predictionSummary"), predictionHtml(report.outcome_prediction)),
      section(t("sections.inferredCapabilities"), list(report.inferred_capabilities)),
      section(t("sections.riskFlags"), chips(report.classification.risk_flags, "risk", riskFlagLabel)),
      section(t("sections.evalCategories"), list(report.applicable_eval_categories.map(categorySummary))),
      section(t("sections.scorecard"), scoreHtml(report.preliminary_scores)),
      section(t("sections.evidenceBasis"), list(report.outcome_prediction.evidence_basis, translateGenerated)),
      section(t("sections.matchedSignals"), matchedSignals(report.classification.matched_signals)),
      section(t("sections.missingEvidence"), list(report.missing_evidence, translateGenerated)),
      section(t("sections.nextTests"), list(report.outcome_prediction.recommended_next_tests, categoryOrTestLabel)),
      section(t("sections.sourceReferences"), sourceListHtml(report.evidence_summary)),
      section(t("sections.limitations"), list(report.limitations, translateGenerated))
    ].join("");
    document.getElementById("json-export").value = JSON.stringify(report, null, 2);
    document.getElementById("markdown-export").value = markdownReport(report);
  }

  function markdownReport(report) {
    const prediction = report.outcome_prediction.predicted_success === null ? t("labels.unsupported") : formatScore(report.outcome_prediction.predicted_success);
    const matchedSignalLines = markdownMatchedSignals(report.classification.matched_signals);
    return [
      `# ${t("markdown.title")}`,
      "",
      `## ${t("markdown.classifiedTypes")}`,
      `- ${t("markdown.primary")}: ${report.classification.primary_types.map(typeLabel).join(", ")}`,
      `- ${t("markdown.secondary")}: ${report.classification.secondary_types.map(typeLabel).join(", ") || t("labels.none")}`,
      "",
      `## ${t("markdown.matchedSignals")}`,
      ...matchedSignalLines,
      "",
      `## ${t("markdown.evidenceBasis")}`,
      ...report.outcome_prediction.evidence_basis.map((item) => `- ${translateGenerated(item)}`),
      "",
      `## ${t("markdown.sourceReferences")}`,
      ...report.evidence_summary.map((source) => `- ${sourceSummary(source)}`),
      "",
      `## ${t("markdown.outcomePrediction")}`,
      `- ${t("markdown.predictedSuccess")}: ${prediction}`,
      `- ${t("markdown.predictionConfidence")}: ${formatScore(report.outcome_prediction.confidence)}`,
      "",
      `## ${t("markdown.missingEvidence")}`,
      ...report.missing_evidence.map((item) => `- ${translateGenerated(item)}`),
      "",
      `## ${t("markdown.nextEvals")}`,
      ...report.outcome_prediction.recommended_next_tests.map((item) => `- ${categoryOrTestLabel(item)}`),
      "",
      `## ${t("markdown.limitations")}`,
      ...report.limitations.map((item) => `- ${translateGenerated(item)}`)
    ].join("\n");
  }

  function markdownMatchedSignals(signalsByType) {
    const lines = [];
    Object.entries(signalsByType || {}).forEach(([typeId, signals]) => {
      signals.forEach((signalItem) => {
        lines.push(`- ${typeLabel(typeId)}: ${sourceFieldLabel(signalItem.source_field)} -> ${signalItem.matched_value} (${t("labels.confidence")} ${formatScore(signalItem.confidence)})`);
      });
    });
    return lines.length ? lines : [`- ${t("labels.none")}`];
  }

  function section(title, body) {
    return `<div class="ae-section"><h3>${escapeHtml(title)}</h3>${body}</div>`;
  }

  function list(items, translator) {
    if (!items || !items.length) return `<p class="ae-empty">${escapeHtml(t("labels.noItems"))}</p>`;
    return `<ul class="ae-list">${items.map((item) => `<li>${escapeHtml(translator ? translator(item) : String(item))}</li>`).join("")}</ul>`;
  }

  function chips(items, extraClass, translator) {
    if (!items || !items.length) return `<p class="ae-empty">${escapeHtml(t("labels.noItems"))}</p>`;
    return `<div class="ae-chip-row">${items.map((item) => `<span class="ae-chip ${extraClass || ""}">${escapeHtml(translator ? translator(item) : String(item))}</span>`).join("")}</div>`;
  }

  function matchedSignals(signalsByType) {
    const rows = [];
    Object.entries(signalsByType || {}).forEach(([typeId, signals]) => {
      rows.push(`${typeLabel(typeId)}: ${signals.map((signalItem) => `${sourceFieldLabel(signalItem.source_field)}:${signalItem.matched_value}`).join(", ")}`);
    });
    return list(rows);
  }

  function scoreHtml(scores) {
    return `<div class="ae-scorecard">${scores.map((item) => `
      <div class="ae-score">
        <div>
          <strong>${escapeHtml(scoreDimensionLabel(item.dimension))}</strong>
          <small>${escapeHtml(translateGenerated(item.explanation))}</small>
        </div>
        <div class="ae-score-meter">
          <div class="ae-bar"><span style="width:${Math.round(item.score * 100)}%"></span></div>
          <span class="ae-score-value">${escapeHtml(formatScore(item.score))}</span>
        </div>
      </div>
    `).join("")}</div>`;
  }

  function predictionHtml(prediction) {
    const success = prediction.predicted_success === null ? t("labels.unsupported") : formatScore(prediction.predicted_success);
    return `
      <div class="ae-summary">
        <div class="ae-summary-item">
          <span class="ae-summary-label">${escapeHtml(t("labels.predictedSuccess"))}</span>
          <span class="ae-summary-value">${escapeHtml(success)}</span>
        </div>
        <div class="ae-summary-item">
          <span class="ae-summary-label">${escapeHtml(t("labels.predictionConfidence"))}</span>
          <span class="ae-summary-value">${escapeHtml(formatScore(prediction.confidence))}</span>
        </div>
      </div>
      <p>${escapeHtml(translateGenerated(prediction.explanation))}</p>
    `;
  }

  function sourceListHtml(sources) {
    if (!sources || !sources.length) {
      return `<p class="ae-empty">${escapeHtml(t("labels.noItems"))}</p>`;
    }
    return `<div class="ae-reference-list">${sources.map((source) => {
      const url = source.url ? `<span>${escapeHtml(source.url)}</span>` : "";
      return `
        <div class="ae-reference">
          <strong>${escapeHtml(sourceTitle(source))}</strong>
          <span>${escapeHtml(source.source_id)} · ${escapeHtml(sourceTypeLabel(source.source_type))} · ${escapeHtml(t("labels.reliability"))} ${Number(source.reliability || 0).toFixed(2)}</span>
          ${url}
        </div>
      `;
    }).join("")}</div>`;
  }

  function sourceSummary(source) {
    const url = source.url ? ` (${source.url})` : "";
    return `${source.source_id} [${sourceTypeLabel(source.source_type)}, ${t("labels.reliability")}=${Number(source.reliability || 0).toFixed(2)}]: ${sourceTitle(source)}${url}`;
  }

  function categorySummary(category) {
    return `${category.category_id}: ${categoryLabel(category.category_id, category.label)}`;
  }

  function sampleProfileLabel(profile) {
    return translatedMapValue("sampleProfiles", profile.profile_id, profile.label || profile.profile_id);
  }

  function typeLabel(typeId) {
    return translatedMapValue("agentTypes", typeId, typeId);
  }

  function categoryLabel(categoryId, fallback) {
    return translatedMapValue("categories", categoryId, fallback || categoryId);
  }

  function categoryOrTestLabel(testId) {
    return categoryLabel(testId, testId);
  }

  function riskFlagLabel(flag) {
    return translatedMapValue("riskFlags", flag, flag);
  }

  function sourceTitle(source) {
    return translatedMapValue("sourceTitles", source.source_id, translateGenerated(source.title || source.source_id));
  }

  function sourceTypeLabel(sourceType) {
    return translatedMapValue("sourceTypes", sourceType, sourceType);
  }

  function scoreDimensionLabel(dimension) {
    return translatedMapValue("scoreDimensions", dimension, dimension);
  }

  function sourceFieldLabel(sourceField) {
    return translatedMapValue("sourceFields", sourceField, sourceField);
  }

  function formatScore(value) {
    return Number(value || 0).toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  }

  function signal(typeId, kind, sourceField, value, strength, confidence) {
    return {
      signal_id: `${typeId}:${kind}:${value.replace(/[^a-z0-9]+/gi, "_").toLowerCase()}`,
      label: value,
      source_field: sourceField,
      matched_value: value,
      capability: value,
      strength,
      confidence,
      explanation: kind === "declared" ? "Declared capability is weak evidence." : "Signal supports broad capability inference."
    };
  }

  function score(dimension, value, confidence, explanation) {
    return { dimension, score: round(value), confidence: round(confidence), evidence_sources: [], missing_evidence: [], explanation };
  }

  function matchSignals(signals, text) {
    return signals.filter((signalText) => new RegExp(`(^|[^a-z0-9])${escapeRegExp(signalText).replace(/\\ /g, "\\s+")}([^a-z0-9]|$)`, "i").test(text));
  }

  function splitSentences(text) {
    return text.split(/[\n.]+/).map((item) => item.trim()).filter(Boolean);
  }

  function listFromText(text) {
    return text.split(/[,\n]+/).map((item) => item.trim()).filter(Boolean);
  }

  function normalize(values) {
    return values.filter(Boolean).join(" ").toLowerCase();
  }

  function average(values) {
    if (!values.length) return 0;
    return values.reduce((sum, value) => sum + Number(value || 0), 0) / values.length;
  }

  function round(value) {
    return Math.round(Math.max(0, Math.min(1, Number(value || 0))) * 1000) / 1000;
  }

  function checked(id) {
    return document.getElementById(id).checked;
  }

  function valueOf(id) {
    return document.getElementById(id).value || "";
  }

  function setValue(id, value) {
    document.getElementById(id).value = value;
  }

  function setChecked(id, value) {
    document.getElementById(id).checked = Boolean(value);
  }

  function textField(value) {
    if (Array.isArray(value)) {
      return value.join(", ");
    }
    return value || "";
  }

  function escapeHtml(value) {
    return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[char]));
  }

  function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  window.Contract2AgentEvalDemo = {
    analyzeProfile,
    classifyProfile,
    scoreProfile,
    predictOutcome,
    setLanguage,
    getLanguage: () => state.language,
    translations: I18N
  };
})();
