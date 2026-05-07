# file_reading

## Responsibility

This directory implements the specialized `file_reading_agent` evaluation
adapter. It supports local CLI-based corpora, task loading/building, black-box
agent runs, deterministic grading, reference comparison, optional LLM judge
supplements, and reports.

## Functionality

- Import local corpora and record provenance, license, limitations, hashes, and
  sanitized paths.
- Load or build file-reading tasks, including citation, distractor,
  unanswerable, and forbidden-file cases.
- Run target agents as local commands with captured input/output artifacts.
- Grade correctness, citation grounding, file selection, abstention, forbidden
  file access, and schema compliance deterministically.
- Compare reference results only under compatible documented conditions.
- Optionally run LLM or command judges with explicit opt-in, budgets, caching,
  compact inputs, and deterministic fallback.

## Important Files And Entry Points

- `cli.py`, `help.py`: `c2a file-eval` command surface and help topics.
- `corpus.py`, `importers.py`: corpus import and manifest logic.
- `tasks.py`: task models and validation.
- `runner.py`: target command execution and run artifacts.
- `graders.py`: deterministic grading.
- `compare.py`, `references.py`: reference metadata and comparisons.
- `llm_judge.py`: optional judge support.
- `reports.py`, `recommendations.py`, `schema.py`: reports, recommendations, schemas.

## Public Behavior Contracts

- Baseline evaluation must make no API calls.
- Profile-only reports must not claim observed performance.
- LLM judge outputs stay separate from deterministic grades.
- Network import requires explicit `--allow-network`.
- Do not send full corpora, forbidden files, secrets, or unsanitized absolute
  paths to an optional judge.

## Related Tests

- `../../../tests/test_file_reading_eval.py`
- `../../../tests/test_file_reading_llm_judge.py`
- `../../../tests/test_file_reading_docs_examples.py`

## Related Docs

- `../../../docs/file-reading-eval/README.md`
- `../../../docs/file-reading-eval/cli-guide.md`
- `../../../docs/harness/EVAL_MATRIX.md`
- `../../../examples/file_reading_eval/README.md`

## Agent Notes

Future agents may add focused task types, graders, or report details with tests.
Do not weaken path containment, forbidden-file checks, API key handling, or
deterministic fallback behavior.
