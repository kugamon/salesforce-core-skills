# salesforce-core Behavioral Eval Report — Iteration 1

**Graded:** 2026-08-30 · **Inputs:** `eval-skills/evals/evals.json` (13 evals) vs `eval-workspace/iteration-1/eval-*/`
**Grades:** PASS / PARTIAL / FAIL / N/A(environment). Environment-caused misses (managed-only org, harness descopes, fixture defects) are N/A, not FAIL, and are noted.

## Summary table

| Eval | Skill | Verdict | Expectations (pass / applicable) | Notes |
|---|---|---|---|---|
| eval-01 | sf-apex | WORKING-WITH-ISSUES | 2/3 (+1 N/A-env, 1 partial) | Managed-only org blocked line-level scoring; validator false-positives found |
| eval-02 | sf-flow | WORKING | 3/3 | 97/110 pre-deploy check; deployed Draft, verified, cleaned up |
| eval-03 | sf-data | WORKING | 3/3 | THIS_FISCAL_QUARTER used (verified equivalent; FY starts Jan) |
| eval-04 | sf-lwc | WORKING | 3/3 | Deployed via Tooling, verified, cleaned up; found real create-order gap |
| eval-05 | sf-metadata | WORKING | 2/2 | Overcame a false skill capability (Tooling can't create CustomObject) |
| eval-06 | sf-permissions | WORKING | 3/3 | Improvised profile roll-up the skill omits |
| eval-07 | sf-diagram | WORKING | 2/2 | No org access; not needed for these expectations |
| eval-08 | sf-audit | WORKING | 2/2 (+1 N/A-env) | Word/Excel descoped by harness; HTML meets §7–8 fully |
| eval-09 | sf-test | WORKING | 3/3 (+1 N/A-env) | runAs descoped (no restricted profile; user creation pollutes org) |
| eval-10 | sf-security | WORKING-WITH-ISSUES | 2/3 (1 partial) | Severity split present; no explicit blocker-vs-advisory framing; AppExchange checklist N/A in subscriber org |
| eval-11 | sf-debug | WORKING | 3/3 | Triage-only, no trace flags created; namespace-recursion diagnosis |
| eval-12 | sf-campaigns | WORKING | 3/3 | All planted traps caught + 2 bonus findings |
| eval-13 | sf-leads | WORKING | 2/2 (+1 N/A-env) | Fixture defect: CSV lacks the documented wrong-domain emails |

**Aggregate: 11 WORKING, 2 WORKING-WITH-ISSUES, 0 BROKEN.** 31 PASS, 3 PARTIAL, 0 FAIL, 4 N/A(environment) across 38 expectations.

---

## Per-eval grading detail

### eval-01 — sf-apex — WORKING-WITH-ISSUES
- **detects execution mode — PARTIAL.** Run adapted to mcp-plus-code-execution behavior (org tools + workspace bash for the validator) and consulted execution-modes.md, but never explicitly detected/recorded the mode as evals 02/04/09/10 did (run-notes.md).
- **fetches trigger bodies — PASS.** Second Tooling query fetched `Body` for the 5 selected triggers; all returned `(hidden)` — managed IP protection (review-report.md "Scope", run-notes.md step 5).
- **150-point scores with line-level evidence — N/A(environment).** All 36 triggers are managed (kugo2p x34, kugadd x2); zero unmanaged triggers exist, bodies unreadable from a subscriber org. Run honestly reported N/A scores and withheld the validator's bogus 150/150 (review-report.md summary table).
- **no invented class names — PASS.** All names sourced from Tooling queries; scores withheld rather than fabricated (review-report.md "Assumptions Recorded").
- Verdict basis: the run behaved correctly, but the eval exposed severe validator defects (150/150 on the string `(hidden)`; "PASSED, exit 0" despite CRITICAL findings) and a missing managed-code branch in the skill.

### eval-02 — sf-flow — WORKING
- **asks/infers entry conditions — PASS.** `filterFormula: AND(ISPICKVAL($Record.Priority,"High"), OR(ISNEW(), ISCHANGED(Priority)))` — infers create-or-transition scope to avoid clobbering manual reassignment (flow.json:107, flow-report.md).
- **fault path included — PASS.** `faultConnector → Assign_Capture_Fault` on the Get Records plus a null-check decision (flow.json:95, flow-report.md elements 2 and 4).
- **110-point self-check before deploy — PASS.** validate_flow_cli.py run BEFORE deploy: 97/110, plus the four-question pre-deploy check; deployed as Draft and verified not InvalidDraft (flow-report.md).
- Notable: 3 validator-vs-SKILL.md contradictions logged (Auto_ vs Before_ prefix, storeOutputAutomatically stance, fault-variable "unused").

### eval-03 — sf-data — WORKING
- **selectivity considered — PASS.** Optimization checklist table: indexed CloseDate range filter, explicit field list, LIMIT 200, no wildcards/negatives (query-and-results.md "Selectivity & Optimization Notes").
- **THIS_QUARTER date literal — PASS (with note).** Used `THIS_FISCAL_QUARTER` after verifying `Organization.FiscalYearStartMonth = 1`, making it identical to the calendar quarter; assumption recorded (query-and-results.md assumptions 1). Evidence-based, not drift.
- **results table — PASS.** Results table rendered (0 rows) plus a verified empty-result diagnosis (COUNT, CloseDate min/max: org data is 2020–2022) and a reference query with sample matches (query-and-results.md "Results").

### eval-04 — sf-lwc — WORKING
- **PICKLES design pass — PASS.** Full P-I-C-K-L-E-S section with per-letter decisions (component-report.md §2).
- **wire/apex decision explained — PASS.** "Wire vs imperative (honest call)" plus Data Source Decision Tree → no-Apex `getRelatedListRecords` design (component-report.md §2).
- **165-point SLDS check — PASS.** validate_slds.py run pre-deploy on all 3 files, 165/165 each, with honest caveats about the validator over-scoring N/A categories (component-report.md §4).
- Notable: real deploy failure found and fixed (JS must be created first on Tooling bundle create — undocumented in skill); deployed, verified, cleaned up.

### eval-05 — sf-metadata — WORKING
- **field-level security / permission set handling — PASS.** `Inspection_Access` PS with ObjectPermissions + 3 FieldPermissions rows, assigned to verify; skill's "FLS is the Silent Killer" empirically confirmed (creation-report.md "FLS / Permission Set handling").
- **describe verification after create — PASS.** Describe attempted (`get_object_fields`) but connector cache was stale; run escalated to authoritative verification: Tooling CustomField queries, per-field Metadata retrieval, functional SOQL selecting all 3 fields, FieldPermissions query (creation-report.md "Describe / verification evidence"). Cleanup verified.
- Notable: skill's `metadata_create(type="CustomObject")` is a false capability — Tooling REST cannot create CustomObject; run reached SOAP Metadata API via executeAnonymous.

### eval-06 — sf-permissions — WORKING
- **object-permission query path — PASS.** `ObjectPermissions WHERE SobjectType='Opportunity' AND PermissionsDelete=true` → 33 rows (access-report.md "Method").
- **PS + PSG traversal — PASS.** PermissionSetAssignment for all 24 non-profile PSs (0 rows) and PermissionSetGroupComponent membership (0 rows); null-Parent row resolved by follow-up query (access-report.md, run-notes.md).
- **user-level rollup — PASS.** Rolled up to exactly 1 human (Kuldip Hillyer via System Administrator); profile-owned grants counted via `User.ProfileId` — a path the skill omits and the run improvised; inactive users also checked (access-report.md "Bottom line", tables 1–2).

### eval-07 — sf-diagram — WORKING
- **mermaid erDiagram — PASS.** Valid `erDiagram` block, line-by-line grammar-checked; `__metadata__` renamed to `metadata` to dodge a real Mermaid parse bug in the skill's own convention (erd.md, run-notes.md "Mermaid validation").
- **relationship cardinality correct — PASS.** `|o--o{` optional-lookup one-to-many for Account→Contact/Opportunity, self-refs for ParentId/ReportsToId, dashed `|o..o|` one-to-one conversion paths for Lead; correctly notes no Master-Detail among these four (erd.md relationships + Key Points).

### eval-08 — sf-audit — WORKING
- **single scan feeds all documents — N/A(environment).** Eval harness scoped the run to HTML-only ("Word/Excel/12 standalone docs skipped per eval scope"); the single Phase A–C scan fed the one document produced, but multi-document reuse is untestable this iteration (run-notes.md Phase D).
- **scores per component — PASS.** Per-class 150-point scores (82–112/150, mean 94.7) and per-flow 110-point scores (85–92/110) in the report tables (audit-report.html C1 section; grep confirms per-component /150 and /110 rows).
- **HTML single-file with inline CSS/JS and charts (§7–8) — PASS.** 37 KB single file, zero external URLs, inline `<style>`/`<script>`, animated SVG donut gauge, severity bar chart, IntersectionObserver scroll-reveal, count-up numbers, `prefers-reduced-motion` in both CSS and JS (audit-report.html; bash grep: 0 http refs).
- Notable: C9 completeness gate caught a real miss mid-run (10th class body); managed-dominant org handled honestly (inventory-only, no inflated findings).

### eval-09 — sf-test — WORKING
- **test plan matrix before code — PASS.** Phase 2 dimension matrix (positive/negative/boundary/bulk/permissions/async/callouts) precedes the generated class (test-report.md Phase 2).
- **200-record bulk test — PASS.** `updatesAll200AccountsInBulk`: 200 @TestSetup records, assertion over the FULL set (count of all 200 stamped) (test-report.md Phase 3).
- **runAs deny case — N/A(environment).** No restricted profile exists in the bare dev org and creating a User is permanent pollution; descoped with an honest 0/15 in the rubric rather than a faked pass (test-report.md assumptions 2, rubric row "Permission & sharing"). Noted: skill needs a documented descope path.
- **Tooling API run + coverage — PASS.** `runTestsAsynchronous` → poll ApexTestQueueItem → 5/5 pass → ApexCodeCoverageAggregate 100% coverage; cleanup verified to zero residue (test-report.md Phase 5, Coverage, Cleanup).

### eval-10 — sf-security — WORKING-WITH-ISSUES
- **category scan with line evidence — PASS.** 7-category rubric scored with file:line evidence (SiteRegisterController.cls:7 hardcoded ID; MyProfilePageController.cls:36 FLS-less DML) (security-report.md findings M1, M4).
- **blockers vs advisories split — PARTIAL.** Findings are severity-ranked (0 Critical / 0 High / 4 Medium / 4 Low + Notes) with a remediation plan, but there is no explicit blocker-vs-advisory framing; the AppExchange Review Readiness checklist (where that split lives) was not executed because this is a subscriber org, not the packaging org — a defensible environment call, explicitly recorded (security-report.md assumption 3). The evals.json prompt asks about AppExchange readiness; the deliverable answers "audit this org" and defers the packaging-org question.
- **Critical caps the grade — PASS.** Cap rule applied and stated: "No Critical finding, so no grade cap applies"; N/A Lightning category renormalized (69/90 → 77/100) instead of free-lifted (security-report.md score table).

### eval-11 — sf-debug — WORKING
- **triage before trace flags — PASS.** Pure read-only triage; zero TraceFlag/DebugLevel created; the exact trace it WOULD run is specified with cleanup step (diagnosis.md "What is missing (and the trace I would run)").
- **SOQL-in-loop signature identified — PASS.** common-errors.md classification names query-in-loop/recursion as the causes; log-signature checklist includes the SOQL-in-loop signature (repeated SOQL_EXECUTE_BEGIN in METHOD_ENTRY loop); evidence-based pivot to managed-cascade recursion since all code is hidden managed and data volumes rule out row amplification (diagnosis.md Diagnosis + Evidence 6).
- **Diagnosis/Evidence/Fix/Prevention format — PASS.** Exact four headings, with confidence levels and 7 numbered evidence items (diagnosis.md).

### eval-12 — sf-campaigns — WORKING
- **null-guarded ROI math — PASS.** "Every division null/zero-guarded"; formula table computed verbatim in Python (campaign-analysis.md header, run-notes.md).
- **missing-cost campaigns flagged as hygiene finding, not ranked last — PASS.** Both no-cost campaigns (Partner Co-Marketing, User Group Sponsorships) excluded from ROI ranking, listed in a separate pipeline-ranked table, and logged as hygiene finding #1 (campaign-analysis.md).
- **invest/pause recommendations — PASS.** Per-campaign Increase/Maintain/Restructure/Pause table with rationale (campaign-analysis.md Recommendations). Bonus: caught the rollup-vs-detail mismatch (9 vs 10 responses) and missing EndDate on all 12 — traps not even listed in the skill.

### eval-13 — sf-leads — WORKING
- **gap-rate profile before enriching — PASS.** §1 gap-rate table (Phone 58%, Employees 35%, Industry 22%, Website 18%, Title 8%) plus process-fix observations (gaps cluster on 11 companies; Industry inconsistency is an intake problem) before any enrichment proposal (gap-analysis.md §1).
- **wrong-domain emails flagged — N/A(environment, fixture defect).** Programmatic scan of all 40 rows found ZERO literal domain-vs-company mismatches — the generated CSV rebuilds emails from the misattributed company, hiding the planted signal. The run still surfaced the underlying ~10% misattribution as cross-company duplicate pairs (Emma Patel #001/#023, Ethan Ali #008/#040 = 4/40) and flagged all 15 de-anon-sourced emails as unverified (gap-analysis.md §2, run-notes.md issue 1). Fix belongs in the fixture, not the skill run.
- **no writes without approval — PASS.** No Salesforce tools called at all; enrichment is "PROPOSED ONLY"; Phone/LeadSource/populated-Industry explicitly excluded from writes per data-quality rules (gap-analysis.md §4).

---

## Skill fix backlog (deduplicated, ranked by breadth x severity)

| # | Defect | Skills affected | Severity | Fix touches |
|---|---|---|---|---|
| 1 | **Tool-name drift**: SKILL.mds hardcode canonical tools (`org_init`, `soql_query`, `tooling_api_query`, `metadata_create/read/update`, `sobject_describe`, `sobject_dml`, `fetch_more`) that no real connector exposes; every run had to translate to `run_soql_query`/`tooling_execute`/`restful`/`get_object_fields`. `org_init` marked "CRITICAL, always FIRST" is unactionable. Reported by evals 01–13. | All 13 | HIGH — a weaker model calls nonexistent tools or stalls | Every `skills/*/SKILL.md`; centralize a connector-mapping table + "Organization SOQL probe as org_init fallback" in `references/execution-modes.md` and reference it consistently |
| 2 | **Managed-package / hidden-body handling missing**: `Body="(hidden)"` is the norm in subscriber orgs. sf-apex validates the literal string `(hidden)` → 150/150 "safe to deploy"; sf-debug triage assumes readable code and omits the namespace-suffix diagnostic (`...: 101 (kugo2p)`) and per-namespace limit buckets; sf-security's "unless the user owns the namespace" conflates ownership with retrievability. (Evals 01, 10, 11; eval-08's local/managed split is the model to copy.) | sf-apex, sf-debug, sf-security (pattern donor: sf-audit) | CRITICAL — produces false perfect scores | `sf-apex/SKILL.md` + `scripts/validate_apex_cli.py`; `sf-debug/SKILL.md` + `references/common-errors.md`; `sf-security/references/vulnerability-patterns.md` |
| 3 | **Validator bugs**: (a) validate_apex_cli.py — no is-this-Apex sanity check; prints "PASSED, exit 0" despite CRITICAL findings (breaks any pre-deploy hook contract); Architecture 20/20 for logic-in-trigger-body, Testing 25/25 with no tests. (b) validate_flow_cli.py — only knows `Auto_` prefix (contradicts SKILL.md's `Before_` table, suggests a malformed name with spaces); flags `storeOutputAutomatically=true` against SKILL.md's own default; flags fault-path write-only variables as unused; deductions not itemized. (c) validate_slds.py — scores non-applicable categories (GraphQL 15/15 on a CSS file) making perfect scores cheap. (d) template_validator.py hangs >120 s on single-file invocation. (Evals 01, 02, 04.) | sf-apex, sf-flow, sf-lwc | HIGH — exit-code and score contracts are soft | `sf-apex/scripts/validate_apex_cli.py`, `sf-flow/scripts/validate_flow_cli.py`, `sf-lwc/scripts/validate_slds.py`, `sf-lwc/scripts/template_validator.py` |
| 4 | **No non-interactive fallback for AskUserQuestion / approval gates**: hard "MUST use AskUserQuestion" and Phase-B approval gates stall headless runs; every eval had to invent "record assumptions and proceed". (Evals 01, 02, 03, 05, 08 explicitly; pattern universal.) | ~10 skills (all with dispatch/approval gates) | MEDIUM-HIGH | All `SKILL.md` dispatch sections: add "if non-interactive, record assumptions and proceed / halt only on destructive ops" |
| 5 | **sf-metadata false capability + thin deletion**: `metadata_create(type="CustomObject")` cannot work — Tooling REST cannot create CustomObject at any API version (maps to unsupported CustomEntityDefinition); SOAP Metadata API via executeAnonymous is the real path and is undocumented. Deletion gaps: Tooling DELETE of CustomField fails INSUFFICIENT_ACCESS; deleteMetadata is reliable; deletes are soft (15-day holding, `_del` rename); PS delete requires removing assignments first. Also rubric says API >= 65.0 while notes say 62.0+. (Eval 05.) | sf-metadata | CRITICAL for its core promise | `sf-metadata/SKILL.md` (create path, Common Errors table, deletion workflow, rubric consistency) |
| 6 | **Dangling / missing / unwired references**: sf-campaigns references `references/execution-modes.md` and `sf-audit/references/report-template.md §7-8` — neither ships with it; sf-security's execution-modes.md references `mcp-pagination.md` (absent) and `org_init`; sf-diagram never mentions its own most useful file (`erd-conventions.md`) and erd-conventions still cites the removed `query-org-metadata.py`/`sf` CLI. (Evals 12, 10, 07.) | sf-campaigns, sf-security, sf-diagram | MEDIUM — followers dead-end | `sf-campaigns/SKILL.md`, `sf-security/references/execution-modes.md`, `sf-diagram/SKILL.md` + `references/erd-conventions.md` |
| 7 | **N/A-category scoring undefined**: empty rubric categories silently score full marks (sf-security Lightning 10/10 with zero unmanaged components; sf-test async 15/15 with no async surface); sf-audit defines per-domain rubrics but no cross-domain weighting or N/A-domain policy for partial audits. Both runs invented renormalization. (Evals 08, 09, 10.) | sf-test, sf-security, sf-audit | MEDIUM — score inflation | The three rubric sections: add "N/A categories excluded from denominator, renormalize and disclose" |
| 8 | **sf-lwc content bugs**: (a) SKILL.md prose examples use quoted bindings (`lwc:if="{isLoading}"`) — invalid LWC that fails to compile (assets are correct, prose is not); (b) Tooling-API bundle create order undocumented — JS base file must be POSTed first or FIELD_INTEGRITY_EXCEPTION; (c) `targetConfigs` Base64 encoding on Tooling create undocumented. (Eval 04.) | sf-lwc | HIGH — copyable broken markup | `sf-lwc/SKILL.md` (examples, Tooling fallback section symptom table) |
| 9 | **sf-leads demo fixture drift**: leads.csv contains zero literal wrong-domain emails despite SKILL.md demo section and eval brief promising ~10%; the pattern was generated as cross-company duplicates instead. Regenerate CSV (keep true-company email on misattributed rows) or reword the demo section. Also: gap query omits NumberOfEmployees (35% of rows missing it are invisible to the stock query). (Eval 13.) | sf-leads | MEDIUM — advertised trap untestable | `sample-data/leads.csv` (regenerate), `sf-leads/SKILL.md` |
| 10 | **Script discovery fragile**: `${CLAUDE_PLUGIN_ROOT}` unset outside plugin installs; `find ~/.claude/plugins` misses Cowork/eval layouts. (Evals 01, 03, 04.) | sf-apex, sf-data, sf-lwc (pattern shared) | LOW-MEDIUM | Script-location snippets in affected SKILL.mds: "resolve relative to this SKILL.md's directory first" |
| 11 | **Per-skill minors**: sf-permissions — profile-grant user counting via `User.ProfileId` missing (literal following reports 0 users for profile grants), Session-type PS filtering advice, null-Parent caveat, garbled "Salesforce MCP AI MCP Server" description; sf-data — no empty-result verification step, DML-shaped completion format; sf-flow — `/tmp` phrasing (say "scratch directory"), SKILL.md length (1,635 lines, repeated contract); sf-test — deploy-tool naming (document Tooling `sobjects/ApexClass` create + MetadataContainer update), non-filterable-field compile error in common-causes list, runAs descope path in rubric; sf-audit — ValidationRule `ORDER BY EntityDefinition.QualifiedApiName` 500-errors (use EntityDefinitionId), §8 JS lacks reduced-motion guard; sf-campaigns — pipeline-ROI flatters zero-win campaigns (add won-revenue caveat: Reactivation ranked #4 with $0 won), rollup-vs-member-sample note; sf-security — token safety (namespace counts first, bodies for unmanaged only), RemoteProxy queryable-field list, inline-markdown Phase 4 path for Org Audit; sf-diagram — flowchart-vs-erDiagram preference conflict, `__metadata__` Mermaid parse bug; sf-debug — FlowDefinitionView `TriggerObjectOrEventLabel` trap, MCP body-redaction note, flow same-value-update re-fire pointer. | various (1 each) | LOW | Respective SKILL.md / references files |

### Recommended fix order
1 (tool-name drift) → 2 (managed-code handling) → 3 (validator exit-code/scoring bugs) → 5 (sf-metadata CustomObject path) → 4 (non-interactive fallback) → 8 (sf-lwc broken examples/create order) → 6 (dangling refs) → 7 (N/A scoring) → 9 (leads fixture) → 10–11.
