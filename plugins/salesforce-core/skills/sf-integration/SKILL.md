---
name: sf-integration
plugin: salesforce-core
argument-hint: '[credentials|events|cdc|review] {name} ...'
metadata:
  version: 1.0.0
  minApiVersion: '60.0'
description: >
  Sets up and reviews Salesforce integrations — Named Credentials and External
  Credentials (creation, principal design, migration from legacy credentials
  and Remote Site Settings), OAuth flow selection, Platform Events
  (define/publish/subscribe/monitor/replay), Change Data Capture, and
  org-wide integration audits — MCP-first against the live org. Use when the
  user mentions a named credential, external credential, wants to connect to
  an external API, asks which OAuth flow to use, mentions platform events,
  CDC, change data capture, an integration audit, or callout setup.
  Usage: /sf-integration [credentials|events|cdc|review] {name} ...
---

# Salesforce Integration Setup & Review

Integration architect for live Salesforce orgs. Design the credential model,
pick the right OAuth flow, wire up event-driven patterns, and audit what's
already connected — leaving the org more secure than you found it.

## Security discipline (read this before anything else)

**This skill never touches an actual secret.** Client secrets, private keys,
certificates, passwords, and API keys are entered by the admin **directly in
the Setup UI** — never pasted into chat, never passed through an MCP call,
never stored in code, custom settings, or custom metadata.

- If the user pastes a secret, do not echo it, do not store it, and tell
  them to rotate it — a secret that has transited chat is burned.
- The skill's job is to build the **shell** (external credential, named
  credential, principal, permission set) and then hand the user the exact
  Setup path that finishes the job: **Setup → Named Credentials → External
  Credentials → {name} → Principals → Edit → enter the secret there.**
- Secrets are write-only in Salesforce by design: no API returns a stored
  client secret. Never attempt to "verify" one by reading it back — verify
  by making the callout.

## Dispatch

| First argument or intent                                        | Workflow            |
| --------------------------------------------------------------- | ------------------- |
| `credentials`, "named credential", "connect to an external API" | Credential Setup    |
| "which OAuth flow", "client credentials vs JWT"                 | OAuth Selection     |
| `events`, "platform event", "publish/subscribe"                 | Platform Events     |
| `cdc`, "change data capture", "change events"                   | Change Data Capture |
| `review`, "integration audit", "what's connected to this org"   | Integration Review  |

## Execution modes

See `references/execution-modes.md`. Initialize the connection first
(`org_init` convention). In headless runs, creating credentials, events, or
channel members is a gated org write — propose, don't execute, unless the
caller granted write permission (headless rule in the same reference).

**API reality check** (the honest version): `NamedCredential` and
`RemoteProxy` are Tooling-queryable, so inventory always works.
**ExternalCredential is a Metadata API entity** for *creation* — it is *not*
creatable via Tooling REST sObject inserts, and neither is the modern (v56+)
NamedCredential that references one. Tooling *querying* of ExternalCredential
IS accepted on some connectors, though (verified live at v59) — query first,
fall back to `metadata_read`/Setup UI listing only if the entity errors. Route creates through the `metadata_create` convention
only when the connector implements the SOAP Metadata API; otherwise fall back
to the executeAnonymous MetadataService pattern (see the CustomObject caveat
in sf-metadata — same platform limitation, same fallback). `PlatformEvent`
definitions (CustomObject with `__e` suffix) and `PlatformEventChannelMember`
follow the same Metadata API path. Don't burn calls retrying Tooling payload
variants — it fails at every API version.

---

## Credential Setup

Modern model (v56+): **External Credential** holds the auth protocol and
principals; **Named Credential** holds the endpoint URL and points at the
external credential. One external credential can back many named credentials.

1. **Gather** — endpoint URL, auth protocol (OAuth 2.0 / AWS Sig4 / JWT /
   Basic / Custom — prefer OAuth *when the remote side actually offers it*;
   many SaaS APIs, Stripe and SendGrid included, authenticate with a static
   API key instead — that's an external credential with Custom-header or
   Basic auth, **not** an OAuth flow; see the API-key row in
   `references/auth-patterns.md`), and who calls it (see principal choice
   below).
2. **Create the ExternalCredential** (Metadata API) — protocol, auth
   provider or token endpoint, and a named principal *placeholder*. No
   secret values in the payload, ever.
3. **Create the NamedCredential** (Metadata API) — URL + reference to the
   external credential. Set `generateAuthorizationHeader` deliberately;
   disable it only when the Apex code builds its own header.
4. **Grant access via permission set** — the step everyone forgets. Users
   (including the integration user and the Automated Process user for
   flows) get `externalCredentialPrincipalAccesses` in a permission set, or
   callouts fail with a misleading 401. Details in
   `references/auth-patterns.md`.
5. **Hand off the secret entry** — tell the user exactly which Setup screen
   to open and which principal to fill in (see Security discipline above).
6. **Verify** — a scripted test callout via `apex_execute`
   (`callout:{NamedCredential}/path`), never by reading secrets back.

**Per-principal vs named-principal:** named principal = one identity for the
whole org (server-to-server, the common case). Per-user principal = each user
authenticates individually (user-context APIs, per-user audit trails on the
remote side). Choosing named-principal for a user-context API is a compliance
smell — flag it.

**Migration paths:**

- **Legacy Named Credentials** (auth defined on the named credential itself)
  still work but are deprecated. Migrate: create an external credential with
  the same protocol, repoint or recreate the named credential, re-enter
  secrets in Setup, regrant via permission set. Apex `callout:` references
  survive unchanged if the developer name is kept.
- **Remote Site Settings** exist to whitelist raw URLs for code that builds
  its own auth — which usually means secrets are hardcoded or in custom
  settings. Each remote site is a candidate for conversion to a named
  credential; the Review workflow (below) finds and ranks them.

## OAuth Selection

Full decision table, prerequisites, and gotchas: `references/auth-patterns.md`.
The one-breath version:

| Flow | Use when |
| --- | --- |
| Client credentials | Server-to-server, no user context, run-as integration user |
| JWT bearer | Headless with certificate trust, no shared secret, CI/CD |
| Authorization code | A human's own identity and permissions must apply |
| (Not OAuth) API key / static bearer | Remote API uses a static secret key (Stripe, SendGrid, ...) — External Credential with Custom or Basic auth; don't force an OAuth flow |

When the user wants to *see* the flow, hand off to **sf-diagram** (`oauth`
mode) — it draws these exact sequences. Explain the choice here; draw it there.

## Platform Events

- **Define** — a CustomObject named `{Name}__e` (Metadata API path, per the
  reality check above). Choose `publishAfterCommit` (default; events roll
  back with the transaction) vs `publishImmediately` (fires even on
  rollback — logging/telemetry only).
- **Publish** — Apex `EventBus.publish()`, REST insert on
  `/sobjects/{Name}__e` (works through the MCP DML convention — handy for
  test publishes), Flow, or external CometD/Pub-Sub API clients. Always
  check `SaveResult`; publish can fail per-event.
- **Subscribe** — Apex trigger (after insert, runs as Automated Process
  user), Flow (platform event-triggered), or external CometD/Pub-Sub API
  subscriber.

**Monitoring** — `EventBusSubscriber` is regular-SOQL queryable:

```sql
SELECT ExternalId, Name, Type, Topic, Position, Tip,
       Retries, LastError, Status
FROM EventBusSubscriber
```

`Tip` is the latest replay ID published on the channel; `Position` is where
this subscriber has read to. Healthy = Position tracks Tip.

**The stalled-subscriber diagnostic:** `Position` frozen well behind a moving
`Tip` with `Status = 'Running'` means the trigger is **silently erroring** —
platform event triggers fail without surfacing anything to users. Check
`Retries`/`LastError`; after the retry budget is exhausted the subscription
suspends (`Status = 'Error'`). Hand off to **sf-debug** to trace the
Automated Process user and read the failure. Resume a suspended trigger from
Setup → Platform Events → the event → Subscriptions.

**Replay semantics** — replay IDs are per-channel, ascending, **not
contiguous**. `-1` = new events only; `-2` = earliest retained (standard
retention 72 hours). A stored replay ID older than retention throws an
invalid-replay error — subscribers must handle it by falling back to `-1`
or `-2` and reconciling the gap. Replay IDs are opaque: never arithmetic on
them, only compare and resume.

## Change Data Capture

- **Enable** — Setup → Change Data Capture (zero-cost manual path), or
  deploy a `PlatformEventChannelMember` on the `ChangeEvents` channel with
  `selectedEntity` = `{Object}ChangeEvent` (e.g. `AccountChangeEvent`;
  custom objects use `{Object}__ChangeEvent`). Entity selections count
  against a per-org allocation — inventory before adding.
- **Subscribe** — Apex change event trigger (async, Automated Process user)
  or external Pub-Sub API / CometD client. `ChangeEventHeader` carries
  `changeType`, `changedFields`, `recordIds`, and `transactionKey` — use
  `transactionKey` to group events from one transaction.
- **Gotchas** admins hit in order: (1) update events carry **only changed
  fields** — unchanged fields arrive as null, so never treat an event as a
  full record snapshot; (2) **gap and overflow events** (`GAP_CREATE`,
  `GAP_OVERFLOW`, etc.) replace normal events under load or after certain
  internal operations — subscribers must re-query the record by ID, and code
  that ignores gap events silently drops data; (3) ordering is guaranteed
  per record within a transaction, not across entities; (4) monitoring and
  replay work exactly like platform events — the EventBusSubscriber query
  and stalled-subscriber diagnostic above apply verbatim.

## Integration Review

Inventory, flag, and produce a migration plan. All reads — headless-safe.

1. **Inventory** (Tooling queries):

```sql
SELECT SiteName, EndpointUrl, IsActive, Description FROM RemoteProxy
SELECT DeveloperName, MasterLabel, Endpoint, PrincipalType FROM NamedCredential
```

   (Run as two separate calls. A 0-row success — as opposed to an
   INVALID_TYPE error — still confirms the entity is queryable; don't retry
   payload variants.)

   External credentials: try
   `SELECT DeveloperName, MasterLabel FROM ExternalCredential` via Tooling
   query first — it is accepted on some connectors; fall back to
   `metadata_read` or a Setup UI listing if the entity errors (say which
   one you used). Add the EventBusSubscriber query when events are in play.

2. **Flag** —
   - remote sites that should be named credentials (any remote site whose
     endpoint hosts an authenticated API);
   - legacy named credentials (PrincipalType set, no external credential)
     that should migrate to the modern model;
   - inactive remote sites and orphaned credentials (attack surface);
   - stalled or errored event subscribers.
3. **Hand off the code side** — hardcoded endpoints and secrets in Apex are
   **sf-security**'s scan (it greps bodies with line-level evidence);
   recurring callout failures and timeout patterns are **sf-debug**'s
   log analysis. Don't duplicate either here.
4. **Report** — a migration table, one row per endpoint:

| Endpoint | Today | Target | Priority | Blocker |
| --- | --- | --- | --- | --- |
| api.example.com | Remote Site + hardcoded key | Named Cred (client credentials) | High | Secret rotation needed |

Priority: hardcoded secrets → High; legacy named creds → Medium; cleanup →
Low. Note that migration is admin work in Setup for every secret re-entry.

## Cross-skill handoffs

- Draw the chosen OAuth flow or integration sequence → **sf-diagram**
- Hardcoded endpoint/secret scan across the codebase → **sf-security**
- Callout failures, timeouts, stalled-subscriber tracing → **sf-debug**
- `HttpCalloutMock` / event test patterns → **sf-test** (checklist in
  `references/auth-patterns.md`)
- Permission set mechanics beyond principal access → **sf-permissions**

## References

| File | Read when |
| --- | --- |
| `references/auth-patterns.md` | OAuth decision table, principal mapping, permission-set access, callout testing |
| `references/execution-modes.md` | Start of session |
