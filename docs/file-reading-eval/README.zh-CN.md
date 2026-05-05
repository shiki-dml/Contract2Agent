# 文件阅读智能体评估

Contract2Agent 提供 `file_reading_agent` 专用适配器，用于本地、可观察的文件阅读评估。它面向需要读取受控语料、选择证据、回答问题、引用源文件行号、在证据不足时拒答，并遵守禁用文件边界的智能体。

该适配器坚持评估优先。`profile-only` 报告只能说明准备度和风险；真实阅读性能分数必须来自实际的 `file-eval run` 运行产物。

## 它做什么

- 将批准的本地文本文件导入受 manifest 约束的语料。
- 加载或生成带金标答案和证据跨度的 JSONL 任务。
- 通过黑盒 JSON 命令适配器运行目标智能体。
- 捕获目标输出、trace、stdout、stderr、耗时和读取文件列表。
- 使用默认确定性评分检查答案正确性、引用、文件选择、拒答、schema 合规和禁用文件安全。
- 在显式启用时追加 LLM 或命令式评审，并与确定性分数分开记录。
- 只在参考结果兼容时比较观测分数；公共 benchmark 仍是上下文参考。
- 生成 Markdown / JSON 报告，说明证据基础、失败模式、建议、限制和产物标签。

## 它不做什么

- 不会仅凭能力声明给出文件阅读性能分数。
- 确定性模式不会调用 API。
- GitHub Pages 不运行实时评估。
- 不读取配置语料之外的私有文件。
- 不把论文、benchmark 描述或方法说明当作目标智能体得分。
- 默认无依赖路径不实现网络数据集下载。

## 文档导航

- [CLI 用户指南](cli-guide.zh-CN.md)
- [样例运行 walkthrough](sample-run.zh-CN.md)
- [报告示例与评分说明](report-examples.zh-CN.md)
- [English overview](README.md)
- [English CLI guide](cli-guide.md)
- [English sample run](sample-run.md)
- [English report examples](report-examples.md)

仓库样例：

- `examples/file_reading_eval/README.md`
- `examples/file_reading_eval/tasks/sample_tasks.jsonl`
- `examples/file_reading_eval/target_outputs/good_output.json`
- `examples/file_reading_eval/expected_reports/deterministic_report.example.md`
- `examples/file_reading_eval/expected_reports/deterministic_report.example.json`

## 最小工作流

从 fresh clone 安装：

```bash
python -m pip install -e ".[dev]"
```

优先使用模块入口，因为它不依赖 `c2a` 是否已进入 PATH：

```bash
python -m contract2agent.cli --help
python -m contract2agent.cli file-eval --help
python -m contract2agent.cli file-eval doctor --plain
python -m contract2agent.cli file-eval help llm
```

安装后通常也可以使用控制台脚本：

```bash
c2a --help
c2a file-eval --help
```

## 核心概念

- Agent profile：描述工具、权限、引用能力、trace 能力和安全约束的 JSON。
- Corpus：导入后的受控本地语料。
- Eval task：包含问题、允许文件、禁用文件、金标答案和证据跨度的 JSONL 记录。
- Gold answer：期望答案或可接受别名。
- Gold evidence spans：可机器校验的 `file_id`、行号范围、quote、label 和 required 标记。
- Target output：目标智能体输出的 `answer`、`citations`、可选 `confidence`、`files_read` 和 `notes`。
- Citation validation：确定性检查文件 ID、行号范围和 quote 匹配。
- Deterministic grader：默认本地评分器，不需要 API key。
- Optional LLM judge：显式启用的补充语义评审，非确定性，和确定性分数分开。
- Report JSON / Markdown report：解释分数、证据、失败模式、建议和限制的报告。
- Run directory：通常位于 `.runs/` 下的本地运行目录，已被忽略。

## 安全模型

`import-local` 默认跳过常见 secret、缓存、虚拟环境、浏览器数据、`.git`、`.env` 和凭据类路径。报告会清理本地绝对路径，并在已实现的报告路径中隐藏敏感形态的值。

runner 只向目标命令发送当前任务所需的输入。目标命令需要遵守 `allowed_files` 和 `forbidden_files`；评分器会根据输出和 trace 检测被报告的禁用文件读取。

参考论文、公共方法文件、CSV 元数据和 benchmark 摘要只是用户提供或上下文证据。除非被整理成任务并关联到兼容指标的实际观测运行，否则它们不是目标智能体性能结果。

## 当前参考导入支持

已实现：

- `import-local --source-type paper|reference|methodology` 可记录本地来源、license 和限制。
- `list-references` 打印已整理的上下文参考源元数据。
- `import-reference --allow-network` 会记录已知参考源元数据；默认无依赖适配器不会下载数据集样例。
- `compare` 在计算分数差异前检查 task pack、评分方法、环境和 comparable 条件。

计划中：

- 更完整的本地论文导入，而不仅是用户预先转换好的文本/Markdown。
- 带 license、来源和可复现实任务构建的 reference pack。
- 更丰富的比较标签，而不仅是当前同任务兼容检查。

## 静态页面约束

GitHub Pages 仍然只是静态查看器和演示页面。文件阅读评估应通过 CLI、本地脚本或 CI 生成的产物运行，而不是在浏览器中运行。
