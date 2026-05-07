# Decisions

Architecture decisions should be short, dated, and linked to evidence when
possible. Add new entries at the top of the table. Do not fabricate historical
decisions; when a decision is inferred from current files rather than explicit
history, mark it as `inferred / needs_verification`.

## Format

| Field | Meaning |
| --- | --- |
| Date | Date the decision was recorded or inferred. |
| Decision | Concise statement of the choice. |
| Status | `proposed`, `accepted`, `superseded`, `deprecated`, or `inferred / needs_verification`. |
| Rationale / Evidence | Source files, commands, tests, or constraints supporting the entry. |

## Log

| Date | Decision | Status | Rationale / Evidence |
| --- | --- | --- | --- |
| 2026-05-07 | Use `Contract2Agent` as the public project name; keep `agentdoctor` only as a legacy CLI alias and runtime artifact namespace. | Accepted | `pyproject.toml` defines both `c2a` and `agentdoctor`; docs and AGENTS call out naming caution. |
| 2026-05-07 | Feature registry statuses must use evidence-specific states and default inferred behavior to `needs_verification`. | Accepted | Bootstrap task requirement and `docs/harness/FEATURE_REGISTRY.schema.json`. |
| 2026-05-06 | Add a repo-local agent-first development harness under docs, `.codex/`, and `scripts/harness/`. | Accepted | Future agent work needs repository-backed context, structured handoff, feature status, and mechanical docs checks without changing application behavior. |
| 2026-05-06 | Keep `AGENTS.md` short and move detailed project context into `docs/`. | Accepted | Large chat or instruction manuals are hard to maintain; repository docs can be validated and updated incrementally. |
| 2026-05-06 | Harness scripts call existing project commands instead of introducing a new build system. | Accepted | Preserves current behavior and keeps validation transparent. |
| 2026-05-05 | Treat file-reading performance as observed-run only. | Accepted | Profile-only declarations cannot prove reading quality, citation grounding, file selection, abstention, or forbidden-file behavior. |
| 2026-05-05 | Keep optional LLM judge outputs separate from deterministic scores. | Accepted | Judge outputs are non-deterministic supplements and must not replace deterministic graders. |
| 2026-05-05 | Keep GitHub Pages static. | Accepted | Long-running agent experiments belong in CLI, local scripts, or CI-generated artifacts, not browser runtime infrastructure. |

## Decision Discipline

- Record decisions that affect architecture, evidence semantics, public behavior, safety, harness workflow, or compatibility.
- Do not turn this file into a changelog; use [harness/PROGRESS.md](harness/PROGRESS.md) for chronological work logs.
- Do not upgrade inferred decisions to accepted without repository evidence or an explicit sprint decision.
