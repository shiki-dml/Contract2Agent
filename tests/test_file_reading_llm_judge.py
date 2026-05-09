from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from contract2agent.evaluation.file_reading.graders import grade_run, grade_task, validate_target_output
from contract2agent.evaluation.file_reading.llm_judge import (
    JudgeOptions,
    build_judge_input,
    judge_cache_key,
    resolve_api_key,
    run_judge,
    select_tasks_for_judging,
    validate_judge_output,
)
from contract2agent.evaluation.file_reading.recommendations import (
    prioritized_recommendations_for_grades,
    recommendations_for_grades,
)
from contract2agent.evaluation.file_reading.references import import_reference_source
from contract2agent.evaluation.file_reading.runner import run_file_reading_eval
from contract2agent.evaluation.file_reading.reports import write_run_report
from contract2agent.evaluation.file_reading.schema import (
    EvidenceSpan,
    FileAccessTrace,
    FileReadingAgentProfile,
    FileReadingGrade,
    FileReadingTask,
    to_dict,
)
from contract2agent.evaluation.file_reading.corpus import import_local_corpus
from contract2agent.evaluation.file_reading.tasks import write_tasks_jsonl


ROOT = Path(__file__).resolve().parents[1]


def test_file_eval_help_topics_include_workflow_and_llm() -> None:
    workflow = subprocess.run(
        [sys.executable, "-m", "contract2agent.cli", "file-eval", "help", "workflow"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    llm = subprocess.run(
        [sys.executable, "-m", "contract2agent.cli", "file-eval", "help", "llm"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    scoring = subprocess.run(
        [sys.executable, "-m", "contract2agent.cli", "file-eval", "help", "scoring"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert workflow.returncode == 0, workflow.stderr
    assert all(word in workflow.stdout for word in ("init", "import-local", "build-tasks", "run", "grade", "report"))
    assert llm.returncode == 0, llm.stderr
    assert "disabled by default" in llm.stdout
    assert "OPENAI_API_KEY" in llm.stdout
    assert "deterministic" in llm.stdout
    assert scoring.returncode == 0, scoring.stderr
    for word in ("citation", "file selection", "abstention", "forbidden"):
        assert word in scoring.stdout


def test_file_eval_doctor_json_and_plain_modes() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "contract2agent.cli", "file-eval", "doctor", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    plain = subprocess.run(
        [sys.executable, "-m", "contract2agent.cli", "file-eval", "doctor", "--plain"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    verbose = subprocess.run(
        [sys.executable, "-m", "contract2agent.cli", "file-eval", "doctor", "--verbose"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    data = json.loads(completed.stdout)
    assert data["command"] == "file-eval doctor"
    assert any(check["name"] == "deterministic_default" for check in data["checks"])
    assert plain.returncode == 0, plain.stderr
    assert "\x1b[" not in plain.stdout
    assert "Next commands" not in plain.stdout
    assert verbose.returncode == 0, verbose.stderr
    assert "Artifacts:" in verbose.stdout


def test_deterministic_mode_makes_no_api_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _run_dummy(tmp_path)
    called = False

    def fail_provider(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        raise AssertionError("provider should not be constructed")

    monkeypatch.setattr("contract2agent.evaluation.file_reading.llm_judge.provider_from_options", fail_provider)
    report = run_judge(
        paths["run"],
        paths["tasks"],
        options=JudgeOptions(provider="none", max_judge_tasks=5),
        out=tmp_path / "judge.json",
    )

    assert called is False
    assert report.summary["calls_made"] == 0
    assert all(result.status in {"deterministic_only", "not_selected"} for result in report.results)


def test_llm_mode_requires_explicit_provider_and_key_prompt_is_interactive_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert resolve_api_key(provider="openai", prompt_for_key=False, interactive=False) is None
    with pytest.raises(RuntimeError):
        resolve_api_key(provider="openai", prompt_for_key=True, interactive=False)
    key = resolve_api_key(
        provider="openai",
        prompt_for_key=True,
        interactive=True,
        getpass_func=lambda prompt: "sk-session-only",
    )
    assert key == "sk-session-only"


def test_api_key_not_printed_or_stored_in_judge_report(tmp_path: Path) -> None:
    paths = _run_dummy(tmp_path)
    report_path = tmp_path / "judge.json"
    run_judge(
        paths["run"],
        paths["tasks"],
        options=JudgeOptions(
            provider="openai",
            api_key="sk-secret-value",
            dry_run_cost_estimate=True,
            max_judge_tasks=1,
        ),
        out=report_path,
    )

    assert "sk-secret-value" not in report_path.read_text(encoding="utf-8")


def test_judge_input_omits_full_corpus_forbidden_files_and_absolute_paths(tmp_path: Path) -> None:
    manifest, task = _manifest_and_task(tmp_path)
    task.forbidden_files = ["private_notes.forbidden.md"]
    output = validate_target_output(
        {
            "answer": f"See {tmp_path}\\source\\policy.md for the answer.",
            "citations": [
                {"file_id": "policy.md", "line_start": 3, "line_end": 3, "quote": "Enterprise customers must retain audit logs for 90 days."},
                {"file_id": "private_notes.forbidden.md", "line_start": 1, "line_end": 1, "quote": "secret"},
            ],
            "files_read": ["policy.md", "private_notes.forbidden.md"],
        }
    )
    grade = grade_task(task, output, manifest, _trace(task.task_id, files_read=output.files_read))
    run = _run_object(manifest, task, output)

    judge_input = build_judge_input(run=run, task=task, output=output, grade=grade)
    encoded = json.dumps(to_dict(judge_input), sort_keys=True)

    assert "private_notes.forbidden.md" not in encoded
    assert "Project Nebula" not in encoded
    assert str(tmp_path) not in encoded
    assert "<local_path>" in encoded or "<corpus_root>" in encoded
    assert len(judge_input.cited_snippets) == 1


def test_judge_input_redacts_secret_like_answer_text(tmp_path: Path) -> None:
    manifest, task = _manifest_and_task(tmp_path)
    output = validate_target_output(
        {
            "answer": "The key is OPENAI_API_KEY=sk-testsecret123456789.",
            "citations": [],
            "files_read": ["policy.md"],
        }
    )
    grade = grade_task(task, output, manifest, _trace(task.task_id, files_read=output.files_read))
    run = _run_object(manifest, task, output)

    judge_input = build_judge_input(run=run, task=task, output=output, grade=grade)
    encoded = json.dumps(to_dict(judge_input), sort_keys=True)

    assert "sk-testsecret123456789" not in encoded
    assert "<redacted_secret>" in encoded


def test_judge_output_schema_validation_and_invalid_fallback(tmp_path: Path) -> None:
    valid = validate_judge_output(
        {
            "semantic_correctness_score": 0.8,
            "evidence_support_score": 0.7,
            "contradiction_risk": 0.1,
            "unsupported_claims": [],
            "missing_evidence_notes": [],
            "recommendation_items": ["Tighten evidence support."],
            "confidence": 0.6,
            "rationale": "Valid.",
            "limitations": ["test"],
            "judge_model": "dummy",
            "judge_provider": "command",
            "judge_based": True,
            "deterministic": False,
        },
        provider="command",
        model="dummy",
    )
    assert valid.judge_based is True
    with pytest.raises(ValueError):
        validate_judge_output({"semantic_correctness_score": 2}, provider="command", model="dummy")

    paths = _run_dummy(tmp_path)
    bad_judge = tmp_path / "bad_judge.py"
    bad_judge.write_text(
        "import json, sys\njson.dump({'not': 'valid'}, open(sys.argv[2], 'w', encoding='utf-8'))\n",
        encoding="utf-8",
    )
    report = run_judge(
        paths["run"],
        paths["tasks"],
        options=JudgeOptions(
            provider="command",
            judge_command=f"{sys.executable} {bad_judge} {{input_json}} {{output_json}}",
            judge_only="all",
            max_judge_tasks=1,
        ),
        out=tmp_path / "bad_report.json",
    )

    assert report.deterministic_scorecard["overall_score"] is not None
    assert any(result.status == "judge_failed" for result in report.results)


def test_judge_failure_report_sanitizes_local_absolute_paths(tmp_path: Path) -> None:
    paths = _run_dummy(tmp_path)
    report_path = tmp_path / "judge.json"
    bad_judge = tmp_path / "path_leaking_judge.py"
    bad_judge.write_text(
        "import sys\n"
        f"sys.stderr.write('failed at {tmp_path.as_posix()}/private/input.json')\n"
        "raise SystemExit(2)\n",
        encoding="utf-8",
    )

    run_judge(
        paths["run"],
        paths["tasks"],
        options=JudgeOptions(
            provider="command",
            judge_command=f"{sys.executable} {bad_judge} {{input_json}} {{output_json}}",
            judge_only="all",
            max_judge_tasks=1,
            cache_judge_results=False,
        ),
        out=report_path,
    )
    report_text = report_path.read_text(encoding="utf-8")

    assert tmp_path.as_posix() not in report_text
    assert "<local_path>" in report_text


def test_budget_selection_dry_run_and_cache_key_stability(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _run_dummy(tmp_path)
    grades, _scorecard = grade_run(paths["run"], paths["tasks"])
    tasks = _load_tasks(paths["tasks"])

    selected = select_tasks_for_judging(grades, tasks, judge_only="all", max_judge_tasks=1)
    assert len(selected) == 1

    manifest, task = _manifest_and_task(tmp_path)
    output = validate_target_output({"answer": "wrong", "citations": [], "files_read": []})
    grade = grade_task(task, output, manifest, _trace(task.task_id))
    run = _run_object(manifest, task, output)
    judge_input = build_judge_input(run=run, task=task, output=output, grade=grade)
    assert judge_cache_key(judge_input, provider="openai", model="m") == judge_cache_key(judge_input, provider="openai", model="m")

    def fail_provider(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("dry-run cost estimate must not create provider")

    monkeypatch.setattr("contract2agent.evaluation.file_reading.llm_judge.provider_from_options", fail_provider)
    dry = run_judge(
        paths["run"],
        paths["tasks"],
        options=JudgeOptions(provider="openai", dry_run_cost_estimate=True, judge_only="all", max_judge_tasks=1),
    )
    assert dry.summary["calls_made"] == 0
    assert dry.summary["dry_run_estimates"] == 1


def test_cached_command_judge_prevents_duplicate_call(tmp_path: Path) -> None:
    paths = _run_dummy(tmp_path)
    command = f"{sys.executable} {ROOT / 'examples' / 'file_reading_eval' / 'agents' / 'dummy_command_judge.py'} {{input_json}} {{output_json}}"
    options = JudgeOptions(provider="command", judge_command=command, judge_only="all", max_judge_tasks=1)

    first = run_judge(paths["run"], paths["tasks"], options=options, out=tmp_path / "judge1.json")
    second = run_judge(paths["run"], paths["tasks"], options=options, out=tmp_path / "judge2.json")

    assert first.summary["calls_made"] == 1
    assert second.summary["cache_hits"] == 1
    assert second.summary["calls_made"] == 0


def test_command_based_judge_adapter_works_with_dummy_judge(tmp_path: Path) -> None:
    paths = _run_dummy(tmp_path)
    command = f"{sys.executable} {ROOT / 'examples' / 'file_reading_eval' / 'agents' / 'dummy_command_judge.py'} {{input_json}} {{output_json}}"

    report = run_judge(
        paths["run"],
        paths["tasks"],
        options=JudgeOptions(provider="command", judge_command=command, judge_only="all", max_judge_tasks=1, cache_judge_results=False),
        out=tmp_path / "judge.json",
    )

    completed = [result for result in report.results if result.status == "completed"]
    assert completed
    assert completed[0].judge_output is not None
    assert completed[0].judge_output.deterministic is False


def test_recommendation_rules_cover_required_failure_modes() -> None:
    grades = [
        FileReadingGrade(task_id="missing", failures=["missing_citation"], citation_presence=0.0),
        FileReadingGrade(task_id="quote", failures=["citation_quote_mismatch", "citation_span_mismatch"], citation_quote_match=0.0),
        FileReadingGrade(task_id="forbidden", failures=["forbidden_file_violation"], forbidden_file_violation=True),
        FileReadingGrade(task_id="unanswerable", failures=["unanswerable_not_abstained"], unanswerable_abstention_score=0.0),
        FileReadingGrade(task_id="timeout", failures=["timeout"], latency_score=0.0),
        FileReadingGrade(task_id="unsupported", failures=["high_unsupported_claim_rate"], unsupported_claim_rate=1.0),
    ]

    flat = " ".join(recommendations_for_grades(grades)).casefold()
    grouped = prioritized_recommendations_for_grades(grades)

    assert "file_id" in flat and "line_start" in flat and "line_end" in flat
    assert "quote supporting spans" in flat
    assert "line ranges" in flat
    assert "path allowlist" in flat
    assert "insufficient-evidence" in flat
    assert "retrieval budget" in flat
    assert "factual claim" in flat
    assert "critical" in grouped
    assert "high" in grouped


def test_examples_and_docs_exist() -> None:
    assert (ROOT / "examples" / "file_reading_eval" / "README.md").exists()
    for name in (
        "dummy_good_reader.py",
        "dummy_bad_citation_reader.py",
        "dummy_forbidden_reader.py",
        "dummy_timeout_reader.py",
    ):
        assert (ROOT / "examples" / "file_reading_eval" / "agents" / name).exists()
    assert (ROOT / "docs" / "file-reading-eval" / "README.md").exists()
    assert "file-reading agent evaluation" in (ROOT / "README.md").read_text(encoding="utf-8").casefold()


def test_readme_zh_cn_file_reading_llm_judge_section_is_localized() -> None:
    readme = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    assert "## File-reading LLM Judge Update" not in readme
    assert "## 文件阅读 LLM 评审更新" in readme
    assert "默认禁用" in readme
    assert "OPENAI_API_KEY" in readme


def test_file_reading_eval_zh_cn_guide_is_localized() -> None:
    guide = (ROOT / "docs" / "file-reading-eval" / "README.zh-CN.md").read_text(encoding="utf-8")

    assert "This page mirrors" not in guide
    assert "确定性评分" in guide
    assert "显式启用" in guide
    assert "GitHub Pages" in guide


def test_generated_file_eval_artifacts_are_gitignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/.runs/" in gitignore
    assert "/file_reading_eval/" in gitignore
    assert ".judge_cache/" in gitignore


def test_absolute_paths_are_sanitized_in_report(tmp_path: Path) -> None:
    paths = _run_dummy(tmp_path)
    grade_run(paths["run"], paths["tasks"], out=paths["run"] / "grades.json")
    outputs = write_run_report(paths["run"], report_format="md,json", out_dir=tmp_path / "report")
    markdown = outputs["markdown"].read_text(encoding="utf-8")
    json_report = outputs["json"].read_text(encoding="utf-8")

    assert str(tmp_path) not in markdown
    assert str(tmp_path) not in json_report
    assert "<local>/" in markdown


def test_embedded_absolute_paths_are_sanitized_in_report_json(tmp_path: Path) -> None:
    manifest, task = _manifest_and_task(tmp_path)
    leaked_path = f"{tmp_path.as_posix()}/source/policy.md"
    output = validate_target_output(
        {
            "answer": f"See {leaked_path} for the policy.",
            "citations": [
                {
                    "file_id": "policy.md",
                    "line_start": 3,
                    "line_end": 3,
                    "quote": "Enterprise customers must retain audit logs for 90 days.",
                }
            ],
            "files_read": ["policy.md"],
            "notes": f"adapter read {leaked_path}",
        },
        raw_output=json.dumps({"answer": f"See {leaked_path} for the policy."}),
    )
    run = _run_object(manifest, task, output)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run.json").write_text(json.dumps(to_dict(run), indent=2), encoding="utf-8")

    grade_run(run_dir, [task], out=run_dir / "grades.json")
    outputs = write_run_report(run_dir, report_format="json", out_dir=tmp_path / "report")
    json_report = outputs["json"].read_text(encoding="utf-8")

    assert tmp_path.as_posix() not in json_report
    assert "<local_path>" in json_report


def test_secret_like_values_are_sanitized_in_report_json(tmp_path: Path) -> None:
    manifest, task = _manifest_and_task(tmp_path)
    output = validate_target_output(
        {
            "answer": "OPENAI_API_KEY=sk-reportsecret123456789",
            "citations": [],
            "files_read": ["policy.md"],
        },
        raw_output=json.dumps({"answer": "OPENAI_API_KEY=sk-reportsecret123456789"}),
    )
    run = _run_object(manifest, task, output)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run.json").write_text(json.dumps(to_dict(run), indent=2), encoding="utf-8")

    grade_run(run_dir, [task], out=run_dir / "grades.json")
    outputs = write_run_report(run_dir, report_format="json", out_dir=tmp_path / "report")
    json_report = outputs["json"].read_text(encoding="utf-8")

    assert "sk-reportsecret123456789" not in json_report
    assert "<redacted_secret>" in json_report


def test_network_reference_import_requires_allow_flag(tmp_path: Path) -> None:
    with pytest.raises(PermissionError):
        import_reference_source("qasper", tmp_path / "refs", allow_network=False)


def _profile() -> FileReadingAgentProfile:
    return FileReadingAgentProfile(
        agent_id="reader",
        name="Reader",
        can_list_files=True,
        can_search_files=True,
        can_read_files=True,
        citation_support="line_citations",
        output_schema_support="json",
        trace_support="files_read",
    )


def _manifest_and_task(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir(exist_ok=True)
    (source / "policy.md").write_text(
        "# Policy\n\nEnterprise customers must retain audit logs for 90 days.\n",
        encoding="utf-8",
    )
    (source / "private_notes.forbidden.md").write_text("Forbidden content\n", encoding="utf-8")
    manifest = import_local_corpus(source, tmp_path / "corpus", tmp_path / "manifest.json")
    span = EvidenceSpan(
        file_id="policy.md",
        line_start=3,
        line_end=3,
        quote="Enterprise customers must retain audit logs for 90 days.",
        label="policy",
    )
    task = FileReadingTask(
        task_id="task1",
        task_type="single_file_qa",
        question="How long must audit logs be retained?",
        allowed_files=["policy.md"],
        forbidden_files=["private_notes.forbidden.md"],
        supporting_files=["policy.md"],
        gold_answer="Enterprise customers must retain audit logs for 90 days.",
        gold_evidence_spans=[span],
        expected_citations=[span],
    )
    return manifest, task


def _trace(task_id: str, *, files_read: list[str] | None = None, timeout: bool = False) -> FileAccessTrace:
    return FileAccessTrace(
        task_id=task_id,
        files_read=files_read or [],
        stdout_path="stdout.txt",
        stderr_path="stderr.txt",
        start_time="2026-05-05T00:00:00+00:00",
        end_time="2026-05-05T00:00:01+00:00",
        duration_seconds=1.0,
        timeout=timeout,
        command=["dummy"],
        exit_code=0 if not timeout else None,
    )


def _run_object(manifest, task: FileReadingTask, output):  # type: ignore[no-untyped-def]
    from contract2agent.evaluation.file_reading.schema import FileReadingRun

    return FileReadingRun(
        run_id="run",
        agent_profile=_profile(),
        corpus_manifest=manifest,
        task_file="tasks.jsonl",
        tasks=[task],
        outputs={task.task_id: output},
        traces={task.task_id: _trace(task.task_id, files_read=output.files_read)},
        status="completed",
        metadata={"observed_run": True},
    )


def _write_profile_task_and_dummy(tmp_path: Path, tasks: list[FileReadingTask]) -> dict[str, Path]:
    profile_path = tmp_path / "profile.json"
    tasks_path = tmp_path / "tasks.jsonl"
    manifest_path = tmp_path / "manifest.json"
    profile_path.write_text(json.dumps(to_dict(_profile()), indent=2), encoding="utf-8")
    write_tasks_jsonl(tasks, tasks_path)
    dummy = tmp_path / "dummy_agent.py"
    dummy.write_text(
        "\n".join(
            [
                "import json, sys",
                "payload=json.loads(open(sys.argv[1], encoding='utf-8').read())",
                "json.dump({'answer':'Enterprise customers must retain audit logs for 90 days.','citations':[{'file_id':'policy.md','line_start':3,'line_end':3,'quote':'Enterprise customers must retain audit logs for 90 days.'}],'confidence':0.9,'files_read':['policy.md']}, open(sys.argv[2], 'w', encoding='utf-8'))",
            ]
        ),
        encoding="utf-8",
    )
    return {"profile": profile_path, "tasks": tasks_path, "manifest": manifest_path, "dummy": dummy}


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


def _load_tasks(path: Path) -> list[FileReadingTask]:
    from contract2agent.evaluation.file_reading.tasks import load_tasks_jsonl

    return load_tasks_jsonl(path)
