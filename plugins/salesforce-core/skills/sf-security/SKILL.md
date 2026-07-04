---
name: sf-security
plugin: salesforce-core
argument-hint: '[audit|review|fix] [org|class|component] {name} ...'
metadata:
  version: 1.0.0
description: >
  Audits Salesforce orgs and codebases for security vulnerabilities — CRUD/FLS
  enforcement, SOQL injection, sharing violations, hardcoded secrets, unsafe
  Lightning patterns, and PII exposure — with a 100-point scored report and an
  AppExchange security review readiness checklist. Use when the user asks for a
  security audit, security review, vulnerability scan, AppExchange submission
  prep, CRUD/FLS check, or asks "is this code secure".
  Usage: /sf-security [audit|review|fix] [org|class|component] {name} ...
---

# Salesforce Security Audit & AppExchange Review Readiness

Security engineer for the Salesforce platform. Find real vulnerabilities with
line-level evidence, score them, and produce remediation plans — including the
checklist an ISV needs to pass the AppExchange security review.

## Dispatch

| First argument or intent                                | Workflow          |
| ------------------------------------------------------- | ----------------- |
| `audit`, "security audit", "scan the org"               | Org Audit (scored report) |
| `review`, specific class/component names, "is X secure" | Targeted Review   |
| `fix`, "remediate", after a prior audit                 | Remediation       |
| "AppExchange", "security review submission"             | Org Audit + Review Readiness checklist |

## Execution modes

See `references/execution-modes.md`. Initialize the org connection first
(`org_init` convention). Code scanning is dramatically faster in `sfdx-repo`
or `mcp-plus-code-execution` modes where bodies can be grepped locally —
fetch class bodies once, scan many times.

---

## Org Audit

### Phase 1: Inventory

Query the attack surface in parallel (Tooling API):

- `ApexClass` / `ApexTrigger` (Name, Body, Status, NamespacePrefix — exclude
  managed namespaces unless asked)
- `LightningComponentBundle` + resources (LWC), `AuraDefinitionBundle`
- `RemoteSiteSetting`, `NamedCredential`, CSP Trusted Sites
- Sharing model: `EntityDefinition` internal/external sharing defaults for
  objects the code touches
- Connected apps and `@RestResource` classes (public entry points)

### Phase 2: Scan by category

Work through `references/vulnerability-patterns.md` category by category.
For each finding record: file/class, line, category, severity, evidence
(the actual code), and the fix. No finding without evidence — "consider
reviewing sharing" is noise, `AccountService.cls:42 'without sharing' on a
class reachable from @AuraEnabled` is a finding.

Severity scale:

| Severity | Meaning | AppExchange impact |
| -------- | ------- | ------------------ |
| Critical | Exploitable now (injection, auth bypass, secret in code) | Automatic rejection |
| High     | Enforcement missing (no CRUD/FLS, without-sharing exposure) | Rejection likely |
| Medium   | Defense-in-depth gap (missing USER_MODE, broad RemoteSite) | Flagged, must justify |
| Low      | Hygiene (debug logs of record data, commented credentials) | Rarely blocking |

### Phase 3: Score (100 points)

| Category                              | Points | Deduction basis |
| ------------------------------------- | ------ | --------------- |
| CRUD/FLS enforcement                   | 25     | Per object-touching entry point lacking USER_MODE / stripInaccessible / describe checks |
| Injection safety (SOQL/SOSL/dynamic)   | 20     | Per un-bound user input reaching Database.query / search |
| Sharing model                          | 15     | without-sharing classes on user-reachable paths; inherited-sharing absent on service layers |
| Secrets & endpoints                    | 15     | Hardcoded credentials/tokens/endpoints; missing Named Credentials; overly broad Remote Sites |
| Lightning security (LWC/Aura)          | 10     | innerHTML/unsafe eval patterns, missing CSP, unsanitized @AuraEnabled inputs |
| Data exposure & PII                    | 10     | Sensitive fields in debug logs, public sites/guest access leaks, unencrypted PII noted |
| Test & config hygiene                  | 5      | Security paths untested (no runAs), seeAllData, profile-based instead of permission-set access |

Grade bands: 90+ Excellent · 75–89 Good · 60–74 Needs work · <60 At risk.
Any Critical finding caps the grade at "Needs work" regardless of score —
a 92-point org with one hardcoded secret is not "Excellent".

### Phase 4: Report

Produce the scored report in the sf-audit house format (Word/Excel/HTML —
reuse `sf-audit/references/report-template.md` styling, including the §7 visualization minimums — score gauge, category bars, severity distribution chart — and the §8 single-file HTML standard with inline CSS/JS and scroll-reveal animations): executive summary,
score by category, findings table sorted by severity, remediation plan with
effort estimates, and the AppExchange readiness verdict if relevant.

---

## Targeted Review

Same scan categories applied to named classes/components only. Output the
findings table and per-category notes inline (no document generation unless
asked). Offer the org-wide audit when targeted findings suggest systemic
patterns (e.g., every reviewed class missing CRUD checks usually means the
whole codebase is).

## Remediation

For each accepted finding, fix in priority order (Critical → Low):

- CRUD/FLS: prefer `WITH USER_MODE` on SOQL and `as user` DML (API 58+);
  `Security.stripInaccessible` for object graphs; `Schema.describe` checks
  only where user-mode operations aren't available.
- Injection: bind variables always; `String.escapeSingleQuotes` only as a
  last resort for dynamic field lists — and validate against a describe-based
  allowlist instead where possible.
- Sharing: `with sharing` default, `inherited sharing` on service/selector
  layers, `without sharing` only in a narrow, documented system-context class.
- Secrets: move to Named Credentials / External Credentials; never custom
  settings for secrets (visible to admins) — call out Protected Custom
  Settings vs Named Credentials tradeoffs.

Deploy fixes via the MCP metadata tools, then re-run the affected scan
categories to verify the score improved. Hand refactors beyond security
(bulkification, SOLID) to **sf-apex**; test coverage for security paths to
**sf-test**.

---

## AppExchange Security Review Readiness

When the user is preparing a managed package submission, run the org audit
scoped to the package namespace plus `references/appexchange-checklist.md`.
The checklist covers what the review team actually checks: Code Analyzer /
Checkmarx-clean scan expectations, CRUD/FLS on every entry point, sharing
declarations on every class, 75% coverage with meaningful assertions, secure
external integrations (Named Credentials, TLS, no secrets), Lightning
Web Security compatibility, guest user profile lockdown, and the false-positive
documentation format reviewers expect. Output a gap list with the submission
blockers separated from the advisories.

## References

| File | Read when |
| --- | --- |
| `references/vulnerability-patterns.md` | Phase 2 — detection patterns per category with code examples |
| `references/appexchange-checklist.md` | Any AppExchange/ISV submission context |
| `references/execution-modes.md` | Start of session |
