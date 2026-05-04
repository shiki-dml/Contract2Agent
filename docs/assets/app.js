(function () {
  "use strict";

  const samples = {
    "service-payment": {
      contractType: "Service Agreement",
      disputeType: "Payment Delay",
      outputFormat: "Markdown-style",
      diagnosisDepth: "Standard",
      riskMode: "Balanced",
      desiredOutcome: "Recover unpaid invoices while preserving leverage for service suspension.",
      contractText:
        "The client must pay all undisputed invoices within 30 days. The provider may suspend service after written notice and a 10-day cure period. Disputed invoice amounts must be identified in writing before the payment due date.",
      disputeDescription:
        "The client has not paid two monthly invoices. The provider sent one email notice and suspended dashboard access 12 days later. The client argues the invoices were disputed because several deliverables were incomplete.",
      claimantPosition:
        "The provider says the invoices were accepted, overdue, and never disputed before the due dates.",
      respondentPosition:
        "The client says the invoices were disputed and suspension was premature because the notice did not clearly start the cure period.",
      evidence:
        "Invoices, email notice, account suspension log, delivery messages, and signed service agreement are available. Payment records and a clear dispute notice are still being collected.",
      metadata:
        '{"currency":"USD","timeline":"invoice dates known, dispute notice date unclear"}'
    },
    "delivery-delay": {
      contractType: "Sales Contract",
      disputeType: "Late Delivery",
      outputFormat: "Detailed",
      diagnosisDepth: "Detailed",
      riskMode: "Evidence-first",
      desiredOutcome: "Assess whether late delivery supports price reduction or rejection.",
      contractText:
        "Seller must deliver the hardware batch by March 15. Buyer must inspect within five business days after delivery. Acceptance is based on the delivery schedule and the technical specification in Exhibit A.",
      disputeDescription:
        "The shipment arrived on March 29. The buyer sent messages complaining about delay and missing accessories. The seller says logistics delays were outside its control and the buyer accepted the shipment by using the units.",
      claimantPosition:
        "The buyer says the missed deadline defeated the deployment plan and caused measurable replacement costs.",
      respondentPosition:
        "The seller says the buyer accepted the goods, did not reject within the inspection window, and has not proven damages.",
      evidence:
        "Shipping receipt, delivery confirmation, warehouse log, buyer messages, and signed purchase order. Damages calculation is incomplete.",
      metadata:
        '{"region":"example only","delivery_date":"March 29","contract_deadline":"March 15"}'
    },
    "termination-cure": {
      contractType: "Freelance Contract",
      disputeType: "Notice/Cure Period",
      outputFormat: "Summary",
      diagnosisDepth: "Standard",
      riskMode: "Conservative",
      desiredOutcome: "Evaluate whether termination was valid and what evidence is missing.",
      contractText:
        "Either party may terminate for material breach after written notice and a 14-day cure period. Termination for convenience requires 30 days written notice. Work accepted before termination remains payable.",
      disputeDescription:
        "The client terminated the contractor immediately after a missed milestone. The contractor says no written breach notice was sent and the milestone was delayed because source materials arrived late.",
      claimantPosition:
        "The contractor seeks payment for accepted work and argues immediate termination violated the cure-period clause.",
      respondentPosition:
        "The client says the missed milestone was material, the delay was repeated, and informal messages gave enough warning.",
      evidence:
        "Milestone plan, Slack messages, email thread, partial acceptance notes, and invoice. No formal breach notice has been found.",
      metadata:
        '{"timeline":"source material delay before milestone","notice_channel":"messages and email"}'
    },
    "refund-dispute": {
      contractType: "Service Agreement",
      disputeType: "Refund",
      outputFormat: "JSON-style",
      diagnosisDepth: "Quick",
      riskMode: "Balanced",
      desiredOutcome: "Decide whether a partial refund position is supportable.",
      contractText:
        "Fees are non-refundable except where services are not delivered after a documented service failure. Client must provide written notice of the alleged failure within 10 days after discovery.",
      disputeDescription:
        "The client prepaid for a campaign package and requests a full refund after canceling midway. The provider says work was delivered and the refund clause does not apply.",
      claimantPosition:
        "The client says promised launch assets were missing and the campaign could not go live.",
      respondentPosition:
        "The provider says draft assets and status logs show substantial delivery, so a full refund is not justified.",
      evidence:
        "Project board export, message thread, payment receipt, draft asset links, and cancellation email. There is no itemized refund calculation yet.",
      metadata:
        '{"payment":"prepaid","requested_resolution":"partial refund analysis"}'
    },
    "saas-suspension": {
      contractType: "SaaS Agreement",
      disputeType: "Payment Delay",
      outputFormat: "Detailed",
      diagnosisDepth: "Detailed",
      riskMode: "Escalation review",
      desiredOutcome: "Assess suspension timing and service restoration options.",
      contractText:
        "Customer must pay undisputed subscription fees within 15 days of invoice. Provider may suspend access after written notice and a 7-day cure period. SLA credits are the exclusive remedy for uptime incidents unless caused by willful misconduct.",
      disputeDescription:
        "The provider suspended access after one reminder email. The customer says invoices included disputed overage fees and that an uptime incident created service credits.",
      claimantPosition:
        "The provider says core subscription fees were undisputed and overdue, so suspension was allowed after notice.",
      respondentPosition:
        "The customer says the notice was vague, overage fees were disputed, and suspension caused operational losses.",
      evidence:
        "Invoices, admin access logs, reminder email, uptime incident logs, and customer support messages. Payment allocation records are missing.",
      metadata:
        '{"service":"SaaS","sla_credit_issue":true,"overage_fees_disputed":true}'
    }
  };

  const keywordGroups = {
    payment: ["payment", "invoice", "unpaid", "overdue", "fee", "fees", "refund"],
    delivery: ["delivery", "milestone", "deadline", "delay", "acceptance", "shipment"],
    termination: ["terminate", "termination", "cancel", "cancellation"],
    notice: ["notice", "written notice", "cure period", "breach notice", "cure"],
    liability: ["damages", "liability", "indemnity", "penalty", "limitation"],
    "force majeure": ["force majeure", "impossibility", "uncontrollable"],
    confidentiality: ["confidential", "nda", "disclosure"],
    service: ["uptime", "sla", "suspension", "access", "service"],
    evidence: ["email", "invoice", "receipt", "log", "message", "signed", "proof"]
  };

  const fields = {
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
  };

  let latestDiagnosis = null;
  let latestMarkdown = "";
  let latestJson = "";

  const form = document.getElementById("diagnosis-form");
  const resultOutput = document.getElementById("result-output");
  const riskBadge = document.getElementById("risk-badge");
  const copyStatus = document.getElementById("copy-status");

  function getValue(id) {
    const element = document.getElementById(id);
    return element ? element.value.trim() : "";
  }

  function setValue(id, value) {
    const element = document.getElementById(id);
    if (element) {
      element.value = value || "";
    }
  }

  function readForm() {
    return Object.fromEntries(
      Object.entries(fields).map(([key, id]) => [key, getValue(id)])
    );
  }

  function loadSample(sampleId) {
    const sample = samples[sampleId] || samples["service-payment"];
    Object.entries(fields).forEach(([key, id]) => setValue(id, sample[key]));
    document.getElementById("sample-select").value = sampleId;
    document.querySelectorAll(".sample-chip").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.sample === sampleId);
    });
    copyStatus.textContent = `Loaded ${sampleId.replaceAll("-", " ")}.`;
  }

  function normalize(text) {
    return (text || "").toLowerCase();
  }

  function hasAny(text, words) {
    const normalized = normalize(text);
    return words.some((word) => normalized.includes(word));
  }

  function countGroup(text, group) {
    return keywordGroups[group].reduce(
      (count, word) => count + (normalize(text).includes(word) ? 1 : 0),
      0
    );
  }

  function detectGroups(data) {
    const combined = [
      data.contractType,
      data.disputeType,
      data.contractText,
      data.disputeDescription,
      data.claimantPosition,
      data.respondentPosition,
      data.evidence,
      data.metadata
    ].join(" ");

    return Object.keys(keywordGroups).filter((group) => countGroup(combined, group) > 0);
  }

  function hasDateSignal(text) {
    return /\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}\b|\b\d+\s*(?:day|days|business days|week|weeks)\b/i.test(
      text
    );
  }

  function dateSignalCount(text) {
    const matches = text.match(
      /\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}\b|\b\d+\s*(?:day|days|business days|week|weeks)\b/gi
    );
    return matches ? matches.length : 0;
  }

  function buildIssues(data, groups) {
    const issues = [];
    const dispute = normalize(data.disputeType);
    const contract = normalize(data.contractType);

    if (groups.includes("payment") || dispute.includes("payment")) {
      issues.push("Whether invoices, fees, or refund amounts are owed and undisputed");
    }
    if (groups.includes("delivery") || dispute.includes("delivery")) {
      issues.push("Whether delivery deadlines, milestones, or acceptance criteria were met");
    }
    if (groups.includes("termination") || dispute.includes("termination")) {
      issues.push("Whether termination or cancellation followed the contract process");
    }
    if (groups.includes("notice") || dispute.includes("notice") || dispute.includes("cure")) {
      issues.push("Whether written notice and any cure period were properly triggered");
    }
    if (groups.includes("liability") || dispute.includes("liability")) {
      issues.push("Whether damages, liability limits, penalties, or indemnity terms apply");
    }
    if (groups.includes("force majeure")) {
      issues.push("Whether uncontrollable events or force majeure excuses performance");
    }
    if (groups.includes("confidentiality")) {
      issues.push("Whether confidential information or disclosure obligations are implicated");
    }
    if (groups.includes("service") || contract.includes("saas")) {
      issues.push("Whether service access, SLA credits, suspension rights, or uptime records matter");
    }

    if (!issues.length) {
      issues.push("Primary dispute issue is unclear from the current text");
    }

    return [...new Set(issues)];
  }

  function buildClauseSignals(data, groups) {
    const contractText = normalize(data.contractText);
    const signals = [];

    if (groups.includes("payment") || contractText.includes("invoice")) {
      signals.push("Payment timing and disputed-invoice language");
    }
    if (groups.includes("delivery") || contractText.includes("acceptance")) {
      signals.push("Delivery deadline, milestone, and acceptance criteria");
    }
    if (groups.includes("termination")) {
      signals.push("Termination rights and cancellation conditions");
    }
    if (groups.includes("notice") || contractText.includes("cure")) {
      signals.push("Written notice, breach notice, and cure-period requirements");
    }
    if (groups.includes("liability")) {
      signals.push("Damages, limitation of liability, penalty, or indemnity allocation");
    }
    if (groups.includes("service") || contractText.includes("sla")) {
      signals.push("Suspension, access, uptime, SLA credit, and service remedy terms");
    }
    if (groups.includes("force majeure")) {
      signals.push("Force majeure or impossibility language");
    }
    if (groups.includes("confidentiality")) {
      signals.push("Confidentiality, NDA, and disclosure restrictions");
    }

    return signals.length ? [...new Set(signals)] : ["No strong clause signal detected yet"];
  }

  function buildEvidenceGaps(data, groups) {
    const combined = normalize(
      [data.contractText, data.disputeDescription, data.evidence, data.metadata].join(" ")
    );
    const evidence = normalize(data.evidence);
    const respondent = normalize(data.respondentPosition);
    const dispute = normalize(data.disputeType);
    const gaps = [];

    if (!hasAny(combined, ["signed", "executed", "agreement", "purchase order"])) {
      gaps.push("Missing signed agreement or executed contract copy");
    }
    if (groups.includes("payment") && !hasDateSignal(data.evidence + " " + data.metadata)) {
      gaps.push("Missing invoice dates or payment due-date timeline");
    }
    if (groups.includes("payment") && !hasAny(evidence, ["receipt", "payment record", "bank", "ledger", "paid"])) {
      gaps.push("Missing payment records or ledger proof");
    }
    if ((groups.includes("notice") || groups.includes("termination") || groups.includes("service")) && !hasAny(combined, ["written notice", "breach notice", "notice date"])) {
      gaps.push("Missing written notice record or notice date");
    }
    if (groups.includes("notice") && !hasAny(combined, ["cure period", "cure-period timeline", "cure date", "days later"])) {
      gaps.push("Missing cure-period timeline");
    }
    if (groups.includes("delivery") && !hasAny(evidence, ["delivery confirmation", "shipping receipt", "warehouse log", "acceptance note", "delivery proof"])) {
      gaps.push("Missing delivery confirmation or acceptance record");
    }
    if (groups.includes("delivery") && !hasAny(data.contractText, ["acceptance", "specification", "criteria", "exhibit"])) {
      gaps.push("Missing acceptance criteria or delivery specification");
    }
    if ((groups.includes("liability") || groups.includes("delivery") || dispute.includes("refund")) && !hasAny(combined, ["damages calculation", "replacement cost", "loss calculation", "itemized refund", "credit amount"])) {
      gaps.push("Missing damages calculation or refund allocation");
    }
    if (!hasAny(respondent, ["disputed", "object", "objection", "defense", "premature", "accepted", "outside its control"])) {
      gaps.push("Missing respondent objection or defense record");
    }

    return gaps.length ? [...new Set(gaps)] : ["No obvious evidence gap detected from the current text"];
  }

  function buildNextSteps(data, diagnosis) {
    const steps = [
      "Build a dated timeline of contract, invoice, notice, cure period, delivery, acceptance, and dispute events",
      "Attach source evidence to each key issue instead of relying on narrative summaries"
    ];

    if (diagnosis.issueTags.includes("payment")) {
      steps.push("Separate disputed and undisputed invoice amounts and map each to payment records");
    }
    if (diagnosis.issueTags.includes("notice")) {
      steps.push("Confirm whether the notice language, channel, and cure-period start date satisfy the contract");
    }
    if (diagnosis.issueTags.includes("delivery")) {
      steps.push("Compare delivery evidence against acceptance criteria and rejection windows");
    }
    if (diagnosis.issueTags.includes("service")) {
      steps.push("Review access logs, SLA incidents, service credits, and suspension authorization");
    }
    if (data.desiredOutcome) {
      steps.push(`Frame the next report around the desired outcome: ${data.desiredOutcome}`);
    }

    return steps.slice(0, data.diagnosisDepth === "Detailed" ? 6 : 5);
  }

  function riskSignal(data, groups, gaps, clauseSignals) {
    const combined = [
      data.contractText,
      data.disputeDescription,
      data.claimantPosition,
      data.respondentPosition,
      data.evidence
    ].join(" ");
    const severe =
      groups.includes("termination") ||
      groups.includes("liability") ||
      (groups.includes("service") && normalize(combined).includes("suspension")) ||
      normalize(data.disputeType).includes("refund");
    const evidenceScore = countGroup(data.evidence, "evidence");
    const timelineScore = dateSignalCount(combined);
    const weakEvidence = evidenceScore < 2;
    const missingNoticeOrTimeline = gaps.some((gap) =>
      /notice|cure|timeline|date/i.test(gap)
    );
    const strongEvidence = evidenceScore >= 3 && timelineScore >= 2;

    if (combined.trim().length < 140) {
      return "unclear";
    }
    if (severe && weakEvidence && missingNoticeOrTimeline) {
      return "high";
    }
    if (
      normalize(data.riskMode).includes("conservative") &&
      severe &&
      missingNoticeOrTimeline &&
      gaps.length >= 3
    ) {
      return "high";
    }
    if (clauseSignals.length >= 2 && strongEvidence && gaps.length <= 2) {
      return "low";
    }
    if (groups.length || evidenceScore || gaps.length) {
      return "medium";
    }
    return "unclear";
  }

  function contestedFacts(data) {
    const facts = [];
    const respondent = normalize(data.respondentPosition);
    const claimant = normalize(data.claimantPosition);

    if (respondent.includes("disputed") || claimant.includes("undisputed")) {
      facts.push("Whether the disputed amount was actually undisputed when payment became due");
    }
    if (respondent.includes("notice") || claimant.includes("notice")) {
      facts.push("Whether notice was sent in the required form and started the cure period");
    }
    if (respondent.includes("accepted") || claimant.includes("accepted")) {
      facts.push("Whether work or goods were accepted before the dispute escalated");
    }
    if (!facts.length) {
      facts.push("Which facts each side can prove with dated records");
    }

    return facts;
  }

  function diagnose(data) {
    const groups = detectGroups(data);
    const issueTags = groups.filter((group) => group !== "evidence");
    const keyIssues = buildIssues(data, groups);
    const relevantClauseSignals = buildClauseSignals(data, groups);
    const evidenceGaps = buildEvidenceGaps(data, groups);
    const risk = riskSignal(data, groups, evidenceGaps, relevantClauseSignals);

    const diagnosis = {
      case_type: normalize(data.disputeType || "other").replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "other",
      contract_type: data.contractType,
      dispute_type: data.disputeType,
      diagnosis_depth: data.diagnosisDepth,
      output_format_preference: data.outputFormat,
      risk_mode: data.riskMode,
      risk_signal: risk,
      issue_tags: issueTags.length ? issueTags : ["unclear"],
      dispute_summary: summarize(data),
      key_issues: keyIssues,
      relevant_clause_signals: relevantClauseSignals,
      position_matrix: {
        claimant: data.claimantPosition || "No claimant position provided.",
        respondent: data.respondentPosition || "No respondent position provided.",
        contested_facts: contestedFacts(data)
      },
      evidence_gaps: evidenceGaps,
      suggested_next_steps: []
    };

    diagnosis.suggested_next_steps = buildNextSteps(data, {
      issueTags: diagnosis.issue_tags
    });

    return diagnosis;
  }

  function summarize(data) {
    const dispute = data.disputeDescription || "No dispute description provided.";
    const trimmed = dispute.replace(/\s+/g, " ").trim();
    const max = 260;
    const summary = trimmed.length > max ? `${trimmed.slice(0, max - 3)}...` : trimmed;
    return `${data.contractType || "Contract"} / ${data.disputeType || "Dispute"}: ${summary}`;
  }

  function markdownReport(diagnosis) {
    return [
      `# Contract2Agent Diagnosis Preview`,
      "",
      `**Contract type:** ${diagnosis.contract_type}`,
      `**Dispute type:** ${diagnosis.dispute_type}`,
      `**Risk signal:** ${diagnosis.risk_signal}`,
      `**Diagnosis depth:** ${diagnosis.diagnosis_depth}`,
      "",
      "## Dispute Summary",
      diagnosis.dispute_summary,
      "",
      "## Key Issues",
      ...diagnosis.key_issues.map((issue) => `- ${issue}`),
      "",
      "## Relevant Clauses or Clause Signals",
      ...diagnosis.relevant_clause_signals.map((signal) => `- ${signal}`),
      "",
      "## Claimant vs Respondent",
      `- Claimant: ${diagnosis.position_matrix.claimant}`,
      `- Respondent: ${diagnosis.position_matrix.respondent}`,
      "",
      "## Evidence Gaps",
      ...diagnosis.evidence_gaps.map((gap) => `- ${gap}`),
      "",
      "## Suggested Next Steps",
      ...diagnosis.suggested_next_steps.map((step) => `- ${step}`)
    ].join("\n");
  }

  function structuredPreview(diagnosis) {
    return {
      summary: diagnosis.dispute_summary,
      detected: {
        contract_type: diagnosis.contract_type,
        dispute_type: diagnosis.dispute_type,
        issue_tags: diagnosis.issue_tags
      },
      risk_signal: diagnosis.risk_signal,
      report_outputs: ["markdown", "json-style"]
    };
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function listHtml(items, className) {
    return `<ul class="${className}">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  }

  function tagsHtml(items) {
    return `<div class="tag-row">${items.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}</div>`;
  }

  function render(diagnosis) {
    latestDiagnosis = diagnosis;
    latestMarkdown = markdownReport(diagnosis);
    latestJson = JSON.stringify(
      {
        ...diagnosis,
        structured_diagnosis_preview: structuredPreview(diagnosis)
      },
      null,
      2
    );

    riskBadge.className = `risk-badge risk-${diagnosis.risk_signal}`;
    riskBadge.textContent = diagnosis.risk_signal;

    resultOutput.innerHTML = [
      `<section class="result-block"><h4>Dispute summary</h4><p>${escapeHtml(diagnosis.dispute_summary)}</p></section>`,
      `<section class="result-block"><h4>Detected contract/dispute type</h4>${tagsHtml([
        diagnosis.contract_type,
        diagnosis.dispute_type,
        ...diagnosis.issue_tags
      ])}</section>`,
      `<section class="result-block"><h4>Key issues</h4>${listHtml(diagnosis.key_issues, "issue-list")}</section>`,
      `<section class="result-block"><h4>Relevant clauses or clause signals</h4>${listHtml(diagnosis.relevant_clause_signals, "issue-list")}</section>`,
      `<section class="result-block"><h4>Claimant vs respondent position matrix</h4><div class="matrix"><div><strong>Claimant</strong><p>${escapeHtml(diagnosis.position_matrix.claimant)}</p></div><div><strong>Respondent</strong><p>${escapeHtml(diagnosis.position_matrix.respondent)}</p></div></div><p><strong>Contested facts:</strong> ${escapeHtml(diagnosis.position_matrix.contested_facts.join("; "))}</p></section>`,
      `<section class="result-block"><h4>Evidence gaps</h4>${listHtml(diagnosis.evidence_gaps, "gap-list")}</section>`,
      `<section class="result-block"><h4>Risk signal</h4><p>${escapeHtml(diagnosis.risk_signal)} risk under ${escapeHtml(diagnosis.risk_mode)} mode.</p></section>`,
      `<section class="result-block"><h4>Suggested next steps</h4>${listHtml(diagnosis.suggested_next_steps, "next-step-list")}</section>`,
      `<section class="result-block"><h4>Structured diagnosis preview</h4><pre class="preview-code"><code>${escapeHtml(JSON.stringify(structuredPreview(diagnosis), null, 2))}</code></pre></section>`,
      `<section class="result-block"><h4>Markdown-style report preview</h4><pre class="preview-code"><code>${escapeHtml(latestMarkdown)}</code></pre></section>`,
      `<section class="result-block"><h4>JSON-style output preview</h4><pre class="preview-code"><code>${escapeHtml(latestJson)}</code></pre></section>`
    ].join("");
  }

  function clearResult() {
    latestDiagnosis = null;
    latestMarkdown = "";
    latestJson = "";
    riskBadge.className = "risk-badge risk-unclear";
    riskBadge.textContent = "Unclear";
    resultOutput.innerHTML =
      '<div class="empty-state"><strong>Load a sample or enter a dispute, then run Analyze.</strong><p>The result panel will show a summary, issue tags, clause signals, evidence gaps, risk, next steps, Markdown, and JSON.</p></div>';
  }

  async function copyText(kind) {
    const value = kind === "json" ? latestJson : latestMarkdown;
    if (!value) {
      copyStatus.textContent = "Run a diagnosis before copying.";
      return;
    }

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value);
      } else {
        const helper = document.createElement("textarea");
        helper.value = value;
        helper.setAttribute("readonly", "");
        helper.style.position = "fixed";
        helper.style.left = "-9999px";
        document.body.appendChild(helper);
        helper.select();
        document.execCommand("copy");
        helper.remove();
      }
      copyStatus.textContent = `Copied ${kind.toUpperCase()} output.`;
    } catch (error) {
      copyStatus.textContent = `Copy failed. Select the ${kind.toUpperCase()} preview manually.`;
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    copyStatus.textContent = "";
    render(diagnose(readForm()));
  });

  document.getElementById("load-sample").addEventListener("click", () => {
    loadSample(document.getElementById("sample-select").value);
    render(diagnose(readForm()));
  });

  document.querySelectorAll(".sample-chip").forEach((button) => {
    button.addEventListener("click", () => {
      loadSample(button.dataset.sample);
      render(diagnose(readForm()));
    });
  });

  document.getElementById("copy-markdown").addEventListener("click", () => copyText("markdown"));
  document.getElementById("copy-json").addEventListener("click", () => copyText("json"));
  document.getElementById("reset-form").addEventListener("click", () => {
    form.reset();
    document.querySelectorAll(".sample-chip").forEach((button) => button.classList.remove("is-active"));
    copyStatus.textContent = "Cleared inputs.";
    clearResult();
  });

  loadSample("service-payment");
  render(diagnose(readForm()));
})();
