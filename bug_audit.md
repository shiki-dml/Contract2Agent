# Contract2Agent Bug Audit

## 2026-05-05 Force Majeure Blocker Follow-Up

### Symptom

The Sales Contract clause-only fixture could still surface force majeure outside `clause_signals` when the desired outcome mentioned force majeure notice or mitigation, even though the factual fields denied force majeure notice, government order, natural disaster, port closure, strike, war, emergency closure, extraordinary external event, and identified ordinary staffing/vendor backlog facts.

### Root cause

The exact active path was `deriveActiveIssueTags` -> `shouldActivateIssueFamily` -> `familyBlocked(data, family, activeTrigger)`. `familyBlocked` intentionally returned `false` whenever `activeTrigger` was truthy, so force majeure blockers were skipped after a phrase such as `force majeure notice` made `triggers.forceMajeure` true. A second visible leak came from `buildNextSteps`, which echoed `desiredOutcome` verbatim even when force majeure had been blocked from active tags.

### Files changed

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### Fix summary

- Added `hasFamilyBlocker(data, family)` and made `shouldActivateIssueFamily` always enforce it for `force_majeure`.
- Added `addDesiredOutcomeStep` so a blocked, inactive force majeure phrase in `desiredOutcome` is not reintroduced into suggested next steps.
- Kept force majeure clause detection intact; force majeure can still appear in `clause_signals`.

### Regression test

- Updated `test_playground_force_majeure_clause_only_stays_clause_signal` so the Sales fixture includes a desired-outcome force majeure phrase plus explicit negative facts.
- The test asserts force majeure remains clause-signal-only and is absent from `active_issue_tags`, `dispute_type`, risk rationale, suggested next steps, Evaluation Lab `case_name`, and Evaluation Lab `must_include_issues`.

### Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `python -m pytest tests\test_docs_site.py::test_playground_force_majeure_clause_only_stays_clause_signal` | Passed | 1 passed after the targeted fix. |
| `python -m pytest` | Passed | 260 passed in 20.94s on the final run. |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript parses successfully. |

### Remaining follow-ups

This was intentionally narrow. Other issue-family blockers still use the existing `familyBlocked(data, family, positiveTrigger)` behavior unless a concrete regression shows the same blocker-after-positive-trigger failure.

## 2026-05-05 Clause Signal vs Active Issue Separation

### Symptom

Contract clauses could be promoted into active disputes. A clause-only family could then flow through the final diagnosis into `active_issue_tags`, `dispute_type`, key issues, risk rationale, suggested next steps, Markdown/JSON exports, and Evaluation Lab `expected_outputs.must_include_issues`.

### Examples observed

- Force majeure clause-only false positive: a Sales Contract force majeure clause plus facts denying force majeure notice, government order, natural disaster, port closure, strike, war, emergency closure, and extraordinary external event could still be at risk of activating force majeure through broad factual matching.
- Invoice/payment false positive: invoice dates or invoice evidence, such as an alternative supplier invoice used to prove cover costs, could be treated as an invoice dispute even without an unpaid invoice, disputed invoice, billing dispute, or invoice nonpayment.
- Other clause-only families covered by regressions: confidentiality, indemnity, and liquidated damages now remain clause signals unless factual fields show an actual disclosure, tender/third-party claim, or liquidated-damages demand/penalty dispute.

### Root cause

The active-trigger layer did not have one explicit gate separating contract clause text from factual issue activation. `factText` included the selected dispute type, some active trigger lists included clause-like terms such as `invoice date` or generic `liquidated damages`, and `deriveActiveIssueTags` had repeated ad hoc checks instead of a shared issue-family activation rule. This allowed clause context or evidence labels to look like active disputes.

### Files inspected

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### Files changed

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### New helper/gate functions

- `activeTriggerText(data)` defines the factual activation source: desired outcome, dispute description, claimant position, respondent position, evidence, and metadata. It excludes contract text and the selected dispute type label.
- `shouldActivateIssueFamily(data, family, clauseSignals, activeTrigger, clausePhrases, options)` is the active issue gate used by `deriveActiveIssueTags`.

### Active triggers vs clause triggers

Clause triggers still come from `buildClauseSignals(data)` and may be detected from contract text alone. Active triggers now come from factual fields through `hasIssueFactTrigger` and family-specific helpers. A clause signal may support the analysis, but it does not by itself create an active issue tag.

### Blocker triggers

Blocker and negative terms remain in the issue-family registry and are evaluated against factual activation text. The force majeure registry now includes explicit blockers such as no force majeure notice, no government order, no natural disaster, no port closure, no strike, no war, no emergency closure, no extraordinary external event, and ordinary backlog/staffing-only facts. Confidentiality, indemnity, invoice dispute, and liquidated-damages blockers were tightened as well.

### Exports and Evaluation Lab

The prior final diagnosis source-of-truth path is preserved. Markdown, JSON, structured preview, risk rationale, suggested next steps, and Evaluation Lab preview still consume `finalDiagnosis`; because `active_issue_tags` is now filtered at the activation gate, clause-only families remain in `clause_signals` and do not appear in legacy `issue_tags` or Evaluation Lab `must_include_issues`.

### Regression tests added

- `test_playground_force_majeure_clause_only_stays_clause_signal`
- `test_playground_positive_force_majeure_still_activates`
- `test_playground_confidentiality_and_indemnity_clause_only_stay_clause_signals`
- `test_playground_liquidated_damages_requires_active_remedy_or_dispute`
- `test_playground_liability_limitation_active_when_damages_are_disputed`
- `test_playground_alternative_supplier_invoice_is_not_invoice_dispute`
- `test_playground_clause_active_separation_survives_sequential_runs`

### Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `Test-Path package.json` | Passed | Returned `False`; no npm project is present, so `npm test`, `npm run build`, `npm run lint`, and `npm run typecheck` are not applicable. |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript parses successfully. |
| `python -m pytest tests\test_docs_site.py` | Passed | 47 passed in 4.41s on the final focused docs-site run. |
| `python -m pytest` | Passed | 260 passed in 21.78s. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully. |
| `git diff --check` | Passed | No whitespace errors. |
| `git status --short` | Passed | Only `bug_audit.md`, `docs/assets/app.js`, and `tests/test_docs_site.py` are modified. |

### Results

- Clause text alone no longer creates active issue tags in the covered families.
- Force majeure positive facts still activate force majeure.
- Confidentiality and indemnity clause-only facts remain clause signals only.
- Liquidated damages activates when sought or contested, not from the clause alone.
- Liability limitation activates when damages/cap recovery is actually disputed.
- Alternative supplier invoice evidence does not activate invoice dispute or invoice-dispute timeline/gap templates.
- Cross-run regression coverage verifies a positive force majeure run does not leak active force majeure templates into a later clause-only run.

### Remaining follow-ups

This patch focuses on the clause-signal/active-issue separation layer for the issue families covered by the requested examples. Deeper semantic tuning may still be needed for less-covered families such as termination, audit rights, complex payment allocation, sales acceptance, or issue-specific jurisdictional nuances.

## 2026-05-05 Final Diagnosis Source-of-Truth Audit

### Symptom

Multiple playground output surfaces could diverge or reuse stale/pre-filtered diagnosis data. The risk display, suggested next steps, Markdown export, JSON export, structured preview, and Evaluation Lab preview all accepted diagnosis-shaped data, but there was no explicit final normalized diagnosis boundary that every output path was required to consume.

### Root cause

The static playground produced a diagnosis object after raw detection, but final filtering, compatibility aliases, risk rationale, next-step generation, export JSON assembly, and Evaluation Lab expected-output generation were not guarded by a single canonical normalization step. Several functions already consumed a passed diagnosis object, but they could still receive partially normalized fields or legacy aliases, and `render` assembled JSON inline instead of using a final-diagnosis export builder. `buildNextSteps` also preferred legacy camelCase aliases, which made it easier for stale or pre-final state to drive user-visible steps.

### Field-generation audit

| Field or surface | Canonical source after this patch |
| --- | --- |
| `contract_type` | `detectContractTypes` in `diagnose`, then normalized by `normalizeFinalDiagnosis`. |
| `dispute_type` | `detectDisputeTypes` in `diagnose`, then normalized from `dispute_types` by `normalizeFinalDiagnosis`. |
| `active_issue_tags` | `deriveActiveIssueTags` in `diagnose`, then deduplicated and filtered by `normalizeFinalDiagnosis`. |
| `issue_tags` | Legacy compatibility field created by `normalizeFinalDiagnosis`; it mirrors `active_issue_tags`. |
| `clause_signals` | `buildClauseSignals` in `diagnose`, then normalized by `normalizeFinalDiagnosis`. |
| `key_issues` | `buildIssues` receives the preliminary normalized diagnosis fields and is normalized into the final diagnosis. |
| `timeline_facts` | `extractTimelineFacts` in `diagnose`, then normalized by `normalizeFinalDiagnosis`. |
| `evidence_gaps` | `buildEvidenceGaps` in `diagnose`, then normalized by `normalizeFinalDiagnosis`. |
| Risk level | `scoreRisk` receives normalized active issues, evidence gaps, and timeline facts; `normalizeFinalDiagnosis` stores it in `risk.level`. |
| Risk rationale | `scoreRisk` builds it from final active issues, evidence gaps, and timeline facts before final normalization. |
| `critical_evidence_gaps` | `scoreRisk` produces them from normalized gaps, and `normalizeFinalDiagnosis` clones them under `risk`. |
| `suggested_next_steps` | `buildNextSteps(data, finalDiagnosis)` runs after risk/key issue normalization and is stored back into `finalDiagnosis`. |
| Structured diagnosis preview | `structuredPreview(finalDiagnosis)`. |
| Markdown report preview/export | `markdownReport(finalDiagnosis)`. |
| JSON-style output preview/export | `jsonReport(finalDiagnosis)`. |
| Evaluation Lab generated test preview | `buildEvaluationPreview(input, finalDiagnosis)`, which calls `computeEvaluationMetrics` and `buildTestCasePreview`. |
| Evaluation Lab `must_include_issues` | `buildTestCasePreview` copies from `finalDiagnosis.active_issue_tags`. |
| Evaluation Lab `must_include_evidence_gaps` | `buildTestCasePreview` copies from `finalDiagnosis.evidence_gaps`. |
| Evaluation Lab `risk_signal` | `buildTestCasePreview` copies from `finalDiagnosis.risk_signal`. |
| Evaluation Lab `case_name` | `caseNameFor` normalizes its diagnosis input and derives the name from final active issue tags only. |

### Files inspected

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### Files changed

- `docs/assets/app.js`
- `tests/test_docs_site.py`
- `bug_audit.md`

### How `finalDiagnosis` is produced

`diagnose` now runs raw deterministic detection first, then creates `finalDiagnosis` through `normalizeFinalDiagnosis`. Key issues and risk are generated from that normalized object, the object is normalized again, suggested next steps are generated from `finalDiagnosis`, and a final normalization pass returns the canonical result. This keeps raw signals upstream and makes the returned diagnosis the source of truth for all user-visible and export-visible fields.

### Output builders now consuming `finalDiagnosis`

- `render`
- `markdownReport`
- `jsonReport`
- `structuredPreview`
- `computeEvaluationMetrics`
- `buildTestCasePreview`
- `buildEvaluationPreview`
- `caseNameFor`

### Legacy compatibility

`normalizeFinalDiagnosis` preserves compatibility fields while making them canonical aliases. `issue_tags` is always a fresh clone of `active_issue_tags`, `relevant_clause_signals` mirrors `clause_signals`, `dispute_type` is derived from `dispute_types`, and `risk_signal` mirrors `risk.level`.

### Fresh per-run state

Every `diagnose` call creates a new `finalDiagnosis` object. `normalizeFinalDiagnosis` clones arrays and nested objects, removes empty strings, deduplicates values with stable ordering, and avoids mutating shared template/default arrays. Output builders normalize their input before rendering, so a caller cannot accidentally export a stale intermediate object.

### Tests added or updated

- Updated `_run_playground_diagnosis` to exercise the rendered copy/export path for Markdown, JSON, and Evaluation Lab generated test cases.
- Added `test_playground_final_diagnosis_is_source_for_json_and_markdown_exports`.
- Added `test_playground_evaluation_preview_uses_final_diagnosis`.
- Added `test_playground_no_post_final_regeneration_of_active_issues`.
- Added `test_playground_final_diagnosis_runs_have_fresh_state`.

### Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `Test-Path package.json` | Passed | Returned `False`; no npm project is present, so `npm install`, `npm test`, `npm run build`, `npm run lint`, and `npm run typecheck` are not applicable. |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript parses successfully. |
| `python -m pytest tests\test_docs_site.py` | Passed | 40 passed in 3.82s on the final focused docs-site regression run. |
| `python -m pytest` | Passed | 253 passed in 19.69s on the final full run. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully after the final `docs/assets/app.js` and audit edits. |
| `git diff --check` | Passed | No whitespace errors. |
| `git status --short` | Passed | Only `bug_audit.md`, `docs/assets/app.js`, and `tests/test_docs_site.py` are modified. |

### Results

- The returned `finalDiagnosis` is now the single source used by UI preview, Markdown export, JSON export, risk display, suggested next steps, and Evaluation Lab preview.
- JSON `issue_tags` mirrors `active_issue_tags` after final filtering.
- Markdown and JSON active issues, key issues, timeline facts, evidence gaps, and suggested next steps match the final diagnosis object.
- Evaluation Lab `expected_outputs.must_include_issues`, `must_include_evidence_gaps`, `risk_signal`, and case naming derive from the final diagnosis.
- Sequential diagnosis runs are covered by a regression test that checks arrays and generated text do not inherit stale values from a prior fixture.

### Remaining follow-ups

- This patch centralizes the diagnosis source of truth. It intentionally does not fully redesign semantic issue-family trigger gates.
- Force majeure, invoice dispute, lease, sales, SaaS/SLA, refund, indemnity, confidentiality, and IP trigger rules may still need separate semantic follow-up when a false positive or false negative comes from raw detection rather than post-final output construction.

## 2026-05-05 Playground Deterministic Diagnosis Bug Catalog and Verification

### Scope

- Area: static GitHub Pages playground diagnosis in `docs/assets/app.js`.
- Goal: keep clause signals separate from active issue tags, block denied force majeure facts, preserve lease-specific active issues, prevent stale template contamination, and keep UI, Markdown, JSON, and Evaluation Lab preview aligned with the final filtered diagnosis.
- Non-goals respected: no backend, no browser runtime network calls, no route/styling/navigation/sample-loading/copy-button/export-button changes, no external API dependencies, and no global deletion of issue families.

### Structured bug catalog

#### PG-DIAG-001: force majeure false positive

- Symptom: a contract containing a force majeure clause could produce an active `force majeure` issue even when facts denied government orders, natural disasters, strikes, war, or other external uncontrollable events.
- Root cause: clause terms and factual invocation terms were previously too easy to conflate.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: force majeure remains a clause signal unless non-blocked facts invoke an external event; blocker triggers run before active issue generation.
- Tests: `test_playground_force_majeure_clause_signal_is_not_active_issue`, `test_playground_late_delivery_blocks_denied_force_majeure_issue`, and positive force-majeure tests.

#### PG-DIAG-002: clause signal vs active issue separation

- Symptom: clause-only concepts such as indemnity, confidentiality, force majeure, SLA, refund, or liquidated damages could leak into active issue tags and downstream previews.
- Root cause: issue-family detection mixed contract clause terms, dropdown/default categories, and fact terms.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: active triggers, clause triggers, negative triggers, and blocker terms are evaluated separately; `issue_tags` mirrors final filtered `active_issue_tags`.
- Tests: static playground structured-output, export, refund, confidentiality/IP, force-majeure, and lease tests.

#### PG-DIAG-003: missing lease active issues

- Symptom: the lease repair / notice / rent abatement / security deposit fixture could miss repair obligation, rent abatement, rent withholding/payment default, security deposit, tenant-caused damage, property damage causation, damages, and liability limitation.
- Root cause: the issue-family registry lacked lease-specific active and clause gates.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: lease maintenance, rent abatement, rent withholding, security deposit, tenant damage, and property-damage causation families are detected through lease-specific fact and clause signals.
- Tests: `test_playground_lease_repair_abatement_filters_false_issue_families`.

#### PG-DIAG-004: stale key issue and next-step template contamination

- Symptom: unrelated SaaS, SLA, invoice, refund, force majeure, indemnity, confidentiality, IP, liquidated-damages, cover-cost, and lost-revenue boilerplate could appear in lease output.
- Root cause: generic output builders ran after broad tags had been activated or when no scoped family branch existed.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: lease, force-majeure, refund/termination/acceptance, and confidentiality/IP branches return scoped key issues, evidence gaps, next steps, and risk rationale from final active tags.
- Tests: lease key issue, next-step/export, refund, confidentiality/IP, positive force-majeure, and cross-contamination tests.

#### PG-DIAG-005: timeline role classification

- Symptom: timeline output could fall back to generic notice/deemed-receipt text instead of classifying dated facts by role.
- Root cause: generic notice extraction did not know lease, refund, force majeure, and confidentiality/IP roles.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: timeline extractors classify dates as tenant notice, landlord response, contractor inspection, rent withholding, repair completion, move-out/surrender, force-majeure order/notice, refund milestones, and confidentiality/IP events.
- Tests: lease, refund, positive force majeure, and confidentiality/IP timeline assertions.

#### PG-DIAG-006: Evaluation Lab preview contamination

- Symptom: generated test-case previews could be named or populated from stale/default/unfiltered state.
- Root cause: previews needed to derive `case_name` and `must_include_issues` from the final filtered diagnosis; export readiness also referenced module-level latest export strings.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: preview expected issues use `diagnosis.active_issue_tags`; case naming uses filtered tags; export readiness now derives from the current diagnosis object rather than `latestMarkdown`/`latestJson`.
- Tests: lease, confidentiality/IP, export consistency, and cross-contamination preview assertions.

#### PG-DIAG-007: Markdown/JSON export consistency

- Symptom: Markdown, JSON, UI diagnosis, and Evaluation Lab preview could diverge if one path used stale or unfiltered fields.
- Root cause: legacy aliases and preview state needed to point at the final diagnosis object.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: `active_issue_tags`, legacy `issue_tags`, key issues, clause signals, evidence gaps, timeline facts, risk rationale, and suggested next steps are copied from the final filtered diagnosis for export paths.
- Tests: SaaS, late-delivery force-majeure-negative, positive force-majeure, refund, confidentiality/IP, and lease export parity tests.

#### PG-DIAG-008: cross-run stale state prevention

- Symptom: running a force-majeure, SaaS/SLA, refund, or confidentiality/IP fixture before the lease fixture could leak prior issue templates.
- Root cause: shared browser module state and mutable output arrays needed stronger isolation from per-run diagnosis data.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: each diagnosis builds fresh arrays and clones legacy aliases; Evaluation Lab previews derive from the passed diagnosis.
- Tests: `test_playground_diagnosis_runs_do_not_cross_contaminate_issue_templates`.

#### PG-DIAG-009: exact lease fixture literals in generated evidence gaps

- Symptom: lease evidence gaps still included `September 4` and `$8,500` as literal fallback text.
- Root cause: the lease evidence-gap branch had fixture-specific strings instead of using extracted notice date and deposit amount values.
- Files affected: `docs/assets/app.js`; regression coverage in `tests/test_docs_site.py`.
- Fix summary: notice date, email label, repair cure period, deposit deduction amount, and deposit statement period now come from `extractLeaseTimeline`; the `September 4` trigger literal was replaced with generic repair/maintenance/tenant notice triggers.
- Tests: added `test_playground_lease_evidence_gaps_use_extracted_values_not_fixture_literals`.

### Files changed in this pass

- `docs/assets/app.js`
  - Generalized lease evidence-gap labels to use extracted values rather than fixed fixture literals.
  - Removed the hard-coded `september 4 notice` trigger in favor of generic repair, maintenance, and tenant notice signals.
  - Made Evaluation Lab export readiness derive from the current diagnosis object rather than stale module-level export strings.
- `tests/test_docs_site.py`
  - Added a lease regression variant that changes dates and the security-deposit deduction amount and asserts generated outputs follow the new values.
- `bug_audit.md`
  - Added this structured catalog and current verification record.

### Commands run and results

| Command | Result | Notes |
| --- | --- | --- |
| `Test-Path package.json` | Passed, returned `False` | No npm project is present, so `npm install`, `npm test`, `npm run build`, `npm run lint`, and `npm run typecheck` are not applicable. |
| `Test-Path mkdocs.yml` | Passed, returned `True` | Strict MkDocs build command exists in repo context. |
| `Test-Path scripts\check_docs_links.py` | Passed, returned `True` | Static docs link checker exists. |
| `Test-Path tests` | Passed, returned `True` | Pytest suite exists. |
| `git diff --check` | Passed | No whitespace errors after the production and test patches. |
| `node --check docs\assets\app.js` | Blocked by approval timeout | Attempted twice; automatic permission approval review did not finish before its deadline. |
| `python -m pytest tests\test_docs_site.py` | Blocked by approval timeout | Attempted before and after patching; automatic permission approval review did not finish before its deadline. |
| `python -m pytest` | Blocked by approval timeout | Attempted twice; automatic permission approval review did not finish before its deadline. |
| `python -m compileall -q contract2agent tests scripts` | Blocked by approval timeout | Attempted twice; automatic permission approval review did not finish before its deadline. |
| `python scripts\check_docs_links.py` | Blocked by approval timeout | Attempted twice; automatic permission approval review did not finish before its deadline. |
| `python -m mkdocs build --strict` | Blocked by approval timeout | Attempted twice; automatic permission approval review did not finish before its deadline. |

### Verification results

- Verified by diff inspection that only `docs/assets/app.js`, `tests/test_docs_site.py`, and `bug_audit.md` are modified.
- Verified by `git diff --check` that the patch has no whitespace errors.
- Verified by source inspection that lease evidence-gap dates and dollar amounts are derived from extracted values rather than unconditional fixture literals.
- Full executable verification is still pending because Python and Node execution approval timed out in this session.

### Remaining limitations and follow-ups

- The playground remains a deterministic static analyzer and depends on explicit textual triggers.
- Business-day arithmetic is still described as an evidence-dependent calculation rather than computed.
- Re-run `node --check docs\assets\app.js`, `python -m pytest tests\test_docs_site.py`, `python -m pytest`, `python -m compileall -q contract2agent tests scripts`, `python scripts\check_docs_links.py`, and `python -m mkdocs build --strict` in an environment where command execution is approved.

## 2026-05-04 Lease Repair / Rent Abatement / Security Deposit Trigger-Gate Follow-Up

### 1. What was wrong

- The deterministic playground analyzer still handled a lease repair dispute through generic notice/cure, damages, invoice/payment, SaaS/SLA, and force-majeure template paths.
- A force majeure clause mention plus negative fact text could still contaminate active issue outputs, dispute type, key issues, next steps, Evaluation Lab preview, and exports.
- Lease-specific facts for roof repair, rent abatement, rent withholding, security deposit deductions, tenant-caused damage, property-damage causation, and base-rent liability limits were under-detected.

### 2. Root cause

- Clause signals and factual issue activation were still not separated for the lease family.
- Existing issue-family gates covered prior SaaS, refund, force majeure, and confidentiality/IP regressions, but there was no lease issue-family registry or lease-specific generation path.
- The generic notice/cure branch assumed invoice, suspension, order-form, or service-platform context.
- The generic damages branch could emit lost-revenue wording whenever damages exclusions appeared, even when the facts requested display-fixture damages, rent abatement, deposit return, and repair-related remedies.
- Evaluation Lab case naming used filtered active tags, but without a lease-specific case-name path it could still choose misleading generic families when active tags were wrong.

### 3. Why force majeure was incorrectly activated

- The contract contained a force majeure clause, and the fixture's negative sentence listed government orders, natural disasters, strikes, war, and force majeure events.
- The correct behavior is clause-only: those terms are clause signals unless a party invokes force majeure, sends force-majeure notice, or claims delay/nonperformance was caused by an external uncontrollable event.
- The fix keeps force majeure as `force majeure clause mentioned but not fact-triggered` and relies on blocker triggers to prevent active issue, dispute type, key issue, next-step, Evaluation Lab, and export activation.

### 4. Why lease-specific issues were missing

- There were no explicit lease-family gates for landlord maintenance, commercially reasonable repairs, rent abatement, unauthorized rent withholding/payment default, security deposit deductions, ordinary wear and tear, tenant-caused damage, or property-damage causation.
- Rent withholding was too easy to confuse with generic payment/invoice disputes, even though lease rent withholding is not an invoice dispute.
- Liability-cap extraction did not preserve the lease-specific `twelve months of base rent` language.

### 5. Trigger-gate changes

- Added lease issue families in `docs/assets/app.js`:
  - `lease_maintenance`
  - `rent_abatement`
  - `rent_withholding`
  - `security_deposit`
  - `tenant_damage`
- Added lease factual trigger helpers for:
  - lease maintenance / repair obligation
  - rent abatement
  - rent withholding / payment default
  - security deposit
  - tenant-caused damage
  - property damage causation
- Added clause signals for lease schedule notice addresses, email plus certified mail notice, 10-business-day repair cure period, commercially reasonable repairs, rent abatement by affected period/area, unauthorized rent withholding as payment default, deposit deductions, itemized deposit statement timing, ordinary wear and tear, base-rent liability cap, and unpaid-rent / intentional-misconduct / tenant-caused-property-damage carve-outs.
- Kept rent withholding separate from generic `payment` and `invoice dispute` active tags.

### 6. Timeline role classification

- Added lease timeline extraction for:
  - September 3 water-intrusion discovery.
  - September 4 tenant email notice.
  - September 7 landlord response.
  - September 15 roof contractor inspection.
  - October rent withholding.
  - October 12 roof repair completion.
  - November 1 move-out / surrender.
  - 30-day deposit statement deadline.
  - 10-business-day repair cure period.
  - email plus certified-mail deemed receipt rule.
- The lease path returns role-specific timeline facts instead of falling through to generic notice/deemed-receipt text.

### 7. Key issues, gaps, next steps, and risk

- Added lease-specific key issues for notice method, lease schedule address, deemed receipt, cure period, commercially reasonable repair start, September 15 inspection, October 12 completion, material interference, rent abatement, 40% October rent withholding, $8,500 deposit deduction, roof-leak versus tenant-misuse causation, itemized statement timing, display-fixture damages, and the base-rent liability cap/carve-outs.
- Added lease-specific evidence gaps and prevented signed-contract, invoice, SLA, integration-log, indemnity, IP-comparison, and lost-revenue gaps from being added to the lease branch.
- Added lease-specific next steps and prevented invoice/suspension/SaaS/force-majeure/refund/indemnity/IP boilerplate from running.
- Added lease-specific risk rationale and avoided generic suspension/termination wording in the lease risk rationale.

### 8. Evaluation Lab and exports

- Evaluation Lab preview now names the fixture `lease_repair_notice_abatement_deposit_golden`.
- `must_include_issues` comes from final filtered `active_issue_tags`.
- Markdown and JSON exports already used the final diagnosis object; the new tests assert active tags, key issues, clause signals, evidence gaps, risk rationale, timeline facts, suggested next steps, and legacy `issue_tags` match the filtered diagnosis.

### 9. Files changed

- `docs/assets/app.js`
  - Added lease issue-family registry entries, factual triggers, clause signals, lease timeline extraction, lease key issues, lease evidence gaps, lease next steps, lease risk rationale, lease dispute types, and lease Evaluation Lab case naming.
- `tests/test_docs_site.py`
  - Added the Lease repair / rent abatement / security deposit fixture.
  - Added regression assertions for active tags, forbidden issue families, clause-only force majeure, fact-specific key issues, role-classified timeline facts, evidence gaps, lease-specific next steps, Evaluation Lab preview, Markdown/JSON export parity, and cross-run contamination.
- `bug_audit.md`
  - Added this audit entry.

### 10. Tests added or updated

- `test_playground_lease_repair_abatement_filters_false_issue_families`
- `test_playground_lease_repair_key_issues_timeline_and_gaps_are_fact_specific`
- `test_playground_lease_repair_next_steps_preview_and_exports_are_scoped`
- Extended `test_playground_diagnosis_runs_do_not_cross_contaminate_issue_templates` to run the lease fixture after force majeure, SaaS/SLA, refund, and confidentiality/IP fixtures.

### 11. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `Test-Path package.json` | Passed | Returned `False`; no npm package file exists, so npm install/test/build/lint/typecheck scripts are not applicable. |
| `git diff --check` | Passed | No whitespace errors in the patch. |
| `node --check docs\assets\app.js` | Blocked by approval timeout | Attempted more than once; the automatic permission approval review did not finish before its deadline. |
| `python -m pytest tests\test_docs_site.py -q` | Blocked by approval timeout | Attempted; the automatic permission approval review did not finish before its deadline. |
| `python -m pytest` | Blocked by approval timeout | Attempted; the automatic permission approval review did not finish before its deadline. |
| `python -m compileall -q contract2agent tests scripts` | Blocked by approval timeout | Attempted; the automatic permission approval review did not finish before its deadline. |
| `python scripts\check_docs_links.py` | Blocked by approval timeout | Attempted; the automatic permission approval review did not finish before its deadline. |
| `python -m mkdocs build --strict` | Blocked by approval timeout | Attempted; the automatic permission approval review did not finish before its deadline. |

### 12. Build/test results

- `git diff --check` passed.
- The repository has no `package.json`, so npm commands are not present.
- Node, pytest, compileall, docs-link, and MkDocs verification could not be executed in this session because executable commands requiring escalation timed out in the approval reviewer.
- The static playground route remains `docs/playground/index.html`, preserving the GitHub Pages `/Contract2Agent/playground/` path. No backend, runtime network call, route, sample loading, export button, copy button, styling, navigation, or unrelated UI change was added.

### 13. Remaining limitations

- The playground remains a deterministic static analyzer. It now has lease-specific trigger gates and blockers, but still depends on explicit textual signals.
- Exact business-day date arithmetic is still described as evidence-dependent rather than computed.
- Full executable verification should be rerun in an environment where `node`, `pytest`, `compileall`, `check_docs_links.py`, and `mkdocs build --strict` are approved.

## 2026-05-04 Confidentiality / IP Indemnity Trigger-Gate Follow-Up

### 1. What was wrong

- The playground diagnosis engine could still let stale/default issue-family templates contaminate an unrelated confidentiality and IP indemnity case.
- A Service Agreement involving public confidential-information exposure, third-party IP demand, indemnity notice, damages, and liability-cap carve-outs could incorrectly receive SaaS, payment, invoice, refund, delivery, force-majeure, SLA, suspension, liquidated-damages, and cover-cost concepts.
- Evaluation Lab generated test-case previews could use active issues from broad selected/default dispute categories instead of the final filtered diagnosis.

### 2. Root cause

- Issue families were still triggered by broad substring and dropdown/default signals before factual trigger gates and negative facts were applied.
- Clause signals, selected dispute type, and fact terms were not consistently separated. Examples:
  - `software` matched the short force-majeure trigger `war`.
  - a negative statement such as `No party claims ... service credits` could still support SaaS classification.
  - `delivered under the project` could be confused with an active late-delivery dispute.
- Template generation for key issues, evidence gaps, timeline facts, next steps, risk, and Evaluation Lab preview did not have a confidentiality/IP indemnity scoped path.

### 3. Evidence of template contamination

- The reported fixture should focus on May 3 public workspace disclosure, May 6 customer discovery, May 8 removal, May 10 third-party IP demand, May 12 indemnity notice, 3-business-day unauthorized-disclosure notice, 10-day indemnity notice, and twelve-month cap carve-outs.
- The stale output instead included refund-calculation, performed-vs-unperformed services, invoice-date, force-majeure notice, migration deadline, temporary consultant, liquidated-damages, SLA/uptime, service-credit, and suspension terms from other playground fixtures.
- The generated test-case preview used payment/refund/default golden state rather than current final active issues.

### 4. Fix

- Added an issue-family registry in `docs/assets/app.js` with active triggers, clause triggers, negative triggers, and blocker terms for payment, invoice dispute, refund, force majeure, confidentiality, indemnity, delivery, SLA, suspension, liquidated damages, and cover costs.
- Added segment-level blocker filtering so negative facts such as `No party claims unpaid invoices`, `No party claims refunds`, `No party claims SLA downtime`, and `No party claims government order` block inactive families unless a separate positive factual trigger exists.
- Tightened contract-type detection so `Service Agreement` is not upgraded to `SaaS Agreement` unless contract text or non-blocked facts contain SaaS-specific support.
- Added confidentiality/IP indemnity timeline extraction, key-issue generation, evidence-gap generation, and next-step generation tied to active confidentiality, unauthorized disclosure, indemnity, third-party IP, damages, liability limitation, and liability-cap carve-out tags.
- Added clause signals for unauthorized-disclosure notice timing, indemnity notice timing, defense control / settlement consent, confidentiality carve-outs, and indemnity carve-outs while keeping force majeure clause-only when not fact-triggered.
- Made Evaluation Lab previews derive `case_name`, `must_include_issues`, and `must_include_evidence_gaps` from the final filtered diagnosis object.
- Cloned diagnosis arrays before assigning legacy aliases so `issue_tags` mirrors `active_issue_tags` without reusing stale mutable output arrays.

### 5. Files changed

- `docs/assets/app.js`
  - Added trigger-gated issue-family registry and blockers.
  - Added confidentiality/IP indemnity fact triggers, timeline extraction, key issues, evidence gaps, next steps, dispute types, and preview generation.
  - Tightened SaaS, force-majeure, delivery, refund, payment, SLA, suspension, and export alias behavior.
- `tests/test_docs_site.py`
  - Added the confidentiality/IP indemnity regression fixture.
  - Added tests for active issue filtering, dispute type filtering, clause signals, role-classified timeline facts, key issues, evidence gaps, next steps, Evaluation Lab preview, export parity, and sequential cross-contamination.
- `bug_audit.md`
  - Added this audit entry.

### 6. Tests added

- `test_playground_confidentiality_ip_indemnity_filters_false_issue_families`
- `test_playground_confidentiality_ip_clauses_issues_and_timeline`
- `test_playground_confidentiality_ip_gaps_next_steps_preview_and_exports_are_scoped`
- `test_playground_diagnosis_runs_do_not_cross_contaminate_issue_templates`

### 7. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript syntax is valid. |
| `python -m pytest tests\test_docs_site.py -q` | Passed | 32 passed in 2.06s. |
| `python -m pytest` | Passed | 245 passed in 20.51s. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully in 0.97s. |
| `Test-Path package.json` | No package file | No npm `test`, `build`, `lint`, or `typecheck` scripts are present to run. |

### 8. Build/test result

- The static playground route remains `docs/playground/index.html`, preserving the GitHub Pages `/Contract2Agent/playground/` path.
- Markdown and JSON exports now use the same final filtered diagnosis object shown in the UI.
- Legacy `issue_tags` mirrors filtered `active_issue_tags`.
- Sequential same-process playground runs no longer leak refund, force-majeure/migration, liquidated-damages, cover-cost, SLA/uptime, service-credit, suspension, invoice, or payment templates into the later confidentiality/IP diagnosis.

### 9. Remaining limitations

- The playground remains a deterministic browser-side analyzer. It now uses stricter trigger gates and blockers, but still depends on explicit text signals and nearby date context rather than legal NLP or a backend.
- The issue-family registry is intentionally conservative; ambiguous facts may remain `unclear` or clause-only until the user provides stronger factual triggers.

## 2026-05-04 Refund / Termination / Acceptance Template Contamination Follow-Up

### 1. Remaining issue

- The prior force-majeure follow-up fixed clause-only force majeure handling, but a refund / termination / acceptance case still received unrelated active issue families and stale templates.
- The analyzer could incorrectly:
  - activate `indemnity` when the facts expressly denied any third-party IP or infringement claim.
  - activate or signal `confidentiality` because substring matching treated `non-refundable` as containing `nda`.
  - convert a prepaid-fee refund dispute into `Payment/Invoice Dispute`.
  - generate unpaid-invoice, suspension, service-credit, stale delivery, and lost-revenue wording.
  - classify March 28 as rejection context and April 2 as a delivery-delay notice instead of provider partial delivery and customer breach notice.

### 2. Root cause

- Active issue tags still relied on broad keyword groups and clause mentions instead of factual invocation.
- Invoice-dispute detection treated generic fee/refund disputes as invoice disputes.
- Indemnity and confidentiality lacked required factual triggers and negative context guards.
- Timeline and next-step generation did not have a scoped refund / termination / acceptance path, so generic payment, suspension, and delivery templates could leak.

### 3. Files changed

- `docs/assets/app.js`
  - Added factual trigger guards for invoice disputes, indemnity, and confidentiality.
  - Kept indemnity and force majeure as clause-only signals when not fact-triggered.
  - Added refund / prepaid-fee / acceptance-rejection active tags separate from payment and invoice disputes.
  - Added refund / termination / acceptance timeline extraction for payment, milestones, delivery, breach notice, response, termination, cure period, and rejection period.
  - Added scoped key issues, evidence gaps, and suggested next steps for refund / prepaid-fee / acceptance disputes.
  - Removed service-credit wording from risk/contested-fact rationale unless service-credit is actually active.
  - Fixed `nda` substring contamination from `non-refundable`.
- `tests/test_docs_site.py`
  - Added a refund / termination / acceptance regression fixture.
  - Added tests for active tag filtering, clause-only signals, case-specific key issues, timeline role classification, evidence gaps, next steps, and Markdown/JSON exports.
- `bug_audit.md`
  - Added this follow-up note.

### 4. Tests added

- `test_playground_refund_termination_filters_false_positive_issue_families`
- `test_playground_refund_termination_clause_signals_are_clause_only_scoped`
- `test_playground_refund_termination_key_issues_and_timeline_are_case_specific`
- `test_playground_refund_termination_gaps_next_steps_and_exports_are_scoped`

### 5. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript syntax is valid. |
| `python -m pytest tests\test_docs_site.py -q` | Passed | 28 passed in 1.30s on the final focused run. |
| `python -m pytest` | Passed | 241 passed in 21.96s. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully in 0.69s. |
| `Test-Path package.json` | No package file | No npm install/test/build/lint/typecheck scripts are present in this repository. |

### 6. Build/test result

- The static playground and `/Contract2Agent/playground/` route remain covered by the existing docs tests and MkDocs strict build.
- No backend, runtime network call, route, sample-loading, export-button, styling, or unrelated UI change was added.
- The refund / termination / acceptance fixture now:
  - excludes indemnity, confidentiality, force majeure, SLA, service credit, suspension, and invoice dispute from active issue tags.
  - keeps indemnity and force majeure as clause-only signals when not fact-triggered.
  - separates refund and prepaid-fee analysis from invoice-dispute analysis.
  - produces case-specific key issues, evidence gaps, timeline facts, suggested next steps, and Markdown/JSON exports.

### 7. Remaining limitations

- The playground remains deterministic and text-pattern based. It now filters each issue family more narrowly, but it still depends on reasonably explicit dates, amounts, clause names, and factual descriptions in the user input.
- No static reference pack was added in this follow-up; the fix stayed inside the existing checked-in static analyzer.

## 2026-05-04 Force Majeure Template Contamination Follow-Up

### 1. Remaining bug

- A positive force-majeure Service Agreement late-delivery case correctly activated force majeure and produced non-low risk, but unrelated SaaS/SLA/payment/suspension templates still leaked into the diagnosis.
- The analyzer could add:
  - `SLA` active issue tags.
  - `SLA/Service Credit` dispute type.
  - SLA/uptime key issues and service-credit next steps.
  - payment timing and suspension clause signals from generic service or fee language.
  - incorrect liquidated-damages cap text because percentage extraction split decimal percentages and selected the wrong percent.
  - lumped notice dates instead of classifying force-majeure dates by event role.

### 2. Root cause

- Template family selection was still too broad:
  - generic `service` words could activate SaaS/SLA logic.
  - generic `fees` language inside liability caps could activate payment timing clause signals.
  - notice and delivery templates were not filtered for force-majeure-specific notice/delay cases.
  - liquidated damages extraction reused a generic first-percent helper and did not preserve both the weekly rate and cap.
  - timeline extraction had no force-majeure event roles.

### 3. Files changed

- `docs/assets/app.js`
  - Tightened active SLA/service-credit selection so it requires explicit SLA/uptime/downtime/service-credit triggers and matching contract clause signals.
  - Tightened payment timing clause detection so fee-cap language does not imply payment timing.
  - Added force-majeure timeline extraction for government order, awareness, force-majeure notice, migration deadline, consultant cover cost, partial completion, and final completion dates.
  - Added liquidated-damages term extraction for rate, unit, and cap.
  - Added force-majeure-specific key issues and next steps.
  - Guarded delivery/notice/cure templates so force-majeure notice cases do not receive invoice/cure/suspension/SLA boilerplate.
- `tests/test_docs_site.py`
  - Added a positive force-majeure Service Agreement fixture.
  - Added regression tests for active tags, forbidden SaaS/SLA leakage, clause signals, case-specific key issues, timeline role classification, scoped next steps, and Markdown/JSON exports.
- `bug_audit.md`
  - Added this follow-up note.

### 4. Tests added

- `test_playground_positive_force_majeure_avoids_saas_template_leakage`
- `test_playground_positive_force_majeure_clauses_issues_and_timeline`
- `test_playground_positive_force_majeure_next_steps_and_exports_are_scoped`

### 5. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript syntax is valid. |
| `python -m pytest tests\test_docs_site.py -q` | Passed | 24 passed in 0.74s on the final focused run. |
| `python -m pytest` | Passed | 237 passed in 18.98s. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully in 0.53s. |

### 6. Build/test result

- The static playground still builds through MkDocs.
- No backend, runtime network call, route, sample-loading, export-button, or styling change was added.
- The positive force-majeure fixture now:
  - includes force majeure as an active issue.
  - excludes SLA, service credit, suspension, invoice, uptime, downtime, support-ticket, and customer-side integration concepts when unsupported by the fixture.
  - extracts the liquidated damages rate as `1.5% per full week` and cap as `12%`.
  - classifies June 20, June 21, June 28, June 30, July 18, July 20, and August 5 by event role.
  - exports corrected structured Markdown and JSON.

## 2026-05-04 Playground Delivery Follow-Up Fix

### 1. Previous partial fix result

- The first playground diagnosis-quality fix separated the main structured fields and made the SaaS notice/cure fixture risk non-low.
- It still left a visible late-delivery failure mode:
  - explicit denial of external-event causation could still activate force majeure because the same sentence contained trigger words such as natural disaster, government order, strike, war, and external uncontrollable event.
  - late-delivery key issues still fell back to broad delivery/liability templates when enough dated delivery, cure, rejection, defect, and damages facts were available.
  - the result header still combined contract/dispute type badges with active issue tags, making the conceptual separation less visible.

### 2. Remaining bug and root cause

- Root cause:
  - force majeure trigger detection looked for positive trigger phrases before understanding sentence-level denial context.
  - delivery-specific dates and remedy terms were not extracted into a delivery timeline shape before key issue generation.
  - the rendered detected badge list grouped type labels and active issue tags together.
- Corrected behavior:
  - active force majeure now requires factual invocation and is blocked when the facts explicitly deny force majeure or external uncontrollable event causation.
  - clause-only force majeure remains available as `force majeure clause mentioned but not fact-triggered`.
  - late-delivery key issues now use extracted delivery milestone, actual delivery, notice, cure, revised package, rejection, review-period, API defect, liquidated-damages, lost-revenue, and liability-cap facts when present.

### 3. Files changed

- `docs/assets/app.js`
  - Added sentence-level external-event denial detection for force majeure.
  - Added delivery timeline extraction helpers for milestone, delivery, delay notice, revised package, rejection, review period, liquidated damages cap, API mapping defects, lost revenue exclusion, and liability cap period.
  - Updated delivery/notice/cure/damages/liability key issue generation to prefer fact-specific issues.
  - Split the rendered detected type badges from active issue tags so clause-only signals do not appear in the active tag list.
- `tests/test_docs_site.py`
  - Added a late-delivery regression fixture with the explicit negative force-majeure context.
  - Added tests for active issue tags, clause signals, fact-specific key issues, and Markdown/JSON export separation.
- `bug_audit.md`
  - Added this follow-up note.

### 4. Tests added

- `test_playground_late_delivery_blocks_denied_force_majeure_issue`
- `test_playground_late_delivery_key_issues_are_fact_specific`
- `test_playground_late_delivery_exports_keep_force_majeure_clause_only`

### 5. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `node --check docs\assets\app.js` | Passed | Static playground JavaScript syntax is valid. |
| `python -m pytest tests\test_docs_site.py -q` | Passed | 21 passed in 0.78s. |
| `python -m pytest` | Passed | 234 passed in 21.43s. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully in 0.55s. |

### 6. Build/test result

- The static playground still builds through MkDocs.
- No backend, runtime network call, route, sample-loading, export-button, or styling change was added.
- The late-delivery fixture now keeps force majeure out of `active_issue_tags`, retains it only in `clause_signals`, and exports the corrected separation in Markdown and JSON.

## 2026-05-04 Playground Diagnosis Quality Fix

### 1. What was wrong

- The GitHub Pages playground diagnosis in `docs/assets/app.js` mixed contract clause mentions with active dispute issues.
- Force majeure could become an active issue merely because it appeared as an SLA exclusion.
- Key issues were generated from broad taxonomy-style templates instead of the case facts, dates, party positions, and evidence gaps.
- Risk scoring could be too optimistic because it treated a case with multiple critical notice/cure evidence gaps as low when the rest of the text looked well populated.
- Timeline reasoning did not separately classify invoice dates, notice dates, deemed receipt, cure period, suspension date, or evidence-dependent procedural prerequisites.

### 2. Root cause

- The browser analyzer used one keyword-group pass over contract text, facts, evidence, and metadata.
- The same detected groups fed active issue tags, key issues, clause signals, evidence gaps, and risk.
- There were no negative-trigger rules for clause-only concepts such as force majeure.
- Evidence gaps were mostly generic and were not tied back to core procedural prerequisites before risk scoring.

### 3. Files changed

- `docs/assets/app.js`
  - Added deterministic separation for:
    - contract type detection
    - dispute type detection
    - active issue tags
    - clause signals
    - evidence gaps
    - timeline facts
    - risk object and risk label
    - suggested next steps
  - Preserved the existing static browser playground and existing aliases such as `issue_tags`, `relevant_clause_signals`, and `risk_signal`.
  - Added force majeure negative-trigger behavior: force majeure remains a clause signal when only present in an SLA exclusion, but becomes active only when dispute facts or party positions invoke an external event or force majeure theory.
  - Updated Markdown and JSON output to include the corrected structured diagnosis fields.
- `tests/test_docs_site.py`
  - Added Node-backed tests that execute the actual static `docs/assets/app.js` diagnosis code with a minimal DOM stub.
  - Added regression coverage for force majeure negative triggers, critical evidence gaps, case-specific key issues, output structure separation, Markdown/JSON exports, and the MkDocs playground route.

### 4. Tests added or updated

- `test_playground_force_majeure_clause_signal_is_not_active_issue`
- `test_playground_notice_cure_critical_gaps_prevent_low_risk`
- `test_playground_saas_key_issues_are_case_specific`
- `test_playground_structured_output_separates_core_fields`
- `test_playground_exports_use_corrected_structured_diagnosis`
- `test_mkdocs_nav_preserves_github_pages_playground_route`

### 5. Commands run

| Command | Result | Summary |
| --- | --- | --- |
| `rg --files` | Passed | Inspected repository structure and located the static playground assets. |
| `rg -n "function diagnose\|function markdownReport\|force majeure\|risk" docs contract2agent tests` | Passed | Located the active diagnosis/export implementation in `docs/assets/app.js`. |
| `node --check docs\assets\app.js` | Passed | Browser playground JavaScript syntax is valid. |
| `python -m pytest tests\test_docs_site.py` | Passed | 18 passed in 0.47s on the final targeted run. |
| `python -m pytest` | Passed | 231 passed in 23.31s on the final full run. |
| `python -m compileall -q contract2agent tests scripts` | Passed | Python syntax compilation succeeded. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully. |
| `Test-Path site\playground\index.html` | Passed | Built playground page exists. This preserves the GitHub Pages route that maps to `/Contract2Agent/playground/`. |
| `Test-Path package.json` | Passed | Returned `False`; no npm scripts are present, so `npm test`, `npm run build`, `npm run lint`, and `npm run typecheck` were not applicable. |

### 6. Build and test results

- Playground static build succeeds.
- `site/playground/index.html` is produced by MkDocs.
- The MkDocs nav still includes `Playground: playground/index.html`.
- The static app still contains no runtime `fetch`, `XMLHttpRequest`, `WebSocket`, or dynamic browser import calls.
- The SaaS regression fixture now produces:
  - `contract_type`: includes `SaaS Agreement`
  - `dispute_type`: includes `Notice/Cure Period` and `Payment/Suspension`
  - `active_issue_tags`: includes payment, invoice dispute, notice, cure period, suspension, SLA, service credit, damages, and liability limitation
  - `active_issue_tags`: does not include force majeure
  - `clause_signals`: includes force majeure as a not fact-triggered clause signal
  - `risk_signal`: `medium`, not low
  - case-specific key issues containing February 1, March 1, March 5, March 18, 10-day cure period, SLA/downtime, service credits, lost revenue, and liability cap concepts

### 7. Remaining limitations

- This remains a deterministic static playground, not legal advice and not an exhaustive legal analyzer.
- Date math is classified and explained, but exact business-day calendar calculation is not performed in the browser.
- Risk scoring is conservative around critical evidence gaps but still heuristic.
- The analyzer does not infer facts that are not present in contract text, dispute facts, party positions, evidence, or metadata.

### 8. Reference pack decision

- A static reference pack was deferred.
- The fix uses curated deterministic phrase maps and negative triggers directly in `docs/assets/app.js`, which keeps the GitHub Pages playground offline, static, and backend-free.
- No runtime browser scraping, external API dependency, CORS proxy, or network call was added.

## 1. Audit Summary

- Audit timestamp: 2026-05-04T17:07:04+08:00
- Repository: Contract2Agent
- Branch/worktree at start of this pass: `main...origin/main` with an already dirty worktree.
- Scope:
  - Repository structure and packaging metadata.
  - `contract2agent/` package import paths, CLI wiring, diagnosis/checker/report-adjacent code paths, and obvious path/error-handling risks.
  - Existing `tests/` suite.
  - MkDocs configuration and Markdown links because docs assets and docs configuration are present in the current worktree.
  - Generated/cache hygiene.
- Final test status: `python -m pytest` passed with 206 tests.
- Source-code fix status for this pass: no new confirmed implementation bug was found after validating the current dirty tree. This file records the audit and environment limitation.

## 2. Environment Notes

- Python command: `python`
- Python version: Python 3.13.7
- Python executable: `D:\tools\python\python.exe`
- Pytest availability before install attempt: already installed.
- Pytest version: 9.0.3
- Runtime/test packages observed:
  - Typer 0.25.1
  - Pydantic 2.13.3
  - PyYAML 6.0.3
  - Jinja2 3.1.6
  - MkDocs 1.6.1
- Packages installed during this pass: none.
- Editable install attempt:
  - Command: `python -m pip install -e .`
  - Result: failed due to Windows permission errors creating pip temporary build-tracker files under `C:\Users\18254\AppData\Local\Temp`.
  - Escalation was requested twice for the same command; automatic approval review timed out both times.
  - Impact: the `c2a` console script could not be verified through PATH in this environment. The module CLI was verified with `python -m contract2agent.cli --help`, and the packaging metadata declares `c2a = "contract2agent.cli:main"`.

## 3. Bugs Found

No new confirmed implementation bugs were found during this pass.

### ENV-001: Editable install blocked by local temp directory permissions

- Files involved:
  - `pyproject.toml`
  - local Python/pip environment
- Symptom:
  - `c2a --help` failed because `c2a` is not installed on PATH.
  - `python -m pip install -e .` failed before installing console scripts.
- Root cause:
  - Pip could not create or access its temporary build tracker under the user's temp directory. This is an external environment permission issue, not a packaging metadata defect in the repository.
- Fix applied:
  - No repository code change was appropriate. The module entry point was validated directly with `python -m contract2agent.cli --help`.
- Why this does not change intended functionality:
  - No product behavior was changed.
  - Existing public console script metadata remains intact: `c2a` is still the primary CLI and `agentdoctor` is retained as a legacy alias.
- Test or verification performed:
  - `python -m contract2agent.cli --help` passed and listed the expected commands.
  - `python -m pytest` passed.

## 4. Tests and Checks Run

| Command | Result | Summary |
| --- | --- | --- |
| `git status --short --branch` | Passed | Worktree was already dirty on `main...origin/main`. |
| `git diff --stat` | Passed | Confirmed broad existing modifications before this pass. |
| `rg --files` | Passed | Inspected repository layout. |
| `python --version` | Passed | Python 3.13.7. |
| `python -c "import sys; print(sys.executable)"` | Passed | `D:\tools\python\python.exe`. |
| `python -m pytest` | Passed | 206 passed in 17.75s. |
| `python -c "import contract2agent; print(contract2agent.__version__ if hasattr(contract2agent, '__version__') else 'import ok')"` | Passed | Printed `0.1.0`. |
| `python -m contract2agent.cli --help` | Passed | CLI module help rendered and listed expected commands. |
| `c2a --help` | Failed due to environment | `c2a` was not on PATH because editable install could not complete. |
| `python -m compileall -q contract2agent tests scripts` | Passed | No syntax errors. |
| `python scripts\check_docs_links.py` | Passed | Checked 26 Markdown files; all relative links resolve. |
| `python -m mkdocs build --strict` | Passed | Documentation built successfully. |
| `python -m pip install -e .` | Failed due to environment | Pip temp build-tracker permission error. |
| `python -m pytest --version` | Passed | pytest 9.0.3. |
| `python -m mkdocs --version` | Passed | MkDocs 1.6.1. |
| Static `rg` scans for stale branding, broad exception handling, stale CLI notes, and docs asset references | Passed | No new confirmed source bug found. Legacy `agentdoctor` references are documented compatibility paths or aliases. |

## 5. Remaining Risks

- Editable installation and PATH-level `c2a` verification remain blocked by local pip temporary-directory permission errors. This could not be fixed inside the repository during this pass.
- No known repository implementation or test-suite failures remain from this audit pass.

## 6. Final Status

- `python -m pytest`: passed, 206 tests.
- `python -m compileall -q contract2agent tests scripts`: passed.
- `python scripts\check_docs_links.py`: passed.
- `python -m mkdocs build --strict`: passed.
- Commands that could not be run successfully:
  - `python -m pip install -e .`: blocked by local pip temp permission errors.
  - `c2a --help`: blocked because editable install could not complete and the script is not on PATH.
