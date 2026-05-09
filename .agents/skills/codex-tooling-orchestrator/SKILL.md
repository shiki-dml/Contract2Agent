---
name: codex-tooling-orchestrator
description: Use this skill when configuring or coordinating Contract2Agent's repo-local Codex tooling, including .codex/config.toml, .codex/agents role files, .agents/skills, optional MCP servers, and ECC-style multi-agent workflows. Use when changing agent/skill/MCP organization, deciding which local role or skill should handle a task, or safely enabling optional tool servers without weakening evidence discipline.
---

# Codex Tooling Orchestrator

## Operating Contract

Use external tooling as support for Contract2Agent's local evidence workflow, not as a replacement for it.

Always preserve these boundaries:

1. Treat `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, `docs/ARCHITECTURE.md`, `docs/CODEMAP.md`, `docs/AGENT_HANDOFF.md`, and `docs/harness/PROGRESS.md` as the local source of truth.
2. Keep declared, inferred, observed, reference, prediction, and missing evidence separate.
3. Do not mark features verified from MCP lookups, web search, or tool availability alone.
4. Do not enable networked MCP servers, install packages, or add API keys without explicit user authorization.
5. Do not store secrets in the repository. Use environment variables or connector auth only.

## Workflow

1. Baseline the repository.
   - Run or inspect `git status --short`.
   - Read handoff/progress and relevant codemap/architecture docs before edits.
2. Choose the smallest role set.
   - Use read-only roles for inventory, mapping, evaluation, and review.
   - Use writer roles only under an approved bounded task or sprint contract.
3. Choose the smallest skill set.
   - Use domain skills for evaluation architecture, file-reading evals, LLM judges, CLI UX, research evidence, or patching only when the task matches them.
   - Do not load unrelated skills just because they exist.
4. Choose MCP only when it adds concrete evidence.
   - Prefer official docs, repository metadata, issue/PR state, or browser/UI evidence.
   - Record whether evidence is external reference, imported result, observed run, or missing.
5. Finish with local evidence.
   - Run the relevant local gates when safe and authorized.
   - Update handoff/progress when project state changes.

## Local Role Map

Use these roles as a project-scoped division of labor:

- `codebase_mapper`: read-only repository map and ownership discovery.
- `docs_inventory_agent`: read-only documentation inventory and stale-signal detection.
- `feature_inventory_agent`: read-only feature candidate inventory with uncertainty preserved.
- `test_inventory_agent`: read-only test layout, fixture, and coverage inventory.
- `harness_planner`: read-only or planning-only harness/sprint planning.
- `contract_generator`: writes only approved/proposed sprint contracts.
- `feature_generator`: writes implementation/docs/tests only inside approved scope.
- `doc_gardener`: writes approved docs only, not registry or progress by default.
- `handoff_writer`: writes handoff/progress artifacts.
- `bug_reviewer`: read-only correctness/regression review.
- `evaluator`: read-only PASS / FAIL / INCONCLUSIVE / BLOCKED review.

Do not blur evaluator/reviewer/planner/writer responsibilities. A tool can help gather evidence, but it does not change the role boundary.

## Skill Map

Prefer existing local skills before inventing new process:

- `agent-eval-architect`: generalized agent evaluation schemas, scoring, prediction, and eval-pack design.
- `file-reading-eval-architect`: file-reading corpus/task/run/grade/report adapter work.
- `llm-judge-eval-architect`: optional LLM judge support with cost, key, and deterministic score separation.
- `research-grounded-eval`: papers, benchmarks, docs, and imported experiment evidence.
- `cli-experience-designer`: CLI help, command grouping, modes, and terminal UX.
- `smart-patcher`: focused bug fixes and same-root-cause patching.
- `pr-reviewer`: structured PR/code review.
- `simple-refactor`: small readability refactors.
- `unit-test-starter`: starter tests for small modules.

When a new skill is needed, keep `SKILL.md` concise, add `agents/openai.yaml`, include only resources that future agents actually need, and validate the skill before claiming it is ready.

## MCP Selection

Use optional MCP servers as evidence-gathering tools:

- Context/documentation MCP: use for current API or library docs; cite official or primary sources when they influence project decisions.
- GitHub MCP or connector: use for issues, PRs, reviews, and CI status; do not treat remote status as a substitute for local validation unless the task is specifically CI triage.
- Playwright/browser MCP: use for manual local UI or docs-site inspection when authorized; do not add browser-run tests unless a sprint contract explicitly allows them.
- Search/research MCP: use only for research context and primary-source discovery; avoid unsupported benchmark claims.
- Memory MCP: avoid as source of truth for this project. Durable state belongs in repository docs, handoff, progress, and artifacts.
- Sequential-thinking/planning MCP: use only for complex planning support; final claims still need repository evidence.

Before enabling an MCP server:

1. Confirm why local tools are insufficient.
2. Confirm package download/network access is acceptable.
3. Confirm required environment variables exist outside the repo.
4. Set the server to optional unless the task cannot proceed without it.
5. Record failures as environment or dependency blockers, not product evidence.

## Config Discipline

Keep `.codex/config.toml` project-scoped and conservative:

- Register local agents and skills explicitly where supported.
- Keep optional MCP servers disabled until needed.
- Avoid global behavior changes that conflict with `AGENTS.md`.
- Do not add production dependencies for tooling-only MCP support.
- Prefer comments and disabled entries over auto-starting tools that need network access or secrets.
