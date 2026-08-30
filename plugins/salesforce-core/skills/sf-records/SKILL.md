---
name: sf-records
plugin: salesforce-core
argument-hint: '[inspect|dedupe|fix|bulk] {object} [criteria] ...'
metadata:
  version: 1.0.0
  minApiVersion: '60.0'
  domains:
    - Data
    - Administration
  relatedSkills:
    - sf-data
    - sf-leads
    - sf-audit
    - sf-metadata
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
description: >
  Record stewardship for a Salesforce object — profiles data health field by
  field, finds and plans duplicate merges, proposes and applies corrections in
  approved batches, and runs mass updates with a rollback plan. Describe-first
  against the live org, every write proposed before it lands and verified
  after. Use when the user says "clean up my accounts", "find duplicate
  contacts", "what's wrong with our opportunity data", "fix these records",
  "bulk update", "data health check on X", "merge these duplicates", "our
  contacts are a mess", or asks how bad the data on an object is.
  Do NOT use for writing or running queries and DML mechanics (use sf-data), enriching records
  from web research (use sf-leads), campaign performance analysis (use sf-campaigns), or
  org-wide quality audits (use sf-audit).
  Usage: /sf-records [inspect|dedupe|fix|bulk] {object} [criteria] ...
---

# Salesforce Record Stewardship

Data steward for a single object at a time. Answer two questions and nothing
else: **what is wrong with the records on this object, and how do I safely fix
it?** Profiling is free; every write is proposed, batched, verified, and
reversible.

This skill does not own query syntax (sf-data does), web research (sf-leads
does), or org-wide scoring (sf-audit does). It owns the records.

## Dispatch

| First argument or intent | Workflow |
| --- | --- |
| `inspect`, "data health check on X", "what's wrong with our opportunity data", "how bad is it" | Inspect |
| `dedupe`, "find duplicate contacts", "are these the same account", "merge these" | Dedupe |
| `fix`, "clean up my accounts", "fix these records", "fill in the gaps" | Fix |
| `bulk`, "bulk update", "reassign all X to Y", "mass update" | Bulk |
| An object name alone | Run **Inspect** and offer the other three from the findings |

Always name the object explicitly in the first line of output. A stewardship
run that silently drifted from Account to Contact is a run nobody can audit.

## Execution modes

See `references/execution-modes.md` (tool-name mapping preamble and the
headless rule). Initialize the connection first (`org_init` convention).

**Headless = propose-only.** In non-interactive runs, Inspect runs fully;
Fix and Bulk stop at the proposal table; Dedupe stops at the candidate list.
Merges never execute headless under any caller-granted permission — a merge
cannot be undone by rerunning the skill.

---

## Phase 0 — Describe first, always

Never assume a field exists. Before any query, `sobject_describe` the target
object and work from what the org actually has:

1. **Confirm the object.** Custom objects, namespaced objects, and objects
   renamed in the UI all resolve differently — match on API name.
2. **Inventory the fields that matter** for the workflow: type, `length`,
   `nillable`, `updateable`, `defaultedOnCreate`, `picklistValues[].active`,
   `calculated` (formula fields cannot be written), and unique/external-id
   flags (they are your best dedupe keys).
   **If the connector's describe tool returns a thin field list** (some
   return only name/label/type/updateable), recover the rest from the
   Tooling API rather than assuming —
   `SELECT QualifiedApiName, DataType, Length, IsCompound, IsNillable, IsCalculated FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = 'Account'`
   — and see `references/execution-modes.md` for the connector variation and
   the compound-address blind spot.
3. **Find custom fields shadowing standard ones.** Orgs routinely keep the
   real value somewhere else: `Contract_Value__c` beside a stale `Amount`,
   `Industry_Segment__c` instead of `Industry`, a custom
   `Primary_Email__c` beside `Email`. Describe alone never proves shadowing —
   populated-rate sampling does. Take the total once and a populated count per
   candidate field —

   ```sql
   SELECT COUNT() FROM Opportunity
   SELECT COUNT() FROM Opportunity WHERE Amount != null
   SELECT COUNT() FROM Opportunity WHERE Contract_Value__c != null
   ```

   — one query per field, because `COUNT(Field)` is rejected outright on
   textarea, long text area, boolean, and encrypted fields, while `COUNT()`
   with a `!= null` filter works on every filterable type. Add a recency
   comparison, and when a shadow candidate wins on population, **ask which
   field is authoritative before proposing any write to either.** Managed
   packages (CPQ, billing, subscription apps) frequently own the real value
   and recompute anything you write into their field.
4. **Note the automation surface:** active validation rules, required fields
   per record type, and duplicate rules. They decide which of your proposed
   fixes will actually land.
5. **Inventory the code automation on the object** — Apex triggers and
   record-triggered flows, **including managed-package ones** — before
   proposing any write. A managed trigger can mirror or overwrite your fix
   (address-sync packages copy billing into shipping), so finding it now is
   the difference between an honest proposal and a surprise:

   ```sql
   SELECT Id, Name, Status, NamespacePrefix FROM ApexTrigger WHERE TableEnumOrId = 'Account'
   ```

   (Tooling API; pair it with `FlowDefinition` / `FlowDefinitionView` for
   active record-triggered flows on the same object.)

Record the describe findings once and reuse them across the run.

## Data-quality canon

The universal record-writing rules — active picklists, address/code
conventions, field lengths, anti-fabrication, source attribution, email
verification and opt-out/bounce one-way doors, departed people, and write
discipline — are shared canon at
`../../shared/standards/record-data-quality.md`. Read it before the first
write of any run and cite it by section (`§1`–`§8`) instead of restating it.

Three canon rules are load-bearing here and get named explicitly in output:
**§4** (blank beats invented), **§6** (opt-out and bounce flags are one-way
doors — never cleared as a side effect of a bulk update), and **§8**
(propose, batch, verify, never overwrite non-null without instruction).

---

## Inspect — profile an object's data health

Read-only. Produces the map the other three workflows navigate by.

1. **Volume and shape.** `SELECT COUNT() FROM {Object}`, plus counts by the
   object's primary segmentation field (RecordType, Stage, Status, Type) and
   by `CreatedDate` year. Volume decides whether later phases can query
   directly or must chunk.
2. **Completeness per field.** For the fields the playbook flags as
   mattering, take the total once (`SELECT COUNT() FROM {Object}`) and one
   populated count per field
   (`SELECT COUNT() FROM {Object} WHERE {Field} != null`). Use a single
   grouped `COUNT(Field)` query only where every field in it is an
   aggregatable type — `COUNT(Field)` is invalid on textarea, long text
   area, boolean, and encrypted fields, which is exactly what the
   `*_Notes__c` / `*_Flag__c` shadows tend to be, so the `COUNT()` + null
   filter is the portable form. Report as a rate, not a raw number —
   "BillingCountry populated on 41% of 12,400 accounts" is actionable;
   "5,084" is trivia.
3. **Validity.** Picklist values present in data but no longer active
   (canon §1 — GROUP BY the data, diff against the describe's active list;
   the authoritative check is the UI API picklist-values endpoint via a
   generic REST tool, and when the connector has neither that nor a full
   describe, report picklist validity as unverified rather than trusting the
   GROUP BY — see `references/execution-modes.md`);
   country/state codes that violate the org's dominant convention (§2);
   emails failing a shape check; numbers and dates outside plausible ranges.
4. **Consistency.** Cross-field contradictions from the object playbook —
   a closed stage with a future close date, a contact with no account, a
   parent pointing at itself.
5. **Ownership and staleness.** Missing owners, inactive owners
   (`Owner.IsActive = false`), and owners that are not real people —
   integration, system, and Automated Process users are `IsActive = true`
   and pass an inactive-owner check while leaving nobody accountable for the
   record. Exclude them from the "owned" count and flag them as their own
   finding; the same applies to queue ownership where the object allows it.
   Then records untouched past the object's natural clock
   (`LastModifiedDate`, `LastActivityDate`).
6. **Duplicate pressure.** A cheap aggregate on the object's natural key —
   count of keys appearing more than once. Not the full Dedupe run; just the
   size of the problem.

Per-object specifics — which fields, which contradictions, which traps — are
in `references/object-playbooks.md`. Report shape:

```
## Data health: {Object}   ({record count}, {UTC timestamp})

| Finding | Severity | Records | Rate | Fix path |
| ... one row per finding, severity-ranked ...

## Top 5 fixes by value
<what to fix first, why, and which workflow does it>
```

Severity: **CRITICAL** = breaks a business process or a downstream system
(orphaned records, cycles, missing required linkage). **HIGH** = wrong data
that people act on (retired picklist values, invalid amounts, duplicates on a
key). **MEDIUM** = missing data that limits reporting. **LOW** = cosmetic or
convention drift.

## Dedupe — find duplicates and plan merges

Detection is safe; merging is not. These are separate steps with a user
between them.

**Matching strategy, in strength order** (details and per-object keys in
`references/dedupe-strategies.md`):

| Tier | Method | Trust |
| --- | --- | --- |
| 1 | Exact match on a unique/external-id key (Email, ProductCode, an external system Id) | Auto-groupable |
| 2 | Normalized composite — lowercased name stripped of legal suffixes + website/email domain; or LastName + FirstName + AccountId | Groupable, user reviews each group |
| 3 | Fuzzy (token overlap, edit distance) on names only | Last resort; every pair reviewed individually, never auto-grouped |

Between tiers 2 and 3 sits a signal worth naming: **one registrable domain,
several different normalized names.** That is usually subsidiaries, not
copies — the default recommendation is an account hierarchy, not a merge
(`references/dedupe-strategies.md`, *When not to merge at all*).

Normalize before comparing, never after: lowercase, trim, strip punctuation,
legal suffixes (`Inc/LLC/Ltd/GmbH/Corp`) and trailing geography or division
qualifiers, reduce websites to registrable domain, strip `+tags` from emails. Report the normalization rules used — a dedupe whose
matching rules aren't stated can't be trusted or repeated.

**Do NOT auto-merge**, ever:
- Records in different record types, currencies, or business units.
- Records with different owners in a territory-managed org until the owner
  question is answered.
- Records where each side has non-null values in the same field that
  disagree — that is a data decision, not a match decision.
- Accounts with children (contacts, opportunities, cases, hierarchy children)
  until the reparenting consequences are shown.
- Anything matched only at tier 3.
- Person Accounts, or Contacts under different Accounts (Salesforce forbids
  or complicates both).

**Merge is a Salesforce operation with real consequences.** The losing record
is deleted, its child records reparent to the winner, field values from the
loser fill only the winner's *blank* fields unless overridden, and audit
history from the losing record does not survive intact. Merges are
**always user-confirmed, one group at a time or in an explicitly approved
list, and never headless.** Before each merge, present:

| Field | Winner (Id) | Loser (Id) | Result after merge |

plus the child-record counts that will reparent, and the master-record
choice with its reason (oldest, most complete, most activity, the one
integrations reference). Ask before executing. After merging, verify the
winner and its reparented children.

When the org has Duplicate Rules and Matching Rules configured, say so and
prefer them — reporting `DuplicateRecordSet`/`DuplicateRecordItem` findings
is better stewardship than inventing a parallel matching scheme.

## Fix — propose and apply corrections

The default workflow for "clean up my X". Never a single sweeping update.

1. **Scope** the fix to one finding from Inspect (or the user's own
   criteria). One finding per Fix run keeps the proposal reviewable.
2. **Gather evidence** from inside the org: the parent record, a sibling
   field, the org's dominant convention, an existing related record. There is
   no web research here — that is sf-leads.
3. **Propose.** Always this table, never prose:

   | Record (Id / Name) | Field | Current | Proposed | Evidence |
   | --- | --- | --- | --- | --- |

   With a count, the batch plan, and any records deliberately excluded and
   why. Values that would overwrite a non-null field are listed separately
   and are **off by default** — they only proceed on an explicit instruction
   naming that overwrite.
4. **Apply in batches of ≤200 records** (the user may raise it; say what
   you raised it to and why). Stop on the first batch that errors, report
   the error and the partial state, and do not continue automatically.
5. **Verify after write.** Re-query the affected records and compare against
   the proposal. Automation can accept a write (HTTP 204) and revert it —
   when a value reverts, automation owns that field. Report which fields
   reverted, don't retry them, and hand the automation question to sf-flow
   or sf-apex (canon §8).
6. **Report** applied / reverted / failed / skipped with counts.

## Bulk — safe mass updates

For deliberate, large, uniform changes: owner reassignment, status
transitions, backfilling a new field, applying a convention.

1. **Dry-run counts first.** Run the selection as `COUNT(Id)` before
   selecting rows, and show the user the number *and* the exact criteria.
   If the count differs materially from what the user expected, stop and
   reconcile — a mass update on a wrong filter is the single most expensive
   mistake in this skill's territory.
2. **Rollback plan before the first write.** Query and preserve `Id` plus
   the prior value of every field being changed, and keep it where the user
   can reach it (a file in code-execution modes; an in-context table capped
   to a reviewable size otherwise). State plainly what rollback restores
   (field values) and what it cannot (deletions, merges, fired automation,
   sent emails, downstream integration events).
3. **Chunk.** ≤200 records per call; sequence chunks and log which chunk
   ranges succeeded so a partial failure is resumable rather than
   re-runnable from zero.
4. **Guardrail-hook awareness.** The plugin's PreToolUse guardrails flag
   broad destructive DML and high-risk permission payloads and can turn a
   write into an explicit confirmation prompt. Expect it, don't work around
   it, and never restructure a call purely to slip under a threshold — if a
   guardrail fires, that is the moment to re-confirm scope with the user.
5. **Never mass-update** opt-out, bounce, or consent fields (canon §6);
   audit/system fields; or fields owned by a managed package, without a
   named, explicit instruction for that specific field.
6. **Verify** a sample of at least 20 records (or all, if fewer) after each
   chunk, and the full set at the end.

Deletion is not a Bulk operation in this skill. Stale records get flagged and
dated (canon §7); when the user genuinely wants deletion, hand off to sf-data
with the scoped Id list and the rollback caveat stated.

## Pitfalls

| Pitfall | Handling |
| --- | --- |
| Field assumed, not described | Phase 0 is not optional — a proposal citing a nonexistent field discredits the whole run |
| Custom field shadowing the standard one | Populated-rate comparison, then ask which is authoritative before writing either |
| Managed-package field (CPQ, billing) | Describe shows the namespace; the package usually recomputes it — propose nothing there without the user's say-so |
| Formula / roll-up / auto-number field in a proposal | `calculated == true` fields are not writable — fix the inputs instead |
| Retired picklist value written back | Diff data values against the describe's `active: true` list (canon §1) |
| Validation rule rejects the whole batch | Read active rules in Phase 0; on `FIELD_CUSTOM_VALIDATION_EXCEPTION`, report the rule name rather than retrying |
| Record types change what's required and allowed | Verify picklists and required fields against the record's own RecordTypeId |
| Merge across different Accounts / Person Accounts | Not auto-groupable; explain the constraint instead of attempting it |
| Silent revert after a successful write | Verify step; attribute to automation, hand to sf-flow / sf-apex |
| Large object (500k+ rows) | Aggregate-only profiling, chunked selection, and offer to narrow scope before enumerating rows |

## Cross-skill handoffs

- Query syntax, selectivity, DML execution mechanics, deletions → **sf-data**
- Filling gaps from web research (titles, industries, company data) →
  **sf-leads**
- Campaign and member performance analysis → **sf-campaigns**
- Org-wide quality scoring and client-ready audit documents → **sf-audit**
  (also its `report-template.md` §7–8 when the user wants a document)
- The automation that reverts your writes → **sf-flow** / **sf-apex**
- Missing fields, picklist values, or duplicate rules that the data needs →
  **sf-metadata** (a metadata change, not a record update)

## References

| File | Read when |
| --- | --- |
| `references/object-playbooks.md` | Inspect and Fix — per-object fields, "good", problems, safe fix patterns, traps |
| `references/dedupe-strategies.md` | Dedupe — matching tiers, normalization, per-object keys, merge mechanics |
| `references/execution-modes.md` | Start of session — tool mapping, headless rule |
