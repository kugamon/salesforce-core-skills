# salesforce-core-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Claude Desktop / Cowork **plugin marketplace** that ships a single plugin (`salesforce-core`) with **thirteen general-purpose Salesforce admin & developer skills** — Apex, Flow, SOQL/Data, LWC, Metadata, Permissions, Architecture Diagrams, Org Audit, Test Generation, Security Review, Debug Log Analysis, Campaign Analytics, and Lead Enrichment.

This repo **does not install an MCP server**. It assumes you already have a Salesforce MCP server connected to your org. The skills are **tool-agnostic** — they reference MCP capabilities generically rather than one vendor's tool names, so they work with any Salesforce MCP server.

## Why this plugin

Out of the box, Claude can call your Salesforce MCP server's tools — but it doesn't know:

- **How to write production-grade Apex** (bulkification, governor limits, SOLID, trigger frameworks) or score it consistently
- **How to build Flows that pass review** (naming, fault paths, entry conditions, subflow patterns)
- **How to optimize SOQL** (selectivity, indexes) or run safe bulk DML with cleanup/rollback plans
- **How to audit an org end-to-end** and produce Word / Excel / HTML reports
- **How to write tests that catch regressions** (assertion quality, 200-record bulk proofs, runAs enforcement tests) and run them via the Tooling API
- **What the AppExchange security review checks** (CRUD/FLS, injection, sharing, secrets) and how to get submission-ready
- **How to read a debug log** — trace flags, limit meters, SOQL-in-loop signatures, row-lock diagnosis
- **How to enrich CRM data safely** — active-picklist verification, source attribution, anti-fabrication rules
- **Which execution mode to use** — local SFDX metadata, Salesforce CLI, MCP + code execution, or MCP-only

This plugin encodes those rules as Cowork skills with structured scoring rubrics (150-point Apex, 110-point Flow, 165-point LWC SLDS 2, 120-point tests, 100-point security), reference guides, metadata schemas, and validation scripts. After you install it, Claude routes Salesforce tasks to the right skill automatically.

## What problems do these skills solve?

| Pain point | Skill | What it does |
| --- | --- | --- |
| An org audit takes a consultant weeks | **sf-audit** | 18 scored documents (Word/Excel/HTML) from a single scan |
| Apex review quality depends on who reviews | **sf-apex** | Consistent 150-point rubric with line-level evidence |
| Test classes are coverage padding | **sf-test** | 120-point rubric that caps assertion-free tests at 60/120 |
| AppExchange security review failures | **sf-security** | Blockers-vs-advisories checklist + 100-point scored audit |
| Debug logs are unreadable walls of text | **sf-debug** | Diagnosis / Evidence / Fix / Prevention from trace to root cause |
| "Who has access to X?" takes a day to answer | **sf-permissions** | Permission set analysis and access auditing |
| Campaign ROI is guesswork | **sf-campaigns** | Funnels, ROI math shown, invest/pause recommendations |
| The CRM is full of blank or wrong lead data | **sf-leads** | Cited, confidence-rated enrichment with approval gates |

## Prerequisites

You need a Salesforce MCP server connected to Claude Desktop, wired to your target org. Options include:

1. **[salesforce-mcp-auto-auth-chrome](https://github.com/kugamon/salesforce-mcp-auto-auth-chrome)** — local MCP server with 14 Salesforce tools that auto-refreshes its session from your Chrome login (no tokens to paste).
2. **Any other Salesforce MCP server** — the skills reason about capabilities (SOQL query, DML, metadata create, Tooling API), not specific tool names.

## The 13 skills

| Skill | What it does | Scoring |
| --- | --- | --- |
| [sf-apex](plugins/salesforce-core/skills/sf-apex/README.md) | Create, update and review Apex classes and triggers | 150-point |
| [sf-flow](plugins/salesforce-core/skills/sf-flow/README.md) | Create, update and review Flows | 110-point |
| [sf-data](plugins/salesforce-core/skills/sf-data/README.md) | SOQL build/optimize/execute, DML, test data factories | — |
| [sf-lwc](plugins/salesforce-core/skills/sf-lwc/README.md) | Lightning Web Components development | 165-point SLDS 2 |
| [sf-metadata](plugins/salesforce-core/skills/sf-metadata/README.md) | Metadata creation, org queries, permission set generation | — |
| [sf-permissions](plugins/salesforce-core/skills/sf-permissions/README.md) | Permission Set analysis, "Who has X?" auditing | — |
| [sf-diagram](plugins/salesforce-core/skills/sf-diagram/README.md) | Architecture diagrams (ERDs, OAuth flows, integrations) in Mermaid | — |
| [sf-audit](plugins/salesforce-core/skills/sf-audit/README.md) | Comprehensive org audit with Word, Excel and HTML reports | — |
| [sf-test](plugins/salesforce-core/skills/sf-test/README.md) | Generate, review, and run Apex test classes | 120-point |
| [sf-security](plugins/salesforce-core/skills/sf-security/README.md) | Security audit + AppExchange review readiness | 100-point |
| [sf-debug](plugins/salesforce-core/skills/sf-debug/README.md) | Debug log capture and analysis via the Tooling API | — |
| [sf-campaigns](plugins/salesforce-core/skills/sf-campaigns/README.md) | Campaign performance, funnels, ROI, and lead-source analysis | — |
| [sf-leads](plugins/salesforce-core/skills/sf-leads/README.md) | Lead/Contact enrichment with citations, confidence ratings, and approval gates | — |

## Org connection convention

The skills refer to `org_init` as shorthand for **your MCP server's session/connection initialization step**. Tool names vary by server:

- If your Salesforce MCP server exposes a connection or init tool, call it first and confirm the target org.
- If it does not, verify connectivity with a lightweight query (e.g. `SELECT Id FROM Organization LIMIT 1`) before running operations.

Likewise, generic tool names used in the skills (`soql_query`, `sobject_dml`, `metadata_create`, `tooling_api_query`, …) map to the equivalent tools on your server — most Salesforce MCP servers expose the same capabilities under similar names.

## Execution modes

Each skill detects one of four execution modes per session and adapts:

| Mode | When | What it enables |
| --- | --- | --- |
| `sfdx-repo` | Working dir is an SFDX project with metadata on disk | Read metadata locally, no API calls for body retrieval |
| `cli` | Salesforce CLI (`sf`) installed and authenticated | Bulk retrieve, CLI queries, code execution |
| `mcp-plus-code-execution` | MCP server + local Python/shell | MCP for org access, scripts for analysis and reports |
| `mcp-only` | MCP server only | Everything via MCP tools, paginated |

See any skill's `references/execution-modes.md` for details.

## Report standards

Skills that generate documents (sf-audit, sf-security) follow shared standards in [`report-template.md`](plugins/salesforce-core/skills/sf-audit/references/report-template.md): every scored report includes charts and tables (score gauges, category breakdowns, severity distributions, top-N offenders), and every HTML deliverable is a **single self-contained file** — inline CSS/JS, inline SVG charts, no external requests — with modern card-based design and tasteful scroll-reveal animations.

## Repo layout

```
salesforce-core-skills/                  # repo root = a marketplace
├── .claude-plugin/
│   └── marketplace.json                 # marketplace manifest (lists 1 plugin)
├── README.md                            # you are here
├── LICENSE                              # MIT
└── plugins/
    └── salesforce-core/                 # the plugin itself
        ├── .claude-plugin/
        │   └── plugin.json              # plugin manifest
        ├── hooks/                       # PreToolUse validation hooks
        ├── shared/                      # shared validator scripts
        └── skills/
            ├── sf-apex/                 # each skill: SKILL.md + README +
            ├── sf-audit/                #   references/ + assets/ + scripts/
            ├── sf-campaigns/
            ├── sf-data/
            ├── sf-debug/
            ├── sf-diagram/
            ├── sf-flow/
            ├── sf-leads/
            ├── sf-lwc/
            ├── sf-metadata/
            ├── sf-permissions/
            ├── sf-security/
            └── sf-test/
```

The marketplace pattern means future contributors can add more plugins under `plugins/<name>/` and register them in `marketplace.json` — the install URL stays the same.

## Install

### Option 1 — Cowork "Add marketplace" (recommended)

1. Open Claude Desktop → **Customize** → **Marketplace**.
2. Click **+ Add marketplace** (sometimes labeled **Sync from URL**).
3. URL: `kugamon/salesforce-core-skills` — or the full URL `https://github.com/kugamon/salesforce-core-skills`.
4. Click **Sync**. You'll see one plugin: `salesforce-core`.
5. Click **Install**.
6. Restart Claude (Cmd+Q + reopen on macOS) so the skills load into the system prompt.

### Option 2 — Local folder

1. Clone the repo or download the source.
2. In Claude Desktop → **Customize** → **Personal plugins** → **+** → **Local folder**.
3. Pick `plugins/salesforce-core/` (the directory that contains `.claude-plugin/plugin.json`).
4. Toggle on. Restart Claude.

### Option 3 — Manually pin to settings.json

```json
{
  "extraKnownMarketplaces": [
    { "url": "https://github.com/kugamon/salesforce-core-skills" }
  ],
  "enabledPlugins": ["salesforce-core"]
}
```

## Try it without an org

The repo ships synthetic sample data (`sample-data/`) so you can see the skills work before connecting a Salesforce MCP server:

> "Using the sample data in sample-data/, which campaigns are actually working? Rank by ROI and flag data problems."

> "Run a gap analysis on sample-data/leads.csv — which records need enrichment, and which emails look wrong?"

See [sample-data/README.md](sample-data/README.md) for what's in the dataset (including the deliberate data-quality problems to find).

## Verify

After installing and restarting, test a skill:

> "Review all Apex triggers in my org for bulkification issues and governor limit risks. For each issue found, suggest a fix and score the code."

Claude should detect the execution mode, connect to your Salesforce MCP server, and run the sf-apex review workflow with 150-point scoring.

## Sample prompts

- "Perform a thorough audit of the Apex classes and Flows in my Salesforce org. Generate Word, HTML and Excel versions of the report."
- "Write tests for AccountService and show me the coverage."
- "Is this codebase ready for AppExchange security review?"
- "Why am I getting 'Too many SOQL queries: 101' on opportunity save?"
- "Which campaigns are actually working? Rank them by ROI."
- "Find leads missing industry or title and enrich the top 10."
- "Analyze all my profiles and permission sets and recommend security fixes and cleanup."
- "Create an ERD diagram for my Sales Cloud data model including Account, Contact, Opportunity, and Lead."

## Model choice

For reports, analysis and simple metadata tasks a fast model (e.g. Sonnet) is a good, cost-effective choice. For deeper design or debugging work, a more capable model may be needed.

## Troubleshooting

**"This repository isn't a marketplace — no manifest found at .claude-plugin/marketplace.json".** Make sure you're on `main` — the manifest lives at the repo root.

**Plugin loads but skills don't trigger.** Restart Claude Desktop fully (Cmd+Q on macOS). Skills are loaded at session start.

**Tools missing entirely.** Confirm your Salesforce MCP server is connected and authenticated to the right org. Check `claude_desktop_config.json`, or ask Claude: *"what's the org name?"* — a working server answers via a SOQL query on `Organization`.

**Skill references a tool your server doesn't have.** The skills use generic tool names (`soql_query`, `sobject_dml`, `metadata_create`, …). Map them to your server's equivalents — see [Org connection convention](#org-connection-convention).

## Contributing

PRs welcome. Especially useful contributions:

- Additional skills (e.g. sf-deploy, sf-docs, sf-integration) — drop a folder under `plugins/salesforce-core/skills/`
- New plugins under `plugins/<name>/`, registered in `marketplace.json`
- Improved scoring rubrics and reference guides as Salesforce releases evolve

Keep skill files terse — a focused skill that triggers correctly beats a sprawling one Claude scrolls past.

## Related projects

- **[salesforce-mcp-auto-auth-chrome](https://github.com/kugamon/salesforce-mcp-auto-auth-chrome)** — our recommended Salesforce MCP server (auto-auth from Chrome).
- **[forcedotcom/sf-skills](https://github.com/forcedotcom/sf-skills)** — Salesforce's official skill library. Broader platform coverage (Agentforce, Data 360, OmniStudio, Commerce), SFDX-project-first. Use it for greenfield development inside an SFDX project; use this repo for MCP-connected live-org admin, audit, and data work.
- **[elijeangilles/revops-skills](https://github.com/elijeangilles/revops-skills)** — complementary RevOps analytics pack (pipeline hygiene, forecast prep) that also runs against any Salesforce MCP server.
- **[kugamon/kugamon-skills](https://github.com/kugamon/kugamon-skills)** — Quote-to-Cash and Subscription Management skills for orgs running the Kugamon managed packages, built on top of this plugin.

## License

MIT — see [LICENSE](./LICENSE).

Portions derived from the MIT-licensed [sf-skills](https://github.com/Jaganpro/sf-skills) project by Jag Valaiyapathy; original copyright notices are preserved in the LICENSE file. Per-skill credits are in each skill's `CREDITS.md`.

This project is **not affiliated with Salesforce, Inc. or with Anthropic.** Tool names, APIs, and platform behavior may change as Salesforce evolves; verify against official Salesforce documentation.
