# sf-records v1.0.0 — behavioural smoke test, run notes

**Run:** 2026-08-30, headless subagent. Task prompt: *"Do a data health check on
our Account records — what's wrong, and are there duplicates?"*
**Org:** Kugamon LLC dev org (`00D8c0000041vBHEAY`), 13 Accounts.
**Tools permitted:** `run_soql_query`, `get_object_fields`, `tooling_execute`
on `mcp__salesforce-kugaextra-dev__*` only. **Strictly read-only.**
**Result:** deliverable produced; **zero writes, zero DML, zero merges, zero
metadata changes.**

---

## 1. Was the skill followable?

**Yes — routing and structure worked without ambiguity.**

- **Dispatch** resolved cleanly. The prompt matches the *Inspect* row verbatim
  ("data health check on X"), and it also carries a dedupe question. The
  dispatch table's fallback line — *"An object name alone → Run Inspect and
  offer the other three from the findings"* — gave a clear composition:
  Inspect fully, then Dedupe detection (which is read-only), stop at the
  candidate list. No guessing required.
- **"Always name the object explicitly in the first line of output"** is a good
  rule and easy to comply with.
- **The Inspect 6-step order (volume → completeness → validity → consistency →
  ownership/staleness → duplicate pressure) is the right order.** Steps 1–2
  built the denominator that every later step reports against; without them the
  findings would have been raw counts ("5 records") rather than rates ("38% of
  13"), exactly as the skill warns.
- **The report shape template** (findings table + "Top 5 fixes by value") and
  the **severity ladder** were unambiguous to apply. I reached for CRITICAL
  once (hierarchy cycles) and correctly landed on "clean" instead — the ladder
  discriminates.
- **The Fix proposal table** (Record / Field / Current / Proposed / Evidence)
  plus the mandate that overwrite candidates are *listed separately and off by
  default* is the single most valuable structural rule in the skill. It forced
  the `BillingState = "UK"` fix into a separate batch where it belongs.
- **Dedupe reference** was directly executable: normalization rules, tier
  table, per-object composite keys, the "prefer the org's own rules" query, the
  master-ranking table, the do-NOT-auto-merge list, and the
  *"When not to merge at all"* escape hatch. The last one is what produced the
  correct answer here.

## 2. Did the canon citations resolve?

**Yes — all of them. Verified path-by-path and section-by-section.**

| Citation site | Path as written | Resolves to | ✓ |
| --- | --- | --- | --- |
| `SKILL.md` §Data-quality canon | `../../shared/standards/record-data-quality.md` | `plugins/salesforce-core/shared/standards/record-data-quality.md` | ✓ |
| `references/object-playbooks.md` line 10 | `../../../shared/standards/record-data-quality.md` | same file | ✓ |
| `references/dedupe-strategies.md` §What a merge does | `../../../shared/standards/record-data-quality.md` §6 | same file | ✓ |

Section-anchor check — every `§n` cited in SKILL.md and the references points
at a real, correctly-titled section of the canon:

| Cited | Canon section | Match |
| --- | --- | --- |
| §1 active picklists | *1. Picklists — only existing, ACTIVE values* | ✓ |
| §2 address/code conventions | *2. Address & code conventions* | ✓ |
| §3 field lengths | *3. Field lengths — check before writing* | ✓ |
| §4 "blank beats invented" | *4. Anti-fabrication — empty is honest* | ✓ |
| §5 source attribution | *5. Source attribution — stated, not inferred* | ✓ |
| §6 opt-out / bounce one-way doors | *6. Email verification* (contains the one-way-door paragraph) | ✓ |
| §7 stale records flagged and dated | *7. Departed people — flag, don't delete* (contains "deactivate, don't destroy") | ✓ |
| §8 propose / batch / verify / never overwrite non-null | *8. Write discipline* | ✓ |

The canon reads as genuinely shared, not as a restatement — SKILL.md's decision
to name only §4, §6 and §8 as "load-bearing here" and cite the rest by number
kept the skill short without losing the rules. **No defect found in the canon
wiring.**

One presentational nit: §6 is titled *"Email verification — de-anonymization
data lies"*, but SKILL.md and the Contact playbook both cite it as the
**opt-out/bounce one-way door** rule. That content *is* in §6, but a reader
following the citation lands on a heading about email verification and has to
read to paragraph 2. Consider retitling §6 to name both halves.

## 3. Tool-mapping friction

`references/execution-modes.md` was read first, as instructed. The mapping
table is **correct as far as it goes** and its core warning —
*"Never report a capability as missing because a conventional name isn't
present"* — is exactly right and saved time. `soql_query → run_soql_query`,
`sobject_describe → get_object_fields`, `tooling_api_query → tooling_execute
with query/?q=... (GET)` all mapped and worked on the first attempt.
`org_init`: no init tool on this connector, so the documented fallback
(`SELECT Id FROM Organization LIMIT 1`) was used — that fallback earned its
place.

**But three real frictions, in severity order:**

### F-1 (HIGH) — `sobject_describe` maps to a tool that cannot satisfy Phase 0

Phase 0 step 2 demands: *type, `length`, `nillable`, `updateable`,
`defaultedOnCreate`, `picklistValues[].active`, `calculated`, and
unique/external-Id flags*.

`get_object_fields` on this connector returns **only** `name,label,type,updateable`.
**Six of the eight attributes Phase 0 requires are simply not there.** The
mapping table is not wrong; the skill's Phase 0 is unachievable *through* it,
and the skill offers no fallback.

Workaround I found, which worked and should be documented:

```
tooling_execute GET  query/?q=SELECT QualifiedApiName,DataType,Length,
  IsNillable,IsCalculated,IsIndexed,IsApiGroupable FROM FieldDefinition
  WHERE EntityDefinition.QualifiedApiName='Account' AND QualifiedApiName IN (...)
```

That recovers `length`, `nillable`, `calculated`, and indexability. It does
**not** recover `picklistValues[].active` or `defaultedOnCreate`, and it
returns **no rows at all for compound-address child fields**
(`BillingStreet/City/State/PostalCode/Country`) — so address lengths stayed
unverifiable, which in turn means canon §3's pre-flight cannot be completed for
the most commonly-fixed fields on Account.

**Recommended fix:** add a "if your describe tool returns a thin field list"
row to the execution-modes mapping table naming the `FieldDefinition` Tooling
query, and note the compound-address blind spot.

### F-2 (HIGH) — canon §1's entire verification order is unreachable from the mapped capability set

Canon §1 gives three methods: *best* = UI-API picklist endpoint; *acceptable* =
`GET /sobjects/{Object}/describe`; *the trap* = `GROUP BY`.

Both non-trap methods are raw REST calls that require a generic REST tool
(`restful`). **`restful` does not appear anywhere in the execution-modes
mapping table** — the table maps `sobject_describe` to `get_object_fields`,
which as F-1 shows does not carry picklist values. I also tried
`PicklistValueInfo` as a fourth route: rejected by standard SOQL
(`INVALID_OPERATION: not yet supported by this sObject storage type`) **and**
by Tooling (`INVALID_TYPE: sObject type 'PicklistValueInfo' is not supported`).

Net effect: an agent following this skill with a connector like this one has
**only the method the canon explicitly forbids**. I recorded picklist validity
as an unverified assumption (A1) and proposed no picklist write anywhere —
which is the honest outcome, but the skill should say so rather than leaving
the agent to invent that response.

**Recommended fix:** add `restful` / generic-REST to the mapping table, and add
one line to canon §1: *"If no generic REST tool is available, picklist validity
is unverifiable — say so explicitly and propose no picklist writes."*

### F-3 (MEDIUM) — `DuplicateRule` is not a Tooling object

`dedupe-strategies.md` §"Prefer the org's own rules" gives the
`DuplicateRecordSet` query (worked, 0 rows) but **no query for "does the org
even have duplicate rules configured?"** — which is the more useful question
when the answer to the first is zero. The natural instinct is to look for
config in the Tooling API; that fails:

```
tooling_execute → SELECT ... FROM DuplicateRule
  → INVALID_TYPE: sObject type 'DuplicateRule' is not supported.
```

`DuplicateRule` is a **standard SOQL** object. Worth stating, plus adding the
query itself — it produced a HIGH finding here (2 rules exist, both inactive,
both Lead/Contact, none for Account).

## 4. Instructions that are wrong against a real org

### D-1 (FACTUAL ERROR) — `object-playbooks.md`, Account, "Billing/shipping incompleteness"

> `COUNT(BillingStreet)` vs `COUNT(Id)`

**This query cannot run. `BillingStreet` is a `textarea`, and SOQL refuses
`COUNT()` on textarea, long-text-area, and boolean fields.** Reproduced:

```
SELECT COUNT(Id), ..., COUNT(Description), ... FROM Account
→ MALFORMED_QUERY: field Description does not support aggregate operator COUNT

SELECT COUNT(Id), COUNT(kugo2p__Convert_To_Person_Account__c) FROM Account
→ MALFORMED_QUERY: field kugo2p__Convert_To_Person_Account__c
  does not support aggregate operator COUNT
```

`BillingStreet` and `ShippingStreet` are `textarea` on stock Account, in every
org. So the playbook's headline detection for the single most common Account
finding fails on a stock object. **Fix:** use an aggregatable component
(`COUNT(BillingCity)`, `COUNT(BillingPostalCode)`, `COUNT(BillingCountry)`), or
`SELECT COUNT(Id) FROM Account WHERE BillingStreet = null`.

### D-2 (GENERALISATION OF D-1) — `SKILL.md` Phase 0 step 3 and Inspect step 2

Both state the completeness/shadow-detection technique as *"compare `COUNT(Id)`
to `COUNT(Field)`"*, with the worked example
`SELECT COUNT(Id), COUNT(Amount), COUNT(Contract_Value__c) FROM Opportunity`.
That example happens to use two currency fields and works — but the rule as
written breaks the moment the shadow candidate is a textarea, long text area,
boolean, or encrypted field, which is common for exactly the
`*_Notes__c` / `*_Flag__c` shadows this check is hunting.

**Fix:** one sentence — *"`COUNT(Field)` works only on aggregatable field
types; for textarea, long text area, boolean, and encrypted fields use
`COUNT(Id) … WHERE Field != null`."* This is a two-line change that prevents a
failed first query on most real objects.

### D-3 (INCOMPLETE) — `SKILL.md` Phase 0 step 4, "note the automation surface"

Step 4 lists *"active validation rules, required fields per record type, and
duplicate rules."* It **omits Apex triggers and record-triggered flows** — and
those are what actually mattered here. This org has two active managed-package
triggers on Account:

- `kugo2p.AccountTrigger`
- `kugadd.Accounts` — the Kugamon Address app's **billing↔shipping sync**

That second trigger means every proposed billing-address write will silently
propagate into the shipping fields. Discovering that *before* proposing was the
difference between an honest proposal and a surprise. The skill's own Pitfalls
table already names *"Silent revert after a successful write → attribute to
automation"* — but it puts the discovery in the *verify* step, after the write.
Phase 0 should find it first.

**Fix:** add triggers and record-triggered flows to Phase 0 step 4. Queries
that worked:
`tooling_execute → SELECT Id,Name,TableEnumOrId,Status,NamespacePrefix FROM ApexTrigger WHERE TableEnumOrId='Account'`
and `... FROM FlowDefinition WHERE ActiveVersion.Status='Active'`.

### D-4 (INCOMPLETE) — owner-gap detection misses system users

`SKILL.md` Inspect step 5 and the Account playbook both define the owner check
as `Owner.IsActive = false`. In this org **zero** owners are inactive — yet one
account is owned by the **Automated Process** user (`0058c000009mVsuAAE`),
which is `IsActive = true`. An `IsActive = false` check reports "owners clean"
and misses that nobody human is accountable for that record. The Case playbook
already handles the analogous case (queue-owned, `00G` prefix); Account should
get the system/integration-user equivalent.

### D-5 (DEDUPE STRATEGY GAP) — the Account tier-2 composite finds nothing on the exact population it exists for

`dedupe-strategies.md` gives Account's tier-2 composite as
*normalized `Name` + registrable `Website` domain*. Applied honestly here it
returns **zero groups** — because geography tokens survive the documented
normalization:

```
"United Oil & Gas Corp."       → united oil gas
"United Oil & Gas, Singapore"  → united oil gas singapore
"United Oil & Gas, UK"         → united oil gas uk
```

Three names, three keys, no collision. The thing that actually found the group
was the **domain alone** (`uos.com` ×3), which the reference does not describe
as a tier. I had to invent a "tier 2.5" label for it, then fall to tier 3
(Jaccard 0.75) to justify grouping.

This matters because the *correct* answer here is **not a merge** — it is an
account hierarchy, which `dedupe-strategies.md` anticipates beautifully in
*"When not to merge at all"* (*"two real legal entities that share a name
belong in an account hierarchy"*). But **nothing in the tier table routes you
to that section.** An agent that trusted tier 2 would report "no duplicates" and
miss the finding entirely; an agent that dropped to tier 3 without reading to
the end of the file might propose a destructive merge of three real companies.

**Fix:** add a named signal for *shared registrable domain, different
normalized name*, whose **default recommendation is hierarchy, not merge**, and
cross-link it to *"When not to merge at all"* from the tier table itself.

### D-6 (COSMETIC, low confidence trap) — Person Account detection

The Account playbook trap says *"If `IsPersonAccount` exists on the org, filter
them out."* Correct, and it resolved cleanly (field absent → not enabled). But
this org carries `kugo2p__Convert_To_Person_Account__c`, a package field whose
name would trip a keyword match into a false positive. Minor: consider
*"match on the `IsPersonAccount` field specifically, not on any field mentioning
person accounts."*

### D-7 (COSMETIC) — `execution-modes.md` structure

The *"Headless runs"* section is spliced between the tool-mapping preamble and
the sentence that opens the modes discussion, and that sentence reads
*"All These Salesforce skills support four execution modes"* (capitalisation
error, and the doc then never uses the mode name it told me to record —
`mcp-plus-code-execution` here). Reads like a patch landed mid-document. The
headless rule is important enough to deserve its own top-level position rather
than being wedged in.

## 5. Did the headless / propose-only rules actually stop the writes?

**Yes, unambiguously, and this is the skill's strongest area.**

The three guardrails and how each fired:

1. **SKILL.md §Execution modes:** *"Headless = propose-only. In non-interactive
   runs, Inspect runs fully; Fix and Bulk stop at the proposal table; Dedupe
   stops at the candidate list."* — Followed exactly. Inspect ran to
   completion; Dedupe stopped at the candidate table; no Fix or Bulk write was
   attempted.
2. **SKILL.md:** *"Merges never execute headless under any caller-granted
   permission — a merge cannot be undone by rerunning the skill."* — This is
   the right absolute. Note it was **belt-and-braces** here: the one candidate
   group independently failed four separate items on the do-NOT-auto-merge
   list (tier-3-only match, accounts with children, disagreeing non-null
   fields, different legal entities). Both the headless rule and the merge
   rules had to be wrong simultaneously for a merge to happen.
3. **`execution-modes.md` §Headless runs:** *"Never silently skip a gate —
   record what would have been asked and what was chosen."* — Produced the
   six-row gate table in the report. This is the rule that turns a headless run
   from "the agent decided" into "the agent deferred, here's the queue." It
   works, and it is the reason the country-convention tie (`US`=2 vs `USA`=2)
   became a recorded question rather than a coin flip written into 7 records.

Canon §8's *"never overwrite a non-null value without an explicit instruction"*
independently forced the `BillingState = "UK"` correction into a separate,
off-by-default batch — a second layer that would have held even in an
interactive run.

**No instruction anywhere in the skill, its references, or the canon pushed
toward a write.** The read-only constraint and the skill's own rules never
conflicted.

## 6. What the playbook got right about Account

Worth recording, since the defects above are the exception:

- **Hierarchy integrity** — self-parent and cycle checks were correctly the
  first Account item, and the detection (`ParentId = Id`, then walk) is right.
- **Convention drift** — *"the long tail (`USA`, `U.S.`, `United States` beside
  `US`) is the finding"*. Exactly what appeared: `US`/`USA` split.
- **Ghost accounts** — *"no contacts, no opportunities, no activity, created
  years ago — candidates for flagging, not deletion"*. Found one, verbatim.
- **The `Name` trap** — *"DBAs, subsidiaries, and divisions belong in a
  separate field, not appended to `Name` — appending it is what created the
  duplicate problem in most orgs."* This is precisely the United Oil & Gas
  situation, correctly diagnosed in advance.
- **The reparenting trap** — *"Show the descendant count before any `ParentId`
  write"*. Applied; the answer was 0 today, which is itself the point worth
  reporting.
- **The safe-fix ordering** — conventions first, then completeness fills from an
  authoritative sibling with the source named. That ordering shaped Batches A/B
  and made the evidence column write itself.

## 7. Verdict

**Publishable, after the fixes below.** The skill is well-structured,
correctly scoped against its sibling skills, and its safety rules demonstrably
hold under a headless read-only run. The defects are concentrated in
executability details, not in judgment.

**Must-fix before publish (each is a few lines):**
- **D-1** — `COUNT(BillingStreet)` is not a valid query. Factual error on a
  stock field, in the most-used row of the most-used playbook.
- **D-2** — generalise the same correction to Phase 0 step 3 and Inspect step 2.
- **F-1** — document the `FieldDefinition` fallback; the mapped describe tool
  cannot satisfy Phase 0 as written.
- **F-2** — canon §1's verification order needs a stated fallback when no
  generic REST tool is available.

**Should-fix:**
- **D-3** — add Apex triggers / record-triggered flows to Phase 0's automation
  surface.
- **D-5** — add the shared-domain signal to the dedupe tier table and route it
  to *"When not to merge at all"*.
- **F-3** — add the `DuplicateRule` query and note it is standard SOQL, not
  Tooling.
- **D-4** — extend owner-gap detection to system/integration users.

**Nice-to-have:** D-6, D-7, and the canon §6 retitle.
