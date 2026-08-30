# Standing Org Monitoring (Cowork recipe)

The skills in this repo answer questions on demand. In Claude Desktop / Cowork they can also run **on a schedule** and render to a **live dashboard** — a capability GitHub-only skill collections can't offer. Two recipes:

## Weekly audit digest (scheduled task)

Ask Claude:

> "Every Monday at 7am, run an apex-and-automation-scoped sf-audit against my sandbox connector and message me a summary: overall score, what changed since last week, and anything that dropped."

Notes that make this work well:
- **Scope the audit** (apex/flow/permissions) — a full 18-document audit is an on-demand job, not a weekly one.
- **Point it at a sandbox or dev connector**; keep production read-only and rate-friendly.
- The headless rules in every skill's execution-modes.md apply automatically: read-only steps run, gated writes stay propose-only.
- Keep last week's summary in the task's context ("compare against the previous run") so the digest reports *deltas*, not the same list every week.

## Live org-health dashboard (artifact)

Ask Claude:

> "Create a live artifact dashboard for my org: overall audit score gauge, flows without fault paths, classes below 75% coverage, permission sets granting ModifyAllData, and open guardrail flags — refreshed from my Salesforce connector each time I open it."

The artifact calls your Salesforce MCP connector on open, so numbers are current without re-running a full audit. Design per the report standards (sf-audit's report-template §7–8): score gauges, category bars, severity pills. Keep queries inventory-level (counts and names) so a refresh takes seconds.

## Escalation pattern

Combine both: the weekly digest watches, and when a score drops or a CRITICAL appears, ask Claude to run the relevant deep skill (sf-audit full domain, sf-security review, sf-orgdiff against the last-known-good) and report before/after.
