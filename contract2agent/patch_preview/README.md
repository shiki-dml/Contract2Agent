# patch_preview

## Responsibility

This directory implements preview-only patch proposal generation from diagnostic
runs or findings. It helps reason about possible edits without applying them by
default.

## Functionality

- Load findings and diagnostic run artifacts.
- Group related issues and select likely targets.
- Build proposed diffs and summarize risk.
- Validate safety/security constraints for proposed patches.
- Render terminal, Markdown, or JSON summaries.

## Important Files And Entry Points

- `models.py`: patch preview data structures.
- `loader.py`, `grouping.py`, `target_selection.py`: input and planning logic.
- `diff_builder.py`, `strategies.py`: proposal construction.
- `risk.py`, `security.py`, `validation.py`: safety analysis.
- `report.py`: output rendering.

## Public Behavior Contracts

- Preview mode must not apply patches unless an explicit future workflow safely
  designs and tests that behavior.
- Do not bypass path safety, generated-artifact exclusions, or security checks.

## Related Tests

- `../../tests/test_patch_preview.py`

## Related Docs

- `../../docs/patch-preview.md`
- `../../docs/CODEMAP.md`

## Agent Notes

Future agents may improve proposals or reports in focused sprints. Do not make
this subsystem a hidden auto-patcher as part of harness work.
