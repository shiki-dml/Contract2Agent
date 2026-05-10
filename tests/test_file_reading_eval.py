from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from contract2agent.evaluation.file_reading import (
    Citation,
    EvidenceSpan,
    FileAccessTrace,
    FileReadingAgentProfile,
    FileReadingTask,
    ReferenceResult,
    compare_with_references,
    curated_reference_sources,
    grade_run,
    grade_task,
    import_local_corpus,
    load_tasks_jsonl,
    render_profile_only_report,
    to_dict,
    validate_target_output,
    validate_tasks,
    write_profile_only_report,
    write_run_report,
    write_tasks_jsonl,
)
from contract2agent.evaluation.file_reading.graders import (
    citation_quote_matches,
    load_grades,
)
from contract2agent.evaluation.file_reading.runner import run_file_reading_eval


ROOT = Path(__file__).resolve().parents[1]


def test_file_reading_agent_profile_serialization() -> None:
    profile = _profile()

    data = json.loads(json.dumps(to_dict(profile)))

    assert data["agent_id"] == "reader"
    assert data["can_read_files"] is True
    assert data["citation_support"] == "line_citations"


def test_corpus_manifest_creation_from_temp_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "doc.md").write_text("# Title\nAnswer: Alpha\n", encoding="utf-8")

    manifest = import_local_corpus(source, tmp_path / "corpus")

    assert manifest.documents
    assert manifest.allowed_files == ["doc.md"]
    assert manifest.hash
    assert manifest.documents[0].section_headings == ["Title"]


def test_local_importer_skips_unsafe_files_and_pycache(tmp_path: Path) -> None:
    source = tmp_path / "source"
    pycache = source / "__pycache__"
    pycache.mkdir(parents=True)
    (source / ".env").write_text("TOKEN=secret", encoding="utf-8")
    (pycache / "cached.pyc").write_bytes(b"cache")
    (source / "safe.txt").write_text("public", encoding="utf-8")

    manifest = import_local_corpus(source, tmp_path / "corpus")

    assert [document.relative_path for document in manifest.documents] == ["safe.txt"]
    skipped = "\n".join(manifest.metadata["skipped"])
    assert ".env" in skipped
    assert "__pycache__" in skipped


def test_document_record_line_counts_hashes_and_sanitized_path(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "doc.txt").write_text("one\ntwo\n", encoding="utf-8")

    manifest = import_local_corpus(source, tmp_path / "corpus")
    record = manifest.documents[0]

    assert record.line_count == 2
    assert len(record.sha256) == 64
    assert record.absolute_path_sanitized == "<corpus_root>/doc.txt"


def test_file_reading_task_jsonl_load_and_validate(tmp_path: Path) -> None:
    manifest, task = _manifest_and_task(tmp_path)
    tasks_path = tmp_path / "tasks.jsonl"
    write_tasks_jsonl([task], tasks_path)

    loaded = load_tasks_jsonl(tasks_path)
    errors = validate_tasks(manifest, loaded)

    assert loaded[0].task_id == task.task_id
    assert errors == []


def test_task_validation_catches_bad_evidence_spans(tmp_path: Path) -> None:
    manifest, task = _manifest_and_task(tmp_path)
    task.expected_citations = [
        EvidenceSpan(file_id="missing.md", line_start=1, line_end=1, quote="Missing"),
        EvidenceSpan(file_id="doc.md", line_start=3, line_end=2, quote="Answer: Alpha"),
        EvidenceSpan(file_id="doc.md", line_start=2, line_end=2, quote="Answer: Beta"),
    ]

    errors = validate_tasks(manifest, [task])
    combined = "\n".join(errors)

    assert "expected_citations[0].file_id not in manifest" in combined
    assert "expected_citations[1] has invalid line range" in combined
    assert "expected_citations[2] quote does not match manifest text" in combined


def test_task_validation_reports_non_integer_evidence_lines(tmp_path: Path) -> None:
    manifest, task = _manifest_and_task(tmp_path)
    tasks_path = tmp_path / "tasks.jsonl"
    data = to_dict(task)
    data["expected_citations"] = [
        {"file_id": "doc.md", "line_start": "first", "line_end": 2, "quote": "Answer: Alpha"}
    ]
    tasks_path.write_text(json.dumps(data) + "\n", encoding="utf-8")

    loaded = load_tasks_jsonl(tasks_path)
    errors = validate_tasks(manifest, loaded)

    assert any("expected_citations[0].line_start must be an integer" in error for error in errors)


def test_citation_span_checker_passes_on_exact_quote(tmp_path: Path) -> None:
    manifest, _task = _manifest_and_task(tmp_path)
    citation = Citation(file_id="doc.md", line_start=2, line_end=2, quote="Answer: Alpha")

    assert citation_quote_matches(citation, manifest) is True


def test_citation_span_checker_fails_on_wrong_quote(tmp_path: Path) -> None:
    manifest, _task = _manifest_and_task(tmp_path)
    citation = Citation(file_id="doc.md", line_start=2, line_end=2, quote="Answer: Beta")

    assert citation_quote_matches(citation, manifest) is False


def test_supporting_file_recall_precision_grader(tmp_path: Path) -> None:
    manifest, task = _manifest_and_task(tmp_path)
    output = validate_target_output(
        {
            "answer": "Alpha",
            "citations": [{"file_id": "doc.md", "line_start": 2, "line_end": 2, "quote": "Answer: Alpha"}],
            "files_read": ["doc.md", "extra.md"],
        }
    )

    grade = grade_task(task, output, manifest, _trace("task", files_read=["doc.md", "extra.md"]))

    assert grade.supporting_file_recall == 1.0
    assert grade.supporting_file_precision == 0.5


def test_forbidden_file_violation_grader(tmp_path: Path) -> None:
    manifest, task = _manifest_and_task(tmp_path)
    task.forbidden_files = ["secret.txt"]
    output = validate_target_output({"answer": "No", "citations": [], "files_read": ["secret.txt"]})

    grade = grade_task(task, output, manifest, _trace("task", files_read=["secret.txt"]))

    assert grade.forbidden_file_violation is True
    assert "forbidden_file_violation" in grade.failures


def test_unanswerable_abstention_grader(tmp_path: Path) -> None:
    manifest, _task = _manifest_and_task(tmp_path)
    task = FileReadingTask(
        task_id="u1",
        task_type="unanswerable_question",
        question="Missing?",
        allowed_files=manifest.allowed_files,
        unanswerable=True,
    )
    output = validate_target_output({"answer": "Insufficient evidence.", "citations": [], "files_read": []})

    grade = grade_task(task, output, manifest, _trace("u1"))

    assert grade.unanswerable_abstention_score == 1.0


def test_output_schema_validation() -> None:
    valid = validate_target_output(
        {
            "answer": "Alpha",
            "citations": [{"file_id": "doc.md", "line_start": 1, "line_end": 1, "quote": "Alpha"}],
            "confidence": 0.8,
            "files_read": ["doc.md"],
        }
    )
    invalid = validate_target_output({"answer": 123, "citations": "missing"})

    assert valid.schema_valid is True
    assert invalid.schema_valid is False
    assert invalid.errors


def test_output_schema_validation_handles_malformed_citation_objects() -> None:
    invalid = validate_target_output(
        {
            "answer": "Alpha",
            "citations": [{"line_start": "first", "line_end": 1, "quote": 42}],
        }
    )

    assert invalid.schema_valid is False
    assert invalid.citations[0].file_id == ""
    assert invalid.citations[0].line_start is None
    assert any("file_id" in error for error in invalid.errors)
    assert any("line_start" in error for error in invalid.errors)
    assert any("quote" in error for error in invalid.errors)


def test_dummy_target_agent_run_and_artifacts_via_cli(tmp_path: Path) -> None:
    manifest, task = _manifest_and_task(tmp_path)
    paths = _write_profile_task_and_dummy(tmp_path, [task])
    run_dir = tmp_path / "run"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contract2agent.cli",
            "file-eval",
            "run",
            "--profile",
            str(paths["profile"]),
            "--agent-command",
            f"{sys.executable} {paths['dummy']} {{input_json}} {{output_json}}",
            "--corpus",
            str(paths["manifest"]),
            "--tasks",
            str(paths["tasks"]),
            "--time-budget-seconds",
            "5",
            "--max-tasks",
            "1",
            "--seed",
            "7",
            "--out",
            str(run_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert (run_dir / "run.json").exists()
    assert (run_dir / "run.jsonl").exists()
    run_data = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run_data["metadata"]["observed_run"] is True
    assert list(run_data["outputs"]) == [task.task_id]
    assert manifest.corpus_id


def test_max_task_budget_respected(tmp_path: Path) -> None:
    manifest, task = _manifest_and_task(tmp_path)
    second = FileReadingTask(
        task_id="task2",
        task_type="quote_lookup",
        question=task.question,
        allowed_files=manifest.allowed_files,
        supporting_files=["doc.md"],
        gold_answer="Answer: Alpha",
    )
    paths = _write_profile_task_and_dummy(tmp_path, [task, second])

    run = run_file_reading_eval(
        profile_path=paths["profile"],
        agent_command=f"{sys.executable} {paths['dummy']} {{input_json}} {{output_json}}",
        corpus_manifest_path=paths["manifest"],
        tasks_path=paths["tasks"],
        time_budget_seconds=5,
        max_tasks=1,
        seed=0,
        out_dir=tmp_path / "run",
    )

    assert len(run.tasks) == 1


def test_grade_artifacts_created(tmp_path: Path) -> None:
    paths = _run_dummy(tmp_path)
    grade_path = tmp_path / "grades.json"

    grades, scorecard = grade_run(paths["run"], paths["tasks"], out=grade_path)
    loaded_grades, loaded_scorecard = load_grades(grade_path)

    assert grade_path.exists()
    assert grades[0].total_score > 0.8
    assert scorecard.overall_score is not None
    assert loaded_grades[0].task_id == grades[0].task_id
    assert loaded_scorecard is not None


def test_report_markdown_includes_scores_and_recommendations(tmp_path: Path) -> None:
    paths = _run_dummy(tmp_path)
    grade_run(paths["run"], paths["tasks"], out=Path(paths["run"]) / "grades.json")

    outputs = write_run_report(paths["run"], report_format="md,json", out_dir=tmp_path / "report")
    markdown = outputs["markdown"].read_text(encoding="utf-8")

    assert "## Scores By Dimension" in markdown
    assert "## Recommended Changes" in markdown
    assert "Overall observed score" in markdown


def test_profile_only_mode_does_not_output_observed_score(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(to_dict(_profile())), encoding="utf-8")

    paths = write_profile_only_report(profile_path, tmp_path / "profile_report")
    markdown = paths["markdown"].read_text(encoding="utf-8")
    data = json.loads(paths["json"].read_text(encoding="utf-8"))

    assert "No observed performance score because no agent run was executed." in markdown
    assert data["observed_performance_score"] is None


def test_reference_registry_lists_contextual_sources() -> None:
    sources = curated_reference_sources()

    assert {"qasper", "squad", "hotpotqa", "docvqa", "longbench", "paperqa2"}.issubset(
        {source.source_id for source in sources}
    )
    assert all(any("Contextual reference only" in item for item in source.limitations) for source in sources)


def test_paperqa2_reference_is_contextual_open_source_metadata() -> None:
    paperqa2 = next(source for source in curated_reference_sources() if source.source_id == "paperqa2")

    assert paperqa2.source_type == "open_source_agent_reference"
    assert paperqa2.license == "Apache-2.0"
    assert paperqa2.metrics_available == []
    assert paperqa2.reliability <= 0.25
    assert "citation_required_qa" in paperqa2.applicable_task_types
    assert any("Contextual reference only" in item for item in paperqa2.limitations)
    assert any("No upstream benchmark claim" in item for item in paperqa2.limitations)


def test_benchmark_references_do_not_become_direct_scores() -> None:
    sources = curated_reference_sources()

    assert all(source.reliability <= 0.25 for source in sources)
    assert all(not source.metrics_available or source.source_type == "benchmark_reference" for source in sources)
    assert all("score" not in " ".join(source.notes).casefold() for source in sources)


def test_comparison_marks_incompatible_references_contextual_only(tmp_path: Path) -> None:
    paths = _run_dummy(tmp_path)
    reference_path = tmp_path / "reference_results.json"
    reference_path.write_text(
        json.dumps(
            [
                to_dict(
                    ReferenceResult(
                        reference_result_id="ref1",
                        source_id="qasper",
                        agent_or_model="reference",
                        task_pack_id="different_pack",
                        metrics={"overall_score": 0.9},
                        environment="documented",
                        scoring_method="different_method",
                        comparable_conditions=False,
                    )
                )
            ]
        ),
        encoding="utf-8",
    )

    report = compare_with_references(paths["run"], reference_path, out=tmp_path / "compare.md")

    assert report.comparable is False
    assert "contextual only" in report.markdown_summary
    assert not report.metric_deltas


def test_cli_help_includes_file_eval_command() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "contract2agent.cli", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "file-eval" in completed.stdout


def test_file_eval_help_lists_subcommands() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "contract2agent.cli", "file-eval", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "import-local" in completed.stdout
    assert "run" in completed.stdout
    assert "profile-only" in completed.stdout


def test_user_provided_paper_import_writes_reference_source(tmp_path: Path) -> None:
    paper = tmp_path / "paper.md"
    paper.write_text("# Method\nEvidence text\n", encoding="utf-8")

    manifest = import_local_corpus(
        paper,
        tmp_path / "paper_corpus",
        source_type="paper",
        title="User Paper",
    )

    reference_path = tmp_path / "paper_corpus" / "reference_source.json"
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    assert manifest.source_type == "paper"
    assert reference["title"] == "User Paper"
    assert reference["metrics_available"] == []


def test_render_profile_only_report_message() -> None:
    markdown = render_profile_only_report(_profile())

    assert "No observed performance score because no agent run was executed." in markdown
    assert "profile declarations only" in markdown


def _profile() -> FileReadingAgentProfile:
    return FileReadingAgentProfile(
        agent_id="reader",
        name="Reader",
        description="Reads local files and cites lines.",
        declared_capabilities=["read files", "cite lines"],
        tools=["file_read", "search_local"],
        tool_permissions=["read_corpus"],
        can_list_files=True,
        can_search_files=True,
        can_read_files=True,
        citation_support="line_citations",
        output_schema_support="json",
        trace_support="files_read",
        policy_constraints=["allowed corpus only"],
    )


def _manifest_and_task(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir(exist_ok=True)
    (source / "doc.md").write_text("# Title\nAnswer: Alpha\n", encoding="utf-8")
    manifest = import_local_corpus(source, tmp_path / "corpus", tmp_path / "manifest.json")
    span = EvidenceSpan(
        file_id="doc.md",
        line_start=2,
        line_end=2,
        quote="Answer: Alpha",
        label="answer",
        required=True,
    )
    task = FileReadingTask(
        task_id="task1",
        task_type="quote_lookup",
        question="What answer is listed?",
        instructions="Answer and cite the exact line.",
        allowed_files=manifest.allowed_files,
        forbidden_files=manifest.forbidden_files,
        supporting_files=["doc.md"],
        gold_answer="Alpha",
        gold_answer_aliases=["Answer: Alpha"],
        gold_evidence_spans=[span],
        expected_citations=[span],
    )
    return manifest, task


def _trace(
    task_id: str,
    *,
    files_read: list[str] | None = None,
    timeout: bool = False,
) -> FileAccessTrace:
    return FileAccessTrace(
        task_id=task_id,
        files_read=files_read or [],
        files_referenced=[],
        stdout_path="stdout.txt",
        stderr_path="stderr.txt",
        start_time="2026-05-05T00:00:00+00:00",
        end_time="2026-05-05T00:00:01+00:00",
        duration_seconds=1.0,
        timeout=timeout,
        command=["dummy"],
        exit_code=0 if not timeout else None,
    )


def _write_profile_task_and_dummy(tmp_path: Path, tasks: list[FileReadingTask]) -> dict[str, Path]:
    profile_path = tmp_path / "profile.json"
    tasks_path = tmp_path / "tasks.jsonl"
    manifest_path = tmp_path / "manifest.json"
    if not manifest_path.exists():
        _manifest_and_task(tmp_path)
    profile_path.write_text(json.dumps(to_dict(_profile()), indent=2), encoding="utf-8")
    write_tasks_jsonl(tasks, tasks_path)
    dummy = tmp_path / "dummy_agent.py"
    dummy.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "import json",
                "import os",
                "import sys",
                "import time",
                "input_path = sys.argv[1]",
                "output_path = sys.argv[2]",
                "mode = os.environ.get('C2A_DUMMY_MODE', 'correct')",
                "payload = json.loads(open(input_path, encoding='utf-8').read())",
                "if mode == 'timeout':",
                "    time.sleep(2)",
                "answer = 'Alpha'",
                "citations = [{'file_id': 'doc.md', 'line_start': 2, 'line_end': 2, 'quote': 'Answer: Alpha'}]",
                "files_read = ['doc.md']",
                "if mode == 'wrong':",
                "    answer = 'Beta'",
                "if mode == 'missing_citation':",
                "    citations = []",
                "if mode == 'forbidden':",
                "    files_read = list(payload.get('forbidden_files') or ['secret.txt'])",
                "json.dump({'answer': answer, 'citations': citations, 'confidence': 0.9, 'files_read': files_read}, open(output_path, 'w', encoding='utf-8'))",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "profile": profile_path,
        "tasks": tasks_path,
        "manifest": manifest_path,
        "dummy": dummy,
    }


def _run_dummy(tmp_path: Path) -> dict[str, Path]:
    _manifest, task = _manifest_and_task(tmp_path)
    paths = _write_profile_task_and_dummy(tmp_path, [task])
    run_dir = tmp_path / "run"
    run_file_reading_eval(
        profile_path=paths["profile"],
        agent_command=f"{sys.executable} {paths['dummy']} {{input_json}} {{output_json}}",
        corpus_manifest_path=paths["manifest"],
        tasks_path=paths["tasks"],
        time_budget_seconds=5,
        max_tasks=1,
        seed=0,
        out_dir=run_dir,
    )
    return {"run": run_dir, "tasks": paths["tasks"]}
