from __future__ import annotations

from pathlib import Path

from contract2agent.generator import generate_project
from contract2agent.parser import parse_requirement
from contract2agent.schema import AgentContract, load_contract


def compile_contract(contract_path: str | Path, output_dir: str | Path) -> Path:
    contract = load_contract(contract_path)
    return generate_project(contract, output_dir)


def create_project_from_requirement(requirement: str, output_dir: str | Path) -> Path:
    contract = parse_requirement(requirement)
    return generate_project(contract, output_dir)


def create_demo_project(output_dir: str | Path) -> Path:
    requirement = (
        "Build a paper PDF reader agent that extracts definitions, theorems, "
        "and proof ideas, handles missing file errors, and must not browse or "
        "use web search."
    )
    return create_project_from_requirement(requirement, output_dir)


def compile_contract_model(contract: AgentContract, output_dir: str | Path) -> Path:
    return generate_project(contract, output_dir)
