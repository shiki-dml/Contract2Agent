# 报告示例与评分说明

本页说明如何阅读文件阅读报告，以及如何把分数维度连接到具体 agent 改进。

已提交样例：

- `examples/file_reading_eval/expected_reports/deterministic_report.example.md`
- `examples/file_reading_eval/expected_reports/deterministic_report.example.json`
- `examples/file_reading_eval/expected_reports/corpus_manifest.example.json`
- `examples/file_reading_eval/expected_reports/reference_result.example.json`

这些都是 sample/synthetic 产物。它们不是生成的 `.runs/` 目录，也不是 benchmark 声明。

## 报告形状

Markdown 报告应包含：

- 运行摘要和观测任务数。
- Agent/profile 摘要。
- Corpus 摘要和来源标签。
- Task 摘要。
- Overall result 和 confidence。
- 分维度分数。
- Citation accuracy。
- Evidence span validity。
- Quote match status。
- Answer correctness。
- Grounding / hallucination 检查。
- Forbidden-file 或边界检查。
- Missing evidence 和拒答行为。
- Failure modes。
- Recommended fixes。
- Data source / reference source 标签。
- Redaction note。
- Limitations。

JSON 报告应以脚本友好格式承载同样概念。

## 评分维度

| Dimension | 衡量内容 | 高分含义 | 低分含义 | 改进方式 | 报告字段 |
| --- | --- | --- | --- | --- | --- |
| `answer_correctness` | 是否匹配 gold answer、别名或正确拒答。 | 观测任务答案正确。 | 答案错误或不受支持。 | 从证据中收敛检索和答案合成。 | `scorecard.scores_by_dimension.answer_correctness` |
| `evidence_grounding` | 事实声明是否由预期证据支持。 | 声明由语料文本支持。 | 声明无依据或被编造。 | 最终答案前做 claim-level citation 检查。 | `unsupported_claim_control` 与 failure modes |
| `citation_validity` | citation 是否存在且结构正确。 | citation 包含已知 `file_id`、行号和 quote。 | citation 缺失或格式错误。 | 强制结构化输出 schema。 | `citation_quality` |
| `citation_precision` | 是否避免无关或错误证据。 | 引用文件和行号聚焦。 | 引用 distractor 或无关行。 | 最终引用前过滤证据。 | `supporting_file_precision` |
| `citation_recall` | 是否覆盖必需证据。 | 必需 span 或支持文件被引用。 | 关键证据缺失。 | 增强检索召回和最终证据检查。 | `supporting_file_recall`, `citation_span_accuracy` |
| `quote_match` | quote 是否与行范围精确匹配。 | quote 出现在引用行范围内。 | quote 与源文本不一致。 | 精确复制源 quote，或仅在允许时省略。 | `citation_quote_match` |
| `line_range_validity` | 行号范围是否覆盖预期证据。 | 行号覆盖 gold evidence。 | 行号指向别处。 | 输出前重新读取引用行。 | `citation_span_accuracy` |
| `file_selection` | 是否读取/引用支持文件并避开 distractor。 | 使用必需文件，少读无关文件。 | 遗漏支持文件或读取过多 distractor。 | 根据问题相关性排序并使用 `allowed_files`。 | `supporting_file_recall`, `supporting_file_precision` |
| `forbidden_file_boundary` | 是否遵守禁用文件边界。 | 没有读取或引用禁用文件。 | `files_read` 或 trace 中出现禁用文件。 | 检索前强制 allowlist。 | `forbidden_file_safety` |
| `unanswerable_handling` | 缺失证据任务是否拒答。 | 说证据不足且不猜测。 | 编造答案。 | 增加缺失证据策略和阈值。 | `unanswerable_abstention` |
| `hallucination_resistance` | 是否避免无依据事实。 | 答案限定在语料证据内。 | 出现无支持声明或编造事实。 | 每个事实声明至少一个 citation。 | `unsupported_claim_control` |
| `robustness_to_malformed_output` | 输出是否可解析并符合 schema。 | JSON 有效且字段存在。 | 不能解析或字段类型错误。 | 提交前校验并修复 JSON。 | `schema_compliance` |
| `optional_judge_agreement` | 可选 judge 与确定性分数的一致性。 | judge 补充确定性发现且无冲突。 | judge 失败、冲突或不可用。 | 只选择必要任务并保持 prompt 紧凑。 | `llm_judge` |
| `report_safety_redaction` | 报告脱敏和路径安全。 | 不泄露本地绝对路径或敏感形态值。 | 报告产物泄露路径或敏感值。 | 使用报告脱敏，不提交 raw prompt dump。 | 报告安全说明与测试 |

## 失败模式与修复

失败：答案正确但缺少 citation。

建议：要求目标 agent 输出带 `file_id`、`line_start`、`line_end` 和 `quote` 的结构化 citation。

失败：citation 文件正确但行号范围错误。

建议：增加最终 citation verification pass，对照检索文本检查行号。

失败：quote mismatch。

建议：让 agent 从源文件精确复制 evidence quote；只有 schema 支持时才省略 quote。

失败：回答了不可回答问题。

建议：增加拒答策略，在没有 gold evidence 时要求回答 "not enough evidence"。

失败：读取 distractor 或 forbidden 文件。

建议：收窄语料权限，在检索前强制执行 `allowed_files`。

失败：幻觉文件中不存在的事实。

建议：要求每个事实性声明至少有一个 citation。

失败：输出 JSON 格式错误。

建议：最终提交前增加 schema 校验和 retry/repair。

失败：可选 LLM judge 内容被脱敏。

建议：将敏感内容排除在 judge prompt 外，或对敏感任务只使用确定性评分。

## 将目标 agent 与参考结果比较

只有在评估类别、任务定义、指标、环境和评分方法兼容时才比较。优先在同一 corpus 和同一 JSONL 任务文件上比较。

标签：

- `same-task`：同一 task pack、评分方法、环境和 comparable 条件。
- `similar-task`：任务族相关但条件不完全一致，只作定性上下文。
- `contextual-only`：方法、论文、benchmark 描述或不可直接比较的公共结果。

不要把本地文件阅读 agent 直接和无关公共 benchmark leaderboard 比较。公共 benchmark 参考可以帮助设计任务，但不表示目标 agent 获得了任何分数。

## Reference 导入指南

支持的本地参考文件：

- Markdown 论文。
- TXT 导出。
- JSONL 任务集。
- CSV 元数据。
- 手工整理的 benchmark 摘要。

使用：

```bash
python -m contract2agent.cli file-eval import-local \
  --input ./reference-notes.md \
  --source-type reference \
  --title "Curated local reference notes" \
  --out .runs/reference-corpus \
  --manifest .runs/reference-corpus/manifest.json
```

公共 benchmark 或方法参考：

- QASPER-like paper QA references。
- SQuAD-like span-grounded QA references。
- HotpotQA-like multi-hop evidence references。
- OpenAI eval methodology references。
- 其他 curated references。

除非关联到观测实验结果，否则这些都是 contextual。

观测实验结果：

- 这是唯一能直接影响性能比较的类别。
- 需要记录 task pack ID、评分方法、环境、模型/agent 摘要、指标、comparable 条件和限制。
- 可比性弱时使用 missing-evidence warnings。
