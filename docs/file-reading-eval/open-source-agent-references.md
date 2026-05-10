# Open-Source Agent References

This page records external open-source file-reading agents that are useful for
Contract2Agent task design, adapter design, and capability profiling. These
references are contextual. They do not become observed performance evidence
until the agent is run through `c2a file-eval run` on a documented corpus and
task pack.

## Selected Reference: PaperQA2

Repository: <https://github.com/Future-House/paper-qa>

PaperQA2 is a good first reference for the file-reading adapter because it is an
open-source agentic RAG system focused on reading local scientific documents,
retrieving evidence, and answering with citations. Its README documents support
for PDFs, text files, Microsoft Office documents, source code files, local
indexes, configurable source limits, code/HTML inputs, multimodal document
reading, and manifest metadata. The GitHub repository is public and identifies
the license as Apache-2.0.

## Open-Source Content Inventory

The upstream repository exposes these relevant content groups:

- Top-level project content: `.github`, `docs`, `packages`, `src/paperqa`,
  `tests`, `README.md`, `LICENSE`, `CITATION.cff`, `CONTRIBUTING.md`,
  `pyproject.toml`, and `uv.lock`.
- Core package content under `src/paperqa`: `agents`, `clients`, `configs`,
  `contrib`, `sources`, `core.py`, `docs.py`, `llms.py`, `paths.py`,
  `prompts.py`, `readers.py`, `settings.py`, `types.py`, and `utils.py`.
- Agent files under `src/paperqa/agents`: `env.py`, `helpers.py`, `main.py`,
  `models.py`, `search.py`, and `tools.py`.
- Bundled settings under `src/paperqa/configs`: `high_quality`, `fast`,
  `wikicrow`, `contracrow`, `debug`, OpenAI tier limit settings, OpenReview,
  and clinical-trial search settings.
- Reader packages under `packages`: `paper-qa-docling`,
  `paper-qa-nemotron`, `paper-qa-pymupdf`, and `paper-qa-pypdf`.
- Docs and reference metadata: tutorials plus
  `docs/2024-10-16_litqa2-splits.json5`.
- Tests and fixtures: cassettes, stub data, agent tests, CLI tests, client
  tests, clinical-trial tests, config tests, PaperQA behavior tests, and utility
  tests.

Only metadata, profile information, and adapter guidance are mirrored in this
repository. Upstream code, datasets, and experiment outputs are not vendored.

## How This Enriches File-Reading Eval

PaperQA2 suggests concrete evaluation improvements:

- Add adapter coverage for document-level and page-level citations that must be
  mapped to Contract2Agent line-level citation spans before deterministic
  citation graders can pass.
- Add task families for PDF reading, Office document reading, source-code/HTML
  lookup, table and figure robustness, local index reuse, source limit behavior,
  and metadata-manifest accuracy.
- Add safety checks for recursive indexing, generated index caches, external
  metadata services, LLM calls, embedding calls, and home-directory cache
  locations.
- Use manifest metadata when possible so evaluation does not depend on LLM-based
  metadata inference.
- Keep optional network behavior outside the default dependency-free path.

## Adapter Boundary

A future PaperQA2 adapter should remain a black-box target command that reads
Contract2Agent's `TargetAgentInput` JSON and writes `TargetAgentOutput` JSON.
It should:

- Point PaperQA2 at the copied corpus directory, not the original workspace.
- Keep `PQA_HOME` and generated indexes under the run directory.
- Restrict indexed files to `allowed_files` from the corpus manifest.
- Report the final answer, files read or indexed, and normalized citations.
- Mark citation granularity honestly when only document or page citations are
  available.
- Require explicit local configuration for metadata, LLM, and embedding calls.

## Claims Not Imported

The upstream project and papers describe benchmark and research results. Those
claims are not imported as Contract2Agent scores. They can inform task design,
but direct comparison requires the same task pack, scoring method, environment,
and a stored observed run.
