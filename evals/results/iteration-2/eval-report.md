# salesforce-core Behavioral Eval Report — Iteration 2 (vs Iteration 1)

**Graded:** 2026-08-30 · **Inputs:** `eval-skills/evals/evals.json` (13 evals) vs `eval-workspace/iteration-2/eval-*/` · **Baseline:** `eval-workspace/iteration-1/{grading.json, eval-report.md}` · **Fixes under test:** v1.3.1 / v1.4.0 backlog items
**Grades:** PASS / PARTIAL / FAIL / N/A(environment). Environment-caused misses (managed-only org, harness descopes) remain N/A, not FAIL.

## Comparison table (iteration 1 → iteration 2)

| Eval | Skill | Iter-1 verdict | Iter-2 verdict | Delta | Why |
|---|---|---|---|---|---|
| eval-01 | sf-apex | WORKING-WITH-ISSUES | **WORKING** | **Improved** | Mode explicitly recorded; managed-code rule + validator N/A/exit-2 killed the (hidden)-scoring trap; zero tool-name friction |
| eval-02 | sf-flow | WORKING | WORKING | Improved | Same design 97→102/110; all 4 validator contradictions fixed; residual = 2 new INFO false positives (−8 phantom pts) |
| eval-03 | sf-data | WORKING | WORKING | Improved | Empty-result probe now skill-mandated (was improvised); 0 failed calls in 4 |
| eval-04 | sf-lwc | WORKING | WORKING | Improved | JS-first create order documented → 4/4 first-attempt deploys; per-file-type SLDS denominators fixed |
| eval-05 | sf-metadata | WORKING | WORKING | Improved | SOAP CustomObject path first-try (iter-1: multiple failures); deletion realities predicted both traps |
| eval-06 | sf-permissions | WORKING | WORKING | Improved | Iter-1's improvised roll-up/session-filter/null-Parent handling now codified and followed verbatim |
| eval-07 | sf-diagram | WORKING | WORKING | Improved | Real mermaid.parse() validation (11.17.2) added; `__metadata__` empirically cleared; CLI snippets still dangle |
| eval-08 | sf-audit | WORKING | **WORKING-WITH-ISSUES** | Mixed | All 4 sf-audit fixes verified; but per-class Apex /150 scoring descoped to a surface inventory (disclosed) — iter-1 scored classes individually; new ErrorConditionFormula INVALID_FIELD limitation |
| eval-09 | sf-test | WORKING | WORKING | Improved | Deploy-naming friction gone; runAs descope now an honest 15→7 deduction; 2 new small gaps logged |
| eval-10 | sf-security | WORKING-WITH-ISSUES | WORKING-WITH-ISSUES | Improved (verdict same) | 0 errors vs 2; codified rules reproduced 77/100 with zero drift; blocker-vs-advisory split still PARTIAL (packaging-org checklist N/A in subscriber org) |
| eval-11 | sf-debug | WORKING | WORKING | Improved | Subscriber-org branch + namespace tell routed diagnosis; FlowDefinitionView gotcha prevented a live false negative |
| eval-12 | sf-campaigns | WORKING | WORKING | Improved | Both dangling references fixed and verified; demo mode clean |
| eval-13 | sf-leads | WORKING | WORKING | Improved | Fixture repair verified: 4 literal wrong-domain emails now detectable; iter-1 N/A expectation → PASS |

**Aggregate iteration 2: 11 WORKING, 2 WORKING-WITH-ISSUES (08, 10), 0 BROKEN** — vs iteration 1's 11/2/0 (01, 10).
Expectations (this grader's count over all 39): **33 PASS, 2 PARTIAL, 0 FAIL, 4 N/A(environment)** — identical totals to iteration 1's recount, but redistributed: eval-01 partial→pass, eval-13 N/A→PASS, eval-08 pass→partial. 11 of 13 evals improved, 1 improved-with-same-verdict (10), 1 mixed (08). No eval regressed on execution quality; eval-08's dip is a disclosed scope choice, not a capability loss.

---

## Per-eval grading detail

### eval-01 — sf-apex — WORKING (was WORKING-WITH-ISSUES)
- **detects execution mode — PASS.** review-report.md header records `Mode: mcp-plus-code-execution`; run-notes.md shows the mapping applied before the first org call (closes iter-1's PARTIAL).
- **fetches trigger bodies — N/A(environment).** Namespace GROUP BY first (kugo2p 34 / kugadd 2 / null 0) → zero unmanaged triggers, so per the new managed-code rule no bodies were fetched at all — the `(hidden)` trap never arose; validator self-test covered the hidden-body path instead. (Iter-1 "PASS" fetched 5 useless `(hidden)` bodies; not fetching is the better behavior.)
- **150-point scores with line-level evidence — N/A(environment).** All 36 triggers managed; honest per-trigger "N/A — managed, source hidden" inventory. Capability partially proven off-org: synthetic BadLoopTrigger → 2 CRITICAL with line refs (L3/L6), FAILED, exit 1; `(hidden)` file → NOT SCORABLE, exit 2.
- **no invented class names — PASS.** All names from metadata-only Tooling queries; "Unmanaged (reviewable) triggers found: 0" stated plainly.
- Delta basis: iter-1's two friction points (mode not recorded; validator scoring hidden code 150/150) are both eliminated. Residual: numeric score 130/150 "Very Good" printed next to a FAILED verdict on the CRITICAL self-test.

### eval-02 — sf-flow — WORKING (same, improved)
- **asks/infers entry conditions — PASS.** flow.json:107 `AND(ISPICKVAL(Priority,"High"), OR(ISNEW(), ISCHANGED(Priority)))`; headless defaults recorded per the new Headless-runs section.
- **fault path included — PASS.** flow.json:95 faultConnector → Assign_Capture_Fault + null-check decision with terminal no-op default.
- **110-point self-check before deploy — PASS.** Fixed validator run pre-deploy: 102/110 PASSED exit 0, every deduction itemized (110−5−3 reconciles); deployed Draft, verified not InvalidDraft, cleanup (flow + eval-created Escalations2 queue) verified to 0 rows.
- Fix verification: all 4 iter-1 validator contradictions resolved (Before_ prefix, storeOutputAutomatically, fault-variable usage, itemization). Residual: 2 new INFO-level false positives with exact line diagnoses — naming checked against `label` not `fullName` (validate_flow_cli.py:53 drops fullName; naming_validator lines 145–148), and `_is_autolaunched()` (validate_flow.py:1266) misclassifying record-triggered flows for the reusability advisory. Both fixed → 110/110.

### eval-03 — sf-data — WORKING (same, improved)
- **selectivity considered — PASS.** Explicit fields, indexed CloseDate filter, IsClosed=false, LIMIT 200.
- **THIS_QUARTER date literal — PASS.** THIS_FISCAL_QUARTER with assumption stated (fiscal-vs-calendar guidance still absent from the skill — carried minor).
- **results table — PASS.** 0-row result + now-mandatory sanity probe (COUNT 31, CloseDate 2020-01-20..2022-03-18, max $915K) → explained zero, reference re-run query offered. "One probe is enough; don't spiral" cap followed.
- Fix verification: mapping preamble converted iter-1's hard org_init blocker into one cheap query; 0 failed calls.

### eval-04 — sf-lwc — WORKING (same, improved)
- **PICKLES design pass — PASS.** Full per-letter table (record-picker + getRelatedListRecords, 300ms debounce with disconnectedCallback cleanup, aria-live).
- **wire/apex decision explained — PASS.** Explicit No-Apex design; wire + client-side filter getter to avoid re-wire per keystroke; UI API CRUD/FLS rationale.
- **165-point SLDS check — PASS.** Fixed validator scores per file type with N/A categories excluded from the denominator: HTML 65/65, CSS 75/75, JS 75/75, pre-deploy, zero issues — iter-1's misleading "/165 per file" framing is gone.
- Fix verification: documented bundle→JS→HTML→CSS create order and Base64-only-targetConfigs callout → 4/4 first-attempt deploys (iter-1's FIELD_INTEGRITY_EXCEPTION did not recur); unquoted-binding examples confirmed compile-clean. Cleanup verified to 0 rows.

### eval-05 — sf-metadata — WORKING (same, improved)
- **field-level security / permission set handling — PASS.** PS + ObjectPermissions + 3 FieldPermissions + assignment (user Id via REST root identity), all first-attempt; cleanup in the documented order.
- **describe verification after create — PASS.** FieldDefinition SOQL (13 fields, correct types) + authoritative Tooling CustomField query (exactly 3 rows) + live SOQL over all 3 fields; deletion verified via INVALID_TYPE and 0-row permset query; Tooling-visible soft-delete residue correctly read as the documented 15-day holding area, not a failed delete.
- Fix verification: the corrected SOAP-createMetadata-via-executeAnonymous path worked in 1 attempt (iter-1: multiple failed Tooling payload variants); the deliberate Tooling DELETE probe reproduced the predicted INSUFFICIENT_ACCESS failure, then deleteMetadata succeeded first-try.

### eval-06 — sf-permissions — WORKING (same, improved)
- **object-permission query path — PASS.** ObjectPermissions query now including Parent.Type/IsOwnedByProfile/Profile.Name → 33 grants split 9 profile / 1 regular PS / 23 Session.
- **PS + PSG traversal — PASS.** PSA count across all 24 non-profile PSs → 0; PSG membership → 0; null-Parent row resolved per the newly documented rule.
- **user-level rollup — PASS.** Headline: exactly 1 user via System Administrator, using the now-documented profile roll-up (iter-1 improvised it); session permsets footnoted per the new default-filter rule; guest-site permset caveat added.
- Delta: iter-1's discovery work became verbatim execution; the roll-up fix "prevents a factually incorrect 'nobody can delete Opportunity' headline, not just friction."

### eval-07 — sf-diagram — WORKING (same, improved)
- **mermaid erDiagram — PASS.** Real-renderer validation this time: mermaid.parse() on Mermaid 11.17.2 → erDiagram PASS, flowchart PASS, `__metadata__` probe PASS (iter-1's defensive rename shown unnecessary on current Mermaid; downgrade to a min-version note).
- **relationship cardinality correct — PASS.** Lookup one-to-many, ParentId self-ref, dashed conversion paths, no-Master-Detail statement. Nit: `Account ||--o{ Contact` implies a required parent though AccountId is nullable — iter-1's `|o--o{` was marginally more precise.
- Still dangling: erd-conventions.md "Query Commands Reference" and sales-cloud-erd.md still invoke the removed `query-org-metadata.py` / `sf` CLI; erd-conventions.md still unlinked from SKILL.md; flowchart-vs-erDiagram preference conflict unreconciled (worked around by emitting both).

### eval-08 — sf-audit — WORKING-WITH-ISSUES (was WORKING; mixed)
- **single scan feeds all documents — N/A(environment).** Single HTML deliverable again (scoped run); multi-document reuse untestable for the second iteration running.
- **scores per component — PARTIAL.** All 5 active flows individually scored vs the 110-pt rubric (94/89/87/87/86, per-flow top issues, systemic zero-fault-connector finding, 1 HIGH re-fire bug). But Apex classes were inventoried at surface level only — the report itself discloses "class bodies were not scored against the 150-point rubric in this scoped run." Iter-1 scored the same 10 classes 82–112/150, so the capability exists; this run traded it away under the caller-specified apex+automation scope and weighted Apex at 20% hygiene. Disclosed and defensible, but the expectation is only half met.
- **HTML single-file §7–8 — PASS.** 29KB single file, zero external URLs, inline CSS/JS, SVG donut gauge + domain/severity bars, IntersectionObserver reveal, reduced-motion guard in both CSS and JS (the v1.3.1 §8 fix, verified in the shipped markup).
- Fix verification: ValidationRule `ORDER BY EntityDefinitionId` workaround followed first-attempt (no 500); partial-audit weighting rule applied verbatim (Flows 60 / Apex 20 / Legacy 20, Validation Rules N/A-renormalized). New finding: `ErrorConditionFormula` is not queryable on this connector (INVALID_FIELD) — C7 field list needs a per-row `Metadata` fallback.

### eval-09 — sf-test — WORKING (same, improved)
- **test plan matrix before code — PASS.** 7-dimension matrix precedes generation; every row mapped to a method or an explicit descope.
- **200-record bulk test — PASS.** stampsAll200InBulk over 200 @TestSetup accounts, full-set assertions, startTest/stopTest scoped to the action.
- **runAs deny case — N/A(environment).** No restricted profile; class has no CRUD/FLS surface to assert. Improvement: taken as an honest 15→7 rubric deduction (110/120 total) instead of iter-1's 0/15 note — the "documented descope path" ask is effectively satisfied in behavior.
- **Tooling API run + coverage — PASS.** POST runTestsAsynchronous → poll → 5/5 pass → ApexCodeCoverageAggregate 100% (10/10 lines); cleanup verified to 0 rows and 0 residual data.
- Fix verification: mapping preamble removed the deploy-naming friction (both class creates first-try). New gaps: the run's one compile failure (SOQL filter on long-text Description) is not in Phase 4's common-causes list (iter-1 backlog #11 for sf-test — still unshipped); runTestsAsynchronous HTTP method unstated (GET → 405, then POST).

### eval-10 — sf-security — WORKING-WITH-ISSUES (same verdict, improved execution)
- **category scan with line evidence — PASS.** Same file:line evidence (SiteRegisterController.cls:7; MyProfilePageController save()); namespace-counts-first guard prevented iter-1's 102KB body overflow — 15 calls, 0 errors (iter-1: ~12 calls, 2 errors).
- **blockers vs advisories split — PARTIAL (unchanged).** Severity-ranked 0C/0H/4M/4L + Notes with remediation plan and effort estimates, but still no explicit blocker-vs-advisory framing; AppExchange Review Readiness checklist again N/A (subscriber org, not the packaging org — recorded). No v1.3.1/v1.4.0 fix targeted this; expectation unchanged by design.
- **Critical caps the grade — PASS.** Cap rule stated; Lightning N/A-excluded, 69/90 → 77/100 per the now-written rule (applied verbatim; the rule's worked example literally matches this org's numbers — change the example so rule-following is distinguishable from example-copying).
- Zero drift vs iter-1 (same score, findings, severities) with 3 factual refinements — the codified rules reproduce iter-1's judgment deterministically, which is what the fixes promised.

### eval-11 — sf-debug — WORKING (same, improved)
- **triage before trace flags — PASS.** Read-only; zero TraceFlag/DebugLevel created; full proposed capture (DebugLevel spec, ≤30-min expiry, cleanup) per the headless propose-only rule.
- **SOQL-in-loop signature identified — PASS.** Log-read plan names repeated SOQL_EXECUTE_BEGIN, LIMIT_USAGE_FOR_NS buckets, and CODE_UNIT_STARTED re-entry; diagnosis pins consumption to the kugo2p managed cascade with bulk-save vs recursion as the realistic forks and the `(kugo2p)` suffix question as the top no-log diagnostic.
- **Diagnosis/Evidence/Fix/Prevention format — PASS.** Exact four headings, 6 numbered evidence items.
- Fix verification: subscriber-org branch + namespace tell routed the whole run; the FlowDefinitionView `TriggerObjectOrEventLabel` gotcha (shipped in v1.3.1) prevented a live false negative — two "Order"/"Quote"-labeled flows actually trigger on kugo2p objects and write Opportunity.CloseDate.

### eval-12 — sf-campaigns — WORKING (same, improved)
- **null-guarded ROI math — PASS.** Guard column per formula; n/a not 0 on missing cost; script-computed.
- **missing-cost campaigns flagged as hygiene finding, not ranked last — PASS.** Separate unrankable table + hygiene finding #1.
- **invest/pause recommendations — PASS.** Per-campaign Increase/Maintain/Restructure/Pause with grounds; zero-win ROI annotated as unrealized pipeline (iter-1 backlog nit, self-mitigated); rollup-vs-member mismatch re-confirmed as finding #4; both over-budget campaigns caught (sample-data README claims only one — doc nit).
- Fix verification: demo-mode org_init skip now explicit in Dispatch + Demo sections; report-template reference now a resolving relative path. Both caused zero friction.

### eval-13 — sf-leads — WORKING (same, improved)
- **gap-rate profile before enriching — PASS.** Scripted table incl. newly-added NumberOfEmployees (35%, the largest enrichable gap — invisible to iter-1's stock query) + process-fix observation before any proposal.
- **wrong-domain emails flagged — PASS (was N/A: fixture defect).** Regenerated leads.csv (md5 0b1c717f..., was 237dbfcd...) contains exactly the 4 documented literal mismatches (records 5/13/27/33 → northwind.example.com); all found, 5 legit Northwind leads correctly not flagged; 15 de-anon-source emails additionally tagged unverified.
- **no writes without approval — PASS.** No Salesforce tools; propose-only throughout; Phone/LeadSource exclusions honored; duplicate pairs skipped loudly.
- Fixture nits (cosmetic): README's de-anon narrative fits only 1 of the 4 wrong-domain rows; surviving duplicate pairs (001/023, 008/040) now undocumented in README.

---

## FIX VERIFICATION — v1.3.1 / v1.4.0 shipped fixes

| # | Fix | Status | Proving run(s) |
|---|---|---|---|
| 1 | **Tool-name mapping table** (execution-modes.md "read this first" preamble incl. org_init → Organization-probe fallback) | **VERIFIED** | Every org-connected run: 01, 02, 03, 04, 05, 06, 08, 09, 10, 11 all report zero tool-name trial-and-error and zero falsely-missing capabilities; 07 applied it for mode detection; 12/13 exercise the demo-mode branch |
| 2 | **Managed-code handling** (sf-apex namespace-first + no-body-fetch rule; sf-debug subscriber-org branch + namespace-suffix tell + FlowDefinitionView gotcha; sf-security managed-dominant scope-out + inventory guard) | **VERIFIED** | eval-01 (zero bodies fetched, honest N/A inventory), eval-11 (branch routed diagnosis; gotcha prevented a live false negative), eval-10 (scope table by instruction; body-overflow error gone) |
| 3 | **Validator repairs** (apex: (hidden) → N/A exit 2, exit-code contract; flow: Before_ naming, storeOutputAutomatically, fault-var usage, itemized deductions; slds: per-file-type denominators) | **VERIFIED** | eval-01 (self-test: exit 0/1/2 contract real), eval-02 (97→102, all 4 contradictions fixed, deductions reconcile), eval-04 (HTML /65, CSS /75, JS /75 with N/A excluded). Residuals: apex 130/150 "Very Good" beside FAILED; flow 2 new INFO false positives |
| 4 | **sf-metadata path correction** (Tooling-can't-create-CustomObject caveat → SOAP createMetadata via executeAnonymous; deletion-realities section; permset delete order) | **VERIFIED** | eval-05: create in 1 attempt (iter-1: several failures); predicted Tooling DELETE failure and 15-day soft-delete residue both observed; 0 failed org writes |
| 5 | **Empty-result verification step** (sf-data Step 6 + "Verifying empty results" probe) | **VERIFIED** | eval-03: 0-row main query → single COUNT/MIN/MAX probe → explained zero ("all opportunities close 2020–2022"); "one probe is enough" cap followed |
| 6 | **Roll-up guidance** (sf-permissions profile roll-up via User GROUP BY, session-permset default filter + footnote format, null-Parent resolution rule) | **VERIFIED** | eval-06: all three followed verbatim; prevents the factually wrong "0 users can delete" headline; null-Parent row resolved exactly as pre-documented |
| 7 | **Demo-mode notes** (org_init skip in sf-campaigns/sf-leads Dispatch + Demo sections; sf-campaigns report-template relative path) | **VERIFIED** | eval-12 (skipped without hesitation; path resolves), eval-13 (no org-connection ambiguity) |
| 8 | **Fixture repair** (regenerated sample-data/leads.csv with literal wrong-domain emails; NumberOfEmployees in gap query) | **VERIFIED** | eval-13: 4/40 literal mismatches present and detected, matching README records 5/13/27/33; NumberOfEmployees (35%) now surfaced by the stock query |
| — | Bonus verifications: sf-audit ValidationRule ORDER BY workaround, partial-audit weighting rule, §8 reduced-motion JS guard (eval-08); sf-lwc JS-first create order + Base64 targetConfigs + unquoted bindings (eval-04); Headless-runs gate degradation (evals 02, 03, 04, 05, 07, 11) | **VERIFIED** | as listed |

**Tally: 8/8 targeted fixes VERIFIED** (plus 3 bonus fix groups), each by at least one run that hit the exact iter-1 failure path and did not reproduce it.

---

## RESIDUAL BACKLOG — iteration-2 findings, deduplicated, ranked

All minor; nothing blocks any workflow. Ranked by (user-visible confusion × breadth).

| # | Issue | Skill(s) | Evidence | Suggested fix |
|---|---|---|---|---|
| 1 | **Flow validator: 2 INFO-level false positives (−8 phantom pts).** (a) Naming validated against `label` not API name — `validate_flow_cli.py:53` drops `fullName` in JSON→XML; `naming_validator._get_flow_label()` (145–148) regex-tests the spaced label, so the "fix" it suggests equals the flow's actual fullName. (b) `_is_autolaunched()` (`validate_flow.py:1266`) keys on processType only; record-triggered flows share `AutoLaunchedFlow`, so the reusability advisory misfires — should also require absence of `start.triggerType`. Fixing both → 110/110 | sf-flow | eval-02 | Preserve fullName through conversion; add triggerType guard |
| 2 | **Apex validator headline mismatch:** 130/150 "Very Good ⭐⭐⭐⭐" printed alongside FAILED + 2 CRITICALs; Testing 25/25 with no tests, Documentation 10/10 with no ApexDoc. Exit code/banner (what gates) are correct; the label is not | sf-apex | eval-01 | Cap star-rating/label (or total) when any CRITICAL present |
| 3 | **SKILL.md bodies still speak conventional-tool dialect** with no inline pointer to the mapping table: sf-data SKILL.md:139 "CRITICAL: Always call org_init() FIRST", sf-permissions Execution Model, sf-apex Validate example (`tooling_api_query(groupBy=...)`), sf-debug Set Up Tracing (no headless pointer). Works when execution-modes.md is read first; a reader who skips it re-hits iter-1 friction | sf-data, sf-permissions, sf-apex, sf-debug (pattern) | evals 01, 03, 06, 11 | One-line cross-reference beside each org_init/conventional-name mention |
| 4 | **sf-diagram dangling CLI snippets:** erd-conventions.md "Query Commands Reference" and sales-cloud-erd.md "Query Org Metadata (Recommended)" still invoke removed `query-org-metadata.py` / `sf` CLI; erd-conventions.md still unlinked from SKILL.md; flowchart-vs-erDiagram preference and fields-vs-no-fields contradictions unreconciled. Trap for a future ERD-from-live-org run | sf-diagram | eval-07 | Purge/replace snippets with mapped MCP calls; link the reference; state when each format wins; add Mermaid min-version note for `__metadata__` |
| 5 | **sf-audit `ErrorConditionFormula` not queryable** on this connector (INVALID_FIELD); formula lives in per-row `Metadata` — C7 sample query needs a documented fallback. Also: count managed FlowDefinitions for the honesty table; consider documenting when scoped runs may swap per-class /150 scoring for surface inventory (the eval-08 PARTIAL) | sf-audit | eval-08 | C7 amendment: "if ErrorConditionFormula errors, SELECT Ids then fetch Metadata per rule" |
| 6 | **sf-security carried items:** Phase-4 inline-markdown path for chat contexts (2nd run to deviate); `references/mcp-pagination.md` referenced but not shipped (also noted in eval-01); vulnerability-patterns.md "owns the namespace" still conflates ownership with retrievability; RemoteProxy known-good field list (SiteName, EndpointUrl, IsActive) still undocumented; new: N/A-rule worked example uses this org's exact 69/90→77/100 numbers | sf-security | eval-10 (eval-01 for pagination ref) | Five one-line edits |
| 7 | **sf-test gaps:** Phase-4 common-causes list missing "SOQL filter on non-filterable field types (long text/rich text/encrypted)" — hit again this run (carried from iter-1 minors, unshipped); Run-Tests step 1 doesn't state HTTP method (GET → 405; needs "POST runTestsAsynchronous/ with classids body") | sf-test | eval-09 | Add third common-cause bullet + method note |
| 8 | **sf-debug branch polish:** mapping table lacks a raw-sub-resource-GET row (ApexLog/{Id}/Body path form); FlowDefinitionView gotcha names the trap but not the recipe (read `Metadata.start.object` + `recordUpdates[].object`, ~2 fields, payloads are 6–7k tokens each); per-namespace bucket sizes unstated (100 sync/200 async per certified namespace, 1,100 org cap) | sf-debug | eval-11 | Three additive sentences |
| 9 | **Mapping covers names, not signatures:** SKILL.mds document structured params (`soql_query(sObject=, whereClause=)`) vs real single-string `run_soql_query(query=)`; plus no fiscal-vs-calendar-quarter guidance for date literals | sf-data (pattern) | eval-03 | Signature note in mapping table; one-line fiscal default |
| 10 | **sf-permissions polish:** `Parent.Type` missing from the Sub-case 1 query template (the session-filter rule needs it — added ad hoc); guest-site permset roll-up edge (bindable to Site guest user outside PSA → false "orphaned"); garbled "Salesforce MCP AI MCP Server" frontmatter persists | sf-permissions | eval-06 | Template + caveat + cosmetic |
| 11 | **sf-metadata additions:** Tooling SOQL semi-joins on CustomObject unsupported (INVALID_TYPE) — note in Phase 5 example; current-user-Id discovery via REST root `identity` URL worth a one-liner in the permset section | sf-metadata | eval-05 | Two additive notes |
| 12 | **sf-lwc pointers:** Create workflow step 5 should point to the Tooling create-order subsection (currently under Update); state that validate_slds.py only scores .html/.css/.js (meta-xml/Jest have no scoring path) | sf-lwc | eval-04 | Two pointers |
| 13 | **sf-flow bulk:** SKILL.md still ~40k tokens (2 paged reads; Approval-Orchestration dead weight for simple tasks); `/tmp` phrasing still not "a scratch directory" | sf-flow | eval-02 | Carried from iter-1 |
| 14 | **Fixture/doc nits:** sample-data README says "one over budget" but two campaigns exceed budget (Dreamforce +$7K, TrailblazerDX +$2K); leads README's de-anon narrative fits only 1 of the 4 wrong-domain rows; surviving duplicate pairs (001/023, 008/040) undocumented; campaigns Demo section could note member-level funnel only (no opportunity rows ship) | sample-data, sf-campaigns, sf-leads | evals 12, 13 | README edits only |
| 15 | **Validator score-example hygiene:** sf-security N/A example (see #6) and sf-apex read-order seam (managed-code rule in Validate section, mapping in reference — one Dispatch pointer closes it) | sf-security, sf-apex | evals 10, 01 | One-liners |

### Priority order
1–2 (validator credibility: false positives and contradictory headlines are what users see first) → 3 (dialect cross-refs; cheap, prevents the one remaining stall path) → 4–5 (dangling snippets / query fallback: real traps on the next org-connected run) → 6–8 (carried one-liners) → 9–15 (polish and doc nits).
