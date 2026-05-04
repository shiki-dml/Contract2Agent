from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_github_pages_entrypoint_references_existing_static_assets() -> None:
    demo_html = ROOT / "docs" / "playground" / "index.html"
    html = demo_html.read_text(encoding="utf-8")

    for asset in (
        "../assets/styles.css",
        "../assets/app.js",
        "../assets/contract2agent-preview.svg",
    ):
        assert asset in html
        assert (demo_html.parent / asset).resolve().exists(), asset

    assert "Contract2Agent" in html
    assert "not legal advice" in html
    assert "docs/" in html


def test_github_pages_entrypoint_uses_deployable_relative_assets() -> None:
    docs_root = ROOT / "docs"
    demo_html = docs_root / "playground" / "index.html"
    html = demo_html.read_text(encoding="utf-8")
    css = (docs_root / "assets" / "styles.css").read_text(encoding="utf-8")

    assert (docs_root / "index.md").exists()
    assert not (docs_root / "index.html").exists()
    assert demo_html.exists()
    assert "localhost" not in html
    assert "127.0.0.1" not in html
    assert "C:\\" not in html
    assert "/mnt/" not in html
    assert "/Users/" not in html

    for asset in _html_asset_refs(html):
        assert not asset.startswith(("/", "C:\\"))
        assert (demo_html.parent / asset).exists(), asset

    for asset in _css_asset_refs(css):
        assert not asset.startswith(("/", "C:\\"))
        assert (docs_root / "assets" / asset).exists(), asset


def test_github_pages_form_contains_required_dispute_inputs() -> None:
    html = (ROOT / "docs" / "playground" / "index.html").read_text(
        encoding="utf-8"
    )

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

    for button_id in (
        "load-sample",
        "copy-markdown",
        "copy-json",
        "copy-test-case",
        "reset-form",
    ):
        assert f'id="{button_id}"' in html

    assert "Analyze / Diagnose" in html
    assert 'id="result-output"' in html
    assert 'id="evaluation-lab"' in html
    assert "Evaluation Lab" in html
    assert "Generated Test Case Preview" in html
    assert "Input Completeness" in html
    assert "Evidence Coverage" in html
    assert "Risk Signal" in html
    assert "Markdown/JSON export" in html
    assert "does not run pytest in the browser" in html


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
    assert 'getElementById("copy-test-case").addEventListener' in app_js
    assert 'getElementById("reset-form").addEventListener' in app_js
    assert 'querySelectorAll(".sample-chip")' in app_js
    assert "function computeEvaluationMetrics" in app_js
    assert "function buildTestCasePreview" in app_js
    assert "function renderEvaluationPanel" in app_js
    assert "latestTestCase" in app_js
    assert "Generated Test Case Preview" in app_js


def test_github_pages_javascript_syntax_or_static_fallback() -> None:
    app_js_path = ROOT / "docs" / "assets" / "app.js"
    node = shutil.which("node")

    if node:
        completed = subprocess.run(
            [node, "--check", str(app_js_path)],
            text=True,
            capture_output=True,
        )
        assert completed.returncode == 0, completed.stderr
        return

    app_js = app_js_path.read_text(encoding="utf-8")
    for required in (
        "function collectInput",
        "function analyzeDispute",
        "function computeEvaluationMetrics",
        "function buildTestCasePreview",
        "function renderEvaluationPanel",
    ):
        assert required in app_js


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
    assert "AgentDoctor" not in readme
    assert "# AgentDoctor" not in readme
    assert "AgentDoctor is" not in readme
    assert "not legal advice" in readme.lower()


def test_readme_explains_evaluation_first_design() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for required in (
        "Evaluation-first design",
        "Evaluation Lab",
        "Golden tests",
        "CLI smoke tests",
        "GitHub Pages static tests",
        "python -m pytest",
        "docs/playground/index.html",
        "Copy Test Case JSON",
    ):
        assert required in readme


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


def _html_asset_refs(html: str) -> list[str]:
    refs: list[str] = []
    patterns = (
        r"<link\b[^>]*\bhref=\"([^\"]+)\"",
        r"<script\b[^>]*\bsrc=\"([^\"]+)\"",
        r"<img\b[^>]*\bsrc=\"([^\"]+)\"",
        r"fetch\(\s*[\"']([^\"']+)[\"']",
    )
    for pattern in patterns:
        refs.extend(
            ref
            for ref in re.findall(pattern, html)
            if _is_local_asset_ref(ref)
        )
    return refs


def _css_asset_refs(css: str) -> list[str]:
    return [
        ref.strip("\"'")
        for ref in re.findall(r"url\(([^)]+)\)", css)
        if _is_local_asset_ref(ref.strip("\"'"))
    ]


def _is_local_asset_ref(ref: str) -> bool:
    return not (
        ref.startswith(("#", "http://", "https://", "data:", "mailto:", "tel:"))
        or ref == "./"
    )
