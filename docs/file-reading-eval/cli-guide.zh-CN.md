# 文件阅读 CLI 用户指南

本指南只记录已经实现的命令。从 fresh clone 开始时优先使用 `python -m contract2agent.cli ...`；执行 `python -m pip install -e ".[dev]"` 后，如果控制台脚本进入 PATH，也可以使用 `c2a ...`。

## 安装

```bash
python -m pip install -e ".[dev]"
```

如需运行文档检查：

```bash
python -m pip install -e ".[docs]"
```

确定性评分不需要 API key。可选 LLM 评审必须显式选择 provider 或命令式 judge。

## 基础帮助命令

```bash
python -m contract2agent.cli --help
python -m contract2agent.cli file-eval --help
python -m contract2agent.cli file-eval doctor --plain
python -m contract2agent.cli file-eval help workflow
python -m contract2agent.cli file-eval help scoring
python -m contract2agent.cli file-eval help llm
python -m contract2agent.cli file-eval help examples
python -m contract2agent.cli file-eval help references
```

安装后的控制台脚本等价命令：

```bash
c2a --help
c2a file-eval --help
```

如果找不到 `c2a`，请使用模块入口，或重新执行 `python -m pip install -e ".[dev]"`。

## 概念和文件

- Agent profile：包含 `agent_id`、工具、权限、引用能力、输出 schema 能力、trace 能力和策略约束的 JSON。
- Corpus：通过 `import-local` 导入的语料目录，以及生成的 `manifest.json`。
- Eval task：JSONL 中的一行，包含 `task_id`、`task_type`、问题、允许/禁用文件、金标答案和证据跨度。
- Gold evidence span：`file_id`、`line_start`、`line_end`、`quote`、`label` 和 `required`。
- Target output：目标智能体输出的 JSON，包含 `answer`、`citations`、可选 `confidence`、`files_read` 和 `notes`。
- Run directory：包含 `run.json`、`run.jsonl`、任务输入、目标输出、stdout、stderr 的本地运行目录。
- Grade JSON：确定性 `grades` 和 `scorecard`。
- Report directory：生成的 Markdown / JSON 报告产物。

## 确定性本地评分流程

请使用绝对 adapter 路径，因为目标命令会以 run directory 作为当前工作目录运行。

PowerShell：

```powershell
$C2A_READER = (Resolve-Path examples/file_reading_eval/agents/dummy_good_reader.py).Path
```

Bash：

```bash
C2A_READER="$PWD/examples/file_reading_eval/agents/dummy_good_reader.py"
```

```bash
python -m contract2agent.cli file-eval import-local \
  --input examples/file_reading_eval/corpus \
  --out .runs/example-corpus \
  --manifest .runs/example-corpus/manifest.json

python -m contract2agent.cli file-eval validate \
  --corpus .runs/example-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl

python -m contract2agent.cli file-eval run \
  --profile examples/file_reading_eval/profiles/cautious_reader_profile.json \
  --agent-command "python ${C2A_READER} {input_json} {output_json}" \
  --corpus .runs/example-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --time-budget-seconds 30 \
  --max-tasks 4 \
  --seed 7 \
  --out .runs/example-good

python -m contract2agent.cli file-eval grade \
  --run .runs/example-good \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl \
  --out .runs/example-good/grades.json

python -m contract2agent.cli file-eval report \
  --run .runs/example-good \
  --format md,json \
  --out .runs/example-report
```

`.runs/` 已被忽略。除非未来任务明确要求创建小型 fixture，否则不要提交生成的运行产物。

## 证据跨度调试

运行目标智能体之前先使用 `validate`：

```bash
python -m contract2agent.cli file-eval validate \
  --corpus .runs/example-corpus/manifest.json \
  --tasks examples/file_reading_eval/tasks/sample_tasks.jsonl
```

常见失败：

- 行号范围无效：`line_start` 至少为 1，且 `line_end` 不能小于 `line_start`。
- quote 不匹配：`quote` 文本没有出现在所选文件行范围内。
- 缺少证据跨度：可回答任务没有 gold answer 或 evidence。
- 未知文件 ID：allowed/supporting/distractor 文件或证据跨度引用了 manifest 之外的文件。

## 目标输出调试

目标输出必须是 JSON object。最小有效示例：

```json
{
  "answer": "Approved refunds require a written service-impact notice within 7 calendar days.",
  "citations": [
    {
      "file_id": "contract_policy.md",
      "line_start": 3,
      "line_end": 3,
      "quote": "Approved refunds require a written service-impact notice within 7 calendar days."
    }
  ],
  "confidence": 0.92,
  "files_read": ["contract_policy.md"]
}
```

常见目标输出错误：

- citation JSON 格式错误：citation 不是 object，或 line 字段不是整数。
- 答案没有 citation：答案可能正确，但引用存在性和 grounding 会失败。
- 读取禁用文件：`files_read` 或 trace 中出现任务禁用文件。
- 不可回答问题被猜答：任务有 `unanswerable: true` 时，应回答证据不足。
- 敏感形态答案被隐藏：报告会隐藏敏感形态值；敏感语料优先使用确定性评分。

## 可选 LLM 评审流程

LLM 评审默认禁用。它是可选、非确定性、补充性的。

无 API 调用的 dry-run 估算：

```bash
python -m contract2agent.cli file-eval judge \
  --run .runs/example-good \
  --provider openai \
  --dry-run-cost-estimate \
  --judge-only failed \
  --max-judge-tasks 3
```

命令式本地 judge：

```bash
python -m contract2agent.cli file-eval judge \
  --run .runs/example-good \
  --provider command \
  --judge-command "python examples/file_reading_eval/agents/dummy_command_judge.py {input_json} {output_json}"
```

OpenAI 兼容 provider：

```bash
python -m contract2agent.cli file-eval judge \
  --run .runs/example-good \
  --provider openai \
  --judge-only failed \
  --max-judge-tasks 5 \
  --llm-max-input-chars 12000 \
  --llm-max-output-tokens 500 \
  --evidence-snippet-limit 5 \
  --cost-budget-usd 1.00
```

API key 规则：

- 默认从环境变量 `OPENAI_API_KEY` 读取。
- `--prompt-for-key` 只在交互式终端中使用隐藏的会话内输入。
- key 不写入报告、日志、缓存、浏览器代码、文档样例或已提交文件。
- judge 输入是紧凑摘要，不包含完整语料、禁用文件或未清理的本地绝对路径。

## 报告导出流程

```bash
python -m contract2agent.cli file-eval report \
  --run .runs/example-good \
  --format md,json \
  --out .runs/example-report
```

报告字段包括运行摘要、语料摘要、任务覆盖率、分维度分数、引用质量、文件选择、答案正确性、拒答质量、禁用文件安全、鲁棒性、参考比较、失败模式、建议、可选 LLM 评审状态、限制和 trace 产物位置。

## 参考和 benchmark 流程

列出上下文参考：

```bash
python -m contract2agent.cli file-eval list-references
```

将本地参考文件作为上下文源导入：

```bash
python -m contract2agent.cli file-eval import-local \
  --input ./my-paper-notes.md \
  --source-type paper \
  --title "My curated paper notes" \
  --out .runs/reference-corpus \
  --manifest .runs/reference-corpus/manifest.json
```

只和观测参考结果比较：

```bash
python -m contract2agent.cli file-eval compare \
  --run .runs/example-good \
  --reference examples/file_reading_eval/expected_reports/reference_result.example.json \
  --out .runs/example-good/comparison.md
```

规则：

- Reference paper 不等于 observed score。
- Benchmark description 不等于 agent performance。
- 用户导入论文不是可信真值，除非被整理成带 gold evidence 的任务。
- 公共结果只有在模型/智能体、任务集、环境和指标都记录清楚时才可比较。
- 报告应标注 `same-task`、`similar-task` 或 `contextual-only`。

## Doctor 和排障

```bash
python -m contract2agent.cli file-eval doctor --plain
python -m contract2agent.cli file-eval doctor --json
```

常见错误：

- 找不到 `c2a`：使用 `python -m contract2agent.cli` 或重新安装 editable package。
- 报告里本地路径被隐藏：这是预期安全行为。
- 可选 judge 不可用或被禁用：确定性评分仍可运行；需要显式配置 provider 或命令式 judge。
- 没有 observed score：必须先运行目标命令；profile-only 不能报告性能。
- 网络导入被阻止：这是默认行为；`import-reference` 需要显式 `--allow-network`，当前只记录元数据。
