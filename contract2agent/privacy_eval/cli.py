from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from contract2agent.privacy_eval.analyzer import load_privacy_profile, privacy_source_references
from contract2agent.privacy_eval.report import build_privacy_report, write_privacy_report


def run_privacy_eval(
    *,
    profile: Path | None,
    out: Path | None = None,
    output_format: str = "markdown",
    list_references: bool = False,
) -> int:
    if list_references:
        print(json.dumps(privacy_source_references(), indent=2, sort_keys=True))
        return 0
    if profile is None:
        print("Error: --profile is required unless --list-references is used.")
        return 2
    if output_format.casefold() not in {"markdown", "json"}:
        print("Error: --format must be markdown or json.")
        return 2
    loaded = load_privacy_profile(profile)
    report = build_privacy_report(loaded)
    rendered = (
        json.dumps(report.json_report, indent=2, sort_keys=True)
        if output_format.casefold() == "json"
        else report.markdown
    )
    if out is not None:
        write_privacy_report(report, out, output_format=output_format)
        print(f"Wrote privacy evaluation report to {out}")
    else:
        print(rendered.rstrip())
    return 0


def register_typer_commands(root_app: Any, typer: Any, _console: Any) -> None:
    @root_app.command(name="privacy-eval")
    def privacy_eval_command(
        profile: Path | None = typer.Option(None, "--profile", help="PrivacyEvalProfile JSON."),
        out: Path | None = typer.Option(None, "--out", "-o", help="Optional report output path."),
        output_format: str = typer.Option("markdown", "--format", help="markdown or json."),
        list_references: bool = typer.Option(False, "--list-references", help="Print contextual privacy references."),
    ) -> None:
        raise typer.Exit(
            run_privacy_eval(
                profile=profile,
                out=out,
                output_format=output_format,
                list_references=list_references,
            )
        )


def add_privacy_eval_argparse(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser("privacy-eval", help="Static privacy-risk evaluation for agent profiles.")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--out", "-o", type=Path)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--list-references", action="store_true")
    parser.set_defaults(func=_argparse_privacy_eval)


def run_argparse_command(args: argparse.Namespace) -> int:
    return int(args.func(args) or 0)


def _argparse_privacy_eval(args: argparse.Namespace) -> int:
    return run_privacy_eval(
        profile=args.profile,
        out=args.out,
        output_format=args.format,
        list_references=args.list_references,
    )
