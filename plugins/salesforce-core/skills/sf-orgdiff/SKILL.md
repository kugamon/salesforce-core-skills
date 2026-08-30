---
name: sf-orgdiff
plugin: salesforce-core
argument-hint: '[drift|release|baseline] {source-connector} {target-connector} [scope] ...'
metadata:
  version: 1.0.0
  minApiVersion: '60.0'
description: >
  Compares two connected Salesforce orgs through their MCP connectors —
  inventory-first metadata diffing across Apex, Flows, objects/fields,
  validation rules, permission sets, layouts, labels, endpoints, and
  installed packages — producing a drift report with severity flags and a
  reconciliation plan. Strictly read-only on both orgs. Use when the user
  asks "what drifted", "compare orgs", "sandbox vs production", "did the
  release deploy everything", "compare against baseline", pre/post-release
  verification, or any question about differences between two orgs.
  Usage: /sf-orgdiff [drift|release|baseline] {source-connector} {target-connector} [scope] ...
---

# Salesforce Org-to-Org Diff

Comparison specialist for two live Salesforce orgs reached through two MCP
connectors. Inventory both sides cheaply, diff the inventories, fetch bodies
only for the narrow shortlist that actually differs, and hand back a drift
report that says what changed, which direction, and what to do about it.

**READ-ONLY, always, on both orgs.** This skill never writes to either org —
no DML, no metadata deploys, no Tooling POSTs. Reconciliation is a *plan*
handed to sf-metadata, never an action taken here. There is no mode or
argument that relaxes this.

## Dispatch

| First argument or intent                                          | Workflow |
| ----------------------------------------------------------------- | -------- |
| `drift`, "what drifted", "sandbox vs production", "out of sync"   | Drift Check |
| `release`, "did the release deploy everything", "post-deploy diff" | Release Verification |
| `baseline`, "compare against baseline", "customer org vs our demo" | Baseline Comparison |
| Two connector names with no mode word                             | Ask which mode — the report reads differently in each |

All three modes share the same engine (Phases 0–4 below); the mode changes
which differences are *findings* and which are *noise*. Never guess the
mode: a prod-only Apex class is a red flag in `drift` and expected
background in `baseline`.

## Two connectors, one direction

Every run names two connectors explicitly:

- **Source** — the org whose state is the "newer" or "reference" side
  (sandbox in drift, the org you deployed FROM in release, the reference/demo
  org in baseline).
- **Target** — the org being measured against it (production in drift, the
  org you deployed TO in release, the customer org in baseline).

A reversed diff is a wrong diff — "5 flows newer in sandbox" and "5 flows
newer in production" demand opposite actions. That is why Phase 0 is not
skippable.

## Execution modes

See `references/execution-modes.md` — including the Tool-name mapping
preamble (the tool names below are capability conventions) and the headless
rule. This skill runs the init/verify step **twice**, once per connector,
and every subsequent call must state which connector it targets. In headless
runs the whole skill proceeds without gates *except* identity confirmation:
if the two connectors cannot both be identity-verified (Phase 0), stop and
report — a headless diff against unverified orgs is worse than no diff.

---

## Phase 0 — Identity confirmation (mandatory)

Query **each** connector before any inventory work:

```sql
SELECT Id, Name, InstanceName, IsSandbox, OrganizationType,
       NamespacePrefix, TrialExpirationDate
FROM Organization
```

Then present both identities side by side and confirm the direction:

| | Source | Target |
| --- | --- | --- |
| Connector | my-sandbox | my-production |
| Org Name / Id | ... / 00D... | ... / 00D... |
| Instance / IsSandbox | ... / true | ... / false |

Hard checks, in order:

1. **Same-org-twice:** identical `Organization.Id` on both connectors means
   the user pointed both arguments at the same org (or two connectors share
   credentials). Stop immediately — a self-diff always reports "no drift"
   and gives false confidence.
2. **Direction sanity:** in `drift` mode, if the *source* has
   `IsSandbox = false` and the *target* `IsSandbox = true`, ask before
   proceeding — the user probably reversed the arguments. Ask, don't assume:
   prod-as-source is legitimate in some workflows (seeding a fresh sandbox).
3. **API-version skew:** fetch `GET /services/data/` (versions list) via the
   connector's **generic REST tool** if it has one (e.g. `restful`). Note:
   `tooling_api_query`-style tools are rooted at the Tooling base path and
   **cannot** reach `/services/data/` — do not attempt the check through
   them. If no generic REST tool is available, record "version skew
   unverified" in the report header and proceed at the lower assumed
   version. When versions are known to differ, run all comparison queries
   at the **lower** common version so both sides see the same field
   surface — a field that exists only at the newer API version would
   otherwise show up as fake drift.
4. **Interactive confirmation:** in interactive runs, get an explicit "yes,
   that direction" from the user before Phase 1. Headless: verify 1–3,
   record the assumed direction in the report header, and continue.

Every report begins with this identity table plus the run timestamp (UTC).
A diff without provenance cannot be trusted a week later.

**Aborted-run report shape.** When Phase 0 fails (one connector cannot be
identity-verified, or a hard check trips), still emit a report — this exact
shape, nothing improvised:

```
## Org Diff: ABORTED at Phase 0   (<mode>, <UTC timestamp>)
<identity table — render the failed side's cells as UNVERIFIED>

## Attention flags
| CRITICAL | Run integrity | <which connector failed and how (e.g.
  auth/session error on target connector 'my-production'); no comparison
  was performed> |

Remediation: re-authenticate the failed connector, then rerun the exact
same command. Never substitute a different connector for the same org.
```

## Phase 1 — Scope

Default domains and the user's controls:

| Domain | Default in drift/release | Default in baseline | Scope keyword |
| --- | --- | --- | --- |
| Apex classes + triggers | yes | yes | `apex` |
| Flows (versions + status) | yes | yes | `flows` |
| Objects + fields | yes | yes | `objects` |
| Validation rules | yes | yes | `validation` |
| Permission sets | yes | no (usually customer-specific) | `permissions` |
| Layouts + FlexiPages (counts/names) | yes | no | `layouts` |
| Custom labels | yes | no | `labels` |
| Remote sites + named credentials | yes | yes | `endpoints` |
| Installed packages (versions) | yes | yes | `packages` |

`scope` in the arguments (e.g. `/sf-orgdiff drift dev prod apex,flows`)
limits the run to those domains. Honor it strictly — a scoped run that
"helpfully" scans everything burns API calls on large orgs and buries the
answer the user asked for.

## Phase 2 — Inventory (both orgs, cheap fields only)

Follow `references/diff-method.md` for the per-domain queries. The
discipline that makes this skill viable on real orgs:

- **Counts before rows.** `COUNT()` each domain on each org first. The
  counts alone are a first-cut diff signal and they size the pagination.
- **Never fetch bodies during inventory.** Names, versions, lengths, and
  dates are enough to classify 95%+ of items. Bodies wait for Phase 4.
- **Paginate defensively.** Domains over ~200 rows: `ORDER BY Name` with
  keyset pagination (`WHERE Name > :last`). Tooling OFFSET caps at 2000 —
  keyset works at any size, so prefer it from the start.
- **Interleave, don't serialize.** Query domain N on source and target
  back to back so partial results are still comparable if the run is cut
  short.

## Phase 3 — Compare inventories

Join each domain on its identity key (`NamespacePrefix` + API name — see
diff-method) and bucket every item:

| Bucket | Meaning | Cost to produce |
| --- | --- | --- |
| **Only in source** | Exists in source, absent in target | Free (set difference) |
| **Only in target** | Exists in target, absent in source | Free |
| **Both, different** | Present in both; a checksum-ish field differs (`LengthWithoutComments`, `ApiVersion`, active version number, field count, `Active` flag, endpoint URL, package version) | Free |
| **Both, touched** | Only `LastModifiedDate` differs | Free — report as low-signal |
| **Identical** | All compared fields match | Not listed individually |

**Managed packages: compare versions, never contents.** Anything with a
`NamespacePrefix` belonging to an installed package is compared solely via
the package-version table. Managed bodies are hidden or irrelevant, and
"drift" inside a managed namespace just means different installed versions
— say that in one line instead of fifty.

## Phase 4 — Body fetch (shortlist only)

Only for **Both, different** items that are unmanaged, and only where a body
diff changes the recommendation (Apex, validation rule formulas, labels).
Cap at ~20 bodies per run before checking in with the user — beyond that the
right deliverable is the shortlist itself, handed to sf-metadata or a CLI
retrieve for a file-level diff. Some connectors redact `Body` in Tooling
*query* results; fetch via `GET .../tooling/sobjects/<Type>/<Id>` per the
mapping preamble before concluding a body is unavailable.

---

## Drift report

Always this shape:

```
## Org Diff: <source name> → <target name>   (<mode>, <UTC timestamp>)
<identity table from Phase 0>

## Summary
| Domain | Only in source | Only in target | Modified | Touched |
| ... one row per scoped domain, zeros included ...

## <Domain> detail   (one section per domain with findings)
<table: item, key fields both sides, what differs>
<the actionable read, e.g. "5 flows have higher active versions in
 sandbox — likely pending deployment" or "2 validation rules active in
 prod only — created directly in prod?">

## Attention flags
<severity-ranked list, see below>

## What to do
<3-6 concrete next steps with skill handoffs>
```

**Severity model** — direction is what makes a difference dangerous:

| Flag | Pattern | Why it ranks high |
| --- | --- | --- |
| CRITICAL | Target(prod)-only or prod-newer changes in drift mode | Hotfix drift: changes made directly in prod will be **overwritten by the next deployment** unless back-promoted |
| CRITICAL | Expected release item absent in target in release mode | The deploy silently didn't land it |
| HIGH | Endpoint drift (RemoteSite/NamedCredential URLs differ) | Integrations point at different systems — data goes to the wrong place |
| HIGH | Permission set present/different across orgs | Access drift is a security finding, not a hygiene one → sf-security |
| MEDIUM | Managed package version skew | Behavioral differences with no visible metadata diff |
| MEDIUM | Flow active-version skew, source newer | Pending deployment — expected in drift, a finding in release |
| LOW | Touched-only items (dates differ, content signals equal) | Often no-op saves, comment edits, or sandbox-refresh artifacts |

Prod-only changes are called out by name every time. They are the dangerous
kind of drift precisely because everyone's deployment tooling looks the
other way.

## Mode-specific reads

- **Drift:** the question is "what will the next deployment overwrite, and
  what hasn't been promoted yet?" Source-newer = pending deployment;
  target-newer/target-only = hotfix drift. If the sandbox was recently
  refreshed, say so — a refresh copies prod's timestamps, so only
  differences dated *after* the refresh are true drift.
- **Release:** run twice around a deploy (or once after, against the source
  org the release was built in). The report pivots to a checklist: every
  item in the release scope must appear in target with matching
  version/length, and flows must be not just present but **active** at the
  expected version — "deployed but latest version inactive" is the classic
  half-landed release.
- **Baseline:** customer org vs reference. Only-in-target items are usually
  legitimate customer customization — inventory them neutrally. Findings are
  reference items *missing* or *modified* in the customer org, and package
  version gaps. Recommend, don't scold: this mode feeds an upgrade or
  enablement conversation.

## Pitfalls

| Pitfall | Handling |
| --- | --- |
| Same org behind both connectors | Phase 0 hard stop on identical Org Ids |
| Connectors pinned to different API versions | Query both at the lower common version (Phase 0 §3) |
| `LastModifiedDate` timezone confusion | API datetimes are UTC on both sides — compare raw; never render them in local time inside comparison tables without labeling the zone |
| Tooling object not queryable on a connector (e.g. `InstalledSubscriberPackage`, `EntityDefinition` quirks) | Fall back per the Tool-name mapping preamble in `references/execution-modes.md`; diff-method lists a fallback per domain. Degrade the domain to "partial" in the summary rather than dropping it silently |
| `EntityDefinition` doesn't support queryMore/deep OFFSET | Keyset-paginate on `QualifiedApiName` (see diff-method); plain `COUNT()` generally works and can drive the counts-first pass |
| Connector auth failure / expired session on ONE side | Hard stop (Phase 0 identity gate). Emit the aborted-run report: identity table with UNVERIFIED on the failed side, a CRITICAL run-integrity flag naming which connector failed, and the remediation line (re-authenticate that connector, rerun the same command). **Never substitute a different connector that reaches the same org** — it silently breaks the run's org rules |
| Equal lengths, different dates | Classify as Touched, not Modified — `LengthWithoutComments` unchanged usually means comments/no-op |
| Huge orgs (10k+ fields, 1k+ classes) | Counts-first guard in Phase 2; offer to narrow scope before inventorying a domain whose count exceeds ~2,000 rows per side |

## Document deliverables

When the user asks for a document (HTML/DOCX/XLSX) rather than a chat
report, follow the sf-audit report template — sections 7 (Visualization
Requirements) and 8 (HTML Deliverable Standards) — at
../sf-audit/references/report-template.md. The summary table becomes the
category-breakdown visual; attention flags become the severity distribution
and top-N offenders.

## Cross-skill handoffs

- Deep quality scoring of either org's code/flows → **sf-audit**
- Deploying the reconciliation (promote source-newer items, back-promote
  hotfixes) → **sf-metadata**
- Permission-set drift → **sf-security** (treat as a security review input)
- "Why does this class differ" root-causing → **sf-apex** / **sf-flow**

## References

| File | Read when |
| --- | --- |
| `references/diff-method.md` | Phase 2 onward — per-domain queries, keys, comparison fields, fallbacks |
| `references/execution-modes.md` | Start of session — tool mapping, headless rule |
