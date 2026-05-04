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


LATE_DELIVERY_FORCE_MAJEURE_NEGATIVE_FIXTURE = {
    "contractType": "Sales Contract",
    "disputeType": "Late Delivery",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Evidence-first",
    "desiredOutcome": "Assess rejection rights, cure timing, and damages limits.",
    "contractText": (
        "Seller must deliver a production-ready integration package by April 1. "
        "If delivery is late, Buyer may send a Delivery Delay Notice to the contractual "
        "notice contacts, and Seller has a 10-day cure period. Buyer must review the "
        "delivery or any revised package within a 5-business-day review period. "
        "Liquidated damages for late delivery must be calculated from proven delay "
        "days and are capped at 10% of project fees. Lost revenue is excluded, and "
        "total liability is capped at fees paid during the six months before the claim. "
        "Force majeure excuses delay caused by natural disaster, government order, "
        "strike, war, or other external uncontrollable event."
    ),
    "disputeDescription": (
        "The April 1 production-ready delivery milestone was missed when Seller delivered "
        "on April 8. Buyer sent an April 9 Delivery Delay Notice to the project notice "
        "contacts. Seller provided a revised package on April 17, and Buyer rejected it "
        "on April 23 because API mapping defects still blocked launch. No party claims "
        "that a natural disaster, government order, strike, war, or other external "
        "uncontrollable event caused the delay."
    ),
    "claimantPosition": (
        "Buyer says the April 8 delivery was late, the April 9 Delivery Delay Notice "
        "started the 10-day cure period, and the April 17 revised package still had API "
        "mapping defects. Buyer seeks liquidated damages and lost revenue."
    ),
    "respondentPosition": (
        "Seller says the April 17 revised package cured the issues and Buyer waited too "
        "long to reject on April 23 under the 5-business-day review period. Seller also "
        "invokes the 10% liquidated damages cap, lost revenue exclusion, and six-month "
        "fee liability cap."
    ),
    "evidence": (
        "Available:\n"
        "- Project schedule showing April 1 production-ready milestone\n"
        "- Delivery log dated April 8\n"
        "- April 9 Delivery Delay Notice\n"
        "- Contractual notice contact list\n"
        "- Revised package changelog dated April 17\n"
        "- April 23 rejection email\n"
        "- API mapping defect tickets\n"
        "- Liquidated damages spreadsheet\n\n"
        "Missing or unclear:\n"
        "- Proof that April 9 notice reached all contractual notice contacts\n"
        "- Final liquidated damages calculation"
    ),
    "metadata": '{"delivery_type":"integration package"}',
}


POSITIVE_FORCE_MAJEURE_DELIVERY_FIXTURE = {
    "contractType": "Service Agreement",
    "disputeType": "Late Delivery",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Evidence-first",
    "desiredOutcome": "Assess force majeure notice, mitigation, cover costs, and damages.",
    "contractText": (
        "Provider must complete the customer migration milestone by June 30, and time "
        "is of the essence. Force majeure includes government orders and emergency "
        "closures that prevent timely performance. Provider must send force majeure "
        "notice to the SOW notice contacts within five business days after becoming "
        "aware of the affected migration impact. Notices are deemed received on the "
        "next-business-day after sending. Provider must use commercially reasonable "
        "mitigation, including remote migration tools, alternate staffing, and alternate "
        "site access where available. Customer may recover reasonable, necessary, direct, "
        "and documented temporary migration support or cover costs. Liquidated damages "
        "for unexcused delay accrue at 1.5% per full week and are capped at 12% of the "
        "monthly service fee. Lost-profit and consequential damages, including lost "
        "revenue, are excluded. Total liability is capped at fees paid during the six "
        "months before the event."
    ),
    "disputeDescription": (
        "A government emergency order was issued on June 20 closing the data center used "
        "for the migration. Provider says it first became aware of the migration impact "
        "on June 21 through an internal awareness email. Provider sent a force majeure "
        "notice on June 28. The contractual migration deadline was June 30. Customer "
        "retained a temporary consultant on July 18 to keep migration work moving. "
        "Provider reached partial completion on July 20 and final completion on August 5."
    ),
    "claimantPosition": (
        "Customer says the June 28 force majeure notice was late, mitigation was thin, "
        "and the July 18 temporary consultant was a reasonable cover cost. Customer seeks "
        "liquidated damages and lost revenue."
    ),
    "respondentPosition": (
        "Provider says the June 20 government emergency order qualifies as force majeure, "
        "it became aware on June 21, sent timely notice on June 28, used remote migration "
        "tools and alternate staffing, and completed as soon as emergency closures allowed. "
        "Provider invokes the 1.5% weekly liquidated damages formula, 12% cap, lost-profit "
        "and consequential damages exclusion, and six-month fee liability cap."
    ),
    "evidence": (
        "Available:\n"
        "- June 20 government emergency order\n"
        "- June 21 provider internal awareness email\n"
        "- June 28 force majeure notice\n"
        "- SOW notice contacts\n"
        "- June 30 migration milestone in the SOW\n"
        "- Remote migration tool logs\n"
        "- Alternate staffing schedule\n"
        "- Alternate site access request\n"
        "- July 18 temporary consultant invoice\n"
        "- July 20 partial completion log\n"
        "- August 5 final completion certificate\n"
        "- Liquidated damages calculation worksheet\n\n"
        "Missing or unclear:\n"
        "- Proof that the June 28 notice reached all SOW notice contacts\n"
        "- Documentation supporting the temporary consultant rate"
    ),
    "metadata": '{"project":"migration"}',
}


REFUND_TERMINATION_ACCEPTANCE_FIXTURE = {
    "contractType": "Service Agreement",
    "disputeType": "Refund / Termination / Acceptance",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Evidence-first",
    "desiredOutcome": "Assess refund, termination timing, acceptance, and damages limits.",
    "contractText": (
        "Customer paid a $60,000 prepaid implementation fee for onboarding services. "
        "The prepaid implementation fee is non-refundable except that Customer may "
        "receive a pro-rata refund after Provider's uncured material breach. Customer "
        "must send written breach notice to the SOW notice contacts and allow a 15-day "
        "cure period. Notices are deemed received on the next business day after "
        "sending.\n\n"
        "The SOW requires Provider to complete the data import milestone by March 15. "
        "The SOW also requires Provider to complete the administrator training "
        "milestone by March 25. Any delivery package requesting formal milestone "
        "acceptance must be reviewed within a 5-business-day rejection period. Any "
        "rejection must identify material defects with reasonable specificity.\n\n"
        "Consequential damages and lost-profit damages are excluded. Total liability is "
        "capped at fees paid during the six months before the event. Provider's "
        "indemnity obligation applies only to third-party IP infringement claims. Force "
        "majeure excuses performance only for external uncontrollable events."
    ),
    "disputeDescription": (
        "Customer paid the $60,000 prepaid implementation fee on March 5. Customer says "
        "Provider missed the March 15 data import milestone and the March 25 "
        "administrator training milestone. Provider sent a partial data import delivery "
        "package on March 28. Customer sent an April 2 breach notice and terminated on "
        "April 20 after the cure period. Provider responded on April 10 that the March "
        "28 partial delivery substantially completed onboarding services. Customer seeks "
        "a $42,000 pro-rata refund plus lost productivity and internal delay costs. The "
        "parties dispute whether the March 28 package requested formal milestone "
        "acceptance and whether any rejection was timely and specific. No party seeks "
        "indemnity, and there is no third-party IP or infringement claim. There is no "
        "confidentiality dispute and no party invokes force majeure."
    ),
    "claimantPosition": (
        "Customer says missed milestones and uncured breach justify termination and a "
        "$42,000 pro-rata refund. Customer also claims lost productivity from internal "
        "onboarding delays."
    ),
    "respondentPosition": (
        "Provider says the March 28 partial data import substantially completed the "
        "onboarding services, the April 2 breach notice was defective or not sent to "
        "the required SOW notice contacts, any rejection was untimely or nonspecific, "
        "and any recovery is limited by the non-refundable fee language, damages "
        "exclusions, and six-month fee liability cap."
    ),
    "evidence": (
        "Available:\n"
        "- March 5 payment receipt for the $60,000 prepaid implementation fee\n"
        "- SOW milestone schedule listing March 15 data import and March 25 administrator training\n"
        "- March 28 partial data import delivery package\n"
        "- April 2 customer breach notice\n"
        "- April 10 provider response email\n"
        "- April 20 termination email\n\n"
        "Missing or unclear:\n"
        "- Statement of work notice contact list\n"
        "- Proof that the April 2 breach notice was sent to the contractual notice contacts\n"
        "- Whether the March 28 delivery package requested formal milestone acceptance\n"
        "- Whether the customer rejected within 5 business days\n"
        "- Whether rejection identified material defects with reasonable specificity\n"
        "- Detailed work-completion records showing performed vs unperformed services\n"
        "- Basis for the $42,000 pro-rata refund calculation\n"
        "- Evidence supporting lost productivity damages"
    ),
    "metadata": '{"project":"onboarding","payment":"prepaid"}',
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


def test_playground_late_delivery_blocks_denied_force_majeure_issue() -> None:
    diagnosis = _run_playground_diagnosis(
        LATE_DELIVERY_FORCE_MAJEURE_NEGATIVE_FIXTURE
    )["diagnosis"]

    assert all(
        "force majeure" not in tag.lower()
        for tag in diagnosis["active_issue_tags"]
    )
    assert any(
        signal == "force majeure clause mentioned but not fact-triggered"
        for signal in diagnosis["clause_signals"]
    )


def test_playground_late_delivery_key_issues_are_fact_specific() -> None:
    diagnosis = _run_playground_diagnosis(
        LATE_DELIVERY_FORCE_MAJEURE_NEGATIVE_FIXTURE
    )["diagnosis"]
    key_issue_text = "\n".join(diagnosis["key_issues"])

    for required in (
        "April 1 production-ready delivery milestone",
        "April 8",
        "April 9 Delivery Delay Notice",
        "contractual notice contacts",
        "10-day cure period",
        "April 17 revised package",
        "April 23 rejection",
        "5-business-day review period",
        "API mapping defects",
        "liquidated damages calculation",
        "10%",
        "lost revenue exclusion",
        "six-month fee liability cap",
    ):
        assert required in key_issue_text

    assert (
        "Whether uncontrollable events or force majeure excuses performance"
        not in key_issue_text
    )
    assert "fact-triggered force majeure event" not in key_issue_text


def test_playground_late_delivery_exports_keep_force_majeure_clause_only() -> None:
    output = _run_playground_diagnosis(
        LATE_DELIVERY_FORCE_MAJEURE_NEGATIVE_FIXTURE
    )
    exported = json.loads(output["json"])
    markdown = output["markdown"]
    active_section = markdown.split("## Active Issue Tags", 1)[1].split(
        "## Key Issues", 1
    )[0]

    assert all(
        "force majeure" not in tag.lower()
        for tag in exported["active_issue_tags"]
    )
    assert "force majeure" not in active_section.lower()
    assert "force majeure clause mentioned but not fact-triggered" in exported[
        "clause_signals"
    ]
    assert "force majeure clause mentioned but not fact-triggered" in markdown
    assert "timeline_facts" in exported
    assert "risk" in exported


def test_playground_positive_force_majeure_avoids_saas_template_leakage() -> None:
    diagnosis = _run_playground_diagnosis(
        POSITIVE_FORCE_MAJEURE_DELIVERY_FIXTURE
    )["diagnosis"]
    active_tags = {tag.lower() for tag in diagnosis["active_issue_tags"]}
    exported_text = json.dumps(diagnosis).lower()

    for expected in (
        "force majeure",
        "delivery",
        "notice",
        "mitigation",
        "cover costs",
        "liquidated damages",
        "damages",
        "liability limitation",
    ):
        assert expected in active_tags

    for forbidden in (
        "sla",
        "service credit",
        "suspension",
        "invoice",
        "payment timing",
    ):
        assert forbidden not in active_tags

    for forbidden_text in (
        "sla/uptime",
        "service credit",
        "support tickets",
        "customer-side integration",
        "uptime report",
        "downtime",
        "suspension",
    ):
        assert forbidden_text not in exported_text

    assert "SLA/Service Credit" not in diagnosis["dispute_type"]
    assert "Delivery/Acceptance" not in diagnosis["dispute_type"]


def test_playground_positive_force_majeure_clauses_issues_and_timeline() -> None:
    diagnosis = _run_playground_diagnosis(
        POSITIVE_FORCE_MAJEURE_DELIVERY_FIXTURE
    )["diagnosis"]
    key_issue_text = "\n".join(diagnosis["key_issues"])
    clause_text = "\n".join(diagnosis["clause_signals"])
    timeline_text = "\n".join(diagnosis["timeline_facts"])

    for expected_dispute_type in (
        "Late Delivery",
        "Force Majeure",
        "Notice",
        "Damages/Liability",
        "Cover Costs/Mitigation",
    ):
        assert expected_dispute_type in diagnosis["dispute_type"]

    for expected_clause in (
        "June 30 migration milestone",
        "time is of the essence",
        "5-business-day force majeure notice requirement",
        "government orders / emergency closures",
        "commercially reasonable mitigation",
        "temporary migration support / cover costs",
        "liquidated damages formula at 1.5% per full week capped at 12%",
        "lost-profit damages exclusion",
        "lost revenue exclusion",
        "six-month",
        "contractual notice contacts",
        "deemed receipt rule",
    ):
        assert expected_clause in clause_text

    for forbidden_clause in (
        "suspension rights",
        "payment timing",
        "SLA/service credit",
    ):
        assert forbidden_clause not in clause_text

    for expected_issue in (
        "Whether the June 20 government emergency order qualifies as a force majeure event.",
        "Whether the provider became aware of the migration impact on June 20 or June 21.",
        "Whether the June 28 force majeure notice was timely under the 5-business-day notice requirement.",
        "Whether the June 28 notice was sent to the contractual notice contacts.",
        "Whether the provider used commercially reasonable mitigation, including remote migration tools and alternate staffing.",
        "Whether the July 18 temporary consultant cost was reasonable, necessary, direct, and documented cover cost.",
        "Whether the July 20 partial completion and August 5 final completion leave any period of unexcused delay.",
        "Whether liquidated damages are calculated at 1.5% per full week of unexcused delay and capped at 12% of the monthly service fee.",
        "Whether claimed lost revenue is barred by the lost revenue exclusion.",
        "Whether the six-month fee liability cap limits recovery.",
    ):
        assert expected_issue in key_issue_text

    for expected_timeline in (
        "June 20: government emergency order issued.",
        "June 21: provider internal awareness email or migration-impact awareness.",
        "June 28: force majeure notice.",
        "June 30: contractual migration deadline.",
        "July 18: temporary consultant retained.",
        "July 20: partial completion.",
        "August 5: final completion.",
    ):
        assert expected_timeline in timeline_text


def test_playground_positive_force_majeure_next_steps_and_exports_are_scoped() -> None:
    output = _run_playground_diagnosis(POSITIVE_FORCE_MAJEURE_DELIVERY_FIXTURE)
    exported = json.loads(output["json"])
    markdown = output["markdown"]
    next_steps = "\n".join(exported["suggested_next_steps"])

    for expected_step in (
        "Build a June 20 / June 21 / June 28 / June 30 / July 18 / July 20 / August 5 timeline.",
        "Verify the SOW notice contacts.",
        "Verify proof that the force majeure notice was sent to contractual contacts.",
        "Determine the actual awareness date for the affected migration.",
        "Assess whether notice was within the contractual business-day notice period.",
        "Review mitigation evidence for remote tools, alternate staffing, and alternate site access.",
        "Evaluate whether the temporary consultant was reasonable and necessary cover.",
        "Calculate liquidated damages by full weeks of unexcused delay using 1.5% weekly and 12% cap.",
        "Analyze lost revenue under the lost-profit/consequential damages exclusion.",
        "Apply the six-month fee liability cap.",
    ):
        assert expected_step in next_steps

    for forbidden_step in (
        "invoice",
        "cure / suspension",
        "service credit",
        "support tickets",
        "uptime",
        "customer-side integration",
    ):
        assert forbidden_step not in next_steps.lower()

    assert exported["active_issue_tags"] == output["diagnosis"]["active_issue_tags"]
    assert exported["clause_signals"] == output["diagnosis"]["clause_signals"]
    assert exported["timeline_facts"] == output["diagnosis"]["timeline_facts"]
    assert "SLA/Service Credit" not in markdown
    assert "Whether the alleged service-impact period downtime qualifies" not in markdown


def test_playground_refund_termination_filters_false_positive_issue_families() -> None:
    diagnosis = _run_playground_diagnosis(
        REFUND_TERMINATION_ACCEPTANCE_FIXTURE
    )["diagnosis"]
    active_tags = {tag.lower() for tag in diagnosis["active_issue_tags"]}

    for expected in (
        "refund",
        "prepaid fees",
        "termination",
        "notice",
        "cure period",
        "delivery",
        "acceptance / rejection",
        "damages",
        "liability limitation",
    ):
        assert expected in active_tags

    for forbidden in (
        "indemnity",
        "confidentiality",
        "force majeure",
        "intellectual property",
        "sla",
        "service credit",
        "suspension",
        "invoice dispute",
    ):
        assert forbidden not in active_tags

    assert "Payment/Invoice Dispute" not in diagnosis["dispute_type"]
    for expected_type in (
        "Notice/Cure Period",
        "Termination",
        "Refund",
        "Acceptance/Rejection",
        "Damages/Liability",
    ):
        assert expected_type in diagnosis["dispute_type"]


def test_playground_refund_termination_clause_signals_are_clause_only_scoped() -> None:
    diagnosis = _run_playground_diagnosis(
        REFUND_TERMINATION_ACCEPTANCE_FIXTURE
    )["diagnosis"]
    clause_text = "\n".join(diagnosis["clause_signals"])

    for expected_clause in (
        "prepaid implementation fee",
        "non-refundable fee provision",
        "pro-rata refund after uncured breach",
        "written breach notice",
        "15-day cure period",
        "milestone acceptance",
        "5-business-day rejection period",
        "reasonable specificity for defect rejection",
        "consequential damages exclusion",
        "lost-profit damages exclusion",
        "six-month fee liability cap",
        "indemnity clause mentioned but not fact-triggered",
        "force majeure clause mentioned but not fact-triggered",
    ):
        assert expected_clause in clause_text

    for forbidden_clause in (
        "confidentiality obligations",
        "SLA/service credit",
        "suspension rights",
    ):
        assert forbidden_clause not in clause_text


def test_playground_refund_termination_key_issues_and_timeline_are_case_specific() -> None:
    diagnosis = _run_playground_diagnosis(
        REFUND_TERMINATION_ACCEPTANCE_FIXTURE
    )["diagnosis"]
    key_issue_text = "\n".join(diagnosis["key_issues"])
    timeline_text = "\n".join(diagnosis["timeline_facts"])

    for required in (
        "March 15 data import milestone and March 25 administrator training milestone",
        "March 28 partial data import",
        "April 2 breach notice",
        "15-day cure period expired before the April 20 termination",
        "March 28 delivery package requested formal milestone acceptance",
        "rejected the March 28 delivery within the 5-business-day rejection period",
        "material defects with reasonable specificity",
        "prepaid $60,000 implementation fee",
        "$42,000 refund calculation",
        "lost productivity or internal delay costs",
        "six-month fee liability cap",
    ):
        assert required in key_issue_text

    for forbidden in (
        "unpaid invoice",
        "identified invoices were unpaid and overdue",
        "revised package revised package",
        "production-ready delivery milestone",
        "service credit",
        "suspension",
        "lost revenue",
    ):
        assert forbidden not in key_issue_text

    for expected_timeline in (
        "March 5: customer paid $60,000 prepaid implementation fee.",
        "March 15: data import milestone.",
        "March 25: administrator training milestone.",
        "March 28: provider partial delivery.",
        "April 2: customer breach notice.",
        "April 10: provider response.",
        "April 20: customer termination.",
        "15-day cure period: calculate from deemed receipt of April 2 notice.",
        "5-business-day rejection period: calculate from March 28 delivery only if acceptance was requested.",
    ):
        assert expected_timeline in timeline_text

    march_28_lines = [
        line for line in diagnosis["timeline_facts"] if "March 28" in line
    ]
    assert any("provider partial delivery" in line for line in march_28_lines)
    assert all(
        not (line.startswith("March 28:") and "rejection" in line.lower())
        for line in march_28_lines
    )


def test_playground_refund_termination_gaps_next_steps_and_exports_are_scoped() -> None:
    output = _run_playground_diagnosis(REFUND_TERMINATION_ACCEPTANCE_FIXTURE)
    exported = json.loads(output["json"])
    markdown = output["markdown"]
    gaps = "\n".join(exported["evidence_gaps"])
    next_steps = "\n".join(exported["suggested_next_steps"])

    for expected_gap in (
        "Statement of work notice contact list",
        "Proof that the April 2 breach notice was sent to the contractual notice contacts",
        "Whether the March 28 delivery package requested formal milestone acceptance",
        "Whether the customer rejected within 5 business days",
        "Whether rejection identified material defects with reasonable specificity",
        "Detailed work-completion records showing performed vs unperformed services",
        "Basis for the $42,000 pro-rata refund calculation",
        "Evidence supporting lost productivity damages",
    ):
        assert expected_gap in gaps

    for forbidden_gap in (
        "invoice receipt dates",
        "invoice dispute notice",
        "disputed vs undisputed invoice amounts",
    ):
        assert forbidden_gap not in gaps.lower()

    for expected_step in (
        "Build a March 5 / March 15 / March 25 / March 28 / April 2 / April 10 / April 20 timeline.",
        "Verify SOW notice contacts.",
        "Verify proof of April 2 breach notice delivery.",
        "Calculate deemed receipt and 15-day cure deadline.",
        "Determine whether the March 28 delivery requested formal acceptance.",
        "Determine whether the customer rejected within 5 business days.",
        "Review whether rejection identified material defects with reasonable specificity.",
        "Compare performed vs unperformed service records.",
        "Validate the $42,000 pro-rata refund calculation.",
        "Review consequential damages, lost-profit exclusion, and six-month fee liability cap.",
        "Verify evidence supporting lost productivity damages.",
    ):
        assert expected_step in next_steps

    for forbidden_step in (
        "invoice receipt",
        "invoice dispute",
        "disputed amounts",
        "suspension",
        "service credit",
    ):
        assert forbidden_step not in next_steps.lower()

    assert exported["active_issue_tags"] == output["diagnosis"]["active_issue_tags"]
    assert exported["clause_signals"] == output["diagnosis"]["clause_signals"]
    assert exported["timeline_facts"] == output["diagnosis"]["timeline_facts"]
    assert "Payment/Invoice Dispute" not in markdown
    assert "indemnity" not in "\n".join(exported["active_issue_tags"]).lower()
    assert "confidentiality" not in "\n".join(exported["active_issue_tags"]).lower()
    assert "service-credit" not in "\n".join(exported["risk"]["rationale"]).lower()


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
