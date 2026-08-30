---
name: sf-leads
plugin: salesforce-core
argument-hint: '[find|enrich|report] {lead-name|criteria} ...'
metadata:
  version: 1.0.0
description: >
  Enriches Salesforce Lead and Contact records with verified data from web
  research — titles, industries, websites, company size, LinkedIn profiles —
  writing back via a Salesforce MCP server with per-field source citations
  and user approval before every update. Use when the user asks to enrich
  leads or contacts, fill in missing lead data, research a lead's company,
  update lead info from the web, or fix incomplete lead records.
  Usage: /sf-leads [find|enrich|report] {lead-name|criteria} ...
---

# Salesforce Lead & Contact Enrichment

Research-driven enrichment: find records with gaps, verify facts from public
sources, and update Salesforce only with citations attached and approval
given. Accuracy beats completeness — a wrong Industry is worse than a blank
one.

## Dispatch

| Argument or intent                         | Workflow |
| ------------------------------------------ | -------- |
| `find`, "which leads need enrichment"      | Gap Analysis |
| `enrich` (+ name or criteria)              | Enrich |
| `report`, after a batch                    | Results Report |

Initialize the org connection first (`org_init` convention — see
`references/execution-modes.md`) — unless running in Demo mode (below),
which has no org to connect to.

## Gap Analysis

```sql
SELECT Id, FirstName, LastName, Company, Title, Email, Phone, Industry,
       LeadSource, Website, NumberOfEmployees, Status
FROM Lead
WHERE IsConverted = false
  AND (Title = null OR Industry = null OR Website = null
       OR NumberOfEmployees = null)
ORDER BY CreatedDate DESC LIMIT 20
```

Adapt the WHERE to the user's criteria (status, source, owner, recency).
Report the gap profile — which fields are missing at what rate — before
enriching; sometimes the answer is a process fix, not 500 enrichments.

## Enrich

Per record, in order:

1. **Identify uniquely.** Name + company must resolve to one real person.
   Ambiguous (common name, no company domain, multiple matches) → skip and
   say why. Never guess identities.
2. **Research** via web search / page fetch (and a LinkedIn tool when
   connected): official company website, industry (from what the company
   actually does, mapped to the org's Industry picklist values — fetch them
   via describe, don't invent new ones), current title, employee-count
   band, person and company LinkedIn URLs.
   Apply `references/data-quality-rules.md` throughout: active-picklist
   verification (§1), org-dominant address/code conventions and HQ rule
   (§2), field-length checks (§3), first-party email corroboration (§6),
   and stated-not-inferred source attribution (§5).
3. **Record confidence + source per field.** High = company's own site or
   the person's own profile. Medium = third-party databases. Low = inference
   — Low-confidence values are presented but not written unless the user
   opts in.
4. **Propose, then write.** Show the proposed field changes as a table
   (current → proposed, source, confidence). On approval, update via the
   MCP DML tool in batches of ≤10. NEVER overwrite an existing non-null
   value unless explicitly asked — enrichment fills gaps, it doesn't
   relitigate CRM history.
5. **Verify after write.** Re-query the updated records — Flows, validation
   rules, and sync automations can accept a write and then revert it. If a
   field reverts, automation owns it: capture intent in a notes field and
   tell the user rather than retrying (data-quality-rules §8).

Contacts: same workflow against Contact (Account.Website often answers
company questions — check inside Salesforce before searching outside).

## Results Report

| Name | Company | Fields updated | Source | Confidence |
| ---- | ------- | -------------- | ------ | ---------- |

Plus: records skipped (with reasons), low-confidence findings awaiting a
decision, and any picklist values that had no good match (data model
feedback for the admin).

When the user wants a document deliverable, follow the sf-audit skill's
`references/report-template.md` (from this skill:
`../sf-audit/references/report-template.md`) §7–8 rather than inventing a
report format.

## Rules (non-negotiable)

- User approval before every write — no silent updates
- Source URL attached to every written value
- No identity guesses; skip ambiguous records loudly
- Existing data wins unless the user says otherwise
- Batches ≤10 records; respect API limits
- PII discipline: enrich business data (title, company, industry) — do not
  hunt personal phone numbers, home addresses, or private accounts
- Opt-out is a one-way door: never unset an email opt-out without documented
  re-opt-in; bounced addresses are unverified until corroborated first-party
- Departed contacts: flag, never delete — and spawn a cross-referenced lead
  at the new company when relevant (data-quality-rules §7)

## References

| File | Read when |
| --- | --- |
| `references/data-quality-rules.md` | Before any batch of writes — picklist, convention, attribution, and verification rules |
| `references/execution-modes.md` | Start of session |

## Cross-skill handoffs

- Bulk data quality beyond enrichment → **sf-data** / **sf-audit**
- Campaign-sourced lead performance → **sf-campaigns**

## Custom-field discernment (customized orgs)

Orgs frequently track lead data in custom fields the standard gap query
won't see — a custom `Industry_Segment__c` used instead of `Industry`, a
`LinkedIn_Profile__c`, a custom company-size picklist. Before gap analysis
in an unfamiliar org, describe Lead/Contact, spot populated custom fields
that shadow the standard ones (populated-rate sampling, as in
data-quality-rules §1-2 verification style), and confirm with the user
which fields the org actually maintains. Enriching a standard field the
org ignores creates the illusion of data quality without the substance.

## Demo mode (no org)

The repo ships synthetic leads at `sample-data/leads.csv` with realistic
gaps and ~10% wrong-domain emails. When no Salesforce MCP server is
connected — or the user asks for a demo — run gap analysis and enrichment
proposals against that CSV (research steps simulated or run for real;
writes proposed only, since there's no org). Skip `org_init` in demo mode —
there is no org to initialize.
