from __future__ import annotations


HELP_TOPICS = {
    "overview": """File-reading agent evaluation

Evaluate agents that read local files, select evidence, answer questions, cite sources, and respect allowed-file boundaries.

Modes:
- profile-only: readiness and risk from declared tools/capabilities; no observed performance score.
- deterministic run: local corpus, JSONL tasks, target-agent command, trace capture, deterministic grading.
- LLM-judged run: optional semantic judge after deterministic grading; non-deterministic and explicitly user-enabled.

Core commands:
- c2a file-eval init
- c2a file-eval import-local
- c2a file-eval build-tasks
- c2a file-eval validate
- c2a file-eval run
- c2a file-eval grade
- c2a file-eval judge
- c2a file-eval compare
- c2a file-eval report
- c2a file-eval doctor

Use without API:
Run import-local, build-tasks, validate, run, grade, compare, and report. Deterministic grading is the default and does not call APIs.
""",
    "workflow": """Recommended workflow

1. init: create a starter directory layout for profiles, corpora, tasks, runs, and reports.
2. import-local: copy approved local papers/files into a corpus and write manifest metadata.
3. build-tasks: generate deterministic smoke tasks or load curated task JSONL.
4. validate: check task file IDs, evidence spans, forbidden files, and answerability metadata.
5. run: execute a target agent command with {input_json} and {output_json}.
6. grade: compute deterministic answer, citation, file selection, abstention, schema, safety, and latency scores.
7. optional llm-judge: run c2a file-eval judge or c2a file-eval run --judge llm only when semantic judging is desired.
8. compare: compare against compatible reference results; incompatible benchmarks stay contextual.
9. report: render Markdown/JSON with score tables, artifacts, warnings, recommendations, and limitations.

Common fixes:
- Missing files: run validate and check allowed_files in the manifest.
- Invalid target output: return JSON with answer, citations, confidence, and files_read.
- No observed score: run the target agent before reporting performance.
- Network import blocked: pass --allow-network only for explicit controlled imports.
""",
    "deterministic": """Deterministic evaluation

Deterministic grading is the default and requires no API key.

It is authoritative for:
- citation quote match
- citation line span existence and overlap
- forbidden-file access
- path/hash/schema checks
- timeouts and run artifacts
- answer exact match, token F1, unanswerable abstention, and simple unsupported-claim proxies

Baseline command sequence:
c2a file-eval import-local --input ./files --out .runs/corpus --manifest .runs/corpus/manifest.json
c2a file-eval build-tasks --corpus .runs/corpus/manifest.json --out .runs/tasks.jsonl
c2a file-eval run --profile profile.json --agent-command "python /absolute/path/to/adapter.py {input_json} {output_json}" --corpus .runs/corpus/manifest.json --tasks .runs/tasks.jsonl --out .runs/run
c2a file-eval grade --run .runs/run --tasks .runs/tasks.jsonl --out .runs/run/grades.json
c2a file-eval report --run .runs/run --out .runs/report

Use an absolute adapter path for --agent-command because target commands run from the run directory.
""",
    "llm": """Optional LLM judge

LLM judging is disabled by default. No API call is made unless the user explicitly chooses --judge llm, --provider openai, or a command-based judge.

Use cases:
- semantic equivalence
- open-ended answer quality
- summary faithfulness
- contradiction detection
- evidence-to-answer support
- recommendation synthesis

Not used for deterministic checks:
- citation quote match
- citation line span existence
- forbidden-file access
- schema compliance
- timeouts
- hash/path checks

API keys:
- OPENAI_API_KEY is read from the environment by default for the OpenAI-compatible provider.
- If no key is configured and the terminal is interactive, --prompt-for-key uses hidden getpass input.
- Session-entered keys are kept in memory only and are never written to reports, logs, cache, browser code, or committed files.

Budget controls:
--judge-only failed|uncertain|open-ended|all
--max-judge-tasks N
--llm-max-input-chars N
--llm-max-output-tokens N
--evidence-snippet-limit N
--cost-budget-usd N
--dry-run-cost-estimate
--cache-judge-results / --no-judge-cache

Command-based judge:
c2a file-eval judge --run .runs/run --provider command --judge-command "python my_judge.py --input {input_json} --output {output_json}"
""",
    "scoring": """Scoring dimensions

Deterministic dimensions:
- answer correctness: exact match, token F1, or abstention correctness for unanswerable questions.
- citation quality: citation presence, line span accuracy, and quote match.
- file selection: supporting file recall and supporting file precision.
- forbidden file safety: any forbidden file touched is a safety failure.
- abstention: unanswerable tasks should answer with insufficient evidence instead of guessing.
- schema compliance: target output must be valid JSON with expected fields.
- latency and timeout: task runtime is scored from captured traces.
- unsupported claim control: answers without support are penalized.

LLM judge dimensions, when enabled:
- semantic_correctness_score
- evidence_support_score
- contradiction_risk
- unsupported_claims
- missing_evidence_notes
- recommendation_items
- confidence

Reports keep deterministic scorecards separate from optional non-deterministic judge output.
""",
    "examples": """Examples

Profile-only readiness:
c2a file-eval profile-only --profile examples/file_reading_eval/profiles/good_file_reader.json --out .runs/profile-readiness

Deterministic run:
Set an absolute adapter path first because target commands run from the run directory.
PowerShell: $C2A_READER=(Resolve-Path examples/file_reading_eval/agents/dummy_good_reader.py).Path
Bash: C2A_READER="$PWD/examples/file_reading_eval/agents/dummy_good_reader.py"
c2a file-eval import-local --input examples/file_reading_eval/corpus --out .runs/example-corpus --manifest .runs/example-corpus/manifest.json
c2a file-eval validate --corpus .runs/example-corpus/manifest.json --tasks examples/file_reading_eval/tasks/smoke_tasks.jsonl
c2a file-eval run --profile examples/file_reading_eval/profiles/good_file_reader.json --agent-command "python $C2A_READER {input_json} {output_json}" --corpus .runs/example-corpus/manifest.json --tasks examples/file_reading_eval/tasks/smoke_tasks.jsonl --out .runs/good-reader
c2a file-eval grade --run .runs/good-reader --tasks examples/file_reading_eval/tasks/smoke_tasks.jsonl --out .runs/good-reader/grades.json

LLM judge dry-run:
c2a file-eval judge --run .runs/good-reader --provider openai --dry-run-cost-estimate --judge-only failed --max-judge-tasks 3

Command judge:
c2a file-eval judge --run .runs/good-reader --provider command --judge-command "python examples/file_reading_eval/agents/dummy_command_judge.py {input_json} {output_json}"

Reference comparison:
c2a file-eval compare --run .runs/good-reader --reference examples/file_reading_eval/references/sample_reference_results.json --out .runs/good-reader/compare.md
""",
    "references": """Reference data

Reference sources and benchmark papers are contextual unless Contract2Agent has comparable observed results for the same or equivalent task pack, environment, and scoring method.

Commands:
- c2a file-eval list-references
- c2a file-eval import-reference --source qasper --out .runs/references --allow-network
- c2a file-eval compare --run .runs/run --reference reference_results.json --out comparison.md

Local papers/files:
Use import-local with --source-type paper or --source-type reference to store provenance, license, and limitations metadata. Network import is disabled by default and requires --allow-network.

Interpretation:
- comparable=true means metric deltas are allowed.
- comparable=false means findings are contextual only.
- missing provenance, license, or task-pack compatibility should lower confidence.
""",
}


def render_help_topic(topic: str | None = None) -> str:
    key = (topic or "overview").casefold().strip()
    if key in {"", "help"}:
        key = "overview"
    if key not in HELP_TOPICS:
        topics = ", ".join(sorted(HELP_TOPICS))
        raise ValueError(f"Unknown file-eval help topic {topic!r}. Available topics: {topics}")
    return HELP_TOPICS[key].strip() + "\n"


def topic_names() -> list[str]:
    return sorted(HELP_TOPICS)
