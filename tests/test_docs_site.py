from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_github_pages_entrypoint_references_existing_static_assets() -> None:
    index = ROOT / "docs" / "index.html"
    html = index.read_text(encoding="utf-8")

    for asset in (
        "assets/styles.css",
        "assets/app.js",
        "assets/contract2agent-preview.svg",
    ):
        assert asset in html
        assert (index.parent / asset).exists(), asset

    assert "Contract2Agent" in html
    assert "not legal advice" in html
    assert "docs/" in html


def test_github_pages_form_contains_required_dispute_inputs() -> None:
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")

    required_ids = {
        "contract-text",
        "dispute-description",
        "claimant-position",
        "respondent-position",
        "evidence",
        "desired-outcome",
        "contract-type",
        "dispute-type",
        "risk-mode",
        "metadata",
        "output-format",
        "diagnosis-depth",
    }
    for element_id in required_ids:
        assert f'id="{element_id}"' in html

    for button_id in ("load-sample", "copy-markdown", "copy-json", "reset-form"):
        assert f'id="{button_id}"' in html


def test_github_pages_app_is_static_and_wires_expected_actions() -> None:
    app_js = (ROOT / "docs" / "assets" / "app.js").read_text(encoding="utf-8")

    forbidden_runtime_calls = ("fetch(", "XMLHttpRequest", "new WebSocket", "import(")
    for call in forbidden_runtime_calls:
        assert call not in app_js

    assert "function diagnose" in app_js
    assert "function markdownReport" in app_js
    assert "JSON.stringify" in app_js
    assert 'dispute.includes("refund")' in app_js
    assert 'groups.includes("refund")' not in app_js
    assert 'getElementById("copy-markdown").addEventListener' in app_js
    assert 'getElementById("copy-json").addEventListener' in app_js
    assert 'getElementById("reset-form").addEventListener' in app_js
    assert 'querySelectorAll(".sample-chip")' in app_js


def test_static_sample_cases_are_valid_and_complete() -> None:
    examples_dir = ROOT / "docs" / "examples"
    samples = sorted(examples_dir.glob("*.json"))

    assert {sample.name for sample in samples} == {
        "delivery-delay-dispute.json",
        "refund-dispute.json",
        "saas-suspension-dispute.json",
        "service-payment-dispute.json",
        "termination-dispute.json",
    }

    required_keys = {
        "name",
        "contract_type",
        "dispute_type",
        "desired_outcome",
        "contract_text",
        "dispute_description",
        "claimant_position",
        "respondent_position",
        "evidence",
        "configuration",
    }
    for sample in samples:
        data = json.loads(sample.read_text(encoding="utf-8"))
        assert required_keys.issubset(data), sample.name
        assert data["evidence"], sample.name
        assert data["configuration"]["diagnosis_depth"] in {"Quick", "Standard", "Detailed"}


def test_readme_preview_asset_and_local_links_exist() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    image_paths = [
        image_path
        for image_path in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
        if not image_path.startswith(("http://", "https://"))
    ]
    assert "docs/assets/contract2agent-preview.svg" in image_paths
    for image_path in image_paths:
        assert (ROOT / image_path).exists(), image_path

    local_links = [
        target
        for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", readme)
        if not target.startswith(("http://", "https://", "#"))
    ]
    for target in local_links:
        assert (ROOT / target).exists(), target


def test_readme_internal_anchor_links_match_headings() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    anchors = {
        target.removeprefix("#")
        for target in re.findall(r"(?<!!)\[[^\]]+\]\((#[^)]+)\)", readme)
    }
    headings = {
        re.sub(r"[^a-z0-9 -]", "", heading.lower()).strip().replace(" ", "-")
        for heading in re.findall(r"^#{1,6}\s+(.+)$", readme, flags=re.MULTILINE)
    }

    assert anchors <= headings


def test_readme_project_identity_is_contract2agent() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert readme.startswith("# Contract2Agent")
    assert "Python import package: `contract2agent`" in readme
    assert "CLI: `c2a`" in readme
    assert "automated lawyer" not in readme.lower()
    assert "# AgentDoctor" not in readme
    assert "AgentDoctor is" not in readme


def test_packaging_declares_c2a_entrypoint_and_pytest_dev_dependency() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["name"] == "contract2agent"
    assert pyproject["project"]["scripts"]["c2a"] == "contract2agent.cli:main"
    assert any(
        dependency.split(">=", 1)[0] == "pytest"
        for dependency in pyproject["project"]["optional-dependencies"]["dev"]
    )


def test_docs_are_preserved_and_not_ignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert (ROOT / "docs").is_dir()
    assert (ROOT / "docs" / "audits").is_dir()
    assert not re.search(r"(^|/|\\)docs/?$", gitignore, flags=re.MULTILINE)
    assert "__pycache__/" in gitignore
    assert ".pytest_cache/" in gitignore
    assert ".tmp/" in gitignore
    assert "build/" in gitignore
    assert "dist/" in gitignore
    assert "*.egg-info/" in gitignore
