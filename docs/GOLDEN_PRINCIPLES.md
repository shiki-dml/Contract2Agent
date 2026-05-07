# Golden Principles

## Product Principles

- Build an evaluation framework, not a fake universal judge.
- Contract-first development comes before implementation: define scope, non-goals, allowed files, acceptance criteria, and validation evidence.
- Scores must be backed by observed evidence, imported traces, documented references, or explicit missing-evidence notes.
- Declared capability is not proof of performance.
- Missing evidence must be visible in reports.
- Benchmark references are contextual unless this project actually ran a comparable evaluation.
- Agent classification must use tools, tasks, permissions, policies, and evidence rather than exact sample names.
- File-reading performance requires observed runs; profile-only reports are readiness and risk reports.
- Financial transaction evaluation is simulation-only.
- GitHub Pages remains static.

## Engineering Principles

- Preserve existing behavior by default.
- Do not perform broad refactors without an approved sprint contract.
- Keep schemas JSON-serializable.
- Prefer existing dataclass/schema style unless a local module already requires Pydantic.
- Avoid production dependencies for harness-only work.
- Keep application logic, docs, examples, CLI help, and tests aligned.
- Preserve legacy contract-diagnosis functionality unless a future sprint intentionally changes it.
- Keep path containment, secret filtering, generated-artifact exclusions, command safety, and preview-only patch boundaries intact.

## Evidence Principles

- Evidence before verification.
- Tests and docs are evidence, not absolute proof of full feature completeness.
- A passing test supports only the surface it covers.
- A failed, skipped, missing, or blocked command must be recorded honestly.
- Do not reinterpret dependency or environment failures as product passes.
- Do not fabricate observed runs, benchmark claims, paper claims, score claims, or experiment results.
- Unknown or uninspected behavior is not failed by default; use `needs_verification` or `blocked` as appropriate.

## Harness Principles

- The repository is the source of truth for future agent sessions.
- Work is incremental: one bounded feature, bug, or documentation unit at a time.
- Planner, generator, evaluator, reviewer, docs, and handoff roles stay separate.
- Scoped writes matter: touch only files allowed by the contract or user task.
- Evaluators and reviewers are skeptical, evidence-based, and must cite commands or files.
- Feature status lives in `docs/harness/feature_registry.json`.
- Handoffs live in `docs/AGENT_HANDOFF.md` and progress logs live in `docs/harness/PROGRESS.md`.
- Handoff/progress files are durable memory; keep them concrete and current without turning them into giant manuals.
