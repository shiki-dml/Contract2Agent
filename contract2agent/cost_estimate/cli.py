from __future__ import annotations

from pathlib import Path

from contract2agent.cost_estimate.models import CostEstimateOptions, EstimatedDiagnosticCost
from contract2agent.cost_estimate.report import (
    format_json_report,
    format_terminal_summary,
    write_cost_reports,
)
from contract2agent.cost_estimate.rules import build_cost_estimate


def run_cost_estimate(
    options: CostEstimateOptions | None = None,
    *,
    cwd: Path | None = None,
    write_reports: bool = True,
) -> tuple[EstimatedDiagnosticCost, str]:
    options = options or CostEstimateOptions()
    estimate = build_cost_estimate(options, cwd=cwd)
    output_dir = _output_dir(options, estimate)
    if write_reports:
        write_cost_reports(estimate, output_dir)
    output_format = options.output_format.casefold()
    if output_format == "json":
        return estimate, format_json_report(estimate)
    if output_format == "markdown":
        return estimate, format_terminal_summary(estimate)
    raise ValueError("--format must be markdown or json")


def _output_dir(options: CostEstimateOptions, estimate: EstimatedDiagnosticCost) -> Path:
    if options.output is not None:
        output = options.output.expanduser()
        if output.is_absolute():
            return output
        return Path(estimate.project_root) / output
    return Path(estimate.project_root) / ".agentdoctor" / "cost"
