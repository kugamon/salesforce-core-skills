# Changelog

Releases: https://github.com/kugamon/salesforce-core-skills/releases

## [2.3.0] — 2026-08-30
- **sf-records** — add record stewardship skill and promote shared data-quality canon **ci** — push an annotated release tag so gh release create can find it link Salesforce's official sf-skills library in the positioning section move when-to-use-what guidance into the README

## [2.2.0] — 2026-08-30
- **ci** — automate releases from conventional commit history

## [2.0.0] — 2026-08-30
- New flagship skill **sf-orgdiff** (org-to-org drift/release/baseline comparison, read-only, identity-gated) and **sf-integration** (Named/External Credentials, OAuth flow selection, Platform Events, CDC — with a no-secrets-through-chat discipline). Fifteen skills total.
- **Shared canon**: decision trees (automation, async, sharing) and copyable Apex templates (TriggerHandler, TestDataFactory, Logger) under `plugins/salesforce-core/shared/`, wired from sf-apex/sf-flow/sf-test/sf-security.
- **Governance**: CONTRIBUTING, SECURITY, issue/PR templates (bug reports double as eval-case intake), this changelog.
- **Docs**: evals methodology (evals/README.md), Cowork monitoring recipe, when-to-use-what positioning; sample animated audit report in docs/demo/.

## [1.5.1] — 2026-08-30 — iteration-2 residual sweep: flow-validator false positives fixed (clean flow = 110/110), honest validator headlines, doc fixes across ten skills, teaching-accurate sample data.
## [1.5.0] — 2026-08-30 — reviewer subagents (apex-reviewer, security-auditor), minApiVersion metadata, behavioral eval iteration 2 (33/39, 0 FAIL, 8/8 fixes verified).
## [1.4.0] — 2026-08-30 — eval results published in-repo, guardrails G2/G3 promoted to blocking "ask", npx skills add support verified.
## [1.3.1] — 2026-08-30 — behavioral-eval fix pass: tool-name mapping preamble everywhere, managed-package honesty, validator repairs.
## [1.3.0] — 2026-08-30 — sample-data zero-setup demo, guardrail hooks, CI validation + evals, custom-field discernment, README pain-point table.
## [1.2.x] — 2026-08 — sf-campaigns + sf-leads migrated and generalized; universal data-quality rules; docs.
## [1.1.x] — 2026-08 — sf-test, sf-security, sf-debug; report visualization + single-file animated HTML standards.
## [1.0.0] — 2026-07 — initial eight skills as a Claude plugin marketplace.
