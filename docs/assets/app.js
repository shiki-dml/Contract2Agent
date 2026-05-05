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
    liability: ["damages", "liability", "indemnity", "penalty", "limitation", "cap"],
    "force majeure": ["force majeure", "impossibility", "uncontrollable"],
    confidentiality: ["confidential", "nda", "disclosure"],
    service: ["uptime", "sla", "suspension", "access", "service", "service credit"],
    evidence: ["email", "invoice", "receipt", "log", "message", "signed", "proof"]
  };

  const forceMajeureFactTriggers = [
    "force majeure notice",
    "invokes force majeure",
    "invoked force majeure",
    "claims force majeure",
    "claimed force majeure",
    "force majeure event",
    "force majeure prevented",
    "excused by force majeure",
    "government order",
    "government action",
    "natural disaster",
    "port closure",
    "emergency closure",
    "extraordinary external event",
    "pandemic",
    "war",
    "strike",
    "impossibility",
    "external disruption",
    "uncontrollable event",
    "third-party outage",
    "third party outage",
    "performance excused",
    "prevented performance"
  ];

  const issueFamilyRegistry = {
    payment: {
      active_triggers: [
        "unpaid invoice",
        "unpaid invoices",
        "overdue invoice",
        "overdue invoices",
        "non-payment",
        "nonpayment",
        "failed to pay",
        "outstanding invoice",
        "outstanding invoices",
        "payment default",
        "undisputed amount",
        "undisputed invoices",
        "fees were due"
      ],
      clause_triggers: ["must pay", "payment due", "pay undisputed", "invoice"],
      negative_triggers: [
        "no unpaid invoice",
        "no unpaid invoices",
        "no overdue invoice",
        "no overdue invoices",
        "no payment dispute",
        "no party claims unpaid invoices"
      ],
      blocker_terms: ["unpaid invoice", "unpaid invoices", "overdue invoice", "overdue invoices", "non-payment", "nonpayment", "payment", "invoice", "invoices"]
    },
    invoice_dispute: {
      active_triggers: [
        "invoice dispute notice",
        "written invoice dispute",
        "disputed invoice",
        "disputed invoices",
        "disputed amount",
        "dispute the invoice",
        "disputes an invoice",
        "invoice was disputed",
        "invoices were disputed",
        "charge dispute",
        "billing dispute",
        "payment demand",
        "failure to pay invoice",
        "invoice rejection"
      ],
      clause_triggers: ["disputes an invoice", "disputed amount", "basis for dispute"],
      negative_triggers: [
        "no invoice dispute",
        "not an invoice dispute",
        "no disputed invoice",
        "no disputed invoices",
        "no unpaid invoice",
        "no billing dispute"
      ],
      blocker_terms: ["invoice dispute", "disputed invoice", "disputed invoices", "charge dispute", "invoice", "invoices"]
    },
    refund: {
      active_triggers: [
        "refund demand",
        "requests a refund",
        "request a refund",
        "requested refund",
        "seeks a refund",
        "refund after",
        "prepaid fee refund",
        "prepaid fees refund",
        "pro-rata refund",
        "pro rata refund",
        "overpayment",
        "cancellation refund",
        "return of fees",
        "non-refundable fee provision disputed",
        "non-refundable fee language",
        "refundable pro rata"
      ],
      clause_triggers: ["refund", "non-refundable", "pro-rata refund", "return of fees"],
      negative_triggers: [
        "no refund",
        "no refunds",
        "not seeking refund",
        "no party claims refunds",
        "no party seeks refunds"
      ],
      blocker_terms: ["refund", "refunds", "refundable", "non-refundable", "return of fees", "overpayment"]
    },
    lease_maintenance: {
      active_triggers: [
        "landlord maintenance obligation",
        "landlord failed to perform a maintenance obligation",
        "roof repair",
        "roof repairs",
        "roof leak",
        "exterior wall repair",
        "hvac repair",
        "plumbing repair",
        "water intrusion",
        "leak",
        "building condition",
        "repairs not begun",
        "repairs delayed",
        "begin commercially reasonable repairs",
        "commercially reasonable roof repairs",
        "materially interferes with the tenant's use",
        "material interference with premises"
      ],
      clause_triggers: ["landlord to maintain", "landlord must maintain", "building roof", "exterior walls", "hvac", "plumbing", "commercially reasonable repairs"],
      negative_triggers: ["no lease maintenance dispute", "no repair dispute", "no water intrusion", "no roof leak"],
      blocker_terms: ["lease maintenance", "maintenance obligation", "roof repair", "roof leak", "water intrusion", "commercially reasonable repairs"]
    },
    rent_abatement: {
      active_triggers: [
        "rent abatement",
        "abatement demand",
        "demanded rent abatement",
        "affected period",
        "affected area",
        "unusable area",
        "part of the showroom was unusable",
        "partial use loss",
        "materially interferes with the tenant's use",
        "material interference with use"
      ],
      clause_triggers: ["rent abatement", "affected period", "affected area", "materially interferes"],
      negative_triggers: ["no rent abatement", "no abatement demand"],
      blocker_terms: ["rent abatement", "abatement", "affected area", "affected period", "unusable"]
    },
    rent_withholding: {
      active_triggers: [
        "withheld rent",
        "withheld 40%",
        "rent withholding",
        "withholding rent",
        "partial rent payment",
        "unauthorized withholding",
        "payment default",
        "rent ledger",
        "failure to pay rent"
      ],
      clause_triggers: ["may not withhold rent", "unauthorized withholding", "payment default", "rent ledger"],
      negative_triggers: ["no rent withholding", "no payment default"],
      blocker_terms: ["rent withholding", "withheld rent", "withholding rent", "payment default", "rent ledger"]
    },
    security_deposit: {
      active_triggers: [
        "security deposit",
        "deposit deduction",
        "deposit deductions",
        "itemized deposit statement",
        "move-out inspection",
        "deposit return",
        "return of the security deposit",
        "repair deductions",
        "ordinary wear and tear"
      ],
      clause_triggers: ["security deposit", "itemized deposit statement", "ordinary wear and tear", "deduct from the security deposit"],
      negative_triggers: ["no security deposit dispute", "no deposit deduction"],
      blocker_terms: ["security deposit", "deposit deduction", "deposit statement", "ordinary wear and tear"]
    },
    tenant_damage: {
      active_triggers: [
        "tenant-caused damage",
        "tenant caused damage",
        "damage beyond ordinary wear and tear",
        "beyond ordinary wear and tear",
        "roof leak caused damage",
        "caused by the roof leak",
        "tenant misuse",
        "repair invoice",
        "repainting",
        "flooring damage",
        "flooring repair invoice",
        "move-out photos",
        "move-out inspection",
        "causation dispute"
      ],
      clause_triggers: ["tenant-caused damage", "tenant caused damage", "tenant misuse", "ordinary wear and tear"],
      negative_triggers: ["no tenant-caused damage", "no tenant caused damage", "no property damage"],
      blocker_terms: ["tenant-caused damage", "tenant caused damage", "property damage", "tenant misuse", "ordinary wear and tear", "flooring", "repainting"]
    },
    force_majeure: {
      active_triggers: forceMajeureFactTriggers,
      clause_triggers: ["force majeure", "government order", "natural disaster", "port closure", "strike", "war", "emergency closure", "extraordinary external event", "external uncontrollable event"],
      negative_triggers: [
        "no force majeure",
        "no force majeure notice",
        "no government order",
        "no natural disaster",
        "no port closure",
        "no strike",
        "no war",
        "no emergency closure",
        "no extraordinary external event",
        "no external uncontrollable event",
        "no external event",
        "no party invokes force majeure",
        "no party claims force majeure",
        "no party claims government order",
        "no party claims natural disaster",
        "force majeure appears only",
        "internal staffing shortage only",
        "ordinary vendor backlog only",
        "ordinary raw-material backlog only",
        "ordinary raw material backlog only"
      ],
      blocker_terms: ["force majeure", "government order", "natural disaster", "port closure", "strike", "war", "emergency closure", "extraordinary external event", "external uncontrollable event", "external event"]
    },
    confidentiality: {
      active_triggers: [
        "confidentiality breach",
        "breach of confidentiality",
        "unauthorized disclosure",
        "public disclosure",
        "public link",
        "public workspace",
        "workspace exposure",
        "publicly accessible",
        "confidential marked",
        "marked \"confidential\"",
        "marked confidential",
        "customer list",
        "pricing model",
        "launch plan",
        "technical docs exposed",
        "technical documentation exposed",
        "anonymous page views",
        "suspected compromise",
        "nda breach"
      ],
      clause_triggers: ["confidential", "non-disclosure", "nondisclosure", "unauthorized disclosure"],
      negative_triggers: [
        "no confidentiality dispute",
        "no confidentiality breach",
        "no confidential information",
        "no confidential information disclosure",
        "no unauthorized disclosure",
        "no public disclosure",
        "not a confidentiality dispute"
      ],
      blocker_terms: ["confidentiality", "confidential information", "disclosure", "public link", "workspace exposure", "nda"]
    },
    indemnity: {
      active_triggers: [
        "third-party claim",
        "third party claim",
        "third-party demand",
        "third party demand",
        "demand letter",
        "indemnity notice",
        "indemnity demand",
        "indemnification demand",
        "defense demand",
        "demand for defense",
        "hold harmless demand",
        "infringement allegation",
        "infringement claim",
        "infringement demand",
        "copyright claim",
        "copyright demand",
        "patent claim",
        "trademark claim",
        "claim tender"
      ],
      clause_triggers: ["indemnity", "indemnify", "defend", "hold harmless"],
      negative_triggers: [
        "no indemnity",
        "not seeking indemnity",
        "no indemnification",
        "no third-party",
        "no third party",
        "no third-party claim",
        "no third party claim",
        "no defense tender",
        "no indemnity tender",
        "no ip",
        "no intellectual property",
        "no infringement",
        "no defense demand",
        "no hold harmless"
      ],
      blocker_terms: ["indemnity", "indemnification", "third-party", "third party", "ip", "intellectual property", "infringement", "copyright", "patent", "trademark", "defense", "hold harmless"]
    },
    delivery: {
      active_triggers: [
        "delivery deadline",
        "delivery milestone",
        "deliver by",
        "must deliver",
        "late delivery",
        "missed deadline",
        "missed the",
        "missed milestone",
        "partial delivery",
        "partial data import",
        "revised package",
        "acceptance criteria",
        "formal acceptance",
        "rejection",
        "rejected",
        "delivery defects",
        "mapping defects",
        "blocked launch",
        "migration deadline",
        "migration milestone"
      ],
      clause_triggers: ["delivery", "milestone", "acceptance", "rejection"],
      negative_triggers: [
        "no delayed delivery",
        "no late delivery",
        "no party claims delayed delivery",
        "no delivery dispute"
      ],
      blocker_terms: ["delayed delivery", "late delivery", "delivery", "deadline", "milestone", "acceptance", "rejection"]
    },
    sla: {
      active_triggers: [
        "sla",
        "uptime",
        "downtime",
        "service availability",
        "service credit",
        "service credits",
        "outage",
        "uptime report",
        "monitoring data",
        "customer-side integration errors",
        "customer side integration errors"
      ],
      clause_triggers: ["sla", "uptime", "service credit", "availability"],
      negative_triggers: [
        "no sla downtime",
        "no service credits",
        "no party claims sla downtime",
        "no party claims service credits"
      ],
      blocker_terms: ["sla", "uptime", "downtime", "service credit", "service credits", "outage"]
    },
    suspension: {
      active_triggers: [
        "suspended access",
        "suspend access",
        "access suspension",
        "suspension log",
        "access disabled",
        "platform access terminated",
        "service access blocked",
        "restoration of access",
        "restore access"
      ],
      clause_triggers: ["suspend", "suspension", "affected services"],
      negative_triggers: ["no suspension", "no party claims suspension", "no suspended access"],
      blocker_terms: ["suspension", "suspended", "suspend", "access disabled", "service access blocked"]
    },
    liquidated_damages: {
      active_triggers: ["seeks liquidated damages", "seek liquidated damages", "liquidated damages claim", "liquidated damages calculation", "disputes liquidated damages", "dispute liquidated damages", "liquidated damages cap", "penalty", "per-week damages", "per week", "ld cap", "unexcused delay damages"],
      clause_triggers: ["liquidated damages", "penalty"],
      negative_triggers: ["no liquidated damages", "no penalties", "no party claims liquidated damages"],
      blocker_terms: ["liquidated damages", "penalty", "penalties", "ld cap"]
    },
    liability_limitation: {
      active_triggers: [
        "liability cap",
        "limitation of liability",
        "damages exclusion",
        "consequential damages",
        "lost revenue exclusion",
        "lost profit exclusion",
        "lost-profit exclusion",
        "requested damages may exceed cap",
        "argues cap applies",
        "cap limits recovery",
        "disputed recovery",
        "carve-out dispute"
      ],
      clause_triggers: ["liability cap", "limitation of liability", "damages exclusion", "consequential damages", "lost-profit"],
      negative_triggers: ["no liability cap dispute", "no limitation of liability dispute", "no damages cap dispute"],
      blocker_terms: ["liability cap", "limitation of liability", "damages cap", "damages exclusion", "cap limits recovery"]
    },
    cover_costs: {
      active_triggers: ["substitute goods", "temporary consultant", "alternate provider", "cover purchase", "replacement supplier", "documented cover costs", "cover cost", "cover costs"],
      clause_triggers: ["cover costs", "temporary consultant", "alternate staffing"],
      negative_triggers: ["no cover costs", "no temporary consultant", "no substitute goods"],
      blocker_terms: ["cover costs", "cover cost", "temporary consultant", "substitute goods", "alternate provider", "replacement supplier"]
    }
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
  let latestTestCase = "";

  const form = document.getElementById("diagnosis-form");
  const resultOutput = document.getElementById("result-output");
  const evaluationOutput = document.getElementById("evaluation-output");
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

  function collectInput() {
    return readForm();
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

  function registryEntry(family) {
    return issueFamilyRegistry[family] || {
      active_triggers: [],
      clause_triggers: [],
      negative_triggers: [],
      blocker_terms: []
    };
  }

  function familyBlockerTerms(family) {
    const entry = registryEntry(family);
    return uniqueValues(
      (entry.blocker_terms || [])
        .concat(entry.active_triggers || [])
        .concat(entry.clause_triggers || [])
    );
  }

  function segmentBlocksFamily(segment, family) {
    const lower = normalize(segment);
    const entry = registryEntry(family);
    const familyTerms = familyBlockerTerms(family);
    const genericDenial = hasAny(lower, [
      "no party claims",
      "no party seeks",
      "no party invokes",
      "neither party claims",
      "neither party seeks",
      "neither party invokes",
      "there is no",
      "there are no",
      "not seeking",
      "does not seek",
      "does not invoke",
      "not invoked",
      "not a"
    ]);
    return (
      hasAny(lower, entry.negative_triggers || []) ||
      (genericDenial && hasAny(lower, familyTerms))
    );
  }

  function hasIssueFactTrigger(data, family, extraTriggers) {
    const triggers = (extraTriggers || []).concat(registryEntry(family).active_triggers || []);
    return splitSegments(activeTriggerText(data)).some((segment) => {
      if (segmentBlocksFamily(segment, family)) {
        return false;
      }
      return hasAny(segment, triggers);
    });
  }

  function familyBlocked(data, family, positiveTrigger) {
    if (positiveTrigger) {
      return false;
    }
    return hasFamilyBlocker(data, family);
  }

  function hasFamilyBlocker(data, family) {
    return splitSegments(activeTriggerText(data)).some((segment) => segmentBlocksFamily(segment, family));
  }

  function shouldActivateIssueFamily(data, family, clauseSignals, activeTrigger, clausePhrases, options) {
    const config = options || {};
    if (family === "force_majeure" && hasFamilyBlocker(data, family)) {
      return false;
    }
    if (!activeTrigger || familyBlocked(data, family, activeTrigger)) {
      return false;
    }
    if (config.requireClause === false) {
      return true;
    }
    const requiredSignals = clausePhrases || registryEntry(family).clause_triggers || [];
    return requiredSignals.some((signal) => hasSignal(clauseSignals, signal));
  }

  function countGroup(text, group) {
    return keywordGroups[group].reduce(
      (count, word) => count + (normalize(text).includes(word) ? 1 : 0),
      0
    );
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

  function dateRegex() {
    return /\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?\b/gi;
  }

  function monthRegex() {
    return /\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b/gi;
  }

  function durationRegex() {
    return /\b\d+\s*-\s*business\s*-\s*days?\b|\b\d+\s*-\s*(?:business\s+)?days?\b|\b\d+\s+(?:business\s+)?days?\b|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+(?:business\s+)?days?\b|\b\d+\s+weeks?\b/gi;
  }

  function monthDurationRegex() {
    return /\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+months?\b/gi;
  }

  function collectCaseText(data, names) {
    return names.map((name) => data[name] || "").join(" ");
  }

  function factText(data) {
    return collectCaseText(data, [
      "disputeType",
      "desiredOutcome",
      "disputeDescription",
      "claimantPosition",
      "respondentPosition",
      "evidence",
      "metadata"
    ]);
  }

  function activeTriggerText(data) {
    return collectCaseText(data, [
      "desiredOutcome",
      "disputeDescription",
      "claimantPosition",
      "respondentPosition",
      "evidence",
      "metadata"
    ]);
  }

  function allText(data) {
    return collectCaseText(data, [
      "contractType",
      "disputeType",
      "desiredOutcome",
      "contractText",
      "disputeDescription",
      "claimantPosition",
      "respondentPosition",
      "evidence",
      "metadata"
    ]);
  }

  function splitSegments(text) {
    return String(text || "")
      .replace(/\r/g, "\n")
      .split(/[.!?\n]+/)
      .map((segment) => segment.trim())
      .filter(Boolean);
  }

  function addUnique(items, value) {
    const cleaned = String(value || "").trim().replace(/\s+/g, " ");
    if (!cleaned) {
      return;
    }
    if (!items.some((item) => normalize(item) === normalize(cleaned))) {
      items.push(cleaned);
    }
  }

  function uniqueValues(items) {
    const result = [];
    items.forEach((item) => addUnique(result, item));
    return result;
  }

  function hasSignal(signals, phrase) {
    return signals.some((signal) => normalize(signal).includes(normalize(phrase)));
  }

  function hasTag(tags, tag) {
    return tags.some((item) => normalize(item) === normalize(tag));
  }

  function hasLeaseActiveIssue(tags) {
    return [
      "lease maintenance",
      "repair obligation",
      "rent abatement",
      "rent withholding",
      "payment default",
      "security deposit",
      "tenant-caused damage",
      "property damage causation"
    ].some((tag) => hasTag(tags, tag));
  }

  function extractDates(text) {
    const matches = String(text || "").match(dateRegex());
    return matches ? uniqueValues(matches.map((match) => match.trim())) : [];
  }

  function extractDurations(text) {
    const matches = String(text || "").match(durationRegex());
    return matches ? uniqueValues(matches.map(cleanDuration)) : [];
  }

  function cleanDuration(value) {
    const cleaned = String(value || "").trim().replace(/\s*-\s*/g, "-").replace(/\s+/g, " ");
    return cleaned.replace(/^five business days$/i, "5-business-day");
  }

  function findSegmentsNear(text, words) {
    return splitSegments(text).filter((segment) => hasAny(segment, words));
  }

  function findDatesNear(text, words) {
    return uniqueValues(
      findSegmentsNear(text, words).flatMap((segment) => extractDates(segment))
    );
  }

  function findDurationNear(text, words) {
    const durations = uniqueValues(
      findSegmentsNear(text, words).flatMap((segment) => extractDurations(segment))
    );
    return durations[0] || "";
  }

  function findDateInSegment(text, words, pick, excludeWords) {
    const segments = findSegmentsNear(text, words).filter((segment) => !hasAny(segment, excludeWords || []));
    for (let index = 0; index < segments.length; index += 1) {
      const dates = extractDates(segments[index]);
      if (dates.length) {
        return pick === "last" ? dates[dates.length - 1] : dates[0];
      }
    }
    return "";
  }

  function findPercentNear(text, words) {
    const segments = findSegmentsNear(text, words);
    for (let index = 0; index < segments.length; index += 1) {
      const match = segments[index].match(/\b\d+(?:\.\d+)?%/);
      if (match) {
        return match[0];
      }
    }
    return "";
  }

  function findDateAfterWords(text, words) {
    const segments = findSegmentsNear(text, words);
    for (let index = 0; index < segments.length; index += 1) {
      const segment = segments[index];
      const lower = normalize(segment);
      let start = -1;
      words.forEach((word) => {
        const found = lower.indexOf(normalize(word));
        if (found !== -1 && (start === -1 || found < start)) {
          start = found;
        }
      });
      const dates = extractDates(start === -1 ? segment : segment.slice(start));
      if (dates.length) {
        return dates[0];
      }
    }
    return "";
  }

  function extractMoneyAmounts(text) {
    const matches = String(text || "").match(/\$\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?|\$\s*\d+(?:\.\d+)?/g);
    return matches ? uniqueValues(matches.map((match) => match.replace(/\$\s+/, "$").trim())) : [];
  }

  function findMoneyNear(text, words, pick) {
    const segments = findSegmentsNear(text, words);
    for (let index = 0; index < segments.length; index += 1) {
      const amounts = extractMoneyAmounts(segments[index]);
      if (amounts.length) {
        return pick === "last" ? amounts[amounts.length - 1] : amounts[0];
      }
    }
    return "";
  }

  function extractPercents(text) {
    const matches = String(text || "").match(/\b\d+(?:\.\d+)?%/g);
    return matches ? uniqueValues(matches) : [];
  }

  function findSegmentNear(text, words) {
    return findSegmentsNear(text, words)[0] || "";
  }

  function formatList(items) {
    const values = uniqueValues(items);
    if (values.length <= 1) {
      return values[0] || "";
    }
    if (values.length === 2) {
      return `${values[0]} and ${values[1]}`;
    }
    return `${values.slice(0, -1).join(", ")}, and ${values[values.length - 1]}`;
  }

  function extractInvoiceDates(data) {
    const source = collectCaseText(data, [
      "disputeDescription",
      "claimantPosition",
      "respondentPosition",
      "evidence",
      "metadata"
    ]);
    const direct = [];
    const pattern = /\binvoices?\s+(?:dated|date|dates|of|from)\s+([^.;\n]+)/gi;
    let match = pattern.exec(source);
    while (match) {
      extractDates(match[1]).forEach((date) => addUnique(direct, date));
      match = pattern.exec(source);
    }
    if (direct.length) {
      return direct;
    }
    splitSegments(source).forEach((segment) => {
      const lower = normalize(segment);
      if (lower.includes("invoice") && !hasAny(segment, ["notice", "suspend", "termination", "terminated"])) {
        extractDates(segment).forEach((date) => addUnique(direct, date));
      }
    });
    return direct;
  }

  function extractNoticeDates(data) {
    const source = collectCaseText(data, [
      "disputeDescription",
      "claimantPosition",
      "respondentPosition",
      "evidence",
      "metadata"
    ]);
    return findDatesNear(source, ["notice", "non-payment", "nonpayment", "breach notice", "reminder email"]);
  }

  function extractActionDates(data) {
    const source = collectCaseText(data, [
      "disputeDescription",
      "claimantPosition",
      "respondentPosition",
      "evidence",
      "metadata"
    ]);
    const direct = [];
    const dateSource = String(source || "");
    const actionDatePatterns = [
      /\b(?:suspended|suspend|terminated|terminate|cancelled|canceled)[^.;\n]*?\bon\s+(\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?\b)/gi,
      /\b(?:suspension|termination|access suspension log|termination notice)[^.;\n]*?\bdated\s+(\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?\b)/gi
    ];
    actionDatePatterns.forEach((pattern) => {
      let match = pattern.exec(dateSource);
      while (match) {
        addUnique(direct, match[1]);
        match = pattern.exec(dateSource);
      }
    });
    if (direct.length) {
      return direct;
    }
    return findDatesNear(source, ["suspend", "suspension", "terminated", "termination", "cancelled", "canceled"]);
  }

  function extractServicePeriods(data) {
    const source = collectCaseText(data, [
      "disputeDescription",
      "claimantPosition",
      "respondentPosition",
      "evidence",
      "metadata"
    ]);
    const periods = [];
    findSegmentsNear(source, ["downtime", "uptime", "sla", "service"]).forEach((segment) => {
      const months = segment.match(monthRegex()) || [];
      months.forEach((month) => addUnique(periods, month));
    });
    return periods;
  }

  function extractLiabilityCapPeriod(contractText) {
    const matches = String(contractText || "").match(monthDurationRegex());
    return matches ? cleanDuration(matches[0]) : "";
  }

  function durationAdjective(duration) {
    return String(duration || "").trim().replace(/\s+months?\b/i, "-month").replace(/\s+days?\b/i, "-day");
  }

  function durationSentence(duration) {
    return String(duration || "")
      .trim()
      .replace(/\b(\d+)-business-day\b/i, "$1 business days")
      .replace(/\b(\d+)-day\b/i, "$1 days");
  }

  function durationRequirementLabel(duration) {
    return durationSentence(duration)
      .replace(/\b(\d+)\s+business\s+days\b/i, "$1-business-day")
      .replace(/\b(\d+)\s+days\b/i, "$1-day");
  }

  function extractDeliveryTimeline(data) {
    const facts = factText(data);
    const source = allText(data);
    return {
      milestoneDate: findDateInSegment(source, ["production-ready", "production ready", "delivery milestone", "migration milestone", "migration deadline", "must deliver", "deliver by", "delivery by"], "first"),
      actualDeliveryDate: findDateInSegment(facts, ["delivered", "delivery occurred", "late delivery", "arrived", "shipment arrived"], "last", ["notice", "revised", "rejection", "rejected"]),
      noticeDate: findDateInSegment(facts, ["delivery delay notice", "delay notice"], "first") || findDatesNear(facts, ["notice"])[0] || "",
      revisedPackageDate: findDateInSegment(facts, ["revised package", "revised delivery", "corrected package", "cure package", "updated package", "revised"], "first"),
      rejectionDate: findDateInSegment(facts, ["rejection", "rejected", "reject"], "last"),
      reviewPeriod: findDurationNear(source, ["review period", "business-day review", "business day review", "inspect", "inspection", "acceptance review", "review"]),
      curePeriod: findDurationNear(source, ["cure"]),
      liquidatedDamagesPercent: findPercentNear(source, ["liquidated damages", "damages cap", "10%", "cap"]),
      liabilityCapPeriod: extractLiabilityCapPeriod(data.contractText),
      hasApiMappingDefects: hasAny(source, ["api mapping", "api mappings", "mapping defect", "mapping defects", "api defect", "api defects"]),
      hasLiquidatedDamages: hasAny(source, ["liquidated damages"]),
      hasLostRevenueExclusion: hasAny(data.contractText, ["lost revenue", "lost revenues", "lost-revenue", "lost-profit", "lost profit", "consequential"]),
      hasNoticeContacts: hasAny(data.contractText, ["notice contacts", "contractual notice contacts", "notice address", "notices must be sent"])
    };
  }

  function extractLiquidatedDamagesTerms(data) {
    const source = allText(data);
    const index = normalize(source).indexOf("liquidated damages");
    const segment = index === -1 ? "" : source.slice(index, index + 260);
    const percents = extractPercents(segment);
    const unit = hasAny(segment, ["full week", "weekly", "per week"]) ? "per full week" : "";
    return {
      rate: percents[0] || "",
      cap: percents.length > 1 ? percents[percents.length - 1] : findPercentNear(data.contractText, ["capped", "cap"]),
      unit
    };
  }

  function extractForceMajeureTimeline(data) {
    const facts = factText(data);
    const source = allText(data);
    return {
      governmentOrderDate: findDateInSegment(facts, ["government emergency order", "government order", "emergency order", "government closure", "emergency closure"], "first"),
      awarenessDate: findDateInSegment(facts, ["became aware", "awareness", "internal awareness", "internal email", "impact email", "migration impact"], "first"),
      forceMajeureNoticeDate: findDateInSegment(facts, ["force majeure notice"], "first"),
      migrationDeadline: findDateInSegment(source, ["migration milestone", "migration deadline", "migration by", "must complete", "completion deadline", "deadline"], "first"),
      consultantDate: findDateInSegment(facts, ["temporary consultant", "consultant retained", "retained", "cover cost", "cover costs"], "first"),
      partialCompletionDate: findDateInSegment(facts, ["partial completion", "partially completed", "partial migration"], "first"),
      finalCompletionDate: findDateInSegment(facts, ["final completion", "finally completed", "completed on", "completion on"], "last")
    };
  }

  function extractRefundTerminationTimeline(data) {
    const facts = factText(data);
    const source = allText(data);
    return {
      prepaidPaymentDate: findDateInSegment(facts, ["paid", "prepaid implementation fee", "prepaid fee", "payment receipt"], "first"),
      dataImportMilestoneDate: findDateAfterWords(source, ["data import milestone", "data import"]),
      trainingMilestoneDate: findDateAfterWords(source, ["administrator training milestone", "admin training milestone", "administrator training", "training milestone"]),
      partialDeliveryDate: findDateInSegment(facts, ["partial data import", "partial delivery", "delivery package", "provider partial delivery"], "first", ["rejected", "rejection", "breach notice", "notice"]),
      breachNoticeDate: findDateInSegment(facts, ["breach notice", "notice of breach"], "first"),
      providerResponseDate: findDateInSegment(facts, ["provider response", "provider responded", "responded", "response"], "first"),
      terminationDate: findDateInSegment(facts, ["termination", "terminated", "terminate"], "last"),
      curePeriod: findDurationNear(source, ["cure period", "cure"]),
      rejectionPeriod: findDurationNear(source, ["rejection period", "business-day rejection", "reject", "rejection", "acceptance"]),
      prepaidAmount: findMoneyNear(source, ["prepaid implementation fee", "prepaid fee", "paid"], "first"),
      refundAmount: findMoneyNear(facts, ["refund calculation", "pro-rata refund", "pro rata refund", "refund"], "last")
    };
  }

  function extractConfidentialityIndemnityTimeline(data) {
    const facts = factText(data);
    const source = allText(data);
    return {
      disclosureDate:
        findDateInSegment(facts, ["uploaded", "public project-management workspace", "public workspace", "workspace exposure", "public link", "disclosure"], "first") ||
        findDateInSegment(source, ["workspace upload log", "upload log"], "first"),
      customerDiscoveryDate:
        findDateInSegment(facts, ["customer discovered", "discovered the public link", "discovered", "captured"], "first"),
      removalDate:
        findDateInSegment(facts, ["removed the file", "removed", "removal confirmation", "containment", "remediation"], "first"),
      thirdPartyClaimDate:
        findDateInSegment(facts, ["demand letter", "third-party ip demand", "third party ip demand", "third-party claim", "third party claim", "copyright", "infringement"], "first"),
      indemnityNoticeDate:
        findDateInSegment(facts, ["indemnity notice", "indemnification notice", "claim tender"], "first"),
      unauthorizedDisclosureNoticePeriod:
        findDurationNear(data.contractText, ["unauthorized disclosure", "suspected compromise", "after discovering", "notify the customer"]),
      indemnityNoticePeriod:
        findDurationNear(data.contractText, ["indemnifiable claim", "receiving the claim", "indemnity notice", "written notice"])
    };
  }

  function extractLeaseRentPeriod(text) {
    const segments = findSegmentsNear(text, ["withheld", "rent withholding", "rent ledger", "withholding"]).concat(
      findSegmentsNear(text, ["rent"])
    );
    for (let index = 0; index < segments.length; index += 1) {
      const segment = segments[index];
      const rentMatch = segment.match(/\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+rent\b/i);
      if (rentMatch) {
        const month = rentMatch[0].split(/\s+/)[0];
        return `${month.charAt(0).toUpperCase()}${month.slice(1).toLowerCase()} rent`;
      }
      const monthMatch = segment.match(/\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b/i);
      if (monthMatch && hasAny(segment, ["withheld", "withholding", "rent ledger"])) {
        return `${monthMatch[0].charAt(0).toUpperCase()}${monthMatch[0].slice(1).toLowerCase()} rent`;
      }
    }
    return "";
  }

  function extractLeaseAbatementPeriod(text) {
    const match = String(text || "").match(
      /\brent abatement\s+for\s+(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2})\s+(?:through|to|-)\s+(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2})/i
    );
    return {
      start: match ? match[1].replace(/\b\w/g, (char) => char.toUpperCase()) : "",
      end: match ? match[2].replace(/\b\w/g, (char) => char.toUpperCase()) : ""
    };
  }

  function extractLeaseTimeline(data) {
    const facts = factText(data);
    const source = allText(data);
    const contractText = data.contractText || "";
    const rentPeriod = extractLeaseRentPeriod(facts);
    return {
      waterIntrusionDate: findDateInSegment(facts, ["discovered water intrusion", "water intrusion", "roof leak", "leak after heavy rain"], "first"),
      tenantNoticeDate:
        findDateInSegment(facts, ["sent an email", "email to the landlord", "reporting water intrusion", "tenant sent", "repair notice", "maintenance notice", "tenant notice"], "first") ||
        findDateInSegment(facts, ["notice"], "first"),
      landlordResponseDate: findDateInSegment(facts, ["landlord responded", "said it would inspect", "response email"], "first"),
      contractorInspectionDate: findDateInSegment(facts, ["roof contractor inspected", "contractor inspected", "inspection report", "contractor inspection"], "first"),
      rentWithholdingPeriod: rentPeriod,
      rentWithholdingPercent: findPercentNear(facts, ["withheld", "rent withholding", "rent ledger"]),
      repairCompletionDate: findDateInSegment(facts, ["completed roof repairs", "roof repairs completed", "repairs completed", "completed"], "last"),
      moveOutDate: findDateInSegment(facts, ["move-out inspection", "move-out", "move out", "surrender", "at move-out"], "first"),
      repairCurePeriod: findDurationNear(contractText, ["begin commercially reasonable repairs", "maintenance obligation", "repair", "cure period"]),
      depositStatementPeriod: findDurationNear(contractText, ["itemized deposit statement", "after surrender", "deposit statement"]),
      abatementPeriod: extractLeaseAbatementPeriod(source),
      depositDeduction: findMoneyNear(facts, ["security deposit", "deducted", "deduction"], "first"),
      liabilityCapPeriod: extractLiabilityCapPeriod(contractText),
      deemedReceiptRule: hasAny(contractText, ["two business days after mailing", "next business day after email", "whichever occurs later"])
    };
  }

  function extractConfidentialMaterials(data) {
    const source = factText(data);
    const materials = [];
    [
      "product launch plan",
      "pricing model",
      "customer list",
      "customer lists",
      "technical documentation",
      "technical docs",
      "business plans",
      "launch schedules"
    ].forEach((material) => {
      if (hasAny(source, [material])) {
        addUnique(materials, material);
      }
    });
    return materials;
  }

  function partyName(data, preferred, fallback) {
    const combined = normalize(allText(data));
    if (combined.includes(preferred)) {
      return preferred;
    }
    if (preferred === "provider" && combined.includes("seller")) {
      return "seller";
    }
    if (preferred === "provider" && combined.includes("contractor")) {
      return "contractor";
    }
    if (preferred === "customer" && combined.includes("client")) {
      return "client";
    }
    if (preferred === "customer" && combined.includes("buyer")) {
      return "buyer";
    }
    return fallback;
  }

  function hasForceMajeureFactTrigger(data) {
    const facts = activeTriggerText(data);
    const longTriggers = forceMajeureFactTriggers
      .filter((trigger) => !["war", "strike"].includes(trigger))
      .concat([
        "external uncontrollable event",
        "export restriction",
        "port closure"
      ]);
    return splitSegments(facts).some((segment) => {
      if (segmentBlocksFamily(segment, "force_majeure")) {
        return false;
      }
      return hasAny(segment, longTriggers) || /\b(?:war|strike)\b/i.test(segment);
    });
  }

  function hasConfidentialityClause(contractText) {
    const text = normalize(contractText);
    return (
      text.includes("confidential") ||
      text.includes("non-disclosure") ||
      text.includes("nondisclosure") ||
      text.includes("disclosure of confidential") ||
      /\bnda\b/i.test(text)
    );
  }

  function hasInvoiceDisputeFactTrigger(data) {
    return hasIssueFactTrigger(data, "invoice_dispute", [
      "overage fees disputed",
      "invoice nonpayment",
      "invoice non-payment",
      "non-payment of invoice",
      "nonpayment of invoice"
    ]);
  }

  function hasPaymentFactTrigger(data) {
    return hasIssueFactTrigger(data, "payment");
  }

  function hasRefundFactTrigger(data) {
    return hasIssueFactTrigger(data, "refund");
  }

  function hasDeliveryFactTrigger(data) {
    return hasIssueFactTrigger(data, "delivery");
  }

  function hasSlaFactTrigger(data) {
    return hasIssueFactTrigger(data, "sla");
  }

  function hasSuspensionFactTrigger(data) {
    return hasIssueFactTrigger(data, "suspension");
  }

  function hasIndemnityFactTrigger(data) {
    return hasIssueFactTrigger(data, "indemnity", [
      "ip infringement",
      "intellectual property infringement",
      "third-party ip demand",
      "third party ip demand"
    ]);
  }

  function hasConfidentialityFactTrigger(data) {
    return hasIssueFactTrigger(data, "confidentiality", [
      "disclosed confidential",
      "misuse of confidential",
      "data leak",
      "data leakage",
      "leaked confidential",
      "access logs",
      "anonymous views"
    ]);
  }

  function hasUnauthorizedDisclosureFactTrigger(data) {
    return hasIssueFactTrigger(data, "confidentiality", [
      "unauthorized disclosure",
      "public disclosure",
      "public link",
      "public workspace",
      "public project-management workspace",
      "workspace exposure",
      "publicly accessible",
      "without authentication",
      "anonymous page views",
      "suspected compromise"
    ]);
  }

  function hasThirdPartyIpFactTrigger(data) {
    return hasIssueFactTrigger(data, "indemnity", [
      "third-party ip demand",
      "third party ip demand",
      "third-party ip claim",
      "third party ip claim",
      "intellectual property",
      "copyright",
      "patent",
      "trademark"
    ]);
  }

  function hasLeaseMaintenanceFactTrigger(data) {
    const contractSupport = hasAny(data.contractText, [
      "landlord to maintain",
      "landlord must maintain",
      "landlord failed to perform a maintenance obligation",
      "building roof",
      "exterior walls",
      "hvac main units",
      "common plumbing systems",
      "commercially reasonable repairs"
    ]);
    const factSupport = hasIssueFactTrigger(data, "lease_maintenance");
    return factSupport && (contractSupport || hasAny(factText(data), ["landlord", "lease", "tenant"]));
  }

  function hasRentAbatementFactTrigger(data) {
    return hasIssueFactTrigger(data, "rent_abatement");
  }

  function hasRentWithholdingFactTrigger(data) {
    return hasIssueFactTrigger(data, "rent_withholding");
  }

  function hasSecurityDepositFactTrigger(data) {
    return hasIssueFactTrigger(data, "security_deposit");
  }

  function hasTenantDamageFactTrigger(data) {
    return hasIssueFactTrigger(data, "tenant_damage");
  }

  function hasPropertyDamageCausationFactTrigger(data) {
    const facts = factText(data);
    return hasTenantDamageFactTrigger(data) && hasAny(facts, [
      "caused by the roof leak",
      "not tenant misuse",
      "tenant misuse",
      "caused by roof leak",
      "damage was caused",
      "causation dispute",
      "flooring and repainting damage"
    ]);
  }

  function hasLiabilityCapCarveoutClause(contractText) {
    const text = normalize(contractText);
    return (
      hasAny(text, ["cap does not limit", "liability cap does not limit", "does not limit claims", "does not limit breach of confidentiality", "does not limit indemnity"]) ||
      (hasAny(text, ["does not limit", "not limit"]) && hasAny(text, ["confidentiality", "indemnity", "willful misconduct", "ip claims"])) ||
      (hasAny(text, ["except for", "carve-out", "carve out"]) && hasAny(text, ["unpaid rent", "intentional misconduct", "tenant-caused property damage", "tenant caused property damage"]))
    );
  }

  function extractFactualTriggers(data) {
    const facts = activeTriggerText(data);
    const lowerFacts = normalize(facts);
    const dispute = normalize(data.disputeType);
    const contract = normalize(data.contractType);
    const paymentFact = hasPaymentFactTrigger(data);
    const invoiceDisputeFact = hasInvoiceDisputeFactTrigger(data);
    const refundFact = hasRefundFactTrigger(data);
    const deliveryFact = hasDeliveryFactTrigger(data);
    const slaFact = hasSlaFactTrigger(data);
    const suspensionFact = hasSuspensionFactTrigger(data);
    const indemnityFact = hasIndemnityFactTrigger(data);
    const confidentialityFact = hasConfidentialityFactTrigger(data);
    const unauthorizedDisclosureFact = hasUnauthorizedDisclosureFactTrigger(data);
    const thirdPartyIpFact = hasThirdPartyIpFactTrigger(data);
    const forceMajeureFact = hasForceMajeureFactTrigger(data);
    const leaseMaintenanceFact = hasLeaseMaintenanceFactTrigger(data);
    const rentAbatementFact = hasRentAbatementFactTrigger(data);
    const rentWithholdingFact = hasRentWithholdingFactTrigger(data);
    const securityDepositFact = hasSecurityDepositFactTrigger(data);
    const tenantDamageFact = hasTenantDamageFactTrigger(data);
    const propertyDamageCausationFact = hasPropertyDamageCausationFactTrigger(data);
    const liquidatedDamagesFact = hasIssueFactTrigger(data, "liquidated_damages");
    const coverCostsFact = hasIssueFactTrigger(data, "cover_costs");
    const liabilityLimitationActiveFact = hasIssueFactTrigger(data, "liability_limitation");
    const nonDesiredFacts = collectCaseText(data, [
      "disputeDescription",
      "claimantPosition",
      "respondentPosition",
      "evidence",
      "metadata"
    ]);
    const damagesFact = splitSegments(facts).some((segment) => {
      if (segmentBlocksFamily(segment, "payment") || segmentBlocksFamily(segment, "refund")) {
        return hasAny(segment, ["damages", "remediation costs", "investigation costs", "defense costs", "business-impact damages"]);
      }
      return hasAny(segment, [
        "damages",
        "liquidated damages",
        "lost revenue",
        "lost productivity",
        "internal delay costs",
        "lost profits",
        "operational losses",
        "replacement costs",
        "remediation costs",
        "investigation costs",
        "defense costs",
        "business-impact damages",
        "recoverable damages",
        "loss calculation",
        "claimed revenue",
        "refund calculation",
        "display-fixture damages",
        "damaged display fixtures",
        "display fixtures",
        "security deposit deduction",
        "deposit deduction",
        "repair costs",
        "repair deductions"
      ]);
    });
    const liabilityLimitationFact =
      liabilityLimitationActiveFact ||
      hasAny(facts, [
        "twelve-month fee cap",
        "six-month fee cap",
        "three-month fee cap",
        "fee cap",
        "damages beyond",
        "fees paid"
      ]);

    return {
      payment:
        paymentFact ||
        (dispute.includes("payment") && !familyBlocked(data, "payment", paymentFact)),
      invoiceDispute: invoiceDisputeFact,
      notice:
        hasAny(facts, ["written notice", "non-payment notice", "nonpayment notice", "notice of breach", "breach notice", "notice of non-payment", "delivery delay notice", "delay notice", "force majeure notice", "indemnity notice", "unauthorized-disclosure notice", "unauthorized disclosure notice", "reminder email", "notice was vague", "notice was sent", "notice contacts", "notice address", "lease notice", "proper lease notice", "tenant notice", "email notice", "certified mail", "failed to notify", "notify the customer"]),
      cure:
        hasAny(facts, ["cure period", "failed to cure", "failure to cure", "waited", "days before suspension", "days before termination"]),
      suspension: suspensionFact,
      termination:
        dispute.includes("termination") || hasAny(nonDesiredFacts, ["terminate", "termination", "terminated", "cancelled", "canceled"]),
      delivery:
        deliveryFact ||
        (dispute.includes("delivery") && !familyBlocked(data, "delivery", deliveryFact)),
      refund:
        refundFact ||
        (dispute.includes("refund") && !familyBlocked(data, "refund", refundFact)),
      prepaidFees:
        refundFact && hasAny(facts, ["prepaid fee", "prepaid fees", "prepaid implementation fee", "implementation fee", "payment receipt"]),
      acceptanceRejection:
        deliveryFact && hasAny(facts, ["acceptance", "formal acceptance", "milestone acceptance", "accepted", "rejected", "rejection", "5-business-day rejection", "reasonable specificity"]),
      milestonePerformance:
        deliveryFact && hasAny(facts, ["milestone", "data import", "administrator training", "admin training", "onboarding services", "partial delivery", "partial data import"]),
      service:
        contract.includes("saas") || hasAny(facts, ["platform access", "service access", "uptime", "downtime", "sla", "service credit", "support ticket", "user seats", "hosted software"]),
      sla: slaFact,
      serviceCredit:
        slaFact && hasIssueFactTrigger(data, "sla", ["service credit", "service credits", "sla credits", "credit remedy", "credit amount"]),
      customerSideCause:
        slaFact && hasAny(facts, ["customer-side", "customer side", "integration error", "api authentication", "customer systems", "customer's own integration"]),
      mitigation:
        forceMajeureFact && hasAny(facts, ["mitigation", "mitigate", "commercially reasonable mitigation", "remote migration", "remote tools", "alternate staffing", "alternate site access"]),
      coverCosts: coverCostsFact,
      damages: damagesFact || liquidatedDamagesFact,
      liabilityLimitation:
        liabilityLimitationFact ||
        (damagesFact && hasAny(data.contractText, ["liability cap", "total liability", "capped at", "damages exclusion", "consequential", "lost-profit", "lost profit"])),
      indemnity: indemnityFact,
      thirdPartyIp: thirdPartyIpFact,
      confidentiality: confidentialityFact,
      unauthorizedDisclosure: unauthorizedDisclosureFact,
      liabilityCapCarveout:
        hasLiabilityCapCarveoutClause(data.contractText) &&
        (confidentialityFact || unauthorizedDisclosureFact || indemnityFact || thirdPartyIpFact),
      leaseMaintenance: leaseMaintenanceFact,
      repairObligation: leaseMaintenanceFact,
      rentAbatement: rentAbatementFact,
      rentWithholding: rentWithholdingFact,
      paymentDefault:
        rentWithholdingFact &&
        hasAny(data.contractText, ["unauthorized withholding is a payment default", "unauthorized withholding", "payment default"]),
      securityDeposit: securityDepositFact,
      tenantCausedDamage: tenantDamageFact,
      propertyDamageCausation: propertyDamageCausationFact,
      penalty: liquidatedDamagesFact,
      forceMajeure: forceMajeureFact,
      contested:
        hasAny(lowerFacts, ["argues", "claims", "says", "disputed", "never", "caused by", "premature", "too aggressively"]) &&
        Boolean(data.claimantPosition || data.respondentPosition)
    };
  }

  function buildClauseSignals(data) {
    const contractText = normalize(data.contractText);
    const signals = [];

    if (hasAny(contractText, ["must pay", "payment due", "pay all", "pay undisputed", "invoice", "invoices", "subscription fees within", "fees within"])) {
      addUnique(signals, "payment timing");
    }
    if (hasAny(contractText, ["disputes an invoice", "disputed invoice", "disputed amount", "basis for dispute", "undisputed invoices"])) {
      addUnique(signals, "disputed invoice procedure");
    }
    if (hasAny(contractText, ["notice contacts", "contractual notice contacts"])) {
      addUnique(signals, "contractual notice contacts");
    }
    if (hasAny(contractText, ["notice address", "order form", "notices must be sent", "sent by email"])) {
      addUnique(signals, "notice address");
    }
    if (hasAny(contractText, ["deemed received", "deemed receipt", "next business day", "next-business-day"])) {
      addUnique(signals, "deemed receipt rule");
    }
    if (hasAny(contractText, ["cure period", "days to cure", "cure"])) {
      addUnique(signals, "cure period");
      const curePeriod = findDurationNear(data.contractText, ["cure period", "days to cure", "cure"]);
      if (curePeriod) {
        addUnique(signals, `${curePeriod} cure period`);
      }
    }
    if (hasAny(contractText, ["landlord to maintain", "landlord must maintain", "requires the landlord to maintain", "building roof", "exterior walls", "hvac main units", "common plumbing systems"])) {
      addUnique(signals, "landlord maintenance obligation");
    }
    if (hasAny(contractText, ["tenant must maintain", "tenant is responsible", "damage caused by the tenant", "tenant-caused damage", "tenant caused damage", "tenant's employees", "tenant misuse"])) {
      addUnique(signals, "tenant maintenance responsibility");
      addUnique(signals, "tenant-caused damage");
    }
    if (hasAny(contractText, ["written notice describing the condition", "written notice", "requested repair"])) {
      addUnique(signals, "written notice requirement");
    }
    if (hasAny(contractText, ["certified mail"])) {
      addUnique(signals, "certified mail requirement");
    }
    if (hasAny(contractText, ["sent by email", "email transmission", "email and certified mail"])) {
      addUnique(signals, "email notice requirement");
    }
    if (hasAny(contractText, ["lease schedule", "notice addresses listed in the lease schedule"])) {
      addUnique(signals, "lease schedule notice addresses");
    }
    if (hasAny(contractText, ["begin commercially reasonable repairs", "commercially reasonable repairs"])) {
      const repairCure = findDurationNear(data.contractText, ["begin commercially reasonable repairs", "maintenance obligation", "repair"]);
      if (repairCure) {
        addUnique(signals, `${durationRequirementLabel(repairCure)} repair cure period`);
      }
      addUnique(signals, "commercially reasonable repairs");
    }
    if (hasAny(contractText, ["rent abatement", "affected period", "affected area", "materially interferes"])) {
      addUnique(signals, "rent abatement for affected period and affected area");
    }
    if (hasAny(contractText, ["may not withhold rent", "unauthorized withholding", "payment default"])) {
      addUnique(signals, "unauthorized rent withholding as payment default");
    }
    if (hasAny(contractText, ["security deposit", "deposit statement", "deduct from the security deposit"])) {
      addUnique(signals, "security deposit deductions");
      const depositStatement = findDurationNear(data.contractText, ["itemized deposit statement", "after surrender", "deposit statement"]);
      if (depositStatement) {
        addUnique(signals, `itemized deposit statement within ${durationSentence(depositStatement)}`);
      }
    }
    if (hasAny(contractText, ["ordinary wear and tear"])) {
      addUnique(signals, "ordinary wear and tear limitation");
    }
    if (hasAny(contractText, ["suspend", "suspension", "suspend access", "affected services"])) {
      addUnique(signals, "suspension rights");
    }
    if (hasAny(contractText, ["sla", "service credit", "service credits", "exclusive remedy"])) {
      addUnique(signals, "SLA/service credit");
    }
    if (hasAny(contractText, ["uptime", "availability"])) {
      addUnique(signals, "uptime obligation");
    }
    if (hasAny(contractText, ["customer-side", "customer side", "customer systems", "integration errors"])) {
      addUnique(signals, "customer-side systems exclusion");
    }
    if (hasAny(contractText, ["consequential", "indirect", "incidental"])) {
      addUnique(signals, "consequential damages exclusion");
    }
    if (hasAny(contractText, ["lost-profit", "lost profit", "lost profits"])) {
      addUnique(signals, "lost-profit damages exclusion");
    }
    if (hasAny(contractText, ["lost revenue", "lost revenues", "lost-revenue"])) {
      addUnique(signals, "lost revenue exclusion");
    }
    if (hasAny(contractText, ["liquidated damages"])) {
      addUnique(signals, "liquidated damages");
      const ldTerms = extractLiquidatedDamagesTerms(data);
      if (ldTerms.rate || ldTerms.cap) {
        addUnique(
          signals,
          `liquidated damages formula${ldTerms.rate ? ` at ${ldTerms.rate}${ldTerms.unit ? ` ${ldTerms.unit}` : ""}` : ""}${ldTerms.cap ? ` capped at ${ldTerms.cap}` : ""}`
        );
      }
    }
    if (hasAny(contractText, ["liability cap", "total liability", "capped at", "fees paid"])) {
      addUnique(signals, "liability cap");
      const capPeriod = extractLiabilityCapPeriod(data.contractText);
      if (capPeriod) {
        addUnique(
          signals,
          hasAny(contractText, ["base rent"])
            ? `${capPeriod} of base rent liability cap`
            : `${durationAdjective(capPeriod)} fee liability cap`
        );
      }
    }
    if (hasLiabilityCapCarveoutClause(data.contractText)) {
      addUnique(signals, "liability cap carve-outs");
      if (hasAny(contractText, ["unpaid rent"])) {
        addUnique(signals, "unpaid rent carve-out");
      }
      if (hasAny(contractText, ["intentional misconduct"])) {
        addUnique(signals, "intentional misconduct carve-out");
      }
      if (hasAny(contractText, ["tenant-caused property damage", "tenant caused property damage"])) {
        addUnique(signals, "tenant-caused property damage carve-out");
      }
      if (hasAny(contractText, ["confidentiality", "breach of confidentiality"])) {
        addUnique(signals, "confidentiality carve-out");
      }
      if (hasAny(contractText, ["indemnity", "indemnity obligations", "indemnification"])) {
        addUnique(signals, "indemnity carve-out");
      }
    }
    if (hasAny(contractText, ["indemnity", "indemnify"])) {
      addUnique(
        signals,
        hasIndemnityFactTrigger(data)
          ? "indemnity clause"
          : "indemnity clause mentioned but not fact-triggered"
      );
      if (hasAny(contractText, ["third-party claims", "third party claims", "third-party claim", "intellectual property", "infringe", "infringement", "copyright", "patent", "trademark"])) {
        addUnique(signals, "third-party IP claim indemnity");
      }
      const indemnityNotice = findDurationNear(data.contractText, ["indemnifiable claim", "receiving the claim", "indemnity notice", "written notice"]);
      if (indemnityNotice) {
        addUnique(signals, `${durationRequirementLabel(indemnityNotice)} indemnity notice requirement`);
      }
      if (hasAny(contractText, ["control the defense", "control defense", "settle", "settlement", "written consent", "admits customer fault", "non-monetary obligations"])) {
        addUnique(signals, "defense control / settlement consent");
      }
    }
    if (hasAny(contractText, ["force majeure"])) {
      addUnique(
        signals,
        hasForceMajeureFactTrigger(data)
          ? "force majeure clause"
          : "force majeure clause mentioned but not fact-triggered"
      );
    }
    if (hasAny(contractText, ["government order", "government orders", "emergency closure", "emergency closures", "natural disaster", "strike", "war"])) {
      addUnique(signals, "government orders / emergency closures");
    }
    if (hasAny(contractText, ["commercially reasonable mitigation", "commercially reasonable efforts", "mitigation", "mitigate"])) {
      addUnique(signals, "commercially reasonable mitigation");
    }
    if (hasAny(contractText, ["temporary migration support", "temporary consultant", "cover cost", "cover costs", "alternate staffing"])) {
      addUnique(signals, "temporary migration support / cover costs");
    }
    if (hasAny(contractText, ["migration milestone", "migration deadline", "migration by", "june 30"])) {
      const fmTimeline = extractForceMajeureTimeline(data);
      addUnique(signals, fmTimeline.migrationDeadline ? `${fmTimeline.migrationDeadline} migration milestone` : "migration milestone");
    }
    if (hasAny(contractText, ["time is of the essence"])) {
      addUnique(signals, "time is of the essence");
    }
    if (hasAny(contractText, ["business-day force majeure notice", "business day force majeure notice", "force majeure notice", "days after becoming aware", "days of becoming aware"])) {
      const noticeRequirement = findDurationNear(data.contractText, ["force majeure notice", "becoming aware", "aware"]);
      addUnique(signals, noticeRequirement ? `${noticeRequirement} force majeure notice requirement` : "force majeure notice requirement");
    }
    if (hasAny(contractText, ["review period", "business-day review", "business day review", "inspect", "inspection"])) {
      addUnique(signals, "review/inspection period");
    }
    if (hasAny(contractText, ["prepaid implementation fee", "prepaid fee", "prepaid fees"])) {
      addUnique(signals, "prepaid implementation fee");
    }
    if (hasAny(contractText, ["non-refundable", "non refundable", "nonrefundable"])) {
      addUnique(signals, "non-refundable fee provision");
    }
    if (hasAny(contractText, ["pro-rata refund", "pro rata refund", "refundable pro rata", "refund after uncured breach", "uncured breach"])) {
      addUnique(signals, "pro-rata refund after uncured breach");
    }
    if (hasAny(contractText, ["written breach notice", "notice of breach", "breach notice"])) {
      addUnique(signals, "written breach notice");
    }
    if (hasAny(contractText, ["milestone acceptance", "formal milestone acceptance", "formal acceptance"])) {
      addUnique(signals, "milestone acceptance");
    }
    if (hasAny(contractText, ["business-day rejection", "business day rejection", "rejection period", "reject within"])) {
      const rejectionPeriod = findDurationNear(data.contractText, ["business-day rejection", "business day rejection", "rejection period", "reject", "rejection"]);
      addUnique(signals, rejectionPeriod ? `${rejectionPeriod} rejection period` : "rejection period");
    }
    if (hasAny(contractText, ["reasonable specificity", "reasonably specific", "specificity for defect", "material defects"])) {
      addUnique(signals, "reasonable specificity for defect rejection");
    }
    if (hasAny(contractText, ["acceptance", "specification"])) {
      addUnique(signals, "delivery and acceptance criteria");
    } else if (hasAny(contractText, ["delivery", "shipment", "milestone"])) {
      addUnique(signals, "delivery milestone");
    }
    if (hasAny(contractText, ["terminate", "termination", "cancel", "cancellation"])) {
      addUnique(signals, "termination rights");
    }
    if (hasConfidentialityClause(contractText)) {
      addUnique(signals, "confidentiality obligations");
      if (hasAny(contractText, ["unauthorized disclosure", "suspected compromise", "notify the customer", "after discovering"])) {
        addUnique(signals, "unauthorized-disclosure notice requirement");
        const disclosureNotice = findDurationNear(data.contractText, ["unauthorized disclosure", "suspected compromise", "after discovering", "notify the customer"]);
        if (disclosureNotice) {
          addUnique(signals, `${durationRequirementLabel(disclosureNotice)} unauthorized-disclosure notice requirement`);
        }
      }
    }
    if (hasAny(contractText, ["refund", "non-refundable", "refundable"])) {
      addUnique(signals, "refund conditions");
    }

    return signals.length ? signals : ["No strong clause signal detected yet"];
  }

  function deriveActiveIssueTags(data, clauseSignals, triggers) {
    const tags = [];
    const activate = (family, activeTrigger, clausePhrases, options) =>
      shouldActivateIssueFamily(data, family, clauseSignals, activeTrigger, clausePhrases, options);

    if (activate("payment", triggers.payment, ["payment", "invoice"])) {
      addUnique(tags, "payment");
    }
    if (activate("invoice_dispute", triggers.invoiceDispute, ["disputed invoice", "payment", "invoice"])) {
      addUnique(tags, "invoice dispute");
    }
    if (activate("refund", triggers.refund, ["refund", "prepaid", "non-refundable"])) {
      addUnique(tags, "refund");
    }
    if (activate("refund", triggers.prepaidFees, ["prepaid", "non-refundable", "refund"])) {
      addUnique(tags, "prepaid fees");
    }
    if (activate("notice", triggers.notice || triggers.suspension || triggers.termination, ["notice", "deemed receipt"], { requireClause: false })) {
      addUnique(tags, "notice");
    }
    if (activate("cure", triggers.cure || triggers.suspension || triggers.termination || (triggers.delivery && triggers.notice), ["cure"])) {
      addUnique(tags, "cure period");
    }
    if (activate("lease_maintenance", triggers.leaseMaintenance, ["landlord maintenance"])) {
      addUnique(tags, "lease maintenance");
    }
    if (activate("lease_maintenance", triggers.repairObligation, ["commercially reasonable repairs", "repair cure period"])) {
      addUnique(tags, "repair obligation");
    }
    if (activate("rent_abatement", triggers.rentAbatement, ["rent abatement"])) {
      addUnique(tags, "rent abatement");
    }
    if (activate("rent_withholding", triggers.rentWithholding, ["rent withholding"])) {
      addUnique(tags, "rent withholding");
    }
    if (activate("rent_withholding", triggers.paymentDefault, ["payment default"])) {
      addUnique(tags, "payment default");
    }
    if (activate("security_deposit", triggers.securityDeposit, ["security deposit"])) {
      addUnique(tags, "security deposit");
    }
    if (activate("tenant_damage", triggers.tenantCausedDamage, ["tenant-caused damage"])) {
      addUnique(tags, "tenant-caused damage");
    }
    if (activate("tenant_damage", triggers.propertyDamageCausation, ["tenant-caused damage", "ordinary wear"])) {
      addUnique(tags, "property damage causation");
    }
    if (activate("suspension", triggers.suspension, ["suspension"])) {
      addUnique(tags, "suspension");
    }
    if (activate("termination", triggers.termination, ["termination"], { requireClause: false })) {
      addUnique(tags, "termination");
    }
    if (activate("delivery", triggers.delivery, ["delivery", "milestone", "acceptance"], { requireClause: false })) {
      addUnique(tags, "delivery");
    }
    if (activate("delivery", triggers.acceptanceRejection, ["acceptance", "rejection", "specificity"])) {
      addUnique(tags, "acceptance / rejection");
    }
    if (activate("sla", triggers.sla, ["SLA", "uptime"])) {
      addUnique(tags, "SLA");
    }
    if (activate("sla", triggers.serviceCredit, ["service credit"])) {
      addUnique(tags, "service credit");
    }
    if (activate("force_majeure", triggers.mitigation, ["mitigation"])) {
      addUnique(tags, "mitigation");
    }
    if (activate("cover_costs", triggers.coverCosts, ["cover costs"])) {
      addUnique(tags, "cover costs");
    }
    if (activate("damages", triggers.damages || triggers.refund || triggers.penalty, [], { requireClause: false })) {
      addUnique(tags, "damages");
    }
    if (activate("liability_limitation", triggers.damages || triggers.liabilityLimitation, ["liability cap", "damages exclusion", "lost-profit", "consequential"])) {
      addUnique(tags, "liability limitation");
    }
    if (activate("indemnity", triggers.indemnity, ["indemnity"])) {
      addUnique(tags, "indemnity");
    }
    if (activate("indemnity", triggers.thirdPartyIp, ["third-party IP", "intellectual property", "indemnity"])) {
      addUnique(tags, "third-party IP claim");
    }
    if (activate("liquidated_damages", triggers.penalty, ["liquidated damages", "penalty"])) {
      addUnique(tags, "liquidated damages");
    }
    if (activate("force_majeure", triggers.forceMajeure, ["force majeure"])) {
      addUnique(tags, "force majeure");
    }
    if (activate("confidentiality", triggers.confidentiality, ["confidentiality", "confidential"])) {
      addUnique(tags, "confidentiality");
    }
    if (activate("confidentiality", triggers.unauthorizedDisclosure, ["confidentiality", "confidential"])) {
      addUnique(tags, "unauthorized disclosure");
    }
    if (activate("liability_limitation", triggers.liabilityCapCarveout, ["carve-out"])) {
      addUnique(tags, "liability cap carve-out");
    }

    return tags.length ? tags : ["unclear"];
  }

  function limitStepsForDepth(data, steps) {
    return data.diagnosisDepth === "Quick" ? steps.slice(0, 6) : steps;
  }

  function extractExplicitEvidenceGaps(evidenceText) {
    const gaps = [];
    const lines = String(evidenceText || "").split(/\r?\n/);
    let inMissingBlock = false;

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return;
      }
      const lower = normalize(trimmed);
      if (/^available\b/.test(lower)) {
        inMissingBlock = false;
      }
      if (lower.includes("missing or unclear") || lower.includes("missing/unclear")) {
        inMissingBlock = true;
        const after = trimmed.replace(/^.*missing(?:\s+or\s+unclear|\/unclear)\s*:?\s*/i, "");
        if (after && normalize(after) !== lower) {
          addUnique(gaps, cleanEvidenceGap(after));
        }
        return;
      }
      if (inMissingBlock || /\b(missing|unclear|not found|still being collected|incomplete|if any)\b/i.test(trimmed)) {
        addUnique(gaps, cleanEvidenceGap(trimmed));
      }
    });

    return gaps;
  }

  function cleanEvidenceGap(text) {
    return String(text || "")
      .replace(/^[*-]\s*/, "")
      .replace(/^missing\s+/i, "")
      .replace(/\.$/, "")
      .trim();
  }

  function hasGap(gaps, words) {
    return gaps.some((gap) => hasAny(gap, words));
  }

  function buildEvidenceGaps(data, activeIssueTags, clauseSignals, triggers) {
    const combined = normalize(allText(data));
    const evidence = normalize(data.evidence);
    const gaps = extractExplicitEvidenceGaps(data.evidence);
    const refundTimeline = extractRefundTerminationTimeline(data);
    const confidentialityTimeline = extractConfidentialityIndemnityTimeline(data);
    const refundAcceptanceIssue =
      hasTag(activeIssueTags, "refund") ||
      hasTag(activeIssueTags, "prepaid fees") ||
      hasTag(activeIssueTags, "acceptance / rejection");
    const confidentialityIpIssue =
      hasTag(activeIssueTags, "confidentiality") ||
      hasTag(activeIssueTags, "unauthorized disclosure") ||
      hasTag(activeIssueTags, "indemnity") ||
      hasTag(activeIssueTags, "third-party IP claim");
    const leaseIssue = hasLeaseActiveIssue(activeIssueTags);

    if (leaseIssue) {
      const leaseTimeline = extractLeaseTimeline(data);
      const tenantNoticeLabel = leaseTimeline.tenantNoticeDate ? `${leaseTimeline.tenantNoticeDate} notice` : "tenant notice";
      const tenantEmailLabel = leaseTimeline.tenantNoticeDate ? `${leaseTimeline.tenantNoticeDate} email` : "tenant email notice";
      const repairCureLabel = leaseTimeline.repairCurePeriod ? durationRequirementLabel(leaseTimeline.repairCurePeriod) : "repair";
      const depositDeductionLabel = leaseTimeline.depositDeduction ? `${leaseTimeline.depositDeduction} deduction` : "security deposit deduction";
      const depositStatementPeriod = leaseTimeline.depositStatementPeriod ? durationSentence(leaseTimeline.depositStatementPeriod) : "the contractual period";

      if ((hasTag(activeIssueTags, "notice") || hasTag(activeIssueTags, "cure period")) && !hasGap(gaps, ["certified mail"])) {
        addUnique(gaps, `Proof that the ${tenantNoticeLabel} was sent by certified mail`);
      }
      if ((hasTag(activeIssueTags, "notice") || hasTag(activeIssueTags, "cure period")) && !hasGap(gaps, ["lease schedule notice", "exact lease schedule"])) {
        addUnique(gaps, `Whether the ${tenantEmailLabel} was sent to the exact lease schedule notice email address`);
      }
      if (hasTag(activeIssueTags, "rent abatement") && !hasGap(gaps, ["materially interfered", "material interference"])) {
        addUnique(gaps, "Whether the roof leak materially interfered with the tenant's use of the premises");
      }
      if (hasTag(activeIssueTags, "rent abatement") && !hasGap(gaps, ["square footage", "affected area", "affected showroom"])) {
        addUnique(gaps, "Affected square footage or affected showroom area");
      }
      if (hasTag(activeIssueTags, "cure period") && !hasGap(gaps, ["cure calculation", "cure deadline", "deemed receipt"])) {
        addUnique(gaps, `${repairCureLabel} cure deadline calculation from valid or deemed receipt`);
      }
      if (hasTag(activeIssueTags, "repair obligation") && !hasGap(gaps, ["began commercially reasonable repairs", "repair timing", "within 10 business days"])) {
        addUnique(gaps, "Whether the landlord began commercially reasonable repairs within 10 business days after valid receipt");
      }
      if ((hasTag(activeIssueTags, "tenant-caused damage") || hasTag(activeIssueTags, "property damage causation")) && !hasGap(gaps, ["roof leak or tenant misuse", "caused by roof leak", "tenant misuse"])) {
        addUnique(gaps, "Whether the flooring and repainting damage was caused by roof leak or tenant misuse");
      }
      if (hasTag(activeIssueTags, "security deposit") && !hasGap(gaps, ["ordinary wear and tear", "beyond ordinary wear"])) {
        addUnique(gaps, `Whether the ${depositDeductionLabel} was limited to damage beyond ordinary wear and tear`);
      }
      if (hasTag(activeIssueTags, "rent abatement") && !hasGap(gaps, ["rent abatement", "affected period"])) {
        addUnique(gaps, "Calculation of rent abatement for the affected area and affected period");
      }
      if (hasTag(activeIssueTags, "damages") && !hasGap(gaps, ["display-fixture", "display fixture"])) {
        addUnique(gaps, "Evidence supporting display-fixture damages");
      }
      if (hasTag(activeIssueTags, "security deposit") && !hasGap(gaps, ["itemized deposit statement timing", "statement timing", "within 30 days"])) {
        addUnique(gaps, `Proof of itemized deposit statement timing within ${depositStatementPeriod} after surrender`);
      }
      return gaps.length ? uniqueValues(gaps) : ["No obvious evidence gap detected from the current text"];
    }

    if (!hasAny(combined, ["signed", "executed", "agreement", "purchase order", "order form"])) {
      addUnique(gaps, "signed agreement or executed contract copy");
    }
    if (hasTag(activeIssueTags, "payment") && !extractInvoiceDates(data).length) {
      addUnique(gaps, "invoice dates or payment due-date timeline");
    }
    if (hasTag(activeIssueTags, "payment") && hasAny(data.contractText, ["receipt", "receiving the invoice"]) && !hasAny(evidence, ["invoice receipt", "receipt date", "received on"])) {
      addUnique(gaps, "invoice receipt dates");
    }
    if (hasTag(activeIssueTags, "invoice dispute") && !hasAny(evidence, ["written invoice dispute", "dispute notice", "customer's written invoice dispute", "customer written invoice dispute"])) {
      addUnique(gaps, "customer written invoice dispute notice");
    }
    if ((hasTag(activeIssueTags, "notice") || hasTag(activeIssueTags, "cure period") || hasTag(activeIssueTags, "suspension") || hasTag(activeIssueTags, "termination")) && !hasGap(gaps, ["notice address", "notice contacts"]) && hasSignal(clauseSignals, "notice address") && !hasAny(evidence, ["notice address listed", "order form notice", "contractual notice address verified", "sow notice contacts", "statement of work listing", "project notice contacts", "notice contact list"])) {
      addUnique(gaps, "contractual notice address");
    }
    if ((hasTag(activeIssueTags, "notice") || hasTag(activeIssueTags, "cure period") || hasTag(activeIssueTags, "suspension") || hasTag(activeIssueTags, "termination")) && !hasGap(gaps, ["proof", "delivery"]) && !hasAny(evidence, ["proof of delivery", "delivery receipt", "sent to the contractual notice address", "email delivery log"])) {
      addUnique(gaps, "proof of notice delivery");
    }
    if (hasTag(activeIssueTags, "cure period") && !hasAny(combined, ["cure deadline", "cure expired", "deemed received"])) {
      addUnique(gaps, "clear cure deadline");
    }
    if (hasTag(activeIssueTags, "payment") && !hasAny(combined, ["payment due", "due date", "within 30 days", "within 15 days", "within 10 days"])) {
      addUnique(gaps, "clear payment due date");
    }
    if (hasTag(activeIssueTags, "SLA") && !hasAny(evidence, ["independent monitoring", "timestamped sla", "timestamped monitoring", "third-party monitoring"])) {
      addUnique(gaps, "independent or timestamped SLA monitoring data");
    }
    if (confidentialityIpIssue) {
      if (!hasGap(gaps, ["first discovered", "actual discovery", "discovered the public workspace exposure"])) {
        addUnique(gaps, "Exact date when the provider first discovered the public workspace exposure");
      }
      if (hasAny(combined, ["anonymous page views", "anonymous views"]) && !hasGap(gaps, ["anonymous page views", "third-party access", "internal testing"])) {
        addUnique(gaps, "Whether anonymous page views reflect actual third-party access or internal testing");
      }
      if (hasAny(combined, ["subcontractor", "subcontractors"]) && !hasGap(gaps, ["subcontractors", "confidentiality obligations"])) {
        addUnique(gaps, "Whether subcontractors were bound by confidentiality obligations at least as protective as the Agreement");
      }
      if (hasTag(activeIssueTags, "indemnity") && confidentialityTimeline.indemnityNoticeDate && !hasGap(gaps, ["indemnity notice", "contractual notice contacts"])) {
        addUnique(gaps, `Proof that the ${confidentialityTimeline.indemnityNoticeDate} indemnity notice was sent to the contractual notice contacts`);
      }
      if (hasTag(activeIssueTags, "third-party IP claim") && !hasGap(gaps, ["technical comparison", "copyrighted work", "third-party copyrighted work"])) {
        addUnique(gaps, "Technical comparison between the provider analytics template and the third-party copyrighted work");
      }
      if (hasTag(activeIssueTags, "third-party IP claim") && !hasGap(gaps, ["provider-owned", "customer-provided", "derived from customer-provided materials"])) {
        addUnique(gaps, "Evidence showing whether the analytics template was provider-owned or derived from customer-provided materials");
      }
      if (hasTag(activeIssueTags, "indemnity") && !hasGap(gaps, ["defense cost estimate"])) {
        addUnique(gaps, "Defense cost estimate for the third-party IP claim");
      }
      if ((hasTag(activeIssueTags, "damages") || hasTag(activeIssueTags, "liability limitation")) && !hasGap(gaps, ["remediation", "investigation", "business-impact", "damages calculation"])) {
        addUnique(gaps, "Calculation of remediation, investigation, and claimed business-impact damages");
      }
      return gaps.length ? uniqueValues(gaps) : ["No obvious evidence gap detected from the current text"];
    }
    if (refundAcceptanceIssue) {
      if (hasSignal(clauseSignals, "notice contacts") && !hasAny(evidence, ["sow notice contacts", "statement of work notice", "notice contact list"])) {
        addUnique(gaps, "Statement of work notice contact list");
      }
      if (refundTimeline.breachNoticeDate && !hasAny(evidence, ["proof", "delivery receipt", "email delivery log", "sent to the contractual notice contacts"])) {
        addUnique(gaps, `Proof that the ${refundTimeline.breachNoticeDate} breach notice was sent to the contractual notice contacts`);
      }
      if (hasSignal(clauseSignals, "milestone acceptance") && !hasAny(evidence, ["formal milestone acceptance", "requested formal acceptance", "acceptance request"])) {
        const deliveryDate = refundTimeline.partialDeliveryDate || "delivery";
        addUnique(gaps, `Whether the ${deliveryDate} delivery package requested formal milestone acceptance`);
      }
      if (hasSignal(clauseSignals, "rejection period") && !hasAny(evidence, ["rejected within", "timely rejection", "rejection email"])) {
        addUnique(gaps, "Whether the customer rejected within 5 business days");
      }
      if (hasSignal(clauseSignals, "specificity") && !hasAny(evidence, ["specificity", "material defects", "defect list", "defect detail"])) {
        addUnique(gaps, "Whether rejection identified material defects with reasonable specificity");
      }
      if (!hasAny(evidence, ["work-completion", "work completion", "performed vs unperformed", "completion records", "service records"])) {
        addUnique(gaps, "Detailed work-completion records showing performed vs unperformed services");
      }
      if (refundTimeline.refundAmount && !hasAny(evidence, ["refund calculation", "pro-rata refund calculation", "pro rata refund calculation"])) {
        addUnique(gaps, `Basis for the ${refundTimeline.refundAmount} pro-rata refund calculation`);
      }
      if (hasAny(combined, ["lost productivity", "internal delay"]) && !hasAny(evidence, ["lost productivity", "internal delay"])) {
        addUnique(gaps, "Evidence supporting lost productivity damages");
      }
    } else if ((hasTag(activeIssueTags, "damages") || hasTag(activeIssueTags, "liability limitation")) && !hasAny(evidence, ["damages calculation", "lost revenue calculation", "loss calculation", "replacement cost", "itemized refund"])) {
      addUnique(gaps, "damages calculation or lost revenue calculation");
    }
    if (triggers.customerSideCause && !hasAny(evidence, ["integration error logs", "api authentication", "customer-side logs", "customer side logs"])) {
      addUnique(gaps, "customer-side system or integration error logs");
    }

    return gaps.length ? gaps : ["No obvious evidence gap detected from the current text"];
  }

  function extractTimelineFacts(data, activeIssueTags, clauseSignals, evidenceGaps) {
    const facts = factText(data);
    const contractText = data.contractText || "";
    const invoiceDates = extractInvoiceDates(data);
    const noticeDates = extractNoticeDates(data);
    const actionDates = extractActionDates(data);
    const servicePeriods = extractServicePeriods(data);
    const deliveryTimeline = extractDeliveryTimeline(data);
    const fmTimeline = extractForceMajeureTimeline(data);
    const refundTimeline = extractRefundTerminationTimeline(data);
    const confidentialityTimeline = extractConfidentialityIndemnityTimeline(data);
    const leaseTimeline = extractLeaseTimeline(data);
    const paymentDeadline = findDurationNear(contractText, ["pay", "payment", "invoice", "fees"]);
    const disputeDeadline = findDurationNear(contractText, ["disputes an invoice", "disputed amount", "basis for dispute"]);
    const cureDuration = findDurationNear(contractText, ["cure"]);
    const timeline = [];
    const refundAcceptanceIssue =
      hasTag(activeIssueTags, "refund") ||
      hasTag(activeIssueTags, "prepaid fees") ||
      hasTag(activeIssueTags, "acceptance / rejection");
    const confidentialityIpIssue =
      hasTag(activeIssueTags, "confidentiality") ||
      hasTag(activeIssueTags, "unauthorized disclosure") ||
      hasTag(activeIssueTags, "indemnity") ||
      hasTag(activeIssueTags, "third-party IP claim");
    const leaseIssue = hasLeaseActiveIssue(activeIssueTags);

    if (leaseIssue) {
      if (leaseTimeline.waterIntrusionDate) {
        addUnique(timeline, `${leaseTimeline.waterIntrusionDate}: tenant discovered water intrusion.`);
      }
      if (leaseTimeline.tenantNoticeDate) {
        addUnique(timeline, `${leaseTimeline.tenantNoticeDate}: tenant sent email notice reporting water intrusion.`);
      }
      if (leaseTimeline.landlordResponseDate) {
        addUnique(timeline, `${leaseTimeline.landlordResponseDate}: landlord responded and said it would inspect.`);
      }
      if (leaseTimeline.contractorInspectionDate) {
        const inspectionDetail = hasAny(facts + " " + data.evidence, ["deteriorated roof flashing"])
          ? " and found deteriorated roof flashing"
          : "";
        addUnique(timeline, `${leaseTimeline.contractorInspectionDate}: roof contractor inspected${inspectionDetail}.`);
      }
      if (leaseTimeline.rentWithholdingPeriod) {
        const withheldAmount = leaseTimeline.rentWithholdingPercent ? `${leaseTimeline.rentWithholdingPercent} of` : "part of";
        addUnique(timeline, `${leaseTimeline.rentWithholdingPeriod}: tenant withheld ${withheldAmount} rent.`);
      }
      if (leaseTimeline.repairCompletionDate) {
        addUnique(timeline, `${leaseTimeline.repairCompletionDate}: landlord completed roof repairs.`);
      }
      if (leaseTimeline.moveOutDate) {
        addUnique(timeline, `${leaseTimeline.moveOutDate}: move-out inspection or surrender event.`);
      }
      if (leaseTimeline.depositStatementPeriod && leaseTimeline.moveOutDate) {
        addUnique(timeline, `${durationSentence(leaseTimeline.depositStatementPeriod)} after surrender: deadline for itemized deposit statement from ${leaseTimeline.moveOutDate}, if applicable.`);
      }
      if (leaseTimeline.repairCurePeriod) {
        addUnique(timeline, `${durationRequirementLabel(leaseTimeline.repairCurePeriod)} repair cure period: calculate from valid/deemed receipt once notice delivery method is verified.`);
      }
      if (leaseTimeline.deemedReceiptRule) {
        addUnique(timeline, "Deemed receipt rule: two business days after mailing or next business day after email transmission, whichever occurs later.");
      } else if (hasSignal(clauseSignals, "deemed receipt")) {
        addUnique(timeline, "Deemed receipt rule identified: calculate receipt under the lease notice clause.");
      }
      if (hasGap(evidenceGaps, ["certified mail", "lease schedule notice", "valid receipt", "deemed receipt", "cure deadline"])) {
        addUnique(timeline, "Repair cure deadline remains evidence-dependent until notice method, lease schedule address, and deemed receipt are verified.");
      }
      return timeline.length ? timeline : ["No dated timeline facts detected yet"];
    }

    if ((hasTag(activeIssueTags, "payment") || hasTag(activeIssueTags, "invoice dispute")) && invoiceDates.length) {
      addUnique(timeline, `Invoice dates identified: ${formatList(invoiceDates)}.`);
    }
    if ((hasTag(activeIssueTags, "payment") || hasTag(activeIssueTags, "invoice dispute")) && paymentDeadline) {
      addUnique(timeline, `Payment deadline signal: undisputed invoices due within ${paymentDeadline} of receipt or the contract trigger.`);
    }
    if (hasTag(activeIssueTags, "invoice dispute") && disputeDeadline) {
      addUnique(timeline, `Invoice dispute deadline signal: written dispute notice due within ${disputeDeadline} of invoice receipt or discovery.`);
    }
    if (confidentialityIpIssue) {
      if (confidentialityTimeline.disclosureDate) {
        addUnique(timeline, `${confidentialityTimeline.disclosureDate}: provider uploaded confidential materials to a public workspace.`);
      }
      if (confidentialityTimeline.customerDiscoveryDate) {
        addUnique(timeline, `${confidentialityTimeline.customerDiscoveryDate}: customer discovered the public link or workspace exposure.`);
      }
      if (confidentialityTimeline.removalDate) {
        addUnique(timeline, `${confidentialityTimeline.removalDate}: provider removed the file or completed initial containment.`);
      }
      if (confidentialityTimeline.thirdPartyClaimDate) {
        addUnique(timeline, `${confidentialityTimeline.thirdPartyClaimDate}: third-party IP demand letter or infringement claim.`);
      }
      if (confidentialityTimeline.indemnityNoticeDate) {
        addUnique(timeline, `${confidentialityTimeline.indemnityNoticeDate}: customer indemnity notice.`);
      }
      if (confidentialityTimeline.unauthorizedDisclosureNoticePeriod) {
        addUnique(timeline, `${durationRequirementLabel(confidentialityTimeline.unauthorizedDisclosureNoticePeriod)} unauthorized-disclosure notice period: calculate from the provider's actual discovery date once known.`);
      }
      if (confidentialityTimeline.indemnityNoticePeriod) {
        addUnique(timeline, `${durationRequirementLabel(confidentialityTimeline.indemnityNoticePeriod)} indemnity notice period: calculate from customer receipt of the third-party claim.`);
      }
    } else if (refundAcceptanceIssue) {
      if (refundTimeline.prepaidPaymentDate) {
        const amount = refundTimeline.prepaidAmount ? ` ${refundTimeline.prepaidAmount}` : "";
        addUnique(timeline, `${refundTimeline.prepaidPaymentDate}: customer paid${amount} prepaid implementation fee.`);
      }
      if (refundTimeline.dataImportMilestoneDate) {
        addUnique(timeline, `${refundTimeline.dataImportMilestoneDate}: data import milestone.`);
      }
      if (refundTimeline.trainingMilestoneDate) {
        addUnique(timeline, `${refundTimeline.trainingMilestoneDate}: administrator training milestone.`);
      }
      if (refundTimeline.partialDeliveryDate) {
        addUnique(timeline, `${refundTimeline.partialDeliveryDate}: provider partial delivery.`);
      }
      if (refundTimeline.breachNoticeDate) {
        addUnique(timeline, `${refundTimeline.breachNoticeDate}: customer breach notice.`);
      }
      if (refundTimeline.providerResponseDate) {
        addUnique(timeline, `${refundTimeline.providerResponseDate}: provider response.`);
      }
      if (refundTimeline.terminationDate) {
        addUnique(timeline, `${refundTimeline.terminationDate}: customer termination.`);
      }
      if (refundTimeline.curePeriod && refundTimeline.breachNoticeDate) {
        addUnique(timeline, `${refundTimeline.curePeriod} cure period: calculate from deemed receipt of ${refundTimeline.breachNoticeDate} notice.`);
      }
      if (refundTimeline.rejectionPeriod && refundTimeline.partialDeliveryDate) {
        addUnique(timeline, `${refundTimeline.rejectionPeriod} rejection period: calculate from ${refundTimeline.partialDeliveryDate} delivery only if acceptance was requested.`);
      }
    } else if (hasTag(activeIssueTags, "force majeure")) {
      if (fmTimeline.governmentOrderDate) {
        addUnique(timeline, `${fmTimeline.governmentOrderDate}: government emergency order issued.`);
      }
      if (fmTimeline.awarenessDate) {
        addUnique(timeline, `${fmTimeline.awarenessDate}: provider internal awareness email or migration-impact awareness.`);
      }
      if (fmTimeline.forceMajeureNoticeDate) {
        addUnique(timeline, `${fmTimeline.forceMajeureNoticeDate}: force majeure notice.`);
      }
      if (fmTimeline.migrationDeadline) {
        addUnique(timeline, `${fmTimeline.migrationDeadline}: contractual migration deadline.`);
      }
      if (fmTimeline.consultantDate) {
        addUnique(timeline, `${fmTimeline.consultantDate}: temporary consultant retained.`);
      }
      if (fmTimeline.partialCompletionDate) {
        addUnique(timeline, `${fmTimeline.partialCompletionDate}: partial completion.`);
      }
      if (fmTimeline.finalCompletionDate) {
        addUnique(timeline, `${fmTimeline.finalCompletionDate}: final completion.`);
      }
    } else if (noticeDates.length) {
      addUnique(timeline, `Notice date identified: ${formatList(noticeDates)}.`);
    }
    if (hasSignal(clauseSignals, "deemed receipt")) {
      addUnique(timeline, "Deemed receipt rule identified: notices are deemed received on the next business day.");
    }
    if (cureDuration && !confidentialityIpIssue) {
      addUnique(timeline, `Cure period length identified: ${cureDuration}.`);
    }
    if (actionDates.length && !refundAcceptanceIssue && !confidentialityIpIssue) {
      addUnique(timeline, `Suspension or termination action date identified: ${formatList(actionDates)}.`);
    }
    if (hasTag(activeIssueTags, "delivery") && !refundAcceptanceIssue) {
      if (deliveryTimeline.milestoneDate) {
        addUnique(timeline, `Delivery milestone date identified: ${deliveryTimeline.milestoneDate}.`);
      }
      if (deliveryTimeline.actualDeliveryDate) {
        addUnique(timeline, `Actual or alleged late delivery date identified: ${deliveryTimeline.actualDeliveryDate}.`);
      }
      if (deliveryTimeline.noticeDate) {
        addUnique(timeline, `Delivery delay notice date identified: ${deliveryTimeline.noticeDate}.`);
      }
      if (deliveryTimeline.revisedPackageDate) {
        addUnique(timeline, `Revised package or cure delivery date identified: ${deliveryTimeline.revisedPackageDate}.`);
      }
      if (deliveryTimeline.rejectionDate) {
        addUnique(timeline, `Rejection date identified: ${deliveryTimeline.rejectionDate}.`);
      }
      if (deliveryTimeline.reviewPeriod) {
        addUnique(timeline, `Review or inspection period identified: ${deliveryTimeline.reviewPeriod}.`);
      }
    }
    if (noticeDates.length && cureDuration && actionDates.length && !refundAcceptanceIssue && !confidentialityIpIssue) {
      addUnique(timeline, `Cure deadline must be calculated from deemed receipt of the ${noticeDates[0]} notice plus the ${cureDuration} cure period before the ${actionDates[0]} action.`);
    }
    if (servicePeriods.length && hasTag(activeIssueTags, "SLA")) {
      addUnique(timeline, `Service-performance period identified for SLA review: ${formatList(servicePeriods)}.`);
    }
    if (hasGap(evidenceGaps, ["notice address", "proof of notice", "delivery", "cure deadline"])) {
      addUnique(timeline, "Timeline verification remains evidence-dependent until notice address, delivery proof, and cure deadline evidence are matched.");
    }
    if (!timeline.length && hasDateSignal(facts + " " + contractText)) {
      extractDates(facts + " " + contractText).forEach((date) => addUnique(timeline, `Date signal requiring classification: ${date}.`));
    }

    return timeline.length ? timeline : ["No dated timeline facts detected yet"];
  }

  function buildIssues(data, activeIssueTags, clauseSignals, timelineFacts, triggers) {
    const issues = [];
    const invoiceDates = extractInvoiceDates(data);
    const invoiceLabel = invoiceDates.length ? `${formatList(invoiceDates)} invoices` : "identified invoices";
    const deliveryTimeline = extractDeliveryTimeline(data);
    const fmTimeline = extractForceMajeureTimeline(data);
    const refundTimeline = extractRefundTerminationTimeline(data);
    const confidentialityTimeline = extractConfidentialityIndemnityTimeline(data);
    const leaseTimeline = extractLeaseTimeline(data);
    const confidentialMaterials = extractConfidentialMaterials(data);
    const ldTerms = extractLiquidatedDamagesTerms(data);
    const noticeDates = extractNoticeDates(data);
    const noticeDate = deliveryTimeline.noticeDate || noticeDates[0] || "the notice";
    const actionDates = extractActionDates(data);
    const actionDate = actionDates[0] || deliveryTimeline.rejectionDate || deliveryTimeline.actualDeliveryDate || "the suspension, termination, rejection, or other action date";
    const servicePeriods = extractServicePeriods(data);
    const servicePeriod = servicePeriods[0] || "the alleged service-impact period";
    const paymentDeadline = findDurationNear(data.contractText, ["pay", "payment", "invoice", "fees"]);
    const disputeDeadline = findDurationNear(data.contractText, ["disputes an invoice", "disputed amount", "basis for dispute"]);
    const cureDuration = findDurationNear(data.contractText, ["cure"]);
    const capPeriod = extractLiabilityCapPeriod(data.contractText);
    const provider = partyName(data, "provider", "claimant");
    const customer = partyName(data, "customer", "respondent");
    const refundAcceptanceIssue =
      hasTag(activeIssueTags, "refund") ||
      hasTag(activeIssueTags, "prepaid fees") ||
      hasTag(activeIssueTags, "acceptance / rejection");
    const confidentialityIpIssue =
      hasTag(activeIssueTags, "confidentiality") ||
      hasTag(activeIssueTags, "unauthorized disclosure") ||
      hasTag(activeIssueTags, "indemnity") ||
      hasTag(activeIssueTags, "third-party IP claim");
    const leaseIssue = hasLeaseActiveIssue(activeIssueTags);

    if (leaseIssue) {
      const noticeDate = leaseTimeline.tenantNoticeDate || "the tenant notice";
      const responseDate = leaseTimeline.landlordResponseDate || "the landlord response";
      const inspectionDate = leaseTimeline.contractorInspectionDate || "the roof contractor inspection";
      const completionDate = leaseTimeline.repairCompletionDate || "repair completion";
      const moveOutDate = leaseTimeline.moveOutDate || "surrender";
      const rentPeriod = leaseTimeline.rentWithholdingPeriod || "the rent period";
      const withholding = leaseTimeline.rentWithholdingPercent || "withheld";
      const depositAmount = leaseTimeline.depositDeduction || "the security deposit";
      const cure = leaseTimeline.repairCurePeriod ? durationRequirementLabel(leaseTimeline.repairCurePeriod) : "contractual";
      const abatementStart = leaseTimeline.abatementPeriod.start || noticeDate;
      const abatementEnd = leaseTimeline.abatementPeriod.end || completionDate;
      const capLabel = leaseTimeline.liabilityCapPeriod
        ? `${leaseTimeline.liabilityCapPeriod} of base rent liability cap`
        : "liability cap";

      if (hasTag(activeIssueTags, "notice")) {
        addUnique(issues, `Whether the ${noticeDate} tenant email satisfied the lease notice requirement or failed because certified mail was also required.`);
        addUnique(issues, `Whether the ${noticeDate} email was sent to the lease schedule notice email address.`);
        addUnique(issues, "When notice was deemed received under the email plus certified mail rule.");
      }
      if (hasTag(activeIssueTags, "cure period") || hasTag(activeIssueTags, "repair obligation")) {
        addUnique(issues, `Whether the ${cure} cure period was triggered and when it expired.`);
        addUnique(issues, `Whether the landlord began commercially reasonable roof repairs within the ${cure} cure period.`);
        addUnique(issues, `Whether the ${inspectionDate} roof contractor inspection qualifies as beginning commercially reasonable repairs.`);
        addUnique(issues, `Whether completion of roof repairs on ${completionDate} was timely enough under the lease after the ${responseDate} response.`);
      }
      if (hasTag(activeIssueTags, "rent abatement")) {
        addUnique(issues, "Whether the water intrusion materially interfered with the tenant's use of the showroom.");
        addUnique(issues, `Whether rent abatement is available for ${abatementStart} through ${abatementEnd}.`);
        addUnique(issues, "Whether rent abatement must be calculated by affected area and affected period.");
      }
      if (hasTag(activeIssueTags, "rent withholding") || hasTag(activeIssueTags, "payment default")) {
        addUnique(issues, `Whether the tenant's ${withholding} ${rentPeriod} withholding was authorized rent abatement or an unauthorized payment default.`);
      }
      if (hasTag(activeIssueTags, "security deposit")) {
        addUnique(issues, `Whether the ${depositAmount} security deposit deduction was supported by documented tenant-caused damage beyond ordinary wear and tear.`);
        addUnique(issues, `Whether the landlord provided an adequate itemized deposit statement within 30 days after the ${moveOutDate} move-out/surrender.`);
      }
      if (hasTag(activeIssueTags, "tenant-caused damage") || hasTag(activeIssueTags, "property damage causation")) {
        addUnique(issues, "Whether the flooring and repainting damage was caused by the roof leak or tenant misuse.");
      }
      if (hasTag(activeIssueTags, "damages") || hasTag(activeIssueTags, "liability limitation")) {
        addUnique(issues, "Whether display-fixture damages are recoverable or limited by consequential or lost-profit damages exclusions.");
        addUnique(issues, `Whether the ${capLabel} or unpaid rent, intentional misconduct, and tenant-caused property damage carve-outs apply.`);
      }
      if (issues.length) {
        return issues;
      }
    }

    if (confidentialityIpIssue) {
      const disclosureDate = confidentialityTimeline.disclosureDate || "the upload date";
      const discoveryDate = confidentialityTimeline.customerDiscoveryDate || "the customer discovery date";
      const removalDate = confidentialityTimeline.removalDate || "the removal date";
      const thirdPartyDate = confidentialityTimeline.thirdPartyClaimDate || "the third-party demand date";
      const indemnityNoticeDate = confidentialityTimeline.indemnityNoticeDate || "the indemnity notice date";
      const disclosureNoticePeriod = confidentialityTimeline.unauthorizedDisclosureNoticePeriod
        ? durationRequirementLabel(confidentialityTimeline.unauthorizedDisclosureNoticePeriod)
        : "contractual";
      const indemnityNoticePeriod = confidentialityTimeline.indemnityNoticePeriod
        ? durationRequirementLabel(confidentialityTimeline.indemnityNoticePeriod)
        : "contractual";
      const materialLabel = confidentialMaterials.length ? formatList(confidentialMaterials) : "customer confidential information";
      const capLabel = capPeriod ? `${durationAdjective(capPeriod)} fee cap` : "liability cap";

      if (hasTag(activeIssueTags, "confidentiality") || hasTag(activeIssueTags, "unauthorized disclosure")) {
        addUnique(issues, `Whether the ${disclosureDate} upload to a public workspace disclosed customer confidential information.`);
        addUnique(issues, `Whether the ${materialLabel} qualify as confidential information.`);
        addUnique(issues, `Whether the provider first discovered the exposure before ${discoveryDate} and failed to notify within the ${disclosureNoticePeriod} notice requirement.`);
        addUnique(issues, `Whether the ${removalDate} removal was sufficient containment and remediation.`);
        if (hasAny(allText(data), ["anonymous page views", "anonymous views"])) {
          addUnique(issues, "Whether anonymous page views show third-party access.");
        }
        if (hasAny(allText(data), ["subcontractor", "subcontractors"])) {
          addUnique(issues, "Whether subcontractors had confidentiality obligations at least as protective as the Agreement.");
        }
      }
      if (hasTag(activeIssueTags, "indemnity") || hasTag(activeIssueTags, "third-party IP claim")) {
        addUnique(issues, `Whether the ${thirdPartyDate} third-party IP demand triggers indemnity.`);
        addUnique(issues, `Whether the ${indemnityNoticeDate} indemnity notice was timely under the ${indemnityNoticePeriod} notice requirement.`);
        addUnique(issues, `Whether the ${indemnityNoticeDate} notice was sent to the contractual notice contacts.`);
        addUnique(issues, "Whether the analytics template was provider-owned or derived from customer-provided materials.");
      }
      if (hasTag(activeIssueTags, "liability cap carve-out")) {
        addUnique(issues, `Whether confidentiality or indemnity carve-outs prevent the ${capLabel} from limiting recovery.`);
      } else if (hasTag(activeIssueTags, "liability limitation")) {
        addUnique(issues, `Whether the ${capLabel} limits recovery after applying any damages exclusions.`);
      }
      if (hasTag(activeIssueTags, "damages") || hasTag(activeIssueTags, "liability limitation")) {
        addUnique(issues, "Whether remediation, investigation, defense, or business-impact damages are recoverable.");
      }
      if (issues.length) {
        return issues;
      }
    }

    if (refundAcceptanceIssue) {
      if (refundTimeline.dataImportMilestoneDate || refundTimeline.trainingMilestoneDate) {
        const dataImport = refundTimeline.dataImportMilestoneDate || "the data import milestone date";
        const training = refundTimeline.trainingMilestoneDate || "the administrator training milestone date";
        addUnique(issues, `Whether the ${dataImport} data import milestone and ${training} administrator training milestone were missed.`);
      }
      if (refundTimeline.partialDeliveryDate) {
        addUnique(issues, `Whether the ${refundTimeline.partialDeliveryDate} partial data import substantially completed the onboarding services.`);
      }
      if (refundTimeline.breachNoticeDate) {
        addUnique(issues, `Whether the customer's ${refundTimeline.breachNoticeDate} breach notice was sent to the contractual notice contacts.`);
      }
      if (refundTimeline.curePeriod && refundTimeline.terminationDate) {
        addUnique(issues, `Whether the ${refundTimeline.curePeriod} cure period expired before the ${refundTimeline.terminationDate} termination.`);
      }
      if (refundTimeline.partialDeliveryDate && hasSignal(clauseSignals, "acceptance")) {
        addUnique(issues, `Whether the ${refundTimeline.partialDeliveryDate} delivery package requested formal milestone acceptance.`);
      }
      if (refundTimeline.partialDeliveryDate && hasSignal(clauseSignals, "rejection")) {
        const rejectionPeriod = refundTimeline.rejectionPeriod ? `the ${refundTimeline.rejectionPeriod} rejection period` : "the contractual rejection period";
        addUnique(issues, `Whether the customer rejected the ${refundTimeline.partialDeliveryDate} delivery within ${rejectionPeriod}.`);
      }
      if (hasSignal(clauseSignals, "specificity")) {
        addUnique(issues, "Whether any rejection identified material defects with reasonable specificity.");
      }
      if (refundTimeline.prepaidAmount || hasSignal(clauseSignals, "non-refundable") || hasSignal(clauseSignals, "pro-rata refund")) {
        const amount = refundTimeline.prepaidAmount ? `${refundTimeline.prepaidAmount} implementation fee` : "implementation fee";
        addUnique(issues, `Whether the prepaid ${amount} is non-refundable or refundable pro rata after uncured breach.`);
      }
      if (refundTimeline.refundAmount || triggers.refund) {
        const amount = refundTimeline.refundAmount || "requested";
        addUnique(issues, `Whether the ${amount} refund calculation is supported by performed vs unperformed service records.`);
      }
      if (hasAny(allText(data), ["lost productivity", "internal delay"]) || hasSignal(clauseSignals, "consequential damages") || hasSignal(clauseSignals, "lost-profit")) {
        addUnique(issues, "Whether lost productivity or internal delay costs are barred by consequential damages or lost-profit exclusions.");
      }
      if (hasTag(activeIssueTags, "liability limitation")) {
        if (capPeriod) {
          addUnique(issues, `Whether the ${durationAdjective(capPeriod)} fee liability cap limits recovery.`);
        } else {
          addUnique(issues, "Whether the contractual liability cap limits recovery.");
        }
      }
      if (issues.length) {
        return issues;
      }
    }

    if (hasTag(activeIssueTags, "payment")) {
      const timing = paymentDeadline ? ` and overdue under the ${paymentDeadline} payment timing` : " and overdue";
      addUnique(issues, `Whether the ${invoiceLabel} were unpaid${timing}, and properly preserved as undisputed amounts.`);
    }
    if (hasTag(activeIssueTags, "invoice dispute")) {
      const deadline = disputeDeadline ? ` within ${disputeDeadline} of receiving each invoice` : " by the contractual invoice-dispute deadline";
      addUnique(issues, `Whether the ${customer} sent a written invoice dispute notice${deadline}, identifying the disputed amount and basis for dispute.`);
    }
    if (hasTag(activeIssueTags, "notice")) {
      if (hasTag(activeIssueTags, "force majeure")) {
        // Force majeure notice issues are generated with external-event dates below.
      } else if (hasTag(activeIssueTags, "delivery") && deliveryTimeline.noticeDate) {
        const cure = deliveryTimeline.curePeriod || cureDuration || "contractual";
        addUnique(issues, `Whether the ${deliveryTimeline.noticeDate} Delivery Delay Notice was sent to the contractual notice contacts and triggered the ${cure} cure period.`);
      } else {
        addUnique(issues, `Whether the ${provider}'s ${noticeDate} notice was sent to the contractual notice address and can be proven with delivery evidence.`);
      }
    }
    if (hasTag(activeIssueTags, "cure period")) {
      if (hasTag(activeIssueTags, "force majeure")) {
        // Force majeure notice timing is not a cure-period issue.
      } else if (hasTag(activeIssueTags, "delivery") && (deliveryTimeline.revisedPackageDate || deliveryTimeline.rejectionDate || deliveryTimeline.hasApiMappingDefects)) {
        const revised = deliveryTimeline.revisedPackageDate ? `${deliveryTimeline.revisedPackageDate} revised package` : "the revised package";
        const rejected = deliveryTimeline.rejectionDate || "the rejection";
        const review = deliveryTimeline.reviewPeriod ? ` and within the ${deliveryTimeline.reviewPeriod} review period` : "";
        const defects = deliveryTimeline.hasApiMappingDefects ? "API mapping defects" : "reported delivery defects";
        addUnique(issues, `Whether ${revised} cured the ${defects} before the ${rejected} rejection${review}.`);
      } else {
        const deemed = hasSignal(clauseSignals, "deemed receipt") ? " after next-business-day deemed receipt" : " after receipt";
        const cure = cureDuration || "contractual";
        addUnique(issues, `Whether the ${cure} cure period began${deemed} and expired before the ${actionDate} action.`);
      }
    }
    if (hasTag(activeIssueTags, "suspension")) {
      const scope = hasSignal(clauseSignals, "suspension") && hasAny(data.contractText, ["affected services", "commercially reasonable"])
        ? " and was limited to affected services where commercially reasonable"
        : "";
      addUnique(issues, `Whether the ${actionDate} suspension was contractually authorized${scope}.`);
    }
    if (hasTag(activeIssueTags, "termination")) {
      addUnique(issues, `Whether termination followed the required notice, cure, and effective-date process before access or work ended.`);
    }
    if (hasTag(activeIssueTags, "delivery")) {
      if (hasTag(activeIssueTags, "force majeure")) {
        // The force majeure block handles migration deadline and completion delay.
      } else if (deliveryTimeline.milestoneDate || deliveryTimeline.actualDeliveryDate) {
        const milestone = deliveryTimeline.milestoneDate ? `${deliveryTimeline.milestoneDate} production-ready delivery milestone` : "production-ready delivery milestone";
        const delivered = deliveryTimeline.actualDeliveryDate ? `delivery occurred on ${deliveryTimeline.actualDeliveryDate}` : "delivery was late";
        addUnique(issues, `Whether the ${milestone} was missed when ${delivered}.`);
      } else {
        const deliveryDates = findDatesNear(allText(data), ["delivery", "shipment", "milestone", "deadline"]);
        addUnique(issues, `Whether the ${deliveryDates.length ? formatList(deliveryDates) + " delivery timeline" : "delivery and milestone timeline"} met the contract deadline and acceptance criteria.`);
      }
      if (deliveryTimeline.rejectionDate && deliveryTimeline.reviewPeriod) {
        const startDate = deliveryTimeline.revisedPackageDate || deliveryTimeline.actualDeliveryDate || "delivery";
        addUnique(issues, `Whether the ${deliveryTimeline.rejectionDate} rejection was timely under the ${deliveryTimeline.reviewPeriod} review period after the ${startDate} package.`);
      }
    }
    if (hasTag(activeIssueTags, "SLA")) {
      const cause = triggers.customerSideCause || hasSignal(clauseSignals, "customer-side")
        ? " or was caused by customer-side systems or integration errors"
        : "";
      addUnique(issues, `Whether the alleged ${servicePeriod} downtime qualifies as an SLA/uptime failure${cause}.`);
    }
    if (hasTag(activeIssueTags, "service credit")) {
      addUnique(issues, "Whether service credits are the exclusive remedy for any verified SLA failure.");
    }
    if (hasTag(activeIssueTags, "damages")) {
      if (deliveryTimeline.hasLiquidatedDamages || hasTag(activeIssueTags, "liquidated damages")) {
        const formula = ldTerms.rate
          ? `${ldTerms.rate}${ldTerms.unit ? ` ${ldTerms.unit}` : ""} of unexcused delay`
          : "the contractual formula";
        const cap = ldTerms.cap ? ` and capped at ${ldTerms.cap}` : "";
        addUnique(issues, `Whether liquidated damages are calculated at ${formula}${cap} of the monthly service fee.`);
        addUnique(issues, "Whether the liquidated damages calculation is documented and applies the contractual formula.");
      }
      if (deliveryTimeline.hasLostRevenueExclusion) {
        addUnique(issues, "Whether claimed lost revenue is barred by the lost revenue exclusion.");
      }
      if (!deliveryTimeline.hasLiquidatedDamages && !deliveryTimeline.hasLostRevenueExclusion) {
        addUnique(issues, "Whether claimed lost revenue or other damages are supported by a calculation and barred by lost-profit or consequential damages exclusions.");
      }
    }
    if (hasTag(activeIssueTags, "liability limitation")) {
      if (capPeriod) {
        addUnique(issues, `Whether the ${durationAdjective(capPeriod)} fee liability cap limits recovery. Cap period is based on fees paid in the prior ${capPeriod}.`);
      } else {
        addUnique(issues, "Whether recovery is limited by the contractual liability cap.");
      }
    }
    if (hasTag(activeIssueTags, "force majeure")) {
      if (fmTimeline.governmentOrderDate) {
        addUnique(issues, `Whether the ${fmTimeline.governmentOrderDate} government emergency order qualifies as a force majeure event.`);
      } else {
        addUnique(issues, "Whether the invoked external event qualifies as force majeure under the contract.");
      }
      if (fmTimeline.awarenessDate || fmTimeline.governmentOrderDate) {
        const orderDate = fmTimeline.governmentOrderDate || "the external event date";
        const awarenessDate = fmTimeline.awarenessDate || "the provider's actual awareness date";
        addUnique(issues, `Whether the provider became aware of the migration impact on ${orderDate} or ${awarenessDate}.`);
      }
      if (fmTimeline.forceMajeureNoticeDate) {
        const requirement = findDurationNear(data.contractText, ["force majeure notice", "becoming aware", "aware"]) || "contractual";
        addUnique(issues, `Whether the ${fmTimeline.forceMajeureNoticeDate} force majeure notice was timely under the ${requirement} notice requirement.`);
        addUnique(issues, `Whether the ${fmTimeline.forceMajeureNoticeDate} notice was sent to the contractual notice contacts.`);
      }
      if (hasTag(activeIssueTags, "mitigation")) {
        addUnique(issues, "Whether the provider used commercially reasonable mitigation, including remote migration tools and alternate staffing.");
      }
      if (hasTag(activeIssueTags, "cover costs") || fmTimeline.consultantDate) {
        const consultantDate = fmTimeline.consultantDate || "temporary consultant";
        addUnique(issues, `Whether the ${consultantDate} temporary consultant cost was reasonable, necessary, direct, and documented cover cost.`);
      }
      if (fmTimeline.partialCompletionDate || fmTimeline.finalCompletionDate) {
        const partial = fmTimeline.partialCompletionDate || "partial completion";
        const final = fmTimeline.finalCompletionDate || "final completion";
        addUnique(issues, `Whether the ${partial} partial completion and ${final} final completion leave any period of unexcused delay.`);
      }
    }
    if (!issues.length) {
      addUnique(issues, "Which contract obligation is actually disputed and which dated records prove or disprove it.");
    }

    return issues;
  }

  function buildNextSteps(data, diagnosis) {
    const steps = [];
    const tags = diagnosis.active_issue_tags || diagnosis.activeIssueTags || diagnosis.issue_tags || diagnosis.issueTags || [];
    const fmTimeline = extractForceMajeureTimeline(data);
    const refundTimeline = extractRefundTerminationTimeline(data);
    const confidentialityTimeline = extractConfidentialityIndemnityTimeline(data);
    const leaseTimeline = extractLeaseTimeline(data);
    const ldTerms = extractLiquidatedDamagesTerms(data);
    const refundAcceptanceIssue =
      hasTag(tags, "refund") ||
      hasTag(tags, "prepaid fees") ||
      hasTag(tags, "acceptance / rejection");
    const confidentialityIpIssue =
      hasTag(tags, "confidentiality") ||
      hasTag(tags, "unauthorized disclosure") ||
      hasTag(tags, "indemnity") ||
      hasTag(tags, "third-party IP claim");
    const leaseIssue = hasLeaseActiveIssue(tags);

    if (leaseIssue) {
      const datedTimeline = [
        leaseTimeline.waterIntrusionDate,
        leaseTimeline.tenantNoticeDate,
        leaseTimeline.landlordResponseDate,
        leaseTimeline.contractorInspectionDate,
        leaseTimeline.rentWithholdingPeriod,
        leaseTimeline.repairCompletionDate,
        leaseTimeline.moveOutDate
      ].filter(Boolean).join(" / ");
      addUnique(steps, datedTimeline ? `Build a ${datedTimeline} timeline.` : "Build a lease repair, notice, rent abatement, rent withholding, repair completion, and move-out timeline.");
      addUnique(steps, "Verify the lease schedule notice addresses.");
      addUnique(steps, `Verify whether the ${leaseTimeline.tenantNoticeDate || "tenant"} notice was sent by both required methods: email and certified mail.`);
      addUnique(steps, "Calculate deemed receipt under the lease notice rule.");
      addUnique(steps, `Calculate the ${durationRequirementLabel(leaseTimeline.repairCurePeriod) || "contractual"} cure deadline after valid receipt.`);
      addUnique(steps, `Determine whether the ${leaseTimeline.contractorInspectionDate || "contractor"} inspection qualifies as beginning commercially reasonable repairs.`);
      addUnique(steps, `Compare repair start, contractor inspection, and ${leaseTimeline.repairCompletionDate || "repair completion"} completion records.`);
      addUnique(steps, "Quantify the affected showroom area and affected period.");
      addUnique(steps, "Calculate permissible rent abatement by affected area and affected period.");
      addUnique(steps, `Assess whether the ${leaseTimeline.rentWithholdingPercent || "partial"} ${leaseTimeline.rentWithholdingPeriod || "rent"} withholding was authorized rent abatement or a payment default.`);
      addUnique(steps, `Compare the ${leaseTimeline.depositDeduction || "security deposit"} security deposit deduction with move-out photos, repair invoices, and the ordinary wear-and-tear standard.`);
      addUnique(steps, "Determine whether flooring and repainting damage was caused by the roof leak or tenant misuse.");
      addUnique(steps, "Review itemized deposit statement timing and sufficiency.");
      addUnique(steps, `Review consequential/lost-profit damages exclusions and ${leaseTimeline.liabilityCapPeriod ? `${leaseTimeline.liabilityCapPeriod} of base rent` : "contractual"} liability cap.`);
      addUnique(steps, "Evaluate recoverability of display-fixture damages.");
      return limitStepsForDepth(data, steps);
    }

    if (confidentialityIpIssue) {
      const datedTimeline = [
        confidentialityTimeline.disclosureDate,
        confidentialityTimeline.customerDiscoveryDate,
        confidentialityTimeline.removalDate,
        confidentialityTimeline.thirdPartyClaimDate,
        confidentialityTimeline.indemnityNoticeDate
      ].filter(Boolean).join(" / ");
      addUnique(steps, datedTimeline ? `Build a ${datedTimeline} timeline.` : "Build a confidentiality exposure, remediation, third-party claim, and indemnity notice timeline.");
      if (hasTag(tags, "confidentiality") || hasTag(tags, "unauthorized disclosure")) {
        addUnique(steps, "Determine provider's actual discovery date for the public exposure.");
        addUnique(steps, `Verify whether the provider gave unauthorized-disclosure notice within the ${durationRequirementLabel(confidentialityTimeline.unauthorizedDisclosureNoticePeriod) || "contractual"} notice period.`);
        addUnique(steps, "Review workspace access logs, including anonymous page views.");
        addUnique(steps, "Verify subcontractor confidentiality obligations.");
      }
      if (hasTag(tags, "indemnity") || hasTag(tags, "third-party IP claim")) {
        addUnique(steps, confidentialityTimeline.indemnityNoticeDate ? `Verify proof of ${confidentialityTimeline.indemnityNoticeDate} indemnity notice delivery to contractual notice contacts.` : "Verify proof of indemnity notice delivery to contractual notice contacts.");
        addUnique(steps, "Compare the analytics template with the third-party copyrighted work.");
        addUnique(steps, "Determine whether the template was provider-owned or derived from customer materials.");
        addUnique(steps, "Estimate defense costs and remediation/investigation costs.");
      }
      if (hasTag(tags, "liability cap carve-out")) {
        const capPeriod = durationAdjective(extractLiabilityCapPeriod(data.contractText));
        addUnique(steps, `Analyze confidentiality and indemnity carve-outs from the ${capPeriod ? `${capPeriod} ` : ""}liability cap.`);
      }
      if (hasTag(tags, "damages") || hasTag(tags, "liability limitation")) {
        addUnique(steps, "Review damages exclusions and recoverability of business-impact damages.");
      }
      addDesiredOutcomeStep(steps, data, tags);
      return limitStepsForDepth(data, steps);
    }

    if (hasTag(tags, "force majeure") && hasTag(tags, "delivery")) {
      const datedTimeline = [
        fmTimeline.governmentOrderDate,
        fmTimeline.awarenessDate,
        fmTimeline.forceMajeureNoticeDate,
        fmTimeline.migrationDeadline,
        fmTimeline.consultantDate,
        fmTimeline.partialCompletionDate,
        fmTimeline.finalCompletionDate
      ].filter(Boolean).join(" / ");
      addUnique(steps, datedTimeline ? `Build a ${datedTimeline} timeline.` : "Build a force majeure notice, migration deadline, mitigation, and completion timeline.");
      addUnique(steps, "Verify the SOW notice contacts.");
      addUnique(steps, "Verify proof that the force majeure notice was sent to contractual contacts.");
      addUnique(steps, "Determine the actual awareness date for the affected migration.");
      addUnique(steps, "Assess whether notice was within the contractual business-day notice period.");
      addUnique(steps, "Review mitigation evidence for remote tools, alternate staffing, and alternate site access.");
      addUnique(steps, "Evaluate whether the temporary consultant was reasonable and necessary cover.");
      addUnique(
        steps,
        `Calculate liquidated damages by full weeks of unexcused delay${ldTerms.rate ? ` using ${ldTerms.rate} weekly` : ""}${ldTerms.cap ? ` and ${ldTerms.cap} cap` : ""}.`
      );
      addUnique(steps, "Analyze lost revenue under the lost-profit/consequential damages exclusion.");
      addUnique(steps, "Apply the six-month fee liability cap.");
      addDesiredOutcomeStep(steps, data, tags);
      return limitStepsForDepth(data, steps);
    }

    if (refundAcceptanceIssue) {
      const datedTimeline = [
        refundTimeline.prepaidPaymentDate,
        refundTimeline.dataImportMilestoneDate,
        refundTimeline.trainingMilestoneDate,
        refundTimeline.partialDeliveryDate,
        refundTimeline.breachNoticeDate,
        refundTimeline.providerResponseDate,
        refundTimeline.terminationDate
      ].filter(Boolean).join(" / ");
      addUnique(steps, datedTimeline ? `Build a ${datedTimeline} timeline.` : "Build a prepaid fee, milestone, breach notice, cure, termination, and acceptance timeline.");
      addUnique(steps, "Verify SOW notice contacts.");
      addUnique(steps, refundTimeline.breachNoticeDate ? `Verify proof of ${refundTimeline.breachNoticeDate} breach notice delivery.` : "Verify proof of breach notice delivery.");
      addUnique(steps, `Calculate deemed receipt and ${refundTimeline.curePeriod || "contractual"} cure deadline.`);
      addUnique(steps, `Determine whether the ${refundTimeline.partialDeliveryDate || "delivery"} delivery requested formal acceptance.`);
      addUnique(steps, `Determine whether the customer rejected within ${durationSentence(refundTimeline.rejectionPeriod) || "the contractual rejection period"}.`);
      addUnique(steps, "Review whether rejection identified material defects with reasonable specificity.");
      addUnique(steps, "Compare performed vs unperformed service records.");
      addUnique(steps, refundTimeline.refundAmount ? `Validate the ${refundTimeline.refundAmount} pro-rata refund calculation.` : "Validate the pro-rata refund calculation.");
      addUnique(steps, `Review consequential damages, lost-profit exclusion, and ${durationAdjective(extractLiabilityCapPeriod(data.contractText)) || "contractual"} fee liability cap.`);
      addUnique(steps, "Verify evidence supporting lost productivity damages.");
      addDesiredOutcomeStep(steps, data, tags);
      return limitStepsForDepth(data, steps);
    }

    if (hasTag(tags, "notice") || hasTag(tags, "cure period") || hasTag(tags, "suspension") || hasTag(tags, "termination")) {
      addUnique(steps, "Reconstruct the invoice / notice / cure / suspension timeline with dates, deemed receipt, and action date.");
      addUnique(steps, "Verify the contractual notice address from the order form or notice clause.");
      addUnique(steps, "Verify proof of notice delivery, including whether the notice was sent to the required address.");
      addUnique(steps, "Calculate deemed receipt and the cure deadline before assessing suspension or termination.");
    }
    if (hasTag(tags, "payment") || hasTag(tags, "invoice dispute")) {
      addUnique(steps, "Collect invoice receipt dates for each invoice.");
      addUnique(steps, "Collect any customer written invoice dispute notices and compare them to the contractual dispute deadline.");
      addUnique(steps, "Separate disputed amounts from undisputed amounts and map both to payment records.");
    }
    if (hasTag(tags, "SLA") || hasTag(tags, "service credit")) {
      addUnique(steps, "Compare support tickets, provider uptime reports, independent monitoring, and customer-side integration or error logs.");
      addUnique(steps, "Determine whether any downtime is excluded by customer-side systems, maintenance, non-payment, or other service exclusions.");
      addUnique(steps, "Review the service credit remedy for any verified SLA failure.");
    }
    if (hasTag(tags, "damages") || hasTag(tags, "liability limitation")) {
      addUnique(steps, "Review lost-profit, consequential damages, and other damages exclusions.");
      addUnique(steps, "Review the liability cap and calculate the applicable fee period.");
      addUnique(steps, "Verify the lost revenue or damages calculation against source records.");
    }
    if (!steps.length) {
      addUnique(steps, "Build a dated timeline and attach source evidence to each issue before relying on the diagnosis.");
    }
    addDesiredOutcomeStep(steps, data, tags);

    return limitStepsForDepth(data, steps);
  }

  function addDesiredOutcomeStep(steps, data, activeIssueTags) {
    if (!data.desiredOutcome) {
      return;
    }
    if (
      !hasTag(activeIssueTags, "force majeure") &&
      hasFamilyBlocker(data, "force_majeure") &&
      hasAny(data.desiredOutcome, ["force majeure"])
    ) {
      return;
    }
    addUnique(steps, `Frame the next report around the desired outcome: ${data.desiredOutcome}`);
  }

  function isCriticalEvidenceGap(gap) {
    const text = normalize(gap);
    return (
      text.includes("notice address") ||
      text.includes("proof of notice") ||
      text.includes("proof that") ||
      text.includes("notice delivery") ||
      text.includes("invoice dispute notice") ||
      text.includes("invoice receipt") ||
      text.includes("cure deadline") ||
      text.includes("payment due") ||
      text.includes("sla monitoring") ||
      text.includes("timestamped sla") ||
      text.includes("damages calculation") ||
      text.includes("lost revenue calculation") ||
      text.includes("lost productivity") ||
      text.includes("refund calculation") ||
      text.includes("work-completion") ||
      text.includes("performed vs unperformed") ||
      text.includes("formal milestone acceptance") ||
      text.includes("rejected within") ||
      text.includes("disputed amounts") ||
      text.includes("first discovered") ||
      text.includes("anonymous page views") ||
      text.includes("subcontractors") ||
      text.includes("technical comparison") ||
      text.includes("provider-owned") ||
      text.includes("customer-provided") ||
      text.includes("defense cost estimate") ||
      text.includes("remediation") ||
      text.includes("investigation") ||
      text.includes("business-impact") ||
      text.includes("certified mail") ||
      text.includes("lease schedule notice") ||
      text.includes("materially interfered") ||
      text.includes("material interference") ||
      text.includes("affected showroom") ||
      text.includes("affected square footage") ||
      text.includes("repair timing") ||
      text.includes("began commercially reasonable repairs") ||
      text.includes("tenant misuse") ||
      text.includes("ordinary wear and tear") ||
      text.includes("rent abatement") ||
      text.includes("display-fixture") ||
      text.includes("itemized deposit statement")
    );
  }

  function isProceduralEvidenceGap(gap) {
    const text = normalize(gap);
    return text.includes("notice address") || text.includes("notice delivery") || text.includes("proof of notice") || text.includes("cure deadline") || text.includes("deemed receipt") || text.includes("certified mail") || text.includes("lease schedule notice");
  }

  function scoreRisk(data, activeIssueTags, evidenceGaps, timelineFacts, triggers) {
    const combined = allText(data);
    const nonPlaceholderGaps = evidenceGaps.filter((gap) => !normalize(gap).startsWith("no obvious"));
    const criticalGaps = nonPlaceholderGaps.filter(isCriticalEvidenceGap);
    const proceduralGap = criticalGaps.some(isProceduralEvidenceGap);
    const proceduralIssue =
      hasTag(activeIssueTags, "notice") ||
      hasTag(activeIssueTags, "cure period") ||
      hasTag(activeIssueTags, "suspension") ||
      hasTag(activeIssueTags, "termination");
    const leaseIssue = hasLeaseActiveIssue(activeIssueTags);
    const severeIssue =
      hasTag(activeIssueTags, "suspension") ||
      hasTag(activeIssueTags, "termination") ||
      hasTag(activeIssueTags, "damages") ||
      hasTag(activeIssueTags, "liability limitation");
    const evidenceScore = countGroup(data.evidence, "evidence");
    const timelineScore = dateSignalCount(combined);
    const rationale = [];
    let level = "unclear";

    if (activeIssueTags.length && !hasTag(activeIssueTags, "unclear")) {
      rationale.push(`Active issues detected: ${activeIssueTags.join(", ")}.`);
    }
    if (criticalGaps.length) {
      rationale.push(`Critical evidence gaps affect core elements: ${criticalGaps.join("; ")}.`);
    }
    if (proceduralIssue && proceduralGap) {
      rationale.push(
        leaseIssue
          ? "Notice and repair cure prerequisites depend on missing procedural proof, so risk cannot be low."
          : "Notice, cure, suspension, or termination depends on missing procedural proof, so risk cannot be low."
      );
    }
    if (triggers.contested) {
      rationale.push("Party positions dispute core facts or causation.");
    }
    if (hasTag(activeIssueTags, "liability limitation")) {
      if (hasTag(activeIssueTags, "service credit")) {
        rationale.push("Requested remedies may exceed service-credit, damages-exclusion, or liability-cap limits.");
      } else {
        rationale.push("Requested remedies may exceed damages-exclusion or liability-cap limits.");
      }
    }
    if (leaseIssue) {
      rationale.push("Notice delivery method and valid receipt remain evidence-dependent.");
      rationale.push("The cure deadline depends on valid notice and deemed receipt.");
      rationale.push("The repair obligation depends on whether the landlord began commercially reasonable repairs.");
      rationale.push("Rent abatement depends on material interference, affected area, and affected period.");
      if (hasTag(activeIssueTags, "rent withholding") || hasTag(activeIssueTags, "payment default")) {
        rationale.push("Rent withholding may create payment default risk if unauthorized.");
      }
      if (hasTag(activeIssueTags, "security deposit") || hasTag(activeIssueTags, "property damage causation")) {
        rationale.push("The security deposit deduction depends on causation and documentation.");
      }
      if (hasTag(activeIssueTags, "liability limitation")) {
        rationale.push("Damages exclusions and the base-rent liability cap may limit recovery.");
      }
    }

    if (combined.trim().length < 140) {
      level = "unclear";
      rationale.push("Input is too short for a reliable deterministic risk label.");
    } else if (severeIssue && criticalGaps.length >= 6 && triggers.contested) {
      level = "high";
    } else if ((proceduralIssue && proceduralGap) || criticalGaps.length >= 2 || (severeIssue && triggers.contested)) {
      level = "medium";
    } else if (activeIssueTags.length && evidenceScore >= 3 && timelineScore >= 2 && nonPlaceholderGaps.length <= 1) {
      level = "low";
    } else if (activeIssueTags.length || nonPlaceholderGaps.length) {
      level = "medium";
    }
    if (leaseIssue && combined.trim().length >= 140 && level !== "unclear") {
      level = "medium";
    }

    return {
      level,
      rationale: rationale.length ? rationale : ["Risk remains unclear because the input lacks enough classified facts."],
      critical_evidence_gaps: criticalGaps,
      evidence_dependent: criticalGaps.length > 0
    };
  }

  function contestedFacts(data) {
    const facts = [];
    const respondent = normalize(data.respondentPosition);
    const claimant = normalize(data.claimantPosition);

    if ((respondent.includes("disputed") || claimant.includes("undisputed")) && hasAny(respondent + " " + claimant, ["invoice", "payment", "amount", "undisputed"])) {
      facts.push("Whether the disputed amount was actually undisputed when payment became due");
    }
    if (respondent.includes("notice") || claimant.includes("notice")) {
      facts.push("Whether notice was sent in the required form and started the cure period");
    }
    if (respondent.includes("downtime") || claimant.includes("downtime") || respondent.includes("sla") || claimant.includes("sla")) {
      facts.push("Whether service downtime was provider-side, customer-side, or otherwise excluded");
    }
    if (respondent.includes("lost revenue") || claimant.includes("lost revenue") || respondent.includes("lost productivity") || claimant.includes("lost productivity") || respondent.includes("damages") || claimant.includes("damages")) {
      if (respondent.includes("service credit") || claimant.includes("service credit")) {
        facts.push("Whether claimed damages are recoverable after service-credit, damages-exclusion, and liability-cap terms");
      } else {
        facts.push("Whether claimed damages are recoverable after damages-exclusion and liability-cap terms");
      }
    }
    if (respondent.includes("accepted") || claimant.includes("accepted")) {
      facts.push("Whether work or goods were accepted before the dispute escalated");
    }
    if (respondent.includes("confidential") || claimant.includes("confidential") || respondent.includes("disclosure") || claimant.includes("disclosure")) {
      facts.push("Whether the alleged disclosure breached confidentiality obligations and what access records prove");
    }
    if (respondent.includes("indemnity") || claimant.includes("indemnity") || respondent.includes("infring") || claimant.includes("infring") || respondent.includes("copyright") || claimant.includes("copyright")) {
      facts.push("Whether the third-party IP demand falls within indemnity coverage or a customer-materials exception");
    }
    if (!facts.length) {
      facts.push("Which facts each side can prove with dated records");
    }

    return facts;
  }

  function normalizeFinalDiagnosis(diagnosis) {
    const source = diagnosis && typeof diagnosis === "object" ? diagnosis : {};
    const activeIssueTags = normalizeStringList(source.active_issue_tags);
    const legacyIssueTags = normalizeStringList(source.issue_tags || source.activeIssueTags || source.issueTags);
    const finalActiveIssueTags = activeIssueTags.length ? activeIssueTags : legacyIssueTags;
    const clauseSignals = normalizeStringList(source.clause_signals);
    const disputeTypes = normalizeStringList(source.dispute_types);
    const finalDisputeTypes = disputeTypes.length ? disputeTypes : normalizeStringList([source.dispute_type || "Other"]);
    const evidenceGaps = normalizeStringList(source.evidence_gaps);
    const risk = normalizeRisk(source.risk);
    const riskSignal = risk.level !== "unclear" ? risk.level : source.risk_signal || "unclear";
    const disputeSummary = source.dispute_summary || source.summary || "";

    return {
      ...source,
      summary: disputeSummary,
      dispute_summary: disputeSummary,
      contract_type: source.contract_type || "Other",
      dispute_types: finalDisputeTypes,
      dispute_type: finalDisputeTypes.join("; "),
      active_issue_tags: finalActiveIssueTags.length ? finalActiveIssueTags : ["unclear"],
      issue_tags: finalActiveIssueTags.length ? [...finalActiveIssueTags] : ["unclear"],
      clause_signals: clauseSignals,
      relevant_clause_signals: [...clauseSignals],
      key_issues: normalizeStringList(source.key_issues),
      timeline_facts: normalizeStringList(source.timeline_facts),
      position_matrix: normalizePositionMatrix(source.position_matrix),
      evidence_gaps: evidenceGaps,
      risk: {
        ...risk,
        level: riskSignal,
        critical_evidence_gaps: normalizeStringList(risk.critical_evidence_gaps)
      },
      risk_signal: riskSignal,
      suggested_next_steps: normalizeStringList(source.suggested_next_steps),
      report_outputs: normalizeStringList(source.report_outputs || ["markdown", "json-style"])
    };
  }

  function normalizeStringList(items) {
    return uniqueValues(Array.isArray(items) ? items : []);
  }

  function normalizeRisk(risk) {
    const source = risk && typeof risk === "object" ? risk : {};
    return {
      ...source,
      level: source.level || "unclear",
      rationale: normalizeStringList(source.rationale || []),
      critical_evidence_gaps: normalizeStringList(source.critical_evidence_gaps || []),
      evidence_dependent: Boolean(source.evidence_dependent)
    };
  }

  function normalizePositionMatrix(positionMatrix) {
    const source = positionMatrix && typeof positionMatrix === "object" ? positionMatrix : {};
    return {
      claimant: source.claimant || "No claimant position provided.",
      respondent: source.respondent || "No respondent position provided.",
      contested_facts: normalizeStringList(source.contested_facts)
    };
  }

  function diagnose(data) {
    const triggers = extractFactualTriggers(data);
    const relevantClauseSignals = buildClauseSignals(data);
    const activeIssueTags = deriveActiveIssueTags(data, relevantClauseSignals, triggers);
    const evidenceGaps = buildEvidenceGaps(data, activeIssueTags, relevantClauseSignals, triggers);
    const timelineFacts = extractTimelineFacts(data, activeIssueTags, relevantClauseSignals, evidenceGaps);
    const detectedDisputeTypes = detectDisputeTypes(data, activeIssueTags, triggers);

    let finalDiagnosis = normalizeFinalDiagnosis({
      case_type: normalize(detectedDisputeTypes[0] || data.disputeType || "other").replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "other",
      contract_type: detectContractTypes(data).join("; "),
      dispute_type: detectedDisputeTypes.join("; "),
      dispute_types: detectedDisputeTypes,
      diagnosis_depth: data.diagnosisDepth,
      output_format_preference: data.outputFormat,
      risk_mode: data.riskMode,
      risk_signal: "unclear",
      risk: {
        level: "unclear",
        rationale: [],
        critical_evidence_gaps: [],
        evidence_dependent: false
      },
      active_issue_tags: [...activeIssueTags],
      issue_tags: [...activeIssueTags],
      dispute_summary: summarize(data),
      key_issues: [],
      clause_signals: [...relevantClauseSignals],
      relevant_clause_signals: [...relevantClauseSignals],
      timeline_facts: [...timelineFacts],
      position_matrix: {
        claimant: data.claimantPosition || "No claimant position provided.",
        respondent: data.respondentPosition || "No respondent position provided.",
        contested_facts: contestedFacts(data)
      },
      evidence_gaps: [...evidenceGaps],
      suggested_next_steps: [],
      report_outputs: ["markdown", "json-style"]
    });

    const keyIssues = buildIssues(
      data,
      finalDiagnosis.active_issue_tags,
      finalDiagnosis.clause_signals,
      finalDiagnosis.timeline_facts,
      triggers
    );
    const risk = scoreRisk(
      data,
      finalDiagnosis.active_issue_tags,
      finalDiagnosis.evidence_gaps,
      finalDiagnosis.timeline_facts,
      triggers
    );
    finalDiagnosis = normalizeFinalDiagnosis({
      ...finalDiagnosis,
      key_issues: keyIssues,
      risk,
      risk_signal: risk.level
    });
    finalDiagnosis = normalizeFinalDiagnosis({
      ...finalDiagnosis,
      suggested_next_steps: buildNextSteps(data, finalDiagnosis)
    });

    return finalDiagnosis;
  }

  function detectContractTypes(data) {
    const types = [];
    const contractSupportText = [data.contractText, data.metadata].join(" ");
    const factSupportedSaas =
      hasIssueFactTrigger(data, "sla") ||
      hasIssueFactTrigger(data, "suspension", ["platform access", "user seats", "hosted software", "subscription platform"]);
    if (data.contractType) {
      addUnique(types, data.contractType);
    }
    if ((hasAny(contractSupportText, ["saas", "subscription platform", "hosted software", "uptime", "sla", "service credits", "service credit", "platform access", "user seats"]) || factSupportedSaas) && !types.some((type) => normalize(type).includes("saas"))) {
      addUnique(types, "SaaS Agreement");
    }
    return types.length ? types : ["Other"];
  }

  function selectedDisputeTypeSupported(selected, activeIssueTags) {
    const text = normalize(selected);
    if (!text || text === "other") {
      return false;
    }
    if (hasAny(text, ["payment", "invoice"])) {
      return hasTag(activeIssueTags, "payment") || hasTag(activeIssueTags, "invoice dispute");
    }
    if (text.includes("refund")) {
      return hasTag(activeIssueTags, "refund") || hasTag(activeIssueTags, "prepaid fees");
    }
    if (hasAny(text, ["force majeure", "external event"])) {
      return hasTag(activeIssueTags, "force majeure");
    }
    if (hasAny(text, ["late delivery", "delivery", "acceptance"])) {
      return hasTag(activeIssueTags, "delivery") || hasTag(activeIssueTags, "acceptance / rejection");
    }
    if (hasAny(text, ["sla", "service credit", "uptime", "downtime"])) {
      return hasTag(activeIssueTags, "SLA") || hasTag(activeIssueTags, "service credit");
    }
    if (text.includes("suspension")) {
      return hasTag(activeIssueTags, "suspension");
    }
    if (hasAny(text, ["notice", "cure"])) {
      return hasTag(activeIssueTags, "notice") || hasTag(activeIssueTags, "cure period");
    }
    if (text.includes("termination")) {
      return hasTag(activeIssueTags, "termination");
    }
    if (hasAny(text, ["damages", "liability"])) {
      return hasTag(activeIssueTags, "damages") || hasTag(activeIssueTags, "liability limitation") || hasTag(activeIssueTags, "liability cap carve-out");
    }
    if (hasAny(text, ["confidentiality", "confidential", "disclosure"])) {
      return hasTag(activeIssueTags, "confidentiality") || hasTag(activeIssueTags, "unauthorized disclosure");
    }
    if (hasAny(text, ["indemnity", "indemnification", "ip", "intellectual property"])) {
      return hasTag(activeIssueTags, "indemnity") || hasTag(activeIssueTags, "third-party IP claim");
    }
    return false;
  }

  function detectDisputeTypes(data, activeIssueTags, triggers) {
    const types = [];
    if (selectedDisputeTypeSupported(data.disputeType, activeIssueTags)) {
      addUnique(types, data.disputeType);
    }
    if (hasTag(activeIssueTags, "confidentiality")) {
      addUnique(types, "Confidentiality");
    }
    if (hasTag(activeIssueTags, "unauthorized disclosure")) {
      addUnique(types, "Unauthorized Disclosure / Data Exposure");
    }
    if (hasTag(activeIssueTags, "indemnity")) {
      addUnique(types, "Indemnity");
    }
    if (hasTag(activeIssueTags, "third-party IP claim")) {
      addUnique(types, "Third-Party IP Claim / Intellectual Property");
    }
    if (hasTag(activeIssueTags, "notice") || hasTag(activeIssueTags, "cure period")) {
      if (hasTag(activeIssueTags, "cure period")) {
        addUnique(types, "Notice/Cure Period");
      }
    }
    if (hasTag(activeIssueTags, "lease maintenance") || hasTag(activeIssueTags, "repair obligation")) {
      addUnique(types, "Lease Maintenance / Repair");
    }
    if (hasTag(activeIssueTags, "rent abatement")) {
      addUnique(types, "Rent Abatement");
    }
    if (hasTag(activeIssueTags, "security deposit")) {
      addUnique(types, "Security Deposit");
    }
    if (hasTag(activeIssueTags, "payment") && hasTag(activeIssueTags, "suspension")) {
      addUnique(types, "Payment/Suspension");
    } else if (hasTag(activeIssueTags, "payment") || hasTag(activeIssueTags, "invoice dispute")) {
      addUnique(types, "Payment/Invoice Dispute");
    }
    if (hasTag(activeIssueTags, "SLA") || hasTag(activeIssueTags, "service credit")) {
      addUnique(types, "SLA/Service Credit");
    }
    if (hasTag(activeIssueTags, "force majeure")) {
      addUnique(types, "Force Majeure");
    }
    if (hasTag(activeIssueTags, "notice")) {
      addUnique(types, "Notice");
    }
    if (hasTag(activeIssueTags, "damages") || hasTag(activeIssueTags, "liability limitation")) {
      addUnique(types, "Damages/Liability");
    }
    if (hasTag(activeIssueTags, "cover costs") || hasTag(activeIssueTags, "mitigation")) {
      addUnique(types, "Cover Costs/Mitigation");
    }
    if ((triggers.termination || hasTag(activeIssueTags, "termination")) && !hasLeaseActiveIssue(activeIssueTags)) {
      addUnique(types, "Termination");
    }
    if (hasTag(activeIssueTags, "acceptance / rejection")) {
      addUnique(types, "Acceptance/Rejection");
    } else if ((triggers.delivery || hasTag(activeIssueTags, "delivery")) && hasAny(allText(data), ["acceptance criteria", "accepted delivery", "acceptance test", "acceptance testing"])) {
      addUnique(types, "Delivery/Acceptance");
    }
    if (hasTag(activeIssueTags, "delivery") && hasAny(factText(data) + " " + data.disputeType, ["late delivery", "delayed", "missed", "deadline", "migration deadline"])) {
      addUnique(types, "Late Delivery");
    }
    if (triggers.refund || hasTag(activeIssueTags, "refund")) {
      addUnique(types, "Refund");
    }
    return types.length ? types : ["Other"];
  }

  function summarize(data) {
    const dispute = data.disputeDescription || "No dispute description provided.";
    const trimmed = dispute.replace(/\s+/g, " ").trim();
    const max = 260;
    const summary = trimmed.length > max ? `${trimmed.slice(0, max - 3)}...` : trimmed;
    return `${data.contractType || "Contract"} / ${data.disputeType || "Dispute"}: ${summary}`;
  }

  function markdownReport(diagnosis) {
    const finalDiagnosis = normalizeFinalDiagnosis(diagnosis);
    return [
      `# Contract2Agent Diagnosis Preview`,
      "",
      `**Contract type:** ${finalDiagnosis.contract_type}`,
      `**Dispute type:** ${finalDiagnosis.dispute_type}`,
      `**Risk signal:** ${finalDiagnosis.risk_signal}`,
      `**Diagnosis depth:** ${finalDiagnosis.diagnosis_depth}`,
      "",
      "## Dispute Summary",
      finalDiagnosis.dispute_summary,
      "",
      "## Active Issue Tags",
      ...finalDiagnosis.active_issue_tags.map((tag) => `- ${tag}`),
      "",
      "## Key Issues",
      ...finalDiagnosis.key_issues.map((issue) => `- ${issue}`),
      "",
      "## Clause Signals",
      ...finalDiagnosis.clause_signals.map((signal) => `- ${signal}`),
      "",
      "## Timeline Facts",
      ...finalDiagnosis.timeline_facts.map((fact) => `- ${fact}`),
      "",
      "## Claimant vs Respondent",
      `- Claimant: ${finalDiagnosis.position_matrix.claimant}`,
      `- Respondent: ${finalDiagnosis.position_matrix.respondent}`,
      `- Contested facts: ${finalDiagnosis.position_matrix.contested_facts.join("; ")}`,
      "",
      "## Risk Rationale",
      ...finalDiagnosis.risk.rationale.map((reason) => `- ${reason}`),
      "",
      "## Evidence Gaps",
      ...finalDiagnosis.evidence_gaps.map((gap) => `- ${gap}`),
      "",
      "## Suggested Next Steps",
      ...finalDiagnosis.suggested_next_steps.map((step) => `- ${step}`)
    ].join("\n");
  }

  function structuredPreview(diagnosis) {
    const finalDiagnosis = normalizeFinalDiagnosis(diagnosis);
    return {
      summary: finalDiagnosis.dispute_summary,
      detected: {
        contract_type: finalDiagnosis.contract_type,
        dispute_type: finalDiagnosis.dispute_type,
        active_issue_tags: finalDiagnosis.active_issue_tags,
        clause_signals: finalDiagnosis.clause_signals
      },
      timeline_facts: finalDiagnosis.timeline_facts,
      evidence_gaps: finalDiagnosis.evidence_gaps,
      risk: finalDiagnosis.risk,
      risk_signal: finalDiagnosis.risk_signal,
      report_outputs: finalDiagnosis.report_outputs
    };
  }

  function jsonReport(diagnosis) {
    const finalDiagnosis = normalizeFinalDiagnosis(diagnosis);
    return JSON.stringify(
      {
        ...finalDiagnosis,
        structured_diagnosis_preview: structuredPreview(finalDiagnosis)
      },
      null,
      2
    );
  }

  function analyzeDispute(input) {
    return diagnose(input);
  }

  function computeEvaluationMetrics(input, diagnosis) {
    const finalDiagnosis = normalizeFinalDiagnosis(diagnosis);
    const requiredFields = [
      "contractText",
      "disputeDescription",
      "claimantPosition",
      "respondentPosition",
      "evidence",
      "desiredOutcome"
    ];
    const completed = requiredFields.filter((field) => input[field] && input[field].length >= 12);
    const inputCompleteness = Math.round((completed.length / requiredFields.length) * 100);
    const evidenceGapCount = finalDiagnosis.evidence_gaps.filter(
      (gap) => !normalize(gap).startsWith("no obvious")
    ).length;
    const clauseSignalCount = finalDiagnosis.relevant_clause_signals.filter(
      (signal) => !normalize(signal).startsWith("no strong")
    ).length;
    const detectedIssueCount = finalDiagnosis.key_issues.filter(
      (issue) => !normalize(issue).includes("unclear")
    ).length;
    const evidenceSignals = countGroup(input.evidence, "evidence") + dateSignalCount(input.evidence);
    const evidenceCoverage =
      evidenceGapCount === 0
        ? "Strong"
        : evidenceSignals >= 4 && evidenceGapCount <= 2
          ? "Good"
          : evidenceSignals >= 2
            ? "Partial"
            : "Thin";
    const structuredOutputReady =
      inputCompleteness >= 50 && detectedIssueCount > 0 && clauseSignalCount > 0
        ? "Ready"
        : "Needs more input";
    const markdownReady = diagnosis ? "Ready" : "Pending";
    const jsonReady = diagnosis ? "Ready" : "Pending";
    const suggestedGoldenCase = caseNameFor(input, finalDiagnosis);

    return {
      inputCompleteness,
      evidenceCoverage,
      detectedIssueCount,
      clauseSignalCount,
      evidenceGapCount,
      riskSignal: finalDiagnosis.risk_signal,
      structuredOutputReady,
      markdownReady,
      jsonReady,
      suggestedGoldenCase,
      ruleChecksPassed: [
        inputCompleteness >= 50 ? "input_fixture_shape" : "input_fixture_needs_more_fields",
        clauseSignalCount > 0 ? "clause_signal_detected" : "clause_signal_missing",
        detectedIssueCount > 0 ? "expected_issue_detected" : "expected_issue_unclear",
        markdownReady === "Ready" ? "markdown_export_ready" : "markdown_export_pending",
        jsonReady === "Ready" ? "json_export_ready" : "json_export_pending"
      ]
    };
  }

  function buildTestCasePreview(input, diagnosis, metrics) {
    const finalDiagnosis = normalizeFinalDiagnosis(diagnosis);
    return {
      case_name: metrics.suggestedGoldenCase,
      contract_type: input.contractType || "Other",
      dispute_type: finalDiagnosis.case_type,
      risk_mode: input.riskMode || "Balanced",
      input_fixture: {
        has_contract_text: Boolean(input.contractText),
        has_dispute_description: Boolean(input.disputeDescription),
        has_party_positions: Boolean(input.claimantPosition && input.respondentPosition),
        has_evidence: Boolean(input.evidence)
      },
      expected_outputs: {
        must_include_issues: finalDiagnosis.active_issue_tags.filter((tag) => tag !== "unclear"),
        must_include_evidence_gaps: [...finalDiagnosis.evidence_gaps],
        minimum_clause_signals: metrics.clauseSignalCount,
        risk_signal: finalDiagnosis.risk_signal
      },
      evaluation_checks: {
        input_completeness: `${metrics.inputCompleteness}%`,
        evidence_coverage: metrics.evidenceCoverage,
        structured_output: metrics.structuredOutputReady,
        markdown_export: metrics.markdownReady,
        json_export: metrics.jsonReady,
        golden_style_checks: metrics.ruleChecksPassed
      }
    };
  }

  function buildEvaluationPreview(input, diagnosis) {
    const finalDiagnosis = normalizeFinalDiagnosis(diagnosis);
    const metrics = computeEvaluationMetrics(input, finalDiagnosis);
    return {
      metrics,
      testCase: buildTestCasePreview(input, finalDiagnosis, metrics)
    };
  }

  function renderEvaluationPanel(metrics, testCase) {
    if (!evaluationOutput) {
      return;
    }

    latestTestCase = JSON.stringify(testCase, null, 2);
    evaluationOutput.innerHTML = [
      '<div class="score-grid">',
      scoreCard("Input Completeness", `${metrics.inputCompleteness}%`, "Fixture field coverage"),
      scoreCard("Evidence Coverage", metrics.evidenceCoverage, `${metrics.evidenceGapCount} gap(s)`),
      scoreCard("Detected Issues", metrics.detectedIssueCount, "Stable issue count"),
      scoreCard("Clause Signals", metrics.clauseSignalCount, "Relevant clause families"),
      scoreCard("Risk Signal", metrics.riskSignal, "Deterministic risk label"),
      scoreCard("Export Readiness", `${metrics.markdownReady} / ${metrics.jsonReady}`, "Markdown / JSON export"),
      "</div>",
      '<section class="evaluation-block">',
      "<h4>Generated Test Case Preview</h4>",
      `<pre class="preview-code"><code>${escapeHtml(latestTestCase)}</code></pre>`,
      "</section>",
      '<section class="evaluation-block">',
      "<h4>What this maps to in pytest</h4>",
      '<ul class="quality-list">',
      "<li>Golden tests compare stable categories, strictness, affected parts, and cause substrings.</li>",
      "<li>Report tests protect Markdown and structured JSON-style output shape.</li>",
      "<li>CLI smoke tests protect local commands such as diagnose, check-all, and why.</li>",
      "<li>GitHub Pages static tests protect this demo, relative assets, copy actions, and no-backend behavior.</li>",
      "</ul>",
      "</section>"
    ].join("");
  }

  function scoreCard(label, value, detail) {
    return [
      '<article class="score-card">',
      `<span>${escapeHtml(label)}</span>`,
      `<strong>${escapeHtml(value)}</strong>`,
      `<small>${escapeHtml(detail)}</small>`,
      "</article>"
    ].join("");
  }

  function caseNameFor(input, diagnosis) {
    const finalDiagnosis = normalizeFinalDiagnosis(diagnosis);
    const activeTags = finalDiagnosis.active_issue_tags.filter((tag) => normalize(tag) !== "unclear");
    let caseTags = activeTags.filter((tag) => !hasAny(tag, ["notice", "damages", "liability limitation", "liability cap carve-out"]));
    if (hasTag(activeTags, "confidentiality") && hasTag(activeTags, "indemnity")) {
      caseTags = ["confidentiality", "indemnity"];
    } else if (hasTag(activeTags, "force majeure") && hasTag(activeTags, "delivery")) {
      caseTags = ["force majeure", "delivery"];
    } else if (hasLeaseActiveIssue(activeTags)) {
      caseTags = ["repair", "notice", "abatement", "deposit"];
    } else if (hasTag(activeTags, "refund")) {
      caseTags = ["refund"].concat(activeTags.filter((tag) => hasAny(tag, ["termination", "acceptance"])));
    }
    const tagLimit = hasLeaseActiveIssue(activeTags) ? 4 : 3;
    const source = [
      input.contractType,
      ...caseTags.slice(0, tagLimit),
      "golden"
    ].join(" ");
    return source
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .slice(0, 80) || "custom_dispute_case";
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

  function render(diagnosis, input) {
    const currentInput = input || collectInput();
    const finalDiagnosis = normalizeFinalDiagnosis(diagnosis);
    latestDiagnosis = finalDiagnosis;
    latestMarkdown = markdownReport(finalDiagnosis);
    latestJson = jsonReport(finalDiagnosis);
    const evaluationPreview = buildEvaluationPreview(currentInput, finalDiagnosis);
    const metrics = evaluationPreview.metrics;
    const testCase = evaluationPreview.testCase;

    riskBadge.className = `risk-badge risk-${finalDiagnosis.risk_signal}`;
    riskBadge.textContent = finalDiagnosis.risk_signal;

    resultOutput.innerHTML = [
      `<section class="result-block"><h4>Dispute summary</h4><p>${escapeHtml(finalDiagnosis.dispute_summary)}</p></section>`,
      `<section class="result-block"><h4>Detected contract/dispute type</h4>${tagsHtml([
        finalDiagnosis.contract_type,
        finalDiagnosis.dispute_type
      ])}</section>`,
      `<section class="result-block"><h4>Active issue tags</h4>${tagsHtml(finalDiagnosis.active_issue_tags)}</section>`,
      `<section class="result-block"><h4>Key issues</h4>${listHtml(finalDiagnosis.key_issues, "issue-list")}</section>`,
      `<section class="result-block"><h4>Relevant clauses or clause signals</h4>${listHtml(finalDiagnosis.clause_signals, "issue-list")}</section>`,
      `<section class="result-block"><h4>Timeline facts</h4>${listHtml(finalDiagnosis.timeline_facts, "issue-list")}</section>`,
      `<section class="result-block"><h4>Claimant vs respondent position matrix</h4><div class="matrix"><div><strong>Claimant</strong><p>${escapeHtml(finalDiagnosis.position_matrix.claimant)}</p></div><div><strong>Respondent</strong><p>${escapeHtml(finalDiagnosis.position_matrix.respondent)}</p></div></div><p><strong>Contested facts:</strong> ${escapeHtml(finalDiagnosis.position_matrix.contested_facts.join("; "))}</p></section>`,
      `<section class="result-block"><h4>Evidence gaps</h4>${listHtml(finalDiagnosis.evidence_gaps, "gap-list")}</section>`,
      `<section class="result-block"><h4>Risk signal</h4><p>${escapeHtml(finalDiagnosis.risk_signal)} risk under ${escapeHtml(finalDiagnosis.risk_mode)} mode.</p>${listHtml(finalDiagnosis.risk.rationale, "gap-list")}</section>`,
      `<section class="result-block"><h4>Suggested next steps</h4>${listHtml(finalDiagnosis.suggested_next_steps, "next-step-list")}</section>`,
      `<section class="result-block"><h4>Structured diagnosis preview</h4><pre class="preview-code"><code>${escapeHtml(JSON.stringify(structuredPreview(finalDiagnosis), null, 2))}</code></pre></section>`,
      `<section class="result-block"><h4>Markdown-style report preview</h4><pre class="preview-code"><code>${escapeHtml(latestMarkdown)}</code></pre></section>`,
      `<section class="result-block"><h4>JSON-style output preview</h4><pre class="preview-code"><code>${escapeHtml(latestJson)}</code></pre></section>`
    ].join("");
    renderEvaluationPanel(metrics, testCase);
  }

  function clearResult() {
    latestDiagnosis = null;
    latestMarkdown = "";
    latestJson = "";
    latestTestCase = "";
    riskBadge.className = "risk-badge risk-unclear";
    riskBadge.textContent = "Unclear";
    resultOutput.innerHTML =
      '<div class="empty-state"><strong>Load a sample or enter a dispute, then run Analyze.</strong><p>The result panel will show a summary, issue tags, clause signals, evidence gaps, risk, next steps, Markdown, and JSON.</p></div>';
    if (evaluationOutput) {
      evaluationOutput.innerHTML =
        '<div class="empty-state"><strong>Evaluation metrics will appear here.</strong><p>Run Analyze to see Input Completeness, Evidence Coverage, Detected Issues, Clause Signals, Risk Signal, Markdown/JSON export readiness, and a Generated Test Case Preview.</p></div>';
    }
  }

  async function copyText(kind) {
    const values = {
      json: latestJson,
      markdown: latestMarkdown,
      "test-case": latestTestCase
    };
    const labels = {
      json: "JSON",
      markdown: "Markdown",
      "test-case": "test case JSON"
    };
    const value = values[kind] || "";
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
      copyStatus.textContent = `Copied ${labels[kind] || kind} output.`;
    } catch (error) {
      copyStatus.textContent = `Copy failed. Select the ${labels[kind] || kind} preview manually.`;
    }
  }

  if (typeof window !== "undefined") {
    window.Contract2AgentPlayground = {
      analyzeDispute,
      diagnose,
      markdownReport,
      structuredPreview,
      computeEvaluationMetrics,
      buildTestCasePreview,
      caseNameFor
    };
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    copyStatus.textContent = "";
    const input = collectInput();
    render(analyzeDispute(input), input);
  });

  document.getElementById("load-sample").addEventListener("click", () => {
    loadSample(document.getElementById("sample-select").value);
    const input = collectInput();
    render(analyzeDispute(input), input);
  });

  document.querySelectorAll(".sample-chip").forEach((button) => {
    button.addEventListener("click", () => {
      loadSample(button.dataset.sample);
      const input = collectInput();
      render(analyzeDispute(input), input);
    });
  });

  document.getElementById("copy-markdown").addEventListener("click", () => copyText("markdown"));
  document.getElementById("copy-json").addEventListener("click", () => copyText("json"));
  document.getElementById("copy-test-case").addEventListener("click", () => copyText("test-case"));
  document.getElementById("reset-form").addEventListener("click", () => {
    form.reset();
    document.querySelectorAll(".sample-chip").forEach((button) => button.classList.remove("is-active"));
    copyStatus.textContent = "Cleared inputs.";
    clearResult();
  });

  loadSample("service-payment");
  render(analyzeDispute(collectInput()), collectInput());
})();
