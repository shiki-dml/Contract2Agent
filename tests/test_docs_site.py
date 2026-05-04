from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


SAAS_NOTICE_CURE_FIXTURE = {
    "contractType": "SaaS Agreement",
    "disputeType": "Payment Delay",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Escalation review",
    "desiredOutcome": "Assess suspension timing, invoice payment, service credits, and damages limits.",
    "contractText": (
        "This SaaS Agreement provides that the customer must pay all undisputed invoices "
        "within 30 days of receipt. If the customer disputes an invoice, the customer must "
        "provide written notice describing the disputed amount and the basis for dispute "
        "within 10 days of receiving the invoice.\n\n"
        "The provider may suspend access to the platform only after giving written notice "
        "of non-payment and allowing a 10-day cure period. Suspension must be limited to "
        "the affected services where commercially reasonable.\n\n"
        "The provider commits to 99.5% monthly uptime, excluding outages caused by "
        "customer non-payment, scheduled maintenance, force majeure, or customer-side "
        "systems. The customer's exclusive remedy for verified SLA failure is a service "
        "credit.\n\n"
        "Neither party is liable for indirect, incidental, consequential, or lost-profit "
        "damages. The total liability of either party is capped at fees paid in the three "
        "months before the event giving rise to the claim.\n\n"
        "All notices must be sent by email to the notice address listed in the order form "
        "and are deemed received on the next business day."
    ),
    "disputeDescription": (
        "The provider suspended the customer's access on March 18 after two invoices dated "
        "February 1 and March 1 remained unpaid. The provider says it sent a non-payment "
        "notice on March 5 and waited more than 10 days before suspension.\n\n"
        "The customer argues that both invoices were disputed because the platform had "
        "repeated downtime in February. The customer also claims the suspension caused "
        "lost revenue and wants damages beyond service credits.\n\n"
        "The provider says the customer never sent a proper written invoice dispute notice "
        "within 10 days, and that the alleged downtime was caused by the customer's own "
        "integration errors."
    ),
    "claimantPosition": (
        "Provider claims the customer failed to pay undisputed invoices, did not send a "
        "valid invoice dispute notice, and failed to cure after written notice. Provider "
        "seeks confirmation that suspension was contractually permitted and wants payment "
        "of outstanding invoices."
    ),
    "respondentPosition": (
        "Customer claims the invoices were disputed due to SaaS downtime and poor service "
        "performance. Customer argues the provider suspended access too aggressively and "
        "seeks service credits, lost revenue damages, and restoration of access."
    ),
    "evidence": (
        "Available:\n"
        "- February 1 invoice\n"
        "- March 1 invoice\n"
        "- Provider email dated March 5 titled \"Notice of Non-Payment\"\n"
        "- Access suspension log dated March 18\n"
        "- Customer support tickets from February reporting downtime\n"
        "- Internal provider uptime report showing 99.7% monthly uptime\n"
        "- Integration error logs showing customer API authentication failures\n\n"
        "Missing or unclear:\n"
        "- Order form notice email address\n"
        "- Proof that the March 5 notice was sent to the contractual notice address\n"
        "- Customer written invoice dispute notice, if any\n"
        "- Timestamped SLA monitoring data from an independent source\n"
        "- Calculation of claimed lost revenue"
    ),
    "metadata": '{"service":"SaaS"}',
}


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


def test_playground_force_majeure_clause_signal_is_not_active_issue() -> None:
    fixture = dict(SAAS_NOTICE_CURE_FIXTURE)
    fixture["disputeDescription"] = (
        "The provider suspended access after unpaid invoices and the customer disputes "
        "the uptime calculation. No party invokes force majeure; the dispute is about "
        "payment timing and uptime records only."
    )
    fixture["claimantPosition"] = "Provider says invoices were unpaid after notice."
    fixture["respondentPosition"] = "Customer says downtime caused invoice disputes."
    fixture["evidence"] = "Invoice, notice email, suspension log, and uptime report."

    diagnosis = _run_playground_diagnosis(fixture)["diagnosis"]

    assert any(
        "force majeure" in signal.lower()
        for signal in diagnosis["clause_signals"]
    )
    assert all(
        "force majeure" not in tag.lower()
        for tag in diagnosis["active_issue_tags"]
    )


def test_playground_notice_cure_critical_gaps_prevent_low_risk() -> None:
    fixture = dict(SAAS_NOTICE_CURE_FIXTURE)

    diagnosis = _run_playground_diagnosis(fixture)["diagnosis"]

    assert diagnosis["risk_signal"] != "low"
    assert diagnosis["risk"]["level"] != "low"
    assert any("cannot be low" in reason for reason in diagnosis["risk"]["rationale"])


def test_playground_saas_key_issues_are_case_specific() -> None:
    diagnosis = _run_playground_diagnosis(SAAS_NOTICE_CURE_FIXTURE)["diagnosis"]
    key_issue_text = "\n".join(diagnosis["key_issues"])

    for required in (
        "February 1",
        "March 1",
        "March 5",
        "March 18",
        "10-day cure period",
        "SLA/uptime",
        "downtime",
        "service credits",
        "lost revenue",
        "liability cap",
        "prior three months",
    ):
        assert required in key_issue_text

    generic_taxonomy_descriptions = {
        "Whether invoices, fees, or refund amounts are owed and undisputed",
        "Whether written notice and any cure period were properly triggered",
        "Whether uncontrollable events or force majeure excuses performance",
    }
    assert not generic_taxonomy_descriptions.intersection(diagnosis["key_issues"])


def test_playground_structured_output_separates_core_fields() -> None:
    diagnosis = _run_playground_diagnosis(SAAS_NOTICE_CURE_FIXTURE)["diagnosis"]

    required_fields = {
        "contract_type",
        "dispute_type",
        "active_issue_tags",
        "clause_signals",
        "evidence_gaps",
        "timeline_facts",
        "risk",
        "key_issues",
        "suggested_next_steps",
    }
    assert required_fields.issubset(diagnosis)
    assert "SaaS Agreement" in diagnosis["contract_type"]
    assert "Notice/Cure Period" in diagnosis["dispute_type"]
    assert "Payment/Suspension" in diagnosis["dispute_type"]
    assert "force majeure" not in {
        tag.lower() for tag in diagnosis["active_issue_tags"]
    }
    assert any(
        "force majeure" in signal.lower()
        for signal in diagnosis["clause_signals"]
    )
    assert diagnosis["active_issue_tags"] != diagnosis["clause_signals"]
    assert any("March 5" in fact for fact in diagnosis["timeline_facts"])


def test_playground_exports_use_corrected_structured_diagnosis() -> None:
    output = _run_playground_diagnosis(SAAS_NOTICE_CURE_FIXTURE)
    exported = json.loads(output["json"])
    markdown = output["markdown"]
    active_section = markdown.split("## Active Issue Tags", 1)[1].split(
        "## Key Issues", 1
    )[0]

    assert exported["active_issue_tags"] == output["diagnosis"]["active_issue_tags"]
    assert exported["clause_signals"] == output["diagnosis"]["clause_signals"]
    assert exported["timeline_facts"] == output["diagnosis"]["timeline_facts"]
    assert all("force majeure" not in tag.lower() for tag in exported["active_issue_tags"])
    assert "force majeure" not in active_section.lower()
    assert "## Clause Signals" in markdown
    assert "## Timeline Facts" in markdown


def test_mkdocs_nav_preserves_github_pages_playground_route() -> None:
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "Playground: playground/index.html" in mkdocs
    assert (ROOT / "docs" / "playground" / "index.html").exists()


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


def _run_playground_diagnosis(input_case: dict) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required to execute the static playground diagnosis")

    app_js_path = ROOT / "docs" / "assets" / "app.js"
    script = f"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync({json.dumps(str(app_js_path))}, "utf8");
function makeElement(id) {{
  return {{
    id,
    value: "",
    textContent: "",
    innerHTML: "",
    className: "",
    dataset: {{}},
    style: {{}},
    addEventListener() {{}},
    reset() {{}},
    remove() {{}},
    select() {{}},
    setAttribute() {{}},
    classList: {{ toggle() {{}}, remove() {{}}, add() {{}} }}
  }};
}}
const elements = new Map();
[
  "diagnosis-form",
  "result-output",
  "evaluation-output",
  "risk-badge",
  "copy-status",
  "sample-select",
  "contract-type",
  "dispute-type",
  "output-format",
  "diagnosis-depth",
  "risk-mode",
  "desired-outcome",
  "contract-text",
  "dispute-description",
  "claimant-position",
  "respondent-position",
  "evidence",
  "metadata",
  "load-sample",
  "copy-markdown",
  "copy-json",
  "copy-test-case",
  "reset-form"
].forEach((id) => elements.set(id, makeElement(id)));
const sampleButtons = [
  "service-payment",
  "delivery-delay",
  "termination-cure",
  "refund-dispute",
  "saas-suspension"
].map((sample) => ({{
  dataset: {{ sample }},
  classList: {{ toggle() {{}}, remove() {{}}, add() {{}} }},
  addEventListener() {{}}
}}));
const document = {{
  getElementById(id) {{
    if (!elements.has(id)) {{
      elements.set(id, makeElement(id));
    }}
    return elements.get(id);
  }},
  querySelectorAll(selector) {{
    return selector === ".sample-chip" ? sampleButtons : [];
  }},
  createElement(tag) {{
    return makeElement(tag);
  }},
  body: {{ appendChild() {{}}, removeChild() {{}} }},
  execCommand() {{ return true; }}
}};
const context = {{ document, window: {{}}, navigator: {{}}, console }};
vm.runInNewContext(code, context);
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const api = context.window.Contract2AgentPlayground;
const diagnosis = api.analyzeDispute(input);
const markdown = api.markdownReport(diagnosis);
const jsonOutput = JSON.stringify(
  {{
    ...diagnosis,
    structured_diagnosis_preview: api.structuredPreview(diagnosis)
  }},
  null,
  2
);
process.stdout.write(JSON.stringify({{ diagnosis, markdown, json: jsonOutput }}));
"""
    completed = subprocess.run(
        [node, "-e", script],
        input=json.dumps(input_case),
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)
