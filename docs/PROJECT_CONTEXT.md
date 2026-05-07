# Project Context

Contract2Agent is an experimental developer framework for structured,
pre-runtime AI agent diagnosis. It takes agent profiles, declared capabilities,
tool surfaces, permissions, sample tasks, policy constraints, and available
evidence, then produces broad capability classifications, eval category
selection, preliminary score dimensions, cautious outcome predictions, and
Markdown/JSON reports.

Use the project name `Contract2Agent`. The `agentdoctor` name is a legacy CLI
alias and runtime artifact namespace only; do not use it as the public project
identity except when documenting backward compatibility.

## What It Is

- A deterministic, evidence-first framework for diagnosing agent readiness before deployment or iteration.
- A generalized framework that supports broad agent families through typed schemas, registries, adapters, and reports.
- A static-demo-friendly project whose GitHub Pages surfaces show precomputed or browser-local behavior only.
- A preservation path for the original contract-dispute playground as a legacy specialized demo.
- A harnessed repository where future agents can plan, implement, evaluate, and hand off bounded work without relying on chat history.

## What It Is Not

- It is not a universal arbitrary-agent judge.
- It is not a benchmark leaderboard.
- It is not proof that an agent performs well from name, branding, or declared capability alone.
- It is not legal, financial, or deployment advice.
- It does not perform real payment, trading, ordering, transfer, or financial execution.
- It does not mark features verified without concrete evaluator, test, command, or artifact evidence.

## Current Scope

The core framework supports broad agent profile evaluation, evidence resolution,
contextual benchmark references, deterministic scoring, cautious prediction, and
report rendering. The first specialized adapter is `file_reading_agent`, which
supports local CLI-based corpus import, task loading/building, black-box agent
runs, trace capture, deterministic grading, reference comparison, optional LLM
judge supplements, and reports.

The legacy contract diagnosis flow remains part of the product and must be
preserved unless a future sprint intentionally deprecates it with tests and docs.
Static triage, time/cost estimation, and patch preview subsystems are planning
and reporting tools; they must not be described as autonomous repair or live
execution systems.

## Supported Agent Families

- `coding_agent`
- `file_reading_agent`
- `contract_review_agent`
- `browser_navigation_agent`
- `research_agent`
- `workflow_automation_agent`
- `financial_transaction_agent_simulated`
- `unknown_agent`

The implementation may also expose compatibility or broad fallback categories,
but new work must not overfit to exact sample names or fixture labels.

## Evidence Model

Contract2Agent keeps these concepts separate:

- Declared capability: what a profile or user says.
- Inferred capability: what tools, permissions, tasks, and policies imply.
- Observed evidence: actual runs, traces, imported results, tests, or manual evidence linked to the agent.
- Reference evidence: benchmark, paper, or methodology metadata used for context.
- Prediction: a cautious pre-runtime estimate based on evidence and risk.
- Missing evidence: explicitly recorded gaps that prevent stronger claims.

For file-reading agents, profile-only assessment can produce readiness, risk,
and recommended eval plans, but it must not claim actual reading performance.
Observed performance requires a documented run artifact.

## Known Constraints

- GitHub Pages remains static.
- Network import of public datasets or papers must be explicit and controlled.
- Baseline file-reading evaluation makes no API calls.
- Optional LLM judge outputs are supplemental, non-deterministic, budgeted, cached only when enabled, and kept separate from deterministic scores.
- API keys must come from environment variables or hidden session-only input and must never be written to disk, reports, logs, caches, browser assets, docs examples, or committed files.
- Path containment, secret filtering, generated-artifact exclusions, command safety checks, and preview-only patch boundaries must not be weakened.
- Production dependencies should not be added for harness-only work.

## Evolving Areas

- Feature registry status is evidence-backed but not exhaustive.
- Project-scoped Codex agent configuration exists, but runtime support still needs verification.
- Some roadmap items, such as richer observed trace import and future specialized eval packs, are inferred or planned rather than verified.
- Historical validation records are useful context, but a future task must run relevant gates before claiming fresh validation.

## Preserve By Default

Future agents should preserve:

- Evidence separation between declared, inferred, observed, reference, prediction, and missing evidence.
- Deterministic default grading and reporting.
- Static GitHub Pages behavior.
- Legacy contract diagnosis behavior and `agentdoctor` compatibility aliases.
- File-reading safety boundaries around corpora, forbidden files, absolute paths, secrets, judge inputs, and report sanitization.
- Scoped writes, sprint contracts, progress logs, and handoff updates for restartability.
