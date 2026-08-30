# Authentication Patterns

Companion reference for the sf-integration Credential Setup and OAuth
Selection workflows. Security discipline from SKILL.md applies to every
pattern here: secrets are entered in the Setup UI by the admin, never
transited through chat, code, or MCP calls.

## OAuth flow decision table

| Flow | When | Prerequisites | Gotchas |
| --- | --- | --- | --- |
| **Client credentials** | Server-to-server, no user context: middleware, ETL, webhook processors calling into or out of Salesforce as a fixed identity | Connected app (or external credential) with client credentials enabled; a dedicated **integration user** assigned as the run-as user — never a human's account | All access is the run-as user's access: over-permission it and every caller inherits that. Secret rotation is a coordinated outage unless you stage two credentials. No refresh tokens — tokens are re-minted per request/expiry. |
| **JWT bearer** | Cert-based headless: CI/CD, scheduled jobs, ISV backends — anywhere a shared secret is unacceptable or unrotatable | Connected app with digital certificate uploaded; the integration user **pre-authorized** via profile/permission set on the connected app (JWT has no consent screen — an unapproved user gets `invalid_grant`) | `invalid_grant` is almost always pre-authorization or a clock-skewed/expired JWT, not the cert. Audience (`aud`) must match the login host exactly (`login` vs `test` vs My Domain). Private key lives on the caller's side — Salesforce never holds it. |
| **Authorization code** (+ PKCE) | A human's own identity, permissions, and audit trail must apply on the remote system — per-user external credentials, user-facing OAuth apps | Callback URL registered; per-user principal on the external credential; users complete the consent dance themselves from Setup or the first callout | Refresh token policy decides whether users re-consent constantly — check the remote side's expiry. Never proxy the consent step for the user. For per-user principals each user authenticates individually; there is no bulk "authorize everyone". |
| **API key / static bearer** (not an OAuth flow) | The remote API authenticates with a static secret key — many SaaS APIs work this way (Stripe, SendGrid, Twilio, etc.) | External credential with **Custom** auth (secret injected as an `Authorization: Bearer ...` or vendor-specific header via a per-principal authentication parameter) or **Basic** auth where the API expects key-as-username; principal design as for client credentials (named principal, dedicated integration identity where the remote side supports it) | Do not force an OAuth flow onto a key-based API — there is no token endpoint to talk to. The key is entered in Setup UI only (standard secret discipline). Rotation is manual: stage the new key as a second principal or coordinate a cutover. |

Rules of thumb:

- Remote side uses a static API key (Stripe, SendGrid, ...) → no OAuth
  flow at all; External Credential with Custom or Basic auth, principal
  design as for client credentials.
- No human in the loop + secret storage acceptable → client credentials.
- No human in the loop + certificate trust available → JWT bearer (prefer
  it over client credentials when the remote side supports it; nothing to
  leak but a public cert).
- Human in the loop → authorization code, with PKCE for anything that
  cannot hold a secret (mobile, SPA).

To visualize any of these sequences, hand off to **sf-diagram** (`oauth`
mode) — it draws exactly these flows.

## External credential principal mapping

An external credential defines *how* to authenticate; a **principal** is a
named slot holding *whose* credentials are used.

| Principal type | Identity model | Typical use |
| --- | --- | --- |
| Named principal | One identity for every caller in the org | Server-to-server APIs, org-level SaaS accounts |
| Per-user principal | Each user authorizes and stores their own tokens | User-context APIs (calendars, personal data stores), remote-side per-user audit requirements |

- A named credential picks up **all** principals of its external
  credential; access control decides which principal a given user actually
  exercises.
- Principal names are referenced by permission sets (below) and by
  `Callout` options in Apex — keep them short and stable; renaming a
  principal breaks the permission-set grant.
- Named-principal against an API that expects individual users is a
  compliance smell: the remote audit log shows one identity for everyone.
  Flag it during review.

## Permission-set access (the step everyone forgets)

Creating the credential is not enough. Under the modern model, a user can
execute a callout through a named credential **only if a permission set
(or profile) grants them access to the external credential's principal**.
Symptom of the missing grant: a 401/403 on the callout that looks exactly
like bad credentials — while Workbench/curl with the same secret works.

1. Create (or reuse) a permission set, e.g. `Integration_Callouts`.
2. Add the principal grant — Setup UI: Permission Set → External Credential
   Principal Access → Edit. Metadata equivalent:

   ```xml
   <externalCredentialPrincipalAccesses>
       <enabled>true</enabled>
       <externalCredentialPrincipal>MyExtCred-NamedPrincipal</externalCredentialPrincipal>
   </externalCredentialPrincipalAccesses>
   ```

   (Format: `{ExternalCredentialDeveloperName}-{PrincipalName}`.)
3. Assign to every identity that executes the callout — including the
   **integration user** and, for flow- or event-triggered callouts, the
   **Automated Process user** context where applicable.
4. Legacy named credentials skip this mechanism entirely — one more reason
   they linger; migration must add the grant or callouts break on day one.

Prefer permission sets over profile edits throughout (see sf-metadata's
cost guidance — profile updates are expensive and unmaintainable). Broader
permission-set architecture questions → **sf-permissions**.

## Callout test guidance

Apex tests cannot make real callouts — every test path through a callout
needs a mock, or the test fails with "methods defined as TestMethod do not
support Web service callouts".

- Implement `HttpCalloutMock` (single response) or
  `Test.setMock(HttpCalloutMock.class, new MultiRequestMock(...))` style
  routers for multi-endpoint transactions.
- Assert on the **request** your code built (endpoint, method, headers,
  body), not only on how it handled the response — that is where named
  credential regressions hide.
- Cover the failure paths: non-200 statuses, timeouts
  (`System.CalloutException`), and malformed bodies. Integration code that
  only tests the happy path fails its first real outage.
- `callout:MyCredential` endpoints resolve fine under mock — tests do not
  need the credential to exist, so CI orgs don't need secrets. (The
  `callout:Name` endpoint is a runtime-resolved string — Apex referencing
  a nonexistent named credential compiles and deploys fine; at runtime in
  a real org the named credential must exist by name, or the callout
  fails.)
- Platform event tests: `Test.startTest()` … `EventBus.publish()` …
  `Test.stopTest()` delivers events synchronously to Apex trigger
  subscribers; assert on the trigger's side effects. Use
  `Test.getEventBus().deliver()` for mid-test delivery.

Full test generation, assertions style, and coverage strategy → **sf-test**.
