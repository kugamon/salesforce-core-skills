# Universal Data-Quality Rules for Enrichment Writes

Battle-tested rules for writing enrichment data into any Salesforce org.
These exist because every one of them, violated, produces damage that looks
like diligence: a plausible picklist value nobody can report on, a confident
wrong attribution, a fabricated phone number someone dials.

## 1. Picklists — only existing, ACTIVE values

Never invent a picklist value, never pass a "close enough" string, never
guess. If the value you want doesn't exist: pick the closest existing active
value, or leave the field blank and put the nuance in a text field, or ask
whether the admin wants a new value added (that's a metadata change, not a
record update).

**Verification order:**
- Best: the UI API picklist endpoint —
  `GET /ui-api/object-info/{Object}/picklist-values/012000000000000AAA/{Field}`
  (that Id is the universal Master record type). Returns only currently
  active values in a small payload.
- Acceptable: `GET /sobjects/{Object}/describe` → `fields[].picklistValues[]`
  where `active: true` (large payload — save to file and filter).
- **The trap:** `SELECT Field, COUNT(Id) FROM Object GROUP BY Field` shows
  what's IN the data, not what's ALLOWED. Long-lived orgs carry retired
  values on thousands of rows — a GROUP BY can return 60 values where only
  17 are active. Writing a retired value back is an error that *looks*
  well-researched. A long tail of oddly-specific values is the tell.
- Multi-select picklists: `;` separator, no spaces, every value
  independently active. (They also can't be GROUP BY'd — sample rows
  instead.)

## 2. Address & code conventions — match the org's dominant convention

Country and State fields are usually free-text, so the API accepts anything —
which is exactly why conventions rot. Before writing, check dominance:

```sql
SELECT Country, COUNT(Id) c FROM Lead WHERE Country != null
GROUP BY Country ORDER BY COUNT(Id) DESC LIMIT 20
```

Most orgs converge on 2-letter ISO 3166-1 codes (`US`, `DE`, `FI`) and
2-letter state codes (`TX`, `CA`) — write the dominant format, and note that
the convention can differ per object in the same org (one object may prefer
`UK`, another `GB` — check the object you're writing to).

**Lead addresses use the company HQ**, even when you know the contact sits
elsewhere — it keeps leads deduplicatable and reporting sane. Put the
contact's actual office in `Description` if it's operationally relevant.
Contact mailing addresses are the person's actual office. Can't reliably
determine HQ? Leave the address blank.

## 3. Field lengths — check before writing

255-char "summary" fields are everywhere, and **Text fields reject the whole
write on overflow while textareas truncate silently** — both are failure
modes. Count characters on every capped field before sending. On
`STRING_TOO_LONG`, the error names the field and max — shorten and retry.
When unsure of a limit, query `FieldDefinition.Length` via the Tooling API.

## 4. Anti-fabrication — empty is honest

Without a public source or first-hand evidence, leave it blank. Never invent:
phone numbers (and never write a company switchboard into a direct
Phone/Mobile field), job titles you can't verify, office addresses, revenue
or employee figures, stakeholder names, or a first name reconstructed from
an email prefix. Fabricated fields poison the CRM and create downstream
landmines; blank fields tell the truth.

## 5. Source attribution — stated, not inferred

Machine-set `LeadSource` values record *how the record got created* (web
form, package install, de-anonymization), not *why the person showed up*.
The first real conversation is usually the only moment the true origin is
spoken — capture it then or lose it.

- Correct `LeadSource` only when a source **states** the origin ("our SI
  told us to look at you", "found you on the marketplace", "met you at
  the conference"). Using the platform ≠ marketplace origin; knowing a
  partner ≠ partner referral. Not stated → leave it alone.
- Map to the closest **active** value; carry the specificity the bucket
  can't hold (who referred, which event, which listing) in a companion
  text field — including a trace of the prior value, so first touch vs
  second touch stays auditable.
- **Report attribution changes** with before → after and the quote that
  justified it. Attribution drives spend decisions; changes are never
  silent.

## 6. Email verification — de-anonymization data lies

Lead-gen and visitor-de-anonymization tools frequently attach the wrong
email or domain to a real person. Before trusting (or writing) an email:
corroborate against a first-party source — the address they actually
replied from, or the calendar invite they RSVP'd from. Watch for domain
changes (person moved companies); sending to a dead address can silently
sink a deal.

Opt-out and bounce state are one-way doors: never unset an email opt-out
without explicit re-opt-in evidence from the person; a bounced flag means
treat the address as unverified until a fresh one is corroborated.

## 7. Departed people — flag, don't delete

When research shows a contact left the company: flag it (many orgs have a
"no longer with company" field; otherwise note it in Description with the
date), keep the record attached to the account so history survives, and if
they landed somewhere relevant, that's a **new lead at the new company**
cross-referenced both ways. A departed champion who knows the product is a
referral seed, not dead data. A LinkedIn profile showing a new employer is
departure evidence, not just a title update.

## 8. Write discipline

- **Pre-flight before every batch:** picklists verified active; capped
  fields counted; codes match org convention; nothing fabricated; strong
  existing data not overwritten by weaker findings.
- **Verify after write:** re-query the records. Automation (Flows,
  validation rules, triggers, sync apps) can accept your write (HTTP 204)
  and then revert or overwrite the field. If a value reverts — automation
  owns that field: don't fight it; capture intent in a notes field and
  flag it to the user honestly.
- **New-in-seat signal:** when enrichment surfaces tenure under ~6 months
  in role, that's sales-relevant context worth noting — new leaders carry
  change mandates. But an evaluation leader is a "likely" economic buyer
  until they confirm it — record roles as evidence states them.
- **Log the work:** when enrichment stems from a real interaction (call,
  email), offer to log a completed Task so Activity History reflects it.
