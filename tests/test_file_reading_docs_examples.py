from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

from contract2agent.evaluation.file_reading import (
    FileAccessTrace,
    grade_run,
    grade_task,
    import_local_corpus,
    load_tasks_jsonl,
    run_file_reading_eval,
    validate_target_output,
    validate_tasks,
)
from contract2agent.evaluation.file_reading.help import render_help_topic


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = ROOT / "examples" / "file_reading_eval"
DOCS_ROOT = ROOT / "docs" / "file-reading-eval"


def test_file_reading_sample_json_files_parse() -> None:
    json_files = sorted(EXAMPLE_ROOT.glob("**/*.json"))

    assert json_files
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))


def test_file_reading_sample_tasks_validate_against_imported_corpus(tmp_path: Path) -> None:
    manifest = import_local_corpus(
        EXAMPLE_ROOT / "corpus",
        tmp_path / "sample_corpus",
        tmp_path / "manifest.json",
    )
    tasks = load_tasks_jsonl(EXAMPLE_ROOT / "tasks" / "sample_tasks.jsonl")

    assert validate_tasks(manifest, tasks) == []


def test_file_reading_sample_target_outputs_are_valid_json_outputs() -> None:
    for path in sorted((EXAMPLE_ROOT / "target_outputs").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        output = validate_target_output(data)

        assert output.schema_valid, (path.name, output.errors)


def test_file_reading_report_examples_are_safe_and_complete() -> None:
    report_json = EXAMPLE_ROOT / "expected_reports" / "deterministic_report.example.json"
    report_md = EXAMPLE_ROOT / "expected_reports" / "deterministic_report.example.md"
    data = json.loads(report_json.read_text(encoding="utf-8"))
    encoded = json.dumps(data, sort_keys=True)
    markdown = report_md.read_text(encoding="utf-8").casefold()

    assert data["sample"] is True
    assert not re.search(r"\b[A-Za-z]:[\\/]", encoded)
    assert not re.search(r"(?<![A-Za-z0-9])/(?:Users|home|tmp|var)/", encoded)
    assert "OPENAI_API_KEY=" not in encoded
    assert "sk-" not in encoded
    assert not re.search(r"(?i)\b(password|token|secret)\s*[:=]", encoded)
    for required in ("score", "evidence", "failure modes", "recommended fixes"):
        assert required in markdown


def test_file_reading_committed_examples_do_not_contain_local_paths_or_keys() -> None:
    for path in EXAMPLE_ROOT.glob("**/*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")

        assert not re.search(r"\b[A-Za-z]:[\\/]", text), path
        assert not re.search(r"(?<![A-Za-z0-9])/(?:Users|home|tmp|var)/", text), path
        assert "sk-" not in text, path
        assert not re.search(r"(?i)\b(api[_-]?key|token|password|secret)\s*[:=]", text), path


def test_file_reading_cli_guide_documents_existing_commands() -> None:
    guide = (DOCS_ROOT / "cli-guide.md").read_text(encoding="utf-8")
    required_commands = [
        "python -m contract2agent.cli --help",
        "python -m contract2agent.cli file-eval --help",
        "python -m contract2agent.cli file-eval doctor --plain",
        "python -m contract2agent.cli file-eval help llm",
        "python -m contract2agent.cli file-eval import-local",
        "python -m contract2agent.cli file-eval validate",
        "python -m contract2agent.cli file-eval run",
        "python -m contract2agent.cli file-eval grade",
        "python -m contract2agent.cli file-eval report",
        "python -m contract2agent.cli file-eval compare",
    ]

    for command in required_commands:
        assert command in guide

    for args in (
        ["--help"],
        ["file-eval", "--help"],
        ["file-eval", "help", "llm"],
        ["file-eval", "doctor", "--plain"],
    ):
        completed = subprocess.run(
            [sys.executable, "-m", "contract2agent.cli", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert completed.returncode == 0, completed.stderr


def test_documented_agent_commands_use_absolute_adapter_path_guidance() -> None:
    doc_paths = [
        ROOT / "README.md",
        ROOT / "README.zh-CN.md",
        EXAMPLE_ROOT / "README.md",
        *sorted(DOCS_ROOT.glob("*.md")),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    help_examples = render_help_topic("examples")
    help_deterministic = render_help_topic("deterministic")

    assert "run directory" in combined
    assert "absolute adapter path" in combined
    assert "absolute adapter path" in help_examples
    assert "absolute adapter path" in help_deterministic
    assert '--agent-command "python examples/file_reading_eval/agents/' not in combined
    assert '--agent-command "python examples/file_reading_eval/agents/' not in help_examples
    assert '--agent-command "python adapter.py' not in help_deterministic


def test_file_reading_docs_reference_existing_sample_files() -> None:
    for name in (
        "README.md",
        "README.zh-CN.md",
        "cli-guide.md",
        "cli-guide.zh-CN.md",
        "sample-run.md",
        "sample-run.zh-CN.md",
        "report-examples.md",
        "report-examples.zh-CN.md",
    ):
        assert (DOCS_ROOT / name).exists()

    for doc in sorted(DOCS_ROOT.glob("*.md")):
        text = _strip_fenced_code(doc.read_text(encoding="utf-8"))
        for target in _markdown_links(text):
            if _ignore_link(target):
                continue
            link_path = unquote(target.split("#", 1)[0]).strip("<>")
            assert (doc.parent / link_path).resolve().exists(), (doc.name, target)

    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOCS_ROOT.glob("*.md"))
    required_paths = [
        "examples/file_reading_eval/README.md",
        "examples/file_reading_eval/tasks/sample_tasks.jsonl",
        "examples/file_reading_eval/corpus/contract_policy.md",
        "examples/file_reading_eval/corpus/incident_notes.md",
        "examples/file_reading_eval/corpus/payment_terms.md",
        "examples/file_reading_eval/corpus/distractor_release_notes.md",
        "examples/file_reading_eval/target_outputs/good_output.json",
        "examples/file_reading_eval/target_outputs/bad_citation_output.json",
        "examples/file_reading_eval/target_outputs/hallucinated_output.json",
        "examples/file_reading_eval/target_outputs/no_citation_output.json",
        "examples/file_reading_eval/expected_reports/deterministic_report.example.md",
        "examples/file_reading_eval/expected_reports/deterministic_report.example.json",
    ]
    for path in required_paths:
        assert path in combined
        assert (ROOT / path).exists()


def test_file_reading_readmes_and_gitignore_link_examples_safely() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    zh_readme = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    for target in (
        "docs/file-reading-eval/README.md",
        "docs/file-reading-eval/cli-guide.md",
        "docs/file-reading-eval/sample-run.md",
        "docs/file-reading-eval/report-examples.md",
    ):
        assert target in readme
        assert (ROOT / target).exists()

    for target in (
        "docs/file-reading-eval/README.zh-CN.md",
        "docs/file-reading-eval/cli-guide.zh-CN.md",
        "docs/file-reading-eval/sample-run.zh-CN.md",
        "docs/file-reading-eval/report-examples.zh-CN.md",
    ):
        assert target in zh_readme
        assert (ROOT / target).exists()

    assert "/.runs/" in gitignore
    assert "/file_reading_eval/" in gitignore
    assert ".judge_cache/" in gitignore
    assert "examples/file_reading_eval" not in gitignore
    for path in EXAMPLE_ROOT.glob("**/*"):
        assert ".runs" not in path.parts
        assert ".judge_cache" not in path.parts


def test_file_reading_docs_mark_llm_judge_optional_and_references_contextual() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOCS_ROOT.glob("*.md")).casefold()

    assert "llm judging is disabled by default" in combined
    assert "optional" in combined
    assert "api key" in combined
    assert "contextual" in combined
    assert "reference paper does not equal observed score" in combined
    assert "benchmark description does not equal agent performance" in combined


def test_file_reading_sample_outputs_exercise_deterministic_grader(tmp_path: Path) -> None:
    manifest = import_local_corpus(
        EXAMPLE_ROOT / "corpus",
        tmp_path / "sample_corpus",
        tmp_path / "manifest.json",
    )
    task = {
        loaded.task_id: loaded
        for loaded in load_tasks_jsonl(EXAMPLE_ROOT / "tasks" / "sample_tasks.jsonl")
    }["sample_refund_notice_period"]

    good = _grade_output("good_output.json", manifest, task)
    bad_citation = _grade_output("bad_citation_output.json", manifest, task)
    hallucinated = _grade_output("hallucinated_output.json", manifest, task)
    no_citation = _grade_output("no_citation_output.json", manifest, task)

    assert good.total_score > 0.8
    assert "citation_quote_mismatch" in bad_citation.failures
    assert "citation_span_mismatch" in bad_citation.failures
    assert "answer_incorrect" in hallucinated.failures
    assert "high_unsupported_claim_rate" in hallucinated.failures
    assert "missing_citation" in no_citation.failures


def test_file_reading_sample_run_walkthrough_dummy_agent_scores_well(tmp_path: Path) -> None:
    manifest = import_local_corpus(
        EXAMPLE_ROOT / "corpus",
        tmp_path / "sample_corpus",
        tmp_path / "manifest.json",
    )
    run_dir = tmp_path / "sample_good_run"

    run_file_reading_eval(
        profile_path=EXAMPLE_ROOT / "profiles" / "cautious_reader_profile.json",
        agent_command=(
            f"{sys.executable} {EXAMPLE_ROOT / 'agents' / 'dummy_good_reader.py'} "
            "{input_json} {output_json}"
        ),
        corpus_manifest_path=tmp_path / "manifest.json",
        tasks_path=EXAMPLE_ROOT / "tasks" / "sample_tasks.jsonl",
        time_budget_seconds=30,
        max_tasks=4,
        seed=7,
        out_dir=run_dir,
    )
    _grades, scorecard = grade_run(
        run_dir,
        EXAMPLE_ROOT / "tasks" / "sample_tasks.jsonl",
        out=run_dir / "grades.json",
    )

    assert manifest.corpus_id
    assert scorecard.overall_score is not None
    assert scorecard.overall_score > 0.8


def _grade_output(name: str, manifest, task):  # type: ignore[no-untyped-def]
    output_data = json.loads((EXAMPLE_ROOT / "target_outputs" / name).read_text(encoding="utf-8"))
    output = validate_target_output(output_data)
    return grade_task(
        task,
        output,
        manifest,
        FileAccessTrace(
            task_id=task.task_id,
            files_read=output.files_read,
            files_referenced=[citation.file_id for citation in output.citations],
            stdout_path="stdout.txt",
            stderr_path="stderr.txt",
            start_time="2026-05-05T00:00:00+00:00",
            end_time="2026-05-05T00:00:01+00:00",
            duration_seconds=1.0,
            timeout=False,
            command=["sample"],
            exit_code=0,
        ),
    )


def _markdown_links(text: str) -> list[str]:
    pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    return [match.group(1).strip() for match in pattern.finditer(text)]


def _strip_fenced_code(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def _ignore_link(target: str) -> bool:
    return (
        not target
        or target.startswith("#")
        or target.startswith(("http://", "https://", "mailto:", "tel:"))
        or bool(re.match(r"^[a-z][a-z0-9+.-]*:", target.casefold()))
    )
