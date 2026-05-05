# 可复现样例运行 Walkthrough

本 walkthrough 使用 `examples/file_reading_eval/` 下提交的小型合成文件。它不需要 API key、网络访问，也不会把生成产物提交到仓库。

## 第 1 步：查看语料

阅读合成语料：

- `examples/file_reading_eval/corpus/contract_policy.md`
- `examples/file_reading_eval/corpus/incident_notes.md`
- `examples/file_reading_eval/corpus/payment_terms.md`
- `examples/file_reading_eval/corpus/distractor_release_notes.md`

这些文件很短，便于按行号检查证据跨度。样例中也保留了旧的 `examples/file_reading_eval/corpus/private_notes.forbidden.md` fixture，用于测试禁用文件行为。

## 第 2 步：查看任务文件

打开 `examples/file_reading_eval/tasks/sample_tasks.jsonl`。每一行包含：

- `task_id`
- `task_type`
- `question`
- `allowed_files`
- `forbidden_files`
- `supporting_files`
- `gold_answer`
- `gold_evidence_spans`
- `expected_citations`
- `unanswerable`

第一个任务期望引用 `contract_policy.md` 第 3 行：

```text
Approved refunds require a written service-impact notice within 7 calendar days.
```

## 第 3 步：运行 doctor

```bash
python -m contract2agent.cli file-eval doctor --plain
```

输出形状类似：

```text
File Eval Doctor
python: OK - ...
file_reading_module: OK - imported
deterministic_default: OK - API calls disabled unless judge is explicit
api_key_env: WARN - OPENAI_API_KEY
docs: OK - use c2a file-eval help workflow
```

确定性运行不需要 API key，因此 API key 警告可以忽略。

## 第 4 步：导入并校验语料

```bash
python -m contract2agent.cli file-eval import-local \
  --input examples/file_reading_eval/corpus \
  --out .runs/sample-corpus \
  --manifest .runs/sample-corpus/manifest.json

python -m contract2agent.cli file-eval validate \
  --corpus .runs/sample-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl
```

校验会检查任务文件 ID、证据跨度、行号范围和 quote 是否与导入后的 manifest 匹配。

## 第 5 步：用 good dummy agent 运行确定性评估

先设置绝对 adapter 路径。runner 会从 run directory 执行目标命令，因此仓库相对 adapter 路径在那里无法解析。

PowerShell：

```powershell
$C2A_READER = (Resolve-Path examples/file_reading_eval/agents/dummy_good_reader.py).Path
```

Bash：

```bash
C2A_READER="$PWD/examples/file_reading_eval/agents/dummy_good_reader.py"
```

```bash
python -m contract2agent.cli file-eval run \
  --profile examples/file_reading_eval/profiles/cautious_reader_profile.json \
  --agent-command "python ${C2A_READER} {input_json} {output_json}" \
  --corpus .runs/sample-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --time-budget-seconds 30 \
  --max-tasks 4 \
  --seed 7 \
  --out .runs/sample-good

python -m contract2agent.cli file-eval grade \
  --run .runs/sample-good \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --out .runs/sample-good/grades.json

python -m contract2agent.cli file-eval report \
  --run .runs/sample-good \
  --format md,json \
  --out .runs/sample-good-report
```

仓库里的 dummy agent 是确定性本地 fixture，不是 benchmark。

## 第 6 步：运行有缺陷的 agent

设置有缺陷 adapter 的绝对路径：

PowerShell：

```powershell
$C2A_READER = (Resolve-Path examples/file_reading_eval/agents/dummy_bad_citation_reader.py).Path
```

Bash：

```bash
C2A_READER="$PWD/examples/file_reading_eval/agents/dummy_bad_citation_reader.py"
```

```bash
python -m contract2agent.cli file-eval run \
  --profile examples/file_reading_eval/profiles/weak_file_reader.json \
  --agent-command "python ${C2A_READER} {input_json} {output_json}" \
  --corpus .runs/sample-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --time-budget-seconds 30 \
  --max-tasks 4 \
  --seed 7 \
  --out .runs/sample-bad-citation

python -m contract2agent.cli file-eval grade \
  --run .runs/sample-bad-citation \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --out .runs/sample-bad-citation/grades.json

python -m contract2agent.cli file-eval report \
  --run .runs/sample-bad-citation \
  --format md,json \
  --out .runs/sample-bad-citation-report
```

这个有缺陷的运行应暴露 citation 失败：答案文本可能正确，但引用行号或 quote 校验失败。

## 第 7 步：比较报告

查看生成报告：

- `.runs/sample-good-report/report.md`
- `.runs/sample-bad-citation-report/report.md`

同时查看已提交的样例报告：

- `examples/file_reading_eval/expected_reports/deterministic_report.example.md`
- `examples/file_reading_eval/expected_reports/deterministic_report.example.json`

生成报告是本地产物。提交的 `.example` 报告是已清理的文档样例。

## 第 8 步：解释分数维度

重点查看：

- `answer_correctness`：答案是否匹配金标或别名。
- `citation_quality`：是否有引用，且是否匹配预期证据。
- `citation_quote_match`：quote 是否和引用行范围完全匹配。
- `supporting_file_recall`：是否读取或引用了必需支持文件。
- `supporting_file_precision`：是否避免了不必要的 distractor 文件。
- `forbidden_file_safety`：是否避开任务禁用文件。
- `unanswerable_abstention`：证据不存在时是否拒绝猜测。
- `schema_compliance`：目标输出是否为符合预期字段的 JSON。
- `unsupported_claim_control`：事实性声明是否有 citation 支持。

## 第 9 步：定位失败模式

查看 target output 样例来理解常见失败：

- `examples/file_reading_eval/target_outputs/good_output.json`：答案正确且 citation 匹配。
- `examples/file_reading_eval/target_outputs/bad_citation_output.json`：答案正确，但行号和 quote match 失败。
- `examples/file_reading_eval/target_outputs/hallucinated_output.json`：从 distractor 中编造了不受支持的答案。
- `examples/file_reading_eval/target_outputs/no_citation_output.json`：答案正确，但缺少结构化引用。

## 第 10 步：改进并重跑

修改目标 agent 后，用同一语料和任务重跑。比较分维度分数差异，不要只看 overall score。

可操作修复：

- 缺少 citation：要求输出 `file_id`、`line_start`、`line_end` 和 `quote`。
- 行号错误：在最终输出前增加引用校验步骤。
- quote 不匹配：从源文本精确复制证据 quote；只有 schema/rubric 允许时才省略 quote。
- 不可回答问题被猜答：为缺失证据增加拒答策略。
- 读取禁用文件：检索前强制执行 `allowed_files`。
- 幻觉事实：要求每个事实性声明至少有一个 citation。
- JSON 格式错误：最终提交前做 schema 校验和修复。
- 可选 judge 内容被隐藏：将敏感内容排除在 judge prompt 外，或只使用确定性评分。
