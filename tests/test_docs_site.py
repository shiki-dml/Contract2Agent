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


SALES_FORCE_MAJEURE_CLAUSE_ONLY_FIXTURE = {
    "contractType": "Sales Contract",
    "disputeType": "Late Delivery",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Evidence-first",
    "desiredOutcome": (
        "Determine whether Seller can rely on force majeure language despite "
        "internal staffing shortages and ordinary raw-material/vendor backlog."
    ),
    "contractText": (
        "Seller must deliver conforming equipment by May 15. The agreement includes a "
        "force majeure clause covering natural disasters, government orders, port "
        "closures, strikes, war, emergency closures, and extraordinary external events "
        "outside the affected party's control. The affected party must provide prompt "
        "written force majeure notice and use commercially reasonable mitigation. "
        "Payment is due net 30 after accepted delivery."
    ),
    "disputeDescription": (
        "Seller shipped the equipment on May 25 after internal staffing shortages and "
        "an ordinary raw-material/vendor backlog. "
        "Buyer says the shipment was late and asks whether it may reject or recover "
        "ordinary delay damages. No party claims force majeure. No force majeure notice "
        "was sent. There was no government order, no natural disaster, no port closure, "
        "no strike, no war, no emergency closure, no widespread infrastructure outage, "
        "no external uncontrollable event, no qualifying external event, and no "
        "extraordinary external event."
    ),
    "claimantPosition": (
        "Buyer says the delay was a commercial supply problem and seeks late-shipment "
        "remedies. Buyer does not seek a force majeure ruling."
    ),
    "respondentPosition": (
        "Seller says the backlog was ordinary vendor delay and does not invoke force "
        "majeure or any external uncontrollable event."
    ),
    "evidence": (
        "Available:\n"
        "- Purchase order delivery schedule\n"
        "- Carrier record showing May 25 shipment\n"
        "- Vendor backlog email describing ordinary component shortages\n\n"
        "Missing or unclear:\n"
        "- Final delay damages calculation"
    ),
    "metadata": '{"product":"equipment"}',
}


CONFIDENTIALITY_CLAUSE_ONLY_FIXTURE = {
    "contractType": "Service Agreement",
    "disputeType": "Service Performance",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Balanced",
    "desiredOutcome": "Assess service completion and payment holdback.",
    "contractText": (
        "Each party must protect Confidential Information and may not make restricted "
        "disclosures except to employees who need access. The agreement also contains "
        "standard non-disclosure obligations."
    ),
    "disputeDescription": (
        "The customer withheld final payment because the provider missed two reporting "
        "deadlines. The parties agree there was no confidentiality breach, no confidential "
        "information disclosure, no unauthorized disclosure, and no public disclosure."
    ),
    "claimantPosition": "Provider seeks payment for completed reporting work.",
    "respondentPosition": "Customer disputes timeliness only and does not allege any disclosure.",
    "evidence": "Available:\n- Reporting schedule\n- Final report delivery email\n- Payment holdback ledger",
    "metadata": '{"issue":"reporting delay"}',
}


INDEMNITY_CLAUSE_ONLY_FIXTURE = {
    "contractType": "Master Services Agreement",
    "disputeType": "Service Performance",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Balanced",
    "desiredOutcome": "Assess service delay and fee credit.",
    "contractText": (
        "Provider will indemnify, defend, and hold harmless Customer from covered "
        "third-party claims. The indemnification section includes a defense obligation "
        "after timely tender."
    ),
    "disputeDescription": (
        "The dispute concerns a missed configuration deadline. There is no third-party "
        "claim, no indemnity claim, no indemnity tender, and no defense demand."
    ),
    "claimantPosition": "Customer seeks a service fee credit for the missed configuration deadline.",
    "respondentPosition": "Provider says the configuration delay was cured and no third party is involved.",
    "evidence": "Available:\n- Configuration timeline\n- Support messages\n- Cure confirmation email",
    "metadata": '{"issue":"configuration delay"}',
}


LIQUIDATED_DAMAGES_ACTIVE_FIXTURE = {
    "contractType": "Sales Contract",
    "disputeType": "Late Delivery",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Evidence-first",
    "desiredOutcome": "Determine liquidated damages enforceability and calculation.",
    "contractText": (
        "Seller must deliver by July 1. For late delivery, Buyer may recover liquidated "
        "damages of 1% of the order value per full week, capped at 8%."
    ),
    "disputeDescription": (
        "Seller delivered on July 22. Buyer seeks liquidated damages for the late "
        "delivery period. Seller disputes liquidated damages and argues the formula is "
        "an unenforceable penalty."
    ),
    "claimantPosition": "Buyer seeks liquidated damages for three full weeks of delay.",
    "respondentPosition": "Seller says the liquidated damages amount is a penalty and exceeds any real loss.",
    "evidence": "Available:\n- July 1 delivery deadline\n- July 22 delivery receipt\n- Liquidated damages calculation",
    "metadata": '{"delivery":"late"}',
}


LIQUIDATED_DAMAGES_CLAUSE_ONLY_FIXTURE = {
    "contractType": "Sales Contract",
    "disputeType": "Quality Dispute",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Balanced",
    "desiredOutcome": "Assess warranty repair obligations.",
    "contractText": (
        "The contract includes a liquidated damages clause for late delivery and a cap "
        "on stipulated delay damages."
    ),
    "disputeDescription": (
        "The goods arrived on time, but Buyer says several units failed inspection. No "
        "party seeks liquidated damages, no party disputes a penalty, and the dispute "
        "does not involve late performance."
    ),
    "claimantPosition": "Buyer seeks repair or replacement of defective units.",
    "respondentPosition": "Seller says the units met the warranty specification.",
    "evidence": "Available:\n- Delivery receipt\n- Inspection report\n- Warranty correspondence",
    "metadata": '{"issue":"quality"}',
}


LIABILITY_LIMITATION_ACTIVE_FIXTURE = {
    "contractType": "Sales Contract",
    "disputeType": "Damages/Liability",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Balanced",
    "desiredOutcome": "Determine damages and whether the liability cap limits recovery.",
    "contractText": (
        "Total liability is capped at amounts paid under the purchase order. Neither "
        "party may recover consequential damages or lost profits."
    ),
    "disputeDescription": (
        "Buyer seeks monetary damages for replacement parts and installation downtime. "
        "Seller argues the liability cap applies and that damages beyond the cap are excluded."
    ),
    "claimantPosition": "Buyer says direct damages exceed the contract cap.",
    "respondentPosition": "Seller says the cap limits recovery.",
    "evidence": "Available:\n- Replacement parts quote\n- Repair labor estimate\n- Damages spreadsheet",
    "metadata": '{"remedy":"damages"}',
}


ALTERNATIVE_SUPPLIER_INVOICE_FIXTURE = {
    "contractType": "Sales Contract",
    "disputeType": "Late Delivery",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Evidence-first",
    "desiredOutcome": "Assess late delivery, cover purchase, and damages.",
    "contractText": (
        "Seller must ship components by August 1. Buyer may recover reasonable direct "
        "cover costs for late delivery. Payment terms are net 30 after accepted delivery."
    ),
    "disputeDescription": (
        "Seller shipped components on August 12. Buyer bought substitute components "
        "from an alternate supplier to keep production running and seeks cover costs. "
        "There is no unpaid invoice, no disputed invoice, no billing dispute, no invoice "
        "nonpayment, no payment controversy, and no invoice dispute notice."
    ),
    "claimantPosition": "Buyer seeks the incremental substitute-purchase cost caused by late delivery.",
    "respondentPosition": "Seller disputes causation and reasonableness of the cover purchase.",
    "evidence": (
        "Available:\n"
        "- August 1 shipment deadline\n"
        "- August 12 carrier record\n"
        "- Alternative supplier invoice dated May 10 used as cover-cost evidence\n"
        "- Supplier invoice used to calculate cover costs, not an invoice payment demand\n"
        "- Production schedule impact memo"
    ),
    "metadata": '{"remedy":"cover costs"}',
}


REAL_UNPAID_INVOICE_DISPUTE_FIXTURE = {
    "contractType": "Service Agreement",
    "disputeType": "Payment Delay",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Evidence-first",
    "desiredOutcome": "Recover unpaid Invoice #1042 and resolve the disputed amount.",
    "contractText": (
        "Customer must pay undisputed invoices within 30 days after receipt. If Customer "
        "disputes an invoice, Customer must give written invoice dispute notice identifying "
        "the disputed amount and basis for dispute within 10 days after receiving the invoice."
    ),
    "disputeDescription": (
        "Customer received Invoice #1042 on January 5 and did not pay by the February 4 "
        "due date. Provider demanded payment on February 10. Customer disputed the invoice "
        "amount in writing on February 12, and the parties disagree over whether the invoice "
        "is owed and whether the disputed amount was preserved."
    ),
    "claimantPosition": (
        "Provider claims Invoice #1042 remains unpaid and says Customer failed to pay the "
        "undisputed amount by the due date."
    ),
    "respondentPosition": (
        "Customer says the invoice amount is contested because several charges were improper "
        "and payment was withheld because the invoice was disputed."
    ),
    "evidence": (
        "Available:\n"
        "- January 5 invoice receipt email\n"
        "- February 10 provider payment demand\n\n"
        "Missing or unclear:\n"
        "- Invoice #1042 copy\n"
        "- Payment records for Invoice #1042\n"
        "- Customer written invoice dispute notice\n"
        "- Calculation of disputed amount"
    ),
    "metadata": '{"invoice":"1042"}',
}


INVOICE_CLAUSE_ONLY_FIXTURE = {
    "contractType": "Sales Contract",
    "disputeType": "Late Delivery",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Balanced",
    "desiredOutcome": "Assess late delivery remedies.",
    "contractText": (
        "Buyer must pay invoices within 30 days after accepted delivery. Any invoice dispute "
        "notice must identify the disputed amount and basis for dispute within 10 days after "
        "invoice receipt. Late payment charges may accrue on undisputed overdue amounts."
    ),
    "disputeDescription": (
        "Seller delivered the goods late, and Buyer seeks delivery remedies. The facts "
        "explicitly say no invoice dispute, no unpaid invoices, no late payment, no billing "
        "dispute, and no payment controversy."
    ),
    "claimantPosition": "Buyer seeks damages for the late shipment only.",
    "respondentPosition": "Seller says delivery was substantially timely and no payment issue is involved.",
    "evidence": "Available:\n- Delivery receipt\n- Shipment log\n- Buyer delay notice",
    "metadata": '{"issue":"late delivery"}',
}


COST_EVIDENCE_INVOICES_FIXTURE = {
    "contractType": "Service Agreement",
    "disputeType": "Damages/Liability",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Evidence-first",
    "desiredOutcome": "Assess recoverability of repair, remediation, and legal-fee costs.",
    "contractText": (
        "The provider must remediate service failures and is liable for reasonable direct "
        "repair, remediation, investigation, and legal costs caused by breach, subject to "
        "the liability cap and damages exclusions."
    ),
    "disputeDescription": (
        "Customer claims a service failure caused direct costs. Customer submits a repair "
        "invoice dated May 10, a remediation vendor invoice dated May 12, and an outside "
        "counsel invoice dated May 15 as evidence of damages and costs. No party disputes "
        "payment of those invoices as between the contracting parties, and there is no "
        "invoice dispute, no unpaid invoice, no billing dispute, and no invoice nonpayment."
    ),
    "claimantPosition": (
        "Customer seeks reimbursement of repair costs, remediation costs, investigation "
        "costs, and legal fees."
    ),
    "respondentPosition": (
        "Provider disputes causation and whether the invoices prove reasonable damages, "
        "but does not claim an invoice-payment controversy."
    ),
    "evidence": (
        "Available:\n"
        "- Repair invoice dated May 10\n"
        "- Remediation vendor invoice dated May 12\n"
        "- Outside counsel invoice dated May 15\n"
        "- Cost summary spreadsheet\n\n"
        "Missing or unclear:\n"
        "- Final damages calculation"
    ),
    "metadata": '{"remedy":"cost reimbursement"}',
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


CONFIDENTIALITY_IP_INDEMNITY_FIXTURE = {
    "contractType": "Service Agreement",
    "disputeType": "Damages/Liability",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Evidence-first",
    "desiredOutcome": "Assess confidentiality breach, IP indemnity coverage, notice timing, and damages limits.",
    "contractText": (
        "This Service Agreement requires the provider to perform implementation and "
        "analytics support services for the customer.\n\n"
        "The provider must protect all customer confidential information using at "
        "least reasonable care and may disclose it only to personnel or subcontractors "
        "who need access to perform the services and are bound by confidentiality "
        "obligations at least as protective as this Agreement.\n\n"
        "Customer confidential information includes non-public business plans, pricing "
        "models, product launch schedules, customer lists, technical documentation, "
        "and any materials marked or reasonably understood to be confidential.\n\n"
        "The provider must notify the customer within 3 business days after "
        "discovering any unauthorized disclosure or suspected compromise of customer "
        "confidential information and must reasonably cooperate in containment and "
        "remediation.\n\n"
        "The provider will indemnify, defend, and hold harmless the customer from "
        "third-party claims alleging that provider-owned tools, templates, software, "
        "or deliverables infringe intellectual property rights, except to the extent "
        "the claim arises from customer-provided materials or customer modifications.\n\n"
        "The customer must give written notice of any indemnifiable claim within 10 "
        "days after receiving the claim. The provider may control the defense, but "
        "may not settle in a way that admits customer fault or imposes non-monetary "
        "obligations without the customer's written consent.\n\n"
        "Neither party is liable for indirect, incidental, consequential, special, "
        "punitive, or lost-profit damages. Total liability is capped at fees paid "
        "under the affected statement of work during the twelve months before the "
        "event giving rise to the claim.\n\n"
        "The liability cap does not limit claims for breach of confidentiality, "
        "willful misconduct, or indemnity obligations.\n\n"
        "Neither party is responsible for delay caused by force majeure events beyond "
        "its reasonable control, provided the affected party gives prompt written "
        "notice and uses commercially reasonable mitigation efforts.\n\n"
        "All notices must be sent by email to the notice contacts listed in the "
        "statement of work and are deemed received on the next business day after "
        "transmission."
    ),
    "disputeDescription": (
        "The provider uploaded a customer product launch plan and pricing model to a "
        "public project-management workspace on May 3. The customer discovered the "
        "public link on May 6 and demanded that the provider remove the file and "
        "identify everyone who accessed it.\n\n"
        "The provider removed the file on May 8 but says the upload was accidental "
        "and that only two subcontractor users accessed the workspace. The customer "
        "argues that the workspace was publicly accessible without authentication "
        "and that the provider failed to notify the customer within 3 business days "
        "after discovering the exposure.\n\n"
        "On May 10, a third-party software company sent the customer a demand letter "
        "alleging that a provider-created analytics template delivered under the "
        "project infringed the third party's copyright. The customer sent an "
        "indemnity notice to the provider on May 12.\n\n"
        "The provider disputes indemnity coverage, arguing that the allegedly "
        "infringing analytics template was modified using customer-provided "
        "materials. The customer argues that the template was provider-owned and "
        "that the indemnity clause applies.\n\n"
        "No party claims delayed delivery, unpaid invoices, refunds, SLA downtime, "
        "service credits, suspension, government order, natural disaster, strike, "
        "war, or other external uncontrollable event."
    ),
    "claimantPosition": (
        "Customer claims the provider breached confidentiality obligations by "
        "exposing the product launch plan and pricing model in a public workspace, "
        "failed to give timely unauthorized-disclosure notice, and must indemnify "
        "the customer against the May 10 third-party IP demand. Customer seeks "
        "remediation costs, investigation costs, defense costs, and damages not "
        "limited by the liability cap."
    ),
    "respondentPosition": (
        "Provider claims the disclosure was accidental, quickly remediated, and "
        "caused no proven loss. Provider denies indemnity because the third-party IP "
        "demand allegedly arises from customer-provided materials or customer "
        "modifications. Provider also argues that any recoverable damages are "
        "limited by the damages exclusion and twelve-month fee cap unless a carve-out "
        "applies."
    ),
    "evidence": (
        "Available:\n"
        "- Statement of work listing the project notice contacts\n"
        "- Provider workspace upload log showing upload on May 3\n"
        "- Screenshot of public workspace link captured by customer on May 6\n"
        "- Provider removal confirmation dated May 8\n"
        "- Workspace access log showing two named subcontractor users and several anonymous page views\n"
        "- Customer product launch plan marked \"Confidential\"\n"
        "- Customer pricing model marked \"Confidential\"\n"
        "- Third-party IP demand letter dated May 10\n"
        "- Customer indemnity notice to provider dated May 12\n"
        "- Provider analytics template delivered under the project\n"
        "- Email thread discussing whether customer materials were used in the analytics template\n"
        "- Customer invoice for forensic review and remediation support\n\n"
        "Missing or unclear:\n"
        "- Exact date when the provider first discovered the public workspace exposure\n"
        "- Whether anonymous page views reflect actual third-party access or internal testing\n"
        "- Whether subcontractors were bound by confidentiality obligations at least as protective as the Agreement\n"
        "- Proof that the customer's May 12 indemnity notice was sent to the contractual notice contacts\n"
        "- Technical comparison between the provider analytics template and the third-party copyrighted work\n"
        "- Evidence showing whether the analytics template was provider-owned or derived from customer-provided materials\n"
        "- Defense cost estimate for the third-party IP claim\n"
        "- Calculation of remediation, investigation, and claimed business-impact damages"
    ),
    "metadata": '{"project":"analytics implementation"}',
}


LEASE_REPAIR_ABATEMENT_DEPOSIT_FIXTURE = {
    "contractType": "Lease",
    "disputeType": "Notice/Cure Period",
    "outputFormat": "Detailed",
    "diagnosisDepth": "Detailed",
    "riskMode": "Evidence-first",
    "desiredOutcome": (
        "Determine whether the tenant properly triggered the landlord's repair "
        "obligations, whether the landlord failed to cure within the contractual "
        "period, whether rent abatement or early termination is available, and "
        "whether the landlord can deduct repair costs from the security deposit."
    ),
    "contractText": (
        "This Commercial Lease requires the landlord to maintain the building roof, "
        "exterior walls, HVAC main units, and common plumbing systems in good "
        "working order.\n\n"
        "The tenant must maintain the leased premises in clean condition and is "
        "responsible for damage caused by the tenant's employees, contractors, "
        "invitees, or misuse of the premises.\n\n"
        "If the tenant claims that the landlord failed to perform a maintenance "
        "obligation, the tenant must give written notice describing the condition, "
        "affected area, and requested repair. The landlord has 10 business days "
        "after receipt of the notice to begin commercially reasonable repairs, "
        "except in emergencies requiring faster action.\n\n"
        "If the landlord fails to begin commercially reasonable repairs within the "
        "cure period and the condition materially interferes with the tenant's use "
        "of the premises, the tenant may claim reasonable rent abatement for the "
        "affected period and affected area.\n\n"
        "The tenant may not withhold rent unless the lease expressly allows rent "
        "abatement or a court order permits withholding. Unauthorized withholding "
        "is a payment default.\n\n"
        "At lease expiration, the landlord may deduct from the security deposit "
        "only unpaid rent, documented repair costs for tenant-caused damage beyond "
        "ordinary wear and tear, and other amounts expressly allowed under this "
        "Lease. The landlord must provide an itemized deposit statement within 30 "
        "days after surrender.\n\n"
        "Neither party is liable for indirect, incidental, consequential, special, "
        "punitive, or lost-profit damages. Total liability is capped at twelve "
        "months of base rent, except for unpaid rent, intentional misconduct, or "
        "tenant-caused property damage.\n\n"
        "Neither party is responsible for delay caused by force majeure events "
        "beyond its reasonable control, provided the affected party gives prompt "
        "written notice and uses commercially reasonable mitigation efforts.\n\n"
        "All notices must be sent by email and certified mail to the notice "
        "addresses listed in the lease schedule. Notices are deemed received two "
        "business days after mailing or the next business day after email "
        "transmission, whichever occurs later."
    ),
    "disputeDescription": (
        "The tenant operates a small retail showroom. On September 3, the tenant "
        "discovered water intrusion near the ceiling after heavy rain. The tenant "
        "sent an email to the landlord on September 4 stating that water was "
        "entering the showroom and damaging display fixtures.\n\n"
        "The landlord responded on September 7 and said it would inspect the issue. "
        "A roof contractor inspected the building on September 15 and found "
        "deteriorated roof flashing. The tenant says the landlord did not begin "
        "repairs within the 10-business-day cure period after notice.\n\n"
        "The tenant withheld 40% of October rent and demanded rent abatement for "
        "September 4 through October 12, arguing that part of the showroom was "
        "unusable. The landlord argues that the tenant's September 4 email was not "
        "a proper lease notice because it was not also sent by certified mail to "
        "the lease schedule notice address.\n\n"
        "The landlord completed roof repairs on October 12. At move-out on "
        "November 1, the landlord deducted $8,500 from the security deposit for "
        "damaged display flooring and repainting. The tenant disputes the "
        "deductions and says the damage was caused by the roof leak, not tenant "
        "misuse.\n\n"
        "No party claims unpaid invoices, SaaS downtime, service credits, platform "
        "suspension, third-party IP claims, indemnity, confidential information "
        "disclosure, government orders, natural disasters, strikes, war, or other "
        "force majeure events."
    ),
    "claimantPosition": (
        "Tenant claims the landlord failed to begin commercially reasonable roof "
        "repairs within the 10-business-day cure period after the September 4 "
        "notice. Tenant seeks rent abatement for the affected showroom area, "
        "return of the $8,500 security deposit deduction, and reimbursement for "
        "damaged display fixtures."
    ),
    "respondentPosition": (
        "Landlord claims the tenant did not send a valid contractual notice because "
        "the September 4 email was not also sent by certified mail to the lease "
        "schedule notice address. Landlord argues that the October rent withholding "
        "was unauthorized and that the $8,500 security deposit deduction was "
        "supported by documented tenant-caused damage beyond ordinary wear and tear."
    ),
    "evidence": (
        "Available:\n"
        "- Lease schedule identifying landlord and tenant notice addresses\n"
        "- Tenant email dated September 4 reporting water intrusion\n"
        "- Landlord response email dated September 7\n"
        "- Roof contractor inspection report dated September 15\n"
        "- Contractor invoice showing roof repairs completed October 12\n"
        "- Tenant photos of water intrusion and damaged display fixtures\n"
        "- October rent ledger showing 40% rent withholding\n"
        "- Move-out inspection report dated November 1\n"
        "- Security deposit statement deducting $8,500\n"
        "- Flooring repair invoice and repainting invoice from landlord\n"
        "- Tenant photos showing water damage near the affected showroom area\n\n"
        "Missing or unclear:\n"
        "- Proof that the September 4 notice was sent by certified mail\n"
        "- Whether the September 4 email was sent to the exact lease schedule notice email address\n"
        "- Whether the roof leak materially interfered with the tenant's use of the premises\n"
        "- Square footage or area affected by the leak\n"
        "- Whether the landlord began commercially reasonable repairs within 10 business days after valid receipt\n"
        "- Whether the flooring and repainting damage was caused by roof leak or tenant misuse\n"
        "- Whether the $8,500 deduction was limited to damage beyond ordinary wear and tear\n"
        "- Calculation of rent abatement for the affected area and affected period\n"
        "- Evidence supporting display-fixture damages"
    ),
    "metadata": '{"property":"retail showroom"}',
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


def test_playground_final_diagnosis_is_source_for_json_and_markdown_exports() -> None:
    output = _run_playground_diagnosis(CONFIDENTIALITY_IP_INDEMNITY_FIXTURE)
    diagnosis = output["diagnosis"]
    exported = json.loads(output["json"])
    markdown = output["markdown"]

    assert _markdown_list_items(markdown, "Active Issue Tags") == diagnosis["active_issue_tags"]
    assert _markdown_list_items(markdown, "Key Issues") == diagnosis["key_issues"]
    assert _markdown_list_items(markdown, "Timeline Facts") == diagnosis["timeline_facts"]
    assert _markdown_list_items(markdown, "Evidence Gaps") == diagnosis["evidence_gaps"]
    assert _markdown_list_items(markdown, "Suggested Next Steps") == diagnosis["suggested_next_steps"]

    for field in (
        "contract_type",
        "dispute_type",
        "active_issue_tags",
        "key_issues",
        "clause_signals",
        "timeline_facts",
        "evidence_gaps",
        "risk",
        "risk_signal",
        "suggested_next_steps",
    ):
        assert exported[field] == diagnosis[field]
    assert exported["issue_tags"] == diagnosis["active_issue_tags"]
    assert exported["structured_diagnosis_preview"]["detected"]["active_issue_tags"] == diagnosis["active_issue_tags"]
    assert exported["structured_diagnosis_preview"]["timeline_facts"] == diagnosis["timeline_facts"]
    assert exported["structured_diagnosis_preview"]["evidence_gaps"] == diagnosis["evidence_gaps"]


def test_playground_evaluation_preview_uses_final_diagnosis() -> None:
    output = _run_playground_diagnosis(REFUND_TERMINATION_ACCEPTANCE_FIXTURE)
    diagnosis = output["diagnosis"]
    test_case = output["test_case"]

    assert test_case["expected_outputs"]["must_include_issues"] == [
        tag for tag in diagnosis["active_issue_tags"] if tag != "unclear"
    ]
    assert test_case["expected_outputs"]["must_include_evidence_gaps"] == diagnosis["evidence_gaps"]
    assert test_case["expected_outputs"]["risk_signal"] == diagnosis["risk_signal"]
    assert set(test_case["expected_outputs"]["must_include_issues"]) <= set(diagnosis["active_issue_tags"])
    assert "saas" not in test_case["case_name"]
    assert "force_majeure" not in test_case["case_name"]


def test_playground_no_post_final_regeneration_of_active_issues() -> None:
    output = _run_playground_diagnosis(LEASE_REPAIR_ABATEMENT_DEPOSIT_FIXTURE)
    diagnosis = output["diagnosis"]
    exported = json.loads(output["json"])
    markdown = output["markdown"]
    test_case = output["test_case"]
    active_tags = diagnosis["active_issue_tags"]

    assert _markdown_list_items(markdown, "Active Issue Tags") == active_tags
    assert exported["active_issue_tags"] == active_tags
    assert test_case["expected_outputs"]["must_include_issues"] == [
        tag for tag in active_tags if tag != "unclear"
    ]

    active_issue_reason = next(
        reason for reason in diagnosis["risk"]["rationale"]
        if reason.startswith("Active issues detected:")
    )
    listed_in_risk = [
        item.strip().removesuffix(".")
        for item in active_issue_reason.removeprefix("Active issues detected:").split(",")
    ]
    assert listed_in_risk == active_tags

    inactive_issue_terms = {
        "force majeure",
        "SLA",
        "service credit",
        "suspension",
        "invoice dispute",
        "refund",
        "confidentiality",
        "indemnity",
        "third-party IP claim",
        "liquidated damages",
        "cover costs",
    }
    inactive_issue_terms -= set(active_tags)
    surface_text = "\n".join(
        [
            "\n".join(_markdown_list_items(markdown, "Active Issue Tags")),
            "\n".join(exported["active_issue_tags"]),
            "\n".join(test_case["expected_outputs"]["must_include_issues"]),
            active_issue_reason,
        ]
    ).lower()
    for inactive in inactive_issue_terms:
        assert inactive.lower() not in surface_text


def test_playground_final_diagnosis_runs_have_fresh_state() -> None:
    force_then_refund = _run_playground_diagnoses_sequentially(
        [POSITIVE_FORCE_MAJEURE_DELIVERY_FIXTURE, REFUND_TERMINATION_ACCEPTANCE_FIXTURE]
    )
    first, second = force_then_refund

    assert first["active_issue_tags"] != second["active_issue_tags"]
    assert second["issue_tags"] == second["active_issue_tags"]
    second_output_text = json.dumps(
        {
            "active_issue_tags": second["active_issue_tags"],
            "key_issues": second["key_issues"],
            "evidence_gaps": second["evidence_gaps"],
            "timeline_facts": second["timeline_facts"],
            "suggested_next_steps": second["suggested_next_steps"],
            "risk": second["risk"],
        }
    ).lower()
    for leaked in (
        "government emergency order",
        "force majeure notice",
        "temporary consultant",
        "remote migration tools",
        "alternate staffing",
        "cover cost",
        "liquidated damages",
    ):
        assert leaked not in second_output_text


def test_playground_force_majeure_clause_only_stays_clause_signal() -> None:
    output = _run_playground_diagnosis(SALES_FORCE_MAJEURE_CLAUSE_ONLY_FIXTURE)
    diagnosis = output["diagnosis"]
    exported = json.loads(output["json"])
    markdown = output["markdown"]
    test_case = output["test_case"]

    assert any("force majeure" in signal.lower() for signal in diagnosis["clause_signals"])
    assert "force majeure" not in diagnosis["active_issue_tags"]
    assert "force majeure" not in diagnosis["issue_tags"]
    assert "Force Majeure" not in diagnosis["dispute_type"]
    assert "force majeure" not in exported["active_issue_tags"]
    assert "force majeure" not in exported["issue_tags"]
    assert exported["issue_tags"] == diagnosis["active_issue_tags"]
    assert "force majeure" not in _markdown_list_items(markdown, "Active Issue Tags")
    assert exported["structured_diagnosis_preview"]["detected"]["active_issue_tags"] == diagnosis["active_issue_tags"]
    assert test_case["expected_outputs"]["must_include_issues"] == [
        tag for tag in diagnosis["active_issue_tags"] if tag != "unclear"
    ]
    assert "force majeure" not in test_case["expected_outputs"]["must_include_issues"]
    assert "force_majeure" not in test_case["case_name"]
    assert "force majeure" not in "\n".join(diagnosis["risk"]["rationale"]).lower()
    assert "force majeure" not in "\n".join(diagnosis["suggested_next_steps"]).lower()

    clause_only_text = "\n".join(
        diagnosis["key_issues"] +
        diagnosis["evidence_gaps"] +
        diagnosis["suggested_next_steps"] +
        diagnosis["risk"]["rationale"]
    ).lower()
    for forbidden in (
        "qualifies as force majeure",
        "invoked external event",
        "external event qualification",
        "government order",
        "natural disaster",
        "port closure",
        "strike",
        "war",
        "force majeure notice was timely",
        "force majeure notice delivery",
        "force majeure notice proof",
        "external event proof",
        "commercially reasonable mitigation",
        "infrastructure outage",
        "emergency closure",
    ):
        assert forbidden not in clause_only_text


def test_playground_positive_force_majeure_still_activates() -> None:
    output = _run_playground_diagnosis(POSITIVE_FORCE_MAJEURE_DELIVERY_FIXTURE)
    diagnosis = output["diagnosis"]
    test_case = output["test_case"]

    assert any("force majeure" in signal.lower() for signal in diagnosis["clause_signals"])
    assert "force majeure" in diagnosis["active_issue_tags"]
    assert "Force Majeure" in diagnosis["dispute_type"]
    assert any("qualifies as a force majeure event" in issue for issue in diagnosis["key_issues"])
    assert any("force majeure notice" in step.lower() for step in diagnosis["suggested_next_steps"])
    assert any("mitigation" in step.lower() for step in diagnosis["suggested_next_steps"])
    assert "force majeure" in test_case["expected_outputs"]["must_include_issues"]
    assert "force_majeure" in test_case["case_name"]


def test_playground_force_majeure_blockers_win_over_desired_outcome_wording() -> None:
    fixture = dict(SALES_FORCE_MAJEURE_CLAUSE_ONLY_FIXTURE)
    fixture["desiredOutcome"] = "Decide whether Seller can rely on force majeure language."
    fixture["disputeDescription"] = (
        "Seller delivered late. No force majeure notice was sent, and there was "
        "no qualifying external event, no government order, no natural disaster, "
        "no port closure, no strike, no war, no emergency closure, no widespread "
        "infrastructure outage, and no extraordinary external event."
    )
    fixture["respondentPosition"] = (
        "Seller points to ordinary vendor backlog and internal resource constraints, "
        "but does not invoke force majeure."
    )

    output = _run_playground_diagnosis(fixture)
    diagnosis = output["diagnosis"]
    surface_text = json.dumps(
        {
            "active_issue_tags": diagnosis["active_issue_tags"],
            "dispute_type": diagnosis["dispute_type"],
            "suggested_next_steps": diagnosis["suggested_next_steps"],
            "risk": diagnosis["risk"],
            "must_include_issues": output["test_case"]["expected_outputs"]["must_include_issues"],
            "case_name": output["test_case"]["case_name"],
        }
    ).lower()

    assert any("force majeure" in signal.lower() for signal in diagnosis["clause_signals"])
    assert "force majeure clause mentioned but not fact-triggered" in diagnosis["clause_signals"]
    assert "force majeure" not in surface_text
    assert "force_majeure" not in output["test_case"]["case_name"]


def test_playground_internal_staffing_and_vendor_backlog_are_not_force_majeure() -> None:
    fixture = dict(SALES_FORCE_MAJEURE_CLAUSE_ONLY_FIXTURE)
    fixture["desiredOutcome"] = "Assess late delivery remedies."
    fixture["disputeDescription"] = (
        "Seller delivered late because of internal staffing shortage, internal "
        "resource constraints, and ordinary supplier backlog. The delay was an "
        "internal delay only and a normal supply delay."
    )
    fixture["respondentPosition"] = (
        "Seller argues ordinary business difficulty and provider staffing issues "
        "made performance harder, but no external event prevented shipment."
    )

    diagnosis = _run_playground_diagnosis(fixture)["diagnosis"]
    next_steps = "\n".join(diagnosis["suggested_next_steps"]).lower()
    risk = "\n".join(diagnosis["risk"]["rationale"]).lower()

    assert any("force majeure" in signal.lower() for signal in diagnosis["clause_signals"])
    assert "force majeure" not in diagnosis["active_issue_tags"]
    assert "force majeure notice" not in next_steps
    assert "mitigation" not in next_steps
    assert "force majeure" not in risk


def test_playground_confidentiality_and_indemnity_clause_only_stay_clause_signals() -> None:
    confidentiality_output = _run_playground_diagnosis(CONFIDENTIALITY_CLAUSE_ONLY_FIXTURE)
    confidentiality = confidentiality_output["diagnosis"]
    confidentiality_case = confidentiality_output["test_case"]
    confidentiality_text = "\n".join(
        confidentiality["key_issues"] +
        confidentiality["evidence_gaps"] +
        confidentiality["suggested_next_steps"]
    ).lower()

    assert any("confidentiality" in signal.lower() for signal in confidentiality["clause_signals"])
    assert "confidentiality" not in confidentiality["active_issue_tags"]
    assert "unauthorized disclosure" not in confidentiality["active_issue_tags"]
    assert "confidentiality" not in confidentiality_case["expected_outputs"]["must_include_issues"]
    assert "unauthorized disclosure" not in confidentiality_text
    assert "public exposure" not in confidentiality_text

    indemnity_output = _run_playground_diagnosis(INDEMNITY_CLAUSE_ONLY_FIXTURE)
    indemnity = indemnity_output["diagnosis"]
    indemnity_case = indemnity_output["test_case"]
    indemnity_text = "\n".join(
        indemnity["key_issues"] +
        indemnity["evidence_gaps"] +
        indemnity["suggested_next_steps"]
    ).lower()

    assert any("indemnity" in signal.lower() for signal in indemnity["clause_signals"])
    assert "indemnity" not in indemnity["active_issue_tags"]
    assert "third-party IP claim" not in indemnity["active_issue_tags"]
    assert "indemnity" not in indemnity_case["expected_outputs"]["must_include_issues"]
    assert "third-party ip" not in indemnity_text
    assert "defense cost" not in indemnity_text


def test_playground_liquidated_damages_requires_active_remedy_or_dispute() -> None:
    active_output = _run_playground_diagnosis(LIQUIDATED_DAMAGES_ACTIVE_FIXTURE)
    active = active_output["diagnosis"]
    assert any("liquidated damages" in signal.lower() for signal in active["clause_signals"])
    assert "liquidated damages" in active["active_issue_tags"]
    assert any("liquidated damages" in issue.lower() for issue in active["key_issues"])
    assert any("penalty" in issue.lower() or "calculation" in issue.lower() for issue in active["key_issues"])

    clause_only_output = _run_playground_diagnosis(LIQUIDATED_DAMAGES_CLAUSE_ONLY_FIXTURE)
    clause_only = clause_only_output["diagnosis"]
    assert any("liquidated damages" in signal.lower() for signal in clause_only["clause_signals"])
    assert "liquidated damages" not in clause_only["active_issue_tags"]
    assert "liquidated damages" not in clause_only_output["test_case"]["expected_outputs"]["must_include_issues"]


def test_playground_liability_limitation_active_when_damages_are_disputed() -> None:
    output = _run_playground_diagnosis(LIABILITY_LIMITATION_ACTIVE_FIXTURE)
    diagnosis = output["diagnosis"]

    assert any("liability cap" in signal.lower() for signal in diagnosis["clause_signals"])
    assert "damages" in diagnosis["active_issue_tags"]
    assert "liability limitation" in diagnosis["active_issue_tags"]
    assert any("liability cap" in issue.lower() or "cap limits recovery" in issue.lower() for issue in diagnosis["key_issues"])


def _assert_no_active_invoice_dispute(output: dict) -> None:
    diagnosis = output["diagnosis"]
    exported = json.loads(output["json"])
    markdown = output["markdown"]
    test_case = output["test_case"]
    active_section = markdown.split("## Active Issue Tags", 1)[1].split(
        "## Key Issues", 1
    )[0]
    active_text = "\n".join(
        diagnosis["active_issue_tags"]
        + diagnosis.get("issue_tags", [])
        + exported["active_issue_tags"]
        + exported.get("issue_tags", [])
        + _markdown_list_items(markdown, "Active Issue Tags")
        + test_case["expected_outputs"]["must_include_issues"]
    ).lower()
    generated_text = json.dumps(
        {
            "key_issues": diagnosis["key_issues"],
            "evidence_gaps": diagnosis["evidence_gaps"],
            "suggested_next_steps": diagnosis["suggested_next_steps"],
            "timeline_facts": diagnosis["timeline_facts"],
            "risk": diagnosis["risk"],
        }
    ).lower()

    expected_issues = [tag for tag in diagnosis["active_issue_tags"] if tag != "unclear"]
    assert diagnosis["issue_tags"] == diagnosis["active_issue_tags"]
    assert exported["active_issue_tags"] == diagnosis["active_issue_tags"]
    assert exported["issue_tags"] == diagnosis["active_issue_tags"]
    assert exported["structured_diagnosis_preview"]["detected"]["active_issue_tags"] == diagnosis["active_issue_tags"]
    assert test_case["expected_outputs"]["must_include_issues"] == expected_issues
    assert "invoice dispute" not in active_text
    assert "invoice dispute" not in diagnosis["dispute_type"].lower()
    assert "invoice_dispute" not in test_case["case_name"]
    assert "invoice dispute" not in active_section.lower()
    for forbidden in (
        "invoice dispute notice",
        "customer written invoice dispute",
        "unpaid invoices",
        "billing dispute",
        "payment demand",
    ):
        assert forbidden not in generated_text


def test_playground_alternative_supplier_invoice_is_not_invoice_dispute() -> None:
    output = _run_playground_diagnosis(ALTERNATIVE_SUPPLIER_INVOICE_FIXTURE)
    diagnosis = output["diagnosis"]

    _assert_no_active_invoice_dispute(output)
    combined_timeline = "\n".join(diagnosis["timeline_facts"]).lower()
    assert "invoice dispute deadline" not in combined_timeline
    assert "unpaid invoice date" not in combined_timeline
    assert "billing dispute date" not in combined_timeline
    assert "may 10" in combined_timeline
    assert "cover-cost evidence invoice" in combined_timeline


def test_playground_real_unpaid_invoice_dispute_still_activates() -> None:
    output = _run_playground_diagnosis(REAL_UNPAID_INVOICE_DISPUTE_FIXTURE)
    diagnosis = output["diagnosis"]
    test_case = output["test_case"]
    key_issue_text = "\n".join(diagnosis["key_issues"]).lower()
    evidence_gap_text = "\n".join(diagnosis["evidence_gaps"]).lower()
    next_step_text = "\n".join(diagnosis["suggested_next_steps"]).lower()

    assert "payment" in diagnosis["active_issue_tags"]
    assert "invoice dispute" in diagnosis["active_issue_tags"]
    assert "Payment/Invoice Dispute" in diagnosis["dispute_type"]
    assert "invoice dispute" in test_case["expected_outputs"]["must_include_issues"]
    assert "invoice_dispute" in test_case["case_name"]
    assert "disputed amount" in key_issue_text
    assert "invoice #1042" in evidence_gap_text
    assert "payment records" in evidence_gap_text
    assert "customer written invoice dispute notice" in evidence_gap_text
    assert "invoice receipt" in next_step_text
    assert "invoice dispute notices" in next_step_text
    assert "disputed amounts" in next_step_text


def test_playground_invoice_clause_only_does_not_activate() -> None:
    output = _run_playground_diagnosis(INVOICE_CLAUSE_ONLY_FIXTURE)
    diagnosis = output["diagnosis"]

    assert any("payment" in signal.lower() for signal in diagnosis["clause_signals"])
    assert any("invoice" in signal.lower() for signal in diagnosis["clause_signals"])
    _assert_no_active_invoice_dispute(output)


def test_playground_cost_evidence_invoices_are_not_invoice_disputes() -> None:
    output = _run_playground_diagnosis(COST_EVIDENCE_INVOICES_FIXTURE)
    diagnosis = output["diagnosis"]
    timeline_text = "\n".join(diagnosis["timeline_facts"]).lower()

    _assert_no_active_invoice_dispute(output)
    assert "may 10: repair-cost evidence invoice" in timeline_text
    assert "may 12: remediation-cost evidence invoice" in timeline_text
    assert "may 15: legal-fee evidence invoice" in timeline_text
    assert "invoice dispute date" not in timeline_text
    assert "billing dispute date" not in timeline_text


def test_playground_invoice_dispute_state_does_not_leak_to_cover_invoice_case() -> None:
    positive, cover_invoice = _run_playground_diagnoses_sequentially(
        [REAL_UNPAID_INVOICE_DISPUTE_FIXTURE, ALTERNATIVE_SUPPLIER_INVOICE_FIXTURE]
    )

    assert "invoice dispute" in positive["active_issue_tags"]
    assert "invoice dispute" not in cover_invoice["active_issue_tags"]
    assert cover_invoice["issue_tags"] == cover_invoice["active_issue_tags"]
    cover_invoice_text = json.dumps(
        {
            "key_issues": cover_invoice["key_issues"],
            "evidence_gaps": cover_invoice["evidence_gaps"],
            "suggested_next_steps": cover_invoice["suggested_next_steps"],
            "risk": cover_invoice["risk"],
        }
    ).lower()
    for leaked in (
        "invoice dispute notice",
        "customer written invoice dispute",
        "unpaid invoices",
        "billing dispute",
        "payment demand",
    ):
        assert leaked not in cover_invoice_text


def test_playground_invoice_dispute_export_consistency_for_cover_invoice() -> None:
    output = _run_playground_diagnosis(ALTERNATIVE_SUPPLIER_INVOICE_FIXTURE)
    diagnosis = output["diagnosis"]
    exported = json.loads(output["json"])
    markdown = output["markdown"]
    test_case = output["test_case"]

    assert diagnosis["active_issue_tags"] == exported["active_issue_tags"]
    assert exported["issue_tags"] == diagnosis["active_issue_tags"]
    assert exported["structured_diagnosis_preview"]["detected"]["active_issue_tags"] == diagnosis["active_issue_tags"]
    assert "invoice dispute" not in "\n".join(diagnosis["active_issue_tags"]).lower()
    assert "invoice dispute" not in "\n".join(exported["active_issue_tags"]).lower()
    assert "invoice dispute" not in "\n".join(exported["issue_tags"]).lower()
    assert "invoice dispute" not in "\n".join(_markdown_list_items(markdown, "Active Issue Tags")).lower()
    assert "invoice dispute" not in test_case["expected_outputs"]["must_include_issues"]
    assert "invoice_dispute" not in test_case["case_name"]


def test_playground_clause_active_separation_survives_sequential_runs() -> None:
    positive, clause_only = _run_playground_diagnoses_sequentially(
        [POSITIVE_FORCE_MAJEURE_DELIVERY_FIXTURE, SALES_FORCE_MAJEURE_CLAUSE_ONLY_FIXTURE]
    )

    assert "force majeure" in positive["active_issue_tags"]
    assert "force majeure" not in clause_only["active_issue_tags"]
    assert clause_only["issue_tags"] == clause_only["active_issue_tags"]
    clause_only_text = json.dumps(
        {
            "key_issues": clause_only["key_issues"],
            "suggested_next_steps": clause_only["suggested_next_steps"],
            "risk": clause_only["risk"],
        }
    ).lower()
    for leaked in (
        "force majeure notice was timely",
        "remote migration tools",
        "alternate staffing",
        "government emergency order qualifies",
    ):
        assert leaked not in clause_only_text


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


def test_playground_confidentiality_ip_indemnity_filters_false_issue_families() -> None:
    diagnosis = _run_playground_diagnosis(
        CONFIDENTIALITY_IP_INDEMNITY_FIXTURE
    )["diagnosis"]
    active_tags = {tag.lower() for tag in diagnosis["active_issue_tags"]}
    dispute_text = diagnosis["dispute_type"]

    assert diagnosis["contract_type"] == "Service Agreement"
    assert "SaaS Agreement" not in diagnosis["contract_type"]

    for expected in (
        "confidentiality",
        "unauthorized disclosure",
        "notice",
        "indemnity",
        "third-party ip claim",
        "damages",
        "liability limitation",
        "liability cap carve-out",
    ):
        assert expected in active_tags

    for forbidden in (
        "payment",
        "invoice dispute",
        "refund",
        "delivery",
        "late delivery",
        "force majeure",
        "sla",
        "service credit",
        "suspension",
        "liquidated damages",
        "cover costs",
    ):
        assert forbidden not in active_tags

    for expected_type in (
        "Confidentiality",
        "Unauthorized Disclosure / Data Exposure",
        "Indemnity",
        "Third-Party IP Claim / Intellectual Property",
        "Notice",
        "Damages/Liability",
    ):
        assert expected_type in dispute_text

    for forbidden_type in (
        "Payment/Invoice Dispute",
        "Refund",
        "Force Majeure",
        "SLA/Service Credit",
        "Suspension",
    ):
        assert forbidden_type not in dispute_text


def test_playground_confidentiality_ip_clauses_issues_and_timeline() -> None:
    diagnosis = _run_playground_diagnosis(
        CONFIDENTIALITY_IP_INDEMNITY_FIXTURE
    )["diagnosis"]
    clause_text = "\n".join(diagnosis["clause_signals"])
    key_issue_text = "\n".join(diagnosis["key_issues"])
    timeline_text = "\n".join(diagnosis["timeline_facts"])

    for expected_clause in (
        "confidentiality obligations",
        "unauthorized-disclosure notice requirement",
        "3-business-day unauthorized-disclosure notice requirement",
        "indemnity clause",
        "third-party IP claim indemnity",
        "10-day indemnity notice requirement",
        "defense control / settlement consent",
        "consequential damages exclusion",
        "lost-profit damages exclusion",
        "twelve-month fee liability cap",
        "confidentiality carve-out",
        "indemnity carve-out",
        "contractual notice contacts",
        "deemed receipt rule",
        "force majeure clause mentioned but not fact-triggered",
    ):
        assert expected_clause in clause_text

    for required in (
        "May 3 upload to a public workspace",
        "product launch plan and pricing model qualify as confidential information",
        "before May 6",
        "3-business-day notice requirement",
        "May 8 removal",
        "anonymous page views show third-party access",
        "subcontractors had confidentiality obligations",
        "May 10 third-party IP demand triggers indemnity",
        "May 12 indemnity notice was timely under the 10-day notice requirement",
        "May 12 notice was sent to the contractual notice contacts",
        "analytics template was provider-owned or derived from customer-provided materials",
        "confidentiality or indemnity carve-outs prevent the twelve-month fee cap",
        "remediation, investigation, defense, or business-impact damages are recoverable",
    ):
        assert required in key_issue_text

    for forbidden in (
        "refund calculation",
        "performed vs unperformed services",
        "lost productivity",
        "unpaid invoices",
        "force majeure notice",
        "migration deadline",
        "liquidated damages",
        "temporary consultant",
        "cover cost",
        "SLA",
        "uptime",
        "suspension",
    ):
        assert forbidden.lower() not in key_issue_text.lower()

    for expected_timeline in (
        "May 3: provider uploaded confidential materials to a public workspace.",
        "May 6: customer discovered the public link or workspace exposure.",
        "May 8: provider removed the file or completed initial containment.",
        "May 10: third-party IP demand letter or infringement claim.",
        "May 12: customer indemnity notice.",
        "3-business-day unauthorized-disclosure notice period",
        "10-day indemnity notice period",
        "Deemed receipt rule identified",
    ):
        assert expected_timeline in timeline_text


def test_playground_confidentiality_ip_gaps_next_steps_preview_and_exports_are_scoped() -> None:
    output = _run_playground_diagnosis(CONFIDENTIALITY_IP_INDEMNITY_FIXTURE)
    diagnosis = output["diagnosis"]
    exported = json.loads(output["json"])
    markdown = output["markdown"]
    test_case = output["test_case"]
    gaps = "\n".join(exported["evidence_gaps"])
    next_steps = "\n".join(exported["suggested_next_steps"])

    for expected_gap in (
        "Exact date when the provider first discovered the public workspace exposure",
        "Whether anonymous page views reflect actual third-party access or internal testing",
        "Whether subcontractors were bound by confidentiality obligations at least as protective as the Agreement",
        "Proof that the customer's May 12 indemnity notice was sent to the contractual notice contacts",
        "Technical comparison between the provider analytics template and the third-party copyrighted work",
        "Evidence showing whether the analytics template was provider-owned or derived from customer-provided materials",
        "Defense cost estimate for the third-party IP claim",
        "Calculation of remediation, investigation, and claimed business-impact damages",
    ):
        assert expected_gap in gaps

    for forbidden_gap in (
        "invoice dates",
        "payment due-date",
        "invoice dispute notice",
        "performed vs unperformed",
        "refund calculation",
    ):
        assert forbidden_gap not in gaps.lower()

    for expected_step in (
        "Build a May 3 / May 6 / May 8 / May 10 / May 12 timeline.",
        "Determine provider's actual discovery date for the public exposure.",
        "Verify whether the provider gave unauthorized-disclosure notice within the 3-business-day notice period.",
        "Review workspace access logs, including anonymous page views.",
        "Verify subcontractor confidentiality obligations.",
        "Verify proof of May 12 indemnity notice delivery to contractual notice contacts.",
        "Compare the analytics template with the third-party copyrighted work.",
        "Determine whether the template was provider-owned or derived from customer materials.",
        "Estimate defense costs and remediation/investigation costs.",
        "Analyze confidentiality and indemnity carve-outs from the twelve-month liability cap.",
        "Review damages exclusions and recoverability of business-impact damages.",
    ):
        assert expected_step in next_steps

    for forbidden_step in (
        "force majeure notice timeline",
        "migration deadline",
        "remote tools",
        "alternate staffing",
        "temporary consultant",
        "liquidated damages",
        "invoice receipt",
        "refund calculation",
        "service credits",
        "uptime",
        "suspension",
    ):
        assert forbidden_step not in next_steps.lower()

    assert exported["active_issue_tags"] == diagnosis["active_issue_tags"]
    assert exported["issue_tags"] == diagnosis["active_issue_tags"]
    assert exported["key_issues"] == diagnosis["key_issues"]
    assert exported["evidence_gaps"] == diagnosis["evidence_gaps"]
    assert exported["timeline_facts"] == diagnosis["timeline_facts"]
    assert "payment" not in markdown.split("## Active Issue Tags", 1)[1].split(
        "## Key Issues", 1
    )[0].lower()

    assert test_case["case_name"] == "service_agreement_confidentiality_indemnity_golden"
    preview_issues = {issue.lower() for issue in test_case["expected_outputs"]["must_include_issues"]}
    for expected in (
        "confidentiality",
        "unauthorized disclosure",
        "indemnity",
        "third-party ip claim",
        "notice",
        "damages",
        "liability limitation",
    ):
        assert expected in preview_issues
    for forbidden in ("payment", "invoice dispute", "refund", "force majeure"):
        assert forbidden not in preview_issues


def test_playground_lease_repair_abatement_filters_false_issue_families() -> None:
    diagnosis = _run_playground_diagnosis(
        LEASE_REPAIR_ABATEMENT_DEPOSIT_FIXTURE
    )["diagnosis"]
    active_tags = {tag.lower() for tag in diagnosis["active_issue_tags"]}
    dispute_text = diagnosis["dispute_type"]
    clause_text = "\n".join(diagnosis["clause_signals"]).lower()

    assert diagnosis["contract_type"] == "Lease"
    assert "SaaS Agreement" not in diagnosis["contract_type"]

    for expected in (
        "lease maintenance",
        "repair obligation",
        "notice",
        "cure period",
        "rent abatement",
        "rent withholding",
        "payment default",
        "security deposit",
        "tenant-caused damage",
        "property damage causation",
        "damages",
        "liability limitation",
    ):
        assert expected in active_tags

    for forbidden in (
        "force majeure",
        "saas",
        "sla",
        "service credit",
        "platform suspension",
        "suspension",
        "invoice dispute",
        "refund",
        "prepaid fees",
        "confidentiality",
        "indemnity",
        "intellectual property",
        "liquidated damages",
        "cover costs",
    ):
        assert forbidden not in active_tags

    for expected_type in (
        "Lease Maintenance / Repair",
        "Notice/Cure Period",
        "Rent Abatement",
        "Security Deposit",
        "Damages/Liability",
    ):
        assert expected_type in dispute_text

    for forbidden_type in (
        "Force Majeure",
        "SaaS",
        "SLA/Service Credit",
        "Payment/Invoice Dispute",
        "Refund",
        "Confidentiality",
        "Indemnity",
        "Intellectual Property",
        "Suspension",
        "Liquidated Damages",
        "Cover Costs",
        "Termination",
    ):
        assert forbidden_type not in dispute_text

    assert "force majeure clause mentioned but not fact-triggered" in clause_text
    assert "sla/service credit" not in clause_text
    assert "invoice timing" not in clause_text
    assert "liquidated damages" not in clause_text
    assert "cover costs" not in clause_text


def test_playground_lease_repair_key_issues_timeline_and_gaps_are_fact_specific() -> None:
    diagnosis = _run_playground_diagnosis(
        LEASE_REPAIR_ABATEMENT_DEPOSIT_FIXTURE
    )["diagnosis"]
    key_issue_text = "\n".join(diagnosis["key_issues"])
    timeline_text = "\n".join(diagnosis["timeline_facts"])
    gaps_text = "\n".join(diagnosis["evidence_gaps"])
    risk_text = "\n".join(diagnosis["risk"]["rationale"]).lower()

    assert diagnosis["risk_signal"] == "medium"
    assert diagnosis["risk"]["evidence_dependent"] is True

    for required in (
        "September 4 tenant email satisfied the lease notice requirement",
        "certified mail was also required",
        "September 4 email was sent to the lease schedule notice email address",
        "email plus certified mail rule",
        "10-business-day cure period was triggered",
        "landlord began commercially reasonable roof repairs",
        "September 15 roof contractor inspection qualifies",
        "October 12 was timely enough",
        "water intrusion materially interfered",
        "rent abatement is available for September 4 through October 12",
        "affected area and affected period",
        "40% October rent withholding was authorized rent abatement or an unauthorized payment default",
        "$8,500 security deposit deduction",
        "roof leak or tenant misuse",
        "November 1 move-out/surrender",
        "display-fixture damages",
        "twelve months of base rent liability cap",
    ):
        assert required in key_issue_text

    for forbidden in (
        "claimed lost revenue",
        "invoked external event",
        "force majeure",
        "SaaS",
        "SLA",
        "service credits",
        "invoices",
        "invoice dispute",
        "suspension",
        "order form",
        "refund",
        "prepaid",
        "indemnity",
        "confidentiality",
        "IP claim",
        "liquidated damages",
        "cover costs",
    ):
        assert forbidden.lower() not in key_issue_text.lower()

    for expected_timeline in (
        "September 3: tenant discovered water intrusion.",
        "September 4: tenant sent email notice reporting water intrusion.",
        "September 7: landlord responded and said it would inspect.",
        "September 15: roof contractor inspected and found deteriorated roof flashing.",
        "October rent: tenant withheld 40% of rent.",
        "October 12: landlord completed roof repairs.",
        "November 1: move-out inspection or surrender event.",
        "30 days after surrender: deadline for itemized deposit statement from November 1, if applicable.",
        "10-business-day repair cure period: calculate from valid/deemed receipt once notice delivery method is verified.",
        "Deemed receipt rule: two business days after mailing or next business day after email transmission, whichever occurs later.",
    ):
        assert expected_timeline in timeline_text

    for expected_gap in (
        "Proof that the September 4 notice was sent by certified mail",
        "Whether the September 4 email was sent to the exact lease schedule notice email address",
        "Whether the roof leak materially interfered with the tenant's use of the premises",
        "Square footage or area affected by the leak",
        "10-business-day cure deadline calculation from valid or deemed receipt",
        "Whether the landlord began commercially reasonable repairs within 10 business days after valid receipt",
        "Whether the flooring and repainting damage was caused by roof leak or tenant misuse",
        "Whether the $8,500 deduction was limited to damage beyond ordinary wear and tear",
        "Calculation of rent abatement for the affected area and affected period",
        "Evidence supporting display-fixture damages",
        "Proof of itemized deposit statement timing within 30 days after surrender",
    ):
        assert expected_gap in gaps_text

    for forbidden_gap in (
        "signed agreement",
        "lost revenue calculation",
        "invoice dates",
        "invoice receipt",
        "order form",
        "sla monitoring",
        "integration logs",
        "indemnity notice proof",
        "technical ip comparison",
    ):
        assert forbidden_gap not in gaps_text.lower()

    for expected_risk in (
        "notice delivery method and valid receipt remain evidence-dependent",
        "cure deadline depends on valid notice and deemed receipt",
        "repair obligation depends on whether the landlord began commercially reasonable repairs",
        "rent abatement depends on material interference, affected area, and affected period",
        "rent withholding may create payment default risk if unauthorized",
        "security deposit deduction depends on causation and documentation",
        "base-rent liability cap may limit recovery",
    ):
        assert expected_risk in risk_text

    for forbidden_risk in (
        "force majeure",
        "external event",
        "lost revenue",
        "suspension",
        "invoice dispute",
        "saas",
        "sla",
        "service-credit",
        "indemnity",
        "confidentiality",
    ):
        assert forbidden_risk not in risk_text


def test_playground_lease_repair_next_steps_preview_and_exports_are_scoped() -> None:
    output = _run_playground_diagnosis(LEASE_REPAIR_ABATEMENT_DEPOSIT_FIXTURE)
    diagnosis = output["diagnosis"]
    exported = json.loads(output["json"])
    markdown = output["markdown"]
    test_case = output["test_case"]
    next_steps = "\n".join(exported["suggested_next_steps"])
    active_section = markdown.split("## Active Issue Tags", 1)[1].split(
        "## Key Issues", 1
    )[0]

    for expected_step in (
        "Build a September 3 / September 4 / September 7 / September 15 / October rent / October 12 / November 1 timeline.",
        "Verify the lease schedule notice addresses.",
        "Verify whether the September 4 notice was sent by both required methods: email and certified mail.",
        "Calculate deemed receipt under the lease notice rule.",
        "Calculate the 10-business-day cure deadline after valid receipt.",
        "Determine whether the September 15 inspection qualifies as beginning commercially reasonable repairs.",
        "Compare repair start, contractor inspection, and October 12 completion records.",
        "Quantify the affected showroom area and affected period.",
        "Calculate permissible rent abatement by affected area and affected period.",
        "Assess whether the 40% October rent withholding was authorized rent abatement or a payment default.",
        "Compare the $8,500 security deposit deduction with move-out photos, repair invoices, and the ordinary wear-and-tear standard.",
        "Determine whether flooring and repainting damage was caused by the roof leak or tenant misuse.",
        "Review itemized deposit statement timing and sufficiency.",
        "Review consequential/lost-profit damages exclusions and twelve months of base rent liability cap.",
        "Evaluate recoverability of display-fixture damages.",
    ):
        assert expected_step in next_steps

    for forbidden_step in (
        "invoice / notice / cure / suspension",
        "order form",
        "suspension",
        "termination",
        "lost revenue",
        "saas",
        "sla",
        "service credits",
        "platform access",
        "force majeure notice",
        "external event mitigation",
        "indemnity notice",
        "ip comparison",
        "refund calculation",
        "liquidated damages",
        "cover purchase",
    ):
        assert forbidden_step not in next_steps.lower()

    assert exported["active_issue_tags"] == diagnosis["active_issue_tags"]
    assert exported["issue_tags"] == diagnosis["active_issue_tags"]
    assert exported["key_issues"] == diagnosis["key_issues"]
    assert exported["clause_signals"] == diagnosis["clause_signals"]
    assert exported["evidence_gaps"] == diagnosis["evidence_gaps"]
    assert exported["risk"]["rationale"] == diagnosis["risk"]["rationale"]
    assert exported["timeline_facts"] == diagnosis["timeline_facts"]
    assert exported["suggested_next_steps"] == diagnosis["suggested_next_steps"]
    assert "force majeure" not in active_section.lower()
    assert "Whether the invoked external event qualifies" not in markdown
    assert "Whether claimed lost revenue is barred" not in markdown

    assert test_case["case_name"] == "lease_repair_notice_abatement_deposit_golden"
    preview_issues = {
        issue.lower()
        for issue in test_case["expected_outputs"]["must_include_issues"]
    }
    for expected in (
        "notice",
        "cure period",
        "repair obligation",
        "lease maintenance",
        "rent abatement",
        "rent withholding",
        "payment default",
        "security deposit",
        "tenant-caused damage",
        "property damage causation",
        "damages",
        "liability limitation",
    ):
        assert expected in preview_issues
    for forbidden in (
        "force majeure",
        "saas",
        "sla",
        "service credit",
        "invoice dispute",
        "refund",
        "confidentiality",
        "indemnity",
        "intellectual property",
        "liquidated damages",
        "cover costs",
        "suspension",
    ):
        assert forbidden not in preview_issues


def test_playground_lease_evidence_gaps_use_extracted_values_not_fixture_literals() -> None:
    fixture = dict(LEASE_REPAIR_ABATEMENT_DEPOSIT_FIXTURE)
    replacements = {
        "September 3": "January 8",
        "September 4": "January 9",
        "September 7": "January 10",
        "September 15": "January 18",
        "October 12": "February 2",
        "November 1": "March 1",
        "October rent": "February rent",
        "$8,500": "$4,200",
    }
    for field in (
        "disputeDescription",
        "claimantPosition",
        "respondentPosition",
        "evidence",
    ):
        updated = fixture[field]
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        fixture[field] = updated

    diagnosis = _run_playground_diagnosis(fixture)["diagnosis"]
    scoped_text = json.dumps(
        {
            "key_issues": diagnosis["key_issues"],
            "evidence_gaps": diagnosis["evidence_gaps"],
            "timeline_facts": diagnosis["timeline_facts"],
            "suggested_next_steps": diagnosis["suggested_next_steps"],
        }
    )

    assert "January 9 notice" in scoped_text
    assert "January 9 email" in scoped_text
    assert "$4,200 deduction" in scoped_text
    assert "February rent withholding" in scoped_text
    assert "September 4" not in scoped_text
    assert "$8,500" not in scoped_text


def test_playground_diagnosis_runs_do_not_cross_contaminate_issue_templates() -> None:
    refund_then_confidentiality = _run_playground_diagnoses_sequentially(
        [REFUND_TERMINATION_ACCEPTANCE_FIXTURE, CONFIDENTIALITY_IP_INDEMNITY_FIXTURE]
    )[1]
    force_then_confidentiality = _run_playground_diagnoses_sequentially(
        [POSITIVE_FORCE_MAJEURE_DELIVERY_FIXTURE, CONFIDENTIALITY_IP_INDEMNITY_FIXTURE]
    )[1]
    saas_then_confidentiality = _run_playground_diagnoses_sequentially(
        [SAAS_NOTICE_CURE_FIXTURE, CONFIDENTIALITY_IP_INDEMNITY_FIXTURE]
    )[1]

    confidentiality_outputs = (
        refund_then_confidentiality,
        force_then_confidentiality,
        saas_then_confidentiality,
    )
    for diagnosis in confidentiality_outputs:
        text = json.dumps(diagnosis).lower()
        for forbidden in (
            "refund calculation",
            "performed vs unperformed",
            "lost productivity",
            "force majeure notice",
            "migration deadline",
            "remote migration tools",
            "alternate staffing",
            "temporary consultant",
            "liquidated damages",
            "service credit",
            "uptime",
            "suspension",
            "invoice receipt",
            "invoice dispute",
        ):
            assert forbidden not in text

    saas_then_refund = _run_playground_diagnoses_sequentially(
        [SAAS_NOTICE_CURE_FIXTURE, REFUND_TERMINATION_ACCEPTANCE_FIXTURE]
    )[1]
    refund_text = json.dumps(saas_then_refund).lower()
    for forbidden in ("service credit", "uptime", "suspension"):
        assert forbidden not in refund_text

    force_then_lease = _run_playground_diagnoses_sequentially(
        [POSITIVE_FORCE_MAJEURE_DELIVERY_FIXTURE, LEASE_REPAIR_ABATEMENT_DEPOSIT_FIXTURE]
    )[1]
    saas_then_lease = _run_playground_diagnoses_sequentially(
        [SAAS_NOTICE_CURE_FIXTURE, LEASE_REPAIR_ABATEMENT_DEPOSIT_FIXTURE]
    )[1]
    refund_then_lease = _run_playground_diagnoses_sequentially(
        [REFUND_TERMINATION_ACCEPTANCE_FIXTURE, LEASE_REPAIR_ABATEMENT_DEPOSIT_FIXTURE]
    )[1]
    confidentiality_then_lease = _run_playground_diagnoses_sequentially(
        [CONFIDENTIALITY_IP_INDEMNITY_FIXTURE, LEASE_REPAIR_ABATEMENT_DEPOSIT_FIXTURE]
    )[1]

    for diagnosis in (
        force_then_lease,
        saas_then_lease,
        refund_then_lease,
        confidentiality_then_lease,
    ):
        text = json.dumps(
            {
                "active_issue_tags": diagnosis["active_issue_tags"],
                "dispute_type": diagnosis["dispute_type"],
                "key_issues": diagnosis["key_issues"],
                "timeline_facts": diagnosis["timeline_facts"],
                "evidence_gaps": diagnosis["evidence_gaps"],
                "suggested_next_steps": diagnosis["suggested_next_steps"],
                "risk": diagnosis["risk"],
            }
        ).lower()
        for forbidden in (
            "whether the invoked external event qualifies",
            "force majeure notice",
            "external event mitigation",
            "sla/uptime",
            "service credit",
            "uptime",
            "platform access",
            "suspension",
            "integration error logs",
            "refund calculation",
            "prepaid fee",
            "performed vs unperformed",
            "invoice dispute",
            "confidentiality",
            "indemnity",
            "ip claim",
            "public workspace",
            "technical comparison",
        ):
            assert forbidden not in text


def test_mkdocs_nav_preserves_github_pages_playground_route() -> None:
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "Playground: playground/index.html" in mkdocs
    assert (ROOT / "docs" / "playground" / "index.html").exists()


def test_mkdocs_nav_includes_agent_eval_route() -> None:
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "Agent Evaluation: agent-eval/index.html" in mkdocs
    assert (ROOT / "docs" / "agent-eval" / "index.html").exists()


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


def test_agent_eval_static_demo_files_exist_and_parse() -> None:
    html_path = ROOT / "docs" / "agent-eval" / "index.html"
    js_path = ROOT / "docs" / "assets" / "agent-eval.js"
    css_path = ROOT / "docs" / "assets" / "agent-eval.css"

    assert html_path.exists()
    assert js_path.exists()
    assert css_path.exists()

    node = shutil.which("node")
    if node:
        completed = subprocess.run(
            [node, "--check", str(js_path)],
            text=True,
            capture_output=True,
        )
        assert completed.returncode == 0, completed.stderr


def test_agent_eval_demo_is_static_and_has_required_inputs_outputs() -> None:
    html = (ROOT / "docs" / "agent-eval" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "docs" / "assets" / "agent-eval.js").read_text(encoding="utf-8")
    combined = html + "\n" + js

    for required in (
        "agent-description",
        "sample-profile",
        "load-sample-profile",
        "declared-capabilities",
        "tool-names",
        "tool-permissions",
        "can-read-files",
        "can-write-files",
        "can-run-code",
        "can-use-browser",
        "can-use-network",
        "can-execute-transactions",
        "can-modify-external-state",
        "requires-human-approval",
        "sample-tasks",
        "policy-constraints",
        "experiment-summary",
        "Classified agent type(s)",
        "Matched signals",
        "Evidence basis",
        "Missing evidence",
        "Outcome prediction",
        "Prediction confidence",
        "Data/source references used",
        "Recommended next evals",
        "JSON Export",
        "Markdown Export",
        "sample_profiles.json",
        "vague_unknown_agent",
        "coding_file_reading_hybrid",
        "browser_navigation_agent",
        "simulated_financial_transaction_agent",
        "contract_review_agent",
    ):
        assert required in combined

    assert "No backend" in combined
    assert "external API calls" in combined

    forbidden_runtime = ("api.openai.com", "XMLHttpRequest", "WebSocket", "eval(")
    for forbidden in forbidden_runtime:
        assert forbidden not in combined
    assert "API key" not in combined


def test_agent_eval_demo_has_language_switch_and_i18n_dictionary() -> None:
    html = (ROOT / "docs" / "agent-eval" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "docs" / "assets" / "agent-eval.js").read_text(encoding="utf-8")

    assert 'data-lang="en"' in html
    assert 'data-lang="zh"' in html
    assert 'data-i18n="page.title"' in html
    assert 'data-i18n="form.agentDescription"' in html
    assert 'data-i18n="exports.markdown"' in html
    assert "const I18N" in js
    assert "localStorage" in js
    assert "URLSearchParams" in js
    assert "智能体评估演示" in js
    assert "缺失证据" in js
    assert "金融交易仅限模拟" in js


def test_agent_eval_static_demo_sample_loading_and_chinese_rendering() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required to execute the static agent eval demo")

    js_path = ROOT / "docs" / "assets" / "agent-eval.js"
    script = f"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync({json.dumps(str(js_path))}, "utf8");
function makeElement(id) {{
  const listeners = {{}};
  return {{
    id,
    value: id === "sample-profile" ? "coding_file_reading_hybrid" : "",
    checked: false,
    textContent: "",
    innerHTML: "",
    dataset: {{}},
    style: {{}},
    listeners,
    addEventListener(type, handler) {{ listeners[type] = handler; }},
    setAttribute(name, value) {{ this[name] = value; }},
    getAttribute(name) {{ return this[name] || ""; }},
    classList: {{ toggle() {{}}, add() {{}}, remove() {{}} }}
  }};
}}
const elements = new Map();
[
  "agent-eval-form",
  "sample-profile",
  "load-sample-profile",
  "agent-name",
  "autonomy-level",
  "agent-description",
  "declared-capabilities",
  "tool-names",
  "tool-permissions",
  "can-read-files",
  "can-write-files",
  "can-run-code",
  "can-use-browser",
  "can-use-network",
  "can-execute-transactions",
  "can-modify-external-state",
  "requires-human-approval",
  "sample-tasks",
  "policy-constraints",
  "experiment-summary",
  "agent-eval-output",
  "json-export",
  "markdown-export"
].forEach((id) => elements.set(id, makeElement(id)));
const languageButtons = [
  {{ dataset: {{ lang: "en" }}, classList: {{ toggle() {{}} }}, setAttribute() {{}}, addEventListener() {{}} }},
  {{ dataset: {{ lang: "zh" }}, classList: {{ toggle() {{}} }}, setAttribute() {{}}, addEventListener() {{}} }}
];
const document = {{
  documentElement: {{ lang: "" }},
  listeners: {{}},
  addEventListener(type, handler) {{ this.listeners[type] = handler; }},
  getElementById(id) {{
    if (!elements.has(id)) {{
      elements.set(id, makeElement(id));
    }}
    return elements.get(id);
  }},
  querySelectorAll(selector) {{
    return selector === "[data-lang]" ? languageButtons : [];
  }}
}};
const storage = {{}};
const window = {{
  location: {{ search: "?lang=zh" }},
  localStorage: {{
    getItem(key) {{ return storage[key] || ""; }},
    setItem(key, value) {{ storage[key] = value; }}
  }}
}};
const context = {{ document, window, console, URLSearchParams }};
vm.runInNewContext(code, context);
(async () => {{
  document.listeners.DOMContentLoaded();
  await Promise.resolve();
  elements.get("sample-profile").value = "browser_navigation_agent";
  elements.get("load-sample-profile").listeners.click();
  process.stdout.write(JSON.stringify({{
    language: context.window.Contract2AgentEvalDemo.getLanguage(),
    document_lang: document.documentElement.lang,
    browser_checked: elements.get("can-use-browser").checked,
    network_checked: elements.get("can-use-network").checked,
    output_html: elements.get("agent-eval-output").innerHTML,
    markdown: elements.get("markdown-export").value,
    json_export: elements.get("json-export").value
  }}));
}})().catch((error) => {{
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
}});
"""
    completed = subprocess.run(
        [node, "-e", script],
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)

    assert result["language"] == "zh"
    assert result["document_lang"] == "zh-CN"
    assert result["browser_checked"] is True
    assert result["network_checked"] is True
    assert "浏览器导航智能体" in result["output_html"]
    assert "证据依据" in result["output_html"]
    assert result["markdown"].startswith("# 智能体评估报告")
    assert "browser_navigation_agent" in result["json_export"]


def test_agent_eval_static_source_reference_json_exists_and_is_contextual() -> None:
    source_path = ROOT / "docs" / "data" / "agent_eval" / "source_references.json"
    category_path = ROOT / "docs" / "data" / "agent_eval" / "eval_categories.json"

    sources = json.loads(source_path.read_text(encoding="utf-8"))["sources"]
    categories = json.loads(category_path.read_text(encoding="utf-8"))["eval_categories"]

    source_ids = {source["source_id"] for source in sources}
    assert {
        "openai_agent_evals_methodology",
        "swe_bench_reference",
        "webarena_reference",
    }.issubset(source_ids)
    assert all(source["reliability"] <= 0.2 for source in sources)
    assert any(category["category_id"] == "profile_completion" for category in categories)


def test_agent_eval_static_sample_profiles_cover_requested_cases() -> None:
    sample_path = ROOT / "docs" / "data" / "agent_eval" / "sample_profiles.json"

    profiles = json.loads(sample_path.read_text(encoding="utf-8"))["profiles"]
    profiles_by_id = {profile["profile_id"]: profile for profile in profiles}

    assert set(profiles_by_id) == {
        "vague_unknown_agent",
        "coding_file_reading_hybrid",
        "browser_navigation_agent",
        "simulated_financial_transaction_agent",
        "contract_review_agent",
    }

    required_keys = {
        "label",
        "description",
        "declared_capabilities",
        "tools",
        "tool_permissions",
        "sample_tasks",
        "policy_constraints",
        "experiment_summary",
        "can_read_files",
        "can_write_files",
        "can_run_code",
        "can_use_browser",
        "can_use_network",
        "can_execute_transactions",
        "can_modify_external_state",
        "requires_human_approval",
        "autonomy_level",
    }
    for profile in profiles:
        assert required_keys.issubset(profile)

    vague = profiles_by_id["vague_unknown_agent"]
    assert vague["tools"] == ""
    assert vague["sample_tasks"] == ""
    assert vague["autonomy_level"] == "unknown"

    hybrid = profiles_by_id["coding_file_reading_hybrid"]
    assert hybrid["can_read_files"] is True
    assert hybrid["can_write_files"] is True
    assert hybrid["can_run_code"] is True
    assert "cite" in hybrid["declared_capabilities"]

    browser = profiles_by_id["browser_navigation_agent"]
    assert browser["can_use_browser"] is True
    assert browser["can_use_network"] is True
    assert browser["requires_human_approval"] is True
    assert "approval" in browser["policy_constraints"].lower()

    finance = profiles_by_id["simulated_financial_transaction_agent"]
    assert finance["can_execute_transactions"] is True
    assert finance["can_modify_external_state"] is False
    assert finance["requires_human_approval"] is True
    assert "simulation only" in finance["policy_constraints"].lower()

    contract = profiles_by_id["contract_review_agent"]
    assert contract["can_read_files"] is True
    assert "contract_parser" in contract["tools"]
    assert "evidence gaps" in contract["declared_capabilities"]


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


def test_bilingual_readmes_are_linked_and_project_aligned() -> None:
    readme_path = ROOT / "README.md"
    zh_path = ROOT / "README.zh-CN.md"
    readme = readme_path.read_text(encoding="utf-8")
    zh = zh_path.read_text(encoding="utf-8")
    language_switch = "[English](./README.md) | [中文](./README.zh-CN.md)"

    assert readme_path.exists()
    assert zh_path.exists()
    assert language_switch in readme
    assert language_switch in zh
    assert "Pre-runtime AI agent evaluation" in readme
    assert "预运行 AI 智能体评估" in zh

    for english_heading, chinese_heading in (
        ("## Project Purpose", "## 项目目的"),
        ("## Evaluation-First Design", "## 评估优先设计"),
        ("## Static Demo", "## 静态演示"),
        ("## CLI Usage", "## CLI 用法"),
        ("## Testing", "## 测试"),
        ("## Limitations", "## 限制"),
    ):
        assert english_heading in readme
        assert chinese_heading in zh

    assert "no backend" in readme.lower()
    assert "没有后端" in zh
    assert "Benchmark references are contextual" in readme
    assert "基准引用" in zh
    assert "simulation-only" in readme.lower()
    assert "仅限模拟" in zh


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


def _markdown_list_items(markdown: str, heading: str) -> list[str]:
    section = markdown.split(f"## {heading}", 1)[1]
    next_heading = section.find("\n## ")
    if next_heading != -1:
        section = section[:next_heading]
    return [
        line.removeprefix("- ").strip()
        for line in section.splitlines()
        if line.startswith("- ")
    ]


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
  const listeners = {{}};
  return {{
    id,
    value: "",
    textContent: "",
    innerHTML: "",
    className: "",
    dataset: {{}},
    style: {{}},
    reset() {{}},
    remove() {{}},
    select() {{}},
    setAttribute() {{}},
    addEventListener(type, handler) {{ listeners[type] = handler; }},
    listeners,
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
  listeners: {{}},
  addEventListener(type, handler) {{ this.listeners[type] = handler; }}
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
let copiedKind = "";
const copied = {{}};
const navigator = {{
  clipboard: {{
    writeText(text) {{
      copied[copiedKind] = text;
      return Promise.resolve();
    }}
  }}
}};
const context = {{ document, window: {{ isSecureContext: true }}, navigator, console }};
vm.runInNewContext(code, context);
(async () => {{
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  const api = context.window.Contract2AgentPlayground;
  const fieldIds = {{
    contractType: "contract-type",
    disputeType: "dispute-type",
    outputFormat: "output-format",
    diagnosisDepth: "diagnosis-depth",
    riskMode: "risk-mode",
    desiredOutcome: "desired-outcome",
    contractText: "contract-text",
    disputeDescription: "dispute-description",
    claimantPosition: "claimant-position",
    respondentPosition: "respondent-position",
    evidence: "evidence",
    metadata: "metadata"
  }};
  Object.entries(fieldIds).forEach(([key, id]) => {{
    elements.get(id).value = input[key] || "";
  }});
  elements.get("diagnosis-form").listeners.submit({{ preventDefault() {{}} }});
  copiedKind = "markdown";
  await elements.get("copy-markdown").listeners.click();
  copiedKind = "json";
  await elements.get("copy-json").listeners.click();
  copiedKind = "test-case";
  await elements.get("copy-test-case").listeners.click();
  const diagnosis = api.analyzeDispute(input);
  process.stdout.write(JSON.stringify({{
    diagnosis,
    markdown: copied.markdown,
    json: copied.json,
    test_case: JSON.parse(copied["test-case"])
  }}));
}})().catch((error) => {{
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
}});
"""
    completed = subprocess.run(
        [node, "-e", script],
        input=json.dumps(input_case),
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _run_playground_diagnoses_sequentially(input_cases: list[dict]) -> list[dict]:
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
const inputs = JSON.parse(fs.readFileSync(0, "utf8"));
const api = context.window.Contract2AgentPlayground;
process.stdout.write(JSON.stringify(inputs.map((input) => api.analyzeDispute(input))));
"""
    completed = subprocess.run(
        [node, "-e", script],
        input=json.dumps(input_cases),
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)
