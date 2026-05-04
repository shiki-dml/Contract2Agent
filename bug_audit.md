# Contract2Agent Bug Audit

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
