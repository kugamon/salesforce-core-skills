# sf-records

Record stewardship for a Salesforce object — what's wrong with the data, and
how to safely fix it. Describe-first against the live org; every write is
proposed before it lands, batched, verified after, and never overwrites a
non-null value without being told to.

## What it does

| Action | Description |
| --- | --- |
| `inspect` | Data-health profile of one object: volume, per-field completeness, validity (retired picklist values, convention drift), cross-field contradictions, ownership and staleness, duplicate pressure — severity-ranked with the top fixes by value |
| `dedupe` | Duplicate detection in three tiers (exact key → normalized name+domain → fuzzy last resort), a stated normalization scheme, and a merge preview showing field outcomes and reparenting counts. Merges are always user-confirmed, never headless |
| `fix` | One finding at a time: propose (record, field, current → proposed, evidence), apply in batches of ≤200, verify by re-query, report what automation reverted |
| `bulk` | Mass updates with dry-run counts first, a rollback plan capturing prior values, chunked execution, and guardrail-hook awareness |

Per-object depth for Account, Contact, Opportunity, Case, and Product & Price
Book lives in [references/object-playbooks.md](references/object-playbooks.md).
The universal record-writing rules are shared canon at
`../../shared/standards/record-data-quality.md`.

## Examples

- "Data health check on Opportunity — what's wrong with our pipeline data?"
- "Find duplicate contacts and tell me which ones are safe to merge"
- "Clean up my accounts — the billing countries are a mess"
- "Bulk reassign all open cases owned by inactive users to the support queue"

## Not this skill

Query and DML mechanics → **sf-data**. Enriching records from web research →
**sf-leads**. Campaign performance → **sf-campaigns**. Org-wide quality
audits → **sf-audit**.

## License

MIT License — see [LICENSE](LICENSE) for details. For credits see [CREDITS](CREDITS.md).
