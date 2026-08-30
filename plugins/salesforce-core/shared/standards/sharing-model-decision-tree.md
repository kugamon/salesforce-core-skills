# Sharing Model Decision Tree

Which sharing declaration goes on an Apex class, how it interacts with
org-wide defaults (OWD), and when `runAs` tests stop being optional. This is
the canon behind sf-security's Sharing category and sf-test's
permission-testing rubric line.

## The declaration choice

Walk top-down; first match wins:

1. **Is this an entry point a user reaches directly?** (Controller,
   `@AuraEnabled`, `@InvocableMethod`, REST resource, trigger handler on
   user-initiated DML)
   → **`with sharing`**. Record visibility follows the running user. This is
   the default posture; deviation needs written justification.

2. **Is this a service/selector/domain layer called BY entry points?**
   → **`inherited sharing`**. It adopts the caller's context — `with sharing`
   when called from a controller, system context when called from system
   code. Crucially, `inherited sharing` defaults to `with sharing` when it IS
   the entry point, unlike an omitted declaration (which silently inherits
   and defaults to without-sharing behavior at the entry). **Never omit the
   keyword** — an unstated sharing model is a finding, not a choice.

3. **Does this code legitimately need to see records the user can't?**
   (Cross-user rollups, dedup against all records, audit/log writers,
   integration sync)
   → **`without sharing`** — but only in a narrow, dedicated system-context
   class with an ApexDoc comment stating WHY, WHAT it exposes, and how output
   is filtered before returning to the user. Never on a controller; never as
   a blanket fix for "user can't see the record" bugs.

## OWD interplay (why the keyword sometimes "does nothing")

- Sharing declarations enforce **record access (sharing rules + OWD)**, NOT
  object CRUD or field-level security. `with sharing` alone is not FLS
  enforcement — that's user-mode SOQL/DML (below).
- If the object's OWD is **Public Read/Write**, `with sharing` and `without
  sharing` behave identically for reads — the keyword only bites when OWD is
  Private or Public Read Only. Don't conclude "sharing works" from a test in
  a Public Read/Write dev org.
- OWD Private + `with sharing` means a user sees only owned/shared records —
  design for empty query results, not just forbidden ones.
- Changing a class from `without` to `with sharing` in a live org can break
  integrations that silently depended on system visibility — audit callers
  first (this is why `inherited sharing` on shared layers is the standard).

## User-mode SOQL/DML (the FLS half)

Sharing keywords don't check CRUD/FLS. Pair them:

- Queries: `WITH USER_MODE` (preferred, API 58+) — enforces CRUD, FLS, AND
  sharing regardless of class keyword.
- DML: `insert as user records;` / `Database.insert(records, AccessLevel.USER_MODE)`.
- Object graphs from elsewhere: `Security.stripInaccessible(AccessType.READABLE, records)`.
- System-mode queries in a `without sharing` class are legitimate only inside
  the documented system-context class from rule 3.

Full detection patterns, severity scale, and remediation order: **sf-security**
(Sharing model category, 15 points; CRUD/FLS category, 25 points).

## When runAs tests are MANDATORY (not nice-to-have)

Write a `System.runAs(restrictedUser)` test whenever the class:

- Declares `with sharing` or `inherited sharing` AND the underlying object's
  OWD is Private/Public Read Only — prove a non-owner is actually filtered.
- Declares `without sharing` — prove the elevated path exposes ONLY what the
  ApexDoc justification claims (test the boundary, not just the feature).
- Uses `WITH USER_MODE`, `as user` DML, or `stripInaccessible` — prove the
  denial path throws/strips for a user missing the permission, AND the
  allow path succeeds for a permitted user. One direction alone proves half
  the requirement.
- Is a guest-user or Experience Cloud entry point — always, no exceptions.

Test construction (minimal-profile user factory, both-directions assertion
pattern) lives in **sf-test** — see its permission & sharing rubric category
(15 points) and its patterns reference.

## Quick table

| Class role | Keyword | Query/DML mode | runAs test |
| --- | --- | --- | --- |
| Controller / @AuraEnabled / Invocable | `with sharing` | `WITH USER_MODE` + `as user` | Mandatory if OWD restricts or FLS enforced |
| Service / selector / domain | `inherited sharing` | `WITH USER_MODE` default | Via its entry points |
| Documented system-context worker | `without sharing` | System mode, justified | Mandatory — test the exposure boundary |
| Trigger handler | `with sharing` (or inherited) | User mode unless justified | For any security-bearing branch |
| Async (Batch/Queueable/Scheduled) | `inherited sharing` or explicit | Runs as system — declare intent explicitly | If it touches user-visible data decisions |
