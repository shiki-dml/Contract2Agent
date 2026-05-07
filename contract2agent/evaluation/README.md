# evaluation

## Responsibility

This directory implements the generalized agent evaluation framework: profile
normalization, capability classification, evidence resolution, eval category
selection, preliminary scoring, cautious prediction, and report rendering.

## Functionality

- JSON-serializable schemas for agent profiles, tools, signals, evidence,
  scorecards, predictions, references, and reports.
- Broad multi-label agent classification from tools, tasks, permissions, and
  policy signals rather than exact names.
- Evidence-aware scoring that keeps observed, imported, reference,
  declared-only, and missing evidence separate.
- Markdown and JSON report generation.

## Important Files And Entry Points

- `schema.py`: dataclasses and serialized evaluation objects.
- `capability_classifier.py`, `classifier.py`: signal extraction and broad classification.
- `registry.py`, `data.py`, `sample_data.py`: agent type, eval category, and reference registries.
- `evidence.py`: evidence source resolution.
- `scoring.py`: preliminary score dimensions.
- `prediction.py`: cautious outcome prediction.
- `reports.py`, `report.py`: rendering.
- `file_reading/`: specialized file-reading adapter.

## Public Behavior Contracts

- Do not infer high confidence from declared capability alone.
- Do not convert benchmark references into direct scores without comparable observed runs.
- Keep schemas JSON-serializable.
- Keep `unknown_agent` handling useful and cautious.

## Related Tests

- `../../tests/test_agent_evaluation_framework.py`
- `../../tests/test_report_rendering.py`
- `../../tests/test_docs_site.py`

## Related Docs

- `../../docs/ARCHITECTURE.md`
- `../../docs/CODEMAP.md`
- `../../docs/PROJECT_CONTEXT.md`
- `../../docs/data/agent_eval/`

## Agent Notes

Future agents may add typed eval packs or adapters incrementally. They must not
build a universal arbitrary-agent judge or hard-code exact sample agent names.
