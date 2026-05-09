from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from contract2agent.evaluation.file_reading.compare import compare_with_references
from contract2agent.evaluation.file_reading.corpus import import_local_corpus, load_corpus_manifest
from contract2agent.evaluation.file_reading.graders import grade_run
from contract2agent.evaluation.file_reading.help import render_help_topic, topic_names
from contract2agent.evaluation.file_reading.llm_judge import (
    DEFAULT_API_KEY_ENV,
    DEFAULT_OPENAI_MODEL,
    JudgeOptions,
    llm_configuration_status,
    normalize_provider,
    run_judge,
)
from contract2agent.evaluation.file_reading.references import (
    curated_reference_sources,
    import_reference_source,
)
from contract2agent.evaluation.file_reading.reports import (
    write_profile_only_report,
    write_run_report,
)
from contract2agent.evaluation.file_reading.runner import run_file_reading_eval
from contract2agent.evaluation.file_reading.schema import to_dict
from contract2agent.evaluation.file_reading.tasks import (
    build_smoke_tasks,
    validate_tasks,
    write_tasks_jsonl,
)


def _style_state() -> dict[str, bool]:
    return {
        "no_color": False,
        "plain": False,
        "json": False,
        "quiet": False,
        "verbose": False,
    }


def _use_color(style: dict[str, bool]) -> bool:
    return not (
        style.get("no_color")
        or style.get("plain")
        or style.get("json")
        or os.environ.get("NO_COLOR")
    )


def _ansi(text: str, code: str, style: dict[str, bool]) -> str:
    if not _use_color(style):
        return text
    return f"\033[{code}m{text}\033[0m"


def _emit(message: str, style: dict[str, bool], *, quiet_ok: bool = False) -> None:
    if style.get("quiet") and not quiet_ok:
        return
    print(message)


def _emit_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _heading(title: str, style: dict[str, bool]) -> str:
    if style.get("plain") or style.get("json"):
        return title
    return _ansi(f"== {title} ==", "1;36", style)


def _status(label: str, value: str, style: dict[str, bool]) -> str:
    code = "32" if value in {"ok", "pass", "completed"} else "33" if value in {"warn", "skipped"} else "31"
    return f"{label}: {_ansi(value.upper(), code, style)}"


def _judge_options_from_values(
    *,
    provider: str,
    model: str,
    judge_command: str,
    prompt_for_key: bool,
    judge_only: str,
    max_judge_tasks: int,
    llm_max_input_chars: int,
    llm_max_output_tokens: int,
    evidence_snippet_limit: int,
    cost_budget_usd: float | None,
    dry_run_cost_estimate: bool,
    cache_judge_results: bool,
    api_key_env: str,
    out_dir: Path,
) -> JudgeOptions:
    interactive = sys.stdin.isatty()
    normalized_provider = normalize_provider(provider)
    return JudgeOptions(
        provider=provider,
        model=model,
        judge_command=judge_command,
        api_key_env=api_key_env,
        prompt_for_key=prompt_for_key
        or (normalized_provider == "openai" and interactive and not dry_run_cost_estimate),
        interactive=interactive,
        judge_only=judge_only,
        max_judge_tasks=max_judge_tasks,
        max_input_chars=llm_max_input_chars,
        max_output_tokens=llm_max_output_tokens,
        evidence_snippet_limit=evidence_snippet_limit,
        cost_budget_usd=cost_budget_usd,
        dry_run_cost_estimate=dry_run_cost_estimate,
        cache_judge_results=cache_judge_results,
        cache_dir=out_dir / ".judge_cache",
    )


def _doctor_payload() -> dict[str, Any]:
    checks = []
    checks.append({"name": "python", "status": "ok", "detail": sys.version.split()[0]})
    checks.append({"name": "file_reading_module", "status": "ok", "detail": "imported"})
    checks.append({"name": "deterministic_default", "status": "ok", "detail": "API calls disabled unless judge is explicit"})
    checks.append({"name": "api_key_env", "status": "ok" if os.environ.get(DEFAULT_API_KEY_ENV) else "warn", "detail": DEFAULT_API_KEY_ENV})
    checks.append({"name": "docs", "status": "ok", "detail": "use c2a file-eval help workflow"})
    return {
        "command": "file-eval doctor",
        "checks": checks,
        "next_commands": [
            "c2a file-eval help workflow",
            "c2a file-eval import-local --input ./files --out .runs/corpus",
            "c2a file-eval judge --help",
        ],
    }


def _print_doctor(style: dict[str, bool]) -> None:
    payload = _doctor_payload()
    if style.get("json"):
        _emit_json(payload)
        return
    _emit(_heading("File Eval Doctor", style), style, quiet_ok=True)
    for check in payload["checks"]:
        _emit(_status(check["name"], check["status"], style) + f" - {check['detail']}", style, quiet_ok=True)
    if not style.get("plain"):
        _emit("", style, quiet_ok=True)
        _emit("Next commands:", style, quiet_ok=True)
        for command in payload["next_commands"]:
            _emit(f"- {command}", style, quiet_ok=True)
    if style.get("verbose"):
        _emit("Artifacts: run.json, run.jsonl, grades.json, llm_judge.json, report.md, report.json", style, quiet_ok=True)


def register_typer_commands(root_app: Any, typer: Any, console: Any) -> None:
    file_eval = typer.Typer(
        help=(
            "CLI-driven file-reading agent evaluation: import local corpora, build tasks, "
            "run target agents, deterministic grade, optionally LLM-judge, compare references, "
            "and render reports. Deterministic grading is the default and requires no API."
        )
    )
    style = _style_state()

    @file_eval.callback()
    def file_eval_callback(
        no_color: bool = typer.Option(False, "--no-color", help="Disable ANSI color output."),
        plain: bool = typer.Option(False, "--plain", help="Use plain script-friendly output."),
        json_output: bool = typer.Option(False, "--json", help="Use JSON output when supported."),
        quiet: bool = typer.Option(False, "--quiet", help="Suppress non-essential output."),
        verbose: bool = typer.Option(False, "--verbose", help="Include additional artifact details."),
    ) -> None:
        style.update(
            {
                "no_color": no_color,
                "plain": plain,
                "json": json_output,
                "quiet": quiet,
                "verbose": verbose,
            }
        )

    @file_eval.command(name="help")
    def help_command(
        topic: str = typer.Argument("overview", help=f"Topic: {', '.join(topic_names())}."),
    ) -> None:
        console.print(render_help_topic(topic).rstrip())

    @file_eval.command(name="doctor")
    def doctor_command(
        json_output: bool = typer.Option(False, "--json", help="Print machine-readable doctor checks."),
        no_color: bool = typer.Option(False, "--no-color", help="Disable ANSI color output."),
        plain: bool = typer.Option(False, "--plain", help="Use plain output."),
        quiet: bool = typer.Option(False, "--quiet", help="Suppress non-essential output."),
        verbose: bool = typer.Option(False, "--verbose", help="Include extra details."),
    ) -> None:
        local_style = {
            **style,
            "json": style.get("json") or json_output,
            "no_color": style.get("no_color") or no_color,
            "plain": style.get("plain") or plain,
            "quiet": style.get("quiet") or quiet,
            "verbose": style.get("verbose") or verbose,
        }
        _print_doctor(local_style)

    @file_eval.command(name="init")
    def init_command(
        out: Path = typer.Option(Path("file_reading_eval"), "--out", help="Starter workspace directory."),
    ) -> None:
        for child in ("corpus", "profiles", "tasks", "runs", "reports", "references", "configs"):
            (out / child).mkdir(parents=True, exist_ok=True)
        readme = out / "README.md"
        if not readme.exists():
            readme.write_text(
                "# File Reading Eval Workspace\n\n"
                "Use `c2a file-eval help workflow` for the recommended workflow.\n",
                encoding="utf-8",
            )
        _emit(f"Initialized file-reading eval workspace at {out}", style)

    @file_eval.command(name="import-local")
    def import_local_command(
        input_path: Path = typer.Option(..., "--input", help="Input file or directory."),
        out: Path = typer.Option(..., "--out", help="Output corpus directory."),
        manifest: Path | None = typer.Option(None, "--manifest", help="Manifest JSON path."),
        source_type: str = typer.Option("local", "--source-type", help="local, paper, reference, or methodology."),
        title: str = typer.Option("", "--title", help="Optional title for paper/reference imports."),
        include: list[str] | None = typer.Option(None, "--include", help="Include glob pattern; repeatable."),
        exclude: list[str] | None = typer.Option(None, "--exclude", help="Exclude glob pattern; repeatable."),
        license_name: str = typer.Option("", "--license", help="Source license metadata."),
    ) -> None:
        loaded = import_local_corpus(
            input_path,
            out,
            manifest,
            source_type=source_type,
            title=title,
            include_patterns=include,
            exclude_patterns=exclude,
            license_name=license_name,
        )
        console.print(f"Imported {len(loaded.documents)} document(s) into {out}")

    @file_eval.command(name="list-references")
    def list_references_command() -> None:
        console.print(json.dumps([to_dict(source) for source in curated_reference_sources()], indent=2, sort_keys=True))

    @file_eval.command(name="import-reference")
    def import_reference_command(
        source: str = typer.Option(..., "--source", help="Curated source id, such as qasper."),
        out: Path = typer.Option(..., "--out", help="Output metadata directory."),
        limit: int | None = typer.Option(None, "--limit", help="Optional source record limit."),
        allow_network: bool = typer.Option(False, "--allow-network", help="Required for network-enabled imports."),
    ) -> None:
        imported = import_reference_source(source, out, allow_network=allow_network, limit=limit)
        console.print(json.dumps(to_dict(imported), indent=2, sort_keys=True))

    @file_eval.command(name="validate")
    def validate_command(
        corpus: Path = typer.Option(..., "--corpus", help="Corpus manifest JSON."),
        tasks: Path = typer.Option(..., "--tasks", help="Task JSONL file."),
    ) -> None:
        errors = validate_tasks(corpus, tasks)
        if errors:
            for error in errors:
                console.print(f"Error: {error}")
            raise typer.Exit(1)
        console.print("Validation passed.")

    @file_eval.command(name="build-tasks")
    def build_tasks_command(
        corpus: Path = typer.Option(..., "--corpus", help="Corpus manifest JSON."),
        mode: str = typer.Option("smoke", "--mode", help="Task generation mode."),
        max_tasks: int = typer.Option(20, "--max-tasks", help="Maximum tasks to write."),
        out: Path = typer.Option(..., "--out", help="Output task JSONL path."),
        seed: int = typer.Option(0, "--seed", help="Deterministic seed."),
    ) -> None:
        manifest = load_corpus_manifest(corpus)
        tasks = build_smoke_tasks(manifest, max_tasks=max_tasks, seed=seed, mode=mode)
        write_tasks_jsonl(tasks, out)
        console.print(f"Wrote {len(tasks)} task(s) to {out}")

    @file_eval.command(name="run")
    def run_command(
        profile: Path = typer.Option(..., "--profile", help="FileReadingAgentProfile JSON."),
        agent_command: str = typer.Option(..., "--agent-command", help="Command with {input_json} and {output_json}."),
        corpus: Path = typer.Option(..., "--corpus", help="Corpus manifest JSON."),
        tasks: Path = typer.Option(..., "--tasks", help="Task JSONL file."),
        time_budget_seconds: float = typer.Option(60.0, "--time-budget-seconds", help="Total run time budget."),
        max_tasks: int | None = typer.Option(None, "--max-tasks", help="Maximum tasks to run."),
        seed: int = typer.Option(0, "--seed", help="Deterministic seed recorded in artifacts."),
        out: Path = typer.Option(..., "--out", help="Run output directory."),
        judge: str = typer.Option("deterministic", "--judge", help="deterministic, none, llm/openai, or command."),
        judge_command: str = typer.Option("", "--judge-command", help="Command judge adapter with {input_json} and {output_json}."),
        judge_model: str = typer.Option(DEFAULT_OPENAI_MODEL, "--judge-model", help="Judge model name."),
        prompt_for_key: bool = typer.Option(False, "--prompt-for-key", help="Use hidden session-only API key input if env key is missing."),
        judge_only: str = typer.Option("failed", "--judge-only", help="failed, uncertain, open-ended, or all."),
        max_judge_tasks: int = typer.Option(20, "--max-judge-tasks", help="Maximum tasks sent to optional judge."),
        llm_max_input_chars: int = typer.Option(12000, "--llm-max-input-chars", help="Maximum compact judge input characters."),
        llm_max_output_tokens: int = typer.Option(500, "--llm-max-output-tokens", help="Maximum judge output tokens."),
        evidence_snippet_limit: int = typer.Option(5, "--evidence-snippet-limit", help="Max cited/gold snippets per judge input."),
        cost_budget_usd: float | None = typer.Option(None, "--cost-budget-usd", help="Stop before estimated budget is exceeded."),
        dry_run_cost_estimate: bool = typer.Option(False, "--dry-run-cost-estimate", help="Estimate judge cost without calls."),
        cache_judge_results: bool = typer.Option(True, "--cache-judge-results/--no-judge-cache", help="Cache judge results by stable input hash."),
        api_key_env: str = typer.Option(DEFAULT_API_KEY_ENV, "--api-key-env", help="Environment variable for OpenAI-compatible provider."),
    ) -> None:
        run = run_file_reading_eval(
            profile_path=profile,
            agent_command=agent_command,
            corpus_manifest_path=corpus,
            tasks_path=tasks,
            time_budget_seconds=time_budget_seconds,
            max_tasks=max_tasks,
            seed=seed,
            out_dir=out,
        )
        _emit(_heading("File Reading Run", style), style)
        _emit(f"Wrote observed run {run.run_id} to {out}", style)
        normalized_judge = normalize_provider("openai" if judge == "llm" else judge)
        if normalized_judge != "none":
            grade_path = out / "grades.json"
            grade_run(run, tasks, out=grade_path)
            options = _judge_options_from_values(
                provider=normalized_judge,
                model=judge_model,
                judge_command=judge_command,
                prompt_for_key=prompt_for_key,
                judge_only=judge_only,
                max_judge_tasks=max_judge_tasks,
                llm_max_input_chars=llm_max_input_chars,
                llm_max_output_tokens=llm_max_output_tokens,
                evidence_snippet_limit=evidence_snippet_limit,
                cost_budget_usd=cost_budget_usd,
                dry_run_cost_estimate=dry_run_cost_estimate,
                cache_judge_results=cache_judge_results,
                api_key_env=api_key_env,
                out_dir=out,
            )
            judge_path = out / "llm_judge.json"
            judge_report = run_judge(run, tasks, options=options, out=judge_path)
            _emit(
                f"Optional judge: provider={judge_report.judge_provider} selected={judge_report.summary['tasks_selected']} calls={judge_report.summary['calls_made']} cache_hits={judge_report.summary['cache_hits']} out={judge_path}",
                style,
            )

    @file_eval.command(name="profile-only")
    def profile_only_command(
        profile: Path = typer.Option(..., "--profile", help="FileReadingAgentProfile JSON."),
        out: Path = typer.Option(..., "--out", help="Report output directory."),
    ) -> None:
        paths = write_profile_only_report(profile, out)
        console.print(f"Wrote profile-only report to {paths['markdown']}")

    @file_eval.command(name="grade")
    def grade_command(
        run: Path = typer.Option(..., "--run", help="Run directory or run.json."),
        tasks: Path | None = typer.Option(None, "--tasks", help="Task JSONL file."),
        out: Path = typer.Option(..., "--out", help="Grade JSON path."),
    ) -> None:
        grades, scorecard = grade_run(run, tasks, out=out)
        if style.get("json"):
            _emit_json({"grades": len(grades), "out": str(out), "overall_score": scorecard.overall_score})
        else:
            _emit(_heading("Deterministic Grade", style), style)
            _emit(f"Wrote {len(grades)} grade(s) to {out}; overall={scorecard.overall_score}", style)

    @file_eval.command(name="compare")
    def compare_command(
        run: Path = typer.Option(..., "--run", help="Run directory."),
        reference: Path = typer.Option(..., "--reference", help="Reference results JSON."),
        out: Path = typer.Option(..., "--out", help="Comparison Markdown or JSON path."),
    ) -> None:
        report = compare_with_references(run, reference, out=out)
        console.print(f"Wrote comparison to {out}; comparable={report.comparable}")

    @file_eval.command(name="report")
    def report_command(
        run: Path = typer.Option(..., "--run", help="Run directory."),
        report_format: str = typer.Option("md,json", "--format", help="md,json, markdown, or json."),
        out: Path = typer.Option(..., "--out", help="Report output directory."),
        reference: Path | None = typer.Option(None, "--reference", help="Optional reference results JSON."),
        include_llm_judge: bool = typer.Option(False, "--include-llm-judge", help="Include run/llm_judge.json when present."),
        judge_report: Path | None = typer.Option(None, "--judge-report", help="Optional LLM judge report JSON."),
    ) -> None:
        paths = write_run_report(
            run,
            report_format=report_format,
            out_dir=out,
            reference_results=reference,
            include_llm_judge=include_llm_judge,
            judge_report_path=judge_report,
        )
        console.print(f"Wrote report artifact(s): {', '.join(str(path) for path in paths.values())}")

    @file_eval.command(name="configure-llm")
    def configure_llm_command(
        provider: str = typer.Option("openai", "--provider", help="openai or command."),
        model: str = typer.Option(DEFAULT_OPENAI_MODEL, "--model", help="Default judge model."),
        out: Path | None = typer.Option(None, "--out", help="Write a keyless example config JSON."),
    ) -> None:
        payload = {
            "provider": normalize_provider(provider),
            "model": model,
            "api_key_env": DEFAULT_API_KEY_ENV,
            "stores_api_key": False,
            "deterministic_default": True,
            "example": {
                "judge_only": "failed",
                "max_judge_tasks": 10,
                "llm_max_input_chars": 12000,
                "llm_max_output_tokens": 500,
                "evidence_snippet_limit": 5,
                "cost_budget_usd": 1.0,
            },
        }
        if out is not None:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            _emit(f"Wrote keyless LLM judge config example to {out}", style)
        else:
            _emit_json(payload)

    @file_eval.command(name="llm-check")
    def llm_check_command(
        provider: str = typer.Option("openai", "--provider", help="none, command, or openai."),
        judge_command: str = typer.Option("", "--judge-command", help="Optional command judge adapter."),
        api_key_env: str = typer.Option(DEFAULT_API_KEY_ENV, "--api-key-env", help="Environment variable for provider key."),
        json_output: bool = typer.Option(False, "--json", help="Print JSON."),
    ) -> None:
        payload = llm_configuration_status(
            provider=provider,
            api_key_env=api_key_env,
            judge_command=judge_command,
        )
        if style.get("json") or json_output:
            _emit_json(payload)
            return
        _emit(_heading("LLM Judge Check", style), style)
        _emit(f"Provider: {payload['provider']}", style)
        _emit(f"API calls enabled: {payload['api_calls_enabled']}", style)
        _emit(f"API key env configured: {payload['api_key_configured']}", style)
        _emit("API key value: not displayed", style)

    @file_eval.command(name="judge")
    def judge_command_fn(
        run: Path = typer.Option(..., "--run", help="Run directory or run.json."),
        tasks: Path | None = typer.Option(None, "--tasks", help="Task JSONL file."),
        out: Path | None = typer.Option(None, "--out", help="Judge report JSON path. Defaults to run/llm_judge.json."),
        provider: str = typer.Option("none", "--provider", help="none, command, llm/openai."),
        judge_command: str = typer.Option("", "--judge-command", help="Command with {input_json} and {output_json}."),
        model: str = typer.Option(DEFAULT_OPENAI_MODEL, "--model", help="Judge model name."),
        prompt_for_key: bool = typer.Option(False, "--prompt-for-key", help="Use hidden session-only key input if env key is missing."),
        judge_only: str = typer.Option("failed", "--judge-only", help="failed, uncertain, open-ended, or all."),
        max_judge_tasks: int = typer.Option(20, "--max-judge-tasks", help="Maximum tasks sent to optional judge."),
        llm_max_input_chars: int = typer.Option(12000, "--llm-max-input-chars", help="Maximum compact judge input characters."),
        llm_max_output_tokens: int = typer.Option(500, "--llm-max-output-tokens", help="Maximum judge output tokens."),
        evidence_snippet_limit: int = typer.Option(5, "--evidence-snippet-limit", help="Max cited/gold snippets per judge input."),
        cost_budget_usd: float | None = typer.Option(None, "--cost-budget-usd", help="Stop before estimated budget is exceeded."),
        dry_run_cost_estimate: bool = typer.Option(False, "--dry-run-cost-estimate", help="Estimate judge cost without calls."),
        cache_judge_results: bool = typer.Option(True, "--cache-judge-results/--no-judge-cache", help="Cache judge results."),
        api_key_env: str = typer.Option(DEFAULT_API_KEY_ENV, "--api-key-env", help="Environment variable for OpenAI-compatible provider."),
    ) -> None:
        run_dir = run if run.is_dir() else run.parent
        target = out or (run_dir / "llm_judge.json")
        selected_provider = provider
        if selected_provider == "none" and judge_command:
            selected_provider = "command"
        options = _judge_options_from_values(
            provider=selected_provider,
            model=model,
            judge_command=judge_command,
            prompt_for_key=prompt_for_key,
            judge_only=judge_only,
            max_judge_tasks=max_judge_tasks,
            llm_max_input_chars=llm_max_input_chars,
            llm_max_output_tokens=llm_max_output_tokens,
            evidence_snippet_limit=evidence_snippet_limit,
            cost_budget_usd=cost_budget_usd,
            dry_run_cost_estimate=dry_run_cost_estimate,
            cache_judge_results=cache_judge_results,
            api_key_env=api_key_env,
            out_dir=run_dir,
        )
        report = run_judge(run, tasks, options=options, out=target)
        if style.get("json"):
            _emit_json(to_dict(report))
            return
        _emit(_heading("Optional LLM Judge", style), style)
        _emit(f"Provider: {report.judge_provider}", style)
        _emit(f"Selected tasks: {report.summary['tasks_selected']}", style)
        _emit(f"Calls made: {report.summary['calls_made']}", style)
        _emit(f"Cache hits: {report.summary['cache_hits']}", style)
        _emit(f"Skipped by budget: {report.summary['skipped_due_to_budget']}", style)
        _emit(f"Estimated cost USD: {report.summary['estimated_cost_usd']}", style)
        _emit(f"Wrote judge report to {target}", style)

    root_app.add_typer(file_eval, name="file-eval")


def add_file_eval_argparse(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser(
        "file-eval",
        help="CLI-driven file-reading agent evaluation.",
        description=(
            "Import local corpora, build tasks, run target agents, deterministic grade, "
            "optionally LLM-judge, compare references, and render reports. Deterministic "
            "grading is the default and requires no API."
        ),
    )
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    sub = parser.add_subparsers(dest="file_eval_command", required=True)

    help_parser = sub.add_parser("help")
    help_parser.add_argument("topic", nargs="?", default="overview")
    help_parser.set_defaults(func=_argparse_help)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--json", action="store_true", dest="json_output")
    doctor.add_argument("--no-color", action="store_true")
    doctor.add_argument("--plain", action="store_true")
    doctor.add_argument("--quiet", action="store_true")
    doctor.add_argument("--verbose", action="store_true")
    doctor.set_defaults(func=_argparse_doctor)

    init = sub.add_parser("init")
    init.add_argument("--out", type=Path, default=Path("file_reading_eval"))
    init.set_defaults(func=_argparse_init)

    import_local = sub.add_parser("import-local")
    import_local.add_argument("--input", required=True, type=Path)
    import_local.add_argument("--out", required=True, type=Path)
    import_local.add_argument("--manifest", type=Path)
    import_local.add_argument("--source-type", default="local")
    import_local.add_argument("--title", default="")
    import_local.add_argument("--include", action="append")
    import_local.add_argument("--exclude", action="append")
    import_local.add_argument("--license", default="", dest="license_name")
    import_local.set_defaults(func=_argparse_import_local)

    list_refs = sub.add_parser("list-references")
    list_refs.set_defaults(func=_argparse_list_references)

    import_ref = sub.add_parser("import-reference")
    import_ref.add_argument("--source", required=True)
    import_ref.add_argument("--out", required=True, type=Path)
    import_ref.add_argument("--limit", type=int)
    import_ref.add_argument("--allow-network", action="store_true")
    import_ref.set_defaults(func=_argparse_import_reference)

    validate = sub.add_parser("validate")
    validate.add_argument("--corpus", required=True, type=Path)
    validate.add_argument("--tasks", required=True, type=Path)
    validate.set_defaults(func=_argparse_validate)

    build_tasks = sub.add_parser("build-tasks")
    build_tasks.add_argument("--corpus", required=True, type=Path)
    build_tasks.add_argument("--mode", default="smoke")
    build_tasks.add_argument("--max-tasks", type=int, default=20)
    build_tasks.add_argument("--out", required=True, type=Path)
    build_tasks.add_argument("--seed", type=int, default=0)
    build_tasks.set_defaults(func=_argparse_build_tasks)

    run = sub.add_parser("run")
    run.add_argument("--profile", required=True, type=Path)
    run.add_argument("--agent-command", required=True)
    run.add_argument("--corpus", required=True, type=Path)
    run.add_argument("--tasks", required=True, type=Path)
    run.add_argument("--time-budget-seconds", type=float, default=60.0)
    run.add_argument("--max-tasks", type=int)
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--out", required=True, type=Path)
    run.add_argument("--judge", default="deterministic")
    run.add_argument("--judge-command", default="")
    run.add_argument("--judge-model", default=DEFAULT_OPENAI_MODEL)
    run.add_argument("--prompt-for-key", action="store_true")
    run.add_argument("--judge-only", default="failed")
    run.add_argument("--max-judge-tasks", type=int, default=20)
    run.add_argument("--llm-max-input-chars", type=int, default=12000)
    run.add_argument("--llm-max-output-tokens", type=int, default=500)
    run.add_argument("--evidence-snippet-limit", type=int, default=5)
    run.add_argument("--cost-budget-usd", type=float)
    run.add_argument("--dry-run-cost-estimate", action="store_true")
    run.add_argument("--cache-judge-results", dest="cache_judge_results", action="store_true", default=True)
    run.add_argument("--no-judge-cache", dest="cache_judge_results", action="store_false")
    run.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    run.set_defaults(func=_argparse_run)

    profile_only = sub.add_parser("profile-only")
    profile_only.add_argument("--profile", required=True, type=Path)
    profile_only.add_argument("--out", required=True, type=Path)
    profile_only.set_defaults(func=_argparse_profile_only)

    grade = sub.add_parser("grade")
    grade.add_argument("--run", required=True, type=Path)
    grade.add_argument("--tasks", type=Path)
    grade.add_argument("--out", required=True, type=Path)
    grade.set_defaults(func=_argparse_grade)

    compare = sub.add_parser("compare")
    compare.add_argument("--run", required=True, type=Path)
    compare.add_argument("--reference", required=True, type=Path)
    compare.add_argument("--out", required=True, type=Path)
    compare.set_defaults(func=_argparse_compare)

    report = sub.add_parser("report")
    report.add_argument("--run", required=True, type=Path)
    report.add_argument("--format", default="md,json")
    report.add_argument("--out", required=True, type=Path)
    report.add_argument("--reference", type=Path)
    report.add_argument("--include-llm-judge", action="store_true")
    report.add_argument("--judge-report", type=Path)
    report.set_defaults(func=_argparse_report)

    configure = sub.add_parser("configure-llm")
    configure.add_argument("--provider", default="openai")
    configure.add_argument("--model", default=DEFAULT_OPENAI_MODEL)
    configure.add_argument("--out", type=Path)
    configure.set_defaults(func=_argparse_configure_llm)

    llm_check = sub.add_parser("llm-check")
    llm_check.add_argument("--provider", default="openai")
    llm_check.add_argument("--judge-command", default="")
    llm_check.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    llm_check.add_argument("--json", action="store_true", dest="json_output")
    llm_check.set_defaults(func=_argparse_llm_check)

    judge = sub.add_parser("judge")
    judge.add_argument("--run", required=True, type=Path)
    judge.add_argument("--tasks", type=Path)
    judge.add_argument("--out", type=Path)
    judge.add_argument("--provider", default="none")
    judge.add_argument("--judge-command", default="")
    judge.add_argument("--model", default=DEFAULT_OPENAI_MODEL)
    judge.add_argument("--prompt-for-key", action="store_true")
    judge.add_argument("--judge-only", default="failed")
    judge.add_argument("--max-judge-tasks", type=int, default=20)
    judge.add_argument("--llm-max-input-chars", type=int, default=12000)
    judge.add_argument("--llm-max-output-tokens", type=int, default=500)
    judge.add_argument("--evidence-snippet-limit", type=int, default=5)
    judge.add_argument("--cost-budget-usd", type=float)
    judge.add_argument("--dry-run-cost-estimate", action="store_true")
    judge.add_argument("--cache-judge-results", dest="cache_judge_results", action="store_true", default=True)
    judge.add_argument("--no-judge-cache", dest="cache_judge_results", action="store_false")
    judge.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    judge.add_argument("--json", action="store_true", dest="json_output")
    judge.set_defaults(func=_argparse_judge)


def run_argparse_command(args: argparse.Namespace) -> int:
    return int(args.func(args) or 0)


def _argparse_style(args: argparse.Namespace) -> dict[str, bool]:
    return {
        "no_color": bool(getattr(args, "no_color", False)),
        "plain": bool(getattr(args, "plain", False)),
        "json": bool(getattr(args, "json_output", False)),
        "quiet": bool(getattr(args, "quiet", False)),
        "verbose": bool(getattr(args, "verbose", False)),
    }


def _argparse_help(args: argparse.Namespace) -> int:
    print(render_help_topic(args.topic).rstrip())
    return 0


def _argparse_doctor(args: argparse.Namespace) -> int:
    _print_doctor(_argparse_style(args))
    return 0


def _argparse_init(args: argparse.Namespace) -> int:
    for child in ("corpus", "profiles", "tasks", "runs", "reports", "references", "configs"):
        (args.out / child).mkdir(parents=True, exist_ok=True)
    readme = args.out / "README.md"
    if not readme.exists():
        readme.write_text(
            "# File Reading Eval Workspace\n\n"
            "Use `c2a file-eval help workflow` for the recommended workflow.\n",
            encoding="utf-8",
        )
    print(f"Initialized file-reading eval workspace at {args.out}")
    return 0


def _argparse_import_local(args: argparse.Namespace) -> int:
    manifest = import_local_corpus(
        args.input,
        args.out,
        args.manifest,
        source_type=args.source_type,
        title=args.title,
        include_patterns=args.include,
        exclude_patterns=args.exclude,
        license_name=args.license_name,
    )
    print(f"Imported {len(manifest.documents)} document(s) into {args.out}")
    return 0


def _argparse_list_references(_args: argparse.Namespace) -> int:
    print(json.dumps([to_dict(source) for source in curated_reference_sources()], indent=2, sort_keys=True))
    return 0


def _argparse_import_reference(args: argparse.Namespace) -> int:
    imported = import_reference_source(args.source, args.out, allow_network=args.allow_network, limit=args.limit)
    print(json.dumps(to_dict(imported), indent=2, sort_keys=True))
    return 0


def _argparse_validate(args: argparse.Namespace) -> int:
    errors = validate_tasks(args.corpus, args.tasks)
    if errors:
        for error in errors:
            print(f"Error: {error}")
        return 1
    print("Validation passed.")
    return 0


def _argparse_build_tasks(args: argparse.Namespace) -> int:
    manifest = load_corpus_manifest(args.corpus)
    tasks = build_smoke_tasks(manifest, max_tasks=args.max_tasks, seed=args.seed, mode=args.mode)
    write_tasks_jsonl(tasks, args.out)
    print(f"Wrote {len(tasks)} task(s) to {args.out}")
    return 0


def _argparse_run(args: argparse.Namespace) -> int:
    run = run_file_reading_eval(
        profile_path=args.profile,
        agent_command=args.agent_command,
        corpus_manifest_path=args.corpus,
        tasks_path=args.tasks,
        time_budget_seconds=args.time_budget_seconds,
        max_tasks=args.max_tasks,
        seed=args.seed,
        out_dir=args.out,
    )
    print(f"Wrote observed run {run.run_id} to {args.out}")
    normalized_judge = normalize_provider("openai" if args.judge == "llm" else args.judge)
    if normalized_judge != "none":
        grade_run(run, args.tasks, out=args.out / "grades.json")
        options = _judge_options_from_values(
            provider=normalized_judge,
            model=args.judge_model,
            judge_command=args.judge_command,
            prompt_for_key=args.prompt_for_key,
            judge_only=args.judge_only,
            max_judge_tasks=args.max_judge_tasks,
            llm_max_input_chars=args.llm_max_input_chars,
            llm_max_output_tokens=args.llm_max_output_tokens,
            evidence_snippet_limit=args.evidence_snippet_limit,
            cost_budget_usd=args.cost_budget_usd,
            dry_run_cost_estimate=args.dry_run_cost_estimate,
            cache_judge_results=args.cache_judge_results,
            api_key_env=args.api_key_env,
            out_dir=args.out,
        )
        judge_path = args.out / "llm_judge.json"
        judge_report = run_judge(run, args.tasks, options=options, out=judge_path)
        print(
            "Optional judge: "
            f"provider={judge_report.judge_provider} "
            f"selected={judge_report.summary['tasks_selected']} "
            f"calls={judge_report.summary['calls_made']} "
            f"cache_hits={judge_report.summary['cache_hits']} "
            f"out={judge_path}"
        )
    return 0


def _argparse_profile_only(args: argparse.Namespace) -> int:
    paths = write_profile_only_report(args.profile, args.out)
    print(f"Wrote profile-only report to {paths['markdown']}")
    return 0


def _argparse_grade(args: argparse.Namespace) -> int:
    grades, scorecard = grade_run(args.run, args.tasks, out=args.out)
    print(f"Wrote {len(grades)} grade(s) to {args.out}; overall={scorecard.overall_score}")
    return 0


def _argparse_compare(args: argparse.Namespace) -> int:
    report = compare_with_references(args.run, args.reference, out=args.out)
    print(f"Wrote comparison to {args.out}; comparable={report.comparable}")
    return 0


def _argparse_report(args: argparse.Namespace) -> int:
    paths = write_run_report(
        args.run,
        report_format=args.format,
        out_dir=args.out,
        reference_results=args.reference,
        include_llm_judge=args.include_llm_judge,
        judge_report_path=args.judge_report,
    )
    print(f"Wrote report artifact(s): {', '.join(str(path) for path in paths.values())}")
    return 0


def _argparse_configure_llm(args: argparse.Namespace) -> int:
    payload = {
        "provider": normalize_provider(args.provider),
        "model": args.model,
        "api_key_env": DEFAULT_API_KEY_ENV,
        "stores_api_key": False,
        "deterministic_default": True,
        "example": {
            "judge_only": "failed",
            "max_judge_tasks": 10,
            "llm_max_input_chars": 12000,
            "llm_max_output_tokens": 500,
            "evidence_snippet_limit": 5,
            "cost_budget_usd": 1.0,
        },
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote keyless LLM judge config example to {args.out}")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _argparse_llm_check(args: argparse.Namespace) -> int:
    payload = llm_configuration_status(
        provider=args.provider,
        api_key_env=args.api_key_env,
        judge_command=args.judge_command,
    )
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Provider: {payload['provider']}")
        print(f"API calls enabled: {payload['api_calls_enabled']}")
        print(f"API key env configured: {payload['api_key_configured']}")
        print("API key value: not displayed")
    return 0


def _argparse_judge(args: argparse.Namespace) -> int:
    run_dir = args.run if args.run.is_dir() else args.run.parent
    target = args.out or (run_dir / "llm_judge.json")
    provider = args.provider
    if provider == "none" and args.judge_command:
        provider = "command"
    options = _judge_options_from_values(
        provider=provider,
        model=args.model,
        judge_command=args.judge_command,
        prompt_for_key=args.prompt_for_key,
        judge_only=args.judge_only,
        max_judge_tasks=args.max_judge_tasks,
        llm_max_input_chars=args.llm_max_input_chars,
        llm_max_output_tokens=args.llm_max_output_tokens,
        evidence_snippet_limit=args.evidence_snippet_limit,
        cost_budget_usd=args.cost_budget_usd,
        dry_run_cost_estimate=args.dry_run_cost_estimate,
        cache_judge_results=args.cache_judge_results,
        api_key_env=args.api_key_env,
        out_dir=run_dir,
    )
    report = run_judge(args.run, args.tasks, options=options, out=target)
    if getattr(args, "json_output", False):
        print(json.dumps(to_dict(report), indent=2, sort_keys=True))
    else:
        print(f"Provider: {report.judge_provider}")
        print(f"Selected tasks: {report.summary['tasks_selected']}")
        print(f"Calls made: {report.summary['calls_made']}")
        print(f"Cache hits: {report.summary['cache_hits']}")
        print(f"Skipped by budget: {report.summary['skipped_due_to_budget']}")
        print(f"Estimated cost USD: {report.summary['estimated_cost_usd']}")
        print(f"Wrote judge report to {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m contract2agent.evaluation.file_reading.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_file_eval_argparse(subparsers)
    args = parser.parse_args(argv)
    return run_argparse_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
