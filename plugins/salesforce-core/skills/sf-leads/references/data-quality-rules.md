# Data-Quality Rules (moved)

The eight universal record-writing rules — active picklists (§1), address and
code conventions (§2), field lengths (§3), anti-fabrication (§4), source
attribution (§5), email verification and opt-out/bounce one-way doors (§6),
departed people (§7), and write discipline (§8) — are shared canon and now
live at:

**`../../../shared/standards/record-data-quality.md`**

Section numbers are unchanged, so existing `§n` citations still resolve.
Read that file before any batch of enrichment writes.

## Lead-specific notes that stay here

- **Lead addresses use the company HQ**, even when you know the person sits
  elsewhere. It keeps leads deduplicatable and keeps geo reporting sane. The
  person's actual office goes in `Description` when it matters operationally.
  (Contact mailing addresses are the opposite: the person's real office.)
- **`LeadSource` is the attribution field enrichment most often gets wrong.**
  Machine-set values record how the record was *created*; the true origin is
  usually spoken once, in the first real conversation. Canon §5 governs — the
  practical rule for this skill is that a web-research finding is never on its
  own sufficient evidence to rewrite `LeadSource`.
- **Converted leads are read-only history.** `IsConverted = true` records
  should be excluded from enrichment gap queries; enrich the resulting
  Contact/Account/Opportunity instead.
- **Enrichment batch size is ≤10**, tighter than the canon's general ≤200,
  because every row carries researched values with per-field citations that a
  human is expected to actually read before approving.

For object-level stewardship — profiling data health, deduplication and
merges, batched corrections, and safe mass updates — use the **sf-records**
skill.
