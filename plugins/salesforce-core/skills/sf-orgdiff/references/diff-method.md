# Diff Method — Per-Domain Inventory & Comparison

The engine behind sf-orgdiff. One principle governs everything here:
**inventory first, bodies last**. Names, versions, lengths, counts, and
dates classify almost every item; bodies are fetched only for the
both-but-different shortlist, and only when unmanaged. This keeps a
two-org diff to a few dozen queries instead of thousands of body fetches.

Tool names below are capability conventions — map them per the Tool-name
mapping preamble in `references/execution-modes.md`. "Tooling" means
`tooling_api_query`; "SOQL" means `soql_query`; raw REST paths go through
the connector's generic REST tool.

## Identity keys and comparison fields

Every domain defines:

- **Identity key** — how an item on side A is matched to side B. Always
  includes `NamespacePrefix` (null ≠ `'ns'`; an unmanaged `Foo` and a
  managed `ns__Foo` are different items).
- **Change signals** — cheap "checksum-ish" fields that mark an item
  Modified without reading its body.
- **Touch signal** — `LastModifiedDate` alone. Dates are UTC in the API on
  both orgs; compare raw values. A date difference with identical change
  signals = Touched (low signal), not Modified.

## Domain reference

### Apex classes

| | |
| --- | --- |
| Query (Tooling) | `SELECT Id, Name, NamespacePrefix, ApiVersion, Status, LengthWithoutComments, LastModifiedDate FROM ApexClass` |
| Identity key | `NamespacePrefix` + `Name` |
| Change signals | `LengthWithoutComments` (the workhorse — comment-insensitive size), `ApiVersion`, `Status` |
| Body fetch | `GET .../tooling/sobjects/ApexClass/{Id}` (query-level `Body` may be redacted); unmanaged only |
| Skip | Items whose namespace matches an installed package — covered by the package-version domain |

`LengthWithoutComments` equal on both sides is strong (not certain)
evidence of identical logic; unequal is proof of difference. That
asymmetry is fine for a drift report — flag equal-length/different-date
items as Touched and move on.

### Apex triggers

Same shape as classes on `ApexTrigger`, adding `TableEnumOrId` to both the
query and the report (a trigger diff means nothing without knowing which
object it fires on). `Status` matters doubly here: an Inactive trigger in
one org is a behavioral diff even with identical bodies.

### Flows

| | |
| --- | --- |
| Query (Tooling) | `SELECT Id, DeveloperName, NamespacePrefix, ActiveVersion.VersionNumber, LatestVersion.VersionNumber, LastModifiedDate FROM FlowDefinition` |
| Identity key | `NamespacePrefix` + `DeveloperName` |
| Change signals | `ActiveVersion.VersionNumber` (the behavioral truth), `LatestVersion.VersionNumber` |

Compare **active** versions for behavior and **latest** for pending work.
Null `ActiveVersion` = flow exists but is switched off — that alone is a
finding when the other side is active. Version numbers are org-local
counters, not content hashes: active v7 vs v5 does not say seven edits
happened, only that activation states diverged. When a flow's *content* is
suspect, fetch it via Tooling `sobjects/Flow/{Id}` and compare
`Metadata.start.object` and element counts before pulling full definitions.
Avoid `FlowDefinitionView` for cross-org matching — its label-based fields
are unreliable for namespaced flows (see sf-debug's FlowDefinitionView
gotcha).

### Custom objects

| | |
| --- | --- |
| Query (Tooling or SOQL) | `SELECT QualifiedApiName, NamespacePrefix, Label, KeyPrefix FROM EntityDefinition WHERE IsCustomizable = true` |
| Identity key | `QualifiedApiName` |
| Change signals | Field count (below), label |

`EntityDefinition` is a quirky virtual object: it doesn't support
queryMore/deep `OFFSET` (plain `COUNT()` generally works — verified live —
and can drive the counts-first pass). Keyset-paginate the inventory:
`WHERE QualifiedApiName > :last ORDER BY QualifiedApiName LIMIT 200`.
If a connector cannot query it at all, fall back to `list_sobjects` /
`sobject_describe`-style discovery and diff the returned name lists —
mark the domain "partial (names only)" in the summary.

### Fields

Two-stage, because fetching every field of every object on two orgs is the
single easiest way to blow up a run:

1. **Counts per object:** loop over the scoped object list (from the Phase-2 object inventory) and run `SELECT COUNT() FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = '<Object>'` per object, on both sides. This is the primary and only method — the platform does not support aggregate functions (`COUNT(Id)`/`GROUP BY`) on the FieldDefinition virtual entity, on any connector (verified live: `MALFORMED_QUERY`). Equal counts ⇒ presumed level; note the presumption in the report.
2. **Drill-down only where counts differ** (or the object is explicitly in
   scope): `SELECT QualifiedApiName, DataType, Length, Precision, Scale, IsCalculated, LastModifiedDate FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = '<Object>'` on both sides.

| | |
| --- | --- |
| Identity key | Object `QualifiedApiName` + field `QualifiedApiName` |
| Change signals | `DataType`, `Length`/`Precision`/`Scale`, `IsCalculated` |

`FieldDefinition` requires an EntityDefinition filter on most connectors —
it is not globally scannable. Same-name-different-type is a CRITICAL flag:
deployments fail or silently truncate on it.

### Validation rules

| | |
| --- | --- |
| Query (Tooling) | `SELECT Id, ValidationName, EntityDefinition.QualifiedApiName, NamespacePrefix, Active, LastModifiedDate FROM ValidationRule` |
| Identity key | Object + `NamespacePrefix` + `ValidationName` |
| Change signals | `Active` (a rule active in prod only is classic hotfix drift), error message/formula via body fetch on the shortlist |

### Permission sets

| | |
| --- | --- |
| Query (SOQL) | `SELECT Id, Name, NamespacePrefix, Type, LastModifiedDate FROM PermissionSet WHERE IsOwnedByProfile = false` |
| Identity key | `NamespacePrefix` + `Name` |
| Change signals | Presence, `Type`; contents via per-PS `ObjectPermissions`/`FieldPermissions` counts, only for scoped/suspect sets |

sf-orgdiff answers "which permission sets differ"; *how* they differ is
sf-permissions' job and *whether it matters* is sf-security's. Exclude
`Type = 'Session'` internal sets from the headline (see sf-permissions'
noise-filter rule) — but never exclude guest-site sets.

### Layouts & FlexiPages

Counts and names only — layout body diffs are not practical over Tooling
and rarely worth it.

| | |
| --- | --- |
| Layouts (Tooling) | `SELECT Id, Name, TableEnumOrId, NamespacePrefix, LastModifiedDate FROM Layout` |
| FlexiPages (Tooling) | `SELECT Id, DeveloperName, NamespacePrefix, Type, LastModifiedDate FROM FlexiPage` |
| Identity keys | `TableEnumOrId` + `Name` / `DeveloperName` |
| Change signals | Presence and per-object counts only; date = Touched |

### Custom labels

| | |
| --- | --- |
| Query (Tooling) | `SELECT Id, Name, NamespacePrefix, Language, Value, LastModifiedDate FROM ExternalString` |
| Identity key | `NamespacePrefix` + `Name` + `Language` |
| Change signals | `Value` (cheap enough to inventory directly — labels are short) |

### Remote sites & named credentials

| | |
| --- | --- |
| Remote sites (Tooling) | `SELECT Id, SiteName, EndpointUrl, IsActive FROM RemoteProxy` |
| Named credentials (SOQL) | `SELECT Id, DeveloperName, Endpoint, PrincipalType FROM NamedCredential` |
| Identity keys | `SiteName` / `DeveloperName` |
| Change signals | `EndpointUrl` / `Endpoint`, `IsActive` |

Endpoint URL differences are expected between sandbox and prod (pointing at
test vs live external systems) — report them, but in drift mode label the
*expected* pattern (same host, different subdomain/path stage) separately
from genuinely divergent endpoints. Never print credential secrets; these
queries return none, and body fetches are off-limits for this domain.

### Installed packages

| | |
| --- | --- |
| Query (Tooling) | `SELECT SubscriberPackage.Name, SubscriberPackage.NamespacePrefix, SubscriberPackageVersion.MajorVersion, SubscriberPackageVersion.MinorVersion, SubscriberPackageVersion.PatchVersion, SubscriberPackageVersion.BuildNumber FROM InstalledSubscriberPackage` |
| Identity key | `SubscriberPackage.NamespacePrefix` (fall back to package name for no-namespace packages) |
| Change signals | Version tuple (major.minor.patch.build) |

`InstalledSubscriberPackage` is **not queryable on every connector** (some
reject it outright). Fallback: build a namespace census from the domains
already inventoried — `SELECT NamespacePrefix, COUNT(Id) FROM ApexClass
GROUP BY NamespacePrefix` (plus EntityDefinition namespaces) — and diff the
namespace sets. That detects packages present in one org only; version skew
detection is then marked "unavailable on this connector" rather than
silently omitted.

## Comparison algorithm

For each scoped domain:

1. `COUNT()` on both orgs (works on EntityDefinition too; its quirks are
   pagination, not aggregates). Record both counts in the summary even
   when equal.
2. Inventory both sides with the domain query, keyset-paginated
   (`ORDER BY <key> LIMIT 200`, then `WHERE <key> > :last`). Tooling
   OFFSET caps at 2000; keyset has no cap, so use it from the start on any
   domain whose count exceeds one page.
3. Bucket on identity keys: only-in-source, only-in-target, both.
4. For `both`: any change signal differs → **Modified**; only
   `LastModifiedDate` differs → **Touched**; nothing differs → identical.
5. Managed-namespace items (namespace appears in the package inventory):
   drop from per-item buckets; their diff is the package version row.
6. Body fetch (Phase 4 of SKILL.md) for the unmanaged Modified shortlist
   where the body changes the recommendation — cap ~20, then check in.

In code-execution modes, do the bucketing in a script over saved inventory
JSON (two sorted lists, single merge pass) rather than eyeballing — it's
faster and it can't miss a row. In `mcp-core`, process one domain at a
time and discard raw inventories after bucketing to protect context.

## Reading the timestamps

- All API datetimes are UTC on both orgs. Never convert one side and not
  the other; label the zone if you render local time at all.
- A **sandbox refresh copies production's metadata and timestamps** — right
  after a refresh, dates match and honest drift is near zero. Ask (or query
  `SandboxInfo` where available) for the refresh date; only differences
  newer than it are true post-refresh drift.
- `LastModifiedDate` is a touch marker, not a content hash. It moves on
  no-op saves, deployment re-pushes, and some package upgrades. That is why
  it only ever produces the Touched bucket on its own.
