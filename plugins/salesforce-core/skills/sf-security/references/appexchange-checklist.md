# AppExchange Security Review Readiness Checklist

What the Salesforce security review team actually evaluates for a managed
package submission, organized as submission **blockers** vs **advisories**.
Written from the ISV side of the process.

## Blockers (fix before submitting)

### Code security
- [ ] Code Analyzer (`sf code-analyzer` / formerly sfdx-scanner) runs clean at
      severity 1–2, or every remaining flag has a documented false-positive
      justification (see format below)
- [ ] CRUD/FLS enforced on EVERY user-reachable entry point (@AuraEnabled,
      @RestResource, @InvocableMethod, VF controllers, web services)
- [ ] Every class declares sharing (`with`/`inherited`; `without` only with a
      documented system-context justification)
- [ ] No SOQL/SOSL built from unbound user input anywhere
- [ ] No secrets in code, custom settings, labels, or static resources —
      Named/External Credentials only
- [ ] No hardcoded org-specific IDs, usernames, or instance URLs

### Lightning / UI
- [ ] Components pass under Lightning Web Security (LWS) — no Locker-era
      workarounds, no eval/new Function, no unsanitized manual DOM
- [ ] @AuraEnabled methods verify access to the records whose IDs the client
      supplies (IDOR)
- [ ] External JS/CSS loaded from static resources, not CDNs (reviewers
      block runtime third-party loads)

### External integrations
- [ ] All callouts via Named Credentials; TLS 1.2+; no IP-address endpoints
- [ ] Third-party services receiving Salesforce data documented in the
      submission (data flow diagram expected for anything nontrivial)

### Tests
- [ ] ≥75% coverage that COMPILES AND PASSES in a clean scratch org install
- [ ] Security enforcement covered by runAs tests (deny cases, not just allow)
- [ ] No SeeAllData=true

### Package & org hygiene
- [ ] Installs cleanly into a fresh org (no dependencies on unpackaged config)
- [ ] Guest/Experience Cloud components: guest profile grants audited and
      minimal; no guest-reachable unfiltered queries
- [ ] Post-install scripts run without admin-only assumptions

## Advisories (won't always block, will draw questions)

- [ ] `WITH SECURITY_ENFORCED` still in use (works; USER_MODE preferred)
- [ ] Broad Remote Site Settings surviving from pre-Named-Credential days
- [ ] System.debug statements logging record data (clean them — cheap win)
- [ ] Permission sets not granular (one mega-permset invites questions about
      least privilege)
- [ ] Aura components that could be LWC (not a security issue per se, but
      Locker-era Aura draws extra scrutiny)

## False-positive documentation format

Reviewers accept justifications in this shape — one row per flagged instance:

| Scanner flag | Location | Why it's a false positive | Compensating control |
| --- | --- | --- | --- |
| SOQL injection | ReportBuilder.cls:88 | Field list built from Schema.describe allowlist, never user input | Allowlist validated at line 71 |

Vague entries ("reviewed, not exploitable") get the submission bounced —
name the exact control and line.

## Process notes

- Scan early: run Code Analyzer in CI from day one; a pre-submission scan
  surfacing 400 findings is a quarter-long detour.
- The review fee and queue times change; check the current Partner Community
  guidance rather than assuming.
- Re-review happens on major version updates — keep the false-positive doc
  maintained, not recreated.
- For Kugamon specifically: the kugo2p/kuga_sub packages have passed review;
  match new code to the patterns already in the shipped packages when in
  doubt.
