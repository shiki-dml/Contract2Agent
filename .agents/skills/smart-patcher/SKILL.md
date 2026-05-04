---
name: smart-patcher
description: Use this skill for focused bug fixes, patch requests, regression repairs, diagnosis-quality improvements, test fixes, and safe localized refactors. It makes Codex concise, scope-aware, and proactive about adjacent same-root-cause issues without changing unrelated behavior.
---

# Smart Patcher Skill

## Purpose

Use this skill when fixing bugs, repairing regressions, improving deterministic diagnosis quality, cleaning up focused code paths, or making localized refactors.

The goal is to produce a correct, minimal, high-quality patch while checking for closely related same-root-cause issues.

## Core rules

1. Fix the requested issue first.
2. Preserve existing reasonable behavior.
3. Do not rewrite or redesign unrelated parts of the project.
4. Do not change unrelated UI, routes, styling, sample loading, copy/export buttons, CLI behavior, build config, dependencies, or unrelated tests.
5. Patch existing logic before creating new parallel logic.
6. Do not hard-code exact fixtures.
7. Add focused regression tests for behavior changes.
8. Run available verification commands.
9. Keep progress updates compact.
10. Report changed files, tests, commands run, results, and remaining limitations.

## Workflow

### 1. Scope the task

Before editing, identify:

- requested behavior
- likely files/subsystems
- non-goals
- existing behavior that must not change
- tests/build commands that should verify the fix

Ask for clarification only if the missing information could cause destructive or broad changes.

### 2. Inspect efficiently

Prefer targeted file reads and targeted search.

Avoid:

- broad recursive searches when exact files are known
- repeated failed approval-escalated commands
- unrelated large-file inspection
- rewriting before understanding the existing flow

If approval or sandbox checks repeatedly fail, switch to smaller read-only inspection or ask the user.

### 3. Patch existing logic

Modify the existing implementation where reasonable.

Do not create a new architecture, new pipeline, new framework, or duplicate implementation unless the existing code cannot reasonably be patched.

### 4. Check adjacent same-root-cause issues

After finding the root cause, check nearby same-layer problems.

Safe adjacent fixes may include:

- another output path using stale data
- JSON/Markdown export using unfiltered diagnosis
- Evaluation Lab preview using default or stale expected issues
- duplicated trigger logic with the same bug
- shared mutable templates causing cross-run contamination
- tests asserting old incorrect behavior

Fix adjacent issues only when they are:

- same root cause or same layer
- localized
- low regression risk
- testable or clearly inspectable
- not a product behavior change outside the request

If not safe, leave a follow-up note instead of silently expanding scope.

### 5. Preserve unrelated behavior

Do not touch unrelated:

- UI layout
- styles
- routes
- navigation
- sample loading
- export/copy buttons unless the bug is in exported content
- CLI behavior
- dependency versions
- generated assets
- unrelated tests

Do not remove an issue family globally just because it caused a false positive. Add proper trigger gates, blocker triggers, or output filtering.

### 6. Generalizable fix rule

Production logic must be general.

Use concepts such as:

- active triggers
- clause triggers
- blocker triggers
- issue-family gates
- final filtered diagnosis objects
- fresh per-run state
- deduplication
- timeline role classification
- shared export source of truth

Regression fixtures may be specific. Production logic must not special-case full fixture text.

### 7. Test discipline

When modifying behavior:

- add or update focused regression tests
- include positive and negative assertions when relevant
- test cross-contamination if stale state is possible
- test UI/export/preview consistency if multiple outputs share the bug
- run available tests/build/lint/typecheck commands

Do not invent nonexistent scripts.

### 8. Self-review before final response

Before finalizing, inspect the diff and verify:

- requested issue is fixed
- unrelated files were not changed
- existing reasonable behavior is preserved
- regression coverage exists
- exports and previews use corrected data
- no exact fixture hard-coding was introduced
- no stale duplicate logic remains
- available verification commands were run

If a safe issue is found, fix it before finalizing. If it is unsafe or out of scope, list it as a follow-up.

## Final response format

Include:

1. What changed.
2. Why it fixes the root cause.
3. Files changed.
4. Tests added or updated.
5. Commands run and results.
6. Remaining limitations or follow-ups.

## Stop and ask before

- adding a production dependency
- deleting user data
- changing public routes or APIs
- changing deployment configuration
- broad architecture rewrite
- destructive Git operations
- force pushing
- modifying unrelated features
- changing security/auth/license behavior
