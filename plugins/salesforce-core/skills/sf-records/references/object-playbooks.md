# Object Playbooks

Per-object depth for Inspect and Fix. Each section: the fields that matter,
what "good" looks like, the common problems, the safe fix pattern, and the
traps specific to that object.

Every field name below is a **starting hypothesis** — describe the object
first (SKILL.md Phase 0). Orgs rename, shadow, and namespace all of these.
All writes follow the shared canon at
`../../../shared/standards/record-data-quality.md`.

---

## Account

**Fields that matter:** `Name`, `ParentId`, `Type`, `Industry`, `Website`,
`BillingCountry`/`BillingState`/`BillingStreet`/`BillingPostalCode`,
`ShippingAddress` set, `OwnerId`, `NumberOfEmployees`, `AnnualRevenue`,
`RecordTypeId`, and any territory/segment fields the org added.

**Good looks like:** one account per real legal entity; a hierarchy that is a
tree, not a graph; billing address complete enough to invoice; `Website`
populated (it is the dedupe key and the enrichment key); an active owner;
`Type` and `Industry` on active picklist values.

**Common problems**

| Problem | Detection |
| --- | --- |
| Hierarchy cycles / self-parent | `ParentId = Id` directly; deeper cycles by walking `ParentId` up from every parented account and detecting a revisit. Salesforce blocks most direct cycles but data loads and merges create orphaned branches |
| Orphan branches | `ParentId` pointing at a deleted or merged account (query returns no row for the Id) |
| Billing/shipping incompleteness | `SELECT COUNT() FROM Account` for the total, then `SELECT COUNT() FROM Account WHERE BillingStreet != null` per field (`COUNT(BillingStreet)` is invalid — `BillingStreet` is a textarea, and SOQL refuses `COUNT()` on textarea, long text area, and boolean fields; the `COUNT()` + null filter is portable). Also country populated without state, or postal code without street |
| Convention drift in country/state | GROUP BY `BillingCountry` — the long tail (`USA`, `U.S.`, `United States` beside `US`) is the finding (canon §2) |
| Duplicates | Registrable `Website` domain first, then normalized `Name` — and a shared domain with *different* normalized names is a hierarchy question, not a merge. See dedupe-strategies |
| Owner / territory gaps | `Owner.IsActive = false`; **plus** accounts owned by a system or integration user (Automated Process, a named integration login, a data-load user) — those are `IsActive = true`, so an inactive-only check reports "owners clean" while nobody human is accountable. Exclude system users from the owned count and flag them separately. Also accounts with no territory assignment in a territory-managed org |
| Ghost accounts | No contacts, no opportunities, no activity, created years ago — candidates for flagging, not deletion |

**Safe fix pattern:** address conventions and casing first (mechanical, high
volume, low risk); then completeness fills from an authoritative sibling
(a child contact's mailing country, the parent's billing country) with the
source named as evidence; hierarchy repairs one branch at a time with the
affected subtree shown before the write; owner reassignment via Bulk with a
rollback file.

**Traps**
- Reparenting an account can silently reshuffle **sharing and roll-up
  reporting** for the entire subtree. Show the descendant count before any
  `ParentId` write.
- Person Accounts behave as Account + Contact in one record. If
  `IsPersonAccount` exists on the org, filter them out of business-account
  workflows explicitly rather than letting them fall through.
- `Name` is the legal-entity name; DBAs, subsidiaries, and divisions belong
  in a separate field, not appended to `Name` — appending it is what created
  the duplicate problem in most orgs.

---

## Contact

**Fields that matter:** `AccountId`, `FirstName`/`LastName`, `Email`,
`Phone`/`MobilePhone`, `Title`, `ReportsToId`, `OwnerId`,
`HasOptedOutOfEmail`, `DoNotCall`, `EmailBouncedDate`/`EmailBouncedReason`,
`MailingAddress` set, `LastActivityDate`, and any "no longer with company"
flag the org added.

**Good looks like:** every contact attached to an account; a deliverable,
unique, first-party-corroborated email; a title that reflects the current
role; opt-out and bounce state accurate; departed people flagged and dated
rather than deleted.

**Common problems**

| Problem | Detection |
| --- | --- |
| Orphaned / unlinked | `AccountId = null` (only legal in orgs with private contacts enabled — confirm before treating it as a defect) |
| Invalid or shape-broken email | Missing `@`, whitespace, a domain that doesn't resolve to the account's domain |
| Bounced but still mailed | `EmailBouncedDate != null` with the address unchanged since |
| `ReportsTo` cycles | Walk `ReportsToId` from each contact; a revisit is a cycle. Self-report (`ReportsToId = Id`) first |
| Duplicates | Exact `Email` first; then `LastName` + `FirstName` + `AccountId` |
| Stale roles | `LastActivityDate` older than ~18 months with a title unchanged since — likely departed |
| Missing owner or inactive owner | `Owner.IsActive = false` |

**Safe fix pattern:** link orphans to an account only when the email domain
or an existing activity proves the association — otherwise list them for the
user. Fix `ReportsTo` cycles by clearing the weakest link, not by guessing a
new manager. Departed contacts get the flag, the date, and a note (canon §7);
the record stays on the account.

**Traps**
- **`HasOptedOutOfEmail`, `DoNotCall`, and bounce fields are one-way doors**
  (canon §6). Never clear them in a fix or a bulk update. Never let a merge
  choose the more permissive value by accident — check it explicitly in the
  merge preview.
- Deleting a contact takes its activity history with it. Flag instead.
- Contacts under different accounts cannot be merged in the standard UI/API
  path; they must be moved first, which is itself a decision with sharing and
  roll-up consequences.
- Multi-account relationships (`AccountContactRelation`) mean a contact can
  legitimately serve several accounts — check whether the org uses it before
  calling a link "wrong".

---

## Opportunity

**Fields that matter:** `AccountId`, `Name`, `StageName`, `Probability`,
`ForecastCategoryName`, `Amount` (and any custom amount field),
`CloseDate`, `OwnerId`, `IsClosed`/`IsWon`, `Type`, `LeadSource`,
`RecordTypeId`, `LastModifiedDate`/`LastActivityDate`,
`NextStep`, plus `OpportunityLineItem` / quote / order children.

**Good looks like:** open opportunities with a `CloseDate` in the future and
recent activity; stage, probability, and forecast category telling the same
story; an amount that matches whatever field the org treats as authoritative;
closed-won records carrying the downstream artifacts the business requires.

**Common problems**

| Problem | Detection |
| --- | --- |
| Stalled / past-due | `IsClosed = false AND CloseDate < TODAY` — the single most common opportunity finding |
| Stale open pipeline | `IsClosed = false` with `LastModifiedDate` beyond the org's sales cycle (often 30–90 days) |
| Stage / probability incoherence | `Probability` not matching the stage's configured default, or a "Closed" stage with a non-0/100 probability |
| Forecast category mismatch | `ForecastCategoryName` inconsistent with the stage's mapping (e.g. Commit on an early stage) |
| Amount problems | `Amount = null` or `0` on open pipeline; amount disagreeing with line-item totals |
| Missing `CloseDate` or `OwnerId` / inactive owner | Direct null and `Owner.IsActive = false` checks |
| Closed-won without downstream records | Won opportunities with no line items, no contract, no order, no quote — whatever the org's process requires |
| No contact roles | Won or late-stage opportunities with zero `OpportunityContactRole` |

**Safe fix pattern:** never bulk-close or bulk-slip dates. Past-due open
opportunities are a **list handed to the owner**, not a write — the correct
close date is knowledge only the rep has. Fixable without judgment:
probability/forecast realignment to the stage's own configuration, owner
reassignment for inactive users, and backfilling a required field from an
unambiguous parent. Everything involving amount or date is proposed and
individually approved.

**Traps**
- **`Amount` may not be the real number.** Orgs with CPQ, billing, or
  subscription packages usually compute the true value into a custom or
  namespaced field, and `Amount` may hold MRR, a prorated figure, or a
  rollup. Describe first, compare populated rates, and **ask which field is
  authoritative** before reporting or writing anything financial.
- `Amount` becomes read-only once line items exist — it rolls up from
  `OpportunityLineItem`. Proposing a write there is an error.
- Stage changes fire automation: validation rules, flows, approval processes,
  and package logic. A stage "fix" is a business event, not a data edit.
- `Probability` and `ForecastCategoryName` are auto-set from `StageName` on
  the UI path but *not* always on the API path — which is exactly how the
  incoherence gets in, and why the fix is to realign to the stage config
  rather than to invent values.

---

## Case

**Fields that matter:** `AccountId`, `ContactId`, `Status`, `Priority`,
`Origin`, `Type`, `Reason`, `OwnerId` (user **or** queue), `EntitlementId`,
`SlaStartDate`/`SlaExitDate`, `MilestoneStatus` on child milestones,
`IsClosed`, `ClosedDate`, `CreatedDate`, `LastModifiedDate`, and the org's
resolution fields (`Resolution__c`, root cause, `Subject`/`Description`).

**Good looks like:** every case linked to a contact and an account; open
cases owned by someone who is looking at them; entitlement and SLA fields
populated where the org sells support; closed cases carrying a resolution and
a reason so the backlog is analyzable.

**Common problems**

| Problem | Detection |
| --- | --- |
| Missing linkage | `ContactId = null` or `AccountId = null` on cases that should have both |
| Aging open cases | `IsClosed = false` with `CreatedDate` beyond the SLA window; bucket by 30/60/90+ days |
| Stale open cases | `IsClosed = false` with no modification in N days — different finding from aging, and often the more damning one |
| Queue-parked backlog | `OwnerId` starting with `00G` (queue) on cases older than the triage window — nobody owns them |
| Inactive user ownership | `Owner.IsActive = false` on open cases |
| SLA / entitlement gaps | `EntitlementId = null` on accounts that have entitlements; missing `SlaStartDate`; violated milestones |
| Resolution incompleteness | Closed cases with blank resolution/reason fields — kills root-cause reporting |
| Reopen churn | Cases closed and reopened repeatedly (field history or a custom counter) |

**Safe fix pattern:** backfill `AccountId` from `Contact.AccountId` where a
contact is present (unambiguous, high volume, safe). Reassign
inactive-user-owned open cases to the appropriate queue via Bulk with a
rollback file. Missing resolutions on closed cases are a **report to the
support manager**, not an invention (canon §4). Never bulk-close aging cases:
closing fires notifications, surveys, and SLA outcomes.

**Traps**
- `OwnerId` is polymorphic — user (`005`) or queue (`00G`). Queries and
  updates that assume a user break on queue-owned cases, and vice versa.
- Entitlement and milestone changes recalculate SLA clocks. Writing
  `EntitlementId` retroactively can mark historical cases as breached.
- `Status` values drive `IsClosed` through the CaseStatus setup, not the
  other way around — check which statuses are flagged closed before treating
  a status as open.
- Case assignment rules only run when explicitly requested via the API
  header; a fix that expects auto-routing to happen usually gets silence.

---

## Product & Price Book

**Objects:** `Product2`, `Pricebook2`, `PricebookEntry` (PBE),
`OpportunityLineItem` / `QuoteLineItem` as consumers.

**Fields that matter:** `Product2.Name`, `ProductCode`, `IsActive`,
`Family`, `Description`, `ExternalId`;
`Pricebook2.Name`, `IsActive`, `IsStandard`;
`PricebookEntry.Product2Id`, `Pricebook2Id`, `UnitPrice`, `IsActive`,
`UseStandardPrice`, `CurrencyIsoCode` (multi-currency orgs).

**Good looks like:** every sellable product active, with a unique
`ProductCode`, a standard price book entry, and an entry in each custom price
book it should be sold from — in every active currency. Retired products
inactive rather than deleted. Families consistent enough to report on.

**Common problems**

| Problem | Detection |
| --- | --- |
| Active product with no PBE | `Product2` where `IsActive = true` and no `PricebookEntry` — the product is unsellable and invisible in quoting |
| Missing standard-price-book entry | A PBE exists in a custom price book but not the standard one. Salesforce requires the standard entry first; without it the custom entry is invalid |
| Orphaned PBEs | Entries whose `Product2` is inactive or whose price book is inactive — they still appear in some flows |
| Currency coverage gaps | In multi-currency orgs, PBEs missing for currencies in active use — GROUP BY `CurrencyIsoCode` per price book and diff against the org's active currencies |
| Missing / duplicate `ProductCode` (SKU) | Null codes, or the same code on multiple products — breaks every integration keyed on SKU |
| Family integrity | Null `Family`, or near-duplicate family values (`Software` / `software` / `SW`) |
| Bundle integrity | Parent bundle active while a component is inactive or missing a PBE (in orgs with a bundling package) |
| Zero or null `UnitPrice` on active entries | Direct check — usually a load artifact |

**Safe fix pattern:** create missing **standard** price book entries before
any custom-book entry (order matters — the reverse fails). Add currency
coverage by cloning an existing PBE's price only when the org has a stated FX
convention; otherwise list the gaps for pricing to fill (canon §4 — never
invent a price). Deactivate rather than delete retired products. Normalize
`Family` values only after confirming the target list with the user.

**Traps**
- **You cannot delete a `PricebookEntry` or `Product2` that is referenced by
  any line item** — active or historical. Deactivate instead; it is the only
  safe move in a mature org.
- `UseStandardPrice = true` on a PBE means `UnitPrice` is inherited; writing
  `UnitPrice` while that flag is set is rejected or ignored.
- The standard price book is unique and cannot be recreated. In sandboxes it
  is sometimes inactive — check `IsStandard` and `IsActive` before concluding
  entries are missing.
- Pricing is often owned by a managed package (CPQ, revenue, billing). If the
  describe shows namespaced pricing fields, the package owns the number —
  propose nothing there without explicit direction.
- Deactivating a product removes it from new quoting but leaves historical
  line items intact. Say that out loud; it is usually the reassurance that
  unblocks the cleanup.
