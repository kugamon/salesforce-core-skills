# When to use this collection (and when not to)

The Salesforce agent-skills ecosystem has excellent options. Honest guidance:

## Use salesforce-core-skills when…

- You're operating against a **live org through an MCP connector** — auditing, scoring, debugging, comparing, enriching. That's this collection's home turf: every skill is MCP-first and behaviorally tested against a live org ([evals/](../evals/)).
- You need **scored, evidence-cited reviews** (150-pt Apex, 110-pt Flow, 165-pt LWC, 120-pt tests, 100-pt security) or client-ready audit documents.
- You work in **managed-package / subscriber orgs** — these skills handle hidden code honestly instead of pretending to review it.
- You're an **ISV preparing for AppExchange security review** (sf-security's readiness checklist is written from the submitting side).
- You want **org-to-org drift detection** (sf-orgdiff) — unique to this collection.
- You run **Claude Desktop / Cowork** and want scheduled monitoring or live dashboards ([monitoring recipe](monitoring-recipe.md)), plus guardrail hooks that stop dangerous writes.

## Use Salesforce's official sf-skills library when…

- You're doing **greenfield development inside an SFDX project** — the official library's 175 micro-task skills cover the whole platform surface (Agentforce, Data 360, OmniStudio, Commerce, Mobile, LWR) with CLI-first workflows and Salesforce-maintained API currency.
- You need coverage for products this collection deliberately doesn't chase.

## Both together

They compose: official skills to build in a scratch org, this collection to audit, test, secure, and monitor what's running in real orgs. Nothing conflicts — different tool assumptions (CLI vs MCP), different jobs.
