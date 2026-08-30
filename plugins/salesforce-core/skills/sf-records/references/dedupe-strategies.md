# Dedupe Strategies

Detection method, per-object keys, and what merging actually does. Detection
is free and reversible; merging is neither. Keep them separate steps with a
user decision in between.

## Normalization (do this before comparing, never after)

| Input | Rule |
| --- | --- |
| Company / account name | lowercase; trim; collapse internal whitespace; strip punctuation; drop legal suffixes (`inc`, `llc`, `ltd`, `limited`, `corp`, `corporation`, `co`, `gmbh`, `bv`, `sa`, `srl`, `pty`, `plc`); drop leading `the` |
| Website | strip scheme, `www.`, path, query; reduce to the registrable domain (`https://www.Acme.com/about` → `acme.com`) |
| Email | lowercase; strip `+tag` before `@`; keep the domain intact (do not fold subdomains) |
| Person name | lowercase; trim; strip punctuation and honorifics; keep hyphens and diacritics (do not ASCII-fold — it merges genuinely different people) |
| Phone | digits only; drop leading country code only when the org is single-country |
| Product code / SKU | trim; case-normalize only if the org's codes are case-insensitive in practice |

State the normalization rules used in the report. A dedupe whose matching
rules aren't stated cannot be trusted, reviewed, or repeated next quarter.

## Matching tiers

**Tier 1 — exact match on a unique key.** Email, ProductCode, an external
system Id, any field the describe reports as `unique` or `externalId`.
Groupable without further evidence; still shown before merging.

```sql
SELECT Email, COUNT(Id) c FROM Contact
WHERE Email != null GROUP BY Email HAVING COUNT(Id) > 1 ORDER BY COUNT(Id) DESC
```

**Tier 2 — normalized composite.** Two independent signals agreeing:

| Object | Composite key |
| --- | --- |
| Account | registrable `Website` domain + normalized `Name` — normalize the website to the registrable domain (`https://www.United-Oil.com/uk` → `united-oil.com`) and the name by stripping legal suffixes **and** trailing geography/division qualifiers (`United Oil & Gas, UK` → `united oil gas`), or the qualifier survives and three copies of one company produce three distinct keys. Fall back to billing city/country when there is no website |
| Contact | `LastName` + `FirstName` + `AccountId`; or `LastName` + email domain |
| Lead | `Email`; else `LastName` + normalized `Company` |
| Opportunity | `AccountId` + normalized `Name` + `CloseDate` within a small window (rare, usually an integration replay) |
| Case | `ContactId` + `Subject` + `CreatedDate` within minutes (duplicate email-to-case) |
| Product2 | `ProductCode`; else normalized `Name` + `Family` |

Groupable, but every group is reviewed by the user before merging.

**Shared-domain signal (Account) — one company's domain, several names.**
Group by registrable `Website` domain alone. When a domain group's normalized
names still differ (`united oil gas` / `united oil gas singapore` /
`united oil gas uk`), that is a **multi-entity group**, and the default
recommendation is an **account hierarchy, not a merge** — see
[*When not to merge at all*](#when-not-to-merge-at-all). Report the group,
name the shared domain as the evidence, and propose a parent account. Do not
drop to tier 3 to justify merging it; three real subsidiaries are not three
copies of one record.

**Tier 3 — fuzzy, last resort.** Token overlap (Jaccard on normalized name
tokens) or edit distance, on names only, with a stated threshold. Never
auto-grouped; every pair is reviewed individually and labelled as fuzzy in
the output. If tier 3 is producing most of your candidates, the honest
finding is "this object has no reliable key" — say that, and recommend an
external Id or a Matching Rule instead of a merge campaign.

**GROUP BY caveats:** `GROUP BY` with `HAVING COUNT(Id) > 1` is the cheapest
detector and works only on directly-groupable fields — not on multi-select
picklists, long text areas, or expressions. For normalized keys, pull the
candidate columns and group in code (code-execution modes) or group on the
raw field first and normalize the smaller result set.

## Prefer the org's own rules

If the org has Duplicate Rules and Matching Rules configured, report what
they already found before inventing a parallel scheme:

```sql
SELECT DuplicateRuleId, COUNT(Id) FROM DuplicateRecordSet GROUP BY DuplicateRuleId
```

`DuplicateRecordItem` gives the member records per set. When that returns
zero, the more useful question is whether the org has any rules configured at
all — and rules that exist but are inactive, or that cover Lead and Contact
but not the object you are cleaning, is itself a finding:

```sql
SELECT DeveloperName, SobjectType, IsActive, MasterLabel FROM DuplicateRule ORDER BY SobjectType
```

`DuplicateRule` is a **standard SOQL object, not a Tooling API object** —
querying it through Tooling returns `INVALID_TYPE`. Use the normal query
tool (or the Metadata path when you need the matching-rule detail).
Aligning with the org's configured rules means your cleanup matches what the
org will keep enforcing after you leave.

## Do NOT auto-merge

- Different record types, currencies, or business units.
- Different owners in a territory-managed org, until ownership is decided.
- Both sides holding **different non-null values in the same field** — that
  is a data decision for a human, not a match decision.
- Accounts with children, until the reparenting consequences are shown.
- Person Accounts; Contacts under different Accounts (Salesforce forbids or
  complicates both — the contact must be moved first, which has its own
  sharing and roll-up consequences).
- Anything matched only at tier 3.
- Records referenced by an active integration keyed on the losing Id, unless
  the integration's mapping is updated in the same change.

## Choosing the master record

Rank candidates and show the reason:

| Signal | Why it wins |
| --- | --- |
| Referenced by integrations / external Id | Changing it breaks systems outside Salesforce |
| Most child records (contacts, opportunities, cases, activities) | Fewest reparent operations, least risk |
| Most complete on the fields that matter | Least data loss |
| Most recent activity | Most likely the record people actually use |
| Oldest `CreatedDate` | Tie-breaker only — age is not quality |

## What a merge actually does

- The losing record is **deleted** (it goes to the recycle bin, but its own
  audit trail does not survive intact).
- Child records — contacts, opportunities, cases, activities, notes,
  attachments — **reparent** to the winner.
- Field values from the loser fill only the winner's **blank** fields, unless
  a value is explicitly chosen per field.
- Up to three records merge at once; all must be the same object type.
- Automation fires on the winner. Flows, triggers, and package logic run.
- **Opt-out, do-not-call, and bounce flags must be checked explicitly** — the
  merge must never land on the more permissive value by accident
  (`../../../shared/standards/record-data-quality.md` §6).

## Merge preview (required before every merge)

```
Merging {N} {Object} records → master {Id} ({Name})
Reason for master: <from the ranking table>

| Field | Winner (Id) | Loser (Id) | Result after merge |
| ... only fields that differ, plus every consent/opt-out field ...

Reparenting: {n} contacts, {n} opportunities, {n} cases, {n} activities
Losing record(s) deleted: {Ids}
Not reversible by rerunning this skill.
```

Ask for confirmation, one group at a time or against an explicitly approved
list. **Never headless.** After each merge, re-query the winner and a sample
of the reparented children and report the result.

## When not to merge at all

Sometimes the right answer is a relationship, not a merge: two real legal
entities that share a name belong in an account hierarchy; a person with two
roles at two companies is two contacts; a genuine repeat case is history, not
noise. Recommend the structural fix instead of destroying a record — and when
the duplicates keep coming back, the durable fix is a Matching Rule, a
Duplicate Rule, or a unique external Id, which is a **sf-metadata** job.
